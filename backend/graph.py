from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph

from .config import settings
from .event_store import event_store
from .models import EiaTaskState, NodeResult
from .task_store import task_store


GraphMode = Literal["step", "run"]
GraphRoute = Literal["execute", "dispatch", "end"]
NodeRunner = Callable[..., Awaitable[NodeResult]]


class GraphState(TypedDict, total=False):
    task_id: str
    mode: GraphMode
    status: str | None
    current_node: str | None
    next_node: str | None
    pause_requested: bool
    executed_node: str | None
    result_status: str | None
    error: str | None
    graph_route: GraphRoute


@dataclass
class GraphRunResult:
    state: GraphState
    task: EiaTaskState
    executed_node: str | None = None
    result: NodeResult | None = None


def _project_task_state(task: EiaTaskState, *, mode: GraphMode, graph_route: GraphRoute) -> GraphState:
    return {
        "task_id": task.task_id,
        "mode": mode,
        "status": task.status,
        "current_node": task.current_node,
        "next_node": task.next_node,
        "pause_requested": task.pause_requested,
        "executed_node": None,
        "result_status": None,
        "error": task.error,
        "graph_route": graph_route,
    }


class EiaGraphRuntime:
    """LangGraph outer workflow runtime.

    Hermes remains responsible for the autonomous work inside each HB node. This
    runtime only owns node ordering, pause checks, node-boundary checkpointing,
    and task-state projection back to the existing FastAPI/frontend API.
    """

    def __init__(
        self,
        *,
        node_runner: NodeRunner,
        implemented_nodes: set[str],
        checkpoint_db: Path | None = None,
    ) -> None:
        self.node_runner = node_runner
        self.implemented_nodes = implemented_nodes
        self.checkpoint_db = checkpoint_db or settings.langgraph_checkpoint_db
        self.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)

    def _build_graph(self):
        async def dispatch(state: GraphState) -> GraphState:
            task_id = state["task_id"]
            mode: GraphMode = state.get("mode") or "step"
            task = task_store.get(task_id)

            if task.pause_requested:
                task.status = "paused"
                task.current_node = None
                task.active_hermes_run_id = None
                task_store.save(task)
                event_store.append(task_id, "task_paused", "Task paused before next node")
                return _project_task_state(task, mode=mode, graph_route="end")

            if not task.next_node:
                if task.status != "completed":
                    task.status = "completed"
                    task.current_node = None
                    task.active_hermes_run_id = None
                    task_store.save(task)
                    event_store.append(task_id, "task_completed", "Task completed")
                return _project_task_state(task, mode=mode, graph_route="end")

            if task.next_node not in self.implemented_nodes:
                task.status = "failed"
                task.current_node = None
                task.active_hermes_run_id = None
                task.error = f"Node is not implemented yet: {task.next_node}"
                task_store.save(task)
                event_store.append(task_id, "task_failed", task.error)
                return _project_task_state(task, mode=mode, graph_route="end")

            return _project_task_state(task, mode=mode, graph_route="execute")

        async def execute_node(state: GraphState) -> GraphState:
            task_id = state["task_id"]
            mode: GraphMode = state.get("mode") or "step"
            task = task_store.get(task_id)
            node_id = task.next_node
            if not node_id:
                return _project_task_state(task, mode=mode, graph_route="end")

            try:
                result = await self.node_runner(task, node_id, continue_on_success=mode == "run")
            except Exception as exc:  # noqa: BLE001
                latest = task_store.get(task_id)
                latest.status = "failed"
                latest.current_node = None
                latest.active_hermes_run_id = None
                latest.error = str(exc)
                task_store.save(latest)
                event_store.append(task_id, "task_failed", str(exc), node_id=node_id)
                projected = _project_task_state(latest, mode=mode, graph_route="end")
                projected["executed_node"] = node_id
                projected["result_status"] = "failed"
                return projected

            latest = task_store.get(task_id)
            if mode == "run" and result.status == "completed" and latest.status == "running" and latest.next_node:
                graph_route: GraphRoute = "dispatch"
            else:
                graph_route = "end"

            projected = _project_task_state(latest, mode=mode, graph_route=graph_route)
            projected["executed_node"] = node_id
            projected["result_status"] = result.status
            return projected

        def route_after_dispatch(state: GraphState) -> str:
            return "execute_node" if state.get("graph_route") == "execute" else END

        def route_after_execute(state: GraphState) -> str:
            return "dispatch" if state.get("graph_route") == "dispatch" else END

        graph = StateGraph(GraphState)
        graph.add_node("dispatch", dispatch)
        graph.add_node("execute_node", execute_node)
        graph.set_entry_point("dispatch")
        graph.add_conditional_edges("dispatch", route_after_dispatch, {"execute_node": "execute_node", END: END})
        graph.add_conditional_edges("execute_node", route_after_execute, {"dispatch": "dispatch", END: END})
        return graph

    async def _invoke(self, task_id: str, mode: GraphMode) -> GraphRunResult:
        input_state: GraphState = {
            "task_id": task_id,
            "mode": mode,
            "status": None,
            "current_node": None,
            "next_node": None,
            "pause_requested": False,
            "executed_node": None,
            "result_status": None,
            "error": None,
            "graph_route": "dispatch",
        }
        config = {"configurable": {"thread_id": task_id}}
        async with AsyncSqliteSaver.from_conn_string(str(self.checkpoint_db)) as checkpointer:
            await checkpointer.setup()
            graph = self._build_graph().compile(checkpointer=checkpointer)
            state = await graph.ainvoke(input_state, config)

        task = task_store.get(task_id)
        executed_node = state.get("executed_node")
        result = task.module_results.get(executed_node) if executed_node else None
        return GraphRunResult(state=state, task=task, executed_node=executed_node, result=result)

    async def step(self, task_id: str) -> GraphRunResult:
        return await self._invoke(task_id, "step")

    async def run(self, task_id: str) -> GraphRunResult:
        return await self._invoke(task_id, "run")

    async def checkpoint_state(self, task_id: str) -> dict[str, Any]:
        config = {"configurable": {"thread_id": task_id}}
        if not self.checkpoint_db.exists():
            return {"exists": False}
        try:
            async with AsyncSqliteSaver.from_conn_string(str(self.checkpoint_db)) as checkpointer:
                await checkpointer.setup()
                graph = self._build_graph().compile(checkpointer=checkpointer)
                snapshot = await graph.aget_state(config)
        except Exception as exc:  # noqa: BLE001
            return {"exists": False, "error": str(exc)}
        return {
            "exists": bool(snapshot.values),
            "values": snapshot.values,
            "next": list(snapshot.next),
            "metadata": snapshot.metadata,
        }

    async def sync_task_state(self, task_id: str, *, mode: GraphMode = "step") -> dict[str, Any]:
        task = task_store.get(task_id)
        graph_route: GraphRoute = "dispatch" if task.next_node and task.status in {"created", "running"} else "end"
        values = _project_task_state(task, mode=mode, graph_route=graph_route)
        config = {"configurable": {"thread_id": task_id}}
        async with AsyncSqliteSaver.from_conn_string(str(self.checkpoint_db)) as checkpointer:
            await checkpointer.setup()
            graph = self._build_graph().compile(checkpointer=checkpointer)
            await graph.aupdate_state(config, values, as_node="dispatch")
            snapshot = await graph.aget_state(config)
        return {
            "exists": bool(snapshot.values),
            "values": snapshot.values,
            "next": list(snapshot.next),
            "metadata": snapshot.metadata,
        }
