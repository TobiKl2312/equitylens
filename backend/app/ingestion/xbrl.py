"""Extract normalized fundamentals from EDGAR `companyfacts` XBRL payloads.

XBRL is messy: companies use different us-gaap concepts for the same
economic quantity, and facts are re-reported across filings (including
restatements). Two traps in particular:
- `fy`/`fp` describe the FILING, not the fact: prior-year comparatives in a
  FY2025 10-K are labeled fy=2025, so labels alone mislabel history
- 10-Qs report both 3-month and year-to-date durations under the same label

Strategy:
- map each metric to an ordered list of candidate concepts, first hit wins
- reject facts whose duration doesn't match their period label (~1 year for
  FY, ~1 quarter for Qn)
- per (metric, fiscal_year, fiscal_period) keep the fact with the latest
  period_end (drops comparatives), tie-broken by filing date (restatements win)
See docs/data-quality.md for the full discussion.
"""

from datetime import date
from typing import Any

# metric -> ordered candidate us-gaap concepts
METRIC_CONCEPTS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net_income": ["NetIncomeLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "stockholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "eps_diluted": ["EarningsPerShareDiluted"],
}

ACCEPTED_FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A")


def _duration_matches_label(fact: dict[str, Any], fiscal_period: str) -> bool:
    """Reject flow facts whose duration contradicts their fy/fp label."""
    start = fact.get("start")
    if start is None:
        return True  # instant fact (balance sheet item)
    days = (date.fromisoformat(fact["end"]) - date.fromisoformat(start)).days
    if fiscal_period == "FY":
        return days > 300
    return 60 <= days <= 120  # a single quarter, not a YTD span


def _facts_for_concept(companyfacts: dict, concept: str) -> list[dict[str, Any]]:
    concept_data = companyfacts.get("facts", {}).get("us-gaap", {}).get(concept)
    if not concept_data:
        return []
    units = concept_data.get("units", {})
    # USD for flows/balances, USD/shares for per-share metrics
    for unit_name in ("USD", "USD/shares"):
        if unit_name in units:
            return [{**fact, "_unit": unit_name} for fact in units[unit_name]]
    return []


def extract_fundamentals(companyfacts: dict) -> list[dict[str, Any]]:
    """Return normalized fact records ready for DB upsert."""
    records: dict[tuple[str, int, str], dict[str, Any]] = {}
    for metric, concepts in METRIC_CONCEPTS.items():
        facts: list[dict[str, Any]] = []
        for concept in concepts:
            facts = _facts_for_concept(companyfacts, concept)
            if facts:
                break
        for fact in facts:
            form = fact.get("form")
            fy = fact.get("fy")
            fp = fact.get("fp")
            if form not in ACCEPTED_FORMS or fy is None or fp is None:
                continue
            if not _duration_matches_label(fact, str(fp)):
                continue
            key = (metric, int(fy), str(fp))
            period_end = date.fromisoformat(fact["end"])
            filed = fact.get("filed", "")
            existing = records.get(key)
            # Latest period_end wins (prior-year comparatives carry the new
            # filing's label); on ties, the later-filed fact wins (restatements)
            if existing and (existing["period_end"], existing["_filed"]) >= (period_end, filed):
                continue
            records[key] = {
                "metric": metric,
                "value": fact["val"],
                "unit": fact["_unit"],
                "fiscal_year": int(fy),
                "fiscal_period": str(fp),
                "period_end": period_end,
                "form": form.removesuffix("/A"),
                "accession_no": fact.get("accn"),
                "_filed": filed,
            }
    for record in records.values():
        record.pop("_filed")
    return list(records.values())
