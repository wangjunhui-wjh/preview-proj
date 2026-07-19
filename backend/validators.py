from __future__ import annotations

import json
import re
from typing import Any


JSON_BLOCK_RE = re.compile(
    r"(?:BEGIN_NODE_RESULT_JSON\s*)(?P<json>\{.*?\})(?:\s*END_NODE_RESULT_JSON)",
    re.DOTALL,
)


def extract_structured_result(text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(text or "")
    if match:
        try:
            return json.loads(match.group("json"))
        except json.JSONDecodeError:
            return {}
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text or "", re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            return {}
    return {}


def clean_markdown_output(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"BEGIN_NODE_RESULT_JSON.*?END_NODE_RESULT_JSON", "", text, flags=re.DOTALL)
    text = text.replace("BEGIN_NODE_RESULT_MARKDOWN", "").replace("END_NODE_RESULT_MARKDOWN", "")
    return text.strip()

