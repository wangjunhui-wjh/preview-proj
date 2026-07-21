#!/usr/bin/env python3
"""Run real-data representative-node checks against an isolated Codex sidecar."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--nodes", default="PREP-INGEST,HB-PT-002,HB-PT-009")
    return parser.parse_args()


def fixture_files(fixture_dir: Path):
    from backend.models import FileRef

    refs = []
    for path in sorted(fixture_dir.glob("*")):
        if not path.is_file():
            continue
        refs.append(
            FileRef(
                id=str(uuid.uuid4()),
                name=path.name,
                path=str(path),
                size=path.stat().st_size,
                content_type="application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream",
                sha256=sha256(path),
            )
        )
    return refs


async def run(args: argparse.Namespace) -> None:
    from backend import main
    from backend.models import EiaTaskState, NodeResult
    from backend.task_store import task_store

    nodes = [item.strip() for item in args.nodes.split(",") if item.strip()]
    if args.attempts < 1:
        raise ValueError("attempts must be positive")
    refs = fixture_files(args.fixture_dir)
    if not refs:
        raise ValueError(f"No fixture files in {args.fixture_dir}")
    results = []
    for node_id in nodes:
        for attempt in range(1, args.attempts + 1):
            task_id = f"cx03-{node_id.lower()}-{attempt}-{uuid.uuid4().hex[:8]}"
            task = EiaTaskState(
                task_id=task_id,
                next_node=node_id,
                project_text=(
                    "项目为 EPS 成套挤出装备相关项目。以下仅为用户输入的样例项目材料，"
                    "请以上传文件读取结果为准，未知信息不得补全。"
                ),
                project_files=refs,
            )
            if node_id == "HB-PT-002":
                task.module_results["HB-PT-001"] = NodeResult(
                    node_id="HB-PT-001",
                    status="completed",
                    markdown="项目概况：EPS 成套挤出装备，建设地点和产能以原始资料为准。",
                    structured={"project_profile": {"product": "EPS 成套挤出装备", "source": "uploaded_files"}},
                )
            elif node_id == "HB-PT-009":
                task.module_results["HB-PT-001"] = NodeResult(
                    node_id="HB-PT-001",
                    status="completed",
                    markdown="项目概况：EPS 成套挤出装备，工艺和污染信息以原始资料为准。",
                    structured={"project_profile": {"product": "EPS 成套挤出装备", "source": "uploaded_files"}},
                )
                task.module_results["HB-PT-002"] = NodeResult(
                    node_id="HB-PT-002",
                    status="completed",
                    markdown="行业类别、环评类别和审批路径需结合真实项目事实和官方依据复核。",
                    structured={"status": "needs_review"},
                )
            task_store.create(task)
            result = await main._run_node(task, node_id)
            saved = task_store.get(task_id)
            events = list(main.event_store.iter_events(task_id))
            event_types = [event.type for event in events]
            url_count = sum(len(ref.source_url or "") > 0 for ref in result.evidence_refs)
            tool_types = [str(item.get("tool") or item.get("summary", {}).get("type") or "") for item in result.tool_trace]
            item = {
                "node_id": node_id,
                "attempt": attempt,
                "task_id": task_id,
                "status": result.status,
                "task_status": saved.status,
                "next_node": saved.next_node,
                "error": result.error,
                "markdown_chars": len(result.markdown),
                "structured_keys": sorted(result.structured.keys()),
                "evidence_url_count": url_count,
                "tool_types": tool_types,
                "required_events": {name: name in event_types for name in ("agent_call_start", "tool_event", "node_complete")},
            }
            results.append(item)
            if result.status != "completed":
                raise RuntimeError(json.dumps(item, ensure_ascii=False))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "provider": main.settings.agent_provider,
                "attempts": args.attempts,
                "nodes": nodes,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"passed": len(results), "report": str(args.report)}, ensure_ascii=False))


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(run(arguments))
