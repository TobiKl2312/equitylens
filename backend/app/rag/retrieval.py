"""Hybrid retrieval: pgvector cosine similarity + SQL metadata filters.

Because chunks and their metadata live in the same Postgres, filtering
by company/form/period and ranking by vector similarity is one query —
the main reason we chose pgvector over a separate vector store (ADR 0002).
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Filing, FilingChunk

DEFAULT_TOP_K = 8


@dataclass
class RetrievedChunk:
    chunk_id: int
    filing_id: int
    section: str | None
    content: str
    form_type: str
    filing_date: str
    source_url: str
    distance: float


async def retrieve(
    session: AsyncSession,
    query_embedding: list[float],
    company_id: int,
    form_type: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    distance = FilingChunk.embedding.cosine_distance(query_embedding)
    query = (
        select(FilingChunk, Filing, distance.label("distance"))
        .join(Filing, Filing.id == FilingChunk.filing_id)
        .where(Filing.company_id == company_id)
        .where(FilingChunk.embedding.is_not(None))
    )
    if form_type:
        query = query.where(Filing.form_type == form_type)
    query = query.order_by(distance).limit(top_k)

    result = await session.execute(query)
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            filing_id=filing.id,
            section=chunk.section,
            content=chunk.content,
            form_type=filing.form_type,
            filing_date=filing.filing_date.isoformat(),
            source_url=filing.source_url,
            distance=float(dist),
        )
        for chunk, filing, dist in result.all()
    ]
