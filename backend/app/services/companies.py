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


async def get_screener(session: AsyncSession) -> list[dict]:
    """One row per company: latest close + latest fiscal-year fundamentals.

    Uses Postgres DISTINCT ON subqueries so the whole screener is a
    single round trip instead of N-per-company requests from the UI.
    """

    def _latest_fy(metric: str):
        return (
            select(
                Fundamental.company_id,
                Fundamental.value,
                Fundamental.fiscal_year,
            )
            .where(Fundamental.metric == metric, Fundamental.fiscal_period == "FY")
            .distinct(Fundamental.company_id)
            .order_by(Fundamental.company_id, Fundamental.fiscal_year.desc())
            .subquery()
        )

    price = (
        select(PriceDaily.company_id, PriceDaily.close, PriceDaily.date)
        .distinct(PriceDaily.company_id)
        .order_by(PriceDaily.company_id, PriceDaily.date.desc())
        .subquery()
    )
    revenue = _latest_fy("revenue")
    net_income = _latest_fy("net_income")

    query = (
        select(
            Company.ticker,
            Company.name,
            price.c.close,
            price.c.date,
            revenue.c.value.label("revenue"),
            revenue.c.fiscal_year,
            net_income.c.value.label("net_income"),
        )
        .outerjoin(price, price.c.company_id == Company.id)
        .outerjoin(revenue, revenue.c.company_id == Company.id)
        .outerjoin(net_income, net_income.c.company_id == Company.id)
        .order_by(Company.ticker)
    )
    result = await session.execute(query)
    rows = []
    for ticker, name, close, date_, rev, fy, ni in result.all():
        margin = float(ni) / float(rev) if rev and ni else None
        rows.append(
            {
                "ticker": ticker,
                "name": name,
                "last_close": float(close) if close is not None else None,
                "last_close_date": date_.isoformat() if date_ else None,
                "revenue": float(rev) if rev is not None else None,
                "net_income": float(ni) if ni is not None else None,
                "net_margin": margin,
                "fiscal_year": fy,
            }
        )
    return rows


async def get_filings(session: AsyncSession, company_id: int) -> list[Filing]:
    result = await session.execute(
        select(Filing)
        .where(Filing.company_id == company_id)
        .order_by(Filing.filing_date.desc())
    )
    return list(result.scalars())
