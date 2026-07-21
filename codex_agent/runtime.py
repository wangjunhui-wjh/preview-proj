from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import re
from typing import Any, AsyncIterator
from uuid import uuid4

from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, LocalImageInput, Sandbox, TextInput
from openai_codex.generated.v2_all import ReasoningEffort

from .config import Settings
from .models import AgentRun, CreateRunRequest, now_iso


TERMINAL_STATUSES = {"completed", "failed", "interrupted"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    return value


def _model_dump(value: Any) -> dict[str, Any]:
    dumped = _jsonable(value)
    return dumped if isinstance(dumped, dict) else {}


def _item_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    item = payload.get("item")
    return item if isinstance(item, dict) else {}


def _write_toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


@dataclass(slots=True)
class RunContext:
    record: AgentRun
    request: CreateRunRequest | None
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    events: list[dict[str, Any]] = field(default_factory=list)
    task: asyncio.Task[None] | None = None
    turn_handle: Any = None
    terminal_event_written: bool = False


class CodexRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.codex: AsyncCodex | None = None
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_runs)
        self.runs: dict[str, RunContext] = {}
        self._closing = False

    async def start(self) -> None:
        self.settings.validate()
        self.settings.ensure_dirs()
        self._write_app_config()
        env = {
            "CODEX_HOME": str(self.settings.codex_home),
            "OPENAI_API_KEY": self.settings.openai_api_key,
            "OPENAI_BASE_URL": self.settings.openai_base_url,
            "OPENAI_MODEL": self.settings.openai_model,
        }
        self.codex = AsyncCodex(
            CodexConfig(
                cwd=str(self.settings.workspace_root),
                env=env,
                client_name="eia_codex_agent",
                client_title="EIA Codex Agent",
            )
        )
        await self.codex.__aenter__()
        self._load_persisted_runs()

    async def close(self) -> None:
        self._closing = True
        active = [run_id for run_id, context in self.runs.items() if context.record.status in {"queued", "running"}]
        for run_id in active:
            await self.stop(run_id)
        tasks = [context.task for context in self.runs.values() if context.task and not context.task.done()]
        if tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=30)
            except asyncio.TimeoutError:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        if self.codex is not None:
            await self.codex.close()
            self.codex = None

    def _write_app_config(self) -> None:
        content = "\n".join(
            [
                'model_provider = "EiaOpenAI"',
                f"model = {_write_toml_string(self.settings.openai_model)}",
                f"review_model = {_write_toml_string(self.settings.openai_model)}",
                f"model_reasoning_effort = {_write_toml_string(self.settings.reasoning_effort)}",
                "disable_response_storage = true",
                'network_access = "enabled"',
                'approval_policy = "never"',
                "suppress_unstable_features_warning = true",
                "",
                "[model_providers.EiaOpenAI]",
                'name = "EiaOpenAI"',
                f"base_url = {_write_toml_string(self.settings.openai_base_url)}",
                'env_key = "OPENAI_API_KEY"',
                'wire_api = "responses"',
                "requires_openai_auth = false",
                "",
                "[features]",
                "standalone_web_search = true",
                "remote_compaction_v2 = true",
                "shell_snapshot = false",
                "plugins = false",
                "apps = false",
                "",
                "[shell_environment_policy]",
                'inherit = "core"',
                'exclude = ["OPENAI_API_KEY", "CODEX_AGENT_API_KEY", "*_API_KEY", "*_TOKEN", "*_SECRET", "*PASSWORD*", "*CREDENTIAL*"]',
                "",
            ]
        )
        self.settings.codex_home.mkdir(parents=True, exist_ok=True)
        (self.settings.codex_home / "config.toml").write_text(content, encoding="utf-8")

    def _record_path(self, run_id: str) -> Path:
        return self.settings.state_dir / f"{run_id}.json"

    def _event_path(self, run_id: str) -> Path:
        return self.settings.state_dir / f"{run_id}.events.jsonl"

    def _persist_record(self, context: RunContext) -> None:
        path = self._record_path(context.record.run_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(context.record.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def _load_persisted_runs(self) -> None:
        for path in sorted(self.settings.state_dir.glob("run_*.json")):
            try:
                record = AgentRun.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if record.status in {"queued", "running"}:
                record.status = "interrupted"
                record.error = "Sidecar restarted before the run reached a terminal state."
                record.completed_at = now_iso()
            context = RunContext(record=record, request=None)
            self.runs[record.run_id] = context
            self._persist_record(context)

    def health(self) -> dict[str, Any]:
        try:
            sdk_version = importlib.metadata.version("openai-codex")
            runtime_version = importlib.metadata.version("openai-codex-cli-bin")
        except importlib.metadata.PackageNotFoundError:
            sdk_version = "unknown"
            runtime_version = "unknown"
        return {
            "status": "ok" if self.codex is not None else "starting",
            "agent": "codex-sdk",
            "sdk_version": sdk_version,
            "runtime_version": runtime_version,
            "model": self.settings.openai_model,
            "wire_api": "responses",
            "active_runs": sum(
                context.record.status in {"queued", "running"} for context in self.runs.values()
            ),
        }

    def _safe_path(self, raw_path: str, *, roots: tuple[Path, ...], suffixes: set[str] | None = None) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError(f"Only absolute paths are accepted: {raw_path}")
        resolved = path.resolve(strict=True)
        if suffixes and resolved.suffix.lower() not in suffixes:
            raise ValueError(f"Unsupported image type: {raw_path}")
        for root in roots:
            try:
                resolved.relative_to(root.resolve())
                return resolved
            except ValueError:
                continue
        raise ValueError(f"Path is outside the Agent input roots: {raw_path}")

    def _validate_request(self, request: CreateRunRequest) -> list[Path]:
        if not SAFE_ID_RE.fullmatch(request.session_id):
            raise ValueError("Invalid session_id")
        roots = (self.settings.input_root, self.settings.vision_root, self.settings.workspace_root)
        return [self._safe_path(path, roots=roots, suffixes=IMAGE_SUFFIXES) for path in request.local_images]

    async def create(self, request: CreateRunRequest) -> AgentRun:
        if self.codex is None or self._closing:
            raise RuntimeError("Codex runtime is not ready")
        local_images = self._validate_request(request)
        run_id = f"run_{uuid4().hex}"
        workspace = self.settings.workspace_root / request.session_id / run_id
        workspace.mkdir(parents=True, exist_ok=True)
        record = AgentRun(run_id=run_id, session_id=request.session_id, workspace=str(workspace))
        context = RunContext(record=record, request=request)
        self.runs[run_id] = context
        self._persist_record(context)
        await self._append_event(context, "run.created", {"run_id": run_id, "session_id": request.session_id})
        context.task = asyncio.create_task(self._execute(context, local_images), name=f"codex-run-{run_id}")
        return record

    async def get(self, run_id: str) -> AgentRun:
        context = self.runs.get(run_id)
        if context is None:
            raise KeyError(run_id)
        return context.record

    async def stop(self, run_id: str) -> AgentRun:
        context = self.runs.get(run_id)
        if context is None:
            raise KeyError(run_id)
        if context.record.status in TERMINAL_STATUSES:
            return context.record
        context.record.stop_requested = True
        self._persist_record(context)
        await self._append_event(context, "run.stop_requested", {"run_id": run_id})
        if context.turn_handle is not None:
            await context.turn_handle.interrupt()
        return context.record

    async def events(self, run_id: str, after: int = 0) -> AsyncIterator[dict[str, Any] | None]:
        context = self.runs.get(run_id)
        if context is None:
            raise KeyError(run_id)
        cursor = max(after, 0)
        while True:
            batch: list[dict[str, Any]] = []
            terminal = False
            heartbeat = False
            async with context.condition:
                batch = [event for event in context.events if int(event["id"]) > cursor]
                terminal = context.record.status in TERMINAL_STATUSES
                if not batch and not terminal:
                    try:
                        await asyncio.wait_for(
                            context.condition.wait(),
                            timeout=self.settings.event_heartbeat_seconds,
                        )
                    except asyncio.TimeoutError:
                        heartbeat = True
                    batch = [event for event in context.events if int(event["id"]) > cursor]
                    terminal = context.record.status in TERMINAL_STATUSES
            if heartbeat and not batch:
                yield None
                continue
            for event in batch:
                cursor = int(event["id"])
                yield event
            if terminal and not batch:
                return

    async def _append_event(self, context: RunContext, event_name: str, payload: dict[str, Any]) -> None:
        event = {
            "id": len(context.events) + 1,
            "event": event_name,
            "run_id": context.record.run_id,
            "at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        context.events.append(event)
        with self._event_path(context.record.run_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        async with context.condition:
            context.condition.notify_all()

    async def _set_status(
        self,
        context: RunContext,
        status: str,
        *,
        error: str | None = None,
        output: str | None = None,
    ) -> None:
        context.record.status = status  # type: ignore[assignment]
        context.record.error = error
        if output is not None:
            context.record.output = output
        if status in TERMINAL_STATUSES:
            context.record.completed_at = now_iso()
        self._persist_record(context)

    def _tool_summary(self, item: dict[str, Any]) -> dict[str, Any]:
        item_type = str(item.get("type", "unknown"))
        summary: dict[str, Any] = {
            "type": item_type,
            "item_id": item.get("id"),
        }
        field_map = {
            "command": "command",
            "query": "query",
            "status": "status",
            "exitCode": "exit_code",
            "durationMs": "duration_ms",
            "cwd": "cwd",
        }
        for source, target in field_map.items():
            if source in item and item[source] is not None:
                value = item[source]
                summary[target] = str(value)[:4000] if isinstance(value, str) else value
        return summary

    async def _execute(self, context: RunContext, local_images: list[Path]) -> None:
        request = context.request
        if request is None:
            return
        async with self.semaphore:
            if context.record.stop_requested:
                await self._set_status(context, "interrupted", error="Run stopped before execution started.")
                await self._append_event(context, "run.cancelled", {"reason": "stop_requested_before_start"})
                return
            await self._set_status(context, "running")
            context.record.started_at = now_iso()
            self._persist_record(context)
            await self._append_event(context, "run.started", {"session_id": request.session_id})
            try:
                if self.codex is None:
                    raise RuntimeError("Codex runtime is not ready")
                thread = await self.codex.thread_start(
                    approval_mode=ApprovalMode.deny_all,
                    developer_instructions=request.instructions,
                    cwd=context.record.workspace,
                    model=self.settings.openai_model,
                    model_provider="EiaOpenAI",
                    sandbox=Sandbox.full_access,
                )
                context.record.thread_id = thread.id
                input_items: list[Any] = []
                if request.conversation_history:
                    history = "\n\n".join(
                        f"{entry.get('role', 'context')}: {entry.get('content', '')}"
                        for entry in request.conversation_history
                    )
                    input_items.append(TextInput(f"Prior run context:\n{history}"))
                input_items.append(TextInput(request.input))
                input_items.extend(LocalImageInput(str(path)) for path in local_images)
                context.turn_handle = await thread.turn(
                    input_items,
                    approval_mode=ApprovalMode.deny_all,
                    effort=ReasoningEffort(self.settings.reasoning_effort),
                    output_schema=request.output_schema,
                    sandbox=Sandbox.full_access,
                )
                context.record.turn_id = context.turn_handle.id
                self._persist_record(context)
                await self._append_event(
                    context,
                    "agent_run_started",
                    {"thread_id": thread.id, "turn_id": context.turn_handle.id},
                )
                await self._consume_turn(context)
            except Exception as exc:  # noqa: BLE001
                await self._set_status(context, "failed", error=f"Codex execution error: {exc}")
                await self._append_event(context, "run.failed", {"error": str(exc)})
            finally:
                context.turn_handle = None

    async def _consume_turn(self, context: RunContext) -> None:
        assert context.turn_handle is not None
        async for notification in context.turn_handle.stream():
            method = notification.method
            payload = _model_dump(notification.payload)
            if method == "item/agentMessage/delta":
                delta = str(payload.get("delta") or "")
                if delta:
                    context.record.output += delta
                    await self._append_event(
                        context,
                        "message.delta",
                        {"delta": delta, "native_method": method},
                    )
                continue
            if method == "thread/tokenUsage/updated":
                usage = payload.get("tokenUsage") or {}
                context.record.usage = usage
                self._persist_record(context)
                await self._append_event(context, "usage.updated", {"usage": usage, "native_method": method})
                continue
            if method in {"item/started", "item/completed"}:
                item = _item_from_payload(payload)
                item_type = item.get("type")
                if item_type in {"commandExecution", "webSearch", "imageView", "fileChange", "collabAgentToolCall", "mcpToolCall"}:
                    summary = self._tool_summary(item)
                    context.record.tool_trace.append({"event": method, **summary})
                    self._persist_record(context)
                    event_name = "tool.started" if method == "item/started" else "tool.completed"
                    await self._append_event(
                        context,
                        event_name,
                        {"tool": item_type, "summary": summary, "native_method": method},
                    )
                elif item_type == "contextCompaction" and method == "item/completed":
                    await self._append_event(context, "agent_context_compacted", {"native_method": method})
                elif item_type == "reasoning" and method == "item/completed":
                    await self._append_event(
                        context,
                        "reasoning.available",
                        {"native_method": method, "summary_available": True},
                    )
                elif item_type == "agentMessage" and method == "item/completed":
                    phase = item.get("phase")
                    if phase in {None, "finalAnswer", "final_answer"} and item.get("text"):
                        context.record.output = str(item["text"])
                        try:
                            parsed = json.loads(context.record.output)
                            if isinstance(parsed, dict):
                                context.record.structured = parsed
                        except json.JSONDecodeError:
                            pass
                        self._persist_record(context)
                continue
            if method == "turn/completed":
                turn = payload.get("turn") or {}
                status = str(turn.get("status") or "failed")
                error = (turn.get("error") or {}).get("message") if isinstance(turn.get("error"), dict) else None
                if status == "completed":
                    await self._set_status(context, "completed", error=error)
                    await self._append_event(
                        context,
                        "run.completed",
                        {"output": context.record.output, "usage": context.record.usage},
                    )
                elif status == "interrupted":
                    await self._set_status(context, "interrupted", error=error or "Turn interrupted")
                    await self._append_event(context, "run.cancelled", {"reason": "turn_interrupted"})
                else:
                    await self._set_status(context, "failed", error=error or f"Turn ended with status: {status}")
                    await self._append_event(context, "run.failed", {"error": context.record.error})
                context.terminal_event_written = True
                return
        if not context.terminal_event_written:
            await self._set_status(context, "failed", error="Codex stream ended without turn/completed")
            await self._append_event(context, "run.failed", {"error": context.record.error})
