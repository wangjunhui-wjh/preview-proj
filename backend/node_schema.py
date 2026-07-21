from __future__ import annotations

import json
from typing import Any


_EXPECTED_SECTIONS = {
    "PREP-INGEST": ("资料包读取概况", "项目档案摘要", "资料矛盾", "后续研判可用输入", "需补充资料"),
    "HB-PT-000": ("资料完整性", "关键字段", "建议启动模块", "补充资料"),
    "HB-PT-002": ("行业类别", "环评类别", "审批路径", "判断依据", "补充资料"),
    "HB-PT-009": ("同类项目", "产污节点", "治理措施", "相似点", "工程分析"),
}


def codex_output_schema(node_id: str) -> dict[str, Any]:
    """Strict envelope shared by all Codex-backed business entrypoints."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "completion_state": {"type": "string", "enum": ["completed"]},
            "node_id": {"type": "string", "const": node_id},
            "markdown": {"type": "string"},
            "structured_json": {"type": "string"},
            "evidence_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "issuer": {"type": "string"},
                        "source_type": {"type": "string"},
                        "locator": {"type": "string"},
                        "claim": {"type": "string"},
                    },
                    "required": ["title", "url", "issuer", "source_type", "locator", "claim"],
                },
            },
            "limitations": {"type": "array", "items": {"type": "string"}},
            "disclaimer": {"type": "string"},
        },
        "required": [
            "completion_state",
            "node_id",
            "markdown",
            "structured_json",
            "evidence_refs",
            "limitations",
            "disclaimer",
        ],
    }


def parse_codex_output(node_id: str, value: Any) -> tuple[str, dict[str, Any], list[dict[str, Any]], list[str]]:
    """Normalize and gate a Codex response before it can advance the graph."""
    errors: list[str] = []
    envelope: dict[str, Any] = {}
    if isinstance(value, dict):
        envelope = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                envelope = parsed
        except json.JSONDecodeError:
            errors.append("Codex output is not a JSON object")

    if envelope.get("completion_state") != "completed":
        errors.append("completion_state must be completed")
    if envelope.get("node_id") != node_id:
        errors.append(f"node_id does not match {node_id}")

    markdown = str(envelope.get("markdown") or "").strip()
    if len(markdown) < 240:
        errors.append("markdown output is too short to be a node result")
    for section in _EXPECTED_SECTIONS.get(node_id, ()):
        if section not in markdown:
            errors.append(f"markdown is missing required section: {section}")

    disclaimer = str(envelope.get("disclaimer") or "")
    if "环评工程师" not in disclaimer and "人工复核" not in disclaimer:
        errors.append("disclaimer must require engineer/manual review")

    structured: dict[str, Any] = {}
    raw_structured = envelope.get("structured_json")
    if isinstance(raw_structured, dict):
        structured = raw_structured
    elif isinstance(raw_structured, str) and raw_structured.strip():
        try:
            parsed = json.loads(raw_structured)
            if isinstance(parsed, dict):
                structured = parsed
            else:
                errors.append("structured_json must contain an object")
        except json.JSONDecodeError:
            errors.append("structured_json is not valid JSON")
    else:
        errors.append("structured_json is required")

    evidence_refs = envelope.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        errors.append("evidence_refs must be an array")
        evidence_refs = []
    normalized_evidence = [item for item in evidence_refs if isinstance(item, dict)]
    structured = {
        **structured,
        "_codex_envelope": {
            "completion_state": envelope.get("completion_state"),
            "node_id": envelope.get("node_id"),
            "limitations": envelope.get("limitations") or [],
            "disclaimer": disclaimer,
            "evidence_refs": normalized_evidence,
        },
    }
    return markdown, structured, normalized_evidence, errors
