# Hermes 原生上下文压缩加固（2026-07-19）

## 背景

任务 `90510bf2-b7b7-4956-857b-a0a3a6b8566b` 的后段节点出现了短过程句被当作完成成果的情况。诊断期间确认 Hermes 原有配置已启用 `compression.enabled: true`，但没有显式声明原会话内压缩和摘要失败处置。

## 变更

共享启动钩子 `docker/hermes/start-hermes.sh` 现在明确配置 Hermes 原生能力：

- `context.engine: compressor`
- `compression.enabled: true`
- `compression.in_place: true`，在同一 session 内压缩，不旋转 session id。
- `compression.abort_on_summary_failure: true`，摘要生成失败时停止节点，不静默以截断上下文继续。

其余已有参数保持：50% 阈值、20% target ratio、保留最近 20 条及最前 3 条消息。

## 验收

- 仅重建 Desktop `hermes` 服务；backend 未重建，运行目录未移动。
- Hermes health 为 `healthy`，Desktop `/api/ready` 返回 ready。
- 容器实际 `/opt/data/config.yaml` 已确认上述四项配置生效。

## 边界

这项加固不是节点成果门禁修复。若模型在压缩前自行以短过程句 `run.completed`，后端仍需后续通过“完整成果文件/结构化结果缺失即失败”来阻止工作流推进；该项未在本次变更中修改。
