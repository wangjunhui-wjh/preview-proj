#!/bin/sh
set -eu

SERVER_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export SERVER_DIR
. "$SERVER_DIR/lib.sh"

require_docker
[ -f "$ENV_FILE" ] || die 'deploy/server/.env does not exist.'
set_runtime_paths
set_host_identity
prepare_runtime

running=$(compose ps --services --status running || true)
was_running=0
for service in $running; do case "$service" in caddy|backend|hermes) was_running=1 ;; esac; done
restart_after_backup() {
  if [ "$was_running" -eq 1 ]; then
    compose up --detach --wait --wait-timeout "${STARTUP_TIMEOUT:-900}"
  fi
}
trap restart_after_backup EXIT HUP INT TERM
if [ "$was_running" -eq 1 ]; then compose stop caddy backend hermes; fi

stamp=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="eia-server-${stamp}.tgz"
export BACKUP_FILE
compose --profile tools run --rm --no-deps backup

[ -s "$BACKUP_ROOT/$BACKUP_FILE" ] || die 'Backup archive was not created.'
printf 'Backup created: %s\n' "$BACKUP_ROOT/$BACKUP_FILE"
printf '%s\n' 'Model keys, Hermes API keys and auth.json are excluded; preserve deploy/server/.env separately if required.'
