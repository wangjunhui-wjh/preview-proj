from __future__ import annotations

import json
from pathlib import Path

from .config import settings
from .models import EiaTaskState, now_iso


class TaskStore:
    def __init__(self, task_dir: Path | None = None) -> None:
        self.task_dir = task_dir or settings.task_dir
        self.task_dir.mkdir(parents=True, exist_ok=True)

    def task_path(self, task_id: str) -> Path:
        return self.task_dir / task_id / "state.json"

    def create(self, task: EiaTaskState) -> EiaTaskState:
        path = self.task_path(task.task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.save(task)
        return task

    def get(self, task_id: str) -> EiaTaskState:
        path = self.task_path(task_id)
        if not path.exists():
            raise FileNotFoundError(task_id)
        return EiaTaskState.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self, task: EiaTaskState) -> EiaTaskState:
        task.updated_at = now_iso()
        path = self.task_path(task.task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(task.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)
        return task

    def list(self) -> list[EiaTaskState]:
        tasks: list[EiaTaskState] = []
        for path in sorted(self.task_dir.glob("*/state.json")):
            tasks.append(EiaTaskState.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return tasks


task_store = TaskStore()

