from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    open: Mapped[float | None] = mapped_column(Numeric(18, 4))
    high: Mapped[float | None] = mapped_column(Numeric(18, 4))
    low: Mapped[float | None] = mapped_column(Numeric(18, 4))
    close: Mapped[float | None] = mapped_column(Numeric(18, 4))
    adj_close: Mapped[float | None] = mapped_column(Numeric(18, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)


class Fundamental(Base):
    """XBRL facts in long/narrow form: one row per (company, metric, period).

    Metric names vary per company in XBRL, so wide columns don't work.
    """

    __tablename__ = "fundamentals"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "metric", "fiscal_year", "fiscal_period", name="uq_fundamental_fact"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    metric: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Numeric(24, 4))
    unit: Mapped[str] = mapped_column(String(20))
    fiscal_year: Mapped[int]
    fiscal_period: Mapped[str] = mapped_column(String(4))  # FY, Q1..Q4
    period_end: Mapped[date] = mapped_column(Date)
    form: Mapped[str] = mapped_column(String(10))  # 10-K / 10-Q
    accession_no: Mapped[str | None] = mapped_column(String(25))
