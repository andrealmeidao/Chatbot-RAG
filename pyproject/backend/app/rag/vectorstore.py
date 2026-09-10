import json
import pickle
from pathlib import Path

import numpy as np

from app.config import INDEX_DIR, TOP_K
from app.rag.loader import Document


class VectorStore:
    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or INDEX_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.vectors: np.ndarray | None = None
        self.documents: list[Document] = []
        self._faiss_index = None
        self.id_index: dict[str, list[int]] = {}
        self._load()

    def _index_path(self) -> Path:
        return self.index_dir / "faiss.index"

    def _docs_path(self) -> Path:
        return self.index_dir / "documents.pkl"

    def _meta_path(self) -> Path:
        return self.index_dir / "meta.json"

    def _try_faiss(self):
        try:
            import faiss

            return faiss
        except Exception:
            return None

    def _load(self) -> None:
        docs_path = self._docs_path()
        if not docs_path.exists():
            return
        with docs_path.open("rb") as handle:
            self.documents = pickle.load(handle)
        faiss = self._try_faiss()
        index_path = self._index_path()
        if faiss and index_path.exists():
            self._faiss_index = faiss.read_index(str(index_path))
        npy_path = self.index_dir / "vectors.npy"
        if npy_path.exists():
            self.vectors = np.load(npy_path)
        self._rebuild_id_index()

    def save(self) -> None:
        with self._docs_path().open("wb") as handle:
            pickle.dump(self.documents, handle)
        faiss = self._try_faiss()
        if faiss and self._faiss_index is not None:
            faiss.write_index(self._faiss_index, str(self._index_path()))
        if self.vectors is not None:
            np.save(self.index_dir / "vectors.npy", self.vectors)
        meta = {"chunks": len(self.documents), "sources": sorted({d.metadata.get("source", "") for d in self.documents})}
        self._meta_path().write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, embeddings: list[list[float]], documents: list[Document]) -> None:
        matrix = np.array(embeddings, dtype=np.float32)
        if self.vectors is None:
            self.vectors = matrix
        else:
            self.vectors = np.vstack([self.vectors, matrix])
        faiss = self._try_faiss()
        if faiss:
            if self._faiss_index is None:
                self._faiss_index = faiss.IndexFlatIP(matrix.shape[1])
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self._faiss_index.add(matrix / norms)
        self.documents.extend(documents)
        self._rebuild_id_index()
        self.save()

    def add_lookup(self, documents: list[Document]) -> None:
        self.documents.extend(documents)
        self._rebuild_id_index()
        self.save()

    def reset(self) -> None:
        self.vectors = None
        self.documents = []
        self._faiss_index = None
        self.id_index = {}
        for path in self.index_dir.glob("*"):
            if path.is_file():
                path.unlink()

    def remove_source(self, source: str) -> None:
        kept = [(i, doc) for i, doc in enumerate(self.documents) if doc.metadata.get("source") != source]
        if len(kept) == len(self.documents):
            return
        remaining_docs = [doc for _, doc in kept]
        if not remaining_docs:
            self.reset()
            return
        if self.vectors is not None:
            idxs = [i for i, _ in kept]
            self.vectors = self.vectors[idxs]
            self.documents = remaining_docs
            self._faiss_index = None
            faiss = self._try_faiss()
            if faiss:
                matrix = self.vectors.astype("float32")
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms[norms == 0] = 1
                self._faiss_index = faiss.IndexFlatIP(matrix.shape[1])
                self._faiss_index.add(matrix / norms)
            self._rebuild_id_index()
            self.save()
            return
        self.reset()
        self.documents = remaining_docs
        self._rebuild_id_index()
        self.save()

    def similarity_search(self, query_embedding: list[float], k: int = TOP_K) -> list[tuple[Document, float]]:
        if not self.documents:
            return []
        k = min(k, len(self.documents))
        query = np.array([query_embedding], dtype=np.float32)
        faiss = self._try_faiss()
        if faiss and self._faiss_index is not None:
            qnorm = np.linalg.norm(query, axis=1, keepdims=True)
            qnorm[qnorm == 0] = 1
            scores, indices = self._faiss_index.search(query / qnorm, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                results.append((self.documents[int(idx)], float(score)))
            return results
        if self.vectors is None:
            return []
        q = query[0]
        qn = np.linalg.norm(q)
        if qn == 0:
            return []
        vn = np.linalg.norm(self.vectors, axis=1)
        vn[vn == 0] = 1
        sims = (self.vectors @ q) / (vn * qn)
        top = np.argsort(sims)[::-1][:k]
        return [(self.documents[int(i)], float(sims[int(i)])) for i in top]

    def _normalize_id(self, value: str) -> str:
        text = str(value or "").strip().upper()
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]
        return text

    def _rebuild_id_index(self) -> None:
        index: dict[str, list[int]] = {}
        for i, doc in enumerate(self.documents):
            keys = {
                self._normalize_id(str(doc.metadata.get("record_id") or "")),
                self._normalize_id(str(doc.metadata.get("heading") or "")),
            }
            for key in keys:
                if not key:
                    continue
                index.setdefault(key, []).append(i)
        self.id_index = index

    def find_by_ids(self, values: list[str]) -> list[Document]:
        found: list[Document] = []
        seen: set[int] = set()
        for value in values:
            key = self._normalize_id(value)
            for idx in self.id_index.get(key, []):
                if idx in seen:
                    continue
                seen.add(idx)
                found.append(self.documents[idx])
        return found

    @property
    def chunk_count(self) -> int:
        return len(self.documents)

    @property
    def sources(self) -> list[str]:
        return sorted({d.metadata.get("source", "unknown") for d in self.documents})
