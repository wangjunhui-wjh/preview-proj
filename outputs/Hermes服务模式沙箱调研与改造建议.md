# Hermes 服务模式沙箱调研与实施记录

调研与实施时间：2026-07-18  
范围：确认 Hermes API Server 是否原生支持由 Agent 自行管理工具、文档读取和受限执行环境，并完成当前环评系统的 Docker terminal 改造。

## 结论

已采用 Hermes 原生的 Docker 终端后端。FastAPI 不手写 PDF/OCR/Web 工具编排，也不建设独立 Worker 集群；LangGraph 仍只负责业务节点顺序、暂停恢复与状态留痕。

Hermes 的 Docker 有两个不同模式：

1. Hermes Controller 自身运行在 Docker 中。它便于部署和守护，但终端若仍使用 `local`，只是把本地执行移入该容器，不等于每个 Agent 任务拥有独立沙箱。
2. Hermes API Server 使用 `terminal.backend: docker`。Agent 的终端、文档解析脚本和 OCR 命令均由 Hermes 放进受限 Docker 沙箱执行。这是本系统应采用的模式。

Docker Compose 是否容器化 Hermes Controller 是部署选择，不是解决审批和任务隔离的核心。

## 已实施配置与验收

| 项目 | 当前状态 |
| --- | --- |
| Hermes API Server | 宿主机 `tmux` 会话 `hermes-eia` 运行，Docker 后端通过 `host.docker.internal:8642` 调用 |
| 终端后端 | `terminal.backend: docker`，共享持久 Docker sandbox |
| 工具镜像 | `eia-ai-hermes-tools:latest`，默认使用清华 Debian/PyPI 镜像构建，无需梯子 |
| 文件边界 | `data/workspaces` 只读挂载为 `/eia/workspaces`；`outputs` 读写挂载为 `/eia/outputs` |
| 工具 | Poppler、Tesseract 中英文、LibreOffice、PyMuPDF、pdfplumber、Office 解析库、Node、FFmpeg 已验收 |
| 审批 | Docker profile 的 `approvals.mode: off`；Agent 只在 Docker 内自由执行脚本和命令 |
| 秘钥和宿主机边界 | 不转发模型环境变量；不挂载 Docker socket、项目源码或 `.env` |
| 真实节点验收 | 三份 PDF 的 `PREP-INGEST` 已完成：14 次模型调用、13 轮工具调用，无 `approval.request`，后端已回收 Markdown/JSON 成果 |

任务 `e098c0e7-d05a-4282-89b8-2053ca4b822c` 现暂停在 `HB-PT-000`，可以由前端继续，不会自动运行后续节点。

## 已核实的原生能力

| 能力 | Hermes 已提供 | 对系统的意义 |
| --- | --- | --- |
| Agent 服务 | `/v1/runs`、状态、SSE、stop | 后端只创建 HB 节点任务、转发状态、保存结果 |
| 审批 API | `/v1/runs/{run_id}/approval`，支持 once/session/always/deny | 用于人工例外的兜底，不是无人值守主路径 |
| Docker 终端 | `terminal.backend: docker`，cap-drop、禁止提权、PID/CPU/内存/磁盘限制 | Agent 自主使用 PDF/OCR/Python/网页工具，避免宿主机执行 |
| 文档缓存挂载 | Hermes documents/images cache 会只读提供给 Docker terminal | 后端可交接上传资料，但不解析也不安排读取策略 |
| 工具与技能 | OCR/documents、vision、web_search、todo、subagent | 资料类型识别、文本层、OCR、视觉和搜索均由 Agent 自主选择 |

官方依据：[Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker)、[安全与审批](https://hermes-agent.nousresearch.com/docs/user-guide/security)、[终端配置](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)。

## 当前故障的准确原因

任务 `e098c0e7-d05a-4282-89b8-2053ca4b822c` 在 `PREP-INGEST` 尚未读取 PDF 时即失败。日志显示 Agent 先检查 `pdftotext`、`pdfinfo`、`tesseract`、PyMuPDF；其中 `python3 -c` 命中 Hermes 的“脚本执行”审批规则。

当前后端收到 `approval.request` 后立即调用 stop，因此节点失败。资料验证任务还看不见后端容器的 `/app/data/workspaces/...` 路径，随后进行了无效文件系统查找。

根因不是 PDF 工具缺失、模型 API 失败或资料过大，而是：

1. Hermes 当前终端为 `local`，需人工审批；
2. 后端把自身绝对工作区路径写进 Agent 提示词；
3. `/v1/runs` 不接收 PDF/DOCX 上传，也没有 run 级工作目录或 volume 参数。

## 接口边界

当前 `/v1/runs` 支持文本、图片 URL/图片数据和 `session_id`，不支持 `input_file`、PDF/DOCX 上传。源码有 `register_task_env_overrides(task_id, ...)`，可以为任务指定独立 Docker 镜像/环境，但它是内部基础设施 API，尚未公开给 `/v1/runs`。默认 Docker 后端是跨会话共享的持久容器。

不能把“每个任务自动独立容器、上传资料自动进入容器”误认为当前开箱即用能力。需要资料交接约定；需要多任务强隔离时，再增加很薄的 Hermes 服务适配层。

## 最终路线

当前单用户模式使用共享持久 Docker sandbox。后端以稳定 `session_id=task_id` 创建 Hermes run，Agent 自主决定文件读取、脚本、OCR、视觉、网页检索和结果格式，成果写入 task 对应的 `/eia/outputs/<task_id>`。

多用户或多项目并发时，才考虑在 Hermes API Server 一侧增加 task environment override，以实现任务级镜像、volume 和容器清理；不把 Docker socket 或工具编排放进业务后端。

## 不采用的方案

| 方案 | 原因 |
| --- | --- |
| 仅把 Hermes Controller 放进 Docker，终端仍为 `local` | 审批仍在，且 Agent 可访问同一控制器容器中的配置和资料 |
| 宿主机 `local` 设置 `approvals.mode: off` | 等价于远程 Agent 在宿主机无审批执行命令，风险不可接受 |
| 用提示词禁止 `python -c`、`find` | 不断漏掉正常工具调用，也不解决路径不可见 |
| FastAPI 手写 PDF/OCR/网页搜索 | 与 Hermes 重叠，再次形成难维护的手写 Agent |
| 每个 HB 节点另建 Worker 服务 | 当前规模没有必要；LangGraph 做业务状态，Hermes 做节点内部执行 |

## 尚待补齐

`vision_analyze` 属于 Controller 侧工具，而终端生成的页面截图位于 Docker 内 `/workspace`，二者路径不共享。当前 Agent 已能以容器内渲染加 Tesseract OCR 处理图像页，但要启用“视觉模型直接分析 PDF 渲染页/上传图片”，需要增加一个受控图片缓存交接路径，并以扫描 PDF、图纸和直接上传图片做独立验收。这不影响本次 Docker terminal、PDF 文本层、OCR、结果回收和无人值守审批的验收结论。
