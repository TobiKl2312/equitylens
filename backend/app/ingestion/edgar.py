"""Client for SEC EDGAR's free JSON APIs.

EDGAR requires a descriptive User-Agent with contact info and allows at
most 10 requests/second; we stay well below that with a fixed delay.
"""

import time
from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{document}"

REQUEST_DELAY_SECONDS = 0.15

RESEARCH_FORMS = ("10-K", "10-Q")


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.TransportError)


class EdgarClient:
    def __init__(self, user_agent: str):
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=30.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _get_json(self, url: str) -> Any:
        time.sleep(REQUEST_DELAY_SECONDS)
        response = self._client.get(url)
        response.raise_for_status()
        return response.json()

    def fetch_company_tickers(self) -> dict[str, dict]:
        """Map ticker -> {cik, name} for all EDGAR-registered companies."""
        raw = self._get_json(COMPANY_TICKERS_URL)
        return {
            entry["ticker"]: {"cik": entry["cik_str"], "name": entry["title"]}
            for entry in raw.values()
        }

    def fetch_submissions(self, cik: int) -> dict:
        return self._get_json(SUBMISSIONS_URL.format(cik=cik))

    def fetch_company_facts(self, cik: int) -> dict:
        return self._get_json(COMPANY_FACTS_URL.format(cik=cik))


def extract_filings(
    submissions: dict,
    forms: tuple[str, ...] = RESEARCH_FORMS,
    since: date | None = None,
) -> list[dict]:
    """Flatten EDGAR's columnar `submissions` payload into filing records.

    Pure function so it is unit-testable against a fixture without network.
    """
    recent = submissions.get("filings", {}).get("recent", {})
    cik = int(submissions["cik"])
    filings = []
    for i, form in enumerate(recent.get("form", [])):
        if form not in forms:
            continue
        filing_date = date.fromisoformat(recent["filingDate"][i])
        if since and filing_date < since:
            continue
        accession = recent["accessionNumber"][i]
        document = recent["primaryDocument"][i]
        report_date = recent["reportDate"][i] or None
        filings.append(
            {
                "form_type": form,
                "filing_date": filing_date,
                "period_end": date.fromisoformat(report_date) if report_date else None,
                "accession_no": accession,
                "primary_document": document,
                "source_url": FILING_URL.format(
                    cik=cik,
                    accession_nodash=accession.replace("-", ""),
                    document=document,
                ),
            }
        )
    return filings
