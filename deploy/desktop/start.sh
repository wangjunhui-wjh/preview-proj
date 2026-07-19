#!/bin/sh
set -eu

DESKTOP_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export DESKTOP_DIR
. "$DESKTOP_DIR/lib.sh"

require_docker
ensure_env

if [ "$ENV_CREATED" -eq 1 ]; then
  printf '%s\n' 'Created deploy/desktop/.env with a random Hermes API key.'
  printf '%s\n' 'Set the model provider, key, URL and model name, then run start.sh again.'
  exit 0
fi

validate_env_file
set_host_identity
prepare_runtime

compose up --detach --build --wait --wait-timeout "${STARTUP_TIMEOUT:-900}"

app_port="$(read_env_value APP_PORT)"
app_port=${app_port:-8501}
printf '\n%s\n' 'Desktop services are healthy.'
printf 'Open: http://127.0.0.1:%s\n' "$app_port"
printf '%s\n' 'Logs:  ./logs.sh'
printf '%s\n' 'Stop:  ./stop.sh'
