#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


RUNS: dict[str, dict[str, Any]] = {}
SCENARIO = "full"
DELAY = 0.02
CREATE_DELAY = 0.0
AFTER_COMPLETED_SLEEP = 0.0


def _node_from_input(text: str) -> str:
    match = re.search(r"节点：\s*(PREP-INGEST|HB-PT-\d{3}(?:-FEEDBACK)?|FILE-VALIDATION|WEB-SEARCH)", text)
    return match.group(1) if match else "HB-PT-000"


def _node_output(node_id: str, port: int) -> str:
    url_line = ""
    extra: dict[str, Any] = {}
    if node_id == "HB-PT-003":
        policy_url = f"http://127.0.0.1:{port}/policy/sample.html"
        url_line = f"\n\n依据URL：{policy_url}"
        extra = {"url": policy_url, "policy": "fake policy"}
    elif node_id == "WEB-SEARCH":
        policy_url = f"http://127.0.0.1:{port}/policy/sample.html"
        url_line = f"\n\n候选依据URL：{policy_url}"
        extra = {
            "query": "fake web search query",
            "results": [
                {
                    "title": "Fake Policy",
                    "url": policy_url,
                    "source": "fake-hermes",
                    "snippet": "低 VOCs 环境友好型涂料属于鼓励类。",
                    "relevance": "high",
                    "suggested_use": "产业政策符合性核验",
                    "needs_review": True,
                }
            ],
        }
    payload = {
        "node": node_id,
        "status": "completed",
        "summary": f"fake Hermes result for {node_id}",
        **extra,
    }
    if node_id == "PREP-INGEST":
        payload["project_dossier"] = {
            "basic_info": {"project_name": "POC fake project", "source": "project_text"},
            "source_index": [{"source": "project_text", "confidence": "high"}],
        }
    if node_id == "FILE-VALIDATION":
        payload["overall_status"] = "可用于初判但需补充核实"
        payload["files"] = [
            {
                "file_name": "fake-project.txt",
                "readability": "可读",
                "relevance": "与本项目相关",
                "usable_for_modules": ["PREP-INGEST", "HB-PT-000", "HB-PT-001"],
                "validity_status": "不适用",
                "risk_level": "低",
                "recommendation": "可用于项目资料读取",
            }
        ]
        payload["manual_review_items"] = ["核实建设地点和产能"]
    if node_id.endswith("-FEEDBACK"):
        payload["feedback_accepted"] = "部分采纳"
        payload["changed_items"] = [{"item": "fake item", "before": "old", "after": "new", "basis": "feedback"}]
        payload["affected_downstream_nodes"] = ["HB-PT-003"]
    return (
        f"# {node_id} Fake Result\n\n"
        f"该节点由 fake Hermes 生成，用于离线验收。{url_line}\n\n"
        "BEGIN_NODE_RESULT_JSON\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
        "END_NODE_RESULT_JSON"
    )


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_sse(handler: BaseHTTPRequestHandler, payload: dict[str, Any]) -> None:
    body = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
    handler.wfile.write(body)
    handler.wfile.flush()


class FakeHermesHandler(BaseHTTPRequestHandler):
    server_version = "FakeHermes/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return _write_json(self, 200, {"status": "ok", "platform": "fake-hermes", "version": "0.1"})
        if parsed.path == "/policy/sample.html":
            body = (
                "<html><head><title>Fake Policy</title></head><body>"
                "<h1>Fake Policy</h1><p>低 VOCs 环境友好型涂料属于鼓励类。</p>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        match = re.fullmatch(r"/v1/runs/([^/]+)/events", parsed.path)
        if match:
            return self._events(match.group(1))
        match = re.fullmatch(r"/v1/runs/([^/]+)", parsed.path)
        if match:
            run = RUNS.get(match.group(1))
            if not run:
                return _write_json(self, 404, {"error": "run not found"})
            return _write_json(
                self,
                200,
                {
                    "run_id": run["run_id"],
                    "status": run.get("status", "completed"),
                    "output": run.get("output", ""),
                    "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                },
            )
        return _write_json(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/v1/runs":
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body or "{}")
            node_id = _node_from_input(str(payload.get("input") or ""))
            run_id = f"fake_{uuid.uuid4().hex[:12]}"
            RUNS[run_id] = {
                "run_id": run_id,
                "node_id": node_id,
                "status": "running",
                "output": "",
                "stopped": False,
            }
            if CREATE_DELAY:
                time.sleep(CREATE_DELAY)
            return _write_json(self, 200, {"run_id": run_id, "status": "queued"})
        match = re.fullmatch(r"/v1/runs/([^/]+)/stop", parsed.path)
        if match:
            run = RUNS.get(match.group(1))
            if run:
                run["stopped"] = True
                run["status"] = "stopping"
            return _write_json(self, 200, {"run_id": match.group(1), "status": "stopping"})
        return _write_json(self, 404, {"error": "not found"})

    def _events(self, run_id: str) -> None:
        run = RUNS.get(run_id)
        if not run:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        node_id = run["node_id"]
        port = self.server.server_address[1]
        events = [
            {"event": "tool.started", "run_id": run_id, "tool": "fake_tool", "preview": node_id},
            {"event": "tool.completed", "run_id": run_id, "tool": "fake_tool", "duration": DELAY, "error": False},
        ]
        output = _node_output(node_id, port)
        if SCENARIO == "approval" and node_id == "HB-PT-003":
            events.append({"event": "approval.request", "run_id": run_id, "command": "fake approval"})
        elif SCENARIO == "fail" and node_id == "HB-PT-003":
            events.append({"event": "run.failed", "run_id": run_id, "error": "fake failure"})
        else:
            events.extend(
                [
                    {"event": "message.delta", "run_id": run_id, "delta": output[: len(output) // 2]},
                    {"event": "message.delta", "run_id": run_id, "delta": output[len(output) // 2 :]},
                    {
                        "event": "run.completed",
                        "run_id": run_id,
                        "output": output,
                        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    },
                ]
            )
        for event in events:
            if run.get("stopped"):
                run["status"] = "cancelled"
                _send_sse(self, {"event": "run.cancelled", "run_id": run_id})
                return
            _send_sse(self, event)
            time.sleep(DELAY)
        if AFTER_COMPLETED_SLEEP and not run.get("stopped"):
            time.sleep(AFTER_COMPLETED_SLEEP)
        run["status"] = "completed"
        run["output"] = output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18642)
    parser.add_argument("--scenario", default="full", choices=["full", "slow", "fail", "approval", "completed_open"])
    parser.add_argument("--delay", type=float, default=None)
    parser.add_argument("--create-delay", type=float, default=0.0)
    args = parser.parse_args()

    global SCENARIO, DELAY, CREATE_DELAY, AFTER_COMPLETED_SLEEP
    SCENARIO = args.scenario
    DELAY = args.delay if args.delay is not None else (0.2 if args.scenario == "slow" else 0.02)
    CREATE_DELAY = args.create_delay
    AFTER_COMPLETED_SLEEP = 30.0 if args.scenario == "completed_open" else 0.0
    server = ThreadingHTTPServer((args.host, args.port), FakeHermesHandler)
    print(f"fake hermes listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
