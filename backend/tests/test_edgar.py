from datetime import date

from app.ingestion.edgar import extract_filings


def test_filters_to_research_forms(submissions):
    filings = extract_filings(submissions)
    assert {f["form_type"] for f in filings} == {"10-K", "10-Q"}
    # The 8-K must be excluded
    assert all(f["accession_no"] != "0000320193-23-000105" for f in filings)


def test_since_cutoff(submissions):
    filings = extract_filings(submissions, since=date(2022, 1, 1))
    assert len(filings) == 2  # the 2021 10-Q falls out


def test_source_url_and_dates(submissions):
    filings = {f["accession_no"]: f for f in extract_filings(submissions)}
    ten_k = filings["0000320193-23-000106"]
    assert ten_k["filing_date"] == date(2023, 11, 3)
    assert ten_k["period_end"] == date(2023, 9, 30)
    assert (
        ten_k["source_url"]
        == "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm"
    )


def test_missing_report_date_is_none(submissions):
    filings = extract_filings(submissions, forms=("8-K",))
    assert filings[0]["period_end"] is None
