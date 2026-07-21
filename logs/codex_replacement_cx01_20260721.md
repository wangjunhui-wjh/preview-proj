# CX-01 Codex SDK 隔离 POC 实施日志

## 2026-07-21

1. 在 `/tmp/eia-codex-sdk-poc-20260721/venv` 安装 `openai-codex==0.144.4`。官方 PyPI 的 128.8 MB runtime 下载过慢，改用阿里云 PyPI 镜像安装完全匹配的 `openai-codex-cli-bin==0.144.4`；`pip check` 通过，CLI 返回 `codex-cli 0.144.4`。
2. 新增 `scripts/codex_sdk_poc.py`，运行时建立独立 `CODEX_HOME` 和 workspace，复制只读测试样本并生成 PNG、纯图片扫描 PDF；覆盖结构化输出、命令执行、Web Search、PDF、OCR、DOCX、视觉、流式事件、Token usage、compact 和 interrupt。
3. 宿主机隔离 POC 首轮能力矩阵通过。发现 `asyncio.wait_for(codex._client.next_notification())` 超时后底层阻塞线程不会同步结束，导致结果已输出但 Python 进程不退出；终止仅属于 POC 的进程后，改为公共 `thread.read(include_turns=True)` 轮询 `contextCompaction` item。假对象专项测试通过。
4. 新增 `Dockerfile.codex-agent-poc`，基于现有文档工具镜像安装固定 Codex SDK/runtime。构建镜像 `eia-codex-agent-poc:0.144.4` 成功。
5. 在只读根文件系统、普通用户、`CapDrop=ALL`、`no-new-privileges`、无 Docker socket/宿主机 home 的临时容器中完成全量矩阵；容器退出码 0，`gate_a_passed=true`。原生 Web Search 返回生态环境部官方 URL，HTTP 实测 200；文档 Agent 自动选择 `pdfinfo/pdftotext/pdftoppm/tesseract/unzip/imageView`。
6. 全量容器验收后发现 SDK `login_api_key()` 会把应用 API Key 写入隔离 `CODEX_HOME/auth.json`。最终实现改为 Provider `env_key=OPENAI_API_KEY`、`requires_openai_auth=false` 并移除 login 调用；宿主机和最终镜像各做一次真实模型复测，均成功且 `auth.json` 不存在。早期两份临时鉴权文件已销毁。
7. 全量报告、事件日志和配置均检查无 Key；临时 POC 容器已删除。当前 Desktop backend/Hermes 健康，未被本阶段修改或重启。

## 结论与下一步

- `CX-01` 完成，Gate A 通过。
- 下一步：`CX-02_CODEX_AGENT_SIDECAR`，先定义通用 AgentClient 契约和 sidecar 内部 API，再接 PREP-INGEST/HB-PT-002/HB-PT-009；当前 Hermes 保持不变直至后续门禁通过。
