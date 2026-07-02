"""In-memory document store wired to the retriever.

A single process-wide instance backs the API. Swapping this for Postgres + pgvector
would mean reimplementing this class against the same method surface — the routes
would not change.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .retrieval import BM25Retriever, Chunk, ScoredChunk, chunk_text


@dataclass
class Document:
    id: str
    title: str
    content: str
    chunks: list[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DocumentStore:
    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._docs: dict[str, Document] = {}
        self._retriever = BM25Retriever()
        self._lock = threading.Lock()

    def add(self, *, title: str, content: str) -> Document:
        chunks = chunk_text(content, size=self._chunk_size, overlap=self._chunk_overlap)
        doc = Document(id=uuid.uuid4().hex[:12], title=title, content=content, chunks=chunks)
        with self._lock:
            self._docs[doc.id] = doc
            self._reindex()
        return doc

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            removed = self._docs.pop(doc_id, None) is not None
            if removed:
                self._reindex()
        return removed

    def list(self) -> list[Document]:
        return sorted(self._docs.values(), key=lambda d: d.created_at)

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    @property
    def document_count(self) -> int:
        return len(self._docs)

    @property
    def chunk_count(self) -> int:
        return self._retriever.chunk_count

    def search(self, query: str, *, top_k: int) -> list[ScoredChunk]:
        return self._retriever.search(query, top_k=top_k)

    def _reindex(self) -> None:
        chunks = [
            Chunk(document_id=doc.id, document_title=doc.title, text=text)
            for doc in self._docs.values()
            for text in doc.chunks
        ]
        self._retriever.rebuild(chunks)
