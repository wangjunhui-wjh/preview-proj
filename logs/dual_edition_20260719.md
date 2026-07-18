# Dual Edition Implementation Log

## DUAL-01 - 2026-07-19

- Confirmed local Hermes Agent version `0.18.0` and inspected its matching bundled documentation/source.
- Confirmed native capabilities used by this project: Docker/local terminal backends, `/v1/runs`, SSE events, run status/stop/approval, vision, web, browser, code execution, delegation, task-id container labels, resource limits and host volume handoff.
- Official web search returned 503, so capability decisions use the locally installed 0.18.0 documentation and source rather than assumptions about another version.
- Chosen editions: fully container-managed single-user Desktop edition; fully container-managed private single-tenant Server edition with Caddy and Hermes native Docker terminal.
- Explicit non-goal: no custom PDF/OCR/vision/search/agent loop and no multi-tenant SaaS claim.
- Plan and acceptance criteria written to `outputs/双版本系统实施计划与验收标准.md`.

## DUAL-02 - 2026-07-19

- Added configurable deployment edition, CORS allowlist, Agent workspace/output/vision paths and startup recovery settings to the shared backend.
- Added startup orphan recovery: persisted `running` tasks are changed to `paused` before serving requests; failed nodes are not skipped or continued automatically.
- Added an explicit vision-cache handoff contract between the Hermes terminal sandbox and Controller-side `vision_analyze`.
- Locked backend Python dependencies in `requirements.lock` and made the backend image use the lock by default.
- Rebuilt `eia-ai-hermes-tools:0.2.0` as a standalone document-tool image. It contains PDF, OCR, Office, Node, FFmpeg and Python document libraries, but no backend source, runtime data or model key.
- Passed Python compile/import checks, frontend JavaScript checks, Shell checks, Dockerfile build checks, isolated startup-recovery smoke and a full document-tool image build/runtime smoke.
- Changed the Git target to the user's new empty repository `git@github.com:wangjunhui-wjh/preview-proj.git`; the deleted/old repository will not be modified.
