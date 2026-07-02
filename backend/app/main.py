"""FastAPI application factory and wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .retrieval import build_retriever
from .routes import chat, documents
from .schemas import HealthResponse
from .store import DocumentStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.store = DocumentStore(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        retriever=build_retriever(settings),
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Lumen API",
        version="0.1.0",
        summary="Grounded, cited answers over your documents, powered by Claude.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents.router)
    app.include_router(chat.router)

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        store = get_store_safe(app)
        return HealthResponse(
            status="ok",
            llm_configured=settings.is_llm_configured,
            model=settings.model,
            document_count=store.document_count if store else 0,
        )

    return app


def get_store_safe(app: FastAPI) -> DocumentStore | None:
    return getattr(app.state, "store", None)


app = create_app()
