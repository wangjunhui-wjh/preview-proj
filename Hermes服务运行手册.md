# Hermes 服务运行手册

本文件记录当前机器上 Hermes Agent 的安装、配置、启动、停止和前置验证结果。业务系统开发暂停时，以本文件和 `.state/progress.md` 为恢复依据。

## 当前结论

- Hermes CLI 已完整安装：`~/.local/bin/hermes`
- Hermes 版本：`0.18.0`
- Hermes 代码目录：`~/.hermes/hermes-agent`
- Hermes 配置目录：`~/.hermes/`
- API Server 已通过 `tmux` 持久运行：`hermes-eia`
- API Server 地址：本机访问 `http://127.0.0.1:8642`；服务监听 `0.0.0.0:8642`，Docker 后端通过 `host.docker.internal:8642` 访问
- API Server model 名称：`hermes-agent`
- 上游模型：`grok-4.5`
- 上游 provider：`custom`
- 上游 base URL：`https://api.aiboys.xyz/v1`
- Agent reasoning effort：`xhigh`
- 终端后端：Hermes 原生 Docker terminal，镜像 `eia-ai-hermes-tools:latest`
- 审批策略：仅 Docker terminal profile 使用 `approvals.mode: off`；Agent 命令不在宿主机执行

## 重要配置

Hermes 自身不应依赖某个临时 shell 里的 `export`。当前已经把模型配置写入：

```text
~/.hermes/config.yaml
```

关键配置：

```yaml
model:
  provider: custom
  default: grok-4.5
  base_url: https://api.aiboys.xyz
agent:
  reasoning_effort: xhigh
terminal:
  backend: docker
  docker_image: eia-ai-hermes-tools:latest
  cwd: /workspace
  timeout: 900
approvals:
  mode: off
```

服务私密环境变量在：

```text
~/.hermes/.env
```

其中包含：

```text
DEEPSEEK_API_KEY=...
OPENAI_API_KEY=...
AIBOYS_API_KEY=...
CUSTOM_BASE_URL=https://api.aiboys.xyz/v1
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8642
API_SERVER_MODEL_NAME=hermes-agent
API_SERVER_KEY=...
```

不要把 `~/.hermes/.env` 提交到项目仓库。切换为 Docker 默认后端容器模式时，已将 `~/.hermes/.env` 中的 `API_SERVER_HOST` 从 `127.0.0.1` 改为 `0.0.0.0`，原文件备份为 `~/.hermes/.env.bak-20260706-docker-host-bind`。

## 模型与 Docker Terminal 规则

当前实际请求走 `custom` provider，Hermes 会以 OpenAI-compatible `chat/completions` 方式访问 `https://api.aiboys.xyz/v1`。模型与 API key 都由 `~/.hermes/.env` 及 `~/.hermes/config.yaml` 提供，业务后端和终端沙箱不转发模型密钥。

Docker terminal 的固定边界：

- 资料工作区以只读方式挂载到 `/eia/workspaces`。
- 节点成果以读写方式挂载到 `/eia/outputs`；后端优先回收这里的 `{NODE}_output.md` / `{NODE}_result.json`。
- 容器工作目录为 `/workspace`，预装 Poppler、Tesseract 中英文、LibreOffice、PyMuPDF、pdfplumber、Office 读取库、Node 和 FFmpeg。
- 容器不挂载 Docker socket、项目源码、`.env` 或模型密钥；`approvals.mode: off` 仅适用于这个受限 Docker 后端，不能切回宿主机 `local` 后端继续沿用。
- 国内构建默认使用清华 Debian/PyPI 镜像；构建不需要梯子。构建参数 `APT_MIRROR`、`PIP_INDEX_URL` 可覆盖。

切回旧的宿主机终端前，必须恢复配置备份并重启网关：

```text
~/.hermes/config.yaml.bak-20260718-hermes-docker-terminal
```

## 启动服务

当前推荐用 `tmux` 运行，避免普通 `nohup &` 被当前执行环境清理：

```bash
tmux new-session -d -s hermes-eia \
  "cd /home/dev/projects/preview-proj && hermes gateway run --replace -v 2>&1 | tee -a logs/hermes_gateway_tmux_20260718_docker_terminal.log"
```

当前会话名记录在：

```text
.state/hermes_gateway_tmux_session
```

## 停止服务

```bash
tmux kill-session -t hermes-eia
```

或：

```bash
hermes gateway stop
```

## 查看状态

```bash
tmux ls | rg hermes-eia
hermes gateway status --full
curl -fsS http://127.0.0.1:8642/health
```

查看日志：

```bash
tail -f logs/hermes_gateway_tmux_20260703_0102.log
hermes logs gateway -n 100
hermes logs errors -n 100
```

## 调用 API Server

健康检查：

```bash
curl -fsS http://127.0.0.1:8642/health
```

模型列表：

```bash
KEY=$(awk -F= '$1=="API_SERVER_KEY"{print $2; exit}' ~/.hermes/.env)
curl -fsS -H "Authorization: Bearer $KEY" http://127.0.0.1:8642/v1/models
```

Agent run：

```bash
KEY=$(awk -F= '$1=="API_SERVER_KEY"{print $2; exit}' ~/.hermes/.env)
curl -fsS \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":"请只回复 OK"}' \
  http://127.0.0.1:8642/v1/runs
```

返回 `run_id` 后读取事件流：

```bash
curl -N -H "Authorization: Bearer $KEY" \
  "http://127.0.0.1:8642/v1/runs/{run_id}/events"
```

## 已完成烟测

安装日志：

```text
logs/hermes_install_20260703_0047.log
```

上游 OpenAI-compatible 探测：

```text
logs/upstream_openai_smoke_20260703_0104.log
```

Hermes chat completions 烟测：

```text
logs/hermes_llm_smoke_20260703_0105.json
```

Hermes `/v1/runs` 烟测：

```text
logs/hermes_run_smoke_20260703_0105_events.sse
```

Hermes Web Search 烟测：

```text
logs/hermes_web_search_smoke_20260703_0107.json
logs/hermes_run_web_smoke_20260703_0108_events.sse
logs/hermes_deepseek_v4_pro_smoke_20260704.sse
```

验证结果：

- `/health` 正常。
- `/v1/models` 正常。
- `/v1/chat/completions` 能通过 Hermes 调用上游模型并返回 `OK`。
- `/v1/runs` 能返回 SSE 事件：`message.delta`、`reasoning.available`、`run.completed`。
- `/v1/runs` 能触发 `web_search` 工具事件：`tool.started`、`tool.completed`。
- 2026-07-04 切换 DeepSeek 后，`/v1/runs` 烟测返回 `OK`；Hermes 日志确认 `provider=deepseek`、`base_url=https://api.deepseek.com/v1`、`model=deepseek-v4-pro`。

## Web Search 当前状态

当前已安装并启用 `ddgs`：

```bash
~/.hermes/bin/uv pip install --python ~/.hermes/hermes-agent/venv/bin/python ddgs
hermes config set web.search_backend ddgs
hermes config set web.backend ddgs
hermes tools enable --platform api_server web file terminal skills
```

说明：

- `ddgs` 不需要 API key，适合前置验证和基础搜索。
- `ddgs` 结果质量和稳定性不如专业 API。
- 政策依据强准确场景，建议后续配置 `FIRECRAWL_API_KEY`、`TAVILY_API_KEY`、`EXA_API_KEY` 或 `PARALLEL_API_KEY`。
- 当前 `ddgs` 主要解决“agent 能调用 Web Search 并返回真实 URL”的前置能力。

## 文档和视觉能力

安装完成后 Hermes 内置 skills 中已存在：

```text
productivity/ocr-and-documents
productivity/nano-pdf
```

API Server 平台当前启用：

```text
web
browser
terminal
file
code_execution
vision
skills
todo
delegation
```

后续业务开发时，LangGraph 节点应通过 `/v1/runs` 发送任务，让 Hermes 在工作区内读取 PDF、图片和资料文件。不要在前端直接解析 PDF，也不要把 PDF 全文一次性塞进 prompt。

2026-07-18 验收：真实任务 `e098c0e7-d05a-4282-89b8-2053ca4b822c` 的三份 PDF 已在 Docker terminal 内完成 `PREP-INGEST`。该 run 完成 14 次模型调用和 13 轮工具执行，产物被后端回收，任务暂停在 `HB-PT-000`；没有 `approval.request`。

注意当前的视觉路径边界：`vision_analyze` 运行在 Hermes Controller，不能直接访问终端容器的 `/workspace/*.png`。PDF 图像页当前会由 Agent 用容器内渲染和 Tesseract OCR 回退处理；要让视觉模型直接分析容器生成的图片，需要后续增加显式的图片缓存交接并做图片样本验收。
