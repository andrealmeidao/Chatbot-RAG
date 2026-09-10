from pathlib import Path

from app.rag.embeddings import embed_texts
from app.rag.loader import load_document
from app.rag.pipeline import RAGPipeline
from app.rag.splitter import split_documents
from app.rag.vectorstore import VectorStore

CSV = Path(__file__).parent / "fixtures" / "produtos-1.csv"


def test_csv_indexes_one_row_per_product():
    docs = load_document(CSV)
    assert len(docs) > 20
    ids = {str(d.metadata.get("record_id")) for d in docs}
    assert "TETO0008014" in ids
    target = next(d for d in docs if d.metadata.get("record_id") == "TETO0008014")
    assert "Toshiba" in target.page_content
    assert "TESA000747" not in target.page_content


def test_sku_query_returns_only_requested_product(tmp_path: Path):
    pipeline = RAGPipeline()
    pipeline.store = VectorStore(index_dir=tmp_path / "index")
    chunks = split_documents(load_document(CSV))
    pipeline.store.add(embed_texts([c.page_content for c in chunks]), chunks)
    result = pipeline.query("TETO0008014")
    answer = result["answer"]
    assert "TETO0008014" in answer
    assert "Toshiba" in answer
    assert "TESA000747" not in answer
    assert "TESE0005016" not in answer


def test_question_number_returns_only_that_item(tmp_path: Path):
    path = tmp_path / "quiz.txt"
    path.write_text(
        "Pergunta 9\nQual e a capital da Alemanha? Resposta: Berlim.\n"
        "Pergunta 10\nQual e a capital da Franca? Resposta: Paris.\n"
        "Pergunta 11\nQual e a capital da Italia? Resposta: Roma.\n",
        encoding="utf-8",
    )
    pipeline = RAGPipeline()
    pipeline.store = VectorStore(index_dir=tmp_path / "index")
    chunks = split_documents(load_document(path))
    pipeline.store.add(embed_texts([c.page_content for c in chunks]), chunks)
    result = pipeline.query("pergunta 10")
    answer = result["answer"].lower()
    assert "paris" in answer
    assert "berlim" not in answer
    assert "roma" not in answer
