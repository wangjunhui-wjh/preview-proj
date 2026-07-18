#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def _tail_jsonl(path: Path, limit: int = 12) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"raw": line})
    return out


def _task_rows(root: Path) -> list[dict]:
    rows = []
    for path in sorted((root / "data" / "tasks").glob("*/state.json")):
        data = _read_json(path)
        if data.get("_read_error"):
            rows.append(
                {
                    "task_id": path.parent.name,
                    "status": "unreadable",
                    "current_node": None,
                    "next_node": None,
                    "modules": [],
                    "knowledge_doc_ids": [],
                    "candidate_doc_ids": [],
                    "error": data["_read_error"],
                }
            )
            continue
        rows.append(
            {
                "task_id": data.get("task_id"),
                "status": data.get("status"),
                "current_node": data.get("current_node"),
                "next_node": data.get("next_node"),
                "modules": sorted((data.get("module_results") or {}).keys()),
                "knowledge_doc_ids": data.get("knowledge_doc_ids") or [],
                "candidate_doc_ids": data.get("candidate_doc_ids") or [],
            }
        )
    return rows


def _knowledge_counts(root: Path) -> list[tuple[str, int]]:
    db_path = root / "data" / "app.db"
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            return list(conn.execute("select status, count(*) from knowledge_documents group by status order by status"))
    except sqlite3.Error as exc:
        return [("error:" + str(exc), 0)]


def _checkpoint_summary(root: Path) -> dict:
    db_path = root / "data" / "langgraph_checkpoints.sqlite"
    if not db_path.exists():
        return {"exists": False}
    summary = {"exists": True, "path": str(db_path.relative_to(root)), "size": db_path.stat().st_size, "tables": {}}
    try:
        with sqlite3.connect(db_path) as conn:
            tables = [row[0] for row in conn.execute("select name from sqlite_master where type='table' order by name")]
            for table in tables:
                quoted = '"' + table.replace('"', '""') + '"'
                summary["tables"][table] = conn.execute(f"select count(*) from {quoted}").fetchone()[0]
    except sqlite3.Error as exc:
        summary["error"] = str(exc)
    return summary


def _recent_files(root: Path, rel: str, limit: int = 20) -> list[str]:
    base = root / rel
    if not base.exists():
        return []
    files = [path for path in base.rglob("*") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [str(path.relative_to(root)) for path in files[:limit]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--task-id", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    progress = root / ".state" / "progress.md"
    print("# Recovery Snapshot\n")
    print(f"- root: `{root}`")
    if progress.exists():
        print("- progress: present")
        print("\n## Progress Head\n")
        print("\n".join(progress.read_text(encoding="utf-8", errors="ignore").splitlines()[:45]))
    else:
        print("- progress: missing")

    rows = _task_rows(root)
    print("\n## Tasks\n")
    for row in rows:
        print(
            f"- `{row['task_id']}` status={row['status']} current={row['current_node']} "
            f"next={row['next_node']} modules={','.join(row['modules']) or '-'} "
            f"knowledge={len(row['knowledge_doc_ids'])} candidates={len(row['candidate_doc_ids'])}"
        )
        if row.get("error"):
            print(f"  error={row['error']}")

    if args.task_id:
        task_path = root / "data" / "tasks" / args.task_id / "state.json"
        event_path = root / "logs" / f"task_{args.task_id}.events.jsonl"
        print(f"\n## Task Detail `{args.task_id}`\n")
        if task_path.exists():
            data = _read_json(task_path)
            if data.get("_read_error"):
                print(f"- error: `{data['_read_error']}`")
                data = {}
            print(f"- status: `{data.get('status')}`")
            print(f"- current_node: `{data.get('current_node')}`")
            print(f"- next_node: `{data.get('next_node')}`")
            print(f"- active_hermes_run_id: `{data.get('active_hermes_run_id')}`")
            print(f"- error: `{data.get('error')}`")
            print(f"- modules: `{', '.join(sorted((data.get('module_results') or {}).keys()))}`")
        print("\n### Recent Events\n")
        for event in _tail_jsonl(event_path):
            print(f"- {event.get('created_at', '')} `{event.get('type', 'raw')}` {event.get('node_id') or ''} {event.get('message') or event.get('raw', '')}")

    print("\n## Knowledge Counts\n")
    for status, count in _knowledge_counts(root):
        print(f"- {status}: {count}")

    print("\n## LangGraph Checkpoint\n")
    checkpoint = _checkpoint_summary(root)
    if not checkpoint.get("exists"):
        print("- missing")
    else:
        print(f"- path: `{checkpoint['path']}`")
        print(f"- size: `{checkpoint['size']}`")
        if checkpoint.get("error"):
            print(f"- error: `{checkpoint['error']}`")
        for table, count in checkpoint.get("tables", {}).items():
            print(f"- {table}: {count}")

    print("\n## Recent Logs\n")
    for item in _recent_files(root, "logs"):
        print(f"- `{item}`")

    print("\n## Recent Outputs\n")
    for item in _recent_files(root, "outputs"):
        print(f"- `{item}`")

    print("\n## Next Step\n")
    print("- Read `.state/progress.md`, then continue from `next_step`.")
    print("- If any task is `running` after process restart, call `POST /api/admin/recover-running-tasks` before continuing.")


if __name__ == "__main__":
    main()
