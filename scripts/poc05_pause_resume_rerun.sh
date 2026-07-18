#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${TMP_DIR:-$(mktemp -d)}"
FAKE_PORT="${FAKE_PORT:-18643}"
BACKEND_PORT="${BACKEND_PORT:-18502}"
LOG_DIR="$TMP_DIR/logs"
PYTHON="$ROOT_DIR/.venv/bin/python"
mkdir -p "$LOG_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

cd "$ROOT_DIR"

"$PYTHON" scripts/fake_hermes_server.py --port "$FAKE_PORT" --scenario slow --delay 0.15 > "$LOG_DIR/fake_hermes.log" 2>&1 &
FAKE_PID=$!
for _ in $(seq 1 80); do
  if curl -fsS "http://127.0.0.1:$FAKE_PORT/health" >/dev/null 2>&1; then break; fi
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
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; then break; fi
  sleep 0.1
done
curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-05 pause resume rerun fake task." > "$TMP_DIR/task.json"
TASK_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TMP_DIR/task.json")"

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/run" > "$TMP_DIR/run1.json"
sleep 0.25
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/pause" > "$TMP_DIR/pause.json"

for _ in $(seq 1 80); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status.json"
  STATUS="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/status.json")"
  [[ "$STATUS" == "paused" ]] && break
  sleep 0.1
done
[[ "$STATUS" == "paused" ]] || { echo "pause failed: $STATUS" >&2; cat "$TMP_DIR/status.json" >&2; exit 1; }

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/resume" > "$TMP_DIR/resume.json"
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/run" > "$TMP_DIR/run2.json"

for _ in $(seq 1 240); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status.json"
  STATUS="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/status.json")"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
  sleep 0.2
done
[[ "$STATUS" == "completed" ]] || { echo "resume/run failed: $STATUS" >&2; cat "$TMP_DIR/status.json" >&2; exit 1; }

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/rerun/HB-PT-003" > "$TMP_DIR/rerun.json"
"$PYTHON" - "$TMP_DIR/rerun.json" "$TMP_DIR/status.json" <<'PY'
import json
import sys

rerun = json.loads(open(sys.argv[1]).read())
expected_clear = ["HB-PT-003", "HB-PT-004", "HB-PT-005", "HB-PT-006", "HB-PT-007", "HB-PT-008", "HB-PT-009", "HB-PT-010", "HB-PT-011"]
if rerun.get("cleared_nodes") != expected_clear:
    raise SystemExit(f"unexpected cleared_nodes: {rerun.get('cleared_nodes')}")
PY

curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status_after_rerun.json"
curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/manifest" > "$TMP_DIR/manifest_after_rerun.json"
"$PYTHON" - "$TMP_DIR/status_after_rerun.json" "$TMP_DIR/manifest_after_rerun.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1]).read())
manifest = json.loads(open(sys.argv[2]).read())
mods = set(data.get("module_results", {}))
if data["status"] != "created" or data["next_node"] != "HB-PT-003":
    raise SystemExit(f"unexpected rerun state: {data['status']} next={data['next_node']}")
if not {"PREP-INGEST", "HB-PT-000", "HB-PT-001", "HB-PT-002"}.issubset(mods):
    raise SystemExit(f"upstream modules missing after rerun: {mods}")
if {"HB-PT-003", "HB-PT-004", "HB-PT-005", "HB-PT-006", "HB-PT-007", "HB-PT-008", "HB-PT-009", "HB-PT-010", "HB-PT-011"} & mods:
    raise SystemExit(f"downstream modules not cleared: {mods}")
checkpoint = manifest.get("graph_checkpoint") or {}
values = checkpoint.get("values") or {}
if values.get("status") != "created" or values.get("next_node") != "HB-PT-003":
    raise SystemExit(f"graph checkpoint not synced after rerun: {checkpoint}")
print(json.dumps({"task_id": data["task_id"], "status": data["status"], "next_node": data["next_node"], "remaining_modules": sorted(mods)}, ensure_ascii=False, indent=2))
PY

echo "POC-05 pause/resume/rerun passed with fake Hermes. tmp=$TMP_DIR"
