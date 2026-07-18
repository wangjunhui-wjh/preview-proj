#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

mkdir -p backups
stamp="$(date +%Y%m%d_%H%M%S)"
target="backups/eia-ai-assistant-${stamp}.tgz"

tar -czf "$target" \
  data \
  outputs \
  logs \
  .state \
  docker/hermes-data \
  .env

echo "备份已生成：$target"
echo "注意：备份包含 .env，里面可能有 API Key，请妥善保管。"
