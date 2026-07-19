# Hermes 节点提前结束根因诊断（2026-07-19）

## 结论

`HB-PT-002` 的短句“继续完成……核验……”不是上下文过长、压缩中断、max turns、上游错误或用户暂停导致，而是模型在工具调用后返回了一个没有 tool call 的普通文本响应，并以 `finish_reason=stop` 结束。Hermes 将任何此类普通文本视为本轮 clean completion，业务后端又将 Hermes `run.completed` 无条件视为节点完成，形成两层完成语义错配。

## 证据

- run：`run_9354a3c1cd9f471694736cf49d81fea2`
- Hermes 共执行 5/60 次模型调用、3 个 tool turn，没有达到轮次或预算限制。
- 各次实际输入 token：23,035、29,478、34,601、34,970、35,004；`run.completed.usage.input_tokens=157,088` 是上述 5 次累计，不是单次上下文。
- Hermes 对 `grok-4.5` 使用 500,000 token 窗口；最后一次约占 7%，没有压缩事件。
- 节点开始日志为 `history=0`，未加载跨节点对话历史。
- 第 4 次调用在工具调用后得到空响应，Hermes 已自动追加 continue nudge；第 5 次模型返回 37 字符过程句，日志随后为 `Turn ended: reason=text_response(finish_reason=stop)`。
- 没有生成 `HB-PT-002_result.json` 或 `HB-PT-002_report.md`；后端生成的 `.md/.json` 只是把该短句作为 fallback 保存。

## Hermes 行为

Hermes 0.18.2 的 `agent/conversation_loop.py` 对没有工具调用的普通文本设置 `text_response(finish_reason=...)` 并结束循环。Hermes 自身 `agent/kanban_stop.py` 明确记录同一已知模型行为：模型可能只叙述下一步并以 `finish_reason=stop` 退出；但该 stop guard 仅对设置了 `HERMES_KANBAN_TASK` 的 Kanban worker 生效，本系统通过 Runs API 执行的 EIA 节点不属于 Kanban worker。

## 系统缺口

当前业务提示词已经要求“不要只描述意图”，但提示词约束不是机器可验证的完成协议。后端在 `backend/main.py` 收到 `run.completed` 后立即发出 `node_complete`，随后即使没有 Agent 成果文件，也会用最终短文本生成节点 `.md/.json` 并推进下一节点。

后续修复方向应是为 EIA 节点增加机器门禁或显式完成工具：仅当要求的 Markdown/JSON 成果存在且通过结构校验时才完成；过程句、空结构或缺成果应触发 bounded nudge/重试，最终失败则暂停，不得推进下游节点。
