from app.ai.embeddings.chunking import chunk_text


def test_chunk_text_keeps_short_text_whole():
    assert chunk_text("one two three") == ["one two three"]


def test_chunk_text_splits_long_text():
    chunks = chunk_text("a" * 1200, chunk_size=500, overlap=50)
    assert len(chunks) == 3
    assert all(chunks)
