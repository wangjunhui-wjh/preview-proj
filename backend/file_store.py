from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from .config import settings
from .models import EiaTaskState, FileRef


def _safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-（）()[]【】 " else "_" for ch in name).strip() or "file"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileStore:
    def upload_dir_for(self, task_id: str) -> Path:
        path = settings.upload_dir / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def workspace_for(self, task_id: str) -> Path:
        path = settings.workspace_dir / task_id
        for child in ("project_files", "evidence_files", "knowledge_refs", "candidate_refs", "prompts", "previous_results", "node_output"):
            (path / child).mkdir(parents=True, exist_ok=True)
        return path

    def workspace_project_file_path(self, task_id: str, file_ref: FileRef) -> Path:
        name = _safe_name(Path(file_ref.name).name)
        return self.workspace_for(task_id) / "project_files" / f"{file_ref.id}_{name}"

    def _resolve_project_source(self, task: EiaTaskState, file_ref: FileRef) -> Path:
        src = Path(file_ref.path)
        if src.exists():
            return src

        # Older tasks may store host absolute paths such as
        # /home/dev/projects/.../data/uploads/<task_id>/<file>.  In Docker, the
        # same data directory is mounted at /app/data, so remap by task and
        # basename before treating the upload as missing.
        upload_candidate = settings.upload_dir / task.task_id / src.name
        if upload_candidate.exists():
            return upload_candidate

        workspace_candidate = self.workspace_project_file_path(task.task_id, file_ref)
        if workspace_candidate.exists():
            return workspace_candidate

        raise FileNotFoundError(f"Uploaded file is missing: {src}")

    async def save_upload(self, task_id: str, upload: UploadFile) -> FileRef:
        file_id = str(uuid.uuid4())
        name = _safe_name(upload.filename or file_id)
        target = self.upload_dir_for(task_id) / f"{file_id}_{name}"
        with target.open("wb") as fh:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        digest = sha256_file(target)
        return FileRef(
            id=file_id,
            name=upload.filename or name,
            path=str(target),
            size=target.stat().st_size,
            content_type=upload.content_type,
            sha256=digest,
            role="project",
        )

    def prepare_workspace(self, task: EiaTaskState) -> Path:
        workspace = self.workspace_for(task.task_id)
        for file_ref in task.project_files:
            src = self._resolve_project_source(task, file_ref)
            dest = self.workspace_project_file_path(task.task_id, file_ref)
            if not dest.exists() or sha256_file(dest) != file_ref.sha256:
                if src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
        return workspace


file_store = FileStore()
