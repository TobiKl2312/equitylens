from datetime import date

from app.ingestion.xbrl import extract_fundamentals


def _by_key(records: list[dict]) -> dict:
    return {(r["metric"], r["fiscal_year"], r["fiscal_period"]): r for r in records}


def test_extracts_all_mapped_metrics(companyfacts):
    records = _by_key(extract_fundamentals(companyfacts))
    assert ("revenue", 2023, "FY") in records
    assert ("revenue", 2024, "Q1") in records
    assert ("net_income", 2023, "FY") in records
    assert ("eps_diluted", 2023, "FY") in records


def test_restatement_wins_over_original(companyfacts):
    records = _by_key(extract_fundamentals(companyfacts))
    fy2023_revenue = records[("revenue", 2023, "FY")]
    # The 10-K/A was filed later than the 10-K, so its value must win
    assert fy2023_revenue["value"] == 383285000001
    assert fy2023_revenue["form"] == "10-K"  # /A suffix normalized away


def test_non_research_forms_are_ignored(companyfacts):
    records = _by_key(extract_fundamentals(companyfacts))
    q1_revenue = records[("revenue", 2024, "Q1")]
    # The 8-K fact for the same period must not leak in
    assert q1_revenue["value"] == 119575000000


def test_prior_year_comparative_does_not_mislabel(companyfacts):
    """A FY2024 10-K restates FY2023 numbers under fy=2024 labels;
    those comparatives must not be mistaken for FY2024 results."""
    records = _by_key(extract_fundamentals(companyfacts))
    fy2024_revenue = records[("revenue", 2024, "FY")]
    assert fy2024_revenue["value"] == 391035000000
    assert fy2024_revenue["period_end"] == date(2024, 9, 28)


def test_ytd_duration_rejected_for_quarter_label(companyfacts):
    """10-Qs report 3-month and 6-month YTD spans under the same Q2 label;
    only the true quarter duration may survive."""
    records = _by_key(extract_fundamentals(companyfacts))
    q2_revenue = records[("revenue", 2024, "Q2")]
    assert q2_revenue["value"] == 90753000000


def test_units_and_period_end(companyfacts):
    records = _by_key(extract_fundamentals(companyfacts))
    assert records[("eps_diluted", 2023, "FY")]["unit"] == "USD/shares"
    assert records[("revenue", 2023, "FY")]["period_end"] == date(2023, 9, 30)
