"""CRUD for the document corpus."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_store
from ..schemas import DocumentIn, DocumentList, DocumentSummary
from ..store import Document, DocumentStore

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _summary(doc: Document) -> DocumentSummary:
    return DocumentSummary(
        id=doc.id,
        title=doc.title,
        chunk_count=len(doc.chunks),
        char_count=len(doc.content),
        created_at=doc.created_at,
    )


@router.get("", response_model=DocumentList)
def list_documents(store: DocumentStore = Depends(get_store)) -> DocumentList:
    return DocumentList(
        documents=[_summary(d) for d in store.list()],
        total_chunks=store.chunk_count,
    )


@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentIn,
    store: DocumentStore = Depends(get_store),
) -> DocumentSummary:
    doc = store.add(title=payload.title, content=payload.content)
    if not doc.chunks:
        store.delete(doc.id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document produced no indexable text.",
        )
    return _summary(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, store: DocumentStore = Depends(get_store)) -> None:
    if not store.delete(doc_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
