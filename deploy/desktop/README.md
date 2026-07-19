# 单机版 Docker Compose 交付

本目录用于在一台 Linux、macOS 或 Windows 电脑上同时运行业务后端与 Hermes。宿主机只需要 Docker（Windows/macOS 使用 Docker Desktop）；Python、Node、Hermes 和 OCR/PDF 工具均在容器内。

## 首次启动

Linux / macOS：

```bash
cd deploy/desktop
./start.sh
```

Windows：双击 `start.bat`，或在命令提示符中运行：

```bat
cd deploy\desktop
start.bat
```

第一次运行只会生成 `.env` 和一把 `desktop-` 前缀的 256-bit 随机 Hermes API Key，然后停止。填写以下三项后再次运行启动脚本：

```env
OPENAI_API_KEY=真实模型服务Key
OPENAI_BASE_URL=https://模型服务地址/v1
OPENAI_MODEL=真实模型名称
```

模型配置只有这三个 `OPENAI_*` 字段。不要再添加 `LLM_BASE_URL`、`CUSTOM_BASE_URL` 或其他模型 Key；启动脚本会将地址统一为 OpenAI 兼容的 `/v1` 基地址，并由 Hermes 从 `OPENAI_API_KEY` 读取凭据。

启动成功后访问 `http://127.0.0.1:8501`。Web 与 Hermes 调试端口都固定绑定宿主机 `127.0.0.1`，不会监听局域网地址。可以通过 `.env` 修改 `APP_PORT` 和 `HERMES_PORT`，但不能修改绑定地址。

## 启动前预检

每次启动都会检查模型配置、端口、随机 Hermes API Key 与 Docker 状态：

脚本不会强制调用模型服务的 `/models` 端点，因为不少兼容服务不实现该接口。Hermes Gateway 的健康检查和实际节点运行会反馈上游接口问题，避免在启动阶段误判正常 API 为不可用。

## 日常操作

Linux / macOS：

```bash
./start.sh
./stop.sh
./logs.sh
./logs.sh backend
./logs.sh hermes
./backup.sh
```

Windows 对应使用 `start.bat`、`stop.bat`、`logs.bat [backend|hermes]` 和 `backup.bat`。

`backup.sh` / `backup.bat` 会短暂停止正在运行的 backend 与 Hermes，归档完成后恢复先前运行的服务。备份写入 `backups/eia-desktop-YYYYmmdd_HHMMSS.tgz`，不包含 `.env`、Hermes `.env` 或 `auth.json`；密钥需要由部署管理员另行保管。

首次使用请通过 `start.sh` / `start.bat` 启动，不要先直接运行 `docker compose up`。启动脚本会按当前桌面用户预创建运行与备份目录；备份辅助容器无网络，仅以 root 完成归档后将产物归还给该用户，以兼容历史 root 所有者目录。

## 独立运行数据

所有持久化内容均位于本目录，不读取或写入仓库根目录的 `data/`、`.state/`、`logs/`、`outputs/` 或 `docker/hermes-data/`：

```text
runtime/data/       上传、任务、checkpoint、知识库、工作区、视觉缓存
runtime/outputs/    Agent 和节点产物
runtime/logs/       后端事件与运行日志
runtime/state/      桌面版维护状态
runtime/hermes/     Hermes 配置、会话和网关状态
backups/            一致性备份包
```

`stop` 和 `docker compose down` 不会删除这些目录。

## 容器接口与边界

- backend 使用仓库共享的 `Dockerfile.backend`。
- Hermes 使用仓库共享的 `Dockerfile.hermes`；该 Dockerfile 会把共享的 `docker/hermes/start-hermes.sh` 安装为 s6 初始化钩子，并保留基础镜像的 Gateway 托管入口。
- Compose 显式传入 `HERMES_TERMINAL_BACKEND=local` 和 `/opt/data/workspace` 工作目录；这里的 local 是 Hermes 容器内部终端，不是宿主机终端。
- Hermes 以只读方式访问 `/eia/workspaces`，以读写方式访问 `/eia/outputs` 和 `/eia/vision-cache`，不挂载 Docker socket；文件工具的写入白名单只包含 `/opt/data` 与 `/eia/outputs`。
- Hermes 使用原生上下文压缩器；压缩在原会话内完成，若摘要生成失败则停止该节点，不以静默截断的上下文继续运行。
- backend 只通过内部 Compose 网络访问 `http://hermes:8642`，模型 Key 只传给预检与 Hermes 容器。

首次构建会下载 Hermes 基础镜像并安装 OCR/PDF 依赖，耗时和占用空间明显高于普通 Web 镜像。项目源码及三个共享文件必须保持相对目录结构不变，不能只复制 `deploy/desktop/` 单独构建。
