"""Daily EOD prices via yfinance.

yfinance scrapes Yahoo Finance and is fine for a portfolio project but
not production-grade (unofficial API, occasional gaps). Documented in
docs/data-quality.md; the interface here is small enough to swap the
vendor later.
"""

import math
from datetime import date
from typing import Any

import yfinance as yf


def fetch_daily_prices(ticker: str, period: str = "2y") -> list[dict[str, Any]]:
    """Return one record per trading day, ready for DB upsert."""
    history = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    records = []
    for index, row in history.iterrows():
        close = _clean(row.get("Close"))
        if close is None:
            continue  # skip empty vendor rows
        records.append(
            {
                "date": date(index.year, index.month, index.day),
                "open": _clean(row.get("Open")),
                "high": _clean(row.get("High")),
                "low": _clean(row.get("Low")),
                "close": close,
                "adj_close": _clean(row.get("Adj Close")),
                "volume": int(row["Volume"]) if not _is_nan(row.get("Volume")) else None,
            }
        )
    return records


def _is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _clean(value: Any) -> float | None:
    return None if _is_nan(value) else round(float(value), 4)
