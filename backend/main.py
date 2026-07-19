from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import asyncio
from contextlib import asynccontextmanager
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .event_store import event_store
from .file_store import file_store
from .graph import EiaGraphRuntime
from .hermes_client import hermes_client
from .knowledge_ingestion import ingest_url_candidate
from .knowledge_store import knowledge_store
from .models import CreateTaskResponse, EiaTaskState, EvidenceRef, NodeResult, StepResponse, now_iso
from .task_store import task_store
from .validators import clean_markdown_output, extract_structured_result


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    if settings.auto_recover_running_tasks:
        try:
            await _recover_running_tasks_impl(mode="pause", force=True)
        except Exception as exc:  # noqa: BLE001
            event_store.append("system", "startup_recovery_failed", str(exc))
    yield


app = FastAPI(title="EIA Pre-Assessment AI Assistant", version="0.2.0", lifespan=_app_lifespan)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
app.mount("/assets", StaticFiles(directory=settings.root_dir / "frontend"), name="assets")


NODE_PROMPTS = {
    "PREP-INGEST": "prep_ingest_project_dossier.txt",
    "HB-PT-000": "hb_pt_000_completeness.txt",
    "HB-PT-001": "hb_pt_001_profile.txt",
    "HB-PT-002": "hb_pt_002_eia_category.txt",
    "HB-PT-003": "hb_pt_003_policy.txt",
    "HB-PT-004": "hb_pt_004_planning.txt",
    "HB-PT-005": "hb_pt_005_zoning.txt",
    "HB-PT-006": "hb_pt_006_yangtze.txt",
    "HB-PT-007": "hb_pt_007_two_high_chemical.txt",
    "HB-PT-008": "hb_pt_008_approval_principles.txt",
    "HB-PT-009": "hb_pt_009_similar_projects.txt",
    "HB-PT-010": "hb_pt_010_report.txt",
    "HB-PT-011": "hb_pt_011_consistency.txt",
}

NODE_TITLES = {
    "PREP-INGEST": "项目资料读取与项目档案构建",
    "HB-PT-000": "项目资料完整性审查与模块选择",
    "HB-PT-001": "项目概况提取",
    "HB-PT-002": "行业类别、环评类别及审批路径判定",
    "HB-PT-003": "产业政策符合性分析",
    "HB-PT-004": "规划及规划环评符合性分析",
    "HB-PT-005": "生态环境分区管控符合性分析",
    "HB-PT-006": "长江保护及岸线管控符合性分析",
    "HB-PT-007": "两高项目或化工项目管理要求符合性分析",
    "HB-PT-008": "行业环评审批原则符合性分析",
    "HB-PT-009": "同类项目污染节点与治理措施借鉴分析",
    "HB-PT-010": "综合研判报告生成",
    "HB-PT-011": "交叉一致性核查与人工复核清单生成",
    "FILE-VALIDATION": "上传资料有效性与可用性验证",
    "WEB-SEARCH": "联网检索与候选依据发现",
}

NEXT_NODE = {
    "PREP-INGEST": "HB-PT-000",
    "HB-PT-000": "HB-PT-001",
    "HB-PT-001": "HB-PT-002",
    "HB-PT-002": "HB-PT-003",
    "HB-PT-003": "HB-PT-004",
    "HB-PT-004": "HB-PT-005",
    "HB-PT-005": "HB-PT-006",
    "HB-PT-006": "HB-PT-007",
    "HB-PT-007": "HB-PT-008",
    "HB-PT-008": "HB-PT-009",
    "HB-PT-009": "HB-PT-010",
    "HB-PT-010": "HB-PT-011",
    "HB-PT-011": None,
}

MAX_EVIDENCE_URLS_PER_NODE = 20
VALID_KNOWLEDGE_STATUSES = {"verified", "verified_candidate", "rejected", "deprecated"}
VALID_KNOWLEDGE_VALIDITY = {"effective", "superseded", "expired", "unknown"}
AGENT_WORKSPACE_ROOT = settings.agent_workspace_root
AGENT_OUTPUT_ROOT = settings.agent_output_root
AGENT_VISION_CACHE_ROOT = settings.agent_vision_cache_root
CONTROLLER_VISION_CACHE_ROOT = settings.controller_vision_cache_root
STRUCTURED_TITLE_KEYS = (
    "file_name",
    "document_name",
    "policy_name",
    "standard_name",
    "title",
    "name",
)
RUNNING_TASKS: set[str] = set()


def _load_prompt(name: str) -> str:
    path = settings.prompts_dir / name
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding="utf-8")


def _task_or_404(task_id: str) -> EiaTaskState:
    try:
        return task_store.get(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}") from None


def _output_path(task_id: str, file_name: str) -> Path:
    base = settings.output_dir.resolve()
    path = (base / task_id / file_name).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid output path")
    return path


def _task_output_manifest(task_id: str) -> list[dict[str, Any]]:
    out_dir = settings.output_dir / task_id
    if not out_dir.exists():
        return []
    files = []
    for path in sorted(out_dir.glob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        files.append({"name": path.name, "size": stat.st_size, "modified_at": stat.st_mtime})
    return files


async def _task_manifest_payload(task_id: str) -> dict[str, Any]:
    task = _task_or_404(task_id)
    events = [event.model_dump() for event in event_store.iter_events(task_id)]
    candidate_docs = []
    for doc_id in task.candidate_doc_ids:
        doc = knowledge_store.get_document(doc_id)
        if doc:
            candidate_docs.append(doc.model_dump())
    knowledge_docs = []
    for doc_id in task.knowledge_doc_ids:
        doc = knowledge_store.get_document(doc_id)
        if doc:
            knowledge_docs.append(doc.model_dump())
    return {
        "task": task.model_dump(),
        "events_tail": events[-80:],
        "outputs": _task_output_manifest(task_id),
        "candidate_documents": candidate_docs,
        "knowledge_documents": knowledge_docs,
        "graph_checkpoint": await graph_runtime.checkpoint_state(task_id),
    }


def _result_markdown_or_placeholder(task: EiaTaskState, node_id: str) -> str:
    result = task.module_results.get(node_id)
    if not result:
        return "未生成。"
    if result.markdown.strip():
        return result.markdown.strip()
    if result.error:
        return f"节点失败：{result.error}"
    return "已运行，但没有 Markdown 输出。"


def _combined_report_markdown(task: EiaTaskState) -> str:
    lines: list[str] = [
        "# 环评前期研判报告",
        "",
        "> AI 辅助生成，所有结论需由环评工程师人工复核确认。",
        "",
        "## 任务信息",
        "",
        f"- 任务 ID：`{task.task_id}`",
        f"- 任务状态：`{task.status}`",
        f"- 当前节点：`{task.current_node or ''}`",
        f"- 下一节点：`{task.next_node or ''}`",
        f"- 创建时间：`{task.created_at}`",
        f"- 更新时间：`{task.updated_at}`",
        "",
    ]
    if task.project_text.strip():
        project_excerpt = re.sub(r"\s+", " ", task.project_text.strip())[:1800]
        lines.extend(["## 项目原始材料摘要", "", project_excerpt, ""])
    if task.project_files:
        lines.extend(["## 上传资料", ""])
        for ref in task.project_files:
            lines.append(f"- {ref.name}；size={ref.size}；sha256={ref.sha256 or ''}")
        lines.append("")

    if "PREP-INGEST" in task.module_results:
        lines.extend(["## 项目档案（PREP-INGEST）", "", _result_markdown_or_placeholder(task, "PREP-INGEST"), ""])
    lines.extend(["## 综合研判结论（HB-PT-010）", "", _result_markdown_or_placeholder(task, "HB-PT-010"), ""])
    lines.extend(["## 交叉一致性核查（HB-PT-011）", "", _result_markdown_or_placeholder(task, "HB-PT-011"), ""])
    lines.extend(["## 节点过程结果", ""])
    for node_id in NODE_PROMPTS:
        if node_id in {"PREP-INGEST", "HB-PT-010", "HB-PT-011"}:
            continue
        if node_id not in task.module_results:
            continue
        lines.extend([f"### {node_id} {NODE_TITLES.get(node_id, '')}", "", _result_markdown_or_placeholder(task, node_id), ""])

    evidence_seen: set[str] = set()
    evidence_rows: list[EvidenceRef] = []
    for result in task.module_results.values():
        for ref in result.evidence_refs:
            key = ref.source_url or ref.file_path or ref.file_name or ref.title or ref.id
            if key in evidence_seen:
                continue
            evidence_seen.add(key)
            evidence_rows.append(ref)
    if evidence_rows:
        lines.extend(["## 依据索引", "", "| 类型 | 标题 | 来源 | 可信度 |", "| --- | --- | --- | --- |"])
        for ref in evidence_rows:
            source = ref.source_url or ref.file_name or ref.file_path or ""
            lines.append(
                f"| {ref.source_type} | {ref.title or '未命名'} | {source} | {ref.confidence or ''} |"
            )
        lines.append("")

    outputs = _task_output_manifest(task.task_id)
    if outputs:
        lines.extend(["## 输出文件清单", ""])
        for item in outputs:
            lines.append(f"- `{item['name']}` ({item['size']} bytes)")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _rebuild_task_evidence_from_results(task: EiaTaskState) -> None:
    evidence_refs = []
    candidate_doc_ids = []
    for result in task.module_results.values():
        for ref in result.evidence_refs:
            evidence_refs.append(ref)
            if ref.knowledge_document_id and ref.knowledge_document_id not in candidate_doc_ids:
                candidate_doc_ids.append(ref.knowledge_document_id)
    task.evidence_refs = evidence_refs
    task.candidate_doc_ids = candidate_doc_ids


def _remove_node_outputs(task_id: str, node_ids: list[str]) -> None:
    out_dir = settings.output_dir / task_id
    if not out_dir.exists():
        return
    prefixes = tuple(prefix for node_id in node_ids for prefix in (f"{node_id}.", f"{node_id}_"))
    for path in out_dir.iterdir():
        if path.is_file() and path.name.startswith(prefixes):
            path.unlink()


def _extract_urls(text: str) -> list[str]:
    trailing_punctuation = ".,;:!?)]}"
    candidates = re.findall(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&()*+,;=%-]+", text or "")
    urls = [url.rstrip(trailing_punctuation) for url in candidates]
    return sorted({url for url in urls if _is_valid_evidence_url(url)})


def _is_valid_evidence_url(url: str) -> bool:
    if not url or re.search(r"\s", url):
        return False
    if "附件URL" in url or "URL：" in url or "；" in url:
        return False
    if url.count("http://") + url.count("https://") != 1:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _collect_evidence_url_candidates(markdown: str, structured: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    def add(url: str, *, title: str = "", source: str) -> None:
        if not _is_valid_evidence_url(url):
            return
        current = candidates.setdefault(url, {"url": url, "title": title, "sources": []})
        if title and not current.get("title"):
            current["title"] = title
        if source not in current["sources"]:
            current["sources"].append(source)

    for url in _extract_urls(markdown):
        add(url, source="markdown")

    def walk(value: Any, path: str = "$", context_title: str = "") -> None:
        if isinstance(value, dict):
            title = context_title
            for key in STRUCTURED_TITLE_KEYS:
                raw = value.get(key)
                if isinstance(raw, str) and raw.strip():
                    title = raw.strip()
                    break
            for key, item in value.items():
                walk(item, f"{path}.{key}", title)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]", context_title)
        elif isinstance(value, str):
            for url in _extract_urls(value):
                add(url, title=context_title, source=f"structured:{path}")

    if structured:
        walk(structured)
    return list(candidates.values())[:MAX_EVIDENCE_URLS_PER_NODE]


def _module_output_context(task: EiaTaskState) -> str:
    payload: dict[str, Any] = {}
    for code, result in task.module_results.items():
        if result.status != "completed":
            continue
        payload[code] = result.structured or {"markdown": result.markdown}
    if not payload:
        return "暂无已完成模块输出。"
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _project_dossier_context(task: EiaTaskState) -> str:
    result = task.module_results.get("PREP-INGEST")
    if result and result.status == "completed":
        if result.structured:
            return json.dumps(result.structured, ensure_ascii=False, indent=2)
        if result.markdown.strip():
            return result.markdown
    return task.project_text or "未提供"


def _project_material_context(task: EiaTaskState, node_id: str) -> str:
    if node_id == "PREP-INGEST":
        return task.project_text or "未提供"
    return _project_dossier_context(task)


def _project_profile_context(task: EiaTaskState) -> str:
    result = task.module_results.get("HB-PT-001")
    if result and result.status == "completed":
        return json.dumps(result.structured, ensure_ascii=False, indent=2) if result.structured else result.markdown
    return _project_dossier_context(task)


def _final_report_context(task: EiaTaskState) -> str:
    result = task.module_results.get("HB-PT-010")
    return result.markdown if result and result.status == "completed" else "暂无综合研判报告。"


def _knowledge_evidence_context(task: EiaTaskState) -> str:
    docs = []
    selected_doc_ids = list(task.knowledge_doc_ids)
    auto_included = False
    if not selected_doc_ids:
        selected_doc_ids = [
            doc.id
            for doc in knowledge_store.list_documents(status="verified")
            if doc.validity == "effective"
        ][:5]
        auto_included = bool(selected_doc_ids)

    for doc_id in selected_doc_ids:
        doc = knowledge_store.get_document(doc_id)
        if not doc or doc.status != "verified":
            continue
        excerpt = ""
        if doc.text_path:
            text_path = Path(doc.text_path)
            if text_path.exists():
                text = text_path.read_text(encoding="utf-8", errors="ignore").strip()
                excerpt = re.sub(r"\s+", " ", text)[:1200]
        docs.append(
            {
                "id": doc.id,
                "title": doc.title,
                "issuer": doc.issuer,
                "doc_no": doc.doc_no,
                "published_at": doc.published_at,
                "validity": doc.validity,
                "source_url": doc.source_url,
                "file_hash": doc.file_hash,
                "local_path": doc.local_path,
                "text_path": doc.text_path,
                "excerpt": excerpt,
            }
        )
    if not docs:
        return "当前任务未选择已确认政策库依据。必要时请自行使用 web_search，并记录真实 URL。"
    intro = (
        "当前任务未显式选择政策库依据；以下为政策库中已人工确认且有效的官方依据，供优先核验使用。"
        if auto_included
        else "以下为本任务已确认并选择使用的政策库依据。"
    )
    return (
        f"{intro} 请优先引用这些依据；如依据不足，仍可使用 web_search 补充真实 URL。\n"
        + json.dumps(docs, ensure_ascii=False, indent=2)
    )


def _node_output_budget(node_id: str) -> str:
    if node_id in {"FILE-VALIDATION", "WEB-SEARCH"}:
        return "Markdown 建议不超过 3000 个中文字符；JSON 建议不超过 120 行。"
    if node_id == "PREP-INGEST":
        return "Markdown 建议不超过 5000 个中文字符；JSON 建议不超过 160 行。"
    if node_id in {"HB-PT-010", "HB-PT-011"}:
        return "Markdown 建议不超过 3500 个中文字符；JSON 建议不超过 120 行。"
    return "Markdown 建议不超过 2200 个中文字符；JSON 建议不超过 80 行。"


def _aux_output_prefix(node_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", node_id).strip("_") or "AUX"


def _agent_workspace_path(task_id: str) -> str:
    return f"{AGENT_WORKSPACE_ROOT}/{task_id}"


def _agent_project_file_path(task_id: str, file_ref: Any) -> str:
    name = file_store.workspace_project_file_path(task_id, file_ref).name
    return f"{_agent_workspace_path(task_id)}/project_files/{name}"


def _agent_artifact_path(task_id: str) -> str:
    return f"{AGENT_OUTPUT_ROOT}/{task_id}"


def _agent_vision_cache_path(task_id: str) -> str:
    return f"{AGENT_VISION_CACHE_ROOT}/{task_id}"


def _controller_vision_cache_path(task_id: str) -> str:
    return f"{CONTROLLER_VISION_CACHE_ROOT}/{task_id}"


def _vision_handoff_context(task_id: str) -> str:
    settings.vision_cache_dir.joinpath(task_id).mkdir(parents=True, exist_ok=True)
    return (
        f"视觉缓存写入目录（终端可见）：{_agent_vision_cache_path(task_id)}\n"
        f"视觉工具读取目录（Hermes Controller 可见）：{_controller_vision_cache_path(task_id)}\n"
        "需要用视觉模型分析 PDF 页面或图片时，先在终端将目标页渲染/复制到视觉缓存写入目录，"
        "再把同名文件对应的 Controller 可见绝对路径传给 Hermes 原生 vision_analyze。"
        "不要把仅存在于 /workspace 的路径直接传给 vision_analyze；若视觉调用失败，可使用 OCR 回退并明确标注。"
    )


def _read_agent_workspace_outputs(
    workspace: Path,
    output_prefix: str,
    artifact_dir: Path | None = None,
) -> tuple[str | None, dict[str, Any], dict[str, str]]:
    markdown: str | None = None
    structured: dict[str, Any] = {}
    sources: dict[str, str] = {}

    locations = [artifact_dir, workspace] if artifact_dir else [workspace]
    for location in locations:
        if location is None:
            continue
        markdown_path = location / f"{output_prefix}_output.md"
        if markdown is None and markdown_path.exists():
            text = markdown_path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                markdown = text
                sources["markdown_path"] = str(markdown_path)

        json_path = location / f"{output_prefix}_result.json"
        if not structured and json_path.exists():
            text = json_path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                parsed: Any = None
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = extract_structured_result(text)
                if isinstance(parsed, dict) and parsed:
                    structured = parsed
                    sources["json_path"] = str(json_path)
                elif parsed is not None:
                    sources["json_parse_error"] = "agent result JSON did not contain an object"

    return markdown, structured, sources


async def _execute_hermes_aux_agent(
    *,
    task: EiaTaskState | None,
    node_id: str,
    title: str,
    user_input: str,
    output_task_id: str | None = None,
    persist_result: bool = False,
    output_prefix: str | None = None,
) -> NodeResult:
    started_at = now_iso()
    output_chunks: list[str] = []
    tool_trace: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    output_text = ""
    status = "completed"
    error: str | None = None
    run_id: str | None = None
    event_task_id = output_task_id or (task.task_id if task else "auxiliary")
    output_prefix = output_prefix or _aux_output_prefix(node_id)

    event_store.append(event_task_id, "node_start", f"{node_id} started", node_id=node_id)
    try:
        run = await hermes_client.create_run(user_input, session_id=task.task_id if task else output_task_id)
        run_id = run["run_id"]
        event_store.append(event_task_id, "hermes_run_started", f"Hermes run started: {run_id}", node_id=node_id, payload=run)
        async for event in hermes_client.stream_run_events(run_id):
            kind = event.get("event") or event.get("type")
            if kind == "message.delta":
                delta = event.get("delta") or event.get("text") or ""
                if delta:
                    output_chunks.append(delta)
                continue
            if kind and (kind.startswith("tool.") or kind in {"approval.request"}):
                tool_trace.append(event)
            if kind == "approval.request":
                command = event.get("command") or event.get("description") or "unknown command"
                status = "failed"
                error = (
                    "Hermes requested manual tool approval during unattended auxiliary execution; "
                    f"the run was stopped. Requested action: {command}"
                )
                event_store.append(event_task_id, "node_failed", error, node_id=node_id, payload=event)
                try:
                    await hermes_client.stop_run(run_id)
                except Exception:
                    pass
                break
            if kind == "run.completed":
                output_text = event.get("output", "")
                usage = event.get("usage") or {}
                event_store.append(event_task_id, "node_complete", f"{node_id} completed", node_id=node_id, payload=event)
                break
            if kind in {"run.failed", "error"}:
                status = "failed"
                error = event.get("error") or event.get("message") or json.dumps(event, ensure_ascii=False)
                event_store.append(event_task_id, "node_failed", error, node_id=node_id, payload=event)
                break
            if kind in {"run.cancelled", "run.stopped", "run.expired", "run.timeout"}:
                status = "failed"
                error = f"Hermes run ended before completion: {kind}"
                event_store.append(event_task_id, "node_failed", error, node_id=node_id, payload=event)
                break
            event_store.append(event_task_id, "hermes_event", str(kind or "event"), node_id=node_id, payload=event)
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        error = f"Hermes auxiliary execution error: {exc}"
        event_store.append(event_task_id, "node_failed", error, node_id=node_id, payload={"run_id": run_id})
        if run_id:
            try:
                await hermes_client.stop_run(run_id)
            except Exception:
                pass

    if not output_text and run_id:
        try:
            final = await hermes_client.get_run(run_id)
            output_text = final.get("output") or "".join(output_chunks)
            usage = final.get("usage") or usage
            if final.get("status") not in {"completed", None} and status != "failed":
                status = "failed"
                error = final.get("error") or f"Hermes run ended with status: {final.get('status')}"
        except Exception:
            output_text = "".join(output_chunks)
    if not output_text:
        output_text = "".join(output_chunks)
    if status == "failed" and output_text and error:
        output_text = f"{output_text}\n\n> 辅助 Agent 未完成：{error}"

    workspace = None
    if task:
        workspace = settings.workspace_dir / task.task_id
    elif output_task_id:
        workspace = settings.workspace_dir / output_task_id
    workspace_markdown: str | None = None
    workspace_structured: dict[str, Any] = {}
    workspace_sources: dict[str, str] = {}
    if workspace and workspace.exists():
        artifact_dir = settings.output_dir / event_task_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        workspace_markdown, workspace_structured, workspace_sources = _read_agent_workspace_outputs(
            workspace,
            output_prefix,
            artifact_dir,
        )
        if workspace_sources:
            event_store.append(
                event_task_id,
                "node_workspace_output_used",
                f"{node_id} result collected from workspace files",
                node_id=node_id,
                payload=workspace_sources,
            )

    result_text = workspace_markdown or output_text
    structured = workspace_structured or extract_structured_result(result_text) or extract_structured_result(output_text)
    markdown = clean_markdown_output(result_text)
    if status == "failed" and markdown and error and error not in markdown:
        markdown = f"{markdown}\n\n> 辅助 Agent 未完成：{error}"
    evidence_refs: list[EvidenceRef] = []
    if status != "failed" and (task or output_task_id):
        record_task_id = task.task_id if task else output_task_id
        for candidate in _collect_evidence_url_candidates(markdown, structured):
            url = candidate["url"]
            title_text = candidate.get("title") or ""
            record_id = knowledge_store.record_web_search(
                task_id=record_task_id,
                node_id=node_id,
                query=str(structured.get("query") or ""),
                result_url=url,
                title=title_text,
                snippet="",
                metadata={"source": "aux_agent_output", "sources": candidate.get("sources", [])},
            )
            try:
                existing_doc = knowledge_store.get_active_candidate_by_url(url)
                doc = existing_doc or await ingest_url_candidate(url, title=title_text, task_id=record_task_id, node_id=node_id)
            except Exception as exc:  # noqa: BLE001
                doc = knowledge_store.create_candidate_url(
                    url,
                    title=title_text,
                    metadata={
                        "task_id": record_task_id,
                        "node_id": node_id,
                        "web_search_record_id": record_id,
                        "ingest_error": str(exc),
                        "source": "aux_agent_output",
                    },
                )
            if task and doc.id not in task.candidate_doc_ids:
                task.candidate_doc_ids.append(doc.id)
            evidence_refs.append(
                EvidenceRef(
                    id=str(uuid.uuid4()),
                    source_type="url",
                    title=doc.title or title_text or url,
                    source_url=url,
                    knowledge_document_id=doc.id,
                    retrieved_at=now_iso(),
                    confidence="candidate",
                )
            )

    if output_task_id:
        out_dir = settings.output_dir / output_task_id
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"{output_prefix}.md"
        json_path = out_dir / f"{output_prefix}.json"
        trace_path = out_dir / f"{output_prefix}.tool_trace.json"
        evidence_path = out_dir / f"{output_prefix}.evidence_refs.json"
        md_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(
            json.dumps(structured or {"raw_markdown": markdown, "usage": usage}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        trace_path.write_text(json.dumps(tool_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence_path.write_text(
            json.dumps([ref.model_dump() for ref in evidence_refs], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        output_files = [md_path.name, json_path.name, trace_path.name, evidence_path.name]
    else:
        output_files = []

    result = NodeResult(
        node_id=node_id,
        status=status,
        title=title,
        markdown=markdown,
        structured=structured,
        evidence_refs=evidence_refs,
        tool_trace=tool_trace,
        output_files=output_files,
        hermes_run_id=run_id,
        error=error,
        started_at=started_at,
        completed_at=now_iso(),
    )
    if task:
        if persist_result:
            task.module_results[node_id] = result
            _rebuild_task_evidence_from_results(task)
        for ref in evidence_refs:
            if ref not in task.evidence_refs:
                task.evidence_refs.append(ref)
            if ref.knowledge_document_id and ref.knowledge_document_id not in task.candidate_doc_ids:
                task.candidate_doc_ids.append(ref.knowledge_document_id)
        task_store.save(task)
    return result


def _project_file_context(task: EiaTaskState) -> str:
    lines = []
    for ref in task.project_files:
        lines.append(
            f"- {ref.name}: file_id={ref.id}; sandbox_path={_agent_project_file_path(task.task_id, ref)}; "
            f"size={ref.size}; content_type={ref.content_type or ''}; sha256={ref.sha256 or ''}"
        )
    return "\n".join(lines) or "无上传文件"


def _build_aux_prompt(task: EiaTaskState | None, prompt_name: str, replacements: dict[str, str], *, node_id: str) -> str:
    system_prompt = _load_prompt("system_prompt.txt")
    template = _load_prompt(prompt_name)
    if task:
        replacements = {
            "project_text": _project_material_context(task, node_id),
            "project_profile": _project_profile_context(task),
            "module_outputs": _module_output_context(task),
            "evidence_context": _knowledge_evidence_context(task),
            **replacements,
        }
        task_context = f"""
任务 ID：{task.task_id}
项目文件目录：{_agent_workspace_path(task.task_id)}/project_files
可写成果目录：{_agent_artifact_path(task.task_id)}
{_vision_handoff_context(task.task_id)}
已上传项目文件：
{_project_file_context(task)}
""".strip()
    else:
        replacements = {
            "project_text": "",
            "project_profile": "未绑定任务。",
            "module_outputs": "暂无已完成模块输出。",
            "evidence_context": "未绑定任务。必要时请自行使用 web_search，并记录真实 URL。",
            **replacements,
        }
        task_context = "未绑定具体任务。"
    prompt_text = template
    for key, value in replacements.items():
        prompt_text = prompt_text.replace("{" + key + "}", value)
    return f"""
{system_prompt}

你正在作为 Hermes Agent 执行环评前期研判辅助任务。请自主读取资料、必要时使用 web_search，但不得编造依据。

节点：{node_id}
{task_context}

执行环境：你运行在受控 Hermes Agent 终端执行环境中。可自主选择 Shell、Python、OCR、Hermes 原生视觉、文档转换、网页检索和子 Agent 等能力；不要等待人工命令批准。项目文件目录为只读，必要的过程文件写入 `/workspace`，需要保留的成果可写入上述成果目录。

工作要求：
1. 读取 PDF 时优先识别文字层，再对扫描页或图片页做 OCR/视觉识别；不要把整份 PDF 简单当作图片处理。
2. 政策依据优先使用 web_search/web_extract 返回的官方 URL、标题、摘要和可见正文；如无法抽取正文，记录候选 URL 并标注人工核实。
3. 工具预算：最多组织 8 次 web_search、6 次 web_extract 或浏览器正文读取；达到预算仍无法确认时停止搜索。
4. 输出预算：{_node_output_budget(node_id)} 不要粘贴大段 OCR 原文、政策原文或搜索摘要。

请严格执行以下辅助提示词：

{prompt_text}
""".strip()


@app.get("/")
async def frontend_index() -> FileResponse:
    return FileResponse(
        settings.root_dir / "环评前期研判AI助手.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.get("/app")
async def frontend_app() -> FileResponse:
    return FileResponse(
        settings.root_dir / "环评前期研判AI助手.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


def _node_prompt_template(task: EiaTaskState, node_id: str) -> str:
    override = (task.prompt_overrides or {}).get(node_id, "").strip()
    return override or _load_prompt(NODE_PROMPTS[node_id])


def _build_node_input(task: EiaTaskState, node_id: str, workspace: Path) -> str:
    system_prompt = _load_prompt("system_prompt.txt")
    node_prompt_template = _node_prompt_template(task, node_id)
    project_file_lines = []
    for ref in task.project_files:
        project_file_lines.append(
            f"- {ref.name}: sandbox_path={_agent_project_file_path(task.task_id, ref)}; "
            f"size={ref.size}; content_type={ref.content_type or ''}; sha256={ref.sha256 or ''}"
        )
    project_files = "\n".join(project_file_lines) or "无上传文件"
    evidence_context = _knowledge_evidence_context(task)
    prep_constraint = (
        "\n9. 当前节点是项目资料读取节点：不得使用 web_search 补充项目事实；只能读取用户粘贴文本和上传文件，所有事实必须带来源或标注需人工核实。"
        if node_id == "PREP-INGEST"
        else ""
    )
    prompt_text = node_prompt_template
    prompt_text = prompt_text.replace("{project_text}", _project_material_context(task, node_id))
    prompt_text = prompt_text.replace("{project_profile}", _project_profile_context(task))
    prompt_text = prompt_text.replace("{module_outputs}", _module_output_context(task))
    prompt_text = prompt_text.replace("{final_report}", _final_report_context(task))
    prompt_text = prompt_text.replace("{evidence_context}", evidence_context)
    return f"""
{system_prompt}

你正在作为 Hermes Agent 执行环评前期研判节点。请在工作区内自主读取资料、必要时使用 web_search，但不得编造依据。

任务 ID：{task.task_id}
节点：{node_id}
沙箱工作区：/workspace
项目文件目录：{_agent_workspace_path(task.task_id)}/project_files
可写成果目录：{_agent_artifact_path(task.task_id)}
{_vision_handoff_context(task.task_id)}
已上传项目文件：
{project_files}

执行环境：你运行在受控 Hermes Agent 终端执行环境中。可自主选择 Shell、Python、OCR、Hermes 原生视觉、文档转换、网页检索和子 Agent 等能力；不要等待人工命令批准。项目文件目录为只读，过程文件写入 `/workspace`，需要保留的成果写入上述成果目录。

工作要求：
1. 读取 PDF 时优先识别文字层，再对扫描页或图片页做 OCR/视觉识别；不要把整份 PDF 简单当作图片处理。
2. 政策依据优先使用 web_search/web_extract 返回的官方 URL、标题、摘要和可见正文；如 web_extract 失败，仍可在沙箱内采用适当工具核验，但必须记录真实来源和限制。
3. 工具预算：每个节点最多组织 8 次 web_search、6 次 web_extract 或浏览器正文读取；达到预算仍无法确认时停止搜索，输出“资料不足，建议人工核实”，不要反复变换近义查询词。
4. 输出预算：{_node_output_budget(node_id)} 不要重复输出 Markdown 表格和等价 JSON；JSON 只保留可供程序读取的关键字段、风险项、依据 URL 和需补充资料。{prep_constraint}

请严格执行以下节点提示词：

{prompt_text}

输出格式要求：
1. 先输出 Markdown 结论，便于页面展示。
2. 如能结构化，请额外输出一个 JSON 代码块或 BEGIN_NODE_RESULT_JSON/END_NODE_RESULT_JSON 包裹的 JSON。
3. 所有 URL 依据必须是真实访问或搜索得到的 URL。
4. 如依据不足，请明确写“资料不足，建议人工核实”。
5. 输出应详细但克制：不要粘贴大段 OCR 原文、政策原文或搜索摘要；Markdown 以结论、关键表格和补充清单为主，结构化 JSON 避免重复 Markdown 全文。
""".strip()


async def _run_node(task: EiaTaskState, node_id: str, *, continue_on_success: bool = False) -> NodeResult:
    if node_id not in NODE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Node is not implemented yet: {node_id}")
    started_at = now_iso()
    try:
        workspace = file_store.prepare_workspace(task)
        (settings.output_dir / task.task_id).mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        error = f"Failed to prepare workspace: {exc}"
        result = NodeResult(
            node_id=node_id,
            status="failed",
            title=NODE_TITLES.get(node_id, node_id),
            error=error,
            started_at=started_at,
            completed_at=now_iso(),
        )
        task.status = "failed"
        task.current_node = None
        task.error = error
        task.module_results[node_id] = result
        task_store.save(task)
        event_store.append(task.task_id, "node_failed", error, node_id=node_id)
        return result
    prompts_dir = workspace / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "system_prompt.txt").write_text(_load_prompt("system_prompt.txt"), encoding="utf-8")
    (prompts_dir / NODE_PROMPTS[node_id]).write_text(_node_prompt_template(task, node_id), encoding="utf-8")

    task.status = "running"
    task.current_node = node_id
    task.error = None
    task_store.save(task)
    event_store.append(task.task_id, "node_start", f"{node_id} started", node_id=node_id)

    user_input = _build_node_input(task, node_id, workspace)
    run_id: str | None = None
    output_text = ""
    output_chunks: list[str] = []
    tool_trace: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    status = "completed"
    error: str | None = None
    paused_by_user = False
    pending_delta = ""

    def flush_delta() -> None:
        nonlocal pending_delta
        if not pending_delta:
            return
        event_store.append(
            task.task_id,
            "node_output_partial",
            pending_delta,
            node_id=node_id,
            payload={"run_id": run_id},
        )
        pending_delta = ""

    try:
        run = await hermes_client.create_run(user_input, session_id=task.task_id)
        run_id = run["run_id"]
        latest_task = task_store.get(task.task_id)
        latest_task.current_node = node_id
        latest_task.active_hermes_run_id = run_id
        if not latest_task.pause_requested:
            latest_task.status = "running"
        task_store.save(latest_task)
        event_store.append(
            task.task_id,
            "hermes_call_start",
            f"Hermes run started: {run_id}",
            node_id=node_id,
            payload={"run_id": run_id},
        )

        skip_stream = False
        if latest_task.pause_requested:
            paused_by_user = True
            status = "failed"
            error = "Task paused by user before Hermes event stream opened."
            skip_stream = True
            try:
                stop_result = await hermes_client.stop_run(run_id)
                event_store.append(
                    task.task_id,
                    "hermes_run_stop_requested",
                    f"Stop requested for {run_id}",
                    node_id=node_id,
                    payload=stop_result,
                )
            except Exception as exc:  # noqa: BLE001
                event_store.append(
                    task.task_id,
                    "hermes_run_stop_failed",
                    str(exc),
                    node_id=node_id,
                    payload={"run_id": run_id},
                )
            event_store.append(
                task.task_id,
                "node_paused",
                error,
                node_id=node_id,
                payload={"run_id": run_id, "phase": "before_stream"},
            )

        if not skip_stream:
            async for event in hermes_client.stream_run_events(run_id):
                kind = event.get("event", "unknown")
                if kind in {"tool.started", "tool.completed"}:
                    flush_delta()
                    tool_trace.append(event)
                    event_store.append(
                        task.task_id,
                        "tool_event",
                        event.get("tool") or kind,
                        node_id=node_id,
                        payload=event,
                    )
                elif kind == "message.delta":
                    delta = event.get("delta", "")
                    output_chunks.append(delta)
                    pending_delta += delta
                    if len(pending_delta) >= 160 or ("\n" in pending_delta and len(pending_delta) >= 60):
                        flush_delta()
                elif kind == "reasoning.available":
                    flush_delta()
                    event_store.append(
                        task.task_id,
                        "agent_reasoning_signal",
                        "Agent reasoning signal received; internal reasoning text is not exposed.",
                        node_id=node_id,
                        payload={"run_id": run_id},
                    )
                elif kind == "approval.request":
                    flush_delta()
                    tool_trace.append(event)
                    command = event.get("command") or event.get("description") or "unknown command"
                    status = "failed"
                    error = (
                        "Hermes requested manual tool approval during unattended execution; "
                        f"the node was stopped. Requested action: {command}"
                    )
                    event_store.append(task.task_id, "node_failed", error, node_id=node_id, payload=event)
                    try:
                        stop_result = await hermes_client.stop_run(run_id)
                        event_store.append(
                            task.task_id,
                            "hermes_run_stop_requested",
                            f"Stop requested for {run_id}",
                            node_id=node_id,
                            payload=stop_result,
                        )
                    except Exception as exc:  # noqa: BLE001
                        event_store.append(
                            task.task_id,
                            "hermes_run_stop_failed",
                            str(exc),
                            node_id=node_id,
                            payload={"run_id": run_id},
                        )
                    break
                elif kind == "run.completed":
                    flush_delta()
                    output_text = event.get("output", "")
                    usage = event.get("usage") or {}
                    event_store.append(task.task_id, "node_complete", f"{node_id} completed", node_id=node_id, payload=event)
                    break
                elif kind in {"run.failed", "error"}:
                    flush_delta()
                    status = "failed"
                    error = event.get("error") or event.get("message") or json.dumps(event, ensure_ascii=False)
                    event_store.append(task.task_id, "node_failed", error, node_id=node_id, payload=event)
                    break
                elif kind in {"run.cancelled", "run.stopped", "run.expired", "run.timeout"}:
                    flush_delta()
                    latest_task = task_store.get(task.task_id)
                    if latest_task.pause_requested:
                        paused_by_user = True
                        status = "failed"
                        error = "Task paused by user; active Hermes run was stopped."
                        event_store.append(task.task_id, "node_paused", error, node_id=node_id, payload=event)
                    elif status != "failed":
                        status = "failed"
                        error = f"Hermes run ended before completion: {kind}"
                        event_store.append(task.task_id, "node_failed", error, node_id=node_id, payload=event)
                    else:
                        event_store.append(task.task_id, "hermes_event", kind, node_id=node_id, payload=event)
                    break
                else:
                    flush_delta()
                    event_store.append(
                        task.task_id,
                        "hermes_event",
                        kind,
                        node_id=node_id,
                        payload=event,
                    )
    except Exception as exc:  # noqa: BLE001
        flush_delta()
        status = "failed"
        error = f"Hermes execution error: {exc}"
        event_store.append(
            task.task_id,
            "node_failed",
            error,
            node_id=node_id,
            payload={"run_id": run_id},
        )
        if run_id:
            try:
                await hermes_client.stop_run(run_id)
            except Exception:
                pass
    flush_delta()

    if not output_text and status != "failed":
        final = await hermes_client.get_run(run_id)
        output_text = final.get("output") or ""
        usage = final.get("usage") or usage
        if final.get("status") not in {"completed", None}:
            status = "failed"
            error = final.get("error") or f"Hermes run ended with status: {final.get('status')}"
            event_store.append(
                task.task_id,
                "node_failed",
                error,
                node_id=node_id,
                payload={"run_id": run_id, "final_status": final.get("status"), "last_event": final.get("last_event")},
            )
    elif not output_text:
        try:
            final = await hermes_client.get_run(run_id) if run_id else {}
            output_text = final.get("output") or "".join(output_chunks)
            usage = final.get("usage") or usage
        except Exception:
            output_text = "".join(output_chunks)

    if not output_text:
        output_text = "".join(output_chunks)
    if status == "failed" and output_text and error:
        output_text = f"{output_text}\n\n> 节点未完成：{error}"

    workspace_markdown, workspace_structured, workspace_sources = _read_agent_workspace_outputs(
        workspace,
        node_id,
        settings.output_dir / task.task_id,
    )
    if workspace_sources:
        event_store.append(
            task.task_id,
            "node_workspace_output_used",
            f"{node_id} result collected from workspace files",
            node_id=node_id,
            payload=workspace_sources,
        )

    result_text = workspace_markdown or output_text
    structured = workspace_structured or extract_structured_result(result_text) or extract_structured_result(output_text)
    if status == "failed" and not result_text:
        result_text = (
            f"## {NODE_TITLES.get(node_id, node_id)} 执行失败\n\n"
            f"错误：{error or '未知错误'}\n\n"
            "请先确认上传文件仍然存在，或重新上传资料后再运行该节点。"
        )
        structured = structured or {"error": error or "unknown_error"}
    markdown = clean_markdown_output(result_text)
    if status == "failed" and markdown and error and error not in markdown:
        markdown = f"{markdown}\n\n> 节点未完成：{error}"
    out_dir = settings.output_dir / task.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{node_id}.md"
    json_path = out_dir / f"{node_id}.json"
    trace_path = out_dir / f"{node_id}.tool_trace.json"
    evidence_path = out_dir / f"{node_id}.evidence_refs.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(structured or {"raw_markdown": markdown, "usage": usage}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps(tool_trace, ensure_ascii=False, indent=2), encoding="utf-8")

    # Register URLs surfaced in the final output as candidate evidence records.
    evidence_refs: list[EvidenceRef] = []
    if not paused_by_user:
        for candidate in _collect_evidence_url_candidates(markdown, structured):
            url = candidate["url"]
            title = candidate.get("title") or ""
            record_id = knowledge_store.record_web_search(
                task_id=task.task_id,
                node_id=node_id,
                query="",
                result_url=url,
                title=title,
                snippet="",
                metadata={"source": "node_final_output", "sources": candidate.get("sources", [])},
            )
            metadata = {
                "task_id": task.task_id,
                "node_id": node_id,
                "web_search_record_id": record_id,
                "source": "node_final_output",
                "sources": candidate.get("sources", []),
            }
            try:
                existing_doc = knowledge_store.get_active_candidate_by_url(url)
                if existing_doc and existing_doc.local_path and existing_doc.text_path:
                    doc = knowledge_store.create_candidate_url(url, title=title, metadata=metadata)
                else:
                    doc = await ingest_url_candidate(url, title=title, task_id=task.task_id, node_id=node_id)
                    doc.metadata = {**doc.metadata, **metadata}
                    doc = knowledge_store.upsert_document(doc)
            except Exception as exc:  # noqa: BLE001
                doc = knowledge_store.create_candidate_url(
                    url,
                    title=title,
                    metadata={**metadata, "ingest_error": str(exc)},
                )
            if doc.id not in task.candidate_doc_ids:
                task.candidate_doc_ids.append(doc.id)
            evidence_refs.append(
                EvidenceRef(
                    id=record_id,
                    source_type="url",
                    title=doc.title,
                    source_url=url,
                    knowledge_document_id=doc.id,
                    retrieved_at=doc.retrieved_at,
                    confidence="candidate",
                )
            )
    evidence_path.write_text(
        json.dumps([ref.model_dump() for ref in evidence_refs], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = NodeResult(
        node_id=node_id,
        status=status,
        title=NODE_TITLES.get(node_id, node_id),
        markdown=markdown,
        structured=structured,
        evidence_refs=evidence_refs,
        tool_trace=tool_trace,
        output_files=[md_path.name, json_path.name, trace_path.name, evidence_path.name],
        hermes_run_id=run_id,
        error=error,
        started_at=started_at,
        completed_at=now_iso(),
    )

    latest_task = task_store.get(task.task_id)
    if not paused_by_user:
        latest_task.module_results[node_id] = result
        for doc_id in task.candidate_doc_ids:
            if doc_id not in latest_task.candidate_doc_ids:
                latest_task.candidate_doc_ids.append(doc_id)
        for ref in evidence_refs:
            exists = any(
                existing.source_url == ref.source_url
                and existing.knowledge_document_id == ref.knowledge_document_id
                for existing in latest_task.evidence_refs
            )
            if not exists:
                latest_task.evidence_refs.append(ref)
    latest_task.active_hermes_run_id = None
    task_completed = False
    if paused_by_user:
        latest_task.module_results.pop(node_id, None)
        _rebuild_task_evidence_from_results(latest_task)
        latest_task.status = "paused"
        latest_task.next_node = node_id
        latest_task.error = error
    elif status == "failed":
        latest_task.status = "failed"
        latest_task.error = error
    elif latest_task.pause_requested:
        latest_task.status = "paused"
        latest_task.next_node = NEXT_NODE.get(node_id)
    else:
        latest_task.next_node = NEXT_NODE.get(node_id)
        if latest_task.next_node:
            latest_task.status = "running" if continue_on_success else "paused"
        else:
            latest_task.status = "completed"
            task_completed = True
    latest_task.current_node = None
    task_store.save(latest_task)
    if task_completed:
        event_store.append(task.task_id, "task_completed", "Task completed")
    return result


graph_runtime = EiaGraphRuntime(node_runner=_run_node, implemented_nodes=set(NODE_PROMPTS))


async def _sync_graph_checkpoint(task_id: str, *, mode: str = "step") -> dict[str, Any]:
    try:
        return await graph_runtime.sync_task_state(task_id, mode=mode)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        event_store.append(
            task_id,
            "graph_checkpoint_sync_failed",
            str(exc),
            payload={"mode": mode},
        )
        return {"exists": False, "error": str(exc)}


async def _run_task_loop(task_id: str) -> None:
    try:
        await graph_runtime.run(task_id)
    except Exception as exc:  # noqa: BLE001
        try:
            task = task_store.get(task_id)
            task.status = "failed"
            task.current_node = None
            task.active_hermes_run_id = None
            task.error = str(exc)
            task_store.save(task)
        except Exception:
            pass
        event_store.append(task_id, "task_failed", str(exc))
    finally:
        RUNNING_TASKS.discard(task_id)


async def _run_task_until_loop(task_id: str, *, stop_after_node: str) -> None:
    try:
        while True:
            task = task_store.get(task_id)
            if task.pause_requested:
                task.status = "paused"
                task.current_node = None
                task.active_hermes_run_id = None
                task_store.save(task)
                event_store.append(task_id, "task_paused", "Task paused before next node")
                await _sync_graph_checkpoint(task_id, mode="run")
                return
            node_id = task.next_node
            if not node_id:
                task.status = "completed"
                task.current_node = None
                task.active_hermes_run_id = None
                task_store.save(task)
                event_store.append(task_id, "task_completed", "Task completed")
                await _sync_graph_checkpoint(task_id, mode="run")
                return
            if node_id not in NODE_PROMPTS:
                task.status = "failed"
                task.current_node = None
                task.error = f"Node is not implemented yet: {node_id}"
                task_store.save(task)
                event_store.append(task_id, "task_failed", task.error, node_id=node_id)
                await _sync_graph_checkpoint(task_id, mode="run")
                return

            result = await _run_node(task, node_id, continue_on_success=True)
            await _sync_graph_checkpoint(task_id, mode="run")
            latest = task_store.get(task_id)
            if result.status != "completed" or latest.status in {"failed", "paused", "completed"}:
                return
            if node_id == stop_after_node:
                latest.status = "paused"
                latest.current_node = None
                latest.active_hermes_run_id = None
                latest.pause_requested = False
                task_store.save(latest)
                event_store.append(
                    task_id,
                    "task_run_until_completed",
                    f"Run stopped after {stop_after_node}",
                    node_id=stop_after_node,
                    payload={"next_node": latest.next_node},
                )
                await _sync_graph_checkpoint(task_id, mode="run")
                return
    except Exception as exc:  # noqa: BLE001
        task = task_store.get(task_id)
        task.status = "failed"
        task.current_node = None
        task.active_hermes_run_id = None
        task.error = str(exc)
        task_store.save(task)
        event_store.append(task_id, "task_failed", str(exc))
    finally:
        RUNNING_TASKS.discard(task_id)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    hermes = None
    try:
        hermes = await hermes_client.health()
    except Exception as exc:  # noqa: BLE001
        hermes = {"status": "error", "error": str(exc)}
    return {
        "status": "ok" if hermes.get("status") != "error" else "degraded",
        "edition": settings.deployment_edition,
        "hermes": hermes,
        "auto_recovery": settings.auto_recover_running_tasks,
    }


@app.get("/api/ready")
async def readiness() -> Response:
    try:
        hermes = await hermes_client.health()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "edition": settings.deployment_edition,
                "hermes": {"status": "error", "error": str(exc)},
            },
        )
    return JSONResponse(
        content={"status": "ready", "edition": settings.deployment_edition, "hermes": hermes}
    )


@app.get("/api/hermes/health")
async def hermes_health() -> dict[str, Any]:
    return await hermes_client.health()


async def _recover_running_tasks_impl(*, mode: str, force: bool) -> dict[str, Any]:
    if mode not in {"pause", "fail"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    recovered = []
    skipped = []
    for task in task_store.list():
        if task.status != "running":
            continue
        if task.task_id in RUNNING_TASKS and not force:
            skipped.append({"task_id": task.task_id, "reason": "active_in_current_process"})
            continue
        original_node = task.current_node
        original_run_id = task.active_hermes_run_id
        stop_result = None
        if original_run_id:
            try:
                stop_result = await hermes_client.stop_run(original_run_id)
                event_store.append(
                    task.task_id,
                    "hermes_run_stop_requested",
                    f"Stop requested for orphan run {original_run_id}",
                    node_id=original_node,
                    payload=stop_result,
                )
            except Exception as exc:  # noqa: BLE001
                stop_result = {"error": str(exc), "run_id": original_run_id}
                event_store.append(
                    task.task_id,
                    "hermes_run_stop_failed",
                    str(exc),
                    node_id=original_node,
                    payload={"run_id": original_run_id},
                )
        if mode == "pause":
            task.status = "paused"
            task.pause_requested = True
            task.next_node = task.current_node or task.next_node
            task.error = "Recovered orphan running task as paused."
        else:
            task.status = "failed"
            task.error = "Recovered orphan running task as failed."
        task.current_node = None
        task.active_hermes_run_id = None
        task_store.save(task)
        event_store.append(
            task.task_id,
            "task_recovered",
            task.error or "Task recovered",
            node_id=original_node,
            payload={"mode": mode, "force": force, "stopped_run": stop_result},
        )
        await _sync_graph_checkpoint(task.task_id)
        recovered.append({"task_id": task.task_id, "status": task.status, "next_node": task.next_node, "stopped_run": stop_result})
    return {"recovered": recovered, "skipped": skipped}


@app.post("/api/admin/recover-running-tasks")
async def recover_running_tasks(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return await _recover_running_tasks_impl(
        mode=str(payload.get("mode") or "pause"),
        force=bool(payload.get("force") or False),
    )


@app.get("/api/admin/workflow/nodes")
async def admin_workflow_nodes() -> dict[str, Any]:
    all_nodes = [
        "PREP-INGEST",
        "HB-PT-000",
        "HB-PT-001",
        "HB-PT-002",
        "HB-PT-003",
        "HB-PT-004",
        "HB-PT-005",
        "HB-PT-006",
        "HB-PT-007",
        "HB-PT-008",
        "HB-PT-009",
        "HB-PT-010",
        "HB-PT-011",
    ]
    return {
        "nodes": [
            {
                "node_id": node_id,
                "title": NODE_TITLES.get(node_id, node_id),
                "implemented": node_id in NODE_PROMPTS,
                "prompt_file": NODE_PROMPTS.get(node_id),
                "next_node": NEXT_NODE.get(node_id),
                "route_index": index,
            }
            for index, node_id in enumerate(all_nodes)
        ],
        "missing_nodes": [
            {"node_id": node_id, "title": NODE_TITLES.get(node_id, node_id)}
            for node_id in all_nodes
            if node_id not in NODE_PROMPTS
        ],
    }


@app.get("/api/admin/knowledge/review-history")
async def admin_knowledge_review_history() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for doc in knowledge_store.list_documents():
        review_history = doc.metadata.get("review_history")
        if not isinstance(review_history, list):
            continue
        for record in review_history:
            if not isinstance(record, dict):
                continue
            records.append(
                {
                    **record,
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "source_url": doc.source_url,
                    "source_domain": doc.source_domain,
                    "current_status": doc.status,
                    "current_validity": doc.validity,
                }
            )
    records.sort(key=lambda item: item.get("reviewed_at") or "", reverse=True)
    return {"records": records}


@app.post("/api/tasks", response_model=CreateTaskResponse)
async def create_task(
    project_text: str = Form(""),
    files: list[UploadFile] | None = File(default=None),
) -> CreateTaskResponse:
    task_id = str(uuid.uuid4())
    refs = []
    for upload in files or []:
        refs.append(await file_store.save_upload(task_id, upload))
    task = EiaTaskState(task_id=task_id, project_text=project_text, project_files=refs)
    task_store.create(task)
    file_store.prepare_workspace(task)
    event_store.append(task_id, "task_created", "Task created", payload={"file_count": len(refs)})
    await _sync_graph_checkpoint(task_id)
    return CreateTaskResponse(task_id=task.task_id, status=task.status, next_node=task.next_node)


@app.get("/api/tasks")
async def list_tasks() -> dict[str, Any]:
    return {"tasks": [task.model_dump() for task in task_store.list()]}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = _task_or_404(task_id)
    return {
        **task.model_dump(),
        "events": [event.model_dump() for event in event_store.iter_events(task_id)],
    }


@app.get("/api/tasks/{task_id}/manifest")
async def task_manifest(task_id: str) -> dict[str, Any]:
    return await _task_manifest_payload(task_id)


@app.get("/api/tasks/{task_id}/report.md")
async def task_report_markdown(task_id: str) -> Response:
    task = _task_or_404(task_id)
    report = _combined_report_markdown(task)
    headers = {"Content-Disposition": f'attachment; filename="eia_report_{task_id}.md"'}
    return Response(content=report, media_type="text/markdown; charset=utf-8", headers=headers)


@app.get("/api/tasks/{task_id}/export.zip")
async def task_export_archive(task_id: str) -> Response:
    task = _task_or_404(task_id)
    manifest = await _task_manifest_payload(task_id)
    report = _combined_report_markdown(task)
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("report.md", report)
        state_path = task_store.task_path(task_id)
        if state_path.exists():
            archive.write(state_path, "state.json")
        events_path = event_store.path_for(task_id)
        if events_path.exists():
            archive.write(events_path, "logs/events.jsonl")
        out_dir = settings.output_dir / task_id
        if out_dir.exists():
            for path in sorted(out_dir.glob("*")):
                if path.is_file():
                    archive.write(path, f"outputs/{path.name}")
    headers = {"Content-Disposition": f'attachment; filename="eia_task_{task_id}.zip"'}
    return Response(content=buffer.getvalue(), media_type="application/zip", headers=headers)


@app.post("/api/tasks/{task_id}/step", response_model=StepResponse)
async def step_task(task_id: str, payload: dict[str, Any] | None = Body(default=None)) -> StepResponse:
    task = _task_or_404(task_id)
    if task.status == "running":
        raise HTTPException(status_code=409, detail="Task is already running")
    if not task.next_node:
        return StepResponse(task_id=task_id, status=task.status, current_node=task.current_node, next_node=task.next_node, result=None)
    if task.next_node not in NODE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Node is not implemented yet: {task.next_node}")
    prompt_override = str((payload or {}).get("prompt_override") or "").strip()
    if prompt_override:
        if len(prompt_override) > 120_000:
            raise HTTPException(status_code=400, detail="prompt_override is too long")
        task.prompt_overrides[task.next_node] = prompt_override
        task_store.save(task)
        event_store.append(
            task_id,
            "node_prompt_override_saved",
            f"Prompt override saved for {task.next_node}",
            node_id=task.next_node,
            payload={"chars": len(prompt_override)},
        )
    graph_result = await graph_runtime.step(task_id)
    updated = graph_result.task
    return StepResponse(
        task_id=task_id,
        status=updated.status,
        current_node=updated.current_node,
        next_node=updated.next_node,
        result=graph_result.result,
    )


@app.post("/api/tasks/{task_id}/run", response_model=StepResponse)
async def run_task(task_id: str) -> StepResponse:
    task = _task_or_404(task_id)
    if task.status == "running" or task_id in RUNNING_TASKS:
        raise HTTPException(status_code=409, detail="Task is already running")
    if not task.next_node:
        return StepResponse(task_id=task_id, status=task.status, current_node=task.current_node, next_node=task.next_node, result=None)
    if task.next_node not in NODE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Node is not implemented yet: {task.next_node}")

    task.pause_requested = False
    task.status = "running"
    task.current_node = None
    task.active_hermes_run_id = None
    task.error = None
    task_store.save(task)
    RUNNING_TASKS.add(task_id)
    event_store.append(task_id, "task_run_started", "Continuous run started", payload={"next_node": task.next_node})
    await _sync_graph_checkpoint(task_id, mode="run")
    asyncio.create_task(_run_task_loop(task_id))
    return StepResponse(task_id=task_id, status=task.status, current_node=task.current_node, next_node=task.next_node, result=None)


@app.post("/api/tasks/{task_id}/run-until", response_model=StepResponse)
async def run_task_until(task_id: str, payload: dict[str, Any]) -> StepResponse:
    task = _task_or_404(task_id)
    stop_after_node = str(payload.get("stop_after_node") or "HB-PT-009")
    if stop_after_node not in NEXT_NODE:
        raise HTTPException(status_code=400, detail=f"Invalid stop_after_node: {stop_after_node}")
    if task.status == "running" or task_id in RUNNING_TASKS:
        raise HTTPException(status_code=409, detail="Task is already running")
    if not task.next_node:
        return StepResponse(task_id=task_id, status=task.status, current_node=task.current_node, next_node=task.next_node, result=None)
    route = list(NEXT_NODE.keys())
    if task.next_node not in route:
        raise HTTPException(status_code=400, detail=f"Node is not in route: {task.next_node}")
    if route.index(task.next_node) > route.index(stop_after_node):
        raise HTTPException(status_code=400, detail=f"Current next node {task.next_node} is after {stop_after_node}")

    task.pause_requested = False
    task.status = "running"
    task.current_node = None
    task.active_hermes_run_id = None
    task.error = None
    task_store.save(task)
    RUNNING_TASKS.add(task_id)
    event_store.append(
        task_id,
        "task_run_until_started",
        f"Run until {stop_after_node} started",
        payload={"next_node": task.next_node, "stop_after_node": stop_after_node},
    )
    await _sync_graph_checkpoint(task_id, mode="run")
    asyncio.create_task(_run_task_until_loop(task_id, stop_after_node=stop_after_node))
    return StepResponse(task_id=task_id, status=task.status, current_node=task.current_node, next_node=task.next_node, result=None)


@app.post("/api/tasks/{task_id}/validate-files", response_model=NodeResult)
async def validate_task_files(task_id: str) -> NodeResult:
    task = _task_or_404(task_id)
    if task.status == "running" or task_id in RUNNING_TASKS:
        raise HTTPException(status_code=409, detail="Task is already running")
    if not task.project_files and not task.project_text.strip():
        raise HTTPException(status_code=400, detail="No project text or files to validate")
    prompt = _build_aux_prompt(task, "aux_file_validation.txt", {}, node_id="FILE-VALIDATION")
    result = await _execute_hermes_aux_agent(
        task=task,
        node_id="FILE-VALIDATION",
        title=NODE_TITLES["FILE-VALIDATION"],
        user_input=prompt,
        output_task_id=task_id,
        persist_result=True,
        output_prefix="FILE-VALIDATION",
    )
    return result


@app.post("/api/tasks/{task_id}/feedback/{node_id}", response_model=NodeResult)
async def feedback_node(task_id: str, node_id: str, payload: dict[str, Any]) -> NodeResult:
    task = _task_or_404(task_id)
    if node_id not in NODE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Node is not implemented: {node_id}")
    if task.status == "running" or task_id in RUNNING_TASKS:
        raise HTTPException(status_code=409, detail="Task is already running")
    feedback = str(payload.get("feedback") or "").strip()
    if not feedback:
        raise HTTPException(status_code=400, detail="feedback is required")
    action = str(payload.get("action") or "revise")
    if action not in {"revise", "analyze_error"}:
        raise HTTPException(status_code=400, detail="Invalid action")
    previous = task.module_results.get(node_id)
    if not previous:
        raise HTTPException(status_code=400, detail=f"No result exists for node: {node_id}")

    node_prompt = _load_prompt(NODE_PROMPTS[node_id])
    action_instruction = (
        "本次处理方式：请根据用户反馈修正并重新输出完整节点结果。"
        if action == "revise"
        else "本次处理方式：请重点分析错误原因和改进建议，不替换原节点结论。"
    )
    prompt = _build_aux_prompt(
        task,
        "aux_feedback_revision.txt",
        {
            "node_id": node_id,
            "node_title": NODE_TITLES.get(node_id, node_id),
            "node_prompt": node_prompt,
            "previous_result": previous.markdown or json.dumps(previous.structured, ensure_ascii=False, indent=2),
            "feedback": f"{action_instruction}\n\n{feedback}",
        },
        node_id=f"{node_id}-FEEDBACK",
    )
    if action == "analyze_error":
        output_prefix = f"{node_id}.feedback_analysis"
        result = await _execute_hermes_aux_agent(
            task=task,
            node_id=f"{node_id}-FEEDBACK",
            title=f"{NODE_TITLES.get(node_id, node_id)} 反馈错误原因分析",
            user_input=prompt,
            output_task_id=task_id,
            persist_result=False,
            output_prefix=output_prefix,
        )
        event_store.append(
            task_id,
            "node_feedback_analyzed",
            f"Feedback analyzed for {node_id}",
            node_id=node_id,
            payload={"feedback": feedback, "output_files": result.output_files},
        )
        return result

    result = await _execute_hermes_aux_agent(
        task=task,
        node_id=node_id,
        title=f"{NODE_TITLES.get(node_id, node_id)}（反馈修正）",
        user_input=prompt,
        output_task_id=task_id,
        persist_result=True,
        output_prefix=node_id,
    )
    if result.status != "completed":
        # _execute_hermes_aux_agent persists its result before returning. Keep
        # the last usable node result when the feedback run itself fails.
        task.module_results[node_id] = previous
        task.status = "paused"
        task.current_node = None
        task.active_hermes_run_id = None
        task.error = result.error or "反馈修正未完成"
        _rebuild_task_evidence_from_results(task)
        task_store.save(task)
        event_store.append(
            task_id,
            "node_feedback_failed",
            f"Feedback revision failed for {node_id}",
            node_id=node_id,
            payload={"feedback": feedback, "error": task.error, "hermes_run_id": result.hermes_run_id},
        )
        return result
    route = list(NEXT_NODE.keys())
    clear_nodes = route[route.index(node_id) + 1 :] if node_id in route else []
    for clear_node in clear_nodes:
        task.module_results.pop(clear_node, None)
    _remove_node_outputs(task_id, clear_nodes)
    _rebuild_task_evidence_from_results(task)
    task.next_node = NEXT_NODE.get(node_id)
    task.status = "created" if task.next_node else "completed"
    task.pause_requested = False
    task.current_node = None
    task.active_hermes_run_id = None
    task.error = None
    history = task.module_results[node_id].structured.get("feedback_history")
    feedback_record = {
        "node_id": node_id,
        "feedback": feedback,
        "action": action,
        "cleared_nodes": clear_nodes,
        "created_at": now_iso(),
        "hermes_run_id": result.hermes_run_id,
    }
    if not isinstance(history, list):
        history = []
    task.module_results[node_id].structured = {
        **task.module_results[node_id].structured,
        "feedback_history": [*history, feedback_record],
    }
    task_store.save(task)
    event_store.append(
        task_id,
        "node_feedback_revised",
        f"Feedback revision applied to {node_id}",
        node_id=node_id,
        payload=feedback_record,
    )
    await _sync_graph_checkpoint(task_id)
    return task.module_results[node_id]


@app.post("/api/tasks/{task_id}/pause")
async def pause_task(task_id: str) -> dict[str, Any]:
    task = _task_or_404(task_id)
    if task.status in {"completed", "failed"}:
        event_store.append(task_id, "task_pause_ignored", f"Pause ignored for terminal task: {task.status}")
        return {
            "task_id": task_id,
            "status": task.status,
            "active_hermes_run_id": task.active_hermes_run_id,
            "stop_result": None,
            "ignored": True,
        }
    task.pause_requested = True
    if task.status != "running" or (task.status == "running" and not task.current_node and not task.active_hermes_run_id):
        task.status = "paused"
        task.active_hermes_run_id = None
    task_store.save(task)

    stop_result = None
    if task.status == "running" and task.active_hermes_run_id:
        try:
            stop_result = await hermes_client.stop_run(task.active_hermes_run_id)
            event_store.append(
                task_id,
                "hermes_run_stop_requested",
                f"Stop requested for {task.active_hermes_run_id}",
                node_id=task.current_node,
                payload=stop_result,
            )
        except Exception as exc:  # noqa: BLE001
            event_store.append(
                task_id,
                "hermes_run_stop_failed",
                str(exc),
                node_id=task.current_node,
                payload={"run_id": task.active_hermes_run_id},
            )
    event_store.append(task_id, "task_paused", "Pause requested")
    if task.status != "running":
        await _sync_graph_checkpoint(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "active_hermes_run_id": task.active_hermes_run_id,
        "stop_result": stop_result,
    }


@app.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str) -> dict[str, Any]:
    task = _task_or_404(task_id)
    task.pause_requested = False
    task.active_hermes_run_id = None
    if task.status == "paused":
        task.status = "created"
    task_store.save(task)
    event_store.append(task_id, "task_resumed", "Task resumed")
    await _sync_graph_checkpoint(task_id)
    return {"task_id": task_id, "status": task.status, "next_node": task.next_node}


@app.post("/api/tasks/{task_id}/rerun/{node_id}")
async def rerun_node(task_id: str, node_id: str) -> dict[str, Any]:
    if node_id not in NODE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Node is not implemented yet: {node_id}")
    task = _task_or_404(task_id)
    if task.status == "running":
        raise HTTPException(status_code=409, detail="Task is already running")
    route = list(NEXT_NODE.keys())
    if node_id not in route:
        raise HTTPException(status_code=400, detail=f"Node is not in route: {node_id}")
    clear_nodes = route[route.index(node_id) :]
    for clear_node in clear_nodes:
        task.module_results.pop(clear_node, None)
    _remove_node_outputs(task_id, clear_nodes)
    _rebuild_task_evidence_from_results(task)
    task.next_node = node_id
    task.status = "created"
    task.pause_requested = False
    task.current_node = None
    task.active_hermes_run_id = None
    task.error = None
    task_store.save(task)
    event_store.append(
        task_id,
        "node_rerun_requested",
        f"Rerun requested: {node_id}",
        node_id=node_id,
        payload={"cleared_nodes": clear_nodes},
    )
    await _sync_graph_checkpoint(task_id)
    return {"task_id": task_id, "status": task.status, "next_node": task.next_node, "cleared_nodes": clear_nodes}


@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str) -> StreamingResponse:
    _task_or_404(task_id)

    async def stream():
        sent = 0
        while True:
            events = list(event_store.iter_events(task_id))
            for event in events[sent:]:
                yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
            sent = len(events)
            task = task_store.get(task_id)
            if task.status in {"failed", "completed", "paused"}:
                yield ": stream closed\n\n"
                return
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/tasks/{task_id}/outputs/{file_name}")
async def get_output(task_id: str, file_name: str) -> FileResponse:
    path = _output_path(task_id, file_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(path)


@app.get("/api/tasks/{task_id}/knowledge-candidates")
async def task_knowledge_candidates(task_id: str) -> dict[str, Any]:
    task = _task_or_404(task_id)
    docs_by_id = {}
    for doc_id in [*task.candidate_doc_ids, *task.knowledge_doc_ids]:
        doc = knowledge_store.get_document(doc_id)
        if doc:
            docs_by_id[doc.id] = doc

    evidence_by_doc: dict[str, list[dict[str, Any]]] = {}
    for node_id, result in task.module_results.items():
        for ref in result.evidence_refs:
            if not ref.knowledge_document_id:
                continue
            evidence_by_doc.setdefault(ref.knowledge_document_id, []).append(
                {
                    "node_id": node_id,
                    "evidence_ref_id": ref.id,
                    "title": ref.title,
                    "source_url": ref.source_url,
                    "confidence": ref.confidence,
                }
            )

    documents = []
    for doc in docs_by_id.values():
        payload = doc.model_dump()
        payload["selected_for_task"] = doc.id in task.knowledge_doc_ids
        payload["evidence_refs"] = evidence_by_doc.get(doc.id, [])
        documents.append(payload)

    return {"task_id": task_id, "documents": documents}


@app.post("/api/search")
async def web_search_agent(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    task_id_raw = str(payload.get("task_id") or "").strip()
    task = _task_or_404(task_id_raw) if task_id_raw else None
    if task and (task.status == "running" or task.task_id in RUNNING_TASKS):
        raise HTTPException(status_code=409, detail="Task is already running")
    purpose = str(payload.get("purpose") or "manual_search").strip()
    prompt = _build_aux_prompt(
        task,
        "aux_web_search.txt",
        {
            "query": f"{query}\n\n检索用途：{purpose}",
        },
        node_id="WEB-SEARCH",
    )
    output_task_id = task.task_id if task else "search"
    result = await _execute_hermes_aux_agent(
        task=task,
        node_id="WEB-SEARCH",
        title=NODE_TITLES["WEB-SEARCH"],
        user_input=prompt,
        output_task_id=output_task_id,
        persist_result=False,
        output_prefix=f"WEB-SEARCH-{uuid.uuid4().hex[:8]}",
    )
    documents = []
    seen_doc_ids: set[str] = set()
    for ref in result.evidence_refs:
        if not ref.knowledge_document_id or ref.knowledge_document_id in seen_doc_ids:
            continue
        doc = knowledge_store.get_document(ref.knowledge_document_id)
        if doc:
            documents.append(doc.model_dump())
            seen_doc_ids.add(doc.id)
    return {
        "query": query,
        "task_id": task.task_id if task else None,
        "result": result.model_dump(),
        "documents": documents,
    }


@app.post("/api/tasks/{task_id}/knowledge-documents")
async def update_task_knowledge_documents(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    task = _task_or_404(task_id)
    mode = str(payload.get("mode") or "add")
    doc_ids = payload.get("doc_ids") or []
    if mode not in {"add", "remove", "set"}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if not isinstance(doc_ids, list) or not all(isinstance(doc_id, str) for doc_id in doc_ids):
        raise HTTPException(status_code=400, detail="doc_ids must be a string list")

    valid_doc_ids: list[str] = []
    for doc_id in doc_ids:
        doc = knowledge_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Knowledge document not found: {doc_id}")
        if doc.status != "verified":
            raise HTTPException(status_code=400, detail=f"Knowledge document is not verified: {doc_id}")
        valid_doc_ids.append(doc_id)

    if mode == "set":
        task.knowledge_doc_ids = []
    if mode == "remove":
        task.knowledge_doc_ids = [doc_id for doc_id in task.knowledge_doc_ids if doc_id not in valid_doc_ids]
    else:
        for doc_id in valid_doc_ids:
            if doc_id not in task.knowledge_doc_ids:
                task.knowledge_doc_ids.append(doc_id)
    task_store.save(task)
    event_store.append(
        task_id,
        "task_knowledge_documents_updated",
        f"Task knowledge documents updated: {mode}",
        payload={"mode": mode, "doc_ids": valid_doc_ids},
    )
    docs = []
    for doc_id in task.knowledge_doc_ids:
        doc = knowledge_store.get_document(doc_id)
        if doc:
            docs.append(doc.model_dump())
    return {"task_id": task_id, "knowledge_doc_ids": task.knowledge_doc_ids, "documents": docs}


@app.get("/api/knowledge/documents")
async def list_knowledge(status: str | None = None) -> dict[str, Any]:
    return {"documents": [doc.model_dump() for doc in knowledge_store.list_documents(status=status)]}


@app.post("/api/knowledge/documents/batch-review")
async def batch_review_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
    doc_ids = payload.get("doc_ids") or []
    status = str(payload.get("status") or "")
    validity = payload.get("validity")
    if not isinstance(doc_ids, list) or not all(isinstance(doc_id, str) for doc_id in doc_ids):
        raise HTTPException(status_code=400, detail="doc_ids must be a string list")
    if not doc_ids:
        raise HTTPException(status_code=400, detail="doc_ids is required")
    if status not in VALID_KNOWLEDGE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if validity and validity not in VALID_KNOWLEDGE_VALIDITY:
        raise HTTPException(status_code=400, detail="Invalid validity")

    documents = []
    errors = []
    for doc_id in doc_ids:
        try:
            doc = knowledge_store.review_document(
                doc_id,
                status=status,
                validity=validity,
                reviewer=payload.get("reviewer") or "batch",
                note=payload.get("note"),
            )
            documents.append(doc.model_dump())
        except FileNotFoundError:
            errors.append({"doc_id": doc_id, "error": "not_found"})
    event_store.append(
        "knowledge",
        "knowledge_batch_review",
        f"Batch reviewed {len(documents)} documents as {status}",
        payload={"doc_ids": [doc["id"] for doc in documents], "errors": errors},
    )
    return {"documents": documents, "errors": errors}


@app.get("/api/knowledge/documents/{doc_id}")
async def get_knowledge_document(doc_id: str) -> dict[str, Any]:
    doc = knowledge_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Knowledge document not found: {doc_id}")
    return {"document": doc.model_dump()}


@app.post("/api/knowledge/ingest")
async def ingest_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    doc = await ingest_url_candidate(url, title=str(payload.get("title") or ""))
    event_store.append("knowledge", "knowledge_ingest", f"Candidate ingested: {url}", payload={"doc_id": doc.id})
    return {"document": doc.model_dump()}


@app.post("/api/knowledge/documents/{doc_id}/verify")
async def verify_knowledge(doc_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    status = str(payload.get("status") or "verified")
    validity = payload.get("validity")
    if status not in VALID_KNOWLEDGE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if validity and validity not in VALID_KNOWLEDGE_VALIDITY:
        raise HTTPException(status_code=400, detail="Invalid validity")
    try:
        doc = knowledge_store.review_document(
            doc_id,
            status=status,
            validity=validity,
            title=payload.get("title"),
            issuer=payload.get("issuer"),
            doc_no=payload.get("doc_no"),
            published_at=payload.get("published_at"),
            reviewer=payload.get("reviewer"),
            note=payload.get("note"),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Knowledge document not found: {doc_id}") from None
    return {"document": doc.model_dump()}
