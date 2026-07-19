# AI 辅助环评前期研判系统开发进度

## Recovery Protocol

如果发生 context compacted 或任务中断，恢复时必须先读取：

1. `.state/progress.md`
2. `logs/`
3. 最近修改的 `outputs/` 或 `.state/` 状态文件

然后从 `next_step` 继续。不要只依赖聊天历史。

## Current State

- current_step: `MAINTENANCE-CTX-01`
- next_step: `DIAGNOSE_AND_GATE_INCOMPLETE_NODE_OUTPUTS`
- status: `native_context_compression_hardened`
- last_updated: `2026-07-19 Asia/Shanghai`
- target_route: `Hermes Agent + LangGraph + uploaded HTML prototype`
- active_agents: `Desktop Compose Hermes API Server eia-desktop-hermes-1, provider:custom:eia-managed, model:grok-4.5, terminal:local in Controller container`; `Desktop Compose backend eia-desktop-backend-1 on http://127.0.0.1:8501`

> 当前主任务为双版本交付。恢复时依次读取 `.state/dual_edition_plan.md`、`logs/dual_edition_20260719.md` 和 `outputs/双版本系统实施计划与验收标准.md`，再从当前 `next_step` 继续。

## New Technical Route

- 前端：以 `环评前期研判AI助手.html` 为目标原型和交互基准。
- 外层流程：LangGraph 负责 HB 节点顺序、状态、暂停、恢复、失败停止、checkpoint。
- 节点执行：Hermes Agent 负责每个节点内部的文档读取、OCR/视觉、网页搜索、工具调用和结果生成。
- 后端职责：任务管理、文件入库、Hermes 调用封装、事件流转发、结果校验、日志和输出归档。
- 依据原则：所有政策/知识依据必须来自上传材料、Hermes 实际读取的文件、实际访问的网页 URL 或可追溯工具结果。

## Reset Step Plan

| Step | Status | Description | Acceptance Criteria |
| --- | --- | --- | --- |
| RESET-01 | complete | 确认新技术路线和清理边界 | 保留 HTML 原型、需求文档、提示词资产和固定状态目录；删除旧 Streamlit/手写工具演示代码和历史产物 |
| RESET-02 | complete | 清理旧代码、旧日志、旧输出 | `app.py`、旧 `eia_ai_demo/` 手写服务、旧 smoke 脚本、历史 logs/outputs 被移除或重置 |
| RESET-03 | complete | 建立新路线目录和依赖说明 | 新增/更新 `requirements.txt`、`prompts/`、实施方案文档；目录适配 Hermes + LangGraph |
| RESET-04 | complete | 编写实施方案 | 输出详细阶段计划、模块边界、API 设计、状态设计、事件流、验收标准和风险 |
| RESET-05 | complete | 清理后检查 | 文件结构符合新路线；`.state/progress.md` 更新为下一阶段可恢复状态 |

## Next Phase Plan

| Step | Status | Description | Acceptance Criteria |
| --- | --- | --- | --- |
| PREP-01 | complete | 前置状态与环境恢复检查 | 不进入业务开发；确认 logs/outputs/.state、Hermes 安装状态、OpenAI 环境变量可见性 |
| PREP-02 | complete | Hermes 完整安装与服务化准备 | `hermes` CLI 可用；明确 API Server 启动命令、服务环境变量、健康检查方式 |
| PREP-03 | complete | 前置运行手册和配置文档 | 写清 `OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL` 与 Hermes custom/API Server 的配置方式 |
| POC-01 | complete | Hermes 单节点 POC | 使用 `HB-PT-000` 提示词和一个 PDF/文本资料验证 Hermes 能自动读取文档、必要时搜索网页，并输出结构化节点结果、依据和工具轨迹 |
| POC-02 | complete | FastAPI + LangGraph 最小后端 | 实现 `prepare -> HB-PT-000 -> complete`，支持创建任务、上传文件、执行一步、查看状态和日志 |
| POC-03 | complete | HTML 原型接后端 | `环评前期研判AI助手.html` 接入任务 API 和实时事件流，前端不再直接调用模型 |
| POC-04 | complete | 后续节点与真实资料验证 | 接入 `HB-PT-001` 起的节点执行；用真实 PDF/图片资料验证 Hermes 文件读取、图片识别、web_search 依据记录和暂停行为 |
| POC-05 | complete | 知识库确认与脚本化全流程长任务验收 | 完成候选依据人工确认/正式入库；完成 fake Hermes 连续全流程、暂停/恢复/rerun、manifest/recovery 验收；真实项目长跑留到 POC-06 运行层稳定后执行 |
| POC-06 | complete | LangGraph 运行层接入 | 用 LangGraph StateGraph/Checkpoint 替换临时顺序循环，保留现有 API、暂停/恢复、事件流、Hermes Agent 节点执行和 outputs/logs 产物 |
| POC-07 | complete | 真实项目全流程长跑与硬化 | 使用真实项目文本从初始化跑到综合报告和交叉核查；根据真实长跑暴露的问题加固输出预算、默认 verified 政策库注入、工具调用约束 |
| POC-08 | complete | 报告导出、前端结果查看与知识库治理 | 前端按节点浏览长跑结果、导出综合报告/交叉核查；候选依据人工审核批处理；补强政策元数据抽取和搜索质量 |
| POC-09 | complete | 项目资料 Agent 解析与项目档案构建 | 在 HB-PT-000 前新增资料读取 Agent 节点；浏览器上传不再把 PDF/图片解析结果当正式项目事实；后续节点优先读取项目档案 |
| POC-10 | complete | 前端上传不解析与缓存硬化 | 项目资料上传路径不再触发浏览器 PDF/DOCX/TXT 解析；HTML 响应禁止缓存；旧本地资料库解析不污染项目上传队列 |
| POC-11 | complete | 前端实时日志与结果展示优化 | 后端事件日志默认自动滚动到最新，鼠标悬停/手动上滚时暂停跟随；节点输出改为 Word 风格文档视图并支持下载 Word 格式 |
| POC-12 | complete | 前端拆分、事件回填与后台管理入口 | HTML 拆分为入口壳 + `frontend/app.css` + `frontend/app.js`；任务刷新会回填后端历史事件；新增知识库管理后台、审核历史和节点接入状态 |
| POC-13 | complete | 全设计节点接入后端 Agent | 基于 HTML 原型提示词补齐 `HB-PT-004/006/008/009` 后端提示词；LangGraph 路由接入全节点；后台管理显示 13/13 节点接入、0 个缺失 |
| POC-14 | complete | 新版原型功能迭代 | 已迁移一键分析、反馈修正、联网搜索独立功能、上传文件有效性 AI 验证和新版提示词约束；前端不恢复直连模型或浏览器解析 |
| POC-15 | complete | 前端原型一致化 | `环评前期研判AI助手.html` 与最新版 `环评前期研判AI助手(2).html` 保持可见结构一致，仅追加后端适配脚本；按钮动作仍走后端 Hermes/LangGraph |
| POC-16 | complete | 前端按钮细节调整 | 后续节点不再追加“一键分析全部流程”，仅 `HB-PT-000` 模块页保留；顶部右侧按钮文字改为黑色 |
| POC-17 | complete | 移除全流程一键分析入口 | 彻底移除前端所有“一键分析全部流程”按钮和 `runBackendAll` 适配函数；仅保留新版原型中的“一键运行全部专项研判” |
| POC-18 | complete | 结果 Word 预览与提示词编辑 | 当前原型适配层已把运行分析结果渲染为 Word 风格页面；提示词预览改为可编辑 textarea，运行节点时提交给后端并作为该任务节点提示词覆盖 |
| POC-19 | complete | 切换主模型到 DeepSeek V4 Pro | Hermes 配置改为 `provider=deepseek`、`model=deepseek-v4-pro`、`agent.reasoning_effort=xhigh`；网关重启并通过真实 `/v1/runs` 烟测 |
| POC-20 | complete | 节点文件产物优先采集与下一节点输入回填 | 修复 Hermes 最终摘要覆盖完整节点结果的问题；后端优先采集工作区 `{node}_output.md`/`{node}_result.json`；已修复任务 `b5b0c3a9-8fca-4efd-84ec-3b9d8ca40e41` 的 `HB-PT-000` 输出；前端 `HB-PT-001` 模块输入回填上一节点结果 |
| POC-21 | complete | 当前分析节点可视化 | 前端新增全局运行状态条、侧边栏当前节点“…”高亮、运行按钮禁用/等待状态；SSE 的 `node_start/hermes_call_start/tool_event/node_output_partial/node_complete` 会实时更新当前分析节点和阶段 |
| POC-22 | stopped | Docker Compose 交付包 | 已新增 `Dockerfile.backend`、`Dockerfile.hermes`、`docker-compose.yml`、`.env.example`、`start/stop/logs/backup` 脚本、Windows bat 和 `安装说明-DockerCompose.md`；脚本语法、后端编译、前端 JS、Compose 配置校验曾通过；后端镜像构建多次卡在 Docker 镜像源/PyPI 网络下载，按用户要求停止 Docker 改造；未完成完整镜像构建和 Compose 启动验收 |
| POC-23 | complete | Qoder Work Skill 交付包 | 已生成 `qoder-work-skills/eia-precheck-assistant/`，包含 `SKILL.md`、workflow/evidence references、结果模板和 17 个当前版本提示词；已打包 `outputs/eia-precheck-assistant-qoder-work-skill.zip`，并复制安装到 `/home/dev/.qoderwork/skills/eia-precheck-assistant/`；Qoder 结构校验和 zip 内容校验通过 |
| POC-24 | complete | Docker Compose 默认交付恢复 | 后端镜像已构建成功：`eia-ai-backend:latest`；`Dockerfile.backend` 改为本机已有 `python:3.13-slim`，`requirements.txt` 去掉 `uvicorn[standard]` 可选依赖，pip 默认使用 `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`；默认 Compose 改为只启动 `backend`，连接宿主机 Hermes `host.docker.internal:8642`；`docker compose --env-file .env.example up -d --build backend` 已启动 `eia-ai-backend`，`http://127.0.0.1:8501/api/health` 返回后端和 Hermes 均 `ok`；Hermes 宿主机监听改为 `0.0.0.0:8642`，备份 `~/.hermes/.env.bak-20260706-docker-host-bind`；Hermes 容器 profile 保留为可选但未完成构建，因 `nousresearch/hermes-agent` 最后一层下载过慢中断 |

## Keep

- `环评前期研判AI助手.html`
- `AI辅助环评前期研判提示词体系模板-可直接使用.docx`
- `系统设计提示词.md`
- `llm开发经验.md`
- `.state/`
- `logs/`
- `outputs/`
- HB-PT 提示词资产，迁移到顶层 `prompts/`

## Current File Structure

- `环评前期研判AI助手.html`: 目标前端原型。
- `实施方案.md`: Hermes + LangGraph + HTML 前端实施方案。
- `README.md`: 新路线简版说明。
- `requirements.txt`: 新后端最小依赖。
- `prompts/`: HB-PT 提示词资产。
- `backend/`: 后续 FastAPI/LangGraph 后端目录。
- `frontend/`: 后续 HTML 原型改造目录。
- `data/uploads/`, `data/tasks/`, `data/workspaces/`: 上传、任务状态和 Hermes 工作区目录。
- `logs/`, `outputs/`: 已清空历史产物，仅保留 `.gitkeep`。

## Remove As Legacy

- 旧 Streamlit 入口：`app.py`
- 旧手写工作流和工具包：`eia_ai_demo/`
- 旧 smoke 脚本：`scripts/`
- Python 缓存：`__pycache__/`
- 历史运行日志与报告产物，仅保留 `.gitkeep`

## Change Log

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-CTX-01` 完成。用户要求先允许 Agent 进行上下文压缩；诊断确认 Hermes 原配置实际已启用 `compression.enabled: true`，因此没有重复造压缩器。共享 Hermes 启动钩子现显式声明原生 `context.engine: compressor`、`compression.in_place: true` 与 `compression.abort_on_summary_failure: true`：压缩不再轮换 session id，压缩摘要失败时停止节点而非静默以截断上下文继续。仅重建了已暂停任务环境中的 Desktop Hermes Controller，backend 未重建、`deploy/desktop/runtime/` 未移动；Hermes healthy、`/api/ready` 已验证。此项不替代短过程句成果门禁：任务 `90510bf2-b7b7-4956-857b-a0a3a6b8566b` 的 `HB-PT-002/005/006/007/008/009` 已证实未写完整成果却被推进，后续需从 `DIAGNOSE_AND_GATE_INCOMPLETE_NODE_OUTPUTS` 实施“缺少完整成果文件/结构化结果即失败停止”修复。详见 `logs/hermes_context_compression_20260719.md`。

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-GIT-01` 完成。按用户要求更新当前 `main` 工作区：已提交 `f025018 chore: organize repository and repair agent artifacts`，包含 Hermes 节点成果写入白名单/工作区权限修复、根目录资料归档、文档分层、Docker 构建上下文收敛和维护记录；源码编译、前端 JS 语法、Desktop/Server Compose 静态配置均通过，在线 Desktop API 仍 ready。当前 `main` 比已知 `origin/main` 领先 6 个提交。SSH-over-443 的 fetch/push 均在密钥交换阶段被本地网络关闭；HTTPS 无凭据返回 403，且环境未配置 Git credential helper 或 `gh`。因此保留本地提交，不强推、不覆盖未知远端。网络/凭据恢复后，先 `git fetch origin main`，确认可快进后执行 `git push origin main`，再到 `/home/dev/projects/preview-proj-desktop-edition` 执行 `git push -u origin desktop-edition`。

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-DESKTOP-BRANCH-01` 完成。按用户要求创建仅含单机版交付所需文件的孤立 `desktop-edition` 分支，工作在独立 worktree，未切换当前 `main` 工作区、未触碰运行中的 Desktop 容器或 `deploy/desktop/runtime/`。分支仅提交应用源码、提示词、Desktop Compose/脚本/示例配置、两个实际使用的 Dockerfile、Hermes 启动钩子、依赖清单与当前运行入口 HTML，共 57 个文件；明确排除运行数据、`.env`、归档、PPT、历史输出/日志、测试脚本、Qoder Skill、服务器版和离线镜像。Python 编译、前端 JS 语法和 Compose config 均通过。本地提交为 `dad3bd9`；SSH-over-443 两次推送都在 GitHub 密钥交换阶段被本地网络关闭，因此推送待网络恢复后从 `/home/dev/projects/preview-proj-desktop-edition` 执行 `git push -u origin desktop-edition`。详见 `logs/desktop_edition_branch_20260719.md`。

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-REPO-01` 完成。用户要求在项目测试运行期间仅进行文件整理。已先通过在线 Desktop backend/Hermes 容器挂载确认，当前有效运行目录仅为 `deploy/desktop/runtime/`，因此未移动、未修改、未重启该目录及服务。根目录历史 `data/`、UUID 任务成果、调试日志、旧 Desktop/Server smoke runtime、路演/PPT/竞赛材料、PPT 生成脚本和历史生成包均已转入忽略 Git 与 Docker 的 `archive/`；需求、方案、运维/安装手册、开发经验和非运行原型按用途转入 `docs/`，当前运行入口 `环评前期研判AI助手.html` 保持根目录原位。`outputs/` 仅保留实施/验收/沙箱设计文档，`logs/` 仅保留持久工程记录。归档边界和清单见 `logs/repository_cleanup_20260719.md`。

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-FS-01` 完成。用户在 `HB-PT-000` 结果中看到 `File-mutation verifier` 告警。根因是官方 Hermes 镜像环境变量 `HERMES_WRITE_SAFE_ROOT=/opt/data` 仅允许 `write_file` 写入 Controller 自身状态目录，而后端提示词要求 Agent 把节点成果写入单独挂载的 `/eia/outputs/<task_id>`；目录物理权限正常，但被 Hermes 路径安全校验拒绝。共享 Desktop/Server Compose 现将白名单限制性扩展为 `/opt/data:/eia/outputs`，没有开放项目资料或其他宿主路径；启动钩子同时将 Desktop local terminal 使用的 `/workspace` 赋予 Hermes 运行 UID/GID，修复过程文件 `mkdir` 的 Permission denied。服务已重建，进程实际白名单正确；真实 Agent `write_file` run `run_3117787a05054fc8bf519296b48448e2` 成功写入隔离诊断成果并返回 `DONE`，新日志无写入/权限告警。历史节点结果未自动改写，需从 `HB-PT-000` 重跑才会替换页面中的旧提示。详见 `logs/hermes_write_safe_root_20260719.md`。

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-LLM-02` 完成。按用户要求，模型配置收敛为唯一的 OpenAI-compatible 三字段：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。共享 Hermes 启动钩子、Desktop/Server Compose、Linux/Windows 启动校验、示例 `.env` 和交付文档均移除了 `LLM_PROVIDER`、`LLM_MODEL`、`LLM_BASE_URL`、`CUSTOM_BASE_URL`、`DEEPSEEK_API_KEY` 的模型配置路径；其余 Hermes 资源限制、超时与联网检索 Key 仍为独立的运维配置。实际 Desktop Hermes 进程和生成 `.env` 仅含三个 `OPENAI_*` 模型变量，生成配置为 `custom:eia-managed`、`https://api.aiboys.xyz/v1`；真实 Agent run `run_7c2ed2c4eb024c658752aa141cb10ff3` 已 `completed`，输出 `OK`。用户当前只需在 `deploy/desktop/.env` 填写这三个字段；服务已重建并健康。实现提交 `8570440` 已推送至 `main`。

- 2026-07-19 Asia/Shanghai: `MAINTENANCE-LLM-01` 完成。用户质疑新单机版是否实际取用了错误模型 Key；已以脱敏长度/SHA-256 比对证明 `deploy/desktop/.env`、Compose 容器、Hermes 实际 Gateway 进程和 Hermes 生成 `.env` 的 `OPENAI_API_KEY` 完全一致，未发生宿主机环境变量覆盖、截断或替换。进一步发现 Hermes 0.18.2 对非 `openai.com` 的裸 `provider=custom` 采用防凭据泄漏策略：Agent `/v1/runs` 不自动向自定义域名发送 `OPENAI_API_KEY`，导致 401；同时高优先级 `LLM_BASE_URL=https://api.aiboys.xyz` 覆盖了 `CUSTOM_BASE_URL=.../v1`，使 SDK 实际请求缺少 `/v1` 并收到 HTTP 200 空 SSE 流。共享 Hermes 启动钩子现将 custom provider 声明为 Hermes 原生 `custom:eia-managed`，通过 `key_env: OPENAI_API_KEY` 取密钥（不写入 config.yaml），并将 OpenAI-compatible 基地址规范化为 `/v1`。完整 `/v1/runs` Agent 验证 `run_8e7783ebdf974e1db5188d2829eb1afc` 已 `completed`，输出 `OK`，输入/输出 token 为 `16778/25`；Desktop backend/Hermes 健康检查均通过。详见 `logs/hermes_custom_provider_20260719.md`；旧失败任务保持未自动续跑。

- 2026-07-19 Asia/Shanghai: 运行诊断完成，未修改或重启在线服务。任务 `90510bf2-b7b7-4956-857b-a0a3a6b8566b` 的 `FILE-VALIDATION` 已完成；`PREP-INGEST` run `run_f0f4c8844455405e85287c461eb95ac5` 在第六次模型续写后连续三次收到上游 `HTTP 502: Upstream request failed` 并失败。当前实际运行的是历史 `eia-ai-backend:latest -> host.docker.internal:8642 -> 宿主 Hermes custom/grok-4.5`，不是新交付的 `deploy/desktop/` Compose。Gateway `/health` 正常，最小 `/v1/chat/completions` 请求返回 HTTP 200/OK，说明 Key/网关/模型服务不是全局不可用；502 为该大工具上下文的上游请求失败。任务同时暴露历史 Docker terminal 的 `vision_analyze` 读取 `/workspace/prep_ingest/pages/*.png` 路径失败，该路径不可被宿主 Hermes Controller 读取。详见 `logs/prep_ingest_502_20260719.md`；建议后续切换到新单机版受控视觉缓存配置并使用部署 `.env` 中指定的模型。

- 2026-07-19 Asia/Shanghai: `DUAL-05` 至 `DUAL-07` 完成。Python、Hermes、Caddy、备份 Alpine 镜像均固定到已验证 digest；根目录旧的“宿主 Hermes + 后端容器”Compose 入口已移除，快捷脚本统一转发新单机版，服务器版仅从 `deploy/server/` 启动。新增 `deploy/images.manifest`、离线镜像导入/导出脚本和双版本交付入口文档；已实生成并校验忽略 Git 的离线镜像包 `deploy/image-bundles/eia-ai-images-0.2.0.tar`（约 1.8 GB）。桌面版和服务器版完整 Compose 烟测均再次通过；服务器版未认证为 401、认证反代 `/api/ready` 成功，backend/Hermes 无主机端口。两版本备份都实测排除 Hermes `.env`/`auth.json` 且将归档文件归还给部署 UID/GID。最终验收记录见 `outputs/双版本系统验收记录.md`；交付提交 `5086152` 已通过 GitHub SSH-over-443 推送至 `wangjunhui-wjh/preview-proj` 的 `main`。后续从 `MAINTENANCE_or_next_release` 继续。

- 2026-07-19 Asia/Shanghai: `DUAL-03`、`DUAL-04` 完成。单机版新增 `deploy/desktop/`，全容器运行 backend 和 Hermes local terminal，端口严格绑定 `127.0.0.1`，支持 Linux/macOS/Windows 启停、日志、无密钥备份；完整 Compose smoke 通过，backend/Hermes 健康且 Hermes 非 root 用户可访问持久工作目录。服务器版新增 `deploy/server/`，由 Caddy 提供 HTTPS/Basic Auth，backend 与 Hermes 不发布主机端口；Hermes Controller 使用官方 s6 基础镜像衍生运行时和原生 Docker terminal，Controller 与 Docker daemon 使用同一绝对 host path，工具容器无 Docker socket/模型密钥且项目输入只读。完整服务器 Compose smoke 通过：未认证 401、认证反代 `/api/ready` 成功、Docker socket 权限和工具容器隔离均已实测。临时 smoke 栈均已停止。下一步执行 `DUAL-05` 运维、安全与离线交付硬化。

- 2026-07-19 Asia/Shanghai: `DUAL-02` 完成。后端新增部署版本、CORS、Agent/输出/视觉缓存路径和启动孤立任务恢复配置；启动时会把遗留 `running` 任务安全恢复为 `paused`。视觉提示词已建立沙箱路径与 Hermes Controller 可见路径的受控交接。后端依赖锁定，文档工具镜像改为不夹带业务代码的独立镜像 `eia-ai-hermes-tools:0.2.0`，实建后通过 PDF/Office/OCR/Node/FFmpeg/Python 文档栈与隔离检查。Python、前端 JavaScript、Shell、Dockerfile 和孤立任务恢复 smoke 均通过。Git 远端按用户最新要求切换为全新仓库 `wangjunhui-wjh/preview-proj`，旧仓库不再使用。下一步实施 `DUAL-03` 单机版。

- 2026-07-19 Asia/Shanghai: `DUAL-01` 完成。用户要求在不重复开发 Hermes 已有 Agent 能力的前提下，同时完成单机版和私有化服务器版。已核对本机 Hermes 0.18.0 文档/源码，确定复用 Runs/SSE/stop、视觉、Web、审批、local/Docker terminal、task-id 容器和资源限制；制定双版本架构、既有隐患处置、七阶段实施计划和逐阶段验收标准。服务器版限定为私有化单租户，不虚构多租户 SaaS 能力。下一步进入 `DUAL-02` 共享运行基线加固。

- 2026-07-18 18:35 Asia/Shanghai: 用户确认采用简化架构：保留当前 Hermes API Server，使用一个共享持久 Docker terminal sandbox，不建设任务级 worker 或 Hermes API 扩展。已完成静态代码改造：新增 `Dockerfile.hermes-tools`；后端 `HermesClient` 支持 `session_id`；Agent 输入由宿主机绝对路径改为 `/eia/workspaces/<task_id>`；新增 `/eia/outputs/<task_id>` 成果路径及后端采集回退；移除仅为规避 host-local 审批而加入的脚本/命令限制。尚未构建工具镜像，尚未修改 `~/.hermes/config.yaml`，尚未重启 Hermes 或后端。详细变更、下一步和回滚点见 `logs/hermes_docker_terminal_20260718.md`。

- 2026-07-18 18:42 Asia/Shanghai: 工具镜像首次构建在 `deb.debian.org` 包索引下载阶段无进展，已停止两个仅属于本次构建的 Docker build 进程；未生成镜像，在线服务未受影响。验证清华、阿里云、腾讯云 Debian `trixie` 镜像均可访问（HTTP 200），已将 `Dockerfile.hermes-tools` 默认 apt/PyPI 源切换为清华，且保留 `APT_MIRROR`、`PIP_INDEX_URL` 构建参数可覆盖。下一步用国内源重新构建并验收镜像。

- 2026-07-18 18:45 Asia/Shanghai: 已使用清华镜像成功构建并验收 `eia-ai-hermes-tools:latest`（约 550 MB）。Poppler、Tesseract、LibreOffice、Node/npm、FFmpeg 及 Python 文档/OCR 库检查均通过；工具容器没有 Docker socket、宿主机 `.env` 或项目数据挂载。镜像基于现有后端镜像，因此含静态应用代码但不含运行数据、上传资料和密钥。下一步备份并切换 Hermes terminal 配置，再重启网关。

- 2026-07-18 18:47 Asia/Shanghai: 已创建并校验 Hermes 配置备份 `~/.hermes/config.yaml.bak-20260718-hermes-docker-terminal`（与修改前 SHA-256 一致）；已将 `~/.hermes/config.yaml` 的 terminal 切换为 Docker、`/workspace`、`eia-ai-hermes-tools:latest`、只读 `/eia/workspaces` 与可写 `/eia/outputs` 挂载、900 秒命令超时和持久容器，并设定 Docker 环境的 `approvals.mode: off`。尚未重启网关，下一步重启并验证生效配置和沙箱运行时。

- 2026-07-18 18:51 Asia/Shanghai: Hermes 网关已重启并健康，Docker 后端已重建；真实 run `run_d51b64e252fc400fa33563c2a62a6ba5` 完整验证 Docker terminal。Agent 在 `/workspace` 实际执行 `python3 -c`，未触发审批；确认 Poppler/Tesseract/LibreOffice/Node/FFmpeg、只读 `/eia/workspaces` 和可写 `/eia/outputs` 均可用，并写入 `outputs/hermes-docker-smoke/SMOKE_output.md`。发现工具镜像继承后端 HTTP health check，命令型容器会显示不健康但执行正常；已增加 `HEALTHCHECK NONE`，待重建工具镜像后执行真实 PDF 节点验收。

- 2026-07-18 18:55 Asia/Shanghai: 工具镜像已重新构建，当前 ID `sha256:ff6e7467dc46...`，Docker inspect 确认 `HEALTHCHECK NONE` 生效。为避免 Hermes 复用上一镜像版本创建的默认沙箱，下一步重启网关并清理仅属于本次 smoke test 的 Hermes 标记容器，然后对真实上传 PDF 执行 `PREP-INGEST` 验收。

- 2026-07-18 18:57 Asia/Shanghai: 已重启 `hermes-eia`，并仅清理两项来自上一镜像版本的 smoke-test Hermes 容器；Hermes `/health` 和后端 `/api/health` 均正常，当前没有复用旧 terminal sandbox。已确认任务 `e098c0e7-d05a-4282-89b8-2053ca4b822c` 的三份 PDF 已位于 `data/workspaces/<task_id>/project_files`，下一步仅执行一次 `PREP-INGEST` 真实资料读取节点，不会自动进入后续 HB 节点。

- 2026-07-18 19:11 Asia/Shanghai: `HERMES-DOCKER-01` 完成。真实 `PREP-INGEST` run `run_f999ef3f814f45d49db657d1d06f140e` 对三份 PDF 完成 14 次模型调用、13 轮工具执行，无 `approval.request`；Agent 在 Docker 内提取 PDF 文本/表格并用 Tesseract OCR 回退识别图片页，成果已由后端回收，任务正确暂停在 `HB-PT-000`。工具镜像默认清华 Debian/PyPI 源，构建无需梯子。当前已确认的后续项为 `HERMES-VISION-02`：`vision_analyze` 是 Controller 侧工具，不能读取 Docker `/workspace` 的渲染图，需要增加受控图片缓存交接并专项验收；该项不影响已完成的 Docker、OCR、结果回收和无人值守验收。

- 2026-07-18 18:29 Asia/Shanghai: 用户要求按 `人工智能大赛报名表.docx` 及备注图片修订 PPT，并限定报名表只能提供痛点背景支持。已先审阅备注图：其要求将行业难点与痛点集中为单页、突出“经验难以规模复制、数据孤立”，并用“智能体”描述解决方案。已将第 2 页改为“项目背景与行业痛点”，新增“经验难以规模复制、资料与依据分散、数据与过程孤立、风险常在后段暴露”四项，并明确不引入市场规模、政策扶持、预期效果、计划或任何量化结论；第 1、6、7 页相关措辞统一为“智能体协同/智能体任务状态”。报名表备注图不嵌入 PPT。已重新生成 PPTX 与 8 页预览，人工检查第 1、2、6 页版式；下一步等待业务审阅。

- 2026-07-18 18:13 Asia/Shanghai: 完成 Hermes 服务模式、Docker terminal sandbox、审批、API Server 和文件交接边界调研。官方文档与本机 Hermes 源码均确认：Hermes 原生提供 Docker 终端沙箱、资源限制、SSE、run stop 和审批响应；当前 `/v1/runs` 不支持文档上传或 run 级工作区/volume 配置，内部 task override 未经公共 API 暴露。当前 PREP-INGEST 失败根因已由事件日志确认，为 `python3 -c` 命中本地终端审批规则，发生在 PDF 读取前，且后端当前收到审批事件会停止 run。建议采用“专用 Hermes profile + 原生 Docker terminal backend + Hermes documents cache 资料交接”的阶段 A；不采用宿主机关闭审批、仅容器化 controller 或后端手写工具编排。调研与分阶段验收已写入 `outputs/Hermes服务模式沙箱调研与改造建议.md`；未改 Hermes 配置、未重启服务、未调用模型。

- 2026-07-18 18:07 Asia/Shanghai: 完成 PPT 路演汇报制作与本机验收。交付 `outputs/AI辅助环评前期研判系统_内部申请汇报.pptx`（8 页可编辑）、`outputs/PPT路演汇报预览/slide-01.png` 至 `slide-08.png`（每页 1920x1080）、总览 `montage.png`、浏览器预览 `index.html`、素材清单和可复现生成脚本。第 6 页仅使用本机空白任务工作台的脱敏截图；其余内容为可编辑文本和图形。已校验 PPTX 压缩包/OOXML、8 页数、无原模板品牌或排污许可文案/API Key 字符串、仅 1 张嵌入媒体、所有 PNG 非空。未安装 Office/LibreOffice，无法进行 Office/WPS 实机渲染，已以 Chromium 预览验收；下一步为业务方在目标演示设备审阅。

- 2026-07-18 17:52 Asia/Shanghai: 用户要求完成大纲审核、逐页制作计划并分步实施。已审核 `outputs/PPT路演汇报制作计划.md`：保留 8 页业务优先叙事，补充事实基线、逐页画面/文案/来源/讲述时长/验收要求和分步实施计划；明确原 PPT 模板主体是扁平图片，改为继承视觉语言并生成全新可编辑页面。当前进入 `PPT-PLAN-02`，下一步采集脱敏系统截图后生成 PPT；未修改业务代码、未调用模型。

- 2026-07-18 17:35 Asia/Shanghai: 根据用户对汇报人业务背景的说明，重构 PPT 待审核计划为业务优先叙事：8 页、6-8 分钟，突出提示词体系和环评前期研判方法如何被产品化、依据如何可追溯、人工如何复核；底层技术只保留 1 页业务化“产品运行保障”，不在主 Deck 展开技术栈。已更新 `outputs/PPT路演汇报制作计划.md`，尚未开始拆分或制作 PPT。
- 2026-07-18 17:32 Asia/Shanghai: 修复 Hermes 网关重启后的内部鉴权失配。确认宿主机 `~/.hermes/.env` 的 `API_SERVER_KEY` 与 Docker 后端旧 `HERMES_API_KEY` 不一致，导致 `/v1/runs` 返回 401；已按宿主机当前网关密钥重建后端容器，容器内鉴权探针返回 400（请求体不完整）而非 401，说明认证通过；后端与 Hermes 健康检查正常。`start.sh` 已增加默认宿主机 Hermes 模式下向项目 `.env` 同步网关密钥的逻辑，项目 `.env` 权限为 600。任务 `e098c0e7-d05a-4282-89b8-2053ca4b822c` 已复位为 `created`，下一节点 `PREP-INGEST`；复位未调用模型。
- 2026-07-18 17:20 Asia/Shanghai: 已审阅工作区模板 `排污许可AI 智脑二期申请汇报.pptx`（16:9、8 页、蓝绿政务科技风、全页视觉稿为主），制定 AI 辅助环评前期研判系统路演汇报的 10 页建议页纲、制作阶段、事实与视觉验收规则，写入 `outputs/PPT路演汇报制作计划.md`；按用户要求停在审核阶段，尚未拆分实施任务或生成 PPT。
- 2026-07-18 17:08 Asia/Shanghai: 修复旧任务切换至 Docker 后无法读取宿主机绝对上传路径的问题：`backend/file_store.py` 会按任务 ID 和文件名重映射到容器挂载的 `/app/data/uploads`，并可回退到已存在的工作区副本；`backend/main.py` 失败时会生成可见 Markdown 错误结果。原型适配层和拆分前端均改为将 `result.status=failed` 作为失败处理，避免误报“分析完成”；HTML 适配脚本版本已更新以规避浏览器缓存。后端镜像重建、健康检查及容器内旧 PDF 工作区准备验证通过。任务 `e778d84a-8d17-43d9-a3be-0aca459ed05c` 已通过 rerun API 复位为 `created`，下一节点 `HB-PT-004`；复位过程未调用大模型。
- 2026-07-18 16:44 Asia/Shanghai: 重启宿主机 Hermes tmux 会话 `hermes-eia`；`/health` 正常，Docker 后端 `http://127.0.0.1:8501/api/health` 返回后端和 Hermes 均 `ok`；真实上游烟测 `/v1/chat/completions` 返回 `OK`；Hermes 当前生效配置为 `provider=custom`、`model=gpt-5.6-luna`、`base_url=https://api.aiboys.xyz/v1`，对后端暴露模型名仍为 `hermes-agent`。
- 2026-07-03 00:22 Asia/Shanghai: 技术路线重置为 Hermes Agent + LangGraph + HTML 原型；开始清理旧 Streamlit/手写工具版本。
- 2026-07-03 00:25 Asia/Shanghai: 完成旧 Streamlit/手写工具代码、旧 smoke 脚本、历史 logs/outputs 清理；提示词迁移到 `prompts/`；新增 `实施方案.md`；下一步进入 Hermes 单节点 POC。
- 2026-07-03 00:34 Asia/Shanghai: 确认 Hermes 支持自定义 OpenAI-compatible 模型 API，已写入 `实施方案.md` 第 8.1 节；下一步仍为 `POC-01`。
- 2026-07-03 00:39 Asia/Shanghai: 确认 Hermes CLI 可通过 gateway/API Server 方式服务化运行；`实施方案.md` 已补充 `5.1 Hermes 服务化运行方式`；下一步仍为 `POC-01`。
- 2026-07-03 00:47 Asia/Shanghai: 用户要求暂不开发系统，改为完成前置工作；当前阶段切换为 `PREP-01`，业务 POC 延后。
- 2026-07-03 01:08 Asia/Shanghai: Hermes 完整安装完成；API Server 通过 `tmux` 会话 `hermes-eia` 运行；修正 custom `base_url` 为 `https://api.aiboys.xyz/v1`；`/health`、`/v1/chat/completions`、`/v1/runs`、SSE 事件流和 `web_search` 工具烟测通过；新增 `Hermes服务运行手册.md`；业务开发继续暂停，等待用户恢复。
- 2026-07-03 09:15 Asia/Shanghai: `实施方案.md` 已补充数据存储、政策知识库、候选依据库、Web Search 发现政策文件后的候选入库/校验/正式入库流程；业务开发仍暂停。
- 2026-07-03 09:42 Asia/Shanghai: 用户要求开始实施并开启多 agent；已启动 workflow_planner 和 frontend_explorer 子 agent；当前进入 `POC-01`，主线程开始后端基础实现和集成。
- 2026-07-03 09:56 Asia/Shanghai: 完成 Hermes 单节点和 FastAPI/LangGraph 最小后端纵切；新增 `backend/` 服务、知识候选库接口、上传/任务/事件/输出 API；使用任务 `697bd903-c40f-4e41-8ea3-0268a040d0c7` 真实执行 `HB-PT-000` 成功，产物写入 `outputs/697bd903-c40f-4e41-8ea3-0268a040d0c7/`，事件写入 `logs/task_697bd903-c40f-4e41-8ea3-0268a040d0c7.events.jsonl`；后端服务运行在 `http://127.0.0.1:8501`，下一步进入 HTML 原型接后端。
- 2026-07-03 10:08 Asia/Shanghai: 完成 `环评前期研判AI助手.html` 最小后端接入；前端可创建任务、上传/粘贴项目资料、触发 `HB-PT-000`、显示 SSE 事件和结果、刷新后按 `task_id` 恢复；禁用前端直连模型和前端搜索 API 配置，web_search 由后端 Agent 自主组织；FastAPI 新增 `/` 和 `/app` 托管 HTML；验证 `http://127.0.0.1:8501/`、`/api/health`、任务恢复和事件流可用。
- 2026-07-03 10:11 Asia/Shanghai: 后端节点执行器已通用化，接入现有提示词节点 `HB-PT-000/001/002/003/005/007/010/011`，缺失提示词节点暂不伪实现；前端允许按 `next_node` 继续执行已接入节点；使用任务 `697bd903-c40f-4e41-8ea3-0268a040d0c7` 真实续跑 `HB-PT-001` 成功，状态停在 `HB-PT-002`，产物写入 `outputs/697bd903-c40f-4e41-8ea3-0268a040d0c7/HB-PT-001.*`。
- 2026-07-03 10:18 Asia/Shanghai: 复盘 PDF 任务 `c2d6b232-66ea-4845-8426-e4b11820d4fe`，确认失败原因不是 API 未请求，而是 Hermes 在 OCR 临时目录清理命令上触发 `approval.request`；已修改 `backend/main.py`，节点输入改为提供工作区绝对文件路径，并加入无人值守禁止人工审批/高风险命令约束；后端事件循环现在遇到 `approval.request`、`run.failed`、`run.cancelled` 会明确失败并停止，不再让前端一直等待；`python -m compileall backend` 通过。
- 2026-07-03 10:19 Asia/Shanghai: 已重启 FastAPI 后端并通过 `/api/health` 验证，Hermes API Server 仍在线；确认没有遗留卡住的 `/step` 测试进程；下一步重新执行 PDF 上传链路验证。
- 2026-07-03 10:34 Asia/Shanghai: 根据并行 reviewer agent 结果继续加固：新增 `active_hermes_run_id`，运行中暂停会请求停止 Hermes run；Hermes 调用异常会写入 `node_failed` 并清理任务状态；失败/取消时保留 `message.delta` 流式输出；工作区项目文件改为 `{file_id}_{safe_name}` 唯一路径并在节点输入中给出绝对 `workspace_path`；`python -m compileall backend` 通过。
- 2026-07-03 10:44 Asia/Shanghai: 新建 PDF 复测任务 `2efcb0f8-b3ec-45bb-8e5c-a97449cd32aa` 并执行 `HB-PT-000` 成功；Hermes 实际完成扫描 PDF 识别链路：确认 PDF 共 6 页、文本层为空、每页为扫描图片，使用 OCR 提取出“盈科杯/青年创新创意大赛”等内容；节点结果写入 `outputs/2efcb0f8-b3ec-45bb-8e5c-a97449cd32aa/HB-PT-000.*`，状态停在 `HB-PT-001`；未再次出现 `approval.request` 卡死。
- 2026-07-03 10:45 Asia/Shanghai: 优化实时事件写入：`message.delta` 改为小段聚合后写入 `node_output_partial`，避免扫描 PDF 节点逐 token 生成数千条日志；节点提示词新增“不要粘贴大段 OCR 原文、JSON 不重复 Markdown 全文”的输出约束；`python -m compileall backend` 通过。
- 2026-07-03 10:48 Asia/Shanghai: 暂停验证任务 `d5dcbd5d-52e9-4f0b-95f3-e281b6f63dd6` 暴露竞态：`/pause` 在保存 `pause_requested` 前先调用 Hermes stop，导致 `run.cancelled` 被识别为失败；已修改 `/api/tasks/{task_id}/pause` 为先保存暂停标记再请求 stop；`python -m compileall backend` 通过，待重启后复测。
- 2026-07-03 10:52 Asia/Shanghai: 暂停二次验证任务 `b6ad603a-28da-4830-9254-3d75f1ae7072` 通过；`/pause` 返回 Hermes `stop_result`，`run.cancelled` 被映射为 `node_paused`，任务最终状态为 `paused`，`next_node` 保持 `HB-PT-000`，并保留暂停前的 partial markdown/tool_trace；后端与 Hermes 健康检查通过，没有遗留 `/step` 测试进程。
- 2026-07-03 10:54 Asia/Shanghai: 更新 `README.md` 和 `实施方案.md`，同步当前真实能力：已接入多个 HB 节点、扫描 PDF/OCR 已验证、运行中暂停会停止当前 Hermes run、实时事件小段聚合、缺失提示词节点不伪实现。
- 2026-07-03 10:59 Asia/Shanghai: 新建直接图片验证任务 `a9648f03-eb2d-458d-af06-2989b85d1540`，上传 `page-1.png` 并执行 `HB-PT-000` 成功；Hermes 工具轨迹包含 `vision_analyze`，日志显示图片被读取、base64 转换并由视觉模型识别，输出识别到“盈科杯/青年创新创意大赛”等可见文字；结果写入 `outputs/a9648f03-eb2d-458d-af06-2989b85d1540/HB-PT-000.*`，状态停在 `HB-PT-001`。
- 2026-07-03 11:09 Asia/Shanghai: 新建 websearch 验证任务 `0154c84e-6de8-4b9f-b328-cee7a6542db0` 并执行 `HB-PT-003`；Hermes 实际调用 `web_search` 多次且成功返回，随后因尝试 `pdftotext | python3` 触发 `approval.request`，后端按无人值守策略 fail-fast、请求停止 Hermes run、写入失败状态和部分输出；已补强节点输入约束，明确禁止把网页/PDF/OCR/curl/pdftotext 输出管道给解释器，并要求 web_extract 失败时退回到候选 URL 与人工核实说明；同时补充最终 Markdown URL 候选依据引用写入逻辑；后端编译通过并重启到会话 `7479`，健康检查通过；下一步修复 URL 提取正则并复测依据落盘。
- 2026-07-03 11:17 Asia/Shanghai: 修复 `_extract_urls()` 正则错误，普通 URL、政府页面 URL、政策 PDF URL、中文句末标点和括号包裹 URL 的样例均能正确提取；`python -m compileall backend` 通过；后端重启到会话 `31380`，`/api/health` 显示后端和 Hermes 正常；下一步复测 HB-PT-003 的无人值守 websearch 与候选依据落盘。
- 2026-07-03 11:19 Asia/Shanghai: 修复节点收尾状态合并逻辑：节点结束时重新读取磁盘最新 task，合并 `module_results`、`candidate_doc_ids` 和任务级 `evidence_refs`，避免运行中暂停请求被旧内存对象覆盖；`python -m compileall backend` 通过；后端重启到会话 `60958`，健康检查通过；下一步执行 HB-PT-003 复测。
- 2026-07-03 11:41 Asia/Shanghai: HB-PT-003 websearch 复测任务 `c32fc4f1-4911-41e2-a503-941a76e57ef1` 已完成，Hermes 实际调用 `web_search`、`web_extract`、浏览器和安全终端工具，未再触发 `approval.request`，产物写入 `outputs/c32fc4f1-4911-41e2-a503-941a76e57ef1/`；修复 URL 提取函数，支持把 `URL:...；附件URL:...` 拆成独立依据；修复该任务已落盘的错误组合 URL，错误候选标记为 `rejected`，当前节点和任务 evidence refs 为 3 条真实 URL；新增知识库 URL 候选复用逻辑，避免同 URL 重跑膨胀；`python -m compileall backend` 和 `/api/health` 通过，后端重启到会话 `39515`。
- 2026-07-03 11:46 Asia/Shanghai: 加固 evidence 链路：节点收尾会同时扫描 Markdown 和结构化 JSON 中的 URL/附件 URL，保留结构化字段路径和政策标题；候选依据优先走 `ingest_url_candidate()` 抓取网页/附件快照，写入 `local_path`、`text_path`、`file_hash`，失败时才降级为仅 URL 候选；知识库层新增 URL 合法性校验，拒绝含 `附件URL`、多个 scheme 或空白的异常 URL；`rerun` 在任务 running 时返回 409，节点收尾不再批量覆盖旧 `module_results`；已为任务 `c32fc4f1-4911-41e2-a503-941a76e57ef1` 的 3 条候选依据补抓本地快照和文本；`python -m compileall backend` 与 `/api/health` 通过，后端重启到会话 `6881`。
- 2026-07-03 11:55 Asia/Shanghai: `/api/tasks/{task_id}/run` 已改为真正后台连续执行，不再只是单步别名；连续执行期间任务保持 `running` 以维持 SSE，用户暂停会停止当前 Hermes run 或停在下一节点前；用任务 `646ab758-aac3-4e81-88c0-5afa14d4a003` 验证 `/run` 后立即 `/pause`，最终状态 `paused`、`next_node=HB-PT-000`、`active_hermes_run_id=null`，无遗留请求；前端新增“连续执行”按钮、节点依据记录展示、任务 evidence 状态同步，并修复图片项目资料上传白名单，图片进入上传队列后由后端 Agent 识别；`README.md` 和 `实施方案.md` 已同步当前能力；前端 JS 语法检查、`python -m compileall backend`、`/api/health` 均通过，后端运行在会话 `57233`。
- 2026-07-03 11:56 Asia/Shanghai: POC-04 验收完成；下一阶段进入 `POC-05`：候选依据确认/正式入库、全流程连续执行到综合报告和交叉核查、checkpoint 恢复验收脚本。
- 2026-07-03 13:38 Asia/Shanghai: 用户要求继续；按恢复协议读取 `.state/progress.md`、最近 logs/outputs/data 状态和服务健康；确认后端 `http://127.0.0.1:8501`、Hermes `http://127.0.0.1:8642` 正常；启动 `POC-05`，并开启两个只读子 agent 分别审查候选依据确认 UI/API 与恢复验收脚本边界。
- 2026-07-03 13:44 Asia/Shanghai: 完成候选依据人工确认/正式入库最小闭环：`KnowledgeStore.review_document()` 支持 `verified/verified_candidate/rejected/deprecated`、validity、审核人、备注和审核历史；确认正式时 web 候选升级为 `official_url`；FastAPI 新增 `GET /api/knowledge/documents/{doc_id}` 并增强 `/verify` 404/参数校验；前端参考资料库页新增政策依据库卡片，支持刷新、手动抓取候选 URL、确认为正式、待复核、驳回、标记废止；已通过 API 将 `e48347d0-1f0a-4925-bc9c-7614a010661d` 国家发改委政策候选确认为 `verified/effective/official_url`，保留快照、hash 和审核记录；`python -m compileall backend`、前端 JS 语法检查和 `/api/health` 通过，后端重启到会话 `89747`。
- 2026-07-03 13:53 Asia/Shanghai: 补齐正式依据参与后续研判闭环：新增 `_knowledge_evidence_context()`，节点提示词会注入本任务已选择的 `verified` 政策依据、URL、hash、本地快照、抽取文本摘要；新增 `GET /api/tasks/{task_id}/knowledge-candidates` 和 `POST /api/tasks/{task_id}/knowledge-documents`，支持将正式政策依据加入/移出任务；前端政策依据库卡片新增“用于本任务/移出任务”；已将 `e48347d0-1f0a-4925-bc9c-7614a010661d` 加入任务 `c32fc4f1-4911-41e2-a503-941a76e57ef1`，并验证后续节点 evidence_context 可读取；同时优化知识库文本抽取，HTML 去标签、DOCX 从正文 XML 提取，已重新抽取现有 3 条政策候选文本；`python -m compileall backend` 与前端 JS 语法检查通过，后端重启到会话 `81060`。
- 2026-07-03 14:11 Asia/Shanghai: POC-05 验收收尾完成：新增 `scripts/fake_hermes_server.py`、`scripts/poc05_acceptance.sh`、`scripts/poc05_pause_resume_rerun.sh` 和 `scripts/recovery_snapshot.py`；fake Hermes 全流程连续执行脚本通过，暂停/恢复/rerun 脚本通过，`GET /api/tasks/{task_id}/manifest` 与 `POST /api/admin/recover-running-tasks` 验证通过；当前后端健康检查正常，Hermes 健康检查正常，没有遗留 `/step` 或 `/run` 请求；上一轮两个只读子 agent 已关闭；下一步进入 `POC-06`，把外层顺序循环改造成真正 LangGraph checkpoint 运行层。
- 2026-07-03 14:35 Asia/Shanghai: POC-06 完成：`backend/graph.py` 已替换为真实 `EiaGraphRuntime`，用 LangGraph StateGraph + SQLite checkpointer 管理外层 `step/run` 节点推进；`backend/main.py` 的同步单步和后台连续执行均改为调用 graph runtime，create/run/resume/rerun/recover 控制路径会同步 graph checkpoint；新增 `LANGGRAPH_CHECKPOINT_DB=data/langgraph_checkpoints.sqlite`，manifest 和恢复脚本可查看 checkpoint 摘要；fake Hermes 全流程脚本、暂停/恢复/rerun 脚本、后端编译、脚本语法、前端 JS 语法均通过；正式后端已重启到 `http://127.0.0.1:8501`，smoke 任务 `0a3d55bc-a512-4736-a61b-b1a012cb11eb` 验证创建任务即写入 graph checkpoint；下一步进入 `POC-07` 真实项目全流程长跑与硬化。
- 2026-07-03 14:49 Asia/Shanghai: 根据 POC-06 reviewer 结果完成运行层硬化：修复 `create_run` 返回前后暂停请求可能被旧 task 覆盖的问题；暂停当前节点时不再把半成品写入候选依据或 `module_results`，且后续提示词只注入 `completed` 模块；`run.completed` 事件现在会立即结束 SSE 循环；终态 `completed/failed` 任务的 pause 会被忽略，不再回退；rerun 会清理 `pause_requested/current_node/active_hermes_run_id`；orphan recovery 会尝试停止遗留 Hermes run；事件日志、checkpoint 查询和 recovery snapshot 增加坏数据兜底；新增 `scripts/poc06_edge_cases.sh` 覆盖 completed-open SSE、create_run 延迟暂停、terminal pause、paused 后 rerun 再 step；`scripts/poc06_edge_cases.sh`、`scripts/poc05_acceptance.sh`、`scripts/poc05_pause_resume_rerun.sh` 均通过。
- 2026-07-03 14:51 Asia/Shanghai: 正式后端已重启加载 POC-06 硬化代码，运行在 `http://127.0.0.1:8501`，pid `359961`；Hermes `http://127.0.0.1:8642` 健康检查正常；smoke 任务 `9aac98f4-d03b-4319-9f15-3a5e698b8739` 验证任务创建即写入 `data/langgraph_checkpoints.sqlite`；`scripts/recovery_snapshot.py` 可显示 checkpoint 表计数；确认没有遗留 `/step` 或 `/run` 请求。
- 2026-07-03 14:53 Asia/Shanghai: `README.md` 与 `实施方案.md` 已同步 POC-06 边界验收脚本和 `LANGGRAPH_CHECKPOINT_DB` 说明；最终静态检查通过：`python -m compileall backend`、脚本 `py_compile`、`bash -n`；后端与 Hermes 健康检查通过。
- 2026-07-03 14:53 Asia/Shanghai: 开始 POC-07 真实项目长跑准备；选择水性涂料项目描述作为完整流程基准，计划新建任务后通过 `/api/tasks/{task_id}/run` 连续执行并监控到终态。
- 2026-07-03 14:54 Asia/Shanghai: POC-07 真实项目长跑任务已创建并启动，task_id=`615772df-7551-4287-a136-701a1ac9cb03`，初始状态 `running`，next_node=`HB-PT-000`；请求记录写入 `logs/poc07_real_project_task_*.json` 与 `logs/poc07_real_project_run_*.json`。
- 2026-07-03 15:00 Asia/Shanghai: POC-07 真实长跑任务 `615772df-7551-4287-a136-701a1ac9cb03` 已完成 `HB-PT-000`，自动进入 `HB-PT-001`，active Hermes run=`run_3264b8c845ff4d92a2f9d3aad6bea06a`；`HB-PT-000` 输出偏长，后续需评估节点输出压缩。
- 2026-07-03 15:04 Asia/Shanghai: POC-07 真实长跑任务已完成 `HB-PT-001` 并自动进入 `HB-PT-002`，active Hermes run=`run_52737f3906ac40b6910d99c7f2a6ba18`；`HB-PT-001` 实际调用多次 `web_search/web_extract`，已暴露节点 Markdown 与 JSON 重复输出偏长的问题，后续需收紧节点输出预算。
- 2026-07-03 15:11 Asia/Shanghai: POC-07 真实长跑任务已完成 `HB-PT-002` 并自动进入 `HB-PT-003`，active Hermes run=`run_5923a4976c0c42d1b15fb622039d86b1`；`HB-PT-002` 实际访问并抽取生态环境部分类名录 PDF、上海市生态环境局审批目录页面，未触发 `approval.request`，输出倾向“报告表但存在报告书风险”。
- 2026-07-03 15:20 Asia/Shanghai: POC-07 真实长跑任务已完成 `HB-PT-003` 并自动进入 `HB-PT-005`，active Hermes run=`run_9decef0312eb4e2ebf74e50e18165348`；`HB-PT-003` 产生大量 `web_search` 事件并完成产业政策符合性初判，暴露政策原文获取质量与单节点搜索轮数上限需要硬化。
- 2026-07-03 15:26 Asia/Shanghai: POC-07 真实长跑任务已完成 `HB-PT-005` 并自动进入 `HB-PT-007`，active Hermes run=`run_c44f76666ad149ebb34051d82fb63da4`；`HB-PT-005` 主要结论为缺少具体地址/坐标/管控单元编码，生态环境分区管控符合性需人工核实。
- 2026-07-03 15:32 Asia/Shanghai: POC-07 真实长跑任务已完成 `HB-PT-007` 并自动进入 `HB-PT-010`，active Hermes run=`run_c29978b516e14cc589ec7d7a2695f424`；`HB-PT-007` 初判非典型“两高”，但化工项目属性、合规化工园区、危化品/MSDS、能耗和环境风险资料需要人工核实。
- 2026-07-03 15:38 Asia/Shanghai: POC-07 真实长跑任务已完成 `HB-PT-010` 并自动进入最终交叉核查 `HB-PT-011`，active Hermes run=`run_677b1cfbc2bb4b3c8767084289dde554`；综合报告建议“谨慎承接”，主要风险为报告书路径、产业政策原文、合规化工园区、三线一单单元、VOCs/危废/废水/环境风险资料不足。
- 2026-07-03 15:42 Asia/Shanghai: POC-07 真实长跑任务 `615772df-7551-4287-a136-701a1ac9cb03` 已完成，状态 `completed`，已完成节点 `HB-PT-000/001/002/003/005/007/010/011`；最终 `HB-PT-011` 发现“是否不涉及化学反应合成”表述强度不一致、未运行模块导致部分综合报告结论只能作为资料不足提示等问题；下一步检查 manifest、outputs、evidence 和 checkpoint。
- 2026-07-03 15:47 Asia/Shanghai: POC-07 验收完成：manifest 显示任务 `615772df-7551-4287-a136-701a1ac9cb03` 为 `completed`，8 个节点结果齐全，`outputs/615772df-7551-4287-a136-701a1ac9cb03/` 共 32 个产物，候选依据 24 条，graph checkpoint 为 `completed`；已根据长跑暴露问题加入节点工具预算、输出预算、JSON 去重约束，并在未显式选择知识库依据时自动注入最多 5 条 verified/effective 官方政策库依据；后端已重启到 pid `479865`，健康检查正常，无遗留 `/step` 或 `/run` 请求；下一步进入 `POC-08` 报告导出、前端结果查看与知识库治理。
- 2026-07-03 16:24 Asia/Shanghai: 按恢复协议读取 `.state/progress.md`、最近 `logs/`、`outputs/` 和后端健康状态；确认后端与 Hermes 在线，开始 `POC-08`，目标为报告/归档导出 API、前端结果查看增强、候选依据批处理审核和导出验收。
- 2026-07-03 16:36 Asia/Shanghai: POC-08 完成：后端新增 `GET /api/tasks/{task_id}/report.md`、`GET /api/tasks/{task_id}/export.zip`、`POST /api/knowledge/documents/batch-review`；前端新增报告/归档下载、节点 MD/JSON/tool_trace 下载、Manifest 打开、候选依据勾选与批量审核/加入任务，并修复任务刷新后旧结果和 liveOutput 遮挡正式结果的问题；政策 URL 入库新增标题、发布机关、文号、发布日期的保守抽取并写入知识库字段；新增 `scripts/poc08_export_smoke.sh`，已通过两次 fake Hermes 验收；真实 POC-07 任务报告与 ZIP 下载验证通过；后端已重启到 pid `586430`，健康检查正常，无遗留 `/step` 或 `/run` 请求。
- 2026-07-03 17:49 Asia/Shanghai: 用户确认第一步资料输入不应由后端/浏览器直接解析为项目事实；开始 POC-09，将流程调整为 `资料上传/粘贴 -> Agent 构建项目档案 -> HB-PT-000 完整性审查 -> 后续研判节点`。
- 2026-07-03 17:59 Asia/Shanghai: POC-09 完成：新增 `prompts/prep_ingest_project_dossier.txt` 和前置节点 `PREP-INGEST`，新任务默认 `next_node=PREP-INGEST`，流程变为 `PREP-INGEST -> HB-PT-000 -> HB-PT-001 -> ...`；后续节点的 `{project_text}`/`{project_profile}` 优先使用 PREP-INGEST 生成的项目档案；前端项目页新增“运行资料读取Agent”和项目档案结果区，上传文件只进入原始资料队列，不再由浏览器解析 PDF/DOCX/TXT 后自动填入项目简介；fake Hermes 和 `poc05/poc06/poc08` 验收脚本已同步并通过；README、实施方案、llm开发经验已更新；正式后端重启到 pid `765151`，健康检查正常，新建任务 smoke 返回 `next_node=PREP-INGEST`，无遗留 `/step` 或 `/run` 请求。
- 2026-07-03 18:07 Asia/Shanghai: 用户反馈前端上传文件后仍有直接识别文本表现；检查发现 HTML 中旧本地资料库解析逻辑仍包含 `parsePdf/parseDocx/readTextFile`，且 `handleLocalFiles()` 会误把本地资料库文件加入 `projectUploadFiles`；开始 POC-10，目标是彻底隔离项目资料上传路径和本地预览解析路径，并禁用 HTML 缓存。
- 2026-07-03 18:11 Asia/Shanghai: POC-10 完成：项目资料上传入口改为唯一 `handleProjectUploads()`，只加入原始资料队列，不调用任何浏览器解析；删除前端 `mammoth/pdf.js` 依赖和 `parsePdf/parseDocx/readTextFile` 函数；参考资料库文件上传也只记录元数据并提示未在前端解析正文，不再污染 `projectUploadFiles`；FastAPI `/` 和 `/app` 响应加 `Cache-Control: no-store` 并重启后端到 pid `787843`；验证服务端 HTML 已无 `mammoth/pdfjs/parsePdf/parseDocx/readTextFile/正在解析/已解析`，新建任务仍为 `next_node=PREP-INGEST`，健康检查正常，无遗留 `/step` 或 `/run` 请求。
- 2026-07-03 18:22 Asia/Shanghai: 确认 Hermes 0.18.0 本地代码包含 `codex_responses`/Responses API 适配路径，但当前 `~/.hermes/config.yaml` 为 `provider: custom`、`base_url: https://api.aiboys.xyz/v1`，运行日志显示实际内部请求为 `chat_completion_stream_request`；当前系统调用链是 FastAPI -> Hermes `/v1/runs` -> Hermes 内部 chat completions，不是直接 `/v1/responses`。
- 2026-07-03 18:39 Asia/Shanghai: POC-11 完成：`环评前期研判AI助手.html` 新增后端事件日志自动跟随到底部，鼠标悬停或手动上滚时暂停自动滚动；节点输出和 PREP-INGEST 项目档案改为 Word 风格文档视图渲染 Markdown 表格/标题/列表，并新增节点结果 `下载Word`；验证服务端 HTML 已返回新样式与脚本，`node` 静态解析通过，`/api/health` 正常；当前测试任务 `e778d84a-8d17-43d9-a3be-0aca459ed05c` 为 `paused`，下一节点 `HB-PT-003`，无活跃 Hermes run。
- 2026-07-03 18:49 Asia/Shanghai: POC-12 完成：确认用户所说“行业类别与环评类别”对应后端 `HB-PT-002`，当前测试任务 `e778d84a-8d17-43d9-a3be-0aca459ed05c` 已完成 `PREP-INGEST/HB-PT-000/HB-PT-001/HB-PT-002`，状态 `paused`，下一节点 `HB-PT-003`；修复前端任务刷新不回填历史事件的问题，`/api/tasks/{task_id}` 返回的后端事件会同步到事件日志，避免停留在旧的 `HB-PT-001 completed`；将原单文件 HTML 拆为 `环评前期研判AI助手.html` 入口、`frontend/app.css` 和 `frontend/app.js`；FastAPI 挂载 `/assets`；新增后台管理入口、`/api/admin/workflow/nodes` 和 `/api/admin/knowledge/review-history`，页面展示知识库管理、审核历史和节点接入状态；明确当前未接入节点为 `HB-PT-004/HB-PT-006/HB-PT-008/HB-PT-009`，按钮禁用并标记未接入；后端重启到 pid `872845`，`/api/health`、静态资源、后台管理接口和任务事件回填验证通过。
- 2026-07-03 18:58 Asia/Shanghai: POC-13 完成：按 HTML 原型提示词补齐后端 `HB-PT-004` 规划及规划环评、`HB-PT-006` 长江保护及岸线管控、`HB-PT-008` 行业环评审批原则、`HB-PT-009` 同类项目污染节点与治理措施借鉴四个提示词，并加入真实依据、资料不足和无人值守 Agent 约束；后端 `NODE_PROMPTS` 与 `NEXT_NODE` 路由改为 `PREP-INGEST -> HB-PT-000 -> ... -> HB-PT-011` 全节点顺序；前端取消 004/006/008/009 未接入标记并更新静态资源版本；综合报告提示词移除 MVP 未运行说明并加入 HB-PT-008/HB-PT-009 专章；README 和实施方案同步全节点接入状态；`python -m compileall backend`、`node` 前端语法检查、`poc05_acceptance`、`poc05_pause_resume_rerun`、`poc06_edge_cases`、`poc08_export_smoke` 均通过；后端重启到 pid `890372`，`/api/health` 正常，`/api/admin/workflow/nodes` 返回 13 个节点、0 个缺失；当前测试任务 `e778d84a-8d17-43d9-a3be-0aca459ed05c` 仍为 `paused`，下一节点 `HB-PT-003`，继续运行后将进入新接入的 `HB-PT-004`。
- 2026-07-04 10:55 Asia/Shanghai: POC-14 启动：用户提供新版原型 `环评前期研判AI助手(2).html`，要求对比当前系统并迁移一键分析、反馈修正、联网搜索独立功能、上传文件有效性 AI 验证及新版提示词；已按恢复协议读取 `.state/progress.md`、最近 logs/outputs，并开启两个只读 explorer 子 agent 分别分析新版原型和当前系统缺口。
- 2026-07-04 12:16 Asia/Shanghai: POC-14 完成：对比新版原型后完成版本迭代。后端新增 `FILE-VALIDATION` 上传资料有效性与可用性验证辅助 Agent、`WEB-SEARCH` 独立联网检索辅助 Agent、`POST /api/tasks/{task_id}/run-until` 专项一键分析、`POST /api/tasks/{task_id}/feedback/{node_id}` 反馈修正/错误原因分析；反馈修正会替换目标节点并清理下游节点，独立检索会把真实 URL 写入候选依据库；前端新增“AI验证上传资料”“一键分析全部流程”“一键运行全部专项研判”“反馈修正”和后端检索面板，保留前端不直连模型、不浏览器解析 PDF/Word 的原则；系统提示词补充“知识库优先、依据不足时联网检索交叉验证、仍不足则资料不足不得编造”；新增 `scripts/poc14_aux_features.sh` 并通过，既有 `poc05_acceptance`、`poc05_pause_resume_rerun`、`poc06_edge_cases`、`poc08_export_smoke` 均通过；正式 Hermes gateway 已启动，后端重启到 pid `76116`，`/api/health` 正常，前端资源版本为 `20260704-poc14`。
- 2026-07-04 14:05 Asia/Shanghai: POC-15 完成：按用户要求将可见前端收敛为最新版 HTML 原型。`环评前期研判AI助手.html` 已机械同步为 `环评前期研判AI助手(2).html`，差异仅为追加 `/assets/prototype_backend_adapter.js?v=20260704-poc15`；适配脚本覆盖原型中的前端直连模型、浏览器解析 PDF/Word、前端搜索 API、反馈重跑和一键运行动作，实际仍调用后端 Hermes/LangGraph；由于原型没有显式 `PREP-INGEST` 步骤，适配层在用户点击 `HB-PT-000` 时先自动执行隐藏资料读取节点再继续资料审查；`node --check frontend/prototype_backend_adapter.js`、`/api/health` 和静态资源返回检查通过，服务无需重启。
- 2026-07-04 14:11 Asia/Shanghai: POC-16 完成：按用户反馈调整前端按钮。`frontend/prototype_backend_adapter.js` 中模块页追加“一键分析全部流程”的条件已收窄为 `code === 'HB-PT-000'`，HB-PT-001 及后续节点不再显示该全流程按钮；`环评前期研判AI助手.html` 顶部右侧“重置/导出报告”按钮文字由白色改为黑色；`node --check frontend/prototype_backend_adapter.js` 和 `/api/health` 检查通过，服务无需重启。
- 2026-07-04 14:18 Asia/Shanghai: POC-17 完成：按用户反馈彻底移除“一键分析全部流程”。`frontend/prototype_backend_adapter.js` 删除项目输入页和模块页两个追加按钮点，并删除 `runBackendAll` 适配函数；`环评前期研判AI助手.html` 适配脚本版本更新为 `20260704-poc17`；清理未完成的 `prompt_overrides` 临时字段；`rg` 确认前端/后端无“一键分析全部流程”或 `runBackendAll` 残留，`node --check frontend/prototype_backend_adapter.js`、`.venv/bin/python -m compileall backend`、`/api/health` 通过。
- 2026-07-04 14:26 Asia/Shanghai: POC-18 完成：修复原型路径下运行分析结果仍显示 Markdown 的问题。`frontend/prototype_backend_adapter.js` 新增 Word 风格 CSS、Markdown 表格/标题/列表/引用/代码渲染器，所有 `resultBox` 中的节点结果和流式输出都会替换为 `.word-page` 预览；`环评前期研判AI助手.html` 适配脚本版本更新为 `20260704-poc18`；提示词预览改为 `.prompt-editor` 可编辑文本框，编辑内容保存到前端并在运行当前节点时以 `prompt_override` 提交；后端 `EiaTaskState.prompt_overrides` 与 `/api/tasks/{task_id}/step` 已接入，节点输入优先使用该任务的节点提示词覆盖；后端重启到 pid `373203`，`node --check frontend/prototype_backend_adapter.js`、`.venv/bin/python -m compileall backend`、`/api/health` 和静态资源检查通过。
- 2026-07-04 15:42 Asia/Shanghai: POC-20 完成：定位用户任务 `b5b0c3a9-8fca-4efd-84ec-3b9d8ca40e41` 的 `HB-PT-000` 页面只显示 “Both outputs verified” 原因是后端使用 Hermes `run.completed.output` 最终摘要入库，而完整结果已写在工作区 `HB-PT-000_output.md` 和 `HB-PT-000_result.json`；已新增工作区产物优先采集逻辑并修复该任务的 `state.json` 与 `outputs/` 产物，API 返回完整 `HB-PT-000` Markdown 2118 字符；前端 `HB-PT-001` 模块输入现在回填 `HB-PT-000`/`PREP-INGEST` 结果，入口脚本版本更新为 `20260704-poc20`；`python -m compileall backend`、`node --check frontend/prototype_backend_adapter.js`、`/api/health` 和任务 API 验证通过；后端重启到 tmux `eia-backend-poc20`，pid `545634`。
- 2026-07-04 16:48 Asia/Shanghai: POC-21 完成：针对“点击运行后看不到分析中、不知道正在分析哪一步”修复前端状态展示。`frontend/prototype_backend_adapter.js` 新增运行状态持久字段、全局运行状态条、侧边栏当前节点高亮和按钮运行态；单节点运行、隐藏 `PREP-INGEST`、一键专项研判和 SSE 事件都会实时显示当前节点、模型调用 run_id、工具事件或输出接收阶段；入口脚本版本更新为 `20260704-poc21`；`node --check frontend/prototype_backend_adapter.js`、静态资源和 `/api/health` 验证通过；当前任务 `b5b0c3a9-8fca-4efd-84ec-3b9d8ca40e41` 为 `paused`，下一节点 `HB-PT-002`，无活跃 Hermes run。
