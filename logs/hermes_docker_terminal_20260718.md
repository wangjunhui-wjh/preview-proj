# Hermes Docker Terminal Change Log

## 2026-07-18 18:35 Asia/Shanghai

User decision: use the current Hermes API Server with one shared persistent Docker terminal sandbox. Do not create a per-task worker layer or a Hermes API extension.

Target runtime:

- Hermes API Server remains the existing host `tmux` service `hermes-eia`.
- `terminal.backend` changes from `local` to `docker`.
- The terminal image will be `eia-ai-hermes-tools:latest` and will include PDF, OCR, document, media, Python and Node tooling.
- Host `data/workspaces` mounts read-only at `/eia/workspaces`.
- Host `outputs` mounts read-write at `/eia/outputs`.
- The sandbox has no Docker socket, no project source mount and no forwarded model credentials.
- `approvals.mode` will be `off` only for this Docker-backed Hermes profile. The backend must not prohibit or manually approve normal Agent scripts.

Completed before runtime switch:

- Added `Dockerfile.hermes-tools` based on the existing local backend image.
- Added Hermes `session_id` support to the backend client.
- Replaced Agent-visible host paths with `/eia/workspaces/<task_id>/...`.
- Added `/eia/outputs/<task_id>` as the Agent artifact path and backend collection fallback.
- Removed prompt restrictions that were only workarounds for host-local approval.

Pending:

1. Build and inspect `eia-ai-hermes-tools:latest`.
2. Back up and switch Hermes terminal configuration, then restart `hermes-eia`.
3. Rebuild/restart the backend and run Docker-sandbox smoke tests followed by a real PDF node.

Rollback:

- Restore the saved `~/.hermes/config.yaml` backup and restart `hermes-eia`.
- The backend changes are compatible with the existing result API, but host-local Hermes will not be able to resolve the new `/eia/...` paths.

## 2026-07-18 18:42 Asia/Shanghai

- The first build was stopped after `deb.debian.org` stalled during the package index download. No image was produced and no runtime service changed.
- Verified `trixie` metadata is reachable from Tsinghua, Alibaba Cloud and Tencent Cloud Debian mirrors (HTTP 200).
- Updated `Dockerfile.hermes-tools` to use the Tsinghua Debian and PyPI mirrors by default. Both are configurable at build time with `APT_MIRROR` and `PIP_INDEX_URL`; a VPN is not required.

## 2026-07-18 18:45 Asia/Shanghai

- Built `eia-ai-hermes-tools:latest` successfully from the Tsinghua mirrors: image ID `sha256:29b37af83ff...`, size 550325741 bytes.
- Runtime checks passed for Poppler (`pdftotext`, `pdfinfo`, `pdftoppm`), Tesseract, LibreOffice, Node/npm, FFmpeg and Python PDF/Office/OCR libraries.
- A fresh tool container has no Docker socket and no project `.env` or data mount. The image intentionally inherits static backend application code from `eia-ai-backend:latest`; it does not contain runtime uploads, task data or credentials.
- Next step: back up and switch the host Hermes terminal configuration, then restart the gateway.

## 2026-07-18 18:47 Asia/Shanghai

- Saved a byte-identical backup at `~/.hermes/config.yaml.bak-20260718-hermes-docker-terminal` before changing runtime configuration.
- Updated `~/.hermes/config.yaml`: Docker terminal backend, `/workspace` working directory, 900-second default command timeout, persistent sandbox, `eia-ai-hermes-tools:latest`, read-only `/eia/workspaces` and read-write `/eia/outputs` host mounts, no forwarded environment variables, and Docker-profile `approvals.mode: off`.
- Gateway restart is required for the terminal configuration bridge to take effect.

## 2026-07-18 18:51 Asia/Shanghai

- Gateway restarted successfully. `/health` returned `ok` and the backend was rebuilt so its Hermes client sends stable task `session_id` values.
- Real run `run_d51b64e252fc400fa33563c2a62a6ba5` completed through the Docker terminal: working directory `/workspace`; `python3 -c` completed without approval; Poppler, Tesseract, LibreOffice, Node and FFmpeg were found; `/eia/workspaces` was readable; the Agent wrote and verified `outputs/hermes-docker-smoke/SMOKE_output.md` through `/eia/outputs`.
- The tool image inherited the backend HTTP health check, which marks command-only sandbox containers unhealthy even though commands execute normally. Added `HEALTHCHECK NONE`; rebuild the image before real project-node validation.

## 2026-07-18 18:55 Asia/Shanghai

- Rebuilt `eia-ai-hermes-tools:latest` after disabling the inherited HTTP health check. New image ID is `sha256:ff6e7467dc46...`; image inspection reports `Healthcheck: {"Test":["NONE"]}`.
- The existing default Docker sandboxes were created from the preceding tag revision. Restart Hermes and remove only those Hermes-labeled test containers before the real-node run so the next terminal session uses the new image.

## 2026-07-18 18:57 Asia/Shanghai

- Restarted `hermes-eia` and removed only the two Hermes-labeled smoke-test containers from the previous image revision. Hermes `/health` and backend `/api/health` are both `ok`; no terminal sandbox is currently reused.
- Prepared real-node validation against task `e098c0e7-d05a-4282-89b8-2053ca4b822c`, which has three staged PDF files under `data/workspaces/<task_id>/project_files` (4.45 MB, 0.92 MB and 0.09 MB). Next action is a single `PREP-INGEST` run only.

## 2026-07-18 19:08 Asia/Shanghai

- Real `PREP-INGEST` run `run_f999ef3f814f45d49db657d1d06f140e` completed for task `e098c0e7-d05a-4282-89b8-2053ca4b822c`. It made 14 model calls and 13 tool rounds, read all three PDFs through `/eia/workspaces/<task_id>/project_files`, and completed without any `approval.request`.
- The Agent used PDF text-layer extraction, PyMuPDF/pdfplumber, page rendering and Tesseract OCR. It wrote `PREP-INGEST.md`, `PREP-INGEST.json`, evidence references and tool trace into `/eia/outputs/<task_id>`; the backend recovered the full result and paused the task at `HB-PT-000` as intended.
- `docker inspect` confirmed the active Hermes terminal containers use `eia-ai-hermes-tools:latest`, expose no health check (`HEALTHCHECK NONE`), have the expected read-only `/eia/workspaces` and read-write `/eia/outputs` mounts, and do not receive model credentials or Docker socket access.
- The run attempted `vision_analyze` for rendered images. This controller-side tool cannot access container-only `/workspace/*.png`, so those calls failed and the Agent fell back to local Tesseract OCR. This is an explicit future image-cache handoff task, not an approval, PDF parsing or model API failure.
- Domestic sources validated: Tsinghua, Alibaba Cloud and Tencent Cloud Debian mirrors returned HTTP 200. The image was built successfully using the Tsinghua defaults; a VPN is not required for this build.
