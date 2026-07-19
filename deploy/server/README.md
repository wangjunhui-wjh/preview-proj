# 私有化服务器版 Docker Compose 交付

本版本面向单一组织的受控内网、VPN 或私有服务器。业务层仍是同一套 HTML、FastAPI 和 LangGraph；每个节点内部的资料读取、OCR、视觉、网页搜索、终端和子 Agent 都由 Hermes 原生能力完成。

只有 Caddy 发布到服务器网络并提供 HTTPS 和基础认证。backend 与 Hermes Controller 只在 Compose 内部网络通信。Hermes Controller 通过 Docker socket 使用原生 Docker terminal，项目任务在带资源限制的工具容器中运行；工具容器没有模型 Key、没有 Docker socket，项目输入只读，输出与视觉缓存可写。

## 首次启动

需要 Linux Docker Engine，部署用户必须可访问 Docker daemon。

```bash
cd deploy/server
./start.sh
```

第一次运行只创建权限为 `0600` 的 `.env`。填写 `SERVER_NAME` 和模型配置后再次运行。首次有效启动会生成并只显示一次 Basic Auth 初始密码，需立即保存。

`RUNTIME_ROOT` 会在启动时转换为宿主机绝对路径。这是 Hermes Docker terminal 的必要条件：工具容器 bind mount 的来源必须是 Docker daemon 所在主机的真实路径，不能是 Controller 容器内的路径。

## TLS 与访问

默认 `TLS_ISSUER=internal`，适用于内网 DNS。客户端需信任 Caddy 内部根证书，相关数据位于 `runtime/caddy/data`。公网域名且 80/443 可达时，可将 `TLS_ISSUER` 改为运维邮箱，由 Caddy 自动申请公开证书。

系统入口为 `https://SERVER_NAME`。

## 日常运维

```bash
./start.sh
./stop.sh
./logs.sh
./logs.sh hermes
./backup.sh
```

备份会短暂停止服务，包含项目数据、节点成果、LangGraph 状态、非密钥 Hermes 状态和 Caddy 证书数据；不包含 `deploy/server/.env`、Hermes `.env` 或 `auth.json`。备份辅助容器无网络，仅以 root 写入归档后立即把文件归还给配置的部署 UID/GID。

## 适用边界

- 本版是私有化单租户，不包含多用户账号、任务归属隔离、横向扩容或高可用。
- Controller 持有 Docker socket，因此是高权限运维组件；只能部署在可信服务器上，Caddy Basic Auth 不能替代多租户隔离。
- 视觉缓存统一使用 `/eia/vision-cache/<task_id>`，Controller 和工具容器经同一宿主目录访问，确保 PDF 渲染图可被 Hermes `vision_analyze` 读取。
