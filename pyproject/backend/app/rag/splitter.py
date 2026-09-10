from app.config import CHUNK_OVERLAP, CHUNK_SIZE
from app.rag.loader import Document
from app.rag.textutils import QA_SPLIT_RE, NUMBERED_SPLIT_RE, extract_question_numbers


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) <= chunk_size:
        return [normalized]
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = start + chunk_size
        piece = normalized[start:end].strip()
        if end < len(normalized):
            cut = piece.rfind("\n")
            if cut < chunk_size * 0.4:
                cut = piece.rfind(". ")
            if cut >= chunk_size * 0.4:
                piece = piece[: cut + 1].strip()
                end = start + len(piece)
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def _qa_parts(text: str) -> list[str]:
    labeled = [p.strip() for p in QA_SPLIT_RE.split(text) if p and p.strip()]
    if len(labeled) >= 2:
        return labeled
    numbered = [p.strip() for p in NUMBERED_SPLIT_RE.split(text) if p and p.strip()]
    if len(numbered) >= 3:
        return numbered
    return []


def split_documents(documents: list[Document]) -> list[Document]:
    chunks: list[Document] = []
    for doc in documents:
        heading = doc.metadata.get("heading") or ""
        kind = doc.metadata.get("kind") or "section"
        if kind == "row":
            meta = dict(doc.metadata)
            meta["chunk"] = 0
            chunks.append(Document(doc.page_content, meta))
            continue
        qa_parts = _qa_parts(doc.page_content)
        parts = qa_parts if qa_parts else split_text(doc.page_content)
        for i, part in enumerate(parts):
            meta = dict(doc.metadata)
            meta["chunk"] = i
            numbers = extract_question_numbers(part)
            if numbers:
                meta["kind"] = "qa"
                meta["record_id"] = numbers[0]
                meta["heading"] = f"Pergunta {numbers[0]}"
                heading_for_part = meta["heading"]
            else:
                heading_for_part = heading
            content = part
            if heading_for_part and heading_for_part not in part[: len(heading_for_part) + 8]:
                content = f"{heading_for_part}\n{part}"
            chunks.append(Document(content, meta))
    return chunks
