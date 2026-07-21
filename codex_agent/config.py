from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _positive_int(name: str, default: int) -> int:
    value = int(_env(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def normalize_base_url(value: str) -> str:
    normalized = value.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return normalized.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    reasoning_effort: str
    codex_home: Path
    state_dir: Path
    workspace_root: Path
    input_root: Path
    output_root: Path
    vision_root: Path
    max_concurrent_runs: int
    event_heartbeat_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=_env("CODEX_AGENT_API_KEY"),
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=normalize_base_url(_env("OPENAI_BASE_URL")),
            openai_model=_env("OPENAI_MODEL"),
            reasoning_effort=_env("CODEX_REASONING_EFFORT", "xhigh"),
            codex_home=Path(_env("CODEX_HOME", "/opt/data/codex-home")),
            state_dir=Path(_env("CODEX_RUN_STATE_DIR", "/opt/data/runs")),
            workspace_root=Path(_env("CODEX_WORKSPACE_ROOT", "/opt/data/workspaces")),
            input_root=Path(_env("AGENT_INPUT_ROOT", "/eia/workspaces")),
            output_root=Path(_env("AGENT_OUTPUT_ROOT", "/eia/outputs")),
            vision_root=Path(_env("AGENT_VISION_ROOT", "/eia/vision-cache")),
            max_concurrent_runs=_positive_int("CODEX_MAX_CONCURRENT_RUNS", 2),
            event_heartbeat_seconds=_positive_int("CODEX_EVENT_HEARTBEAT_SECONDS", 15),
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("OPENAI_API_KEY", self.openai_api_key),
                ("OPENAI_BASE_URL", self.openai_base_url),
                ("OPENAI_MODEL", self.openai_model),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required settings: {', '.join(missing)}")
        if self.reasoning_effort not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
            raise RuntimeError(f"Unsupported CODEX_REASONING_EFFORT: {self.reasoning_effort}")

    def ensure_dirs(self) -> None:
        for path in (self.codex_home, self.state_dir, self.workspace_root, self.output_root):
            path.mkdir(parents=True, exist_ok=True)
