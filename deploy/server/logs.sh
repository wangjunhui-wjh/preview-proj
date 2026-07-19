#!/bin/sh
set -eu

SERVER_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export SERVER_DIR
. "$SERVER_DIR/lib.sh"

require_docker
[ -f "$ENV_FILE" ] || die 'deploy/server/.env does not exist.'
[ "$#" -le 1 ] || die 'Usage: ./logs.sh [caddy|backend|hermes]'
service=${1:-}
case "$service" in ""|caddy|backend|hermes) ;; *) die 'Usage: ./logs.sh [caddy|backend|hermes]' ;; esac
if [ -n "$service" ]; then
  compose logs --follow --tail "${LOG_TAIL:-200}" "$service"
else
  compose logs --follow --tail "${LOG_TAIL:-200}"
fi
