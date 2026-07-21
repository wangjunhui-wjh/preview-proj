# Codex 替换 Hermes：CX-01 / Gate A 验收记录

## 1. 验收结论

- 结论：`通过`。
- 验收时间：2026-07-21（Asia/Shanghai）。
- 范围：仅验证 Codex SDK/App Server 原生能力，不接业务 API，不修改 LangGraph 流程，不切换或重启当前 Desktop backend/Hermes。
- 下一步：`CX-02_CODEX_AGENT_SIDECAR`，构建 Codex Agent sidecar 和通用 AgentClient 契约。

## 2. 固定运行基线

| 项目 | 验收值 |
| --- | --- |
| Python SDK | `openai-codex==0.144.4` |
| SDK 自带 CLI runtime | `openai-codex-cli-bin==0.144.4`，`codex-cli 0.144.4` |
| POC 镜像 | `eia-codex-agent-poc:0.144.4` |
| 镜像 ID | `sha256:b3c25c1130af93570a58ee313c2533da5da72dd83218e4bb6c2f5cabff45fe34` |
| 模型配置 | 仅使用 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` |
| API 方式 | OpenAI-compatible Responses |
| 推理强度 | `xhigh` |
| Agent 权限 | 容器内 `ApprovalMode.deny_all + Sandbox.full_access` |

最终 POC 配置用 Provider 的 `env_key = "OPENAI_API_KEY"` 读取密钥，`requires_openai_auth = false`，不调用 `login_api_key()`，不在应用 `CODEX_HOME` 生成 `auth.json`。

## 3. 容器隔离

- 容器根文件系统为只读，运行用户为宿主普通用户 UID/GID。
- `CapDrop=[ALL]`，启用 `no-new-privileges`。
- 只挂载 3 个只读样例输入和 1 个 POC 可写目录；未挂载 Docker socket、宿主机 home、Git 凭据或个人 Codex 配置。
- 应用专属 `CODEX_HOME` 只包含该 POC 生成的配置、状态和隔离 workspace 信任项；没有个人 MCP 或 Skill。
- 全量结果、事件日志和配置均完成 Key 字面值扫描，未发现 Key；早期登录方式生成的两份临时 `auth.json` 已销毁。

## 4. Gate A 结果

| 验收项 | 结果 | 证据摘要 |
| --- | --- | --- |
| 固定 SDK/runtime | 通过 | SDK、CLI runtime 和容器均固定为 `0.144.4`，`pip check` 无缺失 |
| 三项环境配置调用 | 通过 | 最终容器最小调用返回 `CONTAINER_ENV_AUTH_OK`，且 `auth_file_exists=false` |
| 原生 Web Search | 通过 | 收到 `webSearch` item；检索到生态环境部《建设项目环境影响评价分类管理名录（2021年版）》 |
| 官方 URL 可访问 | 通过 | `https://www.mee.gov.cn/gzk/gz/202112/t20211214_964118.shtml` 实测 HTTP 200 |
| 文字 PDF | 通过 | 自动使用 `pdfinfo/pdftotext`，提取 25 页技术协议中的产能、功率、戊烷注入等事实 |
| 扫描 PDF OCR | 通过 | 自动使用 `pdftoppm + tesseract`，识别 EPS 工艺流程图 |
| 图片视觉 | 通过 | SDK `LocalImageInput` 进入 Turn，事件中出现 `imageView`，识别流程节点和侧线 |
| Office 读取 | 通过 | 自动解包 DOCX 正文 XML，识别提示词模块与人工复核约束 |
| 流式事件/结果/Token | 通过 | 收到 `item/started`、delta、`item/completed`、`thread/tokenUsage/updated`、`turn/completed` |
| 结构化输出 | 通过 | 三项主测试均按 JSON Schema 返回可解析对象 |
| 上下文压缩 | 通过 | `compact()` 后在线程历史捕获 `contextCompaction` item |
| 运行中断 | 通过 | `sleep 30` 命令开始后调用 `interrupt()`，Turn 状态为 `interrupted` |
| 无人工审批 | 通过 | 全量事件中没有 approval 请求 |
| 现有服务不受影响 | 通过 | Desktop backend 和 Hermes 仍为 healthy，未重启、未切换流量 |

## 5. 产物

- `scripts/codex_sdk_poc.py`：可重复执行的隔离能力矩阵。
- `Dockerfile.codex-agent-poc`：固定 SDK/runtime 的临时 POC 镜像。
- `logs/codex_replacement_cx01_20260721.md`：实施过程、问题和处置记录。

原始事件日志包含大量上传文档抽取内容，只保留在 `/tmp` 验收目录，不提交 Git；持久验收记录只保存必要事实和非敏感摘要。

## 6. 已识别边界

1. POC 镜像暂时继承现有 `eia-ai-hermes-tools:0.2.0` 以复用 PDF/OCR/Office 工具层，但容器内没有运行 Hermes 服务。CX-02 应建立正式 Codex Agent 镜像命名和 sidecar 服务入口。
2. SDK `compact()` 只返回启动确认。完成状态通过 `thread.read(include_turns=True)` 中的 `contextCompaction` item 判定；不能用超时取消阻塞式全局通知读取，否则会遗留线程。
3. 当前只是 Gate A 原生能力验证，尚未证明 PREP-INGEST、HB-PT-002、HB-PT-009 的业务 Schema 和结果完整性；这些属于 Gate B。
