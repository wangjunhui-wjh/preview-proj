# 仓库资料整理记录（2026-07-19）

## 边界

- 整理期间不重启、不构建、不停止 Desktop 服务。
- 未修改 `deploy/desktop/runtime/`；该目录继续保存当前项目测试的任务、资料、日志、知识库与 Hermes 状态。
- 通过运行中容器挂载核对，在线 backend 与 Hermes 只使用 `deploy/desktop/runtime/` 下的目录。

## 已归档

- `archive/roadshow/`：竞赛/路演源材料、PPT 成果与预览、PPT 工具脚本、制作日志和状态文件。
- `archive/legacy-project-analysis/`：旧根目录 `data/`、历史 UUID 任务成果、调试日志、历史状态标记及 Desktop/Server 冒烟运行目录。
- `archive/deliverables/`：历史 Qoder Work Skill 打包文件。

## 根目录收敛

- 需求源、方案、运维/安装手册、开发经验和非运行原型已转入 `docs/` 并按用途分层。
- 保留根目录 `环评前期研判AI助手.html`，因为 `backend/main.py` 直接将其作为当前 Web 入口提供。
- Docker 构建不再复制旧原型和文档副本；归档目录已排除在 Git 和 Docker 构建上下文外。

## 结果

根目录不再保留历史 PPT、竞赛报名材料、PPT 生成依赖、旧根目录运行数据、历史任务输出或调试日志。当前运行目录和在线测试没有被移动。
