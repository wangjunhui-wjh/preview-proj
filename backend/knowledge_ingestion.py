from __future__ import annotations

import hashlib
import html
import io
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from .config import settings
from .knowledge_store import knowledge_store
from .models import KnowledgeDocument


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
CN_DATE_RE = re.compile(r"((?:19|20)\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日")
ISO_DATE_RE = re.compile(r"((?:19|20)\d{2})[-./](\d{1,2})[-./](\d{1,2})")
DOC_NO_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z]{1,20}(?:发|环|规|办|函|令|公告)[〔\[]\d{4}[〕\]]\s*\d{1,5}号)")
ISSUER_HINTS = (
    "生态环境部",
    "国家发展改革委",
    "国家发展和改革委员会",
    "工业和信息化部",
    "自然资源部",
    "上海市生态环境局",
    "上海市发展和改革委员会",
    "上海市经济和信息化委员会",
)
TITLE_KEYWORDS = ("通知", "办法", "条例", "目录", "名录", "意见", "规划", "指南", "标准", "政策", "批复", "公告")


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_snapshot_name(url: str, digest: str) -> str:
    parsed = urlparse(url)
    stem = (parsed.netloc + parsed.path).strip("/").replace("/", "_") or "snapshot"
    stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem)[:120]
    suffix = Path(parsed.path).suffix.lower()
    if not suffix or len(suffix) > 10 or not re.fullmatch(r"\.[a-z0-9]+", suffix):
        suffix = ".html"
    if stem.lower().endswith(suffix):
        stem = stem[: -len(suffix)]
    return f"{digest[:16]}_{stem}{suffix}"


def _html_to_text(raw: str) -> str:
    raw = SCRIPT_STYLE_RE.sub(" ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", raw)
    text = TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_docx_text(content: bytes) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in ("word/document.xml",):
            if name not in zf.namelist():
                continue
            root = ElementTree.fromstring(zf.read(name))
            for elem in root.iter():
                if elem.tag.endswith("}t") and elem.text:
                    parts.append(elem.text)
                elif elem.tag.endswith("}p"):
                    parts.append("\n")
    return re.sub(r"\n{3,}", "\n\n", "".join(parts)).strip()


def _extract_text(content: bytes, *, encoding: str | None, content_type: str | None, suffix: str) -> str:
    content_type = (content_type or "").lower()
    suffix = suffix.lower()
    if suffix == ".docx" or "wordprocessingml.document" in content_type:
        try:
            return _extract_docx_text(content)
        except Exception:
            return content.decode(encoding or "utf-8", errors="ignore")
    raw = content.decode(encoding or "utf-8", errors="ignore")
    if suffix in {".html", ".htm"} or "text/html" in content_type:
        return _html_to_text(raw)
    return raw


def _normalize_date(value: str) -> str:
    match = CN_DATE_RE.search(value) or ISO_DATE_RE.search(value)
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _clean_title(value: str) -> str:
    title = re.sub(r"\s+", " ", html.unescape(value or "")).strip()
    title = re.split(r"[-_—|｜]", title)[0].strip()
    return title[:180]


def _extract_policy_metadata(*, title: str, text: str, url: str) -> dict[str, str]:
    head = "\n".join((text or "").splitlines()[:120])
    candidates = [_clean_title(title)]
    for line in head.splitlines()[:40]:
        line = _clean_title(line)
        if 8 <= len(line) <= 120 and any(keyword in line for keyword in TITLE_KEYWORDS):
            candidates.append(line)
            break

    issuer = ""
    for hint in ISSUER_HINTS:
        if hint in head or hint in title or hint in url:
            issuer = hint
            break
    if not issuer:
        match = re.search(r"(?:发布机关|发文机关|制定机关|发布单位)[：:\s]+([\u4e00-\u9fa5A-Za-z（）()]{2,40})", head)
        if match:
            issuer = match.group(1).strip()

    doc_no = ""
    match = DOC_NO_RE.search(head)
    if match:
        doc_no = re.sub(r"\s+", "", match.group(1))

    published_at = ""
    for pattern in (
        r"(?:发布时间|发布日期|成文日期|发文日期)[：:\s]+([0-9年月日./-]{8,14})",
        r"([0-9]{4}年\s*[0-9]{1,2}月\s*[0-9]{1,2}日)",
        r"([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})",
    ):
        match = re.search(pattern, head)
        if match:
            published_at = _normalize_date(match.group(1))
            if published_at:
                break

    return {
        "title": next((candidate for candidate in candidates if candidate), ""),
        "issuer": issuer,
        "doc_no": doc_no,
        "published_at": published_at,
    }


async def ingest_url_candidate(url: str, *, title: str = "", task_id: str | None = None, node_id: str | None = None) -> KnowledgeDocument:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "EIA-AI-Assistant/0.1"})
        response.raise_for_status()
        content = response.content

    digest = _hash_bytes(content)
    snapshot_path = settings.knowledge_dir / "web_snapshots" / _safe_snapshot_name(url, digest)
    snapshot_path.write_bytes(content)

    raw_text = content.decode(response.encoding or "utf-8", errors="ignore")
    title_from_html = ""
    match = TITLE_RE.search(raw_text)
    if match:
        title_from_html = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    suffix = snapshot_path.suffix
    text = _extract_text(content, encoding=response.encoding, content_type=response.headers.get("content-type"), suffix=suffix)
    extracted = _extract_policy_metadata(title=title or title_from_html, text=text, url=url)

    text_path = settings.knowledge_dir / "extracted_text" / f"{digest[:16]}.txt"
    text_path.write_text(text[:2_000_000], encoding="utf-8", errors="ignore")

    doc = knowledge_store.create_candidate_url(
        url,
        title=title or extracted.get("title") or title_from_html or url,
        local_path=str(snapshot_path),
        text_path=str(text_path),
        file_hash=f"sha256:{digest}",
        metadata={
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "task_id": task_id,
            "node_id": node_id,
            "extracted_policy_metadata": extracted,
        },
    )
    changed = False
    for field in ("issuer", "doc_no", "published_at"):
        value = extracted.get(field)
        if value and not getattr(doc, field):
            setattr(doc, field, value)
            changed = True
    if extracted.get("title") and not title and doc.title == url:
        doc.title = extracted["title"]
        changed = True
    if changed:
        doc = knowledge_store.upsert_document(doc)
    return doc
