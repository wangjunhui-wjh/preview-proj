#!/command/with-contenv sh
set -eu

yaml_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/''/g")"
}

require_value() {
  name="$1"
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    echo "[eia-config] ERROR: $name is required" >&2
    exit 1
  fi
}

hermes_home="${HERMES_HOME:-/opt/data}"
api_key="${HERMES_API_SERVER_KEY:-${API_SERVER_KEY:-}}"
model="${OPENAI_MODEL:-}"
base_url="${OPENAI_BASE_URL:-}"
terminal_backend="${HERMES_TERMINAL_BACKEND:-local}"

terminal_cwd="${HERMES_TERMINAL_CWD:-}"
if [ -z "$terminal_cwd" ]; then
  if [ "$terminal_backend" = "local" ]; then
    terminal_cwd="$hermes_home/workspace"
  else
    terminal_cwd="/workspace"
  fi
fi

if [ "${#api_key}" -lt 16 ]; then
  echo "[eia-config] ERROR: HERMES_API_SERVER_KEY must contain at least 16 characters" >&2
  exit 1
fi
if [ -z "$model" ]; then
  echo "[eia-config] ERROR: OPENAI_MODEL is required" >&2
  exit 1
fi
require_value OPENAI_API_KEY
if [ -z "$base_url" ]; then
  echo "[eia-config] ERROR: OPENAI_BASE_URL is required" >&2
  exit 1
fi
case "$terminal_backend" in
  local|docker) ;;
  *)
    echo "[eia-config] ERROR: HERMES_TERMINAL_BACKEND must be local or docker" >&2
    exit 1
    ;;
esac

mkdir -p "$hermes_home" /workspace
chown "${HERMES_UID:-1000}:${HERMES_GID:-1000}" /workspace
chmod 775 /workspace

env_tmp="$hermes_home/.env.eia-tmp"
umask 077
cat > "$env_tmp" <<EOF
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8642
API_SERVER_MODEL_NAME=hermes-agent
API_SERVER_KEY=${api_key}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_BASE_URL=${OPENAI_BASE_URL:-}
FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
EXA_API_KEY=${EXA_API_KEY:-}
PARALLEL_API_KEY=${PARALLEL_API_KEY:-}
EOF
mv "$env_tmp" "$hermes_home/.env"
chmod 600 "$hermes_home/.env"

q_model="$(yaml_quote "$model")"
q_web_backend="$(yaml_quote "${HERMES_WEB_BACKEND:-ddgs}")"
q_web_search_backend="$(yaml_quote "${HERMES_WEB_SEARCH_BACKEND:-ddgs}")"
q_terminal_backend="$(yaml_quote "$terminal_backend")"
q_terminal_cwd="$(yaml_quote "$terminal_cwd")"

# OpenAI-compatible SDK clients append `/chat/completions` to base_url. Keep
# a single canonical `/v1` URL for the only supported model interface.
base_url="${base_url%/}"
case "$base_url" in
  */v1) ;;
  *) base_url="$base_url/v1" ;;
esac
q_base_url="$(yaml_quote "$base_url")"

config_tmp="$hermes_home/config.yaml.eia-tmp"
cat > "$config_tmp" <<EOF
model:
  default: ${q_model}
  provider: 'custom:eia-managed'
  base_url: ${q_base_url}
agent:
  max_turns: ${HERMES_MAX_TURNS:-60}
  verbose: false
  reasoning_effort: ${HERMES_REASONING_EFFORT:-xhigh}
terminal:
  backend: ${q_terminal_backend}
  cwd: ${q_terminal_cwd}
  timeout: ${HERMES_TERMINAL_TIMEOUT:-900}
  home_mode: auto
EOF

cat >> "$config_tmp" <<EOF
custom_providers:
  - name: 'eia-managed'
    base_url: ${q_base_url}
    key_env: 'OPENAI_API_KEY'
    model: ${q_model}
    api_mode: 'chat_completions'
EOF

if [ "$terminal_backend" = "docker" ]; then
  require_value HERMES_DOCKER_WORKSPACES_HOST
  require_value HERMES_DOCKER_OUTPUTS_HOST
  require_value HERMES_DOCKER_VISION_HOST
  cat >> "$config_tmp" <<EOF
  docker_image: $(yaml_quote "${HERMES_DOCKER_IMAGE:-eia-ai-hermes-tools:0.2.0}")
  docker_volumes:
    - $(yaml_quote "${HERMES_DOCKER_WORKSPACES_HOST}:/eia/workspaces:ro")
    - $(yaml_quote "${HERMES_DOCKER_OUTPUTS_HOST}:/eia/outputs")
    - $(yaml_quote "${HERMES_DOCKER_VISION_HOST}:/eia/vision-cache")
  docker_forward_env: []
  docker_env: {}
  docker_extra_args: []
  docker_run_as_host_user: true
  docker_persist_across_processes: false
  docker_orphan_reaper: true
  docker_mount_cwd_to_workspace: false
  container_persistent: false
  container_cpu: ${HERMES_DOCKER_CPU:-2}
  container_memory: ${HERMES_DOCKER_MEMORY_MB:-4096}
  container_disk: ${HERMES_DOCKER_DISK_MB:-20480}
EOF
fi

cat >> "$config_tmp" <<EOF
approvals:
  mode: off
  timeout: 60
  cron_mode: deny
web:
  backend: ${q_web_backend}
  search_backend: ${q_web_search_backend}
browser:
  inactivity_timeout: 120
tool_loop_guardrails:
  warnings_enabled: true
  hard_stop_enabled: true
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
  in_place: true
  abort_on_summary_failure: true
context:
  engine: compressor
prompt_caching:
  cache_ttl: 5m
gateway:
  api_server:
    max_concurrent_runs: ${HERMES_MAX_CONCURRENT_RUNS:-4}
platform_toolsets:
  api_server:
    - browser
    - code_execution
    - delegation
    - file
    - memory
    - session_search
    - skills
    - terminal
    - todo
    - vision
    - web
_config_version: 33
EOF

mv "$config_tmp" "$hermes_home/config.yaml"
chmod 640 "$hermes_home/config.yaml"

echo "[eia-config] Hermes configured: provider=custom:eia-managed model=$model terminal=$terminal_backend"
