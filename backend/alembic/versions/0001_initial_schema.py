"""Initial schema: companies, prices, fundamentals, filings + chunks, research tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-06
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1024  # voyage-finance-2


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cik", sa.BigInteger, unique=True),
        sa.Column("sector", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("market_cap", sa.BigInteger),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "prices_daily",
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("date", sa.Date, primary_key=True, index=True),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("adj_close", sa.Numeric(18, 4)),
        sa.Column("volume", sa.BigInteger),
    )

    op.create_table(
        "fundamentals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("metric", sa.String(100), nullable=False, index=True),
        sa.Column("value", sa.Numeric(24, 4), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("fiscal_period", sa.String(4), nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("form", sa.String(10), nullable=False),
        sa.Column("accession_no", sa.String(25)),
        sa.UniqueConstraint(
            "company_id", "metric", "fiscal_year", "fiscal_period", name="uq_fundamental_fact"
        ),
    )

    op.create_table(
        "filings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("form_type", sa.String(10), nullable=False),
        sa.Column("filing_date", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date),
        sa.Column("accession_no", sa.String(25), nullable=False, unique=True),
        sa.Column("primary_document", sa.String(255)),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column(
            "ingest_status", sa.String(10), nullable=False, server_default="pending"
        ),
    )

    op.create_table(
        "filing_chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "filing_id",
            sa.Integer,
            sa.ForeignKey("filings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("section", sa.String(100)),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.UniqueConstraint("filing_id", "chunk_index", name="uq_filing_chunk"),
    )
    op.execute(
        "CREATE INDEX ix_filing_chunks_embedding ON filing_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("prompt_version", sa.String(20), nullable=False),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("citations", JSONB),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("retrieved_chunk_ids", JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.String(50), nullable=False, server_default="demo", index=True
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("note", sa.Text),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    for table in (
        "watchlist_items",
        "chat_messages",
        "chat_sessions",
        "reports",
        "filing_chunks",
        "filings",
        "fundamentals",
        "prices_daily",
        "companies",
    ):
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS vector")
