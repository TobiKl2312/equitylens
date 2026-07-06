"""Ingestion CLI.

Usage (from backend/):
    uv run python -m app.cli seed
    uv run python -m app.cli filings
    uv run python -m app.cli fundamentals
    uv run python -m app.cli prices
    uv run python -m app.cli all
"""

import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.ingestion.edgar import EdgarClient
from app.services import ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


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
    finally:
        edgar.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="EquityLens data ingestion")
    parser.add_argument(
        "command", choices=["seed", "filings", "fundamentals", "prices", "all"]
    )
    args = parser.parse_args()
    asyncio.run(run(args.command))


if __name__ == "__main__":
    main()
