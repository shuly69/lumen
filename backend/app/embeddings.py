"""Text embedding for semantic retrieval.

Kept behind a tiny `Embedder` protocol so the concrete backend is swappable and — more
importantly — so retrieval can be unit-tested with a deterministic stub, without pulling
in a model download. The default implementation uses `fastembed` (ONNX, CPU-friendly,
no torch), which is an optional dependency installed via the `semantic` extra.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one dense vector per input text."""
        ...


class FastEmbedEmbedder:
    """Lazy-loaded fastembed backend. The model is fetched on first use, not at import."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None  # loaded on demand

    def _ensure_loaded(self) -> None:
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:  # pragma: no cover - depends on optional extra
                raise RuntimeError(
                    "Semantic retrieval requires the 'semantic' extra: pip install '.[semantic]'"
                ) from exc
            self._model = TextEmbedding(model_name=self._model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_loaded()
        return [list(map(float, vector)) for vector in self._model.embed(texts)]
