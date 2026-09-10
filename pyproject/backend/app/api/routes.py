import asyncio
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile

from app.auth import AuthUser, current_user, login_user, register_user
from app.config import DOCS_DIR, MAX_CSV_ROWS, MAX_UPLOAD_BYTES, USER_LLM_API_KEY
from app.db import (
    analytics,
    delete_session,
    ensure_conversation,
    get_history,
    list_conversations,
    save_feedback,
    save_message,
)
from app.models import (
    AuthRequest,
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    FeedbackRequest,
    HealthResponse,
    UploadResponse,
)
from app.rag.pipeline import RAGPipeline
from app.services.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()
pipeline = RAGPipeline()
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _client_key(request: Request, user: AuthUser | None) -> str:
    if user:
        return user.id
    return request.client.host if request.client else "anon"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        documents=pipeline.document_count,
        chunks=pipeline.chunk_count,
        llm_configured=bool(USER_LLM_API_KEY),
        auth_required=True,
    )


@router.post("/auth/register")
def register(payload: AuthRequest) -> dict:
    return register_user(payload.username, payload.password)


@router.post("/auth/login")
def login(payload: AuthRequest) -> dict:
    return login_user(payload.username, payload.password)


@router.post("/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    user: AuthUser = Depends(current_user),
) -> dict:
    if authorization and authorization.startswith("Bearer "):
        delete_session(authorization.split(" ", 1)[1].strip())
    return {"status": "ok", "username": user.username}


@router.get("/me")
def me(user: AuthUser = Depends(current_user)) -> dict:
    return {"id": user.id, "username": user.username}


@router.get("/conversations")
def conversations(user: AuthUser = Depends(current_user)) -> dict:
    return {"conversations": list_conversations(user.id)}


@router.post("/conversations")
def create_conversation(payload: ConversationCreate, user: AuthUser = Depends(current_user)) -> dict:
    conversation_id = ensure_conversation(None, user.id, payload.title or "Nova conversa")
    return {"id": conversation_id, "title": payload.title or "Nova conversa"}


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    user: AuthUser = Depends(current_user),
) -> ChatResponse:
    key = _client_key(request, user)
    if not limiter.allow(key):
        raise HTTPException(status_code=429, detail="Limite de requisicoes excedido")
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Pergunta vazia")
    result = pipeline.query(question)
    try:
        conversation_id = ensure_conversation(payload.conversation_id, user.id, question[:80])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    message_id = save_message(
        conversation_id,
        result["question"],
        result["answer"],
        ",".join(result["sources"]),
        result["confidence"],
    )
    logger.info("chat user=%s conversation=%s confidence=%s", user.username, conversation_id, result["confidence"])
    return ChatResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
        conversation_id=conversation_id,
        message_id=message_id,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    user: AuthUser = Depends(current_user),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo sem nome")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf", ".docx", ".csv"}:
        raise HTTPException(status_code=400, detail="Formato nao suportado")
    safe = SAFE_NAME.sub("_", Path(file.filename).name)
    dest = DOCS_DIR / safe
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo maior que {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    dest.write_bytes(content)
    chunks = await asyncio.to_thread(pipeline.ingest_path, dest)
    warning = None
    if suffix == ".csv" and chunks >= MAX_CSV_ROWS:
        warning = f"CSV grande: indexei as primeiras {MAX_CSV_ROWS} linhas para manter o sistema estavel."
    logger.info("upload user=%s file=%s chunks=%s", user.username, safe, chunks)
    return UploadResponse(filename=safe, chunks=chunks, status="ok", warning=warning)


@router.get("/history/{conversation_id}")
def history(conversation_id: str, user: AuthUser = Depends(current_user)) -> dict:
    return {"conversation_id": conversation_id, "messages": get_history(conversation_id, user.id)}


@router.post("/feedback")
def feedback(payload: FeedbackRequest, user: AuthUser = Depends(current_user)) -> dict:
    feedback_id = save_feedback(payload.message_id, payload.rating, payload.comment)
    return {"id": feedback_id, "status": "ok"}


@router.get("/analytics")
def get_analytics(user: AuthUser = Depends(current_user)) -> dict:
    return analytics(user.id)
