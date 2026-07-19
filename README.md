# AI 辅助环评前期研判系统（单机版）

此分支只包含单机交付所需的应用源码、Hermes 容器配置和 Docker Compose 启停脚本。它不包含服务器版、历史项目资料、任务记录、知识库、日志、PPT 或开发测试资产。

## 安装

1. 安装 Docker。Windows/macOS 使用 Docker Desktop；Linux 安装 Docker Engine 与 Docker Compose Plugin。
2. 进入 `deploy/desktop/`，首次执行 `./start.sh`（Windows 使用 `start.bat`）。脚本会生成本机 `.env` 和内部 Hermes Key 后退出。
3. 在 `deploy/desktop/.env` 填写唯一的模型配置：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
4. 再次执行启动脚本，浏览器打开 `http://127.0.0.1:8501`。

完整日常操作、备份和运行目录说明见 [单机版说明](deploy/desktop/README.md)。

## 数据边界

首次启动会创建 `deploy/desktop/runtime/`。该目录保存该电脑自己的上传资料、任务、结果、知识库、日志和 Hermes 状态，不在 Git 中，也不会随源码分发。迁移或重装前请使用 `deploy/desktop/backup.sh` 或 `backup.bat` 单独备份。
