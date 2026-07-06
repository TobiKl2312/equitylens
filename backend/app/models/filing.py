from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

EMBEDDING_DIM = 1024  # voyage-finance-2

# Ingestion state machine: pending -> parsed -> chunked -> embedded | failed
INGEST_STATUSES = ("pending", "parsed", "chunked", "embedded", "failed")


class Filing(Base):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    form_type: Mapped[str] = mapped_column(String(10))  # 10-K / 10-Q
    filing_date: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    accession_no: Mapped[str] = mapped_column(String(25), unique=True)
    primary_document: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(500))
    ingest_status: Mapped[str] = mapped_column(String(10), default="pending")


class FilingChunk(Base):
    __tablename__ = "filing_chunks"
    __table_args__ = (UniqueConstraint("filing_id", "chunk_index", name="uq_filing_chunk"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    filing_id: Mapped[int] = mapped_column(
        ForeignKey("filings.id", ondelete="CASCADE"), index=True
    )
    section: Mapped[str | None] = mapped_column(String(100))  # e.g. "Item 1A. Risk Factors"
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
