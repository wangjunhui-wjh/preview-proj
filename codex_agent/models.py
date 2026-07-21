from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


RunStatus = Literal["queued", "running", "completed", "failed", "interrupted"]


class CreateRunRequest(BaseModel):
    input: str = Field(min_length=1, max_length=2_000_000)
    instructions: str | None = Field(default=None, max_length=200_000)
    conversation_history: list[dict[str, str]] = Field(default_factory=list, max_length=100)
    session_id: str = Field(
        default="default",
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    local_images: list[str] = Field(default_factory=list, max_length=32)
    output_schema: dict[str, Any] | None = None


class AgentRun(BaseModel):
    run_id: str
    session_id: str
    status: RunStatus = "queued"
    thread_id: str | None = None
    turn_id: str | None = None
    workspace: str
    output: str = ""
    structured: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    stop_requested: bool = False
    created_at: str = Field(default_factory=now_iso)
    started_at: str | None = None
    completed_at: str | None = None


class CreateRunResponse(BaseModel):
    run_id: str
    status: RunStatus
