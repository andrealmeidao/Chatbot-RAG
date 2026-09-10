from app.rag.splitter import split_text


def test_split_short_text():
    chunks = split_text("Refund em 30 dias")
    assert chunks == ["Refund em 30 dias"]


def test_split_long_text_overlap():
    text = "a" * 1200
    chunks = split_text(text, chunk_size=500, overlap=100)
    assert len(chunks) >= 3
    assert chunks[0][:10] == "aaaaaaaaaa"
