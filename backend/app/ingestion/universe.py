"""The MVP ticker universe: ~30 US large caps.

Deliberately small so data quality stays manageable. Class-share tickers
like BRK-B are excluded for now because ticker formats differ between
EDGAR ("BRK-B") and market data vendors ("BRK.B" / "BRK-B") — see
docs/data-quality.md.
"""

UNIVERSE: list[str] = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AVGO",
    "ORCL",
    "CRM",
    "ADBE",
    "CSCO",
    "NFLX",
    "JPM",
    "BAC",
    "V",
    "MA",
    "GS",
    "UNH",
    "JNJ",
    "LLY",
    "MRK",
    "ABBV",
    "PFE",
    "XOM",
    "CVX",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "COST",
    "HD",
    "MCD",
    "DIS",
    "CAT",
]
