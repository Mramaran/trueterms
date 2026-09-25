"""
Tests for the TrueTerms loan-check MCP tools (src/mcpcore/loan_tools.py).

The ACTUS HTTP call is replaced by an outage so every check runs the local engine,
which the live tests in test_loan_truth.py prove matches ACTUS within 5 paise.
"""
import pytest

import loan_truth as lt
from src.mcpcore import loan_tools

RBI_OFFER = {"principal": 50000, "rate_pct": 2, "rate_period": "month", "rate_type": "flat",
             "tenure_months": 12, "processing_fee": 2000, "disbursal_date": "2026-10-01"}

# Rs 1,00,000 at 12%, sanctioned 3 Jan, disbursed 10 Jan, first EMI 5 Feb (26 days from disbursal):
# correct first interest = 100000 x 0.12 x 26/365 = 854.79;
# charged from sanction  = 100000 x 0.12 x 33/365 = 1084.93 -> excess 230.14
BOOK_CSV = (
    "loan_id,segment,principal,annual_rate_pct,tenure_months,sanction_date,disbursal_date,"
    "first_emi_date,advance_emis,emi_charged,first_interest_charged\n"
    "OK-1,retail,100000,12,12,2026-01-03,2026-01-10,2026-02-05,0,8884.88,854.79\n"
    "SANCTION-1,retail,100000,12,12,2026-01-03,2026-01-10,2026-02-05,0,8884.88,1084.93\n"
)


@pytest.fixture(autouse=True)
def actus_offline(monkeypatch):
    def outage(*args, **kwargs):
        raise lt.ActusUnavailable("offline for this test")
    monkeypatch.setattr(lt, "run_actus", outage)


# ── check-loan-offer ────────────────────────────────────────────────────────
def test_offer_tool_reports_true_apr_of_rbi_example():
    out = loan_tools.run_loan_tool("check-loan-offer", RBI_OFFER)
    assert out["apr_pct"] == 50.1
    assert out["emi"] == 5166.67
    assert out["net_disbursed"] == 48000.0
    assert out["total_payable"] == 62000.0
    assert out["actus_contract"]["contractType"] == "ANN"
    assert "schedule" not in out


def test_offer_tool_adds_schedule_only_when_asked():
    out = loan_tools.run_loan_tool("check-loan-offer", {**RBI_OFFER, "include_schedule": True})
    assert len(out["schedule"]) == 12
    assert out["schedule"][-1]["balance"] == 0.0


def test_offer_tool_reports_invalid_terms_as_error():
    out = loan_tools.run_loan_tool("check-loan-offer", {"principal": 50000, "rate_pct": 2})
    assert "tenure_months" in out["error"]


# ── check-loan-book ─────────────────────────────────────────────────────────
def test_book_tool_flags_only_the_sanction_date_loan_in_csv_text():
    out = loan_tools.run_loan_tool("check-loan-book", {"csv_text": BOOK_CSV})
    assert out["summary"]["loans_checked"] == 2
    assert out["summary"]["flagged"] == 1
    [loan] = out["flagged_loans"]
    assert loan["loan_id"] == "SANCTION-1"
    assert loan["pattern"] == "sanction_date_interest"
    assert loan["correct"] == 854.79
    assert loan["excess"] == 230.14


def test_book_tool_reads_csv_path(tmp_path):
    path = tmp_path / "book.csv"
    path.write_text(BOOK_CSV, encoding="utf-8")
    out = loan_tools.run_loan_tool("check-loan-book", {"csv_path": str(path)})
    assert [loan["loan_id"] for loan in out["flagged_loans"]] == ["SANCTION-1"]


def test_book_tool_demo_book_flags_the_35_seeded_errors_worst_first():
    out = loan_tools.run_loan_tool("check-loan-book", {"use_demo_book": True, "max_flagged": 5})
    summary = out["summary"]
    assert summary["loans_checked"] == 500
    assert summary["flagged"] == 35
    assert {k: v["count"] for k, v in summary["by_pattern"].items()} == {
        "sanction_date_interest": 18, "full_month_interest": 10,
        "advance_emi_full_principal": 7, "unexplained": 0}
    assert abs(summary["total_excess"] - 71396.19) < 1.0
    excess = [loan["excess"] for loan in out["flagged_loans"]]
    assert len(excess) == 5 and excess == sorted(excess, reverse=True)


@pytest.mark.parametrize("arguments", [{}, {"csv_text": BOOK_CSV, "use_demo_book": True}])
def test_book_tool_needs_exactly_one_source(arguments):
    out = loan_tools.run_loan_tool("check-loan-book", arguments)
    assert "exactly one" in out["error"]


def test_book_tool_rejects_a_path_that_is_not_csv(tmp_path):
    path = tmp_path / "book.txt"
    path.write_text(BOOK_CSV, encoding="utf-8")
    out = loan_tools.run_loan_tool("check-loan-book", {"csv_path": str(path)})
    assert ".csv" in out["error"]
