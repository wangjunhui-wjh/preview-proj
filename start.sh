#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "未检测到 docker。请先安装 Docker Desktop 或 Docker Engine。"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "未检测到 docker compose。请安装 Docker Compose。"
  exit 1
fi

created_env=0
if [ ! -f .env ]; then
  cp .env.example .env
  created_env=1
  if command -v python3 >/dev/null 2>&1; then
    key="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
    tmp=".env.tmp"
    sed "s/^HERMES_API_SERVER_KEY=.*/HERMES_API_SERVER_KEY=${key}/" .env > "$tmp"
    mv "$tmp" .env
  fi
fi

# The default Compose mode connects to the host Hermes gateway. Keep the
# backend container's internal key in sync with the gateway's API_SERVER_KEY.
if [ "${COMPOSE_PROFILES:-}" != "hermes" ] && [ -r "$HOME/.hermes/.env" ]; then
  host_key="$(sed -n 's/^API_SERVER_KEY=//p' "$HOME/.hermes/.env" | tail -n 1 | sed -E 's/^"(.*)"$/\1/')"
  if [ -n "$host_key" ]; then
    tmp=".env.tmp"
    sed "s/^HERMES_API_SERVER_KEY=.*/HERMES_API_SERVER_KEY=${host_key}/" .env > "$tmp"
    mv "$tmp" .env
    chmod 600 .env
  fi
fi

if [ "$created_env" -eq 1 ]; then
  echo "已生成 .env，并同步宿主机 Hermes 的内部网关密钥。默认模式的模型配置由 ~/.hermes/.env 管理；确认后再次运行 ./start.sh。"
  exit 0
fi

mkdir -p data/uploads data/tasks data/workspaces data/knowledge logs outputs .state docker/hermes-data backups

export HOST_UID="${HOST_UID:-$(id -u 2>/dev/null || echo 1000)}"
export HOST_GID="${HOST_GID:-$(id -g 2>/dev/null || echo 1000)}"

$COMPOSE up -d --build

echo ""
echo "启动完成。"
echo "用户访问地址： http://localhost:${APP_PORT:-8501}"
echo "查看日志：     ./logs.sh"
echo "停止服务：     ./stop.sh"
