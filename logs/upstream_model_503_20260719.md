# 上游模型 503 诊断（2026-07-19）

## 现象

新任务 `3e66d0a2-9e8b-42f1-b02d-6401a85a8bb0` 的 FILE-VALIDATION、PREP-INGEST 和 WEB-SEARCH 均失败，前端显示 `HTTP 503: Service temporarily unavailable`。

## 结论

- Desktop backend 与 Hermes Gateway 的 health 均正常；不是本地服务未就绪。
- Hermes 实际调用的 OpenAI-compatible 上游为 `https://api.aiboys.xyz/v1`，模型为 `gpt-5.5`。
- 每次调用仅约 6.5k token、2 条上下文消息，排除上下文压缩、PDF 大小或长会话作为本次 503 的直接原因。
- Hermes 对每次调用已自动重试三次（约 2 秒、5 秒退避），三次均收到上游 HTTP 503 后才失败。

## 配置变化说明

`deploy/desktop/.env` 始终配置为 `grok-4.5`。诊断期间曾直接调用 `docker compose` 重建 Hermes，绕过了 `deploy/desktop/lib.sh` 的环境隔离包装器；宿主 Shell 导出的 `OPENAI_MODEL=gpt-5.5` 与无 `/v1` URL 因 Compose 变量优先级覆盖了 `.env`，导致该临时容器使用错误模型。随后已通过项目包装器仅重建 Hermes，容器实际恢复为 `grok-4.5` 与正确 `/v1` URL，最小真实 Agent 调用成功。503 的直接原因是这次错误的 Shell 环境覆盖，而不是 `.env` 内容变化。

## 处理边界

未改写 `.env`。失败任务保留原错误记录；恢复 Grok 后的新 Agent 调用已正常运行。
