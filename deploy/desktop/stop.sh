#!/bin/sh
set -eu

DESKTOP_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
export DESKTOP_DIR
. "$DESKTOP_DIR/lib.sh"

require_docker
compose down --remove-orphans
printf '%s\n' 'Desktop services stopped. Runtime data was preserved.'
