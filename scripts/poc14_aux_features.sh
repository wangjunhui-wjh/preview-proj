#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${TMP_DIR:-$(mktemp -d)}"
FAKE_PORT="${FAKE_PORT:-18646}"
BACKEND_PORT="${BACKEND_PORT:-18505}"
LOG_DIR="$TMP_DIR/logs"
PYTHON="$ROOT_DIR/.venv/bin/python"
mkdir -p "$LOG_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

cd "$ROOT_DIR"

"$PYTHON" scripts/fake_hermes_server.py --port "$FAKE_PORT" --scenario full --delay 0.01 > "$LOG_DIR/fake_hermes.log" 2>&1 &
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

PROJECT_FILE="$TMP_DIR/fake-project.txt"
printf 'POC-14 fake project file. 建设水性涂料项目，位于示范工业园，年产1000吨。' > "$PROJECT_FILE"

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-14 auxiliary feature task. 拟建水性涂料项目。" \
  -F "files=@$PROJECT_FILE;filename=fake-project.txt;type=text/plain" \
  > "$TMP_DIR/task.json"
TASK_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TMP_DIR/task.json")"

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/validate-files" > "$TMP_DIR/validate.json"
"$PYTHON" - "$TMP_DIR/validate.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
if data.get("node_id") != "FILE-VALIDATION" or data.get("status") != "completed":
    raise SystemExit(f"unexpected validation result: {data}")
if not data.get("structured", {}).get("files"):
    raise SystemExit(f"missing structured file validation: {data}")
print("file validation ok")
PY

for expected_next in PREP-INGEST HB-PT-000 HB-PT-001; do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status.json"
  NEXT="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["next_node"])' "$TMP_DIR/status.json")"
  [[ "$NEXT" == "$expected_next" ]] || { echo "expected next $expected_next got $NEXT" >&2; cat "$TMP_DIR/status.json" >&2; exit 1; }
  curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/step" > "$TMP_DIR/step_$expected_next.json"
done

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/run-until" \
  -H "Content-Type: application/json" \
  -d '{"stop_after_node":"HB-PT-009"}' \
  > "$TMP_DIR/run_until.json"

STATUS="running"
for _ in $(seq 1 160); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status.json"
  STATUS="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/status.json")"
  [[ "$STATUS" == "paused" || "$STATUS" == "failed" || "$STATUS" == "completed" ]] && break
  sleep 0.1
done
[[ "$STATUS" == "paused" ]] || { echo "run-until expected paused, got $STATUS" >&2; cat "$TMP_DIR/status.json" >&2; exit 1; }

"$PYTHON" - "$TMP_DIR/status.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
mods = data.get("module_results", {})
expected = ["HB-PT-002", "HB-PT-003", "HB-PT-004", "HB-PT-005", "HB-PT-006", "HB-PT-007", "HB-PT-008", "HB-PT-009"]
missing = [node for node in expected if node not in mods]
if missing or data.get("next_node") != "HB-PT-010":
    raise SystemExit(f"unexpected run-until state: missing={missing} next={data.get('next_node')}")
print("run-until ok")
PY

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/search" \
  -H "Content-Type: application/json" \
  -d "{\"task_id\":\"$TASK_ID\",\"query\":\"水性涂料项目环评类别官方依据\",\"purpose\":\"poc14\"}" \
  > "$TMP_DIR/search.json"
"$PYTHON" - "$TMP_DIR/search.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
if data.get("result", {}).get("node_id") != "WEB-SEARCH":
    raise SystemExit(f"unexpected search result: {data}")
if not data.get("documents"):
    raise SystemExit(f"search did not create candidate docs: {data}")
print("search ok")
PY

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/feedback/HB-PT-002" \
  -H "Content-Type: application/json" \
  -d '{"feedback":"行业类别应结合水性涂料制造重新核对，修正后请清理下游结论。","action":"revise"}' \
  > "$TMP_DIR/feedback.json"

curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status_after_feedback.json"
"$PYTHON" - "$TMP_DIR/status_after_feedback.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
mods = set(data.get("module_results", {}))
if data.get("next_node") != "HB-PT-003" or data.get("status") != "created":
    raise SystemExit(f"feedback did not reset downstream route: {data.get('status')} next={data.get('next_node')}")
if "HB-PT-002" not in mods:
    raise SystemExit("revised node missing")
if {"HB-PT-003", "HB-PT-004", "HB-PT-005", "HB-PT-006", "HB-PT-007", "HB-PT-008", "HB-PT-009"} & mods:
    raise SystemExit(f"downstream nodes were not cleared: {sorted(mods)}")
print("feedback ok")
PY

echo "POC-14 auxiliary feature smoke passed. task_id=$TASK_ID tmp=$TMP_DIR"
