from pathlib import Path

from app.rag.embeddings import embed_query, embed_texts
from app.rag.loader import Document, load_txt
from app.rag.pipeline import RAGPipeline
from app.rag.vectorstore import VectorStore


def test_load_txt(tmp_path: Path):
    path = tmp_path / "politica.txt"
    path.write_text("Refund em 30 dias apos a compra.", encoding="utf-8")
    docs = load_txt(path)
    assert len(docs) == 1
    assert "Refund" in docs[0].page_content
    assert docs[0].metadata["source"] == "politica.txt"


def test_vector_search(tmp_path: Path):
    store = VectorStore(index_dir=tmp_path)
    docs = [
        Document("Refund e permitido em 30 dias.", {"source": "politica.txt", "page": 1, "heading": "Refund"}),
        Document("Horario de funcionamento e 9h as 18h.", {"source": "horario.txt", "page": 1, "heading": "Horario"}),
    ]
    embeddings = embed_texts([d.page_content for d in docs])
    store.add(embeddings, docs)
    query = embed_query("Qual o prazo de refund?")
    hits = store.similarity_search(query, k=1)
    assert hits
    assert "Refund" in hits[0][0].page_content


def test_pipeline_query(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "politica.txt").write_text(
        "Politica de Refund. Refund e permitido em 30 dias. Produto deve estar novo.",
        encoding="utf-8",
    )
    pipeline = RAGPipeline()
    pipeline.store = VectorStore(index_dir=tmp_path / "index")
    pipeline.ingest_directory(docs_dir)
    result = pipeline.query("Posso devolver um produto?")
    assert result["answer"]
    assert result["sources"]
    assert 0 <= result["confidence"] <= 1
