#!/usr/bin/env python3
"""Exercise the full Codex provider route without calling a model endpoint.

The real sidecar is covered by CX-02. This smoke test focuses on the business
server contract: every entrypoint selects Codex by default, node completion is
gated by the envelope validator, failures do not advance the route, and
feedback/file-validation use the same provider-neutral execution path.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import sys
import tempfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _configure(root: Path) -> None:
    os.environ.update(
        {
            "EIA_AGENT_PROVIDER": "codex",
            "CODEX_AGENT_BASE_URL": "http://127.0.0.1:8765",
            "UPLOAD_DIR": str(root / "uploads"),
            "LANGGRAPH_CHECKPOINT_DIR": str(root / "tasks"),
            "LANGGRAPH_CHECKPOINT_DB": str(root / "checkpoints.sqlite"),
            "TASK_WORKSPACE_DIR": str(root / "workspaces"),
            "OUTPUT_DIR": str(root / "outputs"),
            "LOG_DIR": str(root / "logs"),
            "VISION_CACHE_DIR": str(root / "vision-cache"),
            "KNOWLEDGE_DIR": str(root / "knowledge"),
        }
    )


class FakeCodexClient:
    def __init__(self) -> None:
        self.counter = 0
        self.records: dict[str, dict] = {}
        self.requests: list[dict] = []
        self.fail_next = False

    async def health(self) -> dict:
        return {"status": "ok", "agent": "fake-codex"}

    async def create_run(self, user_input: str, **kwargs) -> dict:
        self.requests.append({"input": user_input, **kwargs})
        self.counter += 1
        run_id = f"fake-run-{self.counter}"
        node_match = re.search(r"节点：([^\s\n]+)", user_input)
        node_id = node_match.group(1) if node_match else "FILE-VALIDATION"
        if self.fail_next:
            self.records[run_id] = {"status": "failed", "error": "fake upstream failure", "output": ""}
            self.fail_next = False
        else:
            markdown_sections = {
                "PREP-INGEST": "资料包读取概况\n\n项目档案摘要\n\n资料矛盾与不确定项\n\n后续研判可用输入\n\n需补充资料",
                "HB-PT-000": "资料完整性总判断\n\n关键字段提取与缺失判断\n\n建议启动模块\n\n补充资料清单",
                "HB-PT-002": "行业类别判定\n\n环评类别判定\n\n审批路径初判\n\n判断依据表\n\n需补充资料与人工复核要点",
                "HB-PT-009": "同类项目资料来源与可比性\n\n同类项目主要工艺流程及产污节点\n\n污染源与治理措施借鉴\n\n相似点和差异点\n\n工程分析建议",
            }
            markdown = markdown_sections.get(node_id, "资料验证总判断\n\n文件逐项验证表\n\n人工复核清单")
            markdown = "# 测试结果\n\n" + markdown + "\n\n以上为AI辅助初步研判，最终结论需由环评工程师人工复核确认。\n" + ("依据：https://www.mee.gov.cn/" * 8)
            envelope = {
                "completion_state": "completed",
                "node_id": node_id,
                "markdown": markdown,
                "structured_json": json.dumps({"summary": "fake completed", "node_data": {"node": node_id}}, ensure_ascii=False),
                "evidence_refs": [{
                    "title": "生态环境部",
                    "url": "https://www.mee.gov.cn/",
                    "issuer": "生态环境部",
                    "source_type": "url",
                    "locator": "首页",
                    "claim": "官方来源测试",
                }],
                "limitations": [],
                "disclaimer": "以上为AI辅助结果，最终需由环评工程师人工复核确认。",
            }
            self.records[run_id] = {"status": "completed", "output": json.dumps(envelope, ensure_ascii=False), "structured": envelope}
        return {"run_id": run_id, "status": "queued"}

    async def get_run(self, run_id: str) -> dict:
        return {"run_id": run_id, **self.records[run_id]}

    async def stop_run(self, run_id: str) -> dict:
        self.records[run_id]["status"] = "interrupted"
        return {"run_id": run_id, "status": "interrupted"}

    async def stream_run_events(self, run_id: str):
        record = self.records[run_id]
        yield {"event": "run.started", "run_id": run_id}
        if record["status"] == "failed":
            yield {"event": "run.failed", "error": record["error"]}
            return
        yield {"event": "tool.started", "tool": "commandExecution"}
        yield {"event": "tool.completed", "tool": "commandExecution"}
        yield {"event": "message.delta", "delta": "structured result is being prepared"}
        yield {"event": "agent_context_compacted"}
        yield {"event": "usage.updated", "usage": {"input_tokens": 100, "output_tokens": 50}}
        yield {"event": "run.completed", "output": record["output"], "usage": {"input_tokens": 100, "output_tokens": 50}}


async def run() -> None:
    with tempfile.TemporaryDirectory(prefix="eia-cx03-contract-") as raw_root:
        root = Path(raw_root)
        _configure(root)
        from backend import main
        from backend.models import EiaTaskState, NodeResult
        from backend.task_store import task_store

        fake = FakeCodexClient()
        main.codex_agent_client = fake
        assert main.settings.agent_provider == "codex"
        expected_entrypoints = {"PREP-INGEST", *main.NODE_PROMPTS, "FILE-VALIDATION", "WEB-SEARCH"}
        assert main._agent_provider("PREP-INGEST") == "codex"
        assert expected_entrypoints >= set(main.NODE_PROMPTS)

        for node_id in ("PREP-INGEST", "HB-PT-000", "HB-PT-002", "HB-PT-009"):
            task = EiaTaskState(task_id=f"task-{node_id.lower()}", next_node=node_id, project_text="测试项目资料。")
            task_store.create(task)
            result = await main._run_node(task, node_id)
            saved = task_store.get(task.task_id)
            assert result.status == "completed", (node_id, result.error)
            assert saved.module_results[node_id].agent_provider == "codex"
            assert saved.next_node == main.NEXT_NODE[node_id]
            events = [event.type for event in main.event_store.iter_events(task.task_id)]
            assert "node_complete" in events and "tool_event" in events and "agent_context_compacted" in events

        failure = EiaTaskState(task_id="task-failure", next_node="HB-PT-002", project_text="测试项目资料。")
        task_store.create(failure)
        fake.fail_next = True
        failed = await main._run_node(failure, "HB-PT-002")
        saved_failure = task_store.get(failure.task_id)
        assert failed.status == "failed"
        assert saved_failure.status == "failed"
        assert saved_failure.next_node == "HB-PT-002"

        aux_task = EiaTaskState(task_id="task-aux", next_node="PREP-INGEST", project_text="测试项目资料。")
        task_store.create(aux_task)
        aux_prompt = main._build_aux_prompt(aux_task, "aux_file_validation.txt", {}, node_id="FILE-VALIDATION")
        aux_result = await main._execute_agent_aux(
            task=aux_task,
            node_id="FILE-VALIDATION",
            title="资料验证",
            user_input=aux_prompt,
            output_task_id=aux_task.task_id,
            persist_result=True,
            output_prefix="FILE-VALIDATION",
        )
        assert aux_result.status == "completed"
        assert task_store.get(aux_task.task_id).module_results["FILE-VALIDATION"].agent_provider == "codex"

        feedback_task = EiaTaskState(task_id="task-feedback", next_node="HB-PT-001", project_text="测试项目资料。")
        feedback_task.module_results["HB-PT-000"] = NodeResult(
            node_id="HB-PT-000",
            status="completed",
            markdown="旧结果",
            structured={"summary": "old"},
        )
        task_store.create(feedback_task)
        revised = await main.feedback_node(
            feedback_task.task_id,
            "HB-PT-000",
            {"feedback": "请补充完整性判断依据", "action": "revise"},
        )
        saved_feedback = task_store.get(feedback_task.task_id)
        assert revised.status == "completed", revised.error
        assert saved_feedback.module_results["HB-PT-000"].agent_provider == "codex"
        assert saved_feedback.next_node == "HB-PT-001"
        assert fake.requests
        assert all(request.get("instructions") for request in fake.requests)
        assert all("必须使用 Codex 原生 Web Search" in request["instructions"] for request in fake.requests)
        assert all("不得使用 Shell、curl、wget" in request["instructions"] for request in fake.requests)

        print(json.dumps({
            "provider": main.settings.agent_provider,
            "representative_nodes": 4,
            "failure_gate": "passed",
            "auxiliary_agent": "passed",
            "feedback_revision": "passed",
            "developer_instructions": "passed",
        }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
