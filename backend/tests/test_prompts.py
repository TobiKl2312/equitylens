from app.llm.prompts import build_context, extract_citations


def test_extract_valid_citations():
    valid, invalid = extract_citations("Revenue grew 8% [1] driven by Services [2][3].", 5)
    assert valid == [1, 2, 3]
    assert invalid == []


def test_out_of_range_citations_flagged_as_invalid():
    valid, invalid = extract_citations("As stated [2], margins fell [9].", 3)
    assert valid == [2]
    assert invalid == [9]


def test_no_citations():
    valid, invalid = extract_citations("The excerpts do not contain this information.", 8)
    assert valid == []
    assert invalid == []


def test_build_context_numbers_sources():
    sources = [
        {
            "form_type": "10-K",
            "filing_date": "2025-11-01",
            "section": "Item 1A. Risk Factors",
            "content": "Supply chain risks...",
        },
        {
            "form_type": "10-Q",
            "filing_date": "2026-05-01",
            "section": None,
            "content": "Quarterly revenue...",
        },
    ]
    context = build_context(sources)
    assert "[1] 10-K filed 2025-11-01 — Item 1A. Risk Factors" in context
    assert "[2] 10-Q filed 2026-05-01 — unlabeled section" in context
    assert "Supply chain risks..." in context
