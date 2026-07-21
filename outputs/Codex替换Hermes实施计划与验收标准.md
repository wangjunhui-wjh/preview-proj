# Codex 完整替换 Hermes 实施计划与验收标准

制定时间：2026-07-20 Asia/Shanghai  
实施对象：单机版、私有化服务器版  
目标业务内核：HTML 原型前端 + FastAPI/LangGraph + Codex Agent  
当前状态：仅完成方案与单次 Web Search 可行性验证，尚未切换运行服务

## 1. 决策结论

本次改造不采用“Hermes 调用 Codex”、不采用后端直接拼接 Responses API Agent 循环，也不尝试接入当前交互会话本身。目标方案是：

```text
浏览器
  -> FastAPI + LangGraph 业务状态机
  -> Codex Agent Sidecar
       -> 官方 openai-codex Python SDK
       -> SDK 固定版本的 Codex CLI / App Server
       -> 当前 OpenAI-compatible Responses Provider
       -> Codex Web Search / Shell / Vision / Skills / MCP / Subagents
```

Codex 负责每个节点内部的自主规划、文件阅读、文档工具选择、图片识别、联网检索、工具调用、上下文压缩、必要的子 Agent 和最终结果生成。LangGraph 继续只负责业务节点顺序、暂停恢复、checkpoint、失败停止和人工操作入口。

最终通过验收后，删除 Hermes Controller、Hermes Client、Hermes 配置、Hermes UI 文案和 Hermes 镜像。切换期允许短期 feature flag 用于 A/B 与回滚，最终交付不长期保留双 Agent 配置。

## 2. 已确认的事实基线

1. 本机 Codex CLI 为 `0.144.6`，当前使用自定义 OpenAI-compatible Provider、Responses 协议、`gpt-5.6-terra` 和 `xhigh`。
2. 官方 `openai-codex` Python SDK 当前可安装版本为 `0.144.4`，处于 beta；发布包自带固定匹配的 Codex CLI runtime。实现时必须固定 SDK 版本，不混用系统全局 Codex。
3. 官方 SDK 支持同步/异步线程、流式通知、恢复线程、结构化输出、图片输入、Token 用量、上下文压缩、`steer()` 和 `interrupt()`。
4. App Server 协议提供 `webSearch`、`imageView`、`commandExecution`、`fileChange`、`collabAgentToolCall`、`contextCompaction` 等事件。
5. 当前 API 配置下，`codex exec --enable standalone_web_search` 已真实产生 `web_search` 事件，返回生态环境部《建设项目环境影响评价分类管理名录（2021年版）》官方 URL；该 URL 已验证 HTTP 200。
6. `standalone_web_search` 在当前 Codex CLI 中仍标记为 under development，因此只能在固定版本和业务测试集通过后进入生产。
7. ChatGPT 桌面端内置 Browser 官方明确不提供给 Codex CLI。动态网页需求使用 Codex 自主调用成熟的 Playwright MCP；不在后端手写浏览器编排。
8. 现有 Poppler、Tesseract、LibreOffice、PyMuPDF、pdfplumber、python-docx 等文档能力可以复用现有工具镜像定义，不重新开发 PDF/OCR 引擎。

## 3. 范围与非目标

### 3.1 本次必须完成

- 所有现有业务 Agent 入口从 Hermes 切换到 Codex，包括 PREP-INGEST、FILE-VALIDATION、HB-PT-000 至 HB-PT-011、独立联网搜索、反馈修正和上传资料 AI 验证。
- 保持现有前端原型、LangGraph 节点定义、知识库、审核历史、Word 风格预览、导出和任务数据。
- 支持 PDF、扫描 PDF、Office、图片、表格、OCR、视觉、联网搜索、动态网页兜底、长任务、暂停、恢复、重跑和反馈修正。
- 单机版和服务器版均使用容器化 Codex Agent，不要求用户单独安装 Codex CLI、Node、Python 或 Hermes。
- 仅保留 `OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL` 三项模型配置；系统内部运行参数另行命名为 `CODEX_*`，不得出现第二套模型 Key/URL/Model。

### 3.2 明确不做

- 不接入或复制当前正在进行的 Codex 会话。
- 不宣称获得 ChatGPT 桌面端 Browser、账户记忆或当前平台的全部插件。
- 不在业务后端实现通用 Agent 循环、搜索引擎、PDF 解析器、OCR 引擎或浏览器自动化底层。
- 不建设公网多租户 SaaS；服务器版继续定位为私有化单租户部署。
- 不在计划阶段删除、停止或重建当前 Hermes 服务。

## 4. 目标职责边界

| 组件 | 负责 | 不负责 |
| --- | --- | --- |
| 前端 | 上传、节点操作、进度、工具事件、结果、审核管理 | 解析 PDF、组织搜索词、直接调用模型 |
| FastAPI | 任务 API、文件入库、事件转发、结果归档、兼容迁移 | Agent 内部规划、搜索、OCR、视觉策略 |
| LangGraph | 节点顺序、暂停恢复、失败停止、checkpoint | 文档读取和工具循环 |
| Codex SDK Sidecar | Thread/Turn、工具循环、上下文、流式事件、暂停、结果 | 业务节点顺序和知识库审核 |
| Codex | Shell、文件、Web Search、Vision、Skills、MCP、子 Agent | 替代人工最终业务复核 |
| 后端结果门禁 | 校验最终 Schema、真实依据、完成状态 | 反复提示模型直至无限重试 |

## 5. Codex 运行设计

### 5.1 独立 Sidecar

新增 `codex-agent` 容器，内部使用官方 `openai-codex` SDK，不在 FastAPI 中手写 JSON-RPC。Sidecar 只暴露内部运行接口和健康检查，不发布宿主机端口；backend 通过 Compose 内部网络调用。

Sidecar 容器具备现有文档工具栈，但不挂载 Docker socket，不拥有宿主机文件系统。模型 Key 只进入 Codex Agent 和必要的 backend 配置层，不写入日志、任务产物或备份。

### 5.2 独立 CODEX_HOME

系统使用应用专属 `CODEX_HOME`，不挂载开发者个人 `~/.codex`。配置仅包含：

- 当前三项模型环境变量生成的 Provider；
- 固定的 Responses wire API；
- 固定 Codex SDK/runtime 版本；
- `standalone_web_search` 显式开关；
- 环评专用 Skill、必要 MCP 和权限策略；
- 无关插件、个人 MCP、个人记忆和开发 Skill 全部不加载。

这可以避免个人配置泄漏、无关 MCP 403、工具膨胀和每次节点的额外上下文开销。

### 5.3 Thread 策略

- 每次节点首次执行创建独立 Codex thread，thread key 为 `task_id + node_id + attempt`。
- 每个节点从工作区读取项目档案、前序成果和节点提示词，不继承其他节点的完整聊天历史。
- 节点内部允许 Codex 自动压缩上下文，并持久化 thread/turn ID。
- 反馈修正恢复该节点最近一次成功 thread，并提交新的 Turn。
- 重新运行节点创建新 attempt/thread，不复用已被用户判定错误的上下文。
- 下游依赖失效规则保持当前业务决定，不在 Agent 替换中扩大。

### 5.4 文件与结果

- backend 继续为每个任务准备隔离工作区。
- 项目原始资料只读；节点 scratch 和结果目录可写。
- PDF 先由 Codex 自主检查文字层，只对扫描页或关键图片页使用 OCR/视觉，不整册无差别转图片。
- 直接上传图片通过 SDK `LocalImageInput` 传入；PDF 关键页由 Codex 渲染后使用 `imageView`/本地图片输入核验。
- Codex Turn 使用统一 `output_schema` 返回 `completion_state`、`markdown`、`structured`、`evidence_refs`、`limitations`。
- backend 根据最终 Schema 写入标准 `.md/.json/evidence_refs/tool_trace` 文件；不要求 Agent 跨安全根目录写系统文件。

### 5.5 事件映射

| Codex 事件 | 系统事件 |
| --- | --- |
| thread/turn started | `agent_run_started` |
| agentMessage delta | `node_output_partial` |
| commandExecution | `tool_event:terminal` |
| webSearch | `tool_event:web_search` |
| imageView | `tool_event:vision` |
| fileChange | `tool_event:file` |
| collabAgentToolCall | `tool_event:subagent` |
| contextCompaction | `agent_context_compacted` |
| token usage updated | `agent_usage_updated` |
| turn completed | `node_complete` 或成果门禁失败 |
| turn interrupted | `node_paused` |

前端只显示工具名称、阶段、摘要和可公开的 reasoning summary，不展示隐藏思维链。

### 5.6 权限与沙箱

- Codex Agent 容器本身作为外层隔离边界。
- Codex 在专用容器内使用 `ApprovalMode.never + Sandbox.full_access`，允许 Agent 无人值守自主选择并执行命令；这里的 full access 只覆盖该容器可见范围，不是宿主机 full access。
- 容器以非 root、只读根文件系统运行，只提供受控 tmpfs、应用 CODEX_HOME、task 专属 workspace 和 output 挂载。
- Thread 使用 task 专属 workspace roots；宿主机侧只给该任务 scratch/output 写权限。
- 项目上传原件保持只读。
- 禁止挂载 Docker socket、宿主机 home、项目 Git 凭据或开发者个人 Codex 配置。
- 服务器版继续使用独立 `agent_egress` 网络，backend 位于内部 control 网络。

## 6. 分阶段实施计划

| 阶段 | 状态 | 工作内容 | 主要产物 | 退出条件 |
| --- | --- | --- | --- | --- |
| CX-00 | 已完成 | 能力调研、官方 SDK/App Server 核对、当前 API Web Search 烟测 | 本计划、调研日志 | 搜索真实成功，替换边界明确 |
| CX-01 | 已完成 | 建立隔离的 Codex SDK POC，不接业务 API | POC 脚本/报告、固定依赖、最小 CODEX_HOME | Gate A 全通过 |
| CX-02 | 已完成 | 构建 Codex Agent sidecar 与通用 AgentClient 契约 | Sidecar、健康检查、流式运行/停止接口 | 单次 Thread/Turn/interrupt 可用 |
| CX-03 | 待实施 | 接入 PREP-INGEST、HB-PT-002、HB-PT-009 三个代表节点 | 事件映射、输出 Schema、结果归档 | Gate B 代表节点通过 |
| CX-04 | 待实施 | 补齐 PDF/OCR/视觉/Office/Web Search/Playwright MCP/子 Agent | 环评 Skill、工具镜像、能力烟测 | 全工具矩阵通过 |
| CX-05 | 待实施 | 接入全部业务 Agent 入口 | 13 个节点、验证、搜索、反馈修正 | 所有入口均走 Codex |
| CX-06 | 待实施 | 暂停恢复、重跑、反馈修正、崩溃恢复和状态兼容 | thread/turn 状态、迁移逻辑 | 可靠性矩阵通过 |
| CX-07 | 待实施 | 前端和后台管理中性化/改为 Codex | 事件 UI、健康状态、历史记录 | 页面无 Hermes 运行文案 |
| CX-08 | 待实施 | Desktop Compose 切换到 Codex Agent | 单机镜像、脚本、环境模板、备份 | Gate C Desktop 通过 |
| CX-09 | 待实施 | Server Compose 切换到 Codex Agent | 服务器镜像、网络/资源限制、备份 | Gate C Server 通过 |
| CX-10 | 待实施 | 固定项目集 A/B、完整长跑和人工业务验收 | 对比报告、验收记录 | Gate D 业务签收 |
| CX-11 | 待实施 | 删除 Hermes 与临时兼容层，更新交付包 | 干净代码、镜像清单、文档 | 无运行时 Hermes 依赖 |
| CX-12 | 待实施 | 最终双版本回归、离线交付与 Git 收尾 | 最终验收记录、离线镜像包 | 发布判定通过 |

每个阶段完成后必须立即更新 `.state/progress.md` 和 `logs/codex_replacement_*.md`；发生 context compacted 时从记录的 `next_step` 恢复，不依赖聊天历史。

## 7. 四道门禁

### Gate A：Codex 原生能力 POC

必须全部通过，才能开始业务接入：

- 官方 `openai-codex` 固定版本可在独立容器启动，且实际使用其自带 runtime。
- 仅用三项现有模型配置完成登录和模型调用。
- Web Search 产生原生事件，返回至少一个可访问的生态环境官方 URL。
- PDF 文字层读取、扫描页 OCR、图片视觉、Office 读取各通过一个样例。
- SDK 流式事件、Token 用量、上下文压缩信号和最终结果可采集。
- 运行中 `interrupt()` 能终止 Turn，并留下可识别的 interrupted 状态。
- 容器内常规文档与脚本命令不产生人工 approval 请求。
- 应用专属 CODEX_HOME 中没有个人 Skill/MCP/凭据；日志无 Key。
- POC 无法通过时停止改造，不删除或替换 Hermes。

### Gate B：业务节点兼容

使用同一套真实资料对以下节点进行代表性验证：

- `PREP-INGEST`：覆盖大 PDF、扫描页、混合图文和项目档案输出。
- `HB-PT-002`：覆盖官方政策搜索、行业分类、环评类别和审批路径。
- `HB-PT-009`：覆盖同类案例搜索、网页正文核验和资料不足结论。

每个代表节点必须：

- 返回完整 output schema，不能只输出“继续检索”“接下来核验”等过程句。
- 真实依据 URL 可访问，标题、发布机构和引用结论相符。
- 页面结果完整、Word 风格预览正常、下一节点输入可读取。
- 失败时任务停在当前节点，不自动推进下游。
- 同一资料至少重复运行 3 次，完成率必须为 3/3。

### Gate C：双版本部署

- Desktop：只安装 Docker 即可启动，backend 与 Codex Agent healthy，端口仅绑定 localhost，重启后数据/线程/成果保留。
- Server：只有 Caddy 暴露主机端口；backend 与 Codex Agent 无主机端口；无 Docker socket；认证、TLS、资源限制和备份通过。
- 两个版本均不依赖宿主机 Codex、Hermes、Python、Node 或个人 `~/.codex`。
- 离线镜像包包含固定 Codex Agent 镜像且不包含模型 Key、任务资料或个人 Codex 状态。

### Gate D：业务签收与删除 Hermes

- 固定项目集至少包含：纯文字 PDF、扫描 PDF、图文混合 PDF、直接图片、资料不完整项目各 1 个。
- 全流程从 FILE-VALIDATION/PREP-INGEST 运行至 HB-PT-011，不出现跳节点、静默失败或过程句误判完成。
- 业务人员逐节点复核事实、结论、依据、风险和补充资料；关键错误数为 0。
- 反馈修正、单节点重跑、全部专项重跑、暂停和恢复全部通过。
- Codex 版本、模型、Web Search 状态、Token、耗时和工具轨迹可在后台审计。
- Gate A-C 和完整回归全部签收后，才执行 CX-11 删除 Hermes。

## 8. 详细验收矩阵

### 8.1 Web Search 与依据

- 建立不少于 20 条已知答案的环评政策查询集，覆盖生态环境部、发改委、国务院、省级生态环境部门和地方政府。
- 已知官方文件 Top-5 命中率不低于 90%。
- 所有最终引用 URL 必须来自真实 `webSearch`、直接读取或已审核知识库记录。
- 可访问 URL 的 HTTP/页面验证成功率不低于 95%；受站点限制的失败必须记录原因和检索时间。
- 不得把搜索摘要当作完整政策正文，不得引用无法定位的虚构 URL。
- 同一查询达到预算后停止，不因换近义词无限循环。

### 8.2 文档与视觉

- 可复制文字 PDF：优先文字层，关键字段与人工抽查一致。
- 扫描 PDF：仅扫描页进入 OCR；页码和来源保留。
- 图文混合 PDF：文字层与关键图片分别处理，不整册转图。
- 表格：产品、原辅料、设备和参数表不丢主要行列关系。
- 直接图片：流程图、总平图、设备图和截图至少各 1 个样例通过。
- 不得将设备商地址、示例字段或模板文字误判为项目事实。

### 8.3 Agent 完成质量

- 最终结果必须满足统一 output schema，`completion_state=completed` 才允许节点推进。
- 过程消息、短句、计划句、工具错误和中断状态均不得触发完成。
- 缺少依据时允许输出“资料不足，建议人工核实”，但必须完成本节点规定的分析结构。
- 节点失败最多执行有限的同 Turn 修正或单次新 Turn 纠正，不允许无限重试。
- reasoning 只显示官方 reasoning summary，不存储或展示隐藏思维链。

### 8.4 暂停、恢复和故障

- 用户点击暂停后 5 秒内发出 `interrupt()`；下游节点不得启动。
- 中断 Turn 标记为 interrupted/paused，不写成 completed。
- 恢复后从当前节点继续，不重复已经确认完成的上游节点。
- Sidecar 或 backend 重启时，孤立 running 任务恢复为 paused；不得自动越过未完成节点。
- 清空任务、删除任务或重跑节点时，旧 Turn 不得继续向当前任务写结果。
- API 客户端超时不得短于业务长任务上限；默认允许 3600 秒，并持续输出心跳/工具事件。

### 8.5 反馈修正与重跑

- 反馈修正恢复对应节点 thread，页面能看到新的 Turn 和工具事件。
- 修正失败保留原成功结果，明确返回失败，不提示修正成功。
- 单节点重跑创建新 attempt/thread，并完整清理该节点所有标准与派生文件。
- 重新运行全部专项保留上传资料、PREP-INGEST、HB-PT-000、HB-PT-001，从 HB-PT-002 开始重新生成。

### 8.6 安全与隐私

- 容器内不挂载 `/var/run/docker.sock`、宿主机 home、SSH/Git 凭据或个人 Codex 配置。
- 原始项目资料只读；Codex 写入范围限定到 task workspace/output。
- 非当前任务路径访问由 SDK sandbox 或容器挂载边界阻断。
- 日志、SSE、产物、备份和镜像中不得出现完整 API Key。
- Prompt injection 样例不能改变证据规则、读取其他任务或泄漏环境变量。
- Server 版 agent egress 与 control 网络分离，backend 不直接暴露公网。

### 8.7 性能、成本和可观测性

- 后台显示 node、thread ID、turn ID、模型、reasoning effort、开始/结束时间、Token 和工具摘要。
- 应用专属 CODEX_HOME 不加载任何无关个人 MCP/Skill；启动日志不出现无关 MCP 403。
- 记录每节点输入、缓存输入、输出和 reasoning Token，形成 Hermes/Codex 对照表。
- 不设置不合理的短响应超时；长时间无事件时显示“等待模型响应”，而不是误报完成。
- 并发限制由 Sidecar 统一控制：Desktop 默认 2，Server 默认 4，可配置且超限排队。

## 9. 数据与 API 兼容迁移

### 9.1 状态字段

新增中性字段：

- `active_agent_run_id`
- `agent_runtime`
- `agent_thread_id`
- `agent_turn_id`
- `agent_attempt`

读取旧任务时兼容 `active_hermes_run_id` 和 `hermes_run_id`；首次保存时迁移到中性字段。旧节点成果和知识库不重写、不丢失。

### 9.2 API 与前端

- 新增 `/api/agent/health`，旧 `/api/hermes/health` 在切换期返回弃用提示，CX-11 删除。
- 前端状态变量、localStorage 和事件名称改为 Agent/Codex 中性命名。
- 已保存的旧 localStorage key 读取一次后迁移并删除。
- 后端外部任务 API 路径和响应结构保持兼容，避免原型页面大改。

### 9.3 运行中任务

- 不迁移活动中的 Hermes run。
- 发布切换前必须确认所有任务为 paused/failed/completed 且无 active run。
- 已完成结果继续显示；需要重跑的节点由 Codex 创建新 thread。

## 10. 回滚方案

1. CX-01 至 CX-10 期间保留当前 Hermes 镜像和 Compose 配置的 Git tag/提交，不删除运行数据。
2. 通过 `AGENT_RUNTIME=hermes|codex` 进行短期内部切换，但前端不暴露给普通用户。
3. Codex POC 或业务门禁失败时，将运行任务置 paused，停止 Codex sidecar，使用原提交/镜像恢复 Hermes；旧成果不回滚。
4. Gate D 签收并完成 CX-11 后，正式代码不再保留双运行时；如需回退，使用发布 tag 回退整个版本，避免混合配置。
5. 回滚演练必须验证旧任务可读取、上传资料和知识库未丢失、Hermes 健康、至少一个节点可运行。

## 11. 代码与交付影响清单

预计新增：

- `codex_agent/`：官方 SDK 适配服务、运行注册、事件映射和健康检查。
- `Dockerfile.codex-agent`：固定 SDK/runtime + 现有文档工具。
- `backend/agent_client.py`：中性 Agent 接口。
- `skills/eia-precheck/` 或应用专属 Codex Skill。
- Codex POC、事件映射和双版本验收测试。

预计修改：

- `backend/main.py`、`backend/models.py`、`backend/config.py`、`backend/graph.py`。
- `frontend/` 与原型后端适配层中的 Hermes 文案/状态变量。
- Desktop/Server Compose、环境模板、启动/日志/备份脚本、镜像清单和说明文档。
- 依赖锁文件、离线镜像导入导出和发布验收记录。

最终删除：

- `backend/hermes_client.py`
- `Dockerfile.hermes`
- `Dockerfile.hermes-tools`（能力迁移到通用 Codex Agent 工具镜像后）
- `docker/hermes/`
- 所有 `HERMES_*` 配置、Hermes 服务和 Hermes 专用文档
- 运行时代码中的 `active_hermes_run_id`、`hermes_run_id` 和 Hermes UI 文案

历史实施记录可以归档保留，不作为运行依赖。

## 12. 阶段性提交与无人值守规则

- 每个 CX 阶段独立提交，提交前执行对应静态检查和阶段 smoke。
- 每阶段只允许一个明确 `next_step`，完成后立即更新 `.state/progress.md`。
- 长测试过程写入 `logs/codex_replacement_<date>.md`，结果产物写入 `outputs/`。
- 任何门禁失败必须停止推进并记录失败证据，不得自动跳到下一阶段。
- 任何真实业务任务正在 running 时，不重建对应运行服务；先等待完成或人工暂停。
- 不在日志、计划、截图或 Git 中记录 API Key。

## 13. 发布判定

只有同时满足以下条件，才能发布“Codex Agent 版”：

- Gate A、B、C、D 全部通过并有持久验收记录。
- 两个版本的 Docker Compose、健康检查、备份、恢复和离线镜像验收通过。
- 固定业务测试集和至少一个真实项目全流程通过人工复核。
- 代码、配置、页面和交付包不存在 Hermes 运行依赖。
- 当前三项模型配置可直接驱动 Codex SDK，Web Search 实际可用。
- 已知限制明确写入交付文档：Codex CLI 无 ChatGPT 内置 Browser，Web Search 功能版本固定且需要回归。

计划审核通过后的下一步为 `CX-01_CODEX_SDK_ISOLATED_POC`，只建立隔离 POC，不切换当前在线服务。
