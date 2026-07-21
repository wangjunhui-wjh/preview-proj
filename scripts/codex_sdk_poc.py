#!/usr/bin/env python3
"""Run an isolated Codex SDK capability check without touching live services."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

import img2pdf
from openai_codex import (
    ApprovalMode,
    AsyncCodex,
    CodexConfig,
    LocalImageInput,
    Sandbox,
    TextInput,
)
from openai_codex.generated.v2_all import ReasoningEffort


STRUCTURED_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok"]},
        "file_content": {"type": "string"},
        "command_used": {"type": "boolean"},
    },
    "required": ["status", "file_content", "command_used"],
    "additionalProperties": False,
}

WEB_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok"]},
        "title": {"type": "string"},
        "official_url": {"type": "string"},
        "finding": {"type": "string"},
    },
    "required": ["status", "title", "official_url", "finding"],
    "additionalProperties": False,
}

DOCUMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok"]},
        "text_pdf_finding": {"type": "string"},
        "scan_pdf_finding": {"type": "string"},
        "docx_finding": {"type": "string"},
        "image_finding": {"type": "string"},
        "tools_used": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "text_pdf_finding",
        "scan_pdf_finding",
        "docx_finding",
        "image_finding",
        "tools_used",
    ],
    "additionalProperties": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--text-pdf", type=Path, required=True)
    parser.add_argument("--flow-pdf", type=Path, required=True)
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--event-log", type=Path, required=True)
    return parser.parse_args()


def normalize_base_url(value: str) -> str:
    normalized = value.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return normalized.rstrip("/")


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def write_codex_config(home: Path, model: str, base_url: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            'model_provider = "OpenAI"',
            f"model = {toml_string(model)}",
            f"review_model = {toml_string(model)}",
            'model_reasoning_effort = "xhigh"',
            "disable_response_storage = true",
            'network_access = "enabled"',
            'approval_policy = "never"',
            "suppress_unstable_features_warning = true",
            "",
            "[model_providers.OpenAI]",
            'name = "OpenAI"',
            f"base_url = {toml_string(base_url)}",
            'wire_api = "responses"',
            'env_key = "OPENAI_API_KEY"',
            "requires_openai_auth = false",
            "",
            "[features]",
            "standalone_web_search = true",
            "remote_compaction_v2 = true",
            "",
        ]
    )
    (home / "config.toml").write_text(content, encoding="utf-8")


def prepare_fixtures(root: Path, text_pdf: Path, flow_pdf: Path, docx: Path) -> dict[str, Path]:
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "text_pdf": workspace / "technical_agreement.pdf",
        "flow_pdf": workspace / "process_flow.pdf",
        "docx": workspace / "prompt_reference.docx",
        "image": workspace / "process_flow_page.png",
        "scan_pdf": workspace / "process_flow_scan.pdf",
    }
    shutil.copy2(text_pdf, fixtures["text_pdf"])
    shutil.copy2(flow_pdf, fixtures["flow_pdf"])
    shutil.copy2(docx, fixtures["docx"])
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-singlefile",
            "-png",
            str(fixtures["flow_pdf"]),
            str(fixtures["image"].with_suffix("")),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    fixtures["scan_pdf"].write_bytes(img2pdf.convert(str(fixtures["image"])))
    return fixtures


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if is_dataclass(value):
        return asdict(value)
    return value


def append_event(path: Path, test: str, method: str, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "test": test,
        "method": method,
        "payload": jsonable(payload),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def item_dict(payload: dict[str, Any]) -> dict[str, Any]:
    item = payload.get("item")
    return item if isinstance(item, dict) else {}


async def run_streamed_turn(
    thread: Any,
    test: str,
    input_value: Any,
    event_log: Path,
    output_schema: dict[str, Any] | None = None,
    interrupt_on_command: bool = False,
) -> dict[str, Any]:
    handle = await thread.turn(
        input_value,
        approval_mode=ApprovalMode.deny_all,
        effort=ReasoningEffort.xhigh,
        output_schema=output_schema,
        sandbox=Sandbox.full_access,
    )
    methods: list[str] = []
    item_types: list[str] = []
    commands: list[str] = []
    searches: list[str] = []
    final_response: str | None = None
    status: str | None = None
    error: Any = None
    usage: Any = None
    interrupt_requested = False

    async for notification in handle.stream():
        method = notification.method
        payload = jsonable(notification.payload)
        append_event(event_log, test, method, payload)
        methods.append(method)
        if not isinstance(payload, dict):
            continue

        if method in {"item/started", "item/completed"}:
            item = item_dict(payload)
            item_type = str(item.get("type", "unknown"))
            item_types.append(item_type)
            if item_type == "commandExecution":
                command = str(item.get("command", ""))
                if command:
                    commands.append(command[:500])
                if interrupt_on_command and not interrupt_requested:
                    await handle.interrupt()
                    interrupt_requested = True
            elif item_type == "webSearch":
                searches.append(str(item.get("query", ""))[:500])
            elif item_type == "agentMessage" and method == "item/completed":
                if item.get("phase") in {"finalAnswer", "final_answer", None}:
                    final_response = str(item.get("text", ""))

        if method == "thread/tokenUsage/updated":
            usage = payload.get("tokenUsage")
        elif method == "turn/completed":
            turn = payload.get("turn") or {}
            status = str(turn.get("status", ""))
            error = turn.get("error")

    parsed: Any = None
    if final_response:
        try:
            parsed = json.loads(final_response)
        except json.JSONDecodeError:
            parsed = None
    return {
        "turn_id": handle.id,
        "status": status,
        "error": error,
        "final_response": final_response,
        "parsed_response": parsed,
        "event_counts": dict(Counter(methods)),
        "item_types": item_types,
        "commands": commands,
        "searches": searches,
        "usage": usage,
        "interrupt_requested": interrupt_requested,
        "approval_event_seen": any("approval" in method.lower() for method in methods),
    }


async def compact_thread(thread: Any, event_log: Path) -> dict[str, Any]:
    await thread.compact()
    deadline = time.monotonic() + 120
    compacted = False
    while time.monotonic() < deadline:
        read = await thread.read(include_turns=True)
        data = read.model_dump(mode="json", by_alias=True)
        turns = ((data.get("thread") or {}).get("turns") or [])
        compacted = any(
            item.get("type") == "contextCompaction"
            for turn in turns
            for item in turn.get("items", [])
            if isinstance(item, dict)
        )
        append_event(
            event_log,
            "compaction",
            "thread/read",
            {"turn_count": len(turns), "compaction_item_seen": compacted},
        )
        if compacted:
            break
        await asyncio.sleep(1)
    return {
        "requested": True,
        "signal_seen": compacted,
        "verification": "thread/read contextCompaction item",
    }


def test_passed(name: str, result: dict[str, Any], workspace: Path) -> bool:
    if name == "structured_terminal":
        parsed = result.get("parsed_response") or {}
        written_file = workspace / "agent-write-check.txt"
        return (
            result.get("status") == "completed"
            and parsed.get("status") == "ok"
            and parsed.get("command_used") is True
            and written_file.exists()
            and written_file.read_text(encoding="utf-8").strip() == "CODEX_SDK_POC_OK"
            and "commandExecution" in result.get("item_types", [])
        )
    if name == "web_search":
        parsed = result.get("parsed_response") or {}
        return (
            result.get("status") == "completed"
            and parsed.get("status") == "ok"
            and str(parsed.get("official_url", "")).startswith("http")
            and "webSearch" in result.get("item_types", [])
        )
    if name == "documents_vision":
        parsed = result.get("parsed_response") or {}
        return (
            result.get("status") == "completed"
            and parsed.get("status") == "ok"
            and "commandExecution" in result.get("item_types", [])
            and any(
                item in result.get("item_types", [])
                for item in ("imageView", "mcpToolCall")
            )
        )
    if name == "interrupt":
        return result.get("interrupt_requested") and result.get("status") == "interrupted"
    return False


async def main_async(args: argparse.Namespace) -> int:
    required = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise RuntimeError(f"POC root must be an empty dedicated directory: {root}")
    fixtures = prepare_fixtures(root, args.text_pdf, args.flow_pdf, args.docx)
    codex_home = root / "codex-home"
    workspace = root / "workspace"
    model = os.environ["OPENAI_MODEL"]
    base_url = normalize_base_url(os.environ["OPENAI_BASE_URL"])
    write_codex_config(codex_home, model, base_url)
    args.event_log.parent.mkdir(parents=True, exist_ok=True)
    args.event_log.write_text("", encoding="utf-8")

    child_env = os.environ.copy()
    child_env["CODEX_HOME"] = str(codex_home)
    child_env["OPENAI_BASE_URL"] = base_url
    config = CodexConfig(cwd=str(workspace), env=child_env)
    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sdk_version": "0.144.4",
        "runtime_isolated": str(codex_home).startswith(str(root)),
        "model": model,
        "base_url_host": base_url.split("//", 1)[-1].split("/", 1)[0],
        "wire_api": "responses",
        "auth_mode": "provider environment variable",
        "tests": {},
    }

    async with AsyncCodex(config) as codex:
        core_thread = await codex.thread_start(
            approval_mode=ApprovalMode.deny_all,
            cwd=str(workspace),
            model=model,
            model_provider="OpenAI",
            sandbox=Sandbox.full_access,
        )
        report["tests"]["structured_terminal"] = await run_streamed_turn(
            core_thread,
            "structured_terminal",
            "Use the shell to write exactly CODEX_SDK_POC_OK followed by a newline "
            "to agent-write-check.txt in the current workspace, then read it back. "
            "Return only the required JSON object.",
            args.event_log,
            STRUCTURED_SCHEMA,
        )

        web_thread = await codex.thread_start(
            approval_mode=ApprovalMode.deny_all,
            cwd=str(workspace),
            model=model,
            model_provider="OpenAI",
            sandbox=Sandbox.full_access,
        )
        report["tests"]["web_search"] = await run_streamed_turn(
            web_thread,
            "web_search",
            "Use the native Web Search tool to find the official Ministry of Ecology and "
            "Environment page for the current Construction Project Environmental Impact "
            "Assessment Classification Management Catalog. Do not use curl as a substitute "
            "for search. Return one official government URL and only the required JSON.",
            args.event_log,
            WEB_SCHEMA,
        )

        document_thread = await codex.thread_start(
            approval_mode=ApprovalMode.deny_all,
            cwd=str(workspace),
            model=model,
            model_provider="OpenAI",
            sandbox=Sandbox.full_access,
        )
        document_input = [
            TextInput(
                "Autonomously inspect these local files in the current workspace: "
                "technical_agreement.pdf (text PDF), process_flow_scan.pdf (image-only PDF), "
                "prompt_reference.docx (Office document), and process_flow_page.png. Use "
                "appropriate local tools, including OCR for the image-only PDF. The attached "
                "local image is the same process diagram and must be interpreted visually. "
                "Report concrete visible or extracted facts, and return only the required JSON."
            ),
            LocalImageInput(str(fixtures["image"])),
        ]
        report["tests"]["documents_vision"] = await run_streamed_turn(
            document_thread,
            "documents_vision",
            document_input,
            args.event_log,
            DOCUMENT_SCHEMA,
        )
        report["tests"]["compaction"] = await compact_thread(
            document_thread, args.event_log
        )

        interrupt_thread = await codex.thread_start(
            approval_mode=ApprovalMode.deny_all,
            cwd=str(workspace),
            model=model,
            model_provider="OpenAI",
            sandbox=Sandbox.full_access,
        )
        report["tests"]["interrupt"] = await run_streamed_turn(
            interrupt_thread,
            "interrupt",
            "Run the shell command sleep 30, wait for it to finish, then reply DONE.",
            args.event_log,
            interrupt_on_command=True,
        )

    for name in ("structured_terminal", "web_search", "documents_vision", "interrupt"):
        report["tests"][name]["passed"] = test_passed(
            name, report["tests"][name], workspace
        )
    report["tests"]["compaction"]["passed"] = bool(
        report["tests"]["compaction"].get("signal_seen")
    )
    report["no_approval_events"] = not any(
        result.get("approval_event_seen", False)
        for result in report["tests"].values()
        if isinstance(result, dict)
    )
    report["gate_a_passed"] = all(
        result.get("passed") is True for result in report["tests"].values()
    ) and report["no_approval_events"]
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["gate_a_passed"] else 2


def main() -> int:
    try:
        return asyncio.run(main_async(parse_args()))
    except Exception as exc:
        print(f"POC failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
