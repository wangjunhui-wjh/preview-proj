# Codex 替换 Hermes 计划制定记录

- 日期：2026-07-20 Asia/Shanghai
- 工作性质：方案制定与验收基线，不实施运行时切换
- 当前分支：`main`
- 当前在线服务：Desktop backend + Hermes，均 healthy
- 当前工作区：制定计划前 clean，`main` 相对 `origin/main` ahead 8

## 已完成调查

1. 恢复 `.state/progress.md`、前次 Hermes/Codex 调研记录和双版本交付计划。
2. 核对本机 Codex CLI `0.144.6`、App Server 帮助、实验特性和当前 Provider 配置边界；未记录 API Key。
3. 官方 Codex manual helper 因站点 HEAD 请求 HTTP 403 失败，后续使用 OpenAI 官方 Codex 文档和 `openai/codex` 官方仓库补齐。
4. 本机生成 App Server 0.144.6 JSON Schema，确认 Thread/Turn、interrupt、结构化输出、图片、Web Search、文件/命令、子 Agent、上下文压缩和 Token 通知协议。
5. 核对官方 `openai-codex` Python SDK：支持 AsyncCodex、流式 Turn、interrupt、resume、compact、图片输入、sandbox 和 Token；PyPI 当前可见版本为 `0.144.4`，需要固定版本。
6. 使用当前 Codex CLI、模型、Responses Provider 执行单次 `standalone_web_search` 烟测，真实产生 `web_search` 事件并返回生态环境部官方 URL；URL HTTP 200。
7. 烟测同时出现一个无关 MCP transport 403，但 Web Search 正常完成。系统方案使用隔离 CODEX_HOME，不继承个人 MCP，以消除该类无关错误和上下文膨胀。
8. 核对现有代码耦合：LangGraph 节点边界可保留；Hermes 依赖主要集中在 `backend/hermes_client.py`、`backend/main.py`、状态字段、前端文案以及 Desktop/Server Compose 和运维脚本。

## 决策

- 采用官方 `openai-codex` Python SDK + 固定 Codex runtime 的独立 Agent sidecar。
- 不使用 Hermes -> Codex MCP 双 Agent。
- 不在业务后端重写 Codex Agent 循环或 App Server JSON-RPC。
- 搜索使用 Codex 原生 Web Search，不增加 Tavily Key；动态网页使用由 Codex 自主调用的成熟 Playwright MCP。
- PDF/OCR/Office 复用现有工具镜像依赖，不重写底层解析。
- 每个业务节点独立 Codex thread，反馈修正恢复节点 thread，重跑创建新 attempt。
- 专用容器作为安全边界，内部使用 `ApprovalMode.never + Sandbox.full_access`；依靠非 root、只读根文件系统、任务挂载和无 Docker socket 限制影响范围，避免无人值守任务等待人工审批。
- Gate A-D 全通过后删除 Hermes；切换期 feature flag 仅供 A/B 和回滚。

## 官方来源

- Codex SDK：https://developers.openai.com/codex/codex-sdk
- Codex App Server：https://developers.openai.com/codex/app-server
- Codex Browser 边界：https://developers.openai.com/codex/browser
- Codex Python SDK 源码：https://github.com/openai/codex/tree/main/sdk/python
- Python SDK API：https://github.com/openai/codex/blob/main/sdk/python/docs/api-reference.md
- Codex TypeScript SDK：https://github.com/openai/codex/blob/main/sdk/typescript/README.md

## 本轮未执行

- 未修改业务源码、Compose 或环境变量。
- 未安装 `openai-codex` 到项目依赖。
- 未构建 Codex 镜像。
- 未重启 backend 或 Hermes。
- 未推进、重跑或修改任何业务任务。

## 下一步

审核计划后进入 `CX-01_CODEX_SDK_ISOLATED_POC`：建立应用专属 CODEX_HOME，固定 SDK/runtime，在临时 POC 中验收模型、Web Search、PDF/OCR、视觉、流式事件、结构化输出和 interrupt；POC 不接当前业务 API，不切换在线服务。
