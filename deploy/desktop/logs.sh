#!/bin/sh
set -eu

DESKTOP_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export DESKTOP_DIR
. "$DESKTOP_DIR/lib.sh"

require_docker

if [ "$#" -gt 1 ]; then
  printf '%s\n' 'Usage: ./logs.sh [backend|hermes]' >&2
  exit 1
fi

service=${1:-}
case "$service" in
  ""|backend|hermes) ;;
  *)
    printf '%s\n' 'Usage: ./logs.sh [backend|hermes]' >&2
    exit 1
    ;;
esac

if [ -n "$service" ]; then
  compose logs --follow --tail "${LOG_TAIL:-200}" "$service"
else
  compose logs --follow --tail "${LOG_TAIL:-200}"
fi
