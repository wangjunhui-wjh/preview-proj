#!/bin/sh
set -eu

SERVER_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export SERVER_DIR
. "$SERVER_DIR/lib.sh"

require_docker
[ -f "$ENV_FILE" ] || die 'deploy/server/.env does not exist.'
compose down --remove-orphans
printf '%s\n' 'Server services stopped. Runtime data and certificates were preserved.'
