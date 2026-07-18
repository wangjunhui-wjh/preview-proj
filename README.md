# AI 辅助环评前期研判系统

本项目已重置技术路线，旧 Streamlit 演示和手写文档解析/Web Search/视觉工具代码已清理。

新的目标架构：

```text
前端：环评前期研判AI助手.html
后端：FastAPI
流程状态机：LangGraph
节点执行 Agent：Hermes Agent
提示词资产：prompts/
状态与日志：.state/、logs/、outputs/、data/
```

详细实施方案见 [实施方案.md](实施方案.md)。

## 当前状态

当前仓库已完成可运行纵切：

- FastAPI 后端运行在 `http://127.0.0.1:8501`
- HTML 原型可通过 `http://127.0.0.1:8501/` 打开
- 已接入 `PREP-INGEST` 项目资料读取 Agent，以及 `HB-PT-000/001/002/003/005/007/010/011`，缺失提示词的节点暂不伪实现
- 第一页仅提交原始粘贴文本和上传文件；PDF/DOCX/扫描件/图片的正式读取、OCR/视觉识别和项目档案归纳由 `PREP-INGEST` 节点完成，后续 HB 节点优先读取该项目档案
- 后端通过 Hermes Agent 调用模型、读取工作区文件、执行 PDF/OCR/图片识别相关工具、记录工具事件
- 已验证扫描 PDF：能识别空文本层 PDF、转图并 OCR，输出节点 Markdown/JSON/tool_trace
- 已验证独立图片上传：后端 Hermes 视觉工具可读取图片内容并输出节点结果
- 已验证 HB-PT-003 联网检索：Hermes 会自主组织 web_search，候选政策依据写入知识库并保存 URL/快照/hash/抽取文本
- 运行中暂停会请求停止当前 Hermes run，任务最终保持 `paused`，不会继续后续节点
- 支持单步执行、专项一键分析、全流程一键分析和暂停。
- 支持后端 Agent 执行上传资料有效性/可用性验证，输出文件可读性、项目相关性、可用于哪些模块、政策有效性风险和人工复核清单。
- 支持独立联网检索 Agent，用户输入自然语言检索问题，后端自主组织搜索并把真实 URL 写入候选依据库。
- 支持节点反馈修正，人工反馈会触发后端 Agent 重新核对目标节点，并清理受影响的下游节点。
- 外层节点推进已接入 LangGraph StateGraph，checkpoint 写入 `data/langgraph_checkpoints.sqlite`
- 节点结果页面显示该节点已记录的依据 URL 和候选知识库文档 ID
- 支持候选政策依据人工确认、正式入库，并可把已确认依据加入具体任务供后续节点优先使用
- 已新增 fake Hermes 验收脚本，可在不调用真实模型的情况下验证全流程、暂停、恢复和节点重跑
- 已新增 POC-06 边界验收脚本，覆盖暂停竞态、SSE 完成事件、终态暂停和 paused 后 rerun
- 实时事件已做小段聚合，避免逐 token 生成大量日志

已保留：

- `环评前期研判AI助手.html`：目标前端原型。
- `prompts/`：HB-PT 节点提示词资产。
- `AI辅助环评前期研判提示词体系模板-可直接使用.docx`、`系统设计提示词.md`：需求和提示词来源文档。
- `llm开发经验.md`：此前 LLM、文档读取、日志和 agent 经验记录。
- `.state/`、`logs/`、`outputs/`：长任务状态、日志和产物目录。

已清理：

- 旧 Streamlit 入口 `app.py`。
- 旧手写工作流包 `eia_ai_demo/`。
- 旧 smoke 脚本 `scripts/`。
- 历史运行日志和旧报告产物。

## Hermes 前置服务

Hermes Agent 已在本机完成安装和服务化前置验证。运行手册见 [Hermes服务运行手册.md](Hermes服务运行手册.md)。

当前 Hermes API Server：

```bash
http://127.0.0.1:8642
```

当前推荐通过 `tmux` 维护：

```bash
tmux ls | rg hermes-eia
hermes gateway status --full
curl -fsS http://127.0.0.1:8642/health
```

已验证：

- Hermes CLI 可用。
- API Server `/health` 可用。
- `/v1/chat/completions` 可通过 Hermes 调用上游模型。
- `/v1/runs` 可返回 SSE 事件流。
- `web_search` 工具可通过 `ddgs` 返回真实 URL。

## 启动方式

### Docker Compose 部署

面向非技术用户的推荐交付方式是 Docker Compose：部署人员在服务器或固定电脑上启动后端容器，普通用户只通过浏览器访问。

默认模式不构建 Hermes 大镜像，后端容器连接宿主机已运行的 Hermes API Server：

```bash
curl -fsS http://127.0.0.1:8642/health
```

```bash
cp .env.example .env
# 编辑 .env，确认 HERMES_BASE_URL=http://host.docker.internal:8642
./start.sh
```

访问：

```text
http://localhost:8501
```

详细说明见 [安装说明-DockerCompose.md](安装说明-DockerCompose.md)。

如需全容器模式，可在 `.env` 中设置：

```env
COMPOSE_PROFILES=hermes
HERMES_BASE_URL=http://hermes:8642
```

然后再次运行 `./start.sh`。该模式会拉取/构建 Hermes 镜像，首次构建耗时较长。

### 本地开发启动

Hermes API Server 需先保持运行：

```bash
tmux ls | rg hermes-eia
curl -fsS http://127.0.0.1:8642/health
```

业务后端启动方式：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8501
```

打开页面：

```text
http://127.0.0.1:8501/
```

后端调用 Hermes 时应使用：

```bash
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=<读取 ~/.hermes/.env 里的 API_SERVER_KEY>
HERMES_MODEL=hermes-agent
```

## 长任务恢复

开发和后续维护以 `.state/progress.md` 为进度源。发生上下文压缩或中断时，先读取 `.state/progress.md`、`logs/` 和最近输出，再从 `next_step` 继续。

当前外层流程由 LangGraph StateGraph 推进，图 checkpoint 写入 `data/langgraph_checkpoints.sqlite`；`data/tasks/<task_id>/state.json` 仍保留为前端/API 可读的任务状态投影。若后端进程重启后存在 `running` 任务，先调用：

```bash
curl -X POST http://127.0.0.1:8501/api/admin/recover-running-tasks \
  -H 'Content-Type: application/json' \
  -d '{"mode":"pause"}'
```

生成恢复摘要：

```bash
scripts/recovery_snapshot.py --root . --task-id <task_id>
```

离线验收，不调用真实模型：

```bash
scripts/poc05_acceptance.sh
scripts/poc05_pause_resume_rerun.sh
scripts/poc06_edge_cases.sh
scripts/poc08_export_smoke.sh
```

## 当前限制

- 所有设计节点 `PREP-INGEST` 与 `HB-PT-000` 至 `HB-PT-011` 已接入后端 Agent；各节点仍会在依据不足时输出“资料不足，建议人工核实”。
- LangGraph checkpoint 稳定在节点边界；如果进程死在 Hermes SSE 流中途，需要通过恢复接口把任务转为 `paused` 或 `failed`，再重跑当前节点，不能恢复同一个外部 Hermes 流。
- 前端不再配置模型 Key 或搜索 API；模型、视觉和 web_search 能力由 Hermes/后端环境变量管理。独立联网检索也通过后端 Agent 执行。
- 图片/扫描件能力依赖 Hermes 当前可用工具链和上游模型；已用扫描 PDF 和独立图片样本验证基础链路。
- Web Search 可由 Hermes 自主组织；搜索发现的政策依据先进入候选库，已支持人工确认正式入库，规则自动确认尚未实现。
