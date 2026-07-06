from app.rag.chunking import (
    CHARS_PER_TOKEN,
    OVERLAP_TOKENS,
    TARGET_TOKENS,
    chunk_text,
)


def test_short_text_is_single_chunk():
    chunks = chunk_text("Revenue grew 12% year over year.")
    assert len(chunks) == 1
    assert chunks[0].content == "Revenue grew 12% year over year."


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_long_text_respects_target_size():
    paragraphs = "\n\n".join(f"Paragraph {i}. " + "Filler sentence. " * 40 for i in range(60))
    chunks = chunk_text(paragraphs)
    assert len(chunks) > 1
    limit = TARGET_TOKENS * CHARS_PER_TOKEN
    assert all(len(chunk.content) <= limit for chunk in chunks)


def test_chunks_overlap():
    text = "\n\n".join(f"Paragraph {i}. " + "Filler sentence. " * 40 for i in range(60))
    chunks = chunk_text(text)
    # The tail of chunk N must reappear at the head of chunk N+1
    overlap_chars = OVERLAP_TOKENS * CHARS_PER_TOKEN
    probe = chunks[0].content[-40:]
    assert probe in chunks[1].content[: overlap_chars + 100]


def test_no_content_is_lost():
    text = "\n\n".join(f"UNIQUE_MARKER_{i} " + "filler " * 100 for i in range(30))
    combined = " ".join(chunk.content for chunk in chunk_text(text))
    for i in range(30):
        assert f"UNIQUE_MARKER_{i}" in combined
