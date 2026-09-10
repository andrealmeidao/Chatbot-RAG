import logging
from pathlib import Path

from app.config import DOCS_DIR, MAX_EMBEDDED_ROWS, TOP_K
from app.rag.embeddings import embed_texts
from app.rag.llm import generate_answer
from app.rag.loader import load_directory, load_document
from app.rag.retriever import hybrid_search
from app.rag.splitter import split_documents
from app.rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self) -> None:
        self.store = VectorStore()

    def _index_chunks(self, chunks: list) -> int:
        if not chunks:
            return 0
        rows = [c for c in chunks if c.metadata.get("kind") == "row"]
        others = [c for c in chunks if c.metadata.get("kind") != "row"]
        embeddable = others + rows[:MAX_EMBEDDED_ROWS]
        lookup_only = rows[MAX_EMBEDDED_ROWS:]
        if embeddable:
            embeddings = embed_texts([c.page_content for c in embeddable])
            self.store.add(embeddings, embeddable)
        if lookup_only:
            self.store.add_lookup(lookup_only)
        return len(chunks)

    def ingest_path(self, path: Path) -> int:
        documents = load_document(path)
        chunks = split_documents(documents)
        self.store.remove_source(path.name)
        count = self._index_chunks(chunks)
        logger.info("Ingested %s chunks from %s", count, path.name)
        return count

    def ingest_directory(self, directory: Path | None = None) -> int:
        directory = directory or DOCS_DIR
        documents = load_directory(directory)
        chunks = split_documents(documents)
        self.store.reset()
        count = self._index_chunks(chunks)
        logger.info("Indexed %s chunks from %s", count, directory)
        return count

    def query(self, question: str, k: int = TOP_K) -> dict:
        hits = hybrid_search(self.store, question, k=k)
        chunks = [doc for doc, _ in hits]
        scores = [score for _, score in hits]
        answer = generate_answer(question, chunks)
        sources = []
        for doc in chunks:
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", 1)
            heading = doc.metadata.get("heading")
            label = f"{source}:page{page}"
            if heading:
                label = f"{label} [{heading}]"
            if label not in sources:
                sources.append(label)
        confidence = max(scores) if scores else 0.0
        confidence = max(0.0, min(1.0, confidence / 6.0 if confidence > 1 else confidence))
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "confidence": round(float(confidence), 4),
        }

    @property
    def chunk_count(self) -> int:
        return self.store.chunk_count

    @property
    def document_count(self) -> int:
        return len(self.store.sources)
