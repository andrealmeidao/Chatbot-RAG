from app.config import LLM_MAX_TOKENS, LLM_TEMPERATURE, USER_LLM_API_KEY, USER_LLM_BASE_URL, USER_LLM_MODEL
from app.rag.loader import Document
from app.rag.retriever import lexical_score
from app.rag.textutils import extract_question_numbers, extract_skus, has_word, normalize, significant_tokens

SYSTEM_PROMPT = (
    "Voce e um assistente de documentos. "
    "Responda com base APENAS no contexto fornecido. "
    "Se a pergunta pedir um codigo, SKU, produto ou numero de questao, "
    "devolva SOMENTE o registro correspondente, sem linhas vizinhas. "
    "Se a pergunta pedir uma secao especifica (por exemplo 'explicacao do funcionamento'), "
    "use o trecho cujo titulo coincide com essa secao e nao use conclusao, resultados ou capa. "
    "Se nao souber, diga \"Nao tenho informacao sobre isso.\""
)


def build_prompt(question: str, chunks: list[Document]) -> str:
    context_parts = []
    for doc in chunks:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        heading = doc.metadata.get("heading", "")
        prefix = f"[{source}:page{page} | {heading}]" if heading else f"[{source}:page{page}]"
        context_parts.append(f"{prefix}\n{doc.page_content}")
    context = "\n\n".join(context_parts) if context_parts else "(sem contexto)"
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def _strip_heading(text: str, heading: str) -> str:
    if not heading:
        return text.strip()
    lines = text.splitlines()
    if lines and normalize(lines[0]) == normalize(heading):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def _clip(text: str, limit: int = 1400) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ["\n\n", "\n", ". "]:
        idx = cut.rfind(sep)
        if idx >= limit * 0.5:
            return cut[: idx + (0 if sep == "\n" else 1)].strip()
    return cut.rsplit(" ", 1)[0].strip() + "..."


def _pick_exact_chunk(question: str, chunks: list[Document]) -> Document | None:
    skus = extract_skus(question)
    numbers = extract_question_numbers(question)
    for doc in chunks:
        record_id = str(doc.metadata.get("record_id") or doc.metadata.get("heading") or "")
        if skus:
            for sku in skus:
                if has_word(record_id, sku) or has_word(doc.page_content, sku):
                    return doc
        if numbers and str(doc.metadata.get("kind")) == "qa" and str(doc.metadata.get("record_id")) in numbers:
            return doc
    return None


def _format_answer(title: str, text: str, source: str) -> str:
    body = text.strip()
    if title and not body.lower().startswith(title.lower()):
        return f"{title}\n\n{body}\n\nFonte: {source}"
    return f"{body}\n\nFonte: {source}"


def _extractive_answer(question: str, chunks: list[Document]) -> str:
    if not chunks:
        return "Nao tenho informacao sobre isso."
    exact = _pick_exact_chunk(question, chunks)
    if exact is not None:
        heading = str(exact.metadata.get("heading") or exact.metadata.get("record_id") or "")
        text = _strip_heading(exact.page_content, heading)
        return _format_answer(heading, text, exact.metadata.get("source", "documento"))

    scored = [(doc, lexical_score(question, doc)) for doc in chunks]
    scored.sort(key=lambda item: item[1], reverse=True)
    best, best_score = scored[0]
    if best_score <= 0:
        return "Nao tenho informacao sobre isso."

    heading = str(best.metadata.get("heading") or "")
    kind = str(best.metadata.get("kind") or "section")
    if kind in {"row", "qa"}:
        text = _strip_heading(best.page_content, heading)
        return _format_answer(heading, text, best.metadata.get("source", "documento"))

    same = [doc for doc, score in scored if doc.metadata.get("heading") == heading and score > 0]
    bodies = []
    seen = set()
    for doc in same:
        body = _strip_heading(doc.page_content, heading)
        if body and body not in seen:
            seen.add(body)
            bodies.append(body)
    text = "\n\n".join(bodies) if bodies else _strip_heading(best.page_content, heading)
    text = _clip(text)
    source = best.metadata.get("source", "documento")
    title = heading or source
    q_tokens = set(significant_tokens(question))
    b_tokens = set(significant_tokens(text))
    if heading and set(significant_tokens(heading)) & q_tokens:
        return _format_answer(title, text, source)
    if len(q_tokens & b_tokens) == 0:
        return "Nao tenho informacao sobre isso."
    return _format_answer(title, text, source)


def generate_answer(question: str, chunks: list[Document]) -> str:
    prompt = build_prompt(question, chunks)
    if USER_LLM_API_KEY:
        try:
            import httpx

            url = USER_LLM_BASE_URL.rstrip("/") + "/chat/completions"
            payload = {
                "model": USER_LLM_MODEL,
                "temperature": LLM_TEMPERATURE,
                "max_tokens": LLM_MAX_TOKENS,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            }
            headers = {"Authorization": f"Bearer {USER_LLM_API_KEY}"}
            with httpx.Client(timeout=45.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
    return _extractive_answer(question, chunks)
