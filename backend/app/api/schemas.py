from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    cik: int | None
    sector: str | None
    industry: str | None
    market_cap: int | None
    updated_at: datetime


class PriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: int | None


class FundamentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: str
    value: float
    unit: str
    fiscal_year: int
    fiscal_period: str
    period_end: date
    form: str


class FilingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    form_type: str
    filing_date: date
    period_end: date | None
    accession_no: str
    source_url: str
    ingest_status: str
