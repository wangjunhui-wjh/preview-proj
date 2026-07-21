#!/usr/bin/env python3
"""Exercise the Codex sidecar through the provider-neutral AgentClient API."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.agent_client import HttpAgentClient


SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok"]},
        "file_content": {"type": "string"},
        "shell_secrets_absent": {"type": "boolean"},
    },
    "required": ["status", "file_content", "shell_secrets_absent"],
    "additionalProperties": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18765")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    return parser.parse_args()


async def wait_for_ready(base_url: str) -> dict:
    deadline = time.monotonic() + 90
    async with httpx.AsyncClient(timeout=10) as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get(f"{base_url}/api/ready")
                if response.status_code == 200:
                    return response.json()
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    raise RuntimeError("Codex sidecar did not become ready")


async def collect_events(client: HttpAgentClient, run_id: str) -> list[dict]:
    events: list[dict] = []
    async for event in client.stream_run_events(run_id):
        events.append(event)
        if event.get("event") in {"run.completed", "run.failed", "run.cancelled"}:
            break
    return events


async def main_async(args: argparse.Namespace) -> int:
    health = await wait_for_ready(args.base_url)
    client = HttpAgentClient(args.base_url, api_key=args.api_key, request_timeout_seconds=180)

    async with httpx.AsyncClient(timeout=10) as raw_client:
        unauthorized = await raw_client.post(
            f"{args.base_url}/v1/runs",
            json={"input": "should be unauthorized", "session_id": "smoke"},
        )
    if unauthorized.status_code != 401:
        raise RuntimeError(f"Expected sidecar 401 without auth, got {unauthorized.status_code}")

    first = await client.create_run(
        "Use the shell to check whether OPENAI_API_KEY or CODEX_AGENT_API_KEY exists in "
        "the command environment. Write LEAK to env-check.txt if either exists, otherwise "
        "write CLEAN. Then write exactly CX02_AGENT_CLIENT_OK followed by a newline to "
        "contract-check.txt and read both files back. Return only the required JSON object; "
        "shell_secrets_absent must reflect env-check.txt.",
        instructions="This is an unattended smoke test. Use the available terminal autonomously.",
        session_id="smoke",
        output_schema=SCHEMA,
    )
    first_events = await collect_events(client, first["run_id"])
    first_record = await client.get_run(first["run_id"])
    first_output = first_record.get("structured") or {}
    workspace = Path(first_record["workspace"].replace("/opt/data", str(args.runtime_root), 1))
    contract_file = workspace / "contract-check.txt"
    env_check_file = workspace / "env-check.txt"
    first_passed = (
        first_record.get("status") == "completed"
        and first_output.get("status") == "ok"
        and "CX02_AGENT_CLIENT_OK" in str(first_output.get("file_content") or "")
        and first_output.get("shell_secrets_absent") is True
        and contract_file.read_text(encoding="utf-8").strip() == "CX02_AGENT_CLIENT_OK"
        and env_check_file.read_text(encoding="utf-8").strip() == "CLEAN"
        and any(event.get("event") == "tool.started" for event in first_events)
        and any(event.get("event") == "message.delta" for event in first_events)
        and any(event.get("event") == "run.completed" for event in first_events)
    )

    second = await client.create_run(
        "Run the shell command sleep 30 and only reply after it finishes.",
        session_id="smoke",
    )
    second_record = {}
    for _ in range(30):
        second_record = await client.get_run(second["run_id"])
        if second_record.get("turn_id"):
            break
        await asyncio.sleep(0.5)
    stop_response = await client.stop_run(second["run_id"])
    second_events = await collect_events(client, second["run_id"])
    second_record = await client.get_run(second["run_id"])
    interrupt_passed = (
        stop_response.get("stop_requested") is True
        and second_record.get("status") == "interrupted"
        and any(event.get("event") == "run.cancelled" for event in second_events)
    )

    result = {
        "health": health,
        "unauthorized_status": unauthorized.status_code,
        "structured_run": {
            "run_id": first["run_id"],
            "status": first_record.get("status"),
            "event_names": sorted({event.get("event") for event in first_events}),
            "passed": first_passed,
        },
        "interrupt_run": {
            "run_id": second["run_id"],
            "status": second_record.get("status"),
            "event_names": sorted({event.get("event") for event in second_events}),
            "passed": interrupt_passed,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if first_passed and interrupt_passed else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async(parse_args())))
