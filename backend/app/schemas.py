"""Pydantic request/response models — the typed contract between API and clients."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, description="Raw text content of the document.")


class DocumentSummary(BaseModel):
    id: str
    title: str
    chunk_count: int
    char_count: int
    created_at: datetime


class DocumentList(BaseModel):
    documents: list[DocumentSummary]
    total_chunks: int


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    """A retrieved chunk offered to the model as a numbered source."""

    marker: int  # the [n] the model can cite
    document_id: str
    document_title: str
    snippet: str
    score: float


class HealthResponse(BaseModel):
    status: str
    llm_configured: bool
    model: str
    document_count: int
