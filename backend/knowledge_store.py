from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlparse

from .config import settings
from .models import KnowledgeDocument, now_iso


BAD_URL_MARKERS = ("附件URL", "URL：", "；")


def _db_path() -> Path:
    if settings.database_url.startswith("sqlite:///"):
        return Path(settings.database_url.replace("sqlite:///", "", 1))
    return settings.root_dir / "data" / "app.db"


def _validate_http_url(url: str) -> str:
    candidate = (url or "").strip()
    parsed = urlparse(candidate)
    scheme_count = candidate.count("http://") + candidate.count("https://")
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or scheme_count != 1
        or re.search(r"\s", candidate)
        or any(marker in candidate for marker in BAD_URL_MARKERS)
    ):
        raise ValueError(f"Invalid evidence URL: {url}")
    return candidate


class KnowledgeStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or _db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists knowledge_documents (
                    id text primary key,
                    title text not null,
                    source_type text not null,
                    source_url text,
                    source_domain text,
                    issuer text,
                    doc_no text,
                    published_at text,
                    retrieved_at text not null,
                    file_hash text,
                    status text not null,
                    validity text not null,
                    local_path text,
                    text_path text,
                    metadata_json text not null
                );
                create index if not exists idx_knowledge_status on knowledge_documents(status);
                create index if not exists idx_knowledge_source_url on knowledge_documents(source_url);
                create table if not exists web_search_records (
                    id text primary key,
                    task_id text,
                    node_id text,
                    query text,
                    result_url text,
                    title text,
                    snippet text,
                    created_at text not null,
                    metadata_json text not null
                );
                """
            )

    def list_documents(self, status: str | None = None) -> list[KnowledgeDocument]:
        sql = "select * from knowledge_documents"
        params: list[str] = []
        if status:
            sql += " where status = ?"
            params.append(status)
        sql += " order by retrieved_at desc"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_doc(row) for row in rows]

    def get_document(self, doc_id: str) -> KnowledgeDocument | None:
        with self.connect() as conn:
            row = conn.execute("select * from knowledge_documents where id = ?", (doc_id,)).fetchone()
        return self._row_to_doc(row) if row else None

    def get_active_candidate_by_url(self, url: str) -> KnowledgeDocument | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                select * from knowledge_documents
                where source_url = ?
                  and status not in ('rejected', 'deprecated')
                order by retrieved_at desc
                limit 1
                """,
                (url,),
            ).fetchone()
        return self._row_to_doc(row) if row else None

    def upsert_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        with self.connect() as conn:
            conn.execute(
                """
                insert into knowledge_documents (
                    id, title, source_type, source_url, source_domain, issuer, doc_no,
                    published_at, retrieved_at, file_hash, status, validity,
                    local_path, text_path, metadata_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    title=excluded.title,
                    source_type=excluded.source_type,
                    source_url=excluded.source_url,
                    source_domain=excluded.source_domain,
                    issuer=excluded.issuer,
                    doc_no=excluded.doc_no,
                    published_at=excluded.published_at,
                    retrieved_at=excluded.retrieved_at,
                    file_hash=excluded.file_hash,
                    status=excluded.status,
                    validity=excluded.validity,
                    local_path=excluded.local_path,
                    text_path=excluded.text_path,
                    metadata_json=excluded.metadata_json
                """,
                (
                    doc.id,
                    doc.title,
                    doc.source_type,
                    doc.source_url,
                    doc.source_domain,
                    doc.issuer,
                    doc.doc_no,
                    doc.published_at,
                    doc.retrieved_at,
                    doc.file_hash,
                    doc.status,
                    doc.validity,
                    doc.local_path,
                    doc.text_path,
                    json.dumps(doc.metadata, ensure_ascii=False),
                ),
            )
        return doc

    def create_candidate_url(
        self,
        url: str,
        *,
        title: str = "",
        metadata: dict | None = None,
        local_path: str | None = None,
        text_path: str | None = None,
        file_hash: str | None = None,
    ) -> KnowledgeDocument:
        url = _validate_http_url(url)
        parsed = urlparse(url)
        existing = self.get_active_candidate_by_url(url)
        if existing:
            existing.title = title or existing.title
            existing.local_path = local_path or existing.local_path
            existing.text_path = text_path or existing.text_path
            existing.file_hash = file_hash or existing.file_hash
            existing.metadata = {**existing.metadata, **(metadata or {})}
            return self.upsert_document(existing)

        doc = KnowledgeDocument(
            id=str(uuid.uuid4()),
            title=title or parsed.path.rsplit("/", 1)[-1] or url,
            source_type="web_candidate",
            source_url=url,
            source_domain=parsed.netloc,
            retrieved_at=now_iso(),
            file_hash=file_hash,
            status="candidate",
            validity="unknown",
            local_path=local_path,
            text_path=text_path,
            metadata=metadata or {},
        )
        return self.upsert_document(doc)

    def verify_document(self, doc_id: str, status: str = "verified") -> KnowledgeDocument:
        doc = self.get_document(doc_id)
        if not doc:
            raise FileNotFoundError(doc_id)
        doc.status = status  # type: ignore[assignment]
        return self.upsert_document(doc)

    def review_document(
        self,
        doc_id: str,
        *,
        status: str,
        validity: str | None = None,
        title: str | None = None,
        issuer: str | None = None,
        doc_no: str | None = None,
        published_at: str | None = None,
        reviewer: str | None = None,
        note: str | None = None,
    ) -> KnowledgeDocument:
        doc = self.get_document(doc_id)
        if not doc:
            raise FileNotFoundError(doc_id)

        doc.status = status  # type: ignore[assignment]
        if status == "verified" and doc.source_url:
            doc.source_type = "official_url"
            doc.validity = validity or "effective"  # type: ignore[assignment]
        elif status == "deprecated":
            doc.validity = validity or "superseded"  # type: ignore[assignment]
        elif validity:
            doc.validity = validity  # type: ignore[assignment]

        if title:
            doc.title = title
        if issuer is not None:
            doc.issuer = issuer or None
        if doc_no is not None:
            doc.doc_no = doc_no or None
        if published_at is not None:
            doc.published_at = published_at or None

        review_record = {
            "status": status,
            "validity": doc.validity,
            "reviewer": reviewer or "manual",
            "note": note or "",
            "reviewed_at": now_iso(),
        }
        review_history = doc.metadata.get("review_history")
        if not isinstance(review_history, list):
            review_history = []
        doc.metadata = {
            **doc.metadata,
            "review": review_record,
            "review_history": [*review_history, review_record],
        }
        return self.upsert_document(doc)

    def record_web_search(
        self,
        *,
        task_id: str | None,
        node_id: str | None,
        query: str,
        result_url: str,
        title: str = "",
        snippet: str = "",
        metadata: dict | None = None,
    ) -> str:
        record_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                insert into web_search_records (
                    id, task_id, node_id, query, result_url, title, snippet, created_at, metadata_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    task_id,
                    node_id,
                    query,
                    result_url,
                    title,
                    snippet,
                    now_iso(),
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
        return record_id

    @staticmethod
    def _row_to_doc(row: sqlite3.Row) -> KnowledgeDocument:
        data = dict(row)
        data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
        return KnowledgeDocument.model_validate(data)


knowledge_store = KnowledgeStore()
