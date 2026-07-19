# AI 辅助环评前期研判系统

系统以环评前期研判业务流程为主线：前端使用 `环评前期研判AI助手.html` 原型，FastAPI 提供任务与成果接口，LangGraph 管理节点顺序、暂停恢复和 checkpoint，Hermes Agent 负责节点内的资料读取、OCR、视觉识别、网页搜索、终端和子 Agent 工作。

业务后端不重复实现 Hermes 已具备的通用 Agent、PDF/OCR、视觉或搜索能力。所有正式依据必须来自上传资料、Hermes 实际读取的文件、实际访问网页或已审核知识库记录，并在节点成果中保留可追溯来源。

## 选择部署版本

| 版本 | 入口 | 适用对象 |
| --- | --- | --- |
| 单机版 | `deploy/desktop/` | 一位可信用户，在本机浏览器使用；端口只监听 `127.0.0.1` |
| 私有化服务器版 | `deploy/server/` | 单一组织的内网、VPN 或受控服务器；Caddy 提供 TLS 和基础认证 |

新用户默认使用单机版：Linux/macOS 运行 `./start.sh`，Windows 双击 `start.bat`。这两个根目录快捷入口只会转发到 `deploy/desktop/`，不会再启动历史的宿主 Hermes 模式。

服务器部署请直接进入 `deploy/server/` 并运行 `./start.sh`。两个版本的 `.env`、运行数据、备份和 Compose 项目名完全分离，可同时存在。

完整安装、离线镜像和备份说明见 [安装指南](docs/operations/安装说明-DockerCompose.md)；各版本的细节分别见 [单机版说明](deploy/desktop/README.md)、[服务器版说明](deploy/server/README.md) 和 [Docker 交付入口](deploy/README.md)。

## 项目结构

```text
backend/       FastAPI、LangGraph 状态与 Hermes Runs 适配
frontend/      原型后端适配、实时事件与 Word 风格结果预览
prompts/       PREP-INGEST 与 HB-PT 节点提示词
deploy/        单机版、服务器版、离线镜像工具
docker/        Hermes 官方镜像的配置生成钩子
logs/          持久工程实施日志（不存放运行时日志）
outputs/       保留的设计与验收文档
archive/       本地历史资料归档，不纳入 Git 或 Docker 构建
.state/        长任务可恢复进度
```

运行数据按部署版本隔离在 `deploy/desktop/runtime/` 或 `deploy/server/runtime/`。这些目录包含任务、上传资料、知识库、日志和 Hermes 状态，运行期间不得手动整理或移动；根目录的历史测试资料统一放入 `archive/`。

## 开发运行

本地开发需要单独运行 Hermes Gateway，并让后端通过 `HERMES_BASE_URL` 与 `HERMES_API_KEY` 连接。容器交付不依赖宿主机 Hermes：桌面版和服务器版都会启动各自的 Hermes Controller。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
uvicorn backend.main:app --host 127.0.0.1 --port 8501
```

打开 `http://127.0.0.1:8501/`。

## 运行边界

- 当前服务器版是私有化单租户部署，不是多租户 SaaS；不同组织应使用独立部署实例和运行目录。
- SQLite/LangGraph checkpoint 在当前设计中服务于单后端进程，不支持横向扩容。
- 发生服务中断时，后端会将遗留 `running` 任务转为 `paused`，由人工确认后从当前节点继续，绝不自动跳过失败节点。
- 资料、任务、知识库和备份可能包含项目敏感信息；模型 Key 与 Hermes 内部密钥只放入版本目录下权限受限的 `.env`，不提交 Git，也不默认放入备份。

## 长任务恢复

工程维护以 [.state/progress.md](.state/progress.md) 为唯一进度源。发生上下文压缩或任务中断时，先读取 `.state/progress.md`、`logs/` 和最近 `outputs/`/`.state/` 文件，再按 `next_step` 继续。
