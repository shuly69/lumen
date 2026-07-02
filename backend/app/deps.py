"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from .store import DocumentStore


def get_store(request: Request) -> DocumentStore:
    return request.app.state.store
