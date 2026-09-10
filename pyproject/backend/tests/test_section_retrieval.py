from pathlib import Path

from app.rag.llm import generate_answer
from app.rag.loader import load_document
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import hybrid_search
from app.rag.splitter import split_documents
from app.rag.vectorstore import VectorStore

SAMPLE = Path(__file__).parent / "fixtures" / "U3_A3.docx"


def test_docx_sections_keep_explanation_heading():
    docs = load_document(SAMPLE)
    headings = [str(d.metadata.get("heading") or "") for d in docs]
    assert any("EXPLICA" in h.upper() for h in headings)
    assert any("CONCLUS" in h.upper() for h in headings)


def test_explanation_query_does_not_return_conclusion(tmp_path: Path):
    pipeline = RAGPipeline()
    pipeline.store = VectorStore(index_dir=tmp_path / "index")
    chunks = split_documents(load_document(SAMPLE))
    from app.rag.embeddings import embed_texts

    pipeline.store.add(embed_texts([c.page_content for c in chunks]), chunks)
    result = pipeline.query("EXPLICACAO DO FUNCIONAMENTO")
    answer = result["answer"].lower()
    assert "while" in answer or "sentinela" in answer
    assert "atividade pratica permitiu compreender" not in answer
    assert "conclusao" not in answer.split("fonte")[0].lower()[:40]


def test_hybrid_prefers_matching_heading(tmp_path: Path):
    store = VectorStore(index_dir=tmp_path)
    docs = split_documents(load_document(SAMPLE))
    from app.rag.embeddings import embed_texts

    store.add(embed_texts([d.page_content for d in docs]), docs)
    hits = hybrid_search(store, "explicacao do funcionamento", k=3)
    assert hits
    heading = str(hits[0][0].metadata.get("heading") or "").lower()
    assert "explica" in heading
    answer = generate_answer("explicacao do funcionamento", [doc for doc, _ in hits])
    assert "while (numero != 0)" in answer.lower() or "valor zero funciona como sentinela" in answer.lower()
