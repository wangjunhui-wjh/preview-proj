#!/bin/sh
set -eu

DESKTOP_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export DESKTOP_DIR
. "$DESKTOP_DIR/lib.sh"

require_docker
set_host_identity
prepare_runtime

if [ ! -w "$DESKTOP_DIR/backups" ]; then
  printf '%s\n' "Backup directory is not writable: $DESKTOP_DIR/backups" >&2
  printf '%s\n' 'Run start.sh once as the intended desktop user, or correct the directory ownership.' >&2
  exit 1
fi

was_backend=0
was_hermes=0
for service in $(compose ps --services --status running); do
  case "$service" in
    backend) was_backend=1 ;;
    hermes) was_hermes=1 ;;
  esac
done

stopped=0
restart_after_backup() {
  if [ "$stopped" -ne 1 ]; then
    return
  fi
  stopped=0
  if [ "$was_hermes" -eq 1 ] && [ "$was_backend" -eq 1 ]; then
    compose start --wait --wait-timeout "${STARTUP_TIMEOUT:-900}" hermes backend
  elif [ "$was_hermes" -eq 1 ]; then
    compose start --wait --wait-timeout "${STARTUP_TIMEOUT:-900}" hermes
  elif [ "$was_backend" -eq 1 ]; then
    compose start --wait --wait-timeout "${STARTUP_TIMEOUT:-900}" backend
  fi
}
trap restart_after_backup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if [ "$was_backend" -eq 1 ] || [ "$was_hermes" -eq 1 ]; then
  stopped=1
  if [ "$was_backend" -eq 1 ]; then
    compose stop backend
  fi
  if [ "$was_hermes" -eq 1 ]; then
    compose stop hermes
  fi
fi

stamp="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="eia-desktop-${stamp}.tgz"
export BACKUP_FILE
compose --profile tools run --rm --no-deps backup

if [ ! -s "$DESKTOP_DIR/backups/$BACKUP_FILE" ]; then
  printf '%s\n' 'Backup failed: archive was not created.' >&2
  exit 1
fi

restart_after_backup
trap - EXIT HUP INT TERM

printf 'Backup created: %s\n' "$DESKTOP_DIR/backups/$BACKUP_FILE"
printf '%s\n' 'Model keys and Hermes API keys are excluded; back up deploy/desktop/.env separately if required.'
