"""Orchestrates ingestion: fetch from vendors, upsert into Postgres.

All upserts are idempotent (ON CONFLICT DO UPDATE), so every job can be
re-run safely — the recovery story for partial failures is simply
"run it again".
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion import prices as price_ingestion
from app.ingestion.edgar import EdgarClient, extract_filings
from app.ingestion.universe import UNIVERSE
from app.ingestion.xbrl import extract_fundamentals
from app.models import Company, Filing, Fundamental, PriceDaily

logger = logging.getLogger(__name__)

FILINGS_SINCE = date(2022, 1, 1)


async def seed_universe(session: AsyncSession, edgar: EdgarClient) -> int:
    """Create/refresh the Company rows for the MVP universe."""
    edgar_tickers = edgar.fetch_company_tickers()
    count = 0
    for ticker in UNIVERSE:
        entry = edgar_tickers.get(ticker)
        if entry is None:
            logger.warning("Ticker %s not found on EDGAR, skipping", ticker)
            continue
        statement = (
            insert(Company)
            .values(ticker=ticker, name=entry["name"], cik=entry["cik"])
            .on_conflict_do_update(
                index_elements=["ticker"],
                set_={"name": entry["name"], "cik": entry["cik"]},
            )
        )
        await session.execute(statement)
        count += 1
    await session.commit()
    logger.info("Seeded %d companies", count)
    return count


async def _companies_with_cik(session: AsyncSession) -> list[Company]:
    result = await session.execute(select(Company).where(Company.cik.is_not(None)))
    return list(result.scalars())


async def ingest_filings(session: AsyncSession, edgar: EdgarClient) -> int:
    """Store 10-K/10-Q metadata; full-text parsing happens in week 2."""
    total = 0
    for company in await _companies_with_cik(session):
        submissions = edgar.fetch_submissions(company.cik)
        filings = extract_filings(submissions, since=FILINGS_SINCE)
        for filing in filings:
            statement = (
                insert(Filing)
                .values(company_id=company.id, **filing)
                .on_conflict_do_nothing(index_elements=["accession_no"])
            )
            await session.execute(statement)
        total += len(filings)
        logger.info("%s: %d filings", company.ticker, len(filings))
    await session.commit()
    return total


async def ingest_fundamentals(session: AsyncSession, edgar: EdgarClient) -> int:
    total = 0
    for company in await _companies_with_cik(session):
        companyfacts = edgar.fetch_company_facts(company.cik)
        records = extract_fundamentals(companyfacts)
        for record in records:
            statement = (
                insert(Fundamental)
                .values(company_id=company.id, **record)
                .on_conflict_do_update(
                    constraint="uq_fundamental_fact",
                    set_={
                        "value": record["value"],
                        "period_end": record["period_end"],
                        "form": record["form"],
                        "accession_no": record["accession_no"],
                    },
                )
            )
            await session.execute(statement)
        total += len(records)
        logger.info("%s: %d fundamental facts", company.ticker, len(records))
    await session.commit()
    return total


async def ingest_prices(session: AsyncSession) -> int:
    total = 0
    result = await session.execute(select(Company))
    for company in result.scalars():
        records = price_ingestion.fetch_daily_prices(company.ticker)
        for record in records:
            statement = (
                insert(PriceDaily)
                .values(company_id=company.id, **record)
                .on_conflict_do_update(
                    index_elements=["company_id", "date"],
                    set_={key: value for key, value in record.items() if key != "date"},
                )
            )
            await session.execute(statement)
        total += len(records)
        logger.info("%s: %d price rows", company.ticker, len(records))
    await session.commit()
    return total
