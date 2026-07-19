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

## DUAL-03 - 2026-07-19

- Added `deploy/desktop/`: local-only Compose for backend and a fully containerized Hermes Controller using Hermes native `terminal.backend: local` inside the Controller container.
- Kept the official Hermes `/init` + s6 entrypoint. The project hook only writes environment-derived config through `cont-init.d`; it does not replace Gateway supervision.
- Added Linux/macOS Shell and Windows PowerShell/bat operating scripts, provider validation for custom/OpenAI/DeepSeek-compatible settings, local-only ports, host UID/GID handling and no-key backup behavior.
- Built and started the complete Desktop Compose stack on alternate ports. Hermes and backend health checks passed; backend `/api/ready` returned `ready`; Hermes ran as the remapped non-root user and could write its persistent workspace while the project workspace remained read-only.

## DUAL-04 - 2026-07-19

- Added `deploy/server/`: Caddy is the only published service; backend and Hermes Controller have no host port bindings.
- Caddy provides TLS and Basic Auth. The server scope remains private single-tenant; it is not presented as user isolation or SaaS authentication.
- Hermes Controller uses the shared derived official image, the Docker socket, native `terminal.backend: docker`, no forwarded environment and host-path parity for Hermes state and vision handoff.
- Built and started the complete Server Compose stack on alternate ports. An unauthenticated request received 401; authenticated Caddy proxying reached backend `/api/ready`; backend and Hermes had no host ports; the remapped Hermes user could access the Docker daemon; generated tool-container configuration had read-only input, writable output/vision, resource limits and no model-key/socket exposure.

## DUAL-05 - 2026-07-19

- Pinned the Python base used by backend/tools, the Caddy runtime and the Alpine backup helper to verified image digests; the official Hermes base was already digest-pinned.
- Added model/port validation, isolated runtime directories, UID/GID handling, localhost-only Desktop ports, Caddy-only Server publication, server TLS/Basic Auth and no-key backup policies.
- Added `deploy/images.manifest`, `deploy/export-images.sh` and `deploy/import-images.sh`. A real 1.8 GB Docker image archive and SHA-256 sidecar were generated under ignored `deploy/image-bundles/`; dry-run import verified the checksum.
- Removed the confusing root legacy Compose deployment. Root start/stop/logs/backup scripts now only dispatch to `deploy/desktop/`; server deployment remains explicit under `deploy/server/`.
- Found and corrected backup write behavior when an old root-owned backup directory exists. The no-network backup helper now writes the archive and returns ownership to the configured deployment UID/GID; both edition backup archives were checked to exclude Hermes `.env` and `auth.json`.

## DUAL-06 - 2026-07-19

- Passed `git diff --check`, POSIX shell syntax checks, Python compilation/import, frontend JavaScript syntax checks and Desktop/Server Compose configuration validation.
- Rebuilt backend, Hermes Controller and document-tool images from their pinned definitions.
- Desktop final smoke on dedicated ports: backend `/api/ready` returned `edition=desktop`; backend and Hermes both became healthy and both published only `127.0.0.1` ports.
- Server final smoke followed the actual startup preparation path: unauthenticated Caddy request returned 401, authenticated HTTPS request returned `edition=server`, and backend/Hermes had null host port mappings. Smoke stacks were stopped after verification.
- Real Hermes PDF/OCR material-reading validation remains recorded in the earlier `HERMES-DOCKER-01` log; it completed a three-PDF `PREP-INGEST` run with output recovery and no manual approval.

## DUAL-07 - 2026-07-19

- Rewrote delivery-facing README/install/Hermes guidance to separate development-only Gateway use from the two fully containerized delivery editions.
- Updated persistent recovery state, implementation plan and final acceptance record. Next action is normal maintenance or a new release; no smoke Compose stack remains running.
