# CX-02 Codex Agent Sidecar 实施日志

## 2026-07-21

1. 审查当前运行边界：backend 通过 Hermes `/v1/runs`、run 查询、stop 和 SSE；主节点及辅助 Agent 在 `backend/main.py` 中直接解释 Hermes 事件，LangGraph 本身不负责 Agent 工具循环。
2. 新增 `backend/agent_client.py` 中性 Protocol/HTTP 客户端；新增 `codex_agent/` sidecar，直接使用官方 `openai-codex` SDK 0.144.4 管理 Thread/Turn、结构化输出、工具事件、Token、持久状态和 interrupt。
3. 新增 `Dockerfile.codex-agent` 和真实黑盒 smoke。临时容器采用只读根文件系统、普通用户、无 capabilities、无 Docker socket，API 只绑定临时 localhost 端口；未加入当前 Compose。
4. 首轮 smoke 通过 health、401 鉴权、结构化运行、SSE 和 interrupt。密钥全目录扫描发现 Codex shell snapshot 持久化了 app-server 进程环境中的 Key；立即停止容器并销毁敏感临时快照。
5. 依据 Codex 官方 `shell_environment_policy` 配置，增加 `inherit=core` 和敏感变量 glob 排除，并关闭 `shell_snapshot`。同时关闭无关 plugins/apps，避免应用 CODEX_HOME 同步插件缓存。
6. 最终 v4 smoke 通过：结构化 Run completed；流式 message/tool/usage/terminal 事件齐全；活动 Turn stop 后 interrupted/run.cancelled；Agent shell 生成 `env-check.txt=CLEAN`；整个 CODEX_HOME/run/events 对模型 Key 和内部 API Key 扫描 0 命中；无 auth.json、shell snapshot 或 plugin cache。
7. 最终镜像重启后仍可查询 completed Run 的 thread/turn/structured 状态。临时 sidecar 容器已停止并删除；当前 Desktop backend/Hermes 保持 healthy，没有切换执行流量。
8. 正式镜像默认用户固定为 `10001:10001`；不使用 Compose `user:` 覆盖时，独立容器启动和 `/api/ready` 验证通过。

## 下一步

- `CX-03_CODEX_REPRESENTATIVE_NODES`：在 feature flag 下接入 `PREP-INGEST/HB-PT-002/HB-PT-009`，统一 output schema 和事件映射，执行 Gate B；失败时整版回退到当前 Hermes，不混合提交半个节点。
