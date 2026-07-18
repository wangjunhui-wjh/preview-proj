#!/usr/bin/env sh
set -eu

yaml_quote() {
  printf "'%s'" "$(printf "%s" "$1" | sed "s/'/''/g")"
}

mkdir -p /opt/data /app/data /app/logs /app/outputs

api_key="${HERMES_API_SERVER_KEY:-${API_SERVER_KEY:-}}"
if [ -z "$api_key" ]; then
  api_key="change-me"
fi

provider="${LLM_PROVIDER:-custom}"
model="${LLM_MODEL:-${OPENAI_MODEL:-gpt-5.5}}"
base_url="${LLM_BASE_URL:-}"
if [ -z "$base_url" ] && [ "$provider" = "custom" ]; then
  base_url="${OPENAI_BASE_URL:-${CUSTOM_BASE_URL:-}}"
fi

cat > /opt/data/.env <<EOF
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8642
API_SERVER_MODEL_NAME=hermes-agent
API_SERVER_KEY=${api_key}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_BASE_URL=${OPENAI_BASE_URL:-}
CUSTOM_BASE_URL=${OPENAI_BASE_URL:-${CUSTOM_BASE_URL:-}}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
EXA_API_KEY=${EXA_API_KEY:-}
PARALLEL_API_KEY=${PARALLEL_API_KEY:-}
EOF
chmod 600 /opt/data/.env || true

q_provider="$(yaml_quote "$provider")"
q_model="$(yaml_quote "$model")"
q_base_url="$(yaml_quote "$base_url")"
q_web_backend="$(yaml_quote "${HERMES_WEB_BACKEND:-ddgs}")"
q_web_search_backend="$(yaml_quote "${HERMES_WEB_SEARCH_BACKEND:-ddgs}")"

cat > /opt/data/config.yaml <<EOF
model:
  default: ${q_model}
  provider: ${q_provider}
  base_url: ${q_base_url}
agent:
  max_turns: ${HERMES_MAX_TURNS:-60}
  verbose: false
  reasoning_effort: ${HERMES_REASONING_EFFORT:-xhigh}
terminal:
  backend: local
  cwd: /app
  timeout: ${HERMES_TERMINAL_TIMEOUT:-180}
web:
  backend: ${q_web_backend}
  search_backend: ${q_web_search_backend}
browser:
  inactivity_timeout: 120
tool_loop_guardrails:
  warnings_enabled: true
  hard_stop_enabled: false
  warn_after:
    exact_failure: 2
    same_tool_failure: 3
    idempotent_no_progress: 2
  hard_stop_after:
    exact_failure: 5
    same_tool_failure: 8
    idempotent_no_progress: 5
compression:
  enabled: true
  threshold: 0.5
  target_ratio: 0.2
  protect_last_n: 20
  protect_first_n: 3
prompt_caching:
  cache_ttl: 5m
EOF

hermes tools enable --platform api_server web file terminal skills >/dev/null 2>&1 || true

exec hermes gateway run --replace -v
