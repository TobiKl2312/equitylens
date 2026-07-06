from app.rag.retrieval import RetrievedChunk
from app.services.report import _context_for, _renumber


def _chunk(chunk_id: int, content: str = "text") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        filing_id=1,
        section="Item 1A. Risk Factors",
        content=content,
        form_type="10-K",
        filing_date="2026-02-25",
        source_url="https://example.com",
        distance=0.4,
    )


def test_renumber_appends_only_new_chunks():
    existing = [_chunk(1), _chunk(2)]
    merged = _renumber(existing, [_chunk(2), _chunk(3)])
    assert [chunk.chunk_id for chunk in merged] == [1, 2, 3]


def test_context_uses_global_numbers():
    sources = [_chunk(10, "alpha"), _chunk(20, "beta"), _chunk(30, "gamma")]
    # A later section retrieves only chunk 30 — it must render as [3],
    # not restart at [1], so citations stay unique across sections.
    context = _context_for(sources, [sources[2]])
    assert context.startswith("[3] 10-K filed 2026-02-25")
    assert "gamma" in context


def test_context_renders_all_of_subset():
    sources = [_chunk(1, "alpha"), _chunk(2, "beta")]
    context = _context_for(sources, sources)
    assert "[1]" in context and "[2]" in context
