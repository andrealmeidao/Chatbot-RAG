from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    confidence: float
    conversation_id: str
    message_id: str


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    status: str
    warning: str | None = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = None


class HealthResponse(BaseModel):
    status: str
    documents: int
    chunks: int
    llm_configured: bool
    auth_required: bool = True


class AuthRequest(BaseModel):
    username: str = ""
    password: str = ""


class ConversationCreate(BaseModel):
    title: str | None = None
