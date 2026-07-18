# 环评前期研判 AI 助手 Docker Compose 安装说明

本安装方式面向部署人员。最终使用者不需要安装 Python、Hermes、Docker 或配置模型，只需要浏览器访问系统网址。

当前默认模式是：Docker Compose 启动后端 Web 服务，Hermes Agent API Server 运行在宿主机 `127.0.0.1:8642`。这样可以避免首次部署时下载很大的 Hermes Docker 镜像。

## 一、推荐使用方式

```text
部署人员：在服务器或一台固定电脑上运行 Hermes + Docker Compose
普通用户：打开浏览器访问 http://服务器IP:8501
```

如果部署在本机，访问：

```text
http://localhost:8501
```

如果部署在内网服务器，访问：

```text
http://服务器IP:8501
```

## 二、部署前准备

需要安装：

- Docker Desktop（Windows / macOS）
- 或 Docker Engine + Docker Compose（Linux 服务器）
- Hermes Agent API Server，默认监听 `127.0.0.1:8642`

推荐服务器配置：

- CPU：2 核以上
- 内存：8 GB 以上
- 磁盘：50 GB 以上
- 网络：能访问模型 API 和必要的网页检索目标

## 三、首次启动

### Linux / macOS / 服务器

进入项目目录：

```bash
cd /path/to/eia-ai-assistant
./start.sh
```

第一次运行会自动生成 `.env`，然后停止并提示你填写配置。

编辑 `.env`：

```bash
nano .env
```

填好模型配置后再次启动：

```bash
./start.sh
```

默认 `.env` 中应保持：

```env
HERMES_BASE_URL=http://host.docker.internal:8642
```

启动前先确认宿主机 Hermes 在线：

```bash
curl -fsS http://127.0.0.1:8642/health
```

### Windows

1. 安装并启动 Docker Desktop。
2. 双击 `start.bat`。
3. 第一次运行会自动打开 `.env`。
4. 填好模型配置后保存，再次双击 `start.bat`。

Windows 默认同样要求宿主机 Hermes 服务已运行在 `127.0.0.1:8642`。

## 四、模型配置示例

### OpenAI-compatible 接口

适合自建代理、第三方 OpenAI 格式接口、AIBOYS 等。

```env
LLM_PROVIDER=custom
LLM_MODEL=gpt-5.5
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.example.com/v1
HERMES_REASONING_EFFORT=xhigh
```

### DeepSeek

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=你的DeepSeekKey
HERMES_REASONING_EFFORT=xhigh
```

### Hermes Agent API Key

`.env` 中的 `HERMES_API_SERVER_KEY` 是后端访问 Hermes 的内部密钥。首次运行 `start.sh` 会自动生成随机值；如果手动配置，请不要使用默认值：

```env
HERMES_API_SERVER_KEY=change-this-to-a-random-long-string
```

### 可选：全容器模式

如果希望 Docker Compose 同时构建并启动 Hermes 容器，在 `.env` 中设置：

```env
COMPOSE_PROFILES=hermes
HERMES_BASE_URL=http://hermes:8642
```

然后运行：

```bash
./start.sh
```

注意：Hermes 镜像较大，首次构建需要拉取数百 MB 镜像层，并安装 OCR/PDF 相关依赖。网络慢时建议继续使用默认的“宿主机 Hermes + 后端容器”模式。

## 五、日常操作

启动：

```bash
./start.sh
```

停止：

```bash
./stop.sh
```

查看日志：

```bash
./logs.sh
```

只看后端日志：

```bash
./logs.sh backend
```

只看 Hermes 容器日志（仅全容器模式）：

```bash
./logs.sh hermes
```

备份数据：

```bash
./backup.sh
```

注意：备份包包含 `.env`，可能包含 API Key，请妥善保管。

## 六、数据保存位置

以下目录会持久化保存在宿主机：

```text
data/              任务状态、上传文件、知识库、LangGraph checkpoint
outputs/           节点输出 Markdown/JSON/tool_trace
logs/              后端事件日志和服务日志
.state/            开发/维护进度状态
docker/hermes-data/ Hermes 配置、会话和运行数据，仅全容器模式使用
```

升级镜像或重启容器不会删除这些数据。

## 七、服务端口

默认端口：

```text
8501  Web 系统入口
8642  Hermes Agent API，仅绑定 127.0.0.1，供管理员排查
```

修改 Web 端口：

```env
APP_PORT=8501
```

例如改为 8080：

```env
APP_PORT=8080
```

用户访问：

```text
http://服务器IP:8080
```

## 八、验证部署是否正常

查看容器：

```bash
docker compose ps
```

后端健康检查：

```bash
curl http://localhost:8501/api/health
```

正常返回类似：

```json
{"status":"ok","hermes":{"status":"ok","platform":"hermes-agent","version":"0.18.0"}}
```

## 九、常见问题

### 1. 页面打不开

检查容器是否启动：

```bash
docker compose ps
```

检查日志：

```bash
./logs.sh
```

检查端口是否被占用，必要时修改 `.env`：

```env
APP_PORT=8080
```

### 2. 模型没有请求或节点一直等待

检查 `.env` 中模型配置是否正确：

```env
LLM_PROVIDER=
LLM_MODEL=
OPENAI_API_KEY=
OPENAI_BASE_URL=
DEEPSEEK_API_KEY=
```

查看 Hermes 日志：

```bash
./logs.sh hermes
```

### 3. PDF 或图片读取异常

Compose 版 Hermes 镜像已额外安装：

- `poppler-utils`
- `tesseract-ocr`
- `tesseract-ocr-chi-sim`
- `pymupdf`
- `pypdf`
- `python-docx`
- `openpyxl`

如果仍失败，先查看节点 tool_trace 和 Hermes 日志。

### 4. Web Search 不稳定

默认使用 `ddgs`，不需要 key，但稳定性不如专业搜索 API。政策依据强准确场景建议配置：

```env
FIRECRAWL_API_KEY=
TAVILY_API_KEY=
EXA_API_KEY=
PARALLEL_API_KEY=
```

## 十、给普通用户的话术

部署完成后，只需要告诉普通用户：

```text
请用浏览器打开：http://服务器IP:8501
上传项目资料，点击运行分析即可。
```

不要让普通用户接触 `.env`、Docker、Hermes 或后端日志。
