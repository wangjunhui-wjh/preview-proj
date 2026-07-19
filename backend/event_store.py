from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterator

from .config import settings
from .models import TaskEvent


class EventStore:
    def __init__(self, log_dir: Path | None = None) -> None:
        self.log_dir = log_dir or settings.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, task_id: str) -> Path:
        return self.log_dir / f"task_{task_id}.events.jsonl"

    def append(
        self,
        task_id: str,
        event_type: str,
        message: str = "",
        *,
        node_id: str | None = None,
        payload: dict | None = None,
    ) -> TaskEvent:
        event = TaskEvent(
            id=str(uuid.uuid4()),
            task_id=task_id,
            type=event_type,
            message=message,
            node_id=node_id,
            payload=payload or {},
        )
        path = self.path_for(task_id)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.model_dump(), ensure_ascii=False) + "\n")
        return event

    def iter_events(self, task_id: str) -> Iterator[TaskEvent]:
        path = self.path_for(task_id)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield TaskEvent.model_validate(json.loads(line))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue


event_store = EventStore()
