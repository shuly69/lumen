from fastapi.testclient import TestClient

from app.main import create_app


def make_client() -> TestClient:
    # TestClient runs lifespan, so app.state.store is initialized.
    return TestClient(create_app())


def test_health_reports_state():
    with make_client() as client:
        body = client.get("/api/health").json()
        assert body["status"] == "ok"
        assert body["document_count"] == 0
        assert "model" in body


def test_document_lifecycle():
    with make_client() as client:
        created = client.post(
            "/api/documents",
            json={"title": "Notes", "content": "The mitochondria is the powerhouse of the cell."},
        )
        assert created.status_code == 201
        doc_id = created.json()["id"]
        assert created.json()["chunk_count"] >= 1

        listing = client.get("/api/documents").json()
        assert listing["total_chunks"] >= 1
        assert any(d["id"] == doc_id for d in listing["documents"])

        assert client.delete(f"/api/documents/{doc_id}").status_code == 204
        assert client.delete(f"/api/documents/{doc_id}").status_code == 404


def test_empty_document_rejected():
    with make_client() as client:
        resp = client.post("/api/documents", json={"title": "x", "content": "   "})
        assert resp.status_code == 422


def test_chat_without_documents_streams_error_event():
    with make_client() as client:
        with client.stream("POST", "/api/chat", json={"question": "hi"}) as resp:
            body = "".join(resp.iter_text())
        assert "event: error" in body
        assert "No documents" in body
