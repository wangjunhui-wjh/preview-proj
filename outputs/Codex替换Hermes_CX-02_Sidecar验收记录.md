# Codex 替换 Hermes：CX-02 Sidecar 验收记录

## 1. 结论

- 结论：`通过`。
- 验收时间：2026-07-21（Asia/Shanghai）。
- 本阶段完成 Codex Agent sidecar 和中性 AgentClient 契约，但未修改当前 backend 的执行器选择，现网仍由 Hermes 执行。
- 下一步：`CX-03_CODEX_REPRESENTATIVE_NODES`，仅接入 `PREP-INGEST/HB-PT-002/HB-PT-009` 三个代表节点并执行 Gate B。

## 2. 实现范围

| 产物 | 作用 |
| --- | --- |
| `backend/agent_client.py` | provider-neutral `AgentClient` Protocol 和 HTTP 客户端 |
| `codex_agent/config.py` | 三项模型配置、路径、并发和隔离设置 |
| `codex_agent/models.py` | Run 请求、状态和响应模型 |
| `codex_agent/runtime.py` | 官方 SDK Thread/Turn、SSE、结果、Token、工具事件和 interrupt |
| `codex_agent/main.py` | FastAPI sidecar：health、create/get/stop/events |
| `Dockerfile.codex-agent` | 固定 SDK/runtime 的正式 sidecar 镜像 |
| `scripts/cx02_sidecar_smoke.py` | 中性客户端黑盒验收 |

Sidecar 没有实现第二套 Agent 规划或工具循环；Shell、Web Search、视觉、上下文和工具调用仍由 Codex SDK 自带 App Server/Codex 完成。

## 3. API 契约

- `GET /health`、`GET /api/ready`：SDK/runtime/model/wire API 和活动运行数。
- `POST /v1/runs`：input、instructions、session、图片路径、output schema。
- `GET /v1/runs/{run_id}`：状态、thread/turn、输出、结构化结果、Token 和工具轨迹。
- `POST /v1/runs/{run_id}/stop`：对活动 Turn 调用 SDK `interrupt()`。
- `GET /v1/runs/{run_id}/events`：SSE，提供 run、message delta、tool、usage、reasoning signal 和 terminal 事件。

事件层不保存或展示隐藏思维链；只发 `reasoning.available` 信号和可公开的工具摘要。

## 4. 容器验收

| 项目 | 结果 |
| --- | --- |
| 镜像 | `eia-codex-agent:0.144.4-cx02` |
| 镜像 ID | `sha256:a0d73a878ba262abbe97fbba924dd20b9c74b9ca4a79679ae146e6b4e83fddea` |
| SDK/runtime | `0.144.4 / 0.144.4` |
| 镜像默认用户 | `10001:10001`，默认用户启动 readiness 通过 |
| API wire | Responses |
| 未授权访问 | `POST /v1/runs` 返回 401 |
| 结构化运行 | `completed`，Schema 可解析，命令写入和读取结果一致 |
| 流式事件 | `message.delta/tool.started/tool.completed/usage.updated/run.completed` 均存在 |
| 中断 | 活动 Turn stop 后为 `interrupted`，终态事件为 `run.cancelled` |
| 重启恢复 | Sidecar 重启后仍可查询已完成 Run 的 thread/turn/structured 状态 |
| 现网影响 | Desktop backend/Hermes 均 healthy，未重启、未切流量 |

最终 smoke Run：

- 结构化运行：`run_59acafb9b62f447cab9339e5b7513d0a`。
- 中断运行：`run_dcf6d5617e474ada973acf11bf19927b`。

## 5. 安全验收

- 容器只读根文件系统、普通用户、`CapDrop=ALL`、`no-new-privileges`。
- 仅挂载 `/opt/data`、只读输入、输出和只读视觉目录；无 Docker socket、宿主机 home、Git/SSH 凭据。
- Provider 用 `env_key=OPENAI_API_KEY`，不生成 `auth.json`。
- 按 Codex 官方配置参考设置 `shell_environment_policy.inherit="core"` 和 Key glob 排除；同时关闭 `shell_snapshot`，避免 app-server 进程环境被持久化到快照。[Codex Configuration Reference](https://developers.openai.com/codex/config-reference)
- smoke 让 Agent shell 实际检查两个 Key 是否存在，写入 `env-check.txt=CLEAN`。
- 对整个应用 `CODEX_HOME`、run state 和 event log 扫描模型 Key/内部 API Key，0 命中。
- `plugins=false`、`apps=false`，没有插件缓存或个人 MCP；仅保留 SDK 自带的 `.system` 基础能力，不挂载开发者个人 Skill。

## 6. 已知边界

1. Run 记录已经持久化，Sidecar 重启后可查询完成结果；活动 Run 的完整恢复和历史 SSE 回放仍属于 CX-06。
2. CX-02 只证明通用单次 Run/Turn/interrupt，不证明环评节点 output schema、依据真实性和连续三次稳定性。
3. 当前 `EiaTaskState/NodeResult` 仍保留 Hermes 命名字段；在代表节点验证通过前不做大范围状态迁移。
