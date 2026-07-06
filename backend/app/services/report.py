"""Multi-stage AI research report generation.

Design decisions (see docs/rag-design.md):
- Structured financials come FROM THE DATABASE (XBRL), never from the
  LLM — numbers are injected as a table, not recalled from memory.
- Each section runs targeted retrieval and its own generation call;
  the Bull & Bear section synthesizes from all sources gathered so far.
- Model tiering: Haiku formats the financial highlights (cheap
  extraction), Sonnet writes the analytical sections.
- Source numbering is global across sections so citations stay unique;
  the full citation map is persisted with the report for auditability.
"""

import json
import logging
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import prompts
from app.llm.client import CHAT_MODEL, complete_fast, stream_chat
from app.models import Company, Fundamental, Report
from app.rag.embeddings import VoyageClient
from app.rag.retrieval import RetrievedChunk, retrieve

logger = logging.getLogger(__name__)

SOURCES_PER_SECTION = 6
FINANCIAL_YEARS = 4


async def build_financial_table(session: AsyncSession, company_id: int) -> str:
    """Markdown table of the last fiscal years, straight from XBRL data."""
    result = await session.execute(
        select(Fundamental.metric, Fundamental.fiscal_year, Fundamental.value)
        .where(
            Fundamental.company_id == company_id,
            Fundamental.fiscal_period == "FY",
            Fundamental.metric.in_(["revenue", "net_income", "operating_income"]),
        )
        .order_by(Fundamental.fiscal_year)
    )
    by_year: dict[int, dict[str, float]] = {}
    for metric, year, value in result.all():
        by_year.setdefault(year, {})[metric] = float(value)

    years = sorted(by_year)[-FINANCIAL_YEARS:]
    if not years:
        return "No structured financial data available."

    def row(label: str, metric: str) -> str:
        cells = []
        for year in years:
            value = by_year[year].get(metric)
            cells.append(f"{value / 1e9:,.1f}" if value is not None else "–")
        return f"| {label} | " + " | ".join(cells) + " |"

    header = "| $B | " + " | ".join(f"FY{year}" for year in years) + " |"
    divider = "|---" * (len(years) + 1) + "|"
    lines = [
        header,
        divider,
        row("Revenue", "revenue"),
        row("Operating income", "operating_income"),
        row("Net income", "net_income"),
    ]
    return "\n".join(lines)


def _renumber(
    existing: list[RetrievedChunk], new: list[RetrievedChunk]
) -> list[RetrievedChunk]:
    """Append newly retrieved chunks, skipping ones already collected."""
    seen = {chunk.chunk_id for chunk in existing}
    return existing + [chunk for chunk in new if chunk.chunk_id not in seen]


def _context_for(sources: list[RetrievedChunk], subset: list[RetrievedChunk]) -> str:
    """Render `subset` excerpts with their GLOBAL numbers from `sources`."""
    position = {chunk.chunk_id: index + 1 for index, chunk in enumerate(sources)}
    blocks = []
    for chunk in subset:
        number = position[chunk.chunk_id]
        header = (
            f"[{number}] {chunk.form_type} filed {chunk.filing_date}"
            f" — {chunk.section or 'unlabeled section'}"
        )
        blocks.append(f"{header}\n{chunk.content}")
    return "\n\n---\n\n".join(blocks)


async def generate_report(
    session: AsyncSession, voyage: VoyageClient, company: Company
) -> AsyncIterator[str]:
    """Generate a report, streamed as SSE events.

    Event order: `status`* (stage names), `delta`* (markdown text),
    `sources` (global citation list), `done` (report id).
    """
    company_id, ticker, name = company.id, company.ticker, company.name

    yield _sse("status", {"stage": "Financial data"})
    table = await build_financial_table(session, company_id)
    highlights = await complete_fast(
        prompts.FINANCIAL_SUMMARY_SYSTEM, f"Company: {name}\n\n{table}"
    )

    parts: list[str] = [f"## Financial snapshot\n\n{table}\n\n{highlights}\n"]
    yield _sse("delta", {"text": parts[0]})

    sources: list[RetrievedChunk] = []
    for title, query, instruction in prompts.REPORT_SECTIONS:
        yield _sse("status", {"stage": title})
        if query:
            embedding = voyage.embed_query(f"{name}: {query}")
            retrieved = await retrieve(
                session, embedding, company_id, top_k=SOURCES_PER_SECTION
            )
            sources = _renumber(sources, retrieved)
            subset = retrieved
        else:
            subset = sources  # synthesis section sees everything gathered

        context = _context_for(sources, subset)
        user_message = (
            f"Company: {name} ({ticker})\n\n"
            f"Financial data table (from SEC XBRL):\n{table}\n\n"
            f"Source excerpts:\n\n{context}\n\n"
            f"Section to write: {title}\n{instruction}"
        )

        heading = f"\n## {title}\n\n"
        parts.append(heading)
        yield _sse("delta", {"text": heading})
        async for text in stream_chat(prompts.REPORT_SYSTEM, user_message):
            parts.append(text)
            yield _sse("delta", {"text": text})
        parts.append("\n")
        yield _sse("delta", {"text": "\n"})

    content = "".join(parts)
    valid, invalid = prompts.extract_citations(content, len(sources))
    citations = [
        {
            "number": index + 1,
            "chunk_id": chunk.chunk_id,
            "form_type": chunk.form_type,
            "filing_date": chunk.filing_date,
            "section": chunk.section,
            "source_url": chunk.source_url,
            "content": chunk.content,
        }
        for index, chunk in enumerate(sources)
    ]

    report = Report(
        company_id=company_id,
        model=CHAT_MODEL,
        prompt_version=prompts.REPORT_PROMPT_VERSION,
        content_md=content,
        citations={"sources": citations, "cited": valid, "invalid": invalid},
    )
    session.add(report)
    await session.commit()

    yield _sse("sources", {"sources": citations})
    yield _sse(
        "done",
        {
            "report_id": report.id,
            "model": CHAT_MODEL,
            "prompt_version": prompts.REPORT_PROMPT_VERSION,
            "citations": valid,
            "invalid_citations": invalid,
        },
    )


async def get_latest_report(session: AsyncSession, company_id: int) -> Report | None:
    result = await session.execute(
        select(Report)
        .where(Report.company_id == company_id)
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    return result.scalars().first()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
