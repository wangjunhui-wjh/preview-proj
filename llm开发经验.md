# LLM 开发经验记录

本文用于记录本项目中与 LLM、文档解析、知识库、视觉识别、Web Search、日志排障相关的经验。后续遇到类似问题，优先补充到这里。

## 1. 大文档不要一次性塞给模型

问题表现：
- 上传多个 PDF 后，第一步 `HB-PT-000` 请求很慢或连接失败。
- 第三方 API 后台可能看不到明显请求，或者请求长时间不返回。
- `logs/llm_calls.log` 里只有 `call_start`，迟迟没有 `call_success` 或 `call_error`。

原因：
- PDF 解析后的文本可能非常长。
- 如果把 3 个 PDF 全文一次性放进 `HB-PT-000` prompt，会导致请求体过大、上下文过长、网关处理时间过久。
- `gpt-5.5 + xhigh` 推理强度较高，本身也会增加响应时间。

推荐流程：

```text
文件上传
→ 后端只保存原始文件、hash、类型和工作区路径
→ PREP-INGEST Agent 自主读取 PDF/DOCX/图片/扫描件/文本
→ Agent 生成带来源索引的项目档案
→ HB-PT-000 / HB-PT-001 优先读取项目档案
→ 后续模块按需检索原文片段
```

当前实现：
- 前置节点提示词：[prep_ingest_project_dossier.txt](./prompts/prep_ingest_project_dossier.txt)
- 产物：`outputs/<task_id>/PREP-INGEST.md`、`PREP-INGEST.json`、`PREP-INGEST.tool_trace.json`

## 2. Codex 式读文档不是全文直塞

Codex 处理大文件的思路不是“把整份文件发给模型”，而是：

- 先用工具读取文件。
- 看目录、标题、结构、页数。
- 搜索关键词定位相关片段。
- 分块读取和摘要。
- 把中间结果沉淀为结构化信息。
- 后续任务只带必要上下文。

本系统也应遵循同样思路，尤其是 PDF、环评报告、规划文件、政策文件这类长文档。

## 3. 项目资料和知识依据要分开

项目资料：
- 备案证
- 可研摘要
- 项目简介
- 建设单位提供的 PDF/Word/图片

知识依据：
- 政策文件
- 园区规划环评
- 准入清单
- 生态环境分区管控成果
- Web Search 获取的真实网页来源

不要把“项目资料”当成“政策依据”。
也不要把模型记忆当成政策依据。

## 4. 依据必须真实可追溯

当前规则：
- 页面不再加载内置演示政策依据。
- 依据只允许来自：
  - 用户上传的真实文件
  - 用户启用 Web Search 后检索到的真实 URL

如果没有依据，模块必须输出：

```text
资料不足，建议人工核实
```

不能编造政策名称、文号、条款号或结论。

## 5. Web Search 查询词不应由前端手填

问题：
- 让用户在前端填写 Web Search 限定词，会把检索策略暴露给非技术用户。
- 用户不知道每个模块应该搜什么。

推荐：
- 后台根据当前模块和项目摘要自动生成检索式。
- 大模型或检索规划器组织搜索词。
- 搜索词应尽量面向官方来源。

当前实现：
- [search_query_planner.py](./eia_ai_demo/services/search_query_planner.py)

## 6. PDF 图片识别要用混合策略

不要默认把 PDF 整本当图片识别。

推荐流程：

```text
PDF
→ 先抽取内嵌文本
→ 判断页面是否文字很少/疑似扫描页
→ 判断页面是否含图片或图表
→ 只对必要页面渲染成图片
→ 调用视觉模型
```

页面保留手动策略：
- 自动：仅扫描页/含图页
- 全部页面

当前实现：
- [vision.py](./eia_ai_demo/services/vision.py)

## 7. 图片识别结果不能直接当最终事实

图片/扫描件识别适合提取：
- 项目名称
- 建设单位
- 建设地点
- 备案编号
- 产品和产能
- 工艺流程
- 表格字段
- 盖章文件中的日期和文号

但图片识别可能出错，特别是：
- 小字
- 模糊扫描件
- 倾斜拍照
- 表格跨页
- 坐标和编号

推荐流程：

```text
图片识别
→ 提取文本
→ 页面展示
→ 人工确认
→ 再进入 HB-PT 工作流
```

## 8. API 失败不能继续往后跑

问题：
- 之前 API 调用失败后自动 fallback 到 mock，导致 `HB-PT-000` 失败后继续请求 `HB-PT-001`。
- 真实业务中这会造成错误链路。

当前规则：
- API 模式下，模块调用失败立即停止工作流。
- 只有显式设置 `ALLOW_MOCK_FALLBACK=1` 才允许失败后回退 mock。

推荐：
- 演示模式使用 `mock`。
- 真实模式使用 `auto` 或 `api`，失败就停止，不伪造结果。

## 9. 必须记录 LLM 调用日志

排查 LLM 问题不能只看页面。

当前日志：

```text
logs/llm_calls.log
logs/vision_calls.log
logs/document_ingestion.log
logs/workflow_run_*.json
```

`llm_calls.log` 记录：
- module_id
- model
- base_url
- reasoning_effort
- timeout
- max_retries
- call_start
- call_success
- call_error
- duration_seconds
- output_chars

查看命令：

```bash
tail -f logs/llm_calls.log
```

## 10. 环境变量必须以运行进程为准

问题：
- shell 中改了环境变量，但 Streamlit 已经启动。
- 运行中的 Streamlit 进程不会自动读取新的环境变量。

检查运行进程环境：

```bash
pid=$(pgrep -f "streamlit run app.py" | head -1)
tr '\0' '\n' < /proc/$pid/environ | rg '^OPENAI_' | sed -E 's/(OPENAI_API_KEY=).*/\1***MASKED***/'
```

修改环境变量后必须重启服务。

## 11. Base URL 只使用标准变量名

标准变量：

```bash
OPENAI_BASE_URL
```

不要使用错误写法：

```bash
OPENAI_BASE_UR
```

当前代码只读取 `OPENAI_BASE_URL`。

补充：
- 某些 shell 文件会在非交互 shell 中提前 `return`，例如 `.bashrc` 顶部的 `case $-` 判断。服务进程不一定能继承用户交互终端里的 export。
- 长期服务不要依赖“当前终端里 export 过”，应写入服务自己的 `.env`、systemd Environment 或应用配置。
- Hermes `custom` provider 不再把 `OPENAI_BASE_URL` 当 endpoint 真相，应该配置 `~/.hermes/config.yaml` 的 `model.base_url`。

## 11.1 OpenAI-compatible Base URL 必须指向 `/v1`

本机前置验证发现：

```text
https://api.aiboys.xyz      -> 非流式返回形态异常，流式为空
https://api.aiboys.xyz/v1   -> 非流式和流式均正常
```

Hermes 失败日志：

```text
Provider returned an empty stream with no finish_reason
```

排查结论：
- 上游接口本身可用。
- 问题不是 API key，也不是模型名。
- Hermes/OpenAI SDK 需要 `base_url` 指向 OpenAI-compatible 的 `/v1` 根路径。

处理：

```bash
hermes config set model.provider custom
hermes config set model.default gpt-5.5
hermes config set model.base_url https://api.aiboys.xyz/v1
```

如果 custom endpoint 的域名不是 `openai.com`，Hermes 出于防泄漏考虑不一定会自动把 `OPENAI_API_KEY` 发给该域名。当前 `api.aiboys.xyz` 可通过 `AIBOYS_API_KEY` 让 Hermes 读取同一把 key。

## 12. 超时不宜过短

`gpt-5.5 + xhigh + 长上下文` 可能需要较长时间。

当前推荐：

```bash
OPENAI_REQUEST_TIMEOUT=300
OPENAI_MAX_RETRIES=0
```

说明：
- timeout 过短会误杀正常长请求。
- retries 过多会让页面长时间无响应。
- 第三方网关不稳定时，优先看 `logs/llm_calls.log`。

## 13. 分步执行的含义

初始化分步任务：
- 保存用户粘贴文本和上传原始文件
- 建立任务工作区和 LangGraph checkpoint
- 不把 PDF/图片解析结果直接当项目事实

执行下一步：
- 每次只执行一个流程节点。第一步是 `PREP-INGEST` 项目资料读取 Agent，然后才进入 HB 模块。

顺序：

```text
PREP-INGEST 项目资料读取与项目档案构建
HB-PT-000 资料完整性审查与模块选择
HB-PT-001 项目概况提取
HB-PT-002 行业类别、环评类别及审批路径
HB-PT-003 产业政策符合性
HB-PT-005 生态环境分区管控
HB-PT-007 两高/化工项目
HB-PT-010 综合报告生成
HB-PT-011 交叉一致性核查
```

## 14. 排障优先级

遇到“页面没动静”时，按这个顺序查：

1. 看 `logs/llm_calls.log` 是否有 `call_start`。
2. 如果没有，说明前端还没进入 LLM 调用。
3. 如果有 `call_start` 但无结果，说明正在等第三方 API。
4. 如果有 `call_error`，看 `error_type`。
5. 如果是 `AuthenticationError`，查 API key 或 Base URL。
6. 如果是 `APIConnectionError`，查第三方网关、网络、请求体大小、超时。
7. 如果某一步失败，工作流应停止，不应继续后续模块。

## 15. 后续待优化

- 在页面显示项目资料摘要包预览。
- 在页面显示原始文本字符数、摘要包字符数和分块数量。
- 给每个模块显示输入 token/字符估算。
- 对知识库文件也增加摘要和元数据索引。
- Web Search 结果增加 URL 去重、官方来源优先级和有效性标记。
- 继续强化 PREP-INGEST 的来源索引、页码定位、图片识别置信度和缺失资料提示。

## 16. 不要把一个 HB 模块做成一次大请求

问题：
- 当前原型中 `HB-PT-000`、`HB-PT-001` 等模块基本是“一次 prompt → 一次 LLM 返回”。
- 这会导致单次请求过长、等待时间长、失败后损失大。
- 用户体验像“页面卡住”，即使后台已经发出请求。

更合理的方式是 Codex 式自动化工作流：

```text
一个业务模块
→ 多个子任务
→ 多次小请求
→ 每一步有日志
→ 每一步可失败重试
→ 最后汇总成模块结果
```

例如 `HB-PT-000` 应拆成：

```text
1. 本地文件清点：文件名、类型、页数、文本字符数、是否扫描件
2. 项目资料摘要包生成：不调用或少调用 LLM
3. 关键字段候选抽取：按 chunk 提取项目名称、地点、产品、产能、工艺等
4. 字段完整性判断：一次较小 LLM 请求
5. 模块启动建议：一次较小 LLM 请求
6. 补充资料清单生成：一次较小 LLM 请求
7. 结果格式化和自检：一次较小 LLM 请求
```

例如 `HB-PT-001` 应拆成：

```text
1. 按文件/片段抽取项目事实
2. 合并冲突字段
3. 标记来源文件和片段
4. 输出结构化项目画像
5. 自检信息缺口
```

这样做的好处：
- 每次请求更小。
- 可以显示实时进度。
- 某个子步骤失败不会毁掉整个模块。
- 更容易定位到底是文档解析、检索、模型调用还是格式化失败。
- 可以像 Codex 一样自动进行多轮读取和判断。

## 17. 流式输出解决的是体验，不是根因

流式输出有价值：
- 页面能看到模型正在返回。
- 用户不会误以为系统卡死。
- 可以显示首包时间、生成速度和部分结果。

但流式输出不能解决：
- 输入太长。
- 单次任务太大。
- 第三方网关不稳定。
- 模块失败后无法局部重试。

因此正确方向是：

```text
流式输出 + 模块拆分 + 子任务日志 + 分块检索 + 局部重试
```

不要只做流式输出，而继续保持“一模块一大请求”。

## 18. 模型强度应分层使用

不应该所有步骤都用 `xhigh`。

推荐：

```text
文档解析/字段候选抽取：low / medium / 小模型
信息合并/字段冲突处理：medium / high
政策符合性判断：high
综合承接建议和交叉一致性：xhigh
```

原因：
- `xhigh` 慢且贵。
- 解析类任务不需要最高推理强度。
- 高风险判断才需要更强推理。

## 19. 页面进度应该显示子任务而不是只显示 HB 模块

不要只显示：

```text
正在执行 HB-PT-000
```

应显示：

```text
HB-PT-000 / 1. 文件清点
HB-PT-000 / 2. 文档摘要包
HB-PT-000 / 3. 字段候选抽取
HB-PT-000 / 4. 完整性判断
HB-PT-000 / 5. 模块选择
HB-PT-000 / 6. 结果自检
```

每个子任务都应写日志：

```text
logs/llm_calls.log
logs/document_ingestion.log
logs/workflow_events.log
```

## 20. 成熟文档读取方案不是自己从零写

如果系统进入正式化，文档读取不建议长期依赖自研的简单 `PyMuPDF + 正则 + 摘要包`。

成熟组件可以组合使用：

```text
Docling / Unstructured / Apache Tika
→ 文档解析、版面、表格、OCR、图片、阅读顺序

LlamaIndex / LangChain
→ Document Loader、Node Parser、Text Splitter、Retriever

Chroma / FAISS / OpenAI Vector Stores
→ 向量索引和按需检索

LangGraph / LlamaIndex Workflow / 自研状态机
→ 多步骤自动化执行
```

推荐长期架构：

```text
文档上传
→ 专业解析器提取文本、表格、图片、页码和结构
→ 分块并带 metadata
→ 建立索引
→ 每个 HB 模块按需检索
→ 多个小 LLM 请求
→ 汇总和自检
```

这比“一次性读取全文 + 一次大 prompt”更稳定，也更接近 Codex 的文档处理方式。

## 21. 300 字 PDF 都慢/失败时，不应归因于文档过大

本项目中出现过：

```json
{
  "event": "project_digest",
  "raw_chars": 329,
  "digest_chars": 388,
  "chunk_count": 1,
  "truncated": false
}
```

这说明本次送入 LLM 的项目资料并不大。

如果只有几百字仍然出现：

```text
APIConnectionError
请求耗时 200 秒以上
call_start 后长时间无 call_success / call_error
```

优先排查方向应从“文档太大”切换为：

```text
1. 第三方 API 网关稳定性
2. Responses API 是否被该网关完整支持
3. reasoning_effort=xhigh 是否兼容或过慢
4. 是否应该改用 /v1/chat/completions
5. 是否需要 streaming
6. 是否模型名 gpt-5.5 在该网关实际可用
7. 是否网关对长 system prompt 或 structured output 慢
8. 是否存在网络连接超时、代理、TLS 或服务端排队
```

诊断顺序：

```text
1. PING 小请求
2. HB-PT-000 小样本请求
3. 同样 prompt 去掉 reasoning
4. 同样 prompt 改用 high / medium
5. 同样 prompt 改用 chat completions
6. 同样 prompt 开 streaming
7. 再考虑文档解析和摘要包问题
```

结论：

```text
文档读取问题和 API 调用问题必须分开判断。
如果摘要包只有几百字，LLM 仍然异常慢，根因大概率在 API 调用链，而不是文档读取链。
```

## 22. Docker Agent 的工具路径必须区分 Controller 与终端

2026-07-18 的 Hermes Docker terminal 验收确认：Agent 在容器内执行 `pdftotext`、PyMuPDF、Tesseract、Python 脚本等命令时，文件路径是容器路径，例如：

```text
/eia/workspaces/<task_id>/project_files/<file>.pdf
/workspace/<temporary-image>.png
/eia/outputs/<task_id>/<NODE>_output.md
```

不要把这些路径直接交给运行在 Hermes Controller 进程中的工具。尤其是 `vision_analyze` 会按 Controller 所在文件系统验证本地图片；它看不到 Docker 容器内部的 `/workspace/*.png`，会报“Invalid image source”。

正确边界：

```text
终端容器内 PDF 渲染/提取图片
→ 容器内 OCR 可直接执行
→ 若要调用 Controller 侧视觉模型，先通过受控共享图片缓存交接
→ 传 Controller 可见的本地路径或 HTTPS URL
→ 记录图片来源、页码、视觉模型结论与置信度
```

在图片缓存桥接完成并用真实扫描件验收前，提示词应允许 Agent 以容器 OCR 作为回退，但不能把 OCR 结果伪称为视觉模型识别结果。该问题与模型 API、PDF 大小或人工审批无关，是 Docker 文件系统边界问题。
