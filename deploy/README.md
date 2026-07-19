# Docker 交付入口

本仓库提供两个独立运行版本，业务代码、提示词和 Hermes 衍生镜像共享，但运行数据、端口、Compose 项目名和配置文件彼此隔离。

| 版本 | 入口 | 适用场景 | 对外端口 |
| --- | --- | --- | --- |
| 单机版 | `deploy/desktop/` | 一名可信用户的个人电脑 | 仅 `127.0.0.1` |
| 私有化服务器版 | `deploy/server/` | 单一组织的内网、VPN 或受控服务器 | 仅 Caddy 的 HTTPS/HTTP |

不要混用两个目录下的 `.env`、`runtime/`、`backups/` 或 Compose 项目名。二者可以在同一台主机共存，前提是服务器版配置未与桌面版端口冲突。

## 常规交付

有网络的部署电脑只需获得仓库源码并安装 Docker Engine 或 Docker Desktop：

```bash
./deploy/desktop/start.sh
# 或
./deploy/server/start.sh
```

首次执行只创建权限受限的 `.env`。填写模型配置后再次执行。详细说明见各版本目录内的 `README.md`。

## 离线交付

在已经构建并验收镜像、且可访问镜像源的发布机上执行：

```bash
./deploy/export-images.sh --build
```

该命令会生成 `deploy/image-bundles/eia-ai-images-0.2.0.tar` 以及镜像清单和 SHA-256 文件。归档不含 `.env`、模型 Key、任务文件、知识库、Caddy 证书和 Hermes 会话数据。

在离线目标机先安装 Docker，再导入：

```bash
./deploy/import-images.sh /path/to/eia-ai-images-0.2.0.tar
```

然后复制同一版本源码，按所选版本创建 `.env` 并启动。若离线目标机使用服务器版，`CADDY_IMAGE` 必须保持与 `deploy/images.manifest` 中的固定 digest 一致。

## 发布前检查

```bash
./deploy/export-images.sh --dry-run
./deploy/import-images.sh /path/to/eia-ai-images-0.2.0.tar --dry-run
```

镜像档案是运行环境，不替代业务数据备份。使用 `deploy/desktop/backup.sh` 或 `deploy/server/backup.sh` 备份任务数据；部署管理员需单独、安全地保管 `.env`。
