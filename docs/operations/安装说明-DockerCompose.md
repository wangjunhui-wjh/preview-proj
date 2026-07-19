# Docker Compose 安装说明

本项目不再使用历史的“后端容器连接宿主机 Hermes”模式。请选择下列一种完整容器化版本，部署机仅需安装 Docker Engine 或 Docker Desktop。

## 1. 选择版本

| 需求 | 选择 | 启动入口 |
| --- | --- | --- |
| 个人电脑、单人使用、只允许本机访问 | 单机版 | `deploy/desktop/start.sh` 或 `start.bat` |
| 内网/VPN/受控服务器、一个组织共享 | 私有化服务器版 | `deploy/server/start.sh` |

服务器版是单租户部署。它使用 Caddy TLS 和 Basic Auth 保护系统入口，但不提供多用户账号、任务归属隔离、横向扩容或高可用。

## 2. 单机版

Linux/macOS：

```bash
./start.sh
```

Windows：双击根目录 `start.bat`，或执行：

```bat
start.bat
```

第一次执行会创建 `deploy/desktop/.env` 并生成 Hermes 内部随机密钥，然后停止。填写模型配置后再次启动：

```env
OPENAI_API_KEY=真实模型服务Key
OPENAI_BASE_URL=https://模型服务地址/v1
OPENAI_MODEL=真实模型名称
```

模型配置只使用这三个 `OPENAI_*` 字段。成功后访问 `http://127.0.0.1:8501`。Web 与 Hermes 调试端口均只绑定本机回环地址。

常用操作：

```bash
./start.sh
./stop.sh
./logs.sh
./backup.sh
```

详情见 [deploy/desktop/README.md](deploy/desktop/README.md)。

## 3. 私有化服务器版

使用 Linux Docker Engine，在服务器上执行：

```bash
cd deploy/server
./start.sh
```

首次执行会创建权限为 `0600` 的 `.env`。设置 `SERVER_NAME`、模型配置和需要的端口后再次执行。默认 `TLS_ISSUER=internal`，适合内网 DNS；公网域名且 80/443 可访问时，可改为有效运维邮箱，让 Caddy 自动申请证书。

```env
SERVER_NAME=eia.example.internal
OPENAI_API_KEY=真实模型服务Key
OPENAI_BASE_URL=https://模型服务地址/v1
OPENAI_MODEL=真实模型名称
```

仅 Caddy 发布 HTTP/HTTPS；backend `8501` 和 Hermes `8642` 不发布到宿主机。首次有效启动会显示一次 Basic Auth 初始密码，立即安全保存。详情见 [deploy/server/README.md](deploy/server/README.md)。

## 4. 数据与备份

每个部署目录各自保存 `runtime/` 与 `backups/`。其中包含上传资料、任务状态、LangGraph checkpoint、知识库、Agent 成果、非密钥 Hermes 状态和 Caddy 证书（服务器版）。`stop` 和 `docker compose down` 不会清空它们。

`backup.sh` 会短暂停止相关服务以得到一致性快照，并在结束后恢复原先运行的服务。备份不包含模型 Key、Hermes API Key、Hermes `auth.json` 或 `.env`；这些密钥文件需由部署管理员独立、安全保管。

## 5. 离线部署

联网发布机构建并导出镜像：

```bash
./deploy/export-images.sh --build
```

将生成的 `.tar`、`.sha256` 和 `.manifest.txt` 与同版本源码一起交付。离线目标机导入：

```bash
./deploy/import-images.sh /path/to/eia-ai-images-0.2.0.tar
```

然后按第 2 或第 3 节创建 `.env` 并启动。镜像包不含配置和项目数据，不能替代备份。

## 6. 升级与排障

升级前先执行对应版本的 `backup.sh`，再替换为同一发布版本源码并运行 `start.sh`。不要删除 `runtime/`，不要把桌面版运行目录复制到服务器版，也不要把 `.env` 提交 Git。

日志入口：

```bash
./deploy/desktop/logs.sh hermes
./deploy/server/logs.sh caddy
./deploy/server/logs.sh backend
```

Docker 服务健康但节点失败时，优先检查 Hermes 日志与模型服务凭据；不要通过前端传入 Key，也不要绕过 Hermes 自身的工具、审批和 sandbox 管理。
