# Data quality

Financial data is messier than API docs suggest. This page documents the
known issues and how EquityLens handles them.

## XBRL fundamentals (SEC `companyfacts`)

**Concept drift.** Companies report the same economic quantity under
different us-gaap concepts (e.g. revenue as
`RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, or
`SalesRevenueNet`). We map each metric to an ordered candidate list and take
the first concept that has data (`app/ingestion/xbrl.py`).

**`fy`/`fp` labels describe the filing, not the fact.** Prior-year
comparatives inside a FY2025 10-K are labeled `fy=2025`, so trusting labels
alone shifts the whole history forward by up to two years (we hit exactly
this against live Apple data). Additionally, 10-Qs report both 3-month and
year-to-date durations under the same quarter label. Fix: reject facts whose
duration contradicts their label (~1 year for FY, ~1 quarter for Qn), and per
label keep the fact with the latest `period_end` — comparatives always have
older period ends than the filing's own period. Both covered by unit tests.

**Restatements.** The same (metric, fiscal period) appears in multiple
filings, including amended 10-K/A / 10-Q/A. We keep the fact with the latest
`filed` date, so restatements override originals. Covered by a unit test.

**Non-research forms.** `companyfacts` also contains facts from 8-Ks and
other forms; we only accept 10-K/10-Q (and their /A amendments) to keep the
data audited-report-grade.

**Fiscal vs. calendar periods.** Fiscal years don't align across companies
(Apple's FY ends in September). We store `fiscal_year`/`fiscal_period` as
reported plus the concrete `period_end` date; cross-company comparisons must
join on `period_end`, not fiscal labels.

## Prices (yfinance)

- yfinance is an **unofficial** Yahoo Finance client: fine for a portfolio
  project, not production-grade. The vendor interface in
  `app/ingestion/prices.py` is deliberately tiny so it can be swapped.
- We store both `close` and `adj_close`. Adjusted close accounts for splits
  and dividends and is what return calculations must use; raw close is kept
  for display alongside historical filings.
- Empty vendor rows (NaN close) are dropped at ingestion.

## Universe selection

- ~35 US large caps, hand-picked. This is a **survivorship-biased** sample by
  construction — acceptable for a research/RAG showcase, unusable for
  backtesting. Documented so nobody mistakes it for a tradable universe.
- Class-share tickers (BRK.B, GOOG vs GOOGL) have inconsistent formats across
  vendors (EDGAR uses `BRK-B`, some vendors `BRK.B`). We avoid them in the
  MVP universe rather than special-casing.

## Rate limits

- **SEC EDGAR:** max 10 req/s, descriptive User-Agent with contact info
  required. The client enforces a fixed inter-request delay plus exponential
  backoff on 429/5xx (`app/ingestion/edgar.py`).
- All ingestion is idempotent, so a job interrupted by throttling is simply
  re-run.
