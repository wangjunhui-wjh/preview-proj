# 上游模型 503 诊断（2026-07-19）

## 现象

新任务 `3e66d0a2-9e8b-42f1-b02d-6401a85a8bb0` 的 FILE-VALIDATION、PREP-INGEST 和 WEB-SEARCH 均失败，前端显示 `HTTP 503: Service temporarily unavailable`。

## 结论

- Desktop backend 与 Hermes Gateway 的 health 均正常；不是本地服务未就绪。
- Hermes 实际调用的 OpenAI-compatible 上游为 `https://api.aiboys.xyz/v1`，模型为 `gpt-5.5`。
- 每次调用仅约 6.5k token、2 条上下文消息，排除上下文压缩、PDF 大小或长会话作为本次 503 的直接原因。
- Hermes 对每次调用已自动重试三次（约 2 秒、5 秒退避），三次均收到上游 HTTP 503 后才失败。

## 配置变化说明

重建 Hermes 前，旧容器运行配置为 `grok-4.5`；重建后启动钩子按当前 `deploy/desktop/.env` 重新加载，实际模型变为 `gpt-5.5`。本次变更没有修改模型 Key、上游 URL 或模型名；重建使此前未生效的本地 `.env` 配置生效。

## 处理边界

未自动切换模型、未改写 `.env`、未自动重试失败任务。后续应由用户确认：等待当前上游 `gpt-5.5` 服务恢复后重试，或将 `OPENAI_MODEL` 改回已验证可用的模型后重建 Hermes。
