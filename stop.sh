#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if docker compose version >/dev/null 2>&1; then
  docker compose down
else
  docker-compose down
fi
