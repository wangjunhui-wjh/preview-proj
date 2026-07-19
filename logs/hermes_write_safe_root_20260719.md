# Hermes 成果写入白名单修复

诊断时间：2026-07-19

## 现象

任务 `90510bf2-b7b7-4956-857b-a0a3a6b8566b` 的 `HB-PT-000` 中出现：

```text
File-mutation verifier: files were NOT modified
Write denied: /eia/outputs/... is outside HERMES_WRITE_SAFE_ROOT (/opt/data)
```

该提示不是业务分析结论，而是 Hermes 文件工具的执行错误。

## 根因

- 后端提示 Agent 将可保留成果写入 `/eia/outputs/<task_id>`。
- Desktop Compose 已把该目录以读写方式挂载，目录所有权也正确。
- 官方 Hermes 基础镜像默认 `HERMES_WRITE_SAFE_ROOT=/opt/data`；`write_file` 在系统调用前拒绝任何白名单外路径。
- Desktop 的 `/workspace` 目录同时由镜像 root 创建，权限为 `root:root 755`，与提示词指定的过程文件目录不一致。

## 修复

1. Desktop 与 Server Compose 均将 `HERMES_WRITE_SAFE_ROOT` 设为 `/opt/data:/eia/outputs`。
2. 共享启动钩子在 Hermes s6 UID/GID 重映射前创建并赋权 `/workspace`，权限为 Hermes 用户可写的 `775`。
3. 未放开 `/eia/workspaces`、任意宿主路径或凭据目录。

Hermes 官方 `file_safety.py` 已确认该变量使用操作系统路径分隔符支持多个根目录，Linux 使用 `:`。

## 验收

- 重建后实际 Gateway 进程：`HERMES_WRITE_SAFE_ROOT=/opt/data:/eia/outputs`。
- `/workspace` 所有者：`hermes:hermes`，权限 `775`。
- 真实 Agent run：`run_3117787a05054fc8bf519296b48448e2`。
- Agent 通过 `write_file` 成功写入隔离路径 `/eia/outputs/write-safe-root-smoke-20260719/agent-write.txt`，文件内容为 `safe-root-ok`，权限 `600`，最终输出 `DONE`。
- 重建后的 Hermes 日志未出现 `Write denied`、`File-mutation verifier` 或 `/workspace` Permission denied。

## 历史结果

修复不会修改已经完成节点的既有 Markdown/JSON。要移除页面中保存的旧告警，需要用户从 `HB-PT-000` 手动重新运行该节点；系统不会自动重跑并消耗模型调用。
