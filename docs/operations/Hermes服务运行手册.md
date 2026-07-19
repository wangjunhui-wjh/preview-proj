# Hermes 开发与运行手册

## 适用范围

本文件只说明源码开发时如何连接独立 Hermes Gateway。它不是 Docker 交付手册，也不记录任何开发机的模型名称、上游 URL、API Key、tmux 会话或个人 `~/.hermes` 配置。

面向非技术用户的单机版与私有化服务器版均会在 Compose 内启动自己的 Hermes Controller：

- 单机版：`deploy/desktop/`，Hermes 使用容器内 `terminal.backend: local`。
- 服务器版：`deploy/server/`，Hermes 使用原生 `terminal.backend: docker` 和受限文档工具镜像。

部署请阅读 [安装说明-DockerCompose.md](安装说明-DockerCompose.md) 和对应 `deploy/*/README.md`，不要要求部署机先安装 Hermes CLI 或启动宿主 Hermes 服务。

## 开发连接

开发模式中可在本机单独运行 Hermes Gateway，再用环境变量让 FastAPI 连接它：

```bash
export HERMES_BASE_URL=http://127.0.0.1:8642
export HERMES_API_KEY='gateway-internal-key'
export HERMES_MODEL=hermes-agent
uvicorn backend.main:app --host 127.0.0.1 --port 8501
```

Gateway 的模型 provider、模型名和上游 URL 由 Hermes 自身的受保护环境文件配置。业务前端不得保存或提交这些凭据，后端也不从浏览器接收模型 Key。

开发健康检查：

```bash
curl -fsS http://127.0.0.1:8642/health
curl -fsS http://127.0.0.1:8501/api/health
```

## Hermes 职责

Hermes 原生负责节点内部的 Agent 工作：

- 读取 PDF、DOCX、XLSX、图片及扫描件，按需要使用 OCR、Office、Poppler、Tesseract 和视觉工具。
- 自主组织网页检索、打开页面、保留 URL 与工具轨迹。
- 使用终端、代码执行、浏览器、文件、子 Agent 和 Runs/SSE/stop 等平台能力。
- 将节点成果写入受控工作区，供后端归档并传给下游 HB 节点。

FastAPI 不实现通用文档解析、OCR、视觉客户端、搜索引擎或 Agent 循环；LangGraph 仅管理环评节点顺序、checkpoint、暂停、恢复和失败停止。

## Terminal 与视觉边界

单机版的 terminal 在 Hermes Controller 容器内部执行。服务器版由 Hermes 原生 Docker terminal 为任务创建工具容器，工具镜像预装 PDF/OCR/Office 依赖，并满足以下边界：

- 项目资料目录以只读方式挂载到 `/eia/workspaces`。
- 节点成果和视觉缓存可写，分别挂载为 `/eia/outputs` 与 `/eia/vision-cache`。
- 工具容器不接收模型 Key、不挂 Docker socket、不挂业务源码。
- Controller 持有 Docker socket 是服务器版运行 Hermes 原生 Docker terminal 的必要权限，只能部署在受控的单租户主机。

Agent 需要视觉模型分析 PDF 渲染图时，必须把图写到 `/eia/vision-cache/<task_id>/`，后端提示词同时提供 Sandbox 路径与 Controller 可见路径；不要假设 Controller 能读取工具容器的 `/workspace` 私有路径。

## 已验证能力

- Hermes Gateway `/health`、`/v1/runs` 与 SSE 事件链路已完成验证。
- 真实项目资料读取曾在 `PREP-INGEST` 中完成三份 PDF 的文本、表格和扫描页 OCR 处理，并将成果归档到任务输出。
- 单机版与服务器版均完成容器健康烟测；服务器版还验证了 Caddy 认证、Controller Docker socket 权限、工具容器只读资料挂载和无密钥/无 socket 边界。

节点运行出现问题时，优先查看所选版本的 `logs.sh hermes`，然后检查任务事件、Hermes run_id、工具事件和模型服务凭据。不要通过前端重试掩盖失败，也不要绕过 Hermes 的 sandbox、审批或任务状态处理。
