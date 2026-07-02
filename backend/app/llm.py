"""Claude integration: turn retrieved chunks into a grounded, streamed answer.

We keep the model on a tight leash — answer only from the supplied sources and cite
them with [n] markers — which is what makes a RAG answer trustworthy rather than a
confident hallucination.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from .config import Settings
from .retrieval import ScoredChunk

SYSTEM_PROMPT = """You are Lumen, a precise research assistant. Answer the user's \
question using ONLY the numbered sources provided. Follow these rules:

- Cite every claim with its source marker, e.g. "Photosynthesis converts light to \
chemical energy [1]." Cite multiple sources as [1][3] when relevant.
- If the sources do not contain the answer, say so plainly: "The provided documents \
don't cover this." Do not use outside knowledge to fill the gap.
- Be concise and factual. Lead with the answer, then the supporting detail.
- Never invent a source marker that wasn't provided."""


def build_source_block(chunks: list[ScoredChunk]) -> str:
    parts = []
    for i, sc in enumerate(chunks, start=1):
        parts.append(f"[{i}] (from “{sc.chunk.document_title}”)\n{sc.chunk.text}")
    return "\n\n".join(parts)


def build_user_message(question: str, chunks: list[ScoredChunk]) -> str:
    sources = build_source_block(chunks)
    return f"Sources:\n\n{sources}\n\n---\n\nQuestion: {question}"


async def stream_answer(
    settings: Settings,
    question: str,
    chunks: list[ScoredChunk],
) -> AsyncIterator[str]:
    """Yield answer text deltas as they arrive from Claude."""
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    async with client.messages.stream(
        model=settings.model,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(question, chunks)}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
