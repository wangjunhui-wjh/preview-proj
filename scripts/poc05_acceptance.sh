#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${TMP_DIR:-$(mktemp -d)}"
FAKE_PORT="${FAKE_PORT:-18642}"
BACKEND_PORT="${BACKEND_PORT:-18501}"
LOG_DIR="$TMP_DIR/logs"
mkdir -p "$LOG_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

cd "$ROOT_DIR"

PYTHON="$ROOT_DIR/.venv/bin/python"

"$PYTHON" scripts/fake_hermes_server.py --port "$FAKE_PORT" --scenario full --delay 0.01 > "$LOG_DIR/fake_hermes.log" 2>&1 &
FAKE_PID=$!

for _ in $(seq 1 80); do
  if curl -fsS "http://127.0.0.1:$FAKE_PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done
curl -fsS "http://127.0.0.1:$FAKE_PORT/health" >/dev/null

HERMES_BASE_URL="http://127.0.0.1:$FAKE_PORT" \
HERMES_API_KEY="fake-key" \
UPLOAD_DIR="$TMP_DIR/uploads" \
LANGGRAPH_CHECKPOINT_DIR="$TMP_DIR/tasks" \
LANGGRAPH_CHECKPOINT_DB="$TMP_DIR/langgraph_checkpoints.sqlite" \
TASK_WORKSPACE_DIR="$TMP_DIR/workspaces" \
OUTPUT_DIR="$TMP_DIR/outputs" \
LOG_DIR="$TMP_DIR/logs" \
KNOWLEDGE_DIR="$TMP_DIR/knowledge" \
DATABASE_URL="sqlite:///$TMP_DIR/app.db" \
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port "$BACKEND_PORT" > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

for _ in $(seq 1 80); do
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done
curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null

TASK_JSON="$TMP_DIR/task.json"
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-05 fake Hermes 全流程验收项目。拟建水性涂料项目，要求完成全部已接入节点。" \
  > "$TASK_JSON"
TASK_ID="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TASK_JSON")"

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/run" > "$TMP_DIR/run.json"

STATUS="running"
for _ in $(seq 1 200); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status.json"
  STATUS="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/status.json")"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "paused" ]]; then
    break
  fi
  sleep 0.2
done

if [[ "$STATUS" != "completed" ]]; then
  echo "Expected completed, got $STATUS" >&2
  cat "$TMP_DIR/status.json" >&2
  exit 1
fi

curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/manifest" > "$TMP_DIR/manifest.json"

.venv/bin/python - "$TMP_DIR/status.json" "$TMP_DIR/outputs/$TASK_ID" "$TMP_DIR/manifest.json" <<'PY'
import json
import pathlib
import sys

status_path = pathlib.Path(sys.argv[1])
output_dir = pathlib.Path(sys.argv[2])
manifest_path = pathlib.Path(sys.argv[3])
data = json.loads(status_path.read_text())
manifest = json.loads(manifest_path.read_text())
expected = [
    "PREP-INGEST",
    "HB-PT-000",
    "HB-PT-001",
    "HB-PT-002",
    "HB-PT-003",
    "HB-PT-004",
    "HB-PT-005",
    "HB-PT-006",
    "HB-PT-007",
    "HB-PT-008",
    "HB-PT-009",
    "HB-PT-010",
    "HB-PT-011",
]
missing = [node for node in expected if node not in data.get("module_results", {})]
if missing:
    raise SystemExit(f"missing module_results: {missing}")
missing_files = []
for node in expected:
    for suffix in (".md", ".json", ".tool_trace.json", ".evidence_refs.json"):
        path = output_dir / f"{node}{suffix}"
        if not path.exists():
            missing_files.append(str(path))
if missing_files:
    raise SystemExit("missing output files:\n" + "\n".join(missing_files))
events = [event["type"] for event in data.get("events", [])]
for required in ("task_run_started", "node_start", "node_complete", "task_completed"):
    if required not in events:
        raise SystemExit(f"missing event type: {required}")
checkpoint = manifest.get("graph_checkpoint") or {}
if not checkpoint.get("exists"):
    raise SystemExit(f"missing graph checkpoint in manifest: {checkpoint}")
print(json.dumps({
    "task_id": data["task_id"],
    "status": data["status"],
    "nodes": expected,
    "output_dir": str(output_dir),
    "checkpoint_next": checkpoint.get("next", []),
}, ensure_ascii=False, indent=2))
PY

echo "POC-05 acceptance passed with fake Hermes. tmp=$TMP_DIR"
