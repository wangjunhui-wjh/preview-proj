@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo 未检测到 Docker。请先安装并启动 Docker Desktop。
  pause
  exit /b 1
)

if not exist .env (
  copy .env.example .env >nul
  echo 已生成 .env。
  echo 请先用记事本打开 .env，填写模型 API Key、Base URL 和模型名，然后再次双击 start.bat。
  notepad .env
  pause
  exit /b 0
)

if not exist data mkdir data
if not exist logs mkdir logs
if not exist outputs mkdir outputs
if not exist backups mkdir backups
if not exist docker\hermes-data mkdir docker\hermes-data

docker compose up -d --build
if errorlevel 1 (
  echo 启动失败，请查看上方错误。
  pause
  exit /b 1
)

echo 启动完成，正在打开浏览器...
start http://localhost:8501
pause
