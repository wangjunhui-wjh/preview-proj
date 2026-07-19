#!/bin/sh

SERVER_DIR=${SERVER_DIR:?SERVER_DIR must be set before loading lib.sh}
ENV_FILE="$SERVER_DIR/.env"
PROJECT_ROOT=$(CDPATH= cd "$SERVER_DIR/../.." && pwd)

compose() {
  docker compose --env-file "$ENV_FILE" --project-directory "$SERVER_DIR" -f "$SERVER_DIR/compose.yaml" "$@"
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die 'Docker was not found.'
  docker info >/dev/null 2>&1 || die 'Docker daemon is not running or accessible.'
  docker compose version >/dev/null 2>&1 || die 'Docker Compose v2 is required.'
}

read_env_value() {
  key=$1
  awk -v wanted="$key" '
    index($0, wanted "=") == 1 {
      value = substr($0, length(wanted) + 2)
      sub(/\r$/, "", value)
      gsub(/^[ \t]+|[ \t]+$/, "", value)
      if (value ~ /^".*"$/ || value ~ /^'\''.*'\''$/) value = substr(value, 2, length(value) - 2)
      result = value
    }
    END { print result }
  ' "$ENV_FILE"
}

write_env_value() {
  key=$1
  value=$2
  temp_file="$ENV_FILE.tmp.$$"
  awk -v wanted="$key" -v replacement="$value" '
    BEGIN { found = 0 }
    index($0, wanted "=") == 1 { print wanted "=" replacement; found = 1; next }
    { print }
    END { if (!found) print wanted "=" replacement }
  ' "$ENV_FILE" > "$temp_file"
  mv "$temp_file" "$ENV_FILE"
}

is_template_value() {
  normalized=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case "$normalized" in
    ""|*replace-with*|*replace_me*|*your-key*|*your_key*|*change-me*|*changeme*|*placeholder*|*example.com*|__*) return 0 ;;
  esac
  return 1
}

validate_port() {
  name=$1
  value=$2
  case "$value" in
    ""|*[!0-9]*) die "$name must be a port number." ;;
  esac
  [ "$value" -ge 1 ] && [ "$value" -le 65535 ] || die "$name must be between 1 and 65535."
}

validate_server_network() {
  http_port=$(read_env_value HTTP_PORT); http_port=${http_port:-80}
  https_port=$(read_env_value HTTPS_PORT); https_port=${https_port:-443}
  bind_address=$(read_env_value BIND_ADDRESS); bind_address=${bind_address:-0.0.0.0}
  validate_port HTTP_PORT "$http_port"
  validate_port HTTPS_PORT "$https_port"
  [ "$http_port" != "$https_port" ] || die 'HTTP_PORT and HTTPS_PORT must be different.'
  case "$bind_address" in
    0.0.0.0|127.0.0.1|::|::1|*.*) ;;
    *) die 'BIND_ADDRESS must be an IPv4 address, 0.0.0.0, 127.0.0.1, :: or ::1.' ;;
  esac
}

random_hex() {
  LC_ALL=C od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]'
}

ensure_env() {
  ENV_CREATED=0
  umask 077
  if [ ! -f "$ENV_FILE" ]; then
    cp "$SERVER_DIR/.env.example" "$ENV_FILE"
    ENV_CREATED=1
  fi
  chmod 600 "$ENV_FILE" 2>/dev/null || true
}

resolve_server_path() {
  input=$1
  case "$input" in /*) path=$input ;; *) path="$SERVER_DIR/$input" ;; esac
  mkdir -p "$path"
  (cd "$path" && pwd -P)
}

set_runtime_paths() {
  RUNTIME_ROOT=$(resolve_server_path "$(read_env_value RUNTIME_ROOT)")
  BACKUP_ROOT=$(resolve_server_path "$(read_env_value BACKUP_ROOT)")
  write_env_value RUNTIME_ROOT "$RUNTIME_ROOT"
  write_env_value BACKUP_ROOT "$BACKUP_ROOT"
  export RUNTIME_ROOT BACKUP_ROOT
}

set_host_identity() {
  uid=$(read_env_value HOST_UID)
  gid=$(read_env_value HOST_GID)
  current_uid=$(id -u)
  current_gid=$(id -g)
  if [ "$current_uid" -eq 0 ]; then
    [ -n "$uid" ] && [ -n "$gid" ] && [ "$uid" -gt 0 ] && [ "$gid" -gt 0 ] || die 'Root deployment requires explicit non-root HOST_UID and HOST_GID.'
  else
    uid=${uid:-$current_uid}
    gid=${gid:-$current_gid}
    [ "$uid" = "$current_uid" ] && [ "$gid" = "$current_gid" ] || die 'Non-root deployment must use its own HOST_UID and HOST_GID.'
  fi
  HOST_UID=$uid
  HOST_GID=$gid
  write_env_value HOST_UID "$HOST_UID"
  write_env_value HOST_GID "$HOST_GID"
  export HOST_UID HOST_GID
}

prepare_runtime() {
  mkdir -p "$RUNTIME_ROOT/data/uploads" "$RUNTIME_ROOT/data/tasks" \
    "$RUNTIME_ROOT/data/workspaces" "$RUNTIME_ROOT/data/vision-cache" \
    "$RUNTIME_ROOT/data/knowledge" "$RUNTIME_ROOT/outputs" "$RUNTIME_ROOT/logs" \
    "$RUNTIME_ROOT/state" "$RUNTIME_ROOT/hermes/workspace" \
    "$RUNTIME_ROOT/caddy/data" "$RUNTIME_ROOT/caddy/config" "$BACKUP_ROOT"
  if [ "$(id -u)" -eq 0 ]; then
    chown -R "$HOST_UID:$HOST_GID" "$RUNTIME_ROOT" "$BACKUP_ROOT"
  fi
}

validate_model_configuration() {
  provider=$(read_env_value LLM_PROVIDER)
  provider=${provider:-custom}
  model=$(read_env_value LLM_MODEL)
  [ -n "$model" ] || model=$(read_env_value OPENAI_MODEL)
  openai_key=$(read_env_value OPENAI_API_KEY)
  deepseek_key=$(read_env_value DEEPSEEK_API_KEY)
  base_url=$(read_env_value LLM_BASE_URL)
  [ -n "$base_url" ] || base_url=$(read_env_value OPENAI_BASE_URL)
  [ -n "$base_url" ] || base_url=$(read_env_value CUSTOM_BASE_URL)
  case "$provider" in
    custom)
      ! is_template_value "$openai_key" && [ "${#openai_key}" -ge 8 ] || die 'Set OPENAI_API_KEY.'
      ! is_template_value "$base_url" || die 'Set OPENAI_BASE_URL or LLM_BASE_URL for the custom provider.'
      ;;
    openai) ! is_template_value "$openai_key" && [ "${#openai_key}" -ge 8 ] || die 'Set OPENAI_API_KEY.' ;;
    deepseek) ! is_template_value "$deepseek_key" && [ "${#deepseek_key}" -ge 8 ] || die 'Set DEEPSEEK_API_KEY.' ;;
    *) die 'LLM_PROVIDER must be custom, openai or deepseek.' ;;
  esac
  ! is_template_value "$model" || die 'Set LLM_MODEL or OPENAI_MODEL.'
  if [ -n "$base_url" ]; then case "$base_url" in http://*|https://*) ;; *) die 'Model base URL must be absolute HTTP(S).' ;; esac; fi
}

ensure_secrets() {
  hermes_key=$(read_env_value HERMES_API_SERVER_KEY)
  if is_template_value "$hermes_key" || [ "${#hermes_key}" -lt 16 ]; then
    key=$(random_hex); [ "${#key}" -eq 64 ] || die 'Could not generate Hermes API key.'
    write_env_value HERMES_API_SERVER_KEY "server-$key"
  fi
  auth_user=$(read_env_value BASIC_AUTH_USER)
  auth_hash=$(read_env_value BASIC_AUTH_HASH)
  case "$auth_user" in ""|*[!A-Za-z0-9._-]*) die 'BASIC_AUTH_USER has unsupported characters.' ;; esac
  if is_template_value "$auth_hash"; then
    password=$(random_hex | cut -c1-24)
    caddy_image=$(read_env_value CADDY_IMAGE); caddy_image=${caddy_image:-caddy:2-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648}
    auth_hash=$(docker run --rm "$caddy_image" caddy hash-password --algorithm bcrypt --plaintext "$password")
    case "$auth_hash" in '$2'*) ;; *) die 'Caddy did not return a bcrypt password hash.' ;; esac
    write_env_value BASIC_AUTH_HASH "'$auth_hash'"
    printf '\nInitial web password (shown once): %s\nRecord it securely.\n\n' "$password"
  fi
}

ensure_tool_image() {
  image=$(read_env_value HERMES_TOOL_IMAGE); image=${image:-eia-ai-hermes-tools:0.2.0}
  if docker image inspect "$image" >/dev/null 2>&1; then return; fi
  auto_build=$(read_env_value AUTO_BUILD_TOOLS)
  case "${auto_build:-true}" in true|TRUE|1|yes|YES) ;; *) die "Missing required tool image: $image" ;; esac
  docker build -f "$PROJECT_ROOT/Dockerfile.hermes-tools" -t "$image" "$PROJECT_ROOT"
}
