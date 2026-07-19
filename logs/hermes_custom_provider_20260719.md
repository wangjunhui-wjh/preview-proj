# Hermes 自定义模型 Key 与基地址诊断

诊断时间：2026-07-19

## 结论

新版 Desktop Compose 的模型 Key 没有读取错误，也没有被宿主机环境变量覆盖。问题出在 Hermes 0.18.2 的 custom provider 安全策略及两个基地址变量同时存在时的优先级。

修复后，真实 Hermes Agent run `run_8e7783ebdf974e1db5188d2829eb1afc` 返回 `completed` 和 `OK`，Desktop backend 与 Hermes 均健康。

## 证据链

所有比对仅记录长度和 SHA-256 前缀，不记录真实 Key。

- `deploy/desktop/.env` 的 `OPENAI_API_KEY`、Compose 容器环境、Hermes Gateway 实际进程、Hermes 生成 `/opt/data/.env` 的 Key 指纹一致。
- 同一 Key 从 Hermes 容器直接请求 `https://api.aiboys.xyz/v1/chat/completions` 得到 HTTP 200 和有效 completion。
- 修复前，Hermes Agent `/v1/runs` 得到 `HTTP 401: Invalid API key`；因此不是部署文件未读取，而是 Agent 内部 provider 解析未把该 Key 发往自定义域名。
- 将 provider 改为命名 `custom:eia-managed` 并设置 `key_env: OPENAI_API_KEY` 后，401 消失。
- 随后 Agent 出现空流。请求转储显示 Agent URL 为 `https://api.aiboys.xyz/chat/completions`，缺少 `/v1`；根因是当时遗留的多个同义基地址变量优先级冲突。
- 将 custom/OpenAI-compatible 基地址统一规范为 `/v1` 后，Agent run 成功。

## 代码修复

`docker/hermes/start-hermes.sh` 现在仅接受 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`：

1. 生成 Hermes 原生 `custom_providers` 条目。
2. 使用 `provider: custom:eia-managed` 和 `key_env: OPENAI_API_KEY`。
3. 不在 `config.yaml` 写入 API Key。
4. 将 custom/OpenAI-compatible `base_url` 规范为以 `/v1` 结尾。

`deploy/desktop/lib.sh`、`deploy/desktop/desktop.ps1` 和服务器版 Compose 都会强制使用部署 `.env` 中的同名 `OPENAI_*` 值，防止外部 Shell 覆盖部署配置。

后续按用户要求已进一步收敛：模型配置仅保留 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`。`LLM_*`、`CUSTOM_*`、`DEEPSEEK_*` 不再由部署脚本、Compose 或 Hermes 启动钩子读取。收敛后的 Desktop Agent 验证 run `run_7c2ed2c4eb024c658752aa141cb10ff3` 返回 `completed` 和 `OK`。

## 验收

- Shell 语法检查：通过。
- Git diff 空白检查：通过。
- `deploy/desktop/start.sh`：重建 Hermes 与 backend 后健康通过。
- `GET /api/ready`：返回 `edition=desktop`、Hermes `0.18.2`。
- 直接流式 `chat/completions`：HTTP 200，包含 SSE `data:` 和 `[DONE]`。
- Agent `/v1/runs`：`completed`，输出 `OK`。

## 运行边界

- 本次未自动重新执行失败任务 `90510bf2-b7b7-4956-857b-a0a3a6b8566b` 的 `PREP-INGEST`，避免未经确认再次消耗模型调用。
- 该任务此前的 502 与旧运行栈的视觉文件交接问题仍保留在 `logs/prep_ingest_502_20260719.md`，应从失败边界手动重试并观察新 Desktop 日志。
