#!/bin/sh
set -eu

SERVER_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export SERVER_DIR
. "$SERVER_DIR/lib.sh"

require_docker
ensure_env
if [ "$ENV_CREATED" -eq 1 ]; then
  printf '%s\n' 'Created deploy/server/.env.'
  printf '%s\n' 'Set SERVER_NAME and model configuration, then run start.sh again.'
  exit 0
fi

server_name=$(read_env_value SERVER_NAME)
if is_template_value "$server_name" || printf '%s' "$server_name" | grep -q '[/:[:space:]]'; then
  die 'SERVER_NAME must be a DNS name or IP address without scheme, port or path.'
fi
validate_model_configuration
validate_server_network
set_runtime_paths
set_host_identity
prepare_runtime
ensure_secrets
ensure_tool_image

compose config --quiet
compose up --detach --build --wait --wait-timeout "${STARTUP_TIMEOUT:-900}"

printf '\nServer services are healthy: https://%s\n' "$server_name"
printf '%s\n' 'Caddy Basic Auth protects the application. Backend and Hermes do not publish host ports.'
