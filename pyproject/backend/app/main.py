from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import pipeline, router
from app.config import DOCS_DIR
from app.db import init_db
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    init_db()
    if pipeline.chunk_count == 0:
        pipeline.ingest_directory(DOCS_DIR)
    yield


app = FastAPI(title="Chatbot RAG", version="1.6.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": "Chatbot RAG", "docs": "/docs", "health": "/health"}
