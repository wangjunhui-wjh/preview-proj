# 单机版最小交付分支记录（2026-07-19）

## 分支

- 分支：`desktop-edition`
- 隔离 worktree：`/home/dev/projects/preview-proj-desktop-edition`
- 本地提交：`dad3bd9 release: add minimal desktop edition`

## 纳入范围

- 应用源码：`backend/`、`frontend/`、`prompts/`。
- 单机部署：`deploy/desktop/` 的 Compose、启停、日志、备份脚本和 `.env.example`，不含 `.env`、`runtime/`、`backups/`。
- 容器构建：`Dockerfile.backend`、`Dockerfile.hermes`、`docker/hermes/start-hermes.sh`、依赖清单、当前 Web 入口 HTML。

## 排除范围

- 历史项目资料、任务结果、知识库、运行日志、PPT、竞赛材料、文档归档、Qoder Skill、测试脚本、服务器版和离线镜像包。
- 单机版分支自身的 `.gitignore` 与 `.dockerignore` 会排除模型配置、本地运行数据、备份和 Python 缓存。

## 验收

- 后端 Python 编译通过。
- 前端 JavaScript 语法检查通过。
- `docker compose --env-file deploy/desktop/.env.example -f deploy/desktop/compose.yaml config --quiet` 通过。
- 已确认线上 Desktop 容器仍为 healthy；整个过程未切换主工作区分支、未停止或重启服务。

## 推送状态

2026-07-19 两次使用 SSH-over-443 推送均在 GitHub 密钥交换阶段被本地网络关闭（`Connection closed by 198.18.0.20 port 443`）。本地分支和提交已完整存在；网络恢复后在隔离 worktree 运行 `git push -u origin desktop-edition` 即可推送。
