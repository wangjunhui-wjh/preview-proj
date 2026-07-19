# 模型对照测试切换记录（2026-07-19）

- `deploy/desktop/.env` 的 `OPENAI_MODEL` 已由 `grok-4.5` 改为 `gpt-5.6-terra`。
- `OPENAI_BASE_URL`、模型 Key 和任务数据未修改。
- 使用 `deploy/desktop/lib.sh` 的环境隔离 Compose 包装器仅重建 Hermes，避免宿主 Shell 的 `OPENAI_*` 覆盖 `.env`。
- 容器实际模型：`gpt-5.6-terra`；实际 URL：`https://api.aiboys.xyz/v1`。
- Hermes 与 backend healthy，当前任务未自动重跑。
- 对照测试目标：在相同资料、提示词和 HB-PT-002 流程下，观察是否仍出现普通文本 `finish_reason=stop`、无成果文件的提前结束。
