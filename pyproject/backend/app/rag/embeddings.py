import hashlib

import numpy as np

from app.config import EMBEDDING_DIM, USER_EMBEDDING_MODEL, USER_LLM_API_KEY, USER_LLM_BASE_URL
from app.rag.textutils import significant_tokens

SYNONYMS = {
    "devolver": ["refund", "reembolso", "devolucao"],
    "devolucao": ["refund", "reembolso", "devolver"],
    "reembolso": ["refund", "devolver"],
    "refund": ["devolver", "reembolso", "prazo"],
    "prazo": ["dias", "refund"],
    "ferias": ["descanso", "beneficio"],
    "desconto": ["bulk", "preco"],
    "bulk": ["desconto", "quantidade"],
    "cancelamento": ["cancelar", "clausula"],
    "cancelar": ["cancelamento"],
    "horario": ["funcionamento", "atendimento"],
    "funcionamento": ["horario", "atendimento", "explicacao"],
    "explicacao": ["funcionamento", "como", "funciona"],
    "explicar": ["explicacao", "funcionamento"],
    "while": ["laco", "repeticao", "sentinela"],
    "sentinela": ["zero", "parada", "while"],
}


def expand_tokens(tokens: list[str]) -> list[str]:
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, []))
    return expanded


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    tokens = expand_tokens(significant_tokens(text))
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        vec[idx] += 1.0
        idx2 = int.from_bytes(digest[4:8], "little") % dim
        vec[idx2] += 0.45
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]}_{tokens[i + 1]}"
        digest = hashlib.md5(bigram.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        vec[idx] += 1.1
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec


def embed_texts(texts: list[str]) -> list[list[float]]:
    if USER_LLM_API_KEY:
        try:
            import httpx

            url = USER_LLM_BASE_URL.rstrip("/") + "/embeddings"
            payload = {"model": USER_EMBEDDING_MODEL, "input": texts}
            headers = {"Authorization": f"Bearer {USER_LLM_API_KEY}"}
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()["data"]
                return [item["embedding"] for item in data]
        except Exception:
            pass
    return [_hash_embedding(text).tolist() for text in texts]


def embed_matrix(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    return np.vstack([_hash_embedding(text) for text in texts])


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
