"""RAG pipeline: filing processing (parse -> chunk -> embed) and chat.

Filing processing walks the ingest_status state machine
(pending -> parsed -> chunked -> embedded | failed) so partially
processed filings are visible and each stage is resumable.
"""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.edgar import EdgarClient
from app.llm import prompts
from app.llm.client import CHAT_MODEL, stream_chat
from app.models import ChatMessage, ChatSession, Company, Filing, FilingChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import VoyageClient
from app.rag.parsing import html_to_text, split_sections
from app.rag.retrieval import retrieve

logger = logging.getLogger(__name__)

# Latest annual report + two most recent quarterlies per company keeps
# the corpus current while bounding embedding cost.
FILINGS_PER_COMPANY = {"10-K": 1, "10-Q": 2}


async def _filings_to_process(session: AsyncSession, company_id: int) -> list[Filing]:
    selected: list[Filing] = []
    for form_type, count in FILINGS_PER_COMPANY.items():
        result = await session.execute(
            select(Filing)
            .where(Filing.company_id == company_id)
            .where(Filing.form_type == form_type)
            .where(Filing.ingest_status != "embedded")
            .order_by(Filing.filing_date.desc())
            .limit(count)
        )
        selected.extend(result.scalars())
    return selected


async def process_filing(
    session: AsyncSession, edgar: EdgarClient, voyage: VoyageClient, filing: Filing
) -> int:
    """Run one filing through parse -> chunk -> embed. Returns chunk count."""
    # Snapshot attributes up front: after a rollback the ORM instance is
    # expired, and touching it would trigger sync IO inside async code
    # (sqlalchemy MissingGreenlet).
    filing_id = filing.id
    source_url = filing.source_url
    form_type = filing.form_type
    accession_no = filing.accession_no
    try:
        html = edgar.fetch_document(source_url)
        text = html_to_text(html)
        await _set_status(session, filing_id, "parsed")

        sections = split_sections(text, form_type=form_type)
        # Idempotent re-run: replace any chunks from a previous attempt
        await session.execute(delete(FilingChunk).where(FilingChunk.filing_id == filing_id))
        chunks: list[FilingChunk] = []
        index = 0
        for section in sections:
            for piece in chunk_text(section.text):
                chunks.append(
                    FilingChunk(
                        filing_id=filing_id,
                        section=section.name,
                        chunk_index=index,
                        content=piece.content,
                        token_count=piece.token_count,
                    )
                )
                index += 1
        session.add_all(chunks)
        await _set_status(session, filing_id, "chunked")

        vectors = voyage.embed_documents([chunk.content for chunk in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk.embedding = vector
        await _set_status(session, filing_id, "embedded")
        await session.commit()
        return len(chunks)
    except Exception:
        await session.rollback()
        await _set_status(session, filing_id, "failed")
        await session.commit()
        logger.exception("Failed to process filing %s", accession_no)
        return 0


async def _set_status(session: AsyncSession, filing_id: int, status: str) -> None:
    await session.execute(
        update(Filing).where(Filing.id == filing_id).values(ingest_status=status)
    )


async def process_all_filings(
    session: AsyncSession, edgar: EdgarClient, voyage: VoyageClient
) -> int:
    total_chunks = 0
    result = await session.execute(select(Company.id, Company.ticker).order_by(Company.ticker))
    for company_id, ticker in result.all():
        filings = await _filings_to_process(session, company_id)
        for filing in filings:
            # Snapshot before processing — see note in process_filing
            form_type, filing_date = filing.form_type, filing.filing_date
            count = await process_filing(session, edgar, voyage, filing)
            total_chunks += count
            logger.info("%s %s (%s): %d chunks", ticker, form_type, filing_date, count)
    return total_chunks


async def answer_question(
    session: AsyncSession,
    voyage: VoyageClient,
    company: Company,
    question: str,
    chat_session_id: int | None = None,
) -> AsyncIterator[str]:
    """Answer a question about a company, streamed as SSE-formatted events.

    Event order: `sources` (retrieved excerpts), `delta`* (answer text),
    `done` (session id + validated citations).
    """
    query_embedding = voyage.embed_query(question)
    retrieved = await retrieve(session, query_embedding, company.id)
    sources = [asdict(chunk) for chunk in retrieved]

    if chat_session_id is None:
        chat = ChatSession(company_id=company.id)
        session.add(chat)
        await session.flush()
        chat_session_id = chat.id
    session.add(ChatMessage(session_id=chat_session_id, role="user", content=question))
    await session.commit()

    yield _sse("sources", {"session_id": chat_session_id, "sources": sources})

    context = prompts.build_context(sources)
    user_message = (
        f"Company: {company.name} ({company.ticker})\n\n"
        f"Source excerpts:\n\n{context}\n\n"
        f"Question: {question}"
    )

    answer_parts: list[str] = []
    async for text in stream_chat(prompts.CHAT_SYSTEM, user_message):
        answer_parts.append(text)
        yield _sse("delta", {"text": text})

    answer = "".join(answer_parts)
    valid, invalid = prompts.extract_citations(answer, len(sources))
    session.add(
        ChatMessage(
            session_id=chat_session_id,
            role="assistant",
            content=answer,
            retrieved_chunk_ids=[chunk.chunk_id for chunk in retrieved],
        )
    )
    await session.commit()

    yield _sse(
        "done",
        {
            "session_id": chat_session_id,
            "model": CHAT_MODEL,
            "prompt_version": prompts.CHAT_PROMPT_VERSION,
            "citations": valid,
            "invalid_citations": invalid,
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
