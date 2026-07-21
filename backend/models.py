from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


TaskStatus = Literal["created", "running", "paused", "failed", "completed"]
AgentProvider = Literal["codex", "hermes"]
DocumentStatus = Literal["candidate", "verified_candidate", "verified", "rejected", "deprecated"]
DocumentValidity = Literal["effective", "superseded", "expired", "unknown"]


class FileRef(BaseModel):
    id: str
    name: str
    path: str
    size: int = 0
    content_type: str | None = None
    sha256: str | None = None
    role: Literal["project", "evidence", "knowledge", "candidate"] = "project"
    created_at: str = Field(default_factory=now_iso)


class EvidenceRef(BaseModel):
    id: str
    source_type: Literal["file", "url", "tool", "knowledge"] = "tool"
    title: str = ""
    source_url: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    page: int | None = None
    knowledge_document_id: str | None = None
    quote: str | None = None
    retrieved_at: str | None = None
    confidence: str | None = None


class TaskEvent(BaseModel):
    id: str
    task_id: str
    type: str
    message: str = ""
    node_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)


class NodeResult(BaseModel):
    node_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    title: str = ""
    markdown: str = ""
    structured: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    output_files: list[str] = Field(default_factory=list)
    agent_provider: AgentProvider | None = None
    agent_run_id: str | None = None
    # Deprecated compatibility field for historical Hermes results.
    hermes_run_id: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class EiaTaskState(BaseModel):
    task_id: str
    status: TaskStatus = "created"
    current_node: str | None = None
    next_node: str | None = "PREP-INGEST"
    pause_requested: bool = False
    active_agent_provider: AgentProvider | None = None
    active_agent_run_id: str | None = None
    # Deprecated compatibility field for tasks created before provider-neutral state.
    active_hermes_run_id: str | None = None
    project_text: str = ""
    project_files: list[FileRef] = Field(default_factory=list)
    evidence_files: list[FileRef] = Field(default_factory=list)
    knowledge_doc_ids: list[str] = Field(default_factory=list)
    candidate_doc_ids: list[str] = Field(default_factory=list)
    selected_modules: list[str] = Field(default_factory=list)
    prompt_overrides: dict[str, str] = Field(default_factory=dict)
    module_results: dict[str, NodeResult] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    error: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    source_type: Literal["official_url", "uploaded_file", "web_candidate"] = "web_candidate"
    source_url: str | None = None
    source_domain: str | None = None
    issuer: str | None = None
    doc_no: str | None = None
    published_at: str | None = None
    retrieved_at: str = Field(default_factory=now_iso)
    file_hash: str | None = None
    status: DocumentStatus = "candidate"
    validity: DocumentValidity = "unknown"
    local_path: str | None = None
    text_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    next_node: str | None


class StepResponse(BaseModel):
    task_id: str
    status: TaskStatus
    current_node: str | None
    next_node: str | None
    result: NodeResult | None = None
