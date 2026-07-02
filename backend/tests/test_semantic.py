"""Semantic + hybrid retrieval logic, tested with a deterministic stub embedder.

Using a stub keeps these tests fast and offline — no model download — while still
exercising cosine ranking and Reciprocal Rank Fusion.
"""

from app.retrieval import Chunk, HybridRetriever, SemanticRetriever


class StubEmbedder:
    """Maps text to a fixed vector by keyword, so 'similarity' is predictable."""

    VOCAB = ["plant", "oxygen", "money", "water"]

    def _vector(self, text: str) -> list[float]:
        text = text.lower()
        return [1.0 if word in text else 0.0 for word in self.VOCAB]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


def _chunks() -> list[Chunk]:
    return [
        Chunk("d1", "Biology", "plant oxygen photosynthesis"),
        Chunk("d2", "Finance", "money investment growth"),
    ]


def test_semantic_ranks_by_meaning_not_shared_words():
    r = SemanticRetriever(StubEmbedder())
    r.rebuild(_chunks())
    # Query shares NO literal words with the biology chunk, but embeds near it.
    hits = r.search("oxygen", top_k=2)
    assert hits
    assert hits[0].chunk.document_id == "d1"
    assert hits[0].score > 0


def test_semantic_empty_corpus():
    r = SemanticRetriever(StubEmbedder())
    r.rebuild([])
    assert r.search("anything", top_k=3) == []


def test_hybrid_fuses_both_signals():
    r = HybridRetriever(StubEmbedder())
    r.rebuild(_chunks())
    hits = r.search("plant", top_k=2)
    assert hits
    assert hits[0].chunk.document_id == "d1"
    # RRF scores are small positive fractions.
    assert 0 < hits[0].score < 1
    assert r.chunk_count == 2
