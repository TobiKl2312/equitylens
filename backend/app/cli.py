"""Ingestion & RAG CLI.

Usage (from backend/):
    uv run python -m app.cli seed
    uv run python -m app.cli filings
    uv run python -m app.cli fundamentals
    uv run python -m app.cli prices
    uv run python -m app.cli all              # all four above
    uv run python -m app.cli process-filings  # parse -> chunk -> embed
    uv run python -m app.cli refresh          # smart update: only if new filings
    uv run python -m app.cli eval             # retrieval hit rate on golden set
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.ingestion.edgar import EdgarClient
from app.services import ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

GOLDEN_QUESTIONS = Path(__file__).parent.parent / "tests" / "eval" / "golden_questions.json"


async def run(command: str) -> None:
    edgar = EdgarClient(user_agent=get_settings().edgar_user_agent)
    try:
        async with SessionLocal() as session:
            if command in ("seed", "all"):
                await ingestion.seed_universe(session, edgar)
            if command in ("filings", "all"):
                await ingestion.ingest_filings(session, edgar)
            if command in ("fundamentals", "all"):
                await ingestion.ingest_fundamentals(session, edgar)
            if command in ("prices", "all"):
                await ingestion.ingest_prices(session)
            if command == "process-filings":
                await _process_filings(session, edgar)
            if command == "refresh":
                await _refresh(session, edgar)
            if command == "eval":
                await _run_eval(session)
    finally:
        edgar.close()


async def _process_filings(session, edgar) -> None:
    from app.rag.embeddings import VoyageClient
    from app.services import rag

    voyage = VoyageClient(api_key=get_settings().voyage_api_key)
    try:
        total = await rag.process_all_filings(session, edgar, voyage)
        logging.info("Processed filings into %d chunks", total)
    finally:
        voyage.close()


async def _refresh(session, edgar) -> None:
    """Check EDGAR for new filings; only if found, pull fundamentals and embed.

    Cheap when nothing changed (one metadata pass), so it is safe to run
    on a schedule — the desktop launcher calls this weekly.
    """
    from sqlalchemy import func, select

    from app.models import Filing

    before = (await session.execute(select(func.count(Filing.id)))).scalar_one()
    await ingestion.ingest_filings(session, edgar)
    after = (await session.execute(select(func.count(Filing.id)))).scalar_one()
    new_filings = after - before

    if new_filings == 0:
        logging.info("REFRESH: no new filings — data is current")
        return

    logging.info(
        "REFRESH: %d new filing(s) — updating fundamentals and embeddings", new_filings
    )
    await ingestion.ingest_fundamentals(session, edgar)
    await _process_filings(session, edgar)
    logging.info("REFRESH: done")


async def _run_eval(session) -> None:
    """Retrieval eval: does the top-k contain a chunk from the expected section?"""
    from sqlalchemy import select

    from app.models import Company
    from app.rag.embeddings import VoyageClient
    from app.rag.retrieval import retrieve

    questions = json.loads(GOLDEN_QUESTIONS.read_text())
    voyage = VoyageClient(api_key=get_settings().voyage_api_key)
    hits = 0
    try:
        for item in questions:
            result = await session.execute(
                select(Company).where(Company.ticker == item["ticker"])
            )
            company = result.scalar_one()
            embedding = voyage.embed_query(item["question"])
            chunks = await retrieve(session, embedding, company.id)
            sections = " | ".join((chunk.section or "").lower() for chunk in chunks)
            hit = any(expected.lower() in sections for expected in item["expected_sections"])
            hits += hit
            print(f"{'HIT ' if hit else 'MISS'} {item['ticker']}: {item['question']}")
    finally:
        voyage.close()
    print(f"\nRetrieval hit rate: {hits}/{len(questions)} ({hits / len(questions):.0%})")


def main() -> None:
    parser = argparse.ArgumentParser(description="EquityLens data ingestion & RAG")
    parser.add_argument(
        "command",
        choices=[
            "seed",
            "filings",
            "fundamentals",
            "prices",
            "all",
            "process-filings",
            "refresh",
            "eval",
        ],
    )
    args = parser.parse_args()
    asyncio.run(run(args.command))


if __name__ == "__main__":
    main()
