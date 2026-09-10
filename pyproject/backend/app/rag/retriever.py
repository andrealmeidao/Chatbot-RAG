from app.config import TOP_K
from app.rag.embeddings import embed_query
from app.rag.loader import Document
from app.rag.textutils import extract_question_numbers, extract_record_ids, extract_skus, has_word, normalize, significant_tokens
from app.rag.vectorstore import VectorStore

GENERIC_HEADINGS = {
    "conclusao",
    "conclusoes",
    "referencias",
    "bibliografia",
    "agradecimentos",
    "anexo",
    "capa",
}


def _exact_id_hits(store: VectorStore, question: str) -> list[tuple[Document, float]]:
    ids = extract_skus(question) + extract_record_ids(question)
    hits = [(doc, 12.0) for doc in store.find_by_ids(ids)]
    if hits:
        return hits
    numbers = extract_question_numbers(question)
    if not numbers:
        return []
    found: list[tuple[Document, float]] = []
    for doc in store.documents:
        if str(doc.metadata.get("kind")) == "qa" and str(doc.metadata.get("record_id")) in numbers:
            found.append((doc, 11.0))
    return found


def lexical_score(question: str, doc: Document) -> float:
    q_tokens = set(significant_tokens(question))
    if not q_tokens:
        return 0.0
    heading = normalize(str(doc.metadata.get("heading") or ""))
    source = normalize(str(doc.metadata.get("source") or ""))
    body = normalize(doc.page_content)
    h_tokens = set(significant_tokens(heading))
    b_tokens = set(significant_tokens(doc.page_content))
    qn = normalize(question)
    record_id = str(doc.metadata.get("record_id") or "")

    heading_overlap = len(q_tokens & h_tokens) / max(len(q_tokens), 1)
    body_overlap = len(q_tokens & b_tokens) / max(len(q_tokens), 1)
    score = heading_overlap * 2.4 + body_overlap * 0.9

    if heading and (heading in qn or qn in heading):
        score += 3.5
    phrase_hits = 0
    words = [tok for tok in significant_tokens(question)]
    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i + 1]}"
        if phrase in heading:
            phrase_hits += 2
        elif phrase in body:
            phrase_hits += 0.4
    score += phrase_hits

    source_tokens = set(significant_tokens(source.replace("_", " ").replace(".", " ")))
    if source_tokens & q_tokens:
        score += 0.8

    for sku in extract_skus(question):
        if has_word(record_id, sku) or has_word(heading, sku) or has_word(doc.page_content, sku):
            score += 8.0
    for number in extract_question_numbers(question):
        if str(doc.metadata.get("kind")) == "qa" and str(doc.metadata.get("record_id")) == number:
            score += 8.0
        elif f"pergunta {number}" in heading or heading == number:
            score += 6.0

    if heading in GENERIC_HEADINGS and heading not in qn and "conclus" not in qn:
        score *= 0.15
    return score


def hybrid_search(store: VectorStore, question: str, k: int = TOP_K) -> list[tuple[Document, float]]:
    if not store.documents:
        return []
    exact = _exact_id_hits(store, question)
    if exact:
        return exact[: min(k, len(exact))]

    query_vec = embed_query(question)
    vector_hits = store.similarity_search(query_vec, k=min(max(k * 4, 8), len(store.documents)))
    vector_by_id = {id(doc): max(0.0, score) for doc, score in vector_hits}

    ranked: list[tuple[Document, float]] = []
    for doc in store.documents:
        lex = lexical_score(question, doc)
        vec = vector_by_id.get(id(doc), 0.0)
        score = lex * 0.72 + vec * 0.28
        ranked.append((doc, score))
    ranked.sort(key=lambda item: item[1], reverse=True)

    selected: list[tuple[Document, float]] = []
    seen_headings: set[str] = set()
    for doc, score in ranked:
        heading = normalize(str(doc.metadata.get("heading") or ""))
        if heading in seen_headings and len(selected) >= k:
            continue
        selected.append((doc, score))
        seen_headings.add(heading)
        if len(selected) >= k:
            break
    return selected
