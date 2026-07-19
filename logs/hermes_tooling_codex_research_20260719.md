# Hermes 工具配置经验与 Codex CLI 接入研判

- 日期：2026-07-19 Asia/Shanghai
- 性质：只读调研、架构研判与部署核验
- 当前在线环境：Desktop Compose backend + Hermes 0.18.2
- 当前业务任务：`3e66d0a2-9e8b-42f1-b02d-6401a85a8bb0` 保持 `paused`，`next_node=HB-PT-010`，无活动 Hermes run

## 1. Hermes 官方能力确认

Hermes 不是只能使用当前的搜索实现。官方配置文档支持把搜索和正文抽取分开配置，并列出 Firecrawl、SearXNG、Parallel、Tavily、Exa 等后端。SearXNG 只负责搜索结果发现，需要另外配置正文抽取后端。浏览器工具可配置命令超时和 CDP，但浏览器应作为需要交互、动态渲染或登录页面的补充路径，不应作为所有公开政策资料的首选检索路径。

Hermes 官方 MCP 能力支持外部工具自动发现、工具过滤、连接/调用超时和进程回收。官方还提供 Codex preset：`hermes mcp add codex --preset codex`，本质是让 Hermes 通过 MCP 启动 `codex mcp-server`；它要求 Codex CLI 已安装并位于 Hermes 进程的 `PATH`。

官方来源：

- Configuration: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md
- MCP: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md
- Tools reference: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/tools-reference.md

## 2. 社区使用经验的共同点

以下为社区经验，不等同于官方承诺，尤其 Reddit megathread 中可能包含汇总或 AI 辅助整理内容，只用于发现配置方向：

1. Web 工具是否可靠高度依赖搜索后端、模型工具调用能力和工具是否真正启用。社区对 Tavily 的反馈相对直接；SearXNG 常被用于自建搜索，但仍需独立正文抽取。
2. 少量、边界清楚的 profile 比把所有工具和 skill 全部装入上下文更稳定。工具过多会占用上下文并降低模型选对工具的概率。
3. 先把一个固定工作流做稳定，再扩展工具；配置文件、状态文件、超时与循环保护本身就是产品的一部分。
4. 模型需要稳定支持 tool calling。基础模型和辅助任务模型/Provider 都应显式固定，避免自动探测到过期 key 或不同 Provider。
5. Docker 适合已经固定工具链的交付系统；裸机/VM 更适合早期探索。这是运维取舍，不代表当前已稳定的双版本 Docker 架构应回退到裸机。
6. 浏览器自动化在 VPS 和公开搜索站点上仍可能遇到验证码、反自动化和地区网络限制，不能靠放开沙箱解决。稳定方案应优先使用搜索 API/自建元搜索和正文抽取服务，再以浏览器兜底。

社区与问题记录：

- Web search setup: https://www.reddit.com/r/hermesagent/comments/1t4civb/does_hermes_web_search_even_work/
- One month experience: https://www.reddit.com/r/hermesagent/comments/1t29ogw/one_month_with_hermes_agent_what_i_wish_i_knew/
- Three months experience: https://www.reddit.com/r/hermesagent/comments/1u8fm0t/three_months_with_hermes_agent_what_i_wish_i_had/
- Tool and skills bloat: https://www.reddit.com/r/hermesagent/comments/1t34qee/hermes_agent_tool_and_skills_bloat/
- Focused profiles: https://www.reddit.com/r/hermesagent/comments/1t66lhy/my_simplest_yet_effective_hermes_agent_profile/
- VPS deployment: https://www.reddit.com/r/hermesagent/comments/1ucke01/vps_deployment_megathread_hermes_agent_june_2026/
- Cost and token optimization: https://www.reddit.com/r/hermesagent/comments/1ud03si/cost_token_optimization_megathread_hermes_agent/
- MCP and n8n pattern: https://www.reddit.com/r/hermesagent/comments/1u245ua/i_built_a_complete_hermes_agent_desktop_setup/
- Private deployment discussion: https://www.reddit.com/r/hermesagent/comments/1t1t6m6/best_setup_for_private_hermes_usage/
- web_extract context issue: https://github.com/NousResearch/hermes-agent/issues/26568
- Firecrawl/local model tool-calling issue: https://github.com/NousResearch/hermes-agent/issues/8993
- Provider auto-detection issue: https://github.com/NousResearch/hermes-agent/issues/4171
- Long run timeout issue: https://github.com/NousResearch/hermes-agent/issues/4815
- Premature agent termination issue: https://github.com/NousResearch/hermes-agent/issues/7968

## 3. 当前系统的 Hermes 配置建议

### 3.1 Web 搜索与正文抽取

推荐按运维条件二选一：

- 低运维优先：使用 Tavily 作为 search/extract 后端。只增加一个外部服务配置，适合非技术用户交付；先用固定环评政策问题集验收中文政府网站的召回率和正文质量。
- 私有化优先：SearXNG 负责搜索发现，Firecrawl 负责正文抽取。二者作为独立 sidecar/服务部署；SearXNG 不应单独承担正文读取。

当前搜索方式可保留为开发回退，但不应作为生产环境唯一检索后端。公开政策检索优先顺序应为：已审核知识库 -> 专业 search backend -> extract backend/官方页面直读 -> browser fallback。百度/Bing 页面自动化不应成为主路径。

### 3.2 Profile 与工具范围

为 EIA 节点建立专用 profile，只开放业务实际需要的工具组：文件、terminal、web、browser、vision、skills、todo。关闭图片生成、音视频、社交平台等无关工具；MCP 工具使用 include/exclude 白名单，并设置连接、调用和进程生命周期超时。

继续使用项目级 Markdown/JSON 状态和节点成果文件作为跨节点记忆，不将所有历史对话持续灌入每个节点。基础模型、辅助模型和 Provider 显式固定，并使用工具调用稳定的模型。

## 4. Codex CLI 作为当前系统节点 Agent 的可行性

本项由独立只读子 Agent 审查当前源码、容器边界和 Codex CLI 能力后得出。

### 路径 A：后端直接调用 `codex exec --json`

- 可行性：POC 高，生产中等。
- 优点：当前 LangGraph 的节点执行边界清楚，可以把 HermesClient 替换为可选 executor；Codex JSONL 事件可映射为现有 SSE 事件，`--output-schema` 可约束结构，`--image` 可输入图片。
- 改造点：backend 镜像当前没有 Node/Codex；需要独立 CODEX_HOME/凭据、工作目录映射、子进程组停止、事件转换和成果文件回收。
- 适用：先做 A/B POC，不直接替换全系统。

### 路径 B：Hermes 通过 Codex MCP preset 调用 Codex

- 可行性：条件可行，但不建议作为固定主链。
- 原因：形成 Hermes Agent 决策后再调用 Codex Agent 的双层 Agent，增加成本、时延和提示词冲突；内层 Codex 的工具事件、暂停和取消不如直接 executor 清楚。
- 当前障碍：Hermes Controller 目前没有 Codex CLI；启动脚本会重建配置，MCP 配置需要持久化；凭据不能隐式从宿主机泄漏给子进程。
- 适用：偶发编码或专项委派，不适合 13 个固定环评节点的主执行路径。

### 路径 C：Codex 独立 sidecar

- 可行性：生产目标较好，初始开发量高于路径 A。
- 做法：用 `codex app-server` 或包装服务提供与当前 `/v1/runs`、SSE、stop 相容的接口；backend 只切换 Agent endpoint。
- 优点：Agent 生命周期、凭据、工具环境和业务后端解耦，适合后续 Desktop/Server 双版本统一交付。

Codex 官方参考：

- Non-interactive mode: https://developers.openai.com/codex/noninteractive
- Codex as MCP server: https://developers.openai.com/codex/mcp-server
- App server: https://developers.openai.com/codex/app-server

## 5. 接入结论与验证顺序

当前系统可以把 Codex CLI 作为 Agent 分析工具，但不应直接全量替换 Hermes。推荐：

1. 保持 Hermes 为默认 executor，先完成 Hermes search/extract 后端收敛，解决当前公开检索成功率问题。
2. 增加 feature-flagged Codex executor POC，只在 `HB-PT-002` 和 `HB-PT-009` 两个联网依赖高的节点做同资料 A/B 测试。
3. 固定测试集比较事实准确率、官方依据 URL 有效率、完整成果率、耗时、成本、工具轨迹和暂停能力。
4. POC 通过后再做独立 Codex sidecar；不优先采用 Hermes -> Codex MCP 的双 Agent 主链。

重要边界：Codex CLI 本身不保证自动获得当前 Codex 会话使用的托管 `web.run` 搜索能力。部署环境中的 Codex 认证、模型、web search 权限、PDF/图片工具和网络策略必须实际 A/B 验证，不能仅凭 CLI 可安装就认定搜索质量与当前 Codex 会话相同。

## 6. 本次运行与发布核验

- Desktop backend 已重建并 healthy，`http://127.0.0.1:8501/api/ready` 返回 ready。
- Hermes 保持 0.18.2 运行中，未重建。
- 反馈修正失败回滚和节点输出清理补丁已进入运行容器。
- 当前真实业务任务仍为 paused，下一节点 `HB-PT-010`，没有活动 run；本次调研未触发业务模型调用或任务推进。
- 本次未实施 Hermes 搜索后端或 Codex executor，只形成可恢复的方案和下一步。
