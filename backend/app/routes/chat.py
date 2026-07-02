"""Streaming RAG chat endpoint (Server-Sent Events).

The client opens one POST and receives a sequence of typed SSE events:
  - `sources` : the retrieved chunks the answer is grounded in (sent first)
  - `token`   : incremental answer text as the model generates it
  - `done`    : end-of-stream marker
  - `error`   : a terminal error with a human-readable message
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from ..config import Settings, get_settings
from ..deps import get_store
from ..llm import stream_answer
from ..retrieval import ScoredChunk
from ..schemas import ChatRequest, Citation
from ..store import DocumentStore

router = APIRouter(prefix="/api", tags=["chat"])


def _citations(chunks: list[ScoredChunk]) -> list[Citation]:
    return [
        Citation(
            marker=i,
            document_id=sc.chunk.document_id,
            document_title=sc.chunk.document_title,
            snippet=_snippet(sc.chunk.text),
            score=round(sc.score, 3),
        )
        for i, sc in enumerate(chunks, start=1)
    ]


def _snippet(text: str, limit: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _event(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


async def _stream(
    request: ChatRequest,
    store: DocumentStore,
    settings: Settings,
) -> AsyncIterator[dict]:
    if store.document_count == 0:
        yield _event("error", {"message": "No documents yet — add one before asking."})
        return

    if not settings.is_llm_configured:
        yield _event("error", {"message": "The server has no Anthropic API key configured."})
        return

    chunks = store.search(request.question, top_k=settings.top_k)
    citations = _citations(chunks)
    yield _event("sources", {"citations": [c.model_dump() for c in citations]})

    if not chunks:
        yield _event("token", {"text": "The provided documents don't cover this question."})
        yield _event("done", {})
        return

    try:
        async for text in stream_answer(settings, request.question, chunks):
            yield _event("token", {"text": text})
    except Exception as exc:  # surface upstream failures to the client, don't hang the stream
        yield _event("error", {"message": f"Model request failed: {exc}"})
        return

    yield _event("done", {})


@router.post("/chat")
async def chat(
    request: ChatRequest,
    store: DocumentStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> EventSourceResponse:
    return EventSourceResponse(_stream(request, store, settings))
