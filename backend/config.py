from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _read_dotenv_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())


def _default_hermes_api_key() -> str:
    return (
        _env("HERMES_API_KEY")
        or _env("API_SERVER_KEY")
        or _read_dotenv_value(Path.home() / ".hermes" / ".env", "API_SERVER_KEY")
    )


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    prompts_dir: Path = ROOT_DIR / "prompts"
    upload_dir: Path = Path(_env("UPLOAD_DIR", str(ROOT_DIR / "data" / "uploads")))
    task_dir: Path = Path(_env("LANGGRAPH_CHECKPOINT_DIR", str(ROOT_DIR / "data" / "tasks")))
    langgraph_checkpoint_db: Path = Path(
        _env("LANGGRAPH_CHECKPOINT_DB", str(ROOT_DIR / "data" / "langgraph_checkpoints.sqlite"))
    )
    workspace_dir: Path = Path(_env("TASK_WORKSPACE_DIR", str(ROOT_DIR / "data" / "workspaces")))
    output_dir: Path = Path(_env("OUTPUT_DIR", str(ROOT_DIR / "outputs")))
    log_dir: Path = Path(_env("LOG_DIR", str(ROOT_DIR / "logs")))
    vision_cache_dir: Path = Path(_env("VISION_CACHE_DIR", str(ROOT_DIR / "data" / "vision-cache")))
    knowledge_dir: Path = Path(_env("KNOWLEDGE_DIR", str(ROOT_DIR / "data" / "knowledge")))
    database_url: str = _env("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'data' / 'app.db'}")
    hermes_base_url: str = _env("HERMES_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
    hermes_api_key: str = _default_hermes_api_key()
    hermes_model: str = _env("HERMES_MODEL", "hermes-agent")
    request_timeout_seconds: float = float(_env("HERMES_REQUEST_TIMEOUT", "1800"))
    max_node_repair_attempts: int = int(_env("MAX_NODE_REPAIR_ATTEMPTS", "1"))
    deployment_edition: str = _env("EIA_DEPLOYMENT_EDITION", "development")
    cors_origins: tuple[str, ...] = _csv_env("EIA_CORS_ORIGINS")
    auto_recover_running_tasks: bool = _bool_env("EIA_AUTO_RECOVER_RUNNING_TASKS", True)
    agent_workspace_root: str = _env("AGENT_WORKSPACE_ROOT", "/eia/workspaces").rstrip("/")
    agent_output_root: str = _env("AGENT_OUTPUT_ROOT", "/eia/outputs").rstrip("/")
    agent_vision_cache_root: str = _env("AGENT_VISION_CACHE_ROOT", "/eia/vision-cache").rstrip("/")
    controller_vision_cache_root: str = _env(
        "HERMES_CONTROLLER_VISION_ROOT",
        _env("AGENT_VISION_CACHE_ROOT", "/eia/vision-cache"),
    ).rstrip("/")

    def ensure_dirs(self) -> None:
        for path in (
            self.upload_dir,
            self.task_dir,
            self.langgraph_checkpoint_db.parent,
            self.workspace_dir,
            self.output_dir,
            self.log_dir,
            self.vision_cache_dir,
            self.knowledge_dir,
            self.knowledge_dir / "policy_files",
            self.knowledge_dir / "web_snapshots",
            self.knowledge_dir / "extracted_text",
            self.knowledge_dir / "indexes",
            self.knowledge_dir / "candidates",
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
