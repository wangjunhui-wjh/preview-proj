#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${TMP_DIR:-$(mktemp -d)}"
FAKE_PORT="${FAKE_PORT:-18645}"
BACKEND_PORT="${BACKEND_PORT:-18504}"
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

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks" \
  -F "project_text=POC-08 export smoke task. 拟建水性涂料项目，要求完成报告导出和归档验收。" \
  > "$TMP_DIR/task.json"
TASK_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$TMP_DIR/task.json")"

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/run" > "$TMP_DIR/run.json"
STATUS="running"
for _ in $(seq 1 200); do
  curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID" > "$TMP_DIR/status.json"
  STATUS="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$TMP_DIR/status.json")"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "paused" ]]; then break; fi
  sleep 0.2
done
[[ "$STATUS" == "completed" ]] || { echo "Expected completed, got $STATUS" >&2; cat "$TMP_DIR/status.json" >&2; exit 1; }

curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/report.md" > "$TMP_DIR/report.md"
grep -q "环评前期研判报告" "$TMP_DIR/report.md"
grep -q "综合研判结论" "$TMP_DIR/report.md"
grep -q "交叉一致性核查" "$TMP_DIR/report.md"

curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/tasks/$TASK_ID/export.zip" > "$TMP_DIR/export.zip"
"$PYTHON" - "$TMP_DIR/export.zip" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    names = set(archive.namelist())
required = {
    "manifest.json",
    "report.md",
    "state.json",
    "logs/events.jsonl",
    "outputs/PREP-INGEST.md",
    "outputs/HB-PT-010.md",
    "outputs/HB-PT-011.md",
}
missing = sorted(required - names)
if missing:
    raise SystemExit(f"missing archive entries: {missing}")
print("archive entries ok")
PY

curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/api/knowledge/documents/batch-review" \
  -H "Content-Type: application/json" \
  -d '{"doc_ids":["missing-doc-for-poc08-smoke"],"status":"verified_candidate","validity":"unknown","reviewer":"smoke"}' \
  > "$TMP_DIR/batch_review.json"
"$PYTHON" - "$TMP_DIR/batch_review.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
if data.get("documents") != [] or not data.get("errors"):
    raise SystemExit(f"unexpected batch review response: {data}")
print("batch review route ok")
PY

echo "POC-08 export smoke passed. task_id=$TASK_ID tmp=$TMP_DIR"
