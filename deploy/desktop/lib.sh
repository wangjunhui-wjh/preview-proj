#!/bin/sh

DESKTOP_DIR=${DESKTOP_DIR:?DESKTOP_DIR must be set before loading lib.sh}

compose() {
  docker compose --project-directory "$DESKTOP_DIR" -f "$DESKTOP_DIR/compose.yaml" "$@"
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    printf '%s\n' 'Docker was not found. Install Docker Desktop or Docker Engine first.' >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    printf '%s\n' 'Docker is installed but the daemon is not running.' >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    printf '%s\n' 'The Docker Compose plugin is required (docker compose).' >&2
    exit 1
  fi
}

read_env_value() {
  key=$1
  awk -v wanted="$key" '
    index($0, wanted "=") == 1 {
      value = substr($0, length(wanted) + 2)
      sub(/\r$/, "", value)
      gsub(/^[ \t]+|[ \t]+$/, "", value)
      if (value ~ /^".*"$/ || value ~ /^'\''.*'\''$/) {
        value = substr(value, 2, length(value) - 2)
      }
      result = value
    }
    END { print result }
  ' "$DESKTOP_DIR/.env"
}

write_env_value() {
  key=$1
  value=$2
  temp_file="$DESKTOP_DIR/.env.tmp.$$"
  if awk -v wanted="$key" -v replacement="$value" '
    BEGIN { found = 0 }
    index($0, wanted "=") == 1 {
      print wanted "=" replacement
      found = 1
      next
    }
    { print }
    END {
      if (!found) {
        print wanted "=" replacement
      }
    }
  ' "$DESKTOP_DIR/.env" > "$temp_file"; then
    mv "$temp_file" "$DESKTOP_DIR/.env"
  else
    rm -f "$temp_file"
    return 1
  fi
}

generate_hermes_key() {
  random_hex="$(LC_ALL=C od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]')"
  if [ "${#random_hex}" -ne 64 ]; then
    printf '%s\n' 'Could not generate a 256-bit Hermes API key.' >&2
    exit 1
  fi
  printf 'desktop-%s\n' "$random_hex"
}

ensure_env() {
  ENV_CREATED=0
  umask 077
  if [ ! -f "$DESKTOP_DIR/.env" ]; then
    cp "$DESKTOP_DIR/.env.example" "$DESKTOP_DIR/.env"
    ENV_CREATED=1
  fi

  hermes_key="$(read_env_value HERMES_API_SERVER_KEY)"
  case "$hermes_key" in
    ""|__GENERATE_ON_FIRST_START__|change-me|change-this-to-a-random-long-string)
      write_env_value HERMES_API_SERVER_KEY "$(generate_hermes_key)"
      ;;
  esac
  chmod 600 "$DESKTOP_DIR/.env" 2>/dev/null || true
}

is_template_value() {
  normalized="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    ""|*replace-with*|*replace_me*|*your-key*|*your_key*|*change-me*|*changeme*|*placeholder*|*example.com*|__*)
      return 0
      ;;
  esac
  return 1
}

validate_port() {
  name=$1
  value=$2
  case "$value" in
    ""|*[!0-9]*)
      printf 'Invalid %s: expected a port number.\n' "$name" >&2
      exit 1
      ;;
  esac
  if [ "$value" -lt 1 ] || [ "$value" -gt 65535 ]; then
    printf 'Invalid %s: expected a value between 1 and 65535.\n' "$name" >&2
    exit 1
  fi
}

validate_env_file() {
  provider="$(read_env_value LLM_PROVIDER)"
  provider=${provider:-custom}
  model_name="$(read_env_value LLM_MODEL)"
  if [ -z "$model_name" ]; then
    model_name="$(read_env_value OPENAI_MODEL)"
  fi
  openai_key="$(read_env_value OPENAI_API_KEY)"
  deepseek_key="$(read_env_value DEEPSEEK_API_KEY)"
  model_url="$(read_env_value LLM_BASE_URL)"
  if [ -z "$model_url" ]; then
    model_url="$(read_env_value OPENAI_BASE_URL)"
  fi
  if [ -z "$model_url" ]; then
    model_url="$(read_env_value CUSTOM_BASE_URL)"
  fi
  hermes_key="$(read_env_value HERMES_API_SERVER_KEY)"

  case "$provider" in
    custom)
      if is_template_value "$openai_key" || [ "${#openai_key}" -lt 8 ]; then
        printf '%s\n' 'Set OPENAI_API_KEY in deploy/desktop/.env.' >&2
        exit 1
      fi
      if is_template_value "$model_url"; then
        printf '%s\n' 'Set OPENAI_BASE_URL or LLM_BASE_URL for the custom provider.' >&2
        exit 1
      fi
      ;;
    openai)
      if is_template_value "$openai_key" || [ "${#openai_key}" -lt 8 ]; then
        printf '%s\n' 'Set OPENAI_API_KEY in deploy/desktop/.env.' >&2
        exit 1
      fi
      ;;
    deepseek)
      if is_template_value "$deepseek_key" || [ "${#deepseek_key}" -lt 8 ]; then
        printf '%s\n' 'Set DEEPSEEK_API_KEY in deploy/desktop/.env.' >&2
        exit 1
      fi
      ;;
    *)
      printf '%s\n' 'LLM_PROVIDER must be custom, openai or deepseek.' >&2
      exit 1
      ;;
  esac

  if [ -n "$model_url" ]; then
    case "$model_url" in
      http://*|https://*) ;;
      *)
        printf '%s\n' 'The configured model base URL must be an absolute HTTP(S) URL.' >&2
        exit 1
        ;;
    esac
  fi
  if is_template_value "$model_name"; then
    printf '%s\n' 'Set LLM_MODEL or OPENAI_MODEL in deploy/desktop/.env.' >&2
    exit 1
  fi
  if is_template_value "$hermes_key" || [ "${#hermes_key}" -lt 16 ]; then
    printf '%s\n' 'HERMES_API_SERVER_KEY must contain at least 16 non-template characters.' >&2
    exit 1
  fi
  if [ "$hermes_key" = "$openai_key" ] || [ "$hermes_key" = "$deepseek_key" ]; then
    printf '%s\n' 'HERMES_API_SERVER_KEY must not reuse a model provider key.' >&2
    exit 1
  fi

  app_port="$(read_env_value APP_PORT)"
  hermes_port="$(read_env_value HERMES_PORT)"
  app_port=${app_port:-8501}
  hermes_port=${hermes_port:-8642}
  validate_port APP_PORT "$app_port"
  validate_port HERMES_PORT "$hermes_port"
  if [ "$app_port" = "$hermes_port" ]; then
    printf '%s\n' 'APP_PORT and HERMES_PORT must be different.' >&2
    exit 1
  fi
}

prepare_runtime() {
  mkdir -p \
    "$DESKTOP_DIR/runtime/data/uploads" \
    "$DESKTOP_DIR/runtime/data/tasks" \
    "$DESKTOP_DIR/runtime/data/workspaces" \
    "$DESKTOP_DIR/runtime/data/vision-cache" \
    "$DESKTOP_DIR/runtime/data/knowledge" \
    "$DESKTOP_DIR/runtime/logs" \
    "$DESKTOP_DIR/runtime/outputs" \
    "$DESKTOP_DIR/runtime/state" \
    "$DESKTOP_DIR/runtime/hermes" \
    "$DESKTOP_DIR/runtime/hermes/workspace" \
    "$DESKTOP_DIR/backups"
  if [ "$(id -u)" -eq 0 ]; then
    chown -R "$HOST_UID:$HOST_GID" "$DESKTOP_DIR/runtime" "$DESKTOP_DIR/backups"
  fi
}

set_host_identity() {
  HOST_UID=${HOST_UID:-$(id -u 2>/dev/null || printf '1000')}
  HOST_GID=${HOST_GID:-$(id -g 2>/dev/null || printf '1000')}
  export HOST_UID HOST_GID
}
