from fastapi.testclient import TestClient

from app.api.routes import pipeline
from app.db import init_db
from app.main import app
from app.rag.embeddings import embed_texts
from app.rag.loader import Document
from app.rag.vectorstore import VectorStore

client = TestClient(app)


def auth_headers(username: str = "alice", password: str = "secret1") -> dict:
    response = client.post("/auth/register", json={"username": username, "password": password})
    if response.status_code == 409:
        response = client.post("/auth/login", json={"username": username, "password": password})
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def setup_module() -> None:
    init_db()
    pipeline.store.reset()
    docs = [
        Document(
            "Politica de Refund. Refund e permitido em 30 dias apos a compra. Produto deve estar novo e sem marcas de uso.",
            {"source": "politica.txt", "page": 1, "heading": "Politica de Refund"},
        )
    ]
    pipeline.store.add(embed_texts([docs[0].page_content]), docs)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["auth_required"] is True


def test_chat_requires_auth():
    response = client.post("/chat", json={"question": "Qual e a politica de refund?"})
    assert response.status_code == 401


def test_register_validates_credentials():
    empty = client.post("/auth/register", json={"username": "", "password": ""})
    assert empty.status_code == 400
    short = client.post("/auth/register", json={"username": "ab", "password": "123"})
    assert short.status_code == 400
    assert "Usuario" in short.json()["detail"] or "Senha" in short.json()["detail"]


def test_register_login_and_chat():
    headers = auth_headers("bob", "secret1")
    response = client.post("/chat", json={"question": "Qual e a politica de refund?"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert body["conversation_id"]
    assert body["message_id"]


def test_history_feedback_and_conversations():
    headers = auth_headers("carol", "secret1")
    chat = client.post("/chat", json={"question": "Posso devolver?"}, headers=headers).json()
    history = client.get(f"/history/{chat['conversation_id']}", headers=headers)
    assert history.status_code == 200
    assert history.json()["messages"]
    listed = client.get("/conversations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["conversations"]
    feedback = client.post(
        "/feedback",
        json={"message_id": chat["message_id"], "rating": 1, "comment": "util"},
        headers=headers,
    )
    assert feedback.status_code == 200
    analytics = client.get("/analytics", headers=headers)
    assert analytics.status_code == 200
    assert analytics.json()["total_questions"] >= 1


def test_conversation_isolation():
    alice = auth_headers("dave", "secret1")
    erin = auth_headers("erin", "secret1")
    chat = client.post("/chat", json={"question": "Posso devolver um produto?"}, headers=alice).json()
    other = client.get(f"/history/{chat['conversation_id']}", headers=erin)
    assert other.json()["messages"] == []


def test_upload():
    headers = auth_headers("frank", "secret1")
    response = client.post(
        "/upload",
        files={"file": ("manual.txt", b"Como instalar a versao 2.0 do software.", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
