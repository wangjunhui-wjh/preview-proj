# 专项研判一键重跑恢复记录

## 目标

允许已执行过部分或全部专项流程的任务，从 `HB-PT-002` 重新一键运行至 `HB-PT-009`，避免重复读取上传资料和重复提取项目概况。

## 实现

- 当前原型适配层 `frontend/prototype_backend_adapter.js` 与拆分版 `frontend/app.js` 使用同一业务规则。
- 首次运行直接调用 `POST /api/tasks/{task_id}/run-until`，停止节点为 `HB-PT-009`。
- 已存在专项结果或任务已越过 `HB-PT-002` 时，先调用 `POST /api/tasks/{task_id}/rerun/HB-PT-002`。
- 后端现有 rerun 机制会清理 `HB-PT-002` 至 `HB-PT-011` 的状态和输出文件，保留 `PREP-INGEST`、`HB-PT-000`、`HB-PT-001`、上传资料及项目工作区。
- 前端在重置后刷新任务状态，删除浏览器缓存中的旧专项结果，再启动连续运行，避免新旧结果混显。
- `HB-PT-001` 页面会按任务状态显示“运行”或“重新运行”按钮，并说明重跑清理范围。

## 验收

- `node --check frontend/prototype_backend_adapter.js`：通过。
- `node --check frontend/app.js`：通过。
- 原型 HTML 内联脚本解析：通过。
- `git diff --check`：通过。
- Desktop backend 镜像重建并健康；Hermes 容器和模型配置未重建。
- 服务实际返回脚本版本 `20260719-specialty-rerun`，适配层包含 `/rerun/HB-PT-002` 调用。
- 任务 `3e66d0a2-9e8b-42f1-b02d-6401a85a8bb0` 在线触发成功：
  - `node_rerun_requested` 清理节点为 `HB-PT-002` 至 `HB-PT-011`。
  - `task_run_until_started` 的起点为 `HB-PT-002`，停止节点为 `HB-PT-009`。
  - 输出目录仍保留 `PREP-INGEST`、`HB-PT-000`、`HB-PT-001` 全套成果文件。
  - 新 Hermes run 为 `run_eff55a92ad0048c489c2c05fe4046dcf`，记录时正在正常使用 terminal/web_search。

## 当前状态

功能已在线生效；专项长流程仍由用户当前任务继续运行，本次改动未暂停该任务。
