#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${TMP_DIR:-$(mktemp -d)}"
FAKE_PORT="${FAKE_PORT:-18644}"
BACKEND_PORT="${BACKEND_PORT:-18503}"
LOG_DIR="$TMP_DIR/logs"
PYTHON="$ROOT_DIR/.venv/bin/python"
mkdir -p "$LOG_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

cd "$ROOT_DIR"

"$PYTHON" scripts/fake_hermes_server.py \
  --port "$FAKE_PORT" \
  --scenario completed_open \
  --delay 0.01 \
  --create-delay 0.8 \
  > "$LOG_DIR/fake_hermes.log" 2>&1 &
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

# run.completed must terminate the backend node even if the SSE connection stays open.
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-06 completed-open edge task." > "$TMP_DIR/completed_task.json"
COMPLETED_TASK_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TMP_DIR/completed_task.json")"
timeout 8 curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$COMPLETED_TASK_ID/step" > "$TMP_DIR/completed_step.json"
"$PYTHON" - "$TMP_DIR/completed_step.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1]).read())
if data["status"] != "paused" or data["next_node"] != "HB-PT-000":
    raise SystemExit(f"step did not finish after run.completed: {data}")
if not data.get("result") or data["result"].get("status") != "completed":
    raise SystemExit(f"missing completed result: {data}")
PY

# A terminal completed task must not be moved back to paused/created by pause/resume.
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-06 terminal pause edge task." > "$TMP_DIR/terminal_task.json"
TERMINAL_TASK_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TMP_DIR/terminal_task.json")"
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TERMINAL_TASK_ID/run" > "$TMP_DIR/terminal_run.json"
for _ in $(seq 1 160); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TERMINAL_TASK_ID" > "$TMP_DIR/terminal_status.json"
  STATUS="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/terminal_status.json")"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
  sleep 0.1
done
[[ "$STATUS" == "completed" ]] || { echo "terminal run failed: $STATUS" >&2; cat "$TMP_DIR/terminal_status.json" >&2; exit 1; }
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TERMINAL_TASK_ID/pause" > "$TMP_DIR/terminal_pause.json"
"$PYTHON" - "$TMP_DIR/terminal_pause.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1]).read())
if data["status"] != "completed" or not data.get("ignored"):
    raise SystemExit(f"terminal pause was not ignored: {data}")
PY

# Pause while create_run is delayed. Backend must preserve pause_requested and stop the run once run_id appears.
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-06 pause race edge task." > "$TMP_DIR/pause_race_task.json"
PAUSE_TASK_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TMP_DIR/pause_race_task.json")"
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$PAUSE_TASK_ID/run" > "$TMP_DIR/pause_race_run.json"
sleep 0.2
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$PAUSE_TASK_ID/pause" > "$TMP_DIR/pause_race_pause.json"
for _ in $(seq 1 120); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$PAUSE_TASK_ID" > "$TMP_DIR/pause_race_status.json"
  STATUS="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/pause_race_status.json")"
  [[ "$STATUS" == "paused" || "$STATUS" == "failed" ]] && break
  sleep 0.1
done
"$PYTHON" - "$TMP_DIR/pause_race_status.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1]).read())
if data["status"] != "paused" or data["next_node"] != "PREP-INGEST":
    raise SystemExit(f"pause race did not pause at current node: {data}")
if data.get("active_hermes_run_id") is not None:
    raise SystemExit(f"active run not cleared: {data.get('active_hermes_run_id')}")
if "PREP-INGEST" in data.get("module_results", {}):
    raise SystemExit("paused node leaked into module_results")
PY

# Rerun from a paused task must clear pause_requested and allow the node to run.
curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$PAUSE_TASK_ID/rerun/PREP-INGEST" > "$TMP_DIR/pause_race_rerun.json"
curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$PAUSE_TASK_ID/manifest" > "$TMP_DIR/pause_race_manifest_after_rerun.json"
"$PYTHON" - "$TMP_DIR/pause_race_manifest_after_rerun.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1]).read())
task = data["task"]
checkpoint = data.get("graph_checkpoint") or {}
values = checkpoint.get("values") or {}
if task["pause_requested"] or values.get("pause_requested"):
    raise SystemExit(f"pause flag not cleared by rerun: {data}")
if task["status"] != "created" or task["next_node"] != "PREP-INGEST":
    raise SystemExit(f"unexpected rerun task state: {task}")
PY
timeout 8 curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$PAUSE_TASK_ID/step" > "$TMP_DIR/pause_race_step.json"
"$PYTHON" - "$TMP_DIR/pause_race_step.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1]).read())
if data["status"] != "paused" or data["next_node"] != "HB-PT-000":
    raise SystemExit(f"step after rerun did not advance: {data}")
PY

echo "POC-06 edge cases passed with fake Hermes. tmp=$TMP_DIR"
