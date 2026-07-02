"""Chunking + lexical retrieval.

The retriever is kept behind a small interface so the storage/scoring strategy can
evolve (e.g. swap BM25 for vector embeddings) without touching the routes. For a
compact, dependency-light demo we use BM25 over word tokens, which needs no model
downloads and works fully offline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def chunk_text(text: str, *, size: int, overlap: int) -> list[str]:
    """Split text into overlapping windows, preferring paragraph boundaries.

    Overlap keeps context intact across chunk edges so an answer isn't cut in half.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""

    for para in paragraphs:
        if len(buffer) + len(para) + 2 <= size:
            buffer = f"{buffer}\n\n{para}".strip()
            continue
        if buffer:
            chunks.append(buffer)
        # Paragraph itself may exceed the window — hard-split it.
        if len(para) <= size:
            buffer = para
        else:
            for start in range(0, len(para), size - overlap):
                chunks.append(para[start : start + size])
            buffer = ""

    if buffer:
        chunks.append(buffer)
    return chunks


@dataclass(frozen=True)
class Chunk:
    document_id: str
    document_title: str
    text: str


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class BM25Retriever:
    """In-memory BM25 index rebuilt whenever the corpus changes.

    Rebuilding is O(n) over chunks; for a demo corpus that is trivially fast and keeps
    the code honest and easy to reason about.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._index: BM25Okapi | None = None

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def rebuild(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._index = BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None

    def search(self, query: str, *, top_k: int) -> list[ScoredChunk]:
        if self._index is None or not self._chunks:
            return []
        query_tokens = tokenize(query)
        scores = self._index.get_scores(query_tokens)
        ranked = sorted(zip(scores, self._chunks, strict=True), key=lambda x: x[0], reverse=True)
        positive = [
            ScoredChunk(chunk=chunk, score=float(score))
            for score, chunk in ranked[:top_k]
            if score > 0
        ]
        if positive:
            return positive
        # Small-corpus fallback: BM25's IDF term collapses to 0 when a token appears
        # in ~half of a tiny document set, so every score can be 0. Rank by raw
        # query-term overlap instead so retrieval still works on a handful of docs.
        return self._overlap_search(set(query_tokens), top_k=top_k)

    def _overlap_search(self, query_tokens: set[str], *, top_k: int) -> list[ScoredChunk]:
        hits = []
        for chunk in self._chunks:
            overlap = sum(1 for t in tokenize(chunk.text) if t in query_tokens)
            if overlap:
                hits.append(ScoredChunk(chunk=chunk, score=float(overlap)))
        hits.sort(key=lambda s: s.score, reverse=True)
        return hits[:top_k]
