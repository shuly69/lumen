from app.retrieval import chunk_text, tokenize
from app.store import DocumentStore


def test_tokenize_lowercases_and_splits():
    assert tokenize("Hello, World! 42") == ["hello", "world", "42"]


def test_chunk_text_respects_size_with_overlap():
    text = "\n\n".join(f"Paragraph number {i} with some filler words." for i in range(20))
    chunks = chunk_text(text, size=120, overlap=30)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)  # windows stay bounded


def test_chunk_text_empty():
    assert chunk_text("   ", size=100, overlap=10) == []


def test_store_indexes_and_ranks_relevant_chunk_first():
    store = DocumentStore(chunk_size=400, chunk_overlap=50)
    store.add(
        title="Biology",
        content="Photosynthesis converts sunlight into chemical energy in plants.",
    )
    store.add(
        title="Finance",
        content="Compound interest grows an investment exponentially over time.",
    )

    hits = store.search("How do plants use sunlight?", top_k=2)
    assert hits, "expected at least one hit"
    assert "Photosynthesis" in hits[0].chunk.text
    assert hits[0].score > 0


def test_store_delete_reindexes():
    store = DocumentStore(chunk_size=400, chunk_overlap=50)
    doc = store.add(title="Doc", content="unique_token_xyz appears here.")
    assert store.chunk_count == 1
    assert store.delete(doc.id) is True
    assert store.chunk_count == 0
    assert store.search("unique_token_xyz", top_k=3) == []
