from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Filing, Fundamental, PriceDaily


async def list_companies(session: AsyncSession) -> list[Company]:
    result = await session.execute(select(Company).order_by(Company.ticker))
    return list(result.scalars())


async def get_company(session: AsyncSession, ticker: str) -> Company | None:
    result = await session.execute(select(Company).where(Company.ticker == ticker.upper()))
    return result.scalar_one_or_none()


async def get_prices(
    session: AsyncSession,
    company_id: int,
    start: date | None = None,
    end: date | None = None,
) -> list[PriceDaily]:
    query = select(PriceDaily).where(PriceDaily.company_id == company_id)
    if start:
        query = query.where(PriceDaily.date >= start)
    if end:
        query = query.where(PriceDaily.date <= end)
    result = await session.execute(query.order_by(PriceDaily.date))
    return list(result.scalars())


async def get_fundamentals(
    session: AsyncSession, company_id: int, metric: str | None = None
) -> list[Fundamental]:
    query = select(Fundamental).where(Fundamental.company_id == company_id)
    if metric:
        query = query.where(Fundamental.metric == metric)
    result = await session.execute(
        query.order_by(Fundamental.metric, Fundamental.period_end)
    )
    return list(result.scalars())


async def get_filings(session: AsyncSession, company_id: int) -> list[Filing]:
    result = await session.execute(
        select(Filing)
        .where(Filing.company_id == company_id)
        .order_by(Filing.filing_date.desc())
    )
    return list(result.scalars())
