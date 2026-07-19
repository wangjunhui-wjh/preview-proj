# 反馈修正与节点成果清理记录

## 本次范围

本次只保证当前节点的反馈修正链路可正确返回成功或失败，不处理节点完成门禁、普通流程或下游节点依赖失效策略。

## 反馈修正调整

- 原型适配层和拆分版前端在提交反馈前建立任务 SSE 连接，能够接收反馈 Agent 的事件。
- 前端检查接口返回的 `NodeResult.status`，失败结果不再提示“修正成功”。
- 后端反馈 Agent 失败时恢复原节点结果，任务置为可重试的暂停状态，并记录 `node_feedback_failed`；不会用失败文本覆盖原结果。
- 反馈错误原因分析同样检查失败状态，但不替换正式节点结果。

## 成果删除调整

原逻辑只匹配 `{node_id}.*`，遗漏 Agent 产生的下划线成果文件。现按节点名前缀清理：

- `{node_id}.md/json/tool_trace/evidence_refs`；
- `{node_id}_report.md`；
- `{node_id}_result.json`；
- `{node_id}_output.md`；
- `{node_id}.feedback_analysis.*`。

只删除指定节点文件，不删除其他节点文件和项目资料。

## 验收

- Python backend 编译：通过。
- 两个前端 JavaScript 语法检查：通过。
- `git diff --check`：通过。
- 临时目录删除测试：目标节点的点号、下划线、反馈分析成果全部删除，其他节点和项目 PDF 保留。
- 当前真实任务 `3e66d0a2-9e8b-42f1-b02d-6401a85a8bb0` 在 `HB-PT-007` 运行中，未调用反馈接口、未修改任务数据、未重启服务。

## 发布状态

源码已修改但尚未重建 Desktop backend，等待当前长任务结束后发布，避免中断正在运行的 Hermes 流程。
