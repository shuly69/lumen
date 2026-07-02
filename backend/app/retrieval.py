"""Chunking + lexical retrieval.

The retriever is kept behind a small interface so the storage/scoring strategy can
evolve (e.g. swap BM25 for vector embeddings) without touching the routes. For a
compact, dependency-light demo we use BM25 over word tokens, which needs no model
downloads and works fully offline.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rank_bm25 import BM25Okapi

if TYPE_CHECKING:
    from .config import Settings
    from .embeddings import Embedder

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


class Retriever(Protocol):
    """The surface the store depends on. Any strategy that implements this is swappable."""

    @property
    def chunk_count(self) -> int: ...

    def rebuild(self, chunks: list[Chunk]) -> None: ...

    def search(self, query: str, *, top_k: int) -> list[ScoredChunk]: ...


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


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class SemanticRetriever:
    """Dense-vector retrieval: embed chunks once, rank by cosine similarity to the query.

    Unlike BM25 this matches by meaning, so "what gas do plants release?" finds a passage
    about "oxygen" even with no shared words.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def rebuild(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._vectors = self._embedder.embed([c.text for c in chunks]) if chunks else []

    def search(self, query: str, *, top_k: int) -> list[ScoredChunk]:
        if not self._chunks:
            return []
        q = self._embedder.embed([query])[0]
        scored = [
            ScoredChunk(chunk=chunk, score=_cosine(q, vec))
            for vec, chunk in zip(self._vectors, self._chunks, strict=True)
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score > 0]


class HybridRetriever:
    """Fuse BM25 (lexical) and semantic rankings with Reciprocal Rank Fusion.

    RRF blends the two rank orders without needing their scores to be on the same scale —
    a robust, standard way to get the best of exact-term and semantic matching.
    """

    def __init__(self, embedder: Embedder, *, rrf_k: int = 60) -> None:
        self._bm25 = BM25Retriever()
        self._semantic = SemanticRetriever(embedder)
        self._rrf_k = rrf_k

    @property
    def chunk_count(self) -> int:
        return self._bm25.chunk_count

    def rebuild(self, chunks: list[Chunk]) -> None:
        self._bm25.rebuild(chunks)
        self._semantic.rebuild(chunks)

    def search(self, query: str, *, top_k: int) -> list[ScoredChunk]:
        pool = max(top_k * 3, 10)
        rankings = [
            self._bm25.search(query, top_k=pool),
            self._semantic.search(query, top_k=pool),
        ]
        fused: dict[Chunk, float] = {}
        for results in rankings:
            for rank, sc in enumerate(results):
                fused[sc.chunk] = fused.get(sc.chunk, 0.0) + 1.0 / (self._rrf_k + rank + 1)
        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)
        return [ScoredChunk(chunk=chunk, score=score) for chunk, score in ranked[:top_k]]


def build_retriever(settings: Settings) -> Retriever:
    """Construct the retriever selected by config. Embedding backends load lazily."""
    kind = settings.retriever.lower()
    if kind == "bm25":
        return BM25Retriever()
    if kind in ("semantic", "hybrid"):
        from .embeddings import FastEmbedEmbedder

        embedder = FastEmbedEmbedder(settings.embedding_model)
        return SemanticRetriever(embedder) if kind == "semantic" else HybridRetriever(embedder)
    raise ValueError(f"Unknown LUMEN_RETRIEVER={settings.retriever!r} (use bm25|semantic|hybrid)")
