"""
Tests for backend/loan_truth.py — TrueTerms loan-verification engine.

Unit tests run offline (local engine / fake clients). Tests marked "live" talk to
the real ACTUS server (env ACTUS_SERVER_URL, default http://34.203.247.32:8083)
and are skipped automatically when it is unreachable.

Run from the project root:  pytest backend/tests -q
"""
import csv
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import loan_truth as lt

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEMO_DIR = BACKEND_DIR / "demo_data"
DEMO_CSV = DEMO_DIR / "demo_loan_book.csv"

BOOK_COLUMNS = [
    "loan_id", "segment", "principal", "annual_rate_pct", "tenure_months",
    "sanction_date", "disbursal_date", "first_emi_date", "advance_emis",
    "emi_charged", "first_interest_charged",
]

# Contract verified live against ACTUS (lender view, interest from disbursal date, A365).
T1 = {
    "contractType": "ANN", "contractID": "t1", "contractRole": "RPA",
    "statusDate": "2026-01-09T00:00:00", "contractDealDate": "2026-01-03T00:00:00",
    "initialExchangeDate": "2026-01-10T00:00:00", "maturityDate": "2027-01-05T00:00:00",
    "notionalPrincipal": 100000, "nominalInterestRate": 0.12, "currency": "INR",
    "dayCountConvention": "A365",
    "cycleAnchorDateOfInterestPayment": "2026-02-05T00:00:00", "cycleOfInterestPayment": "P1ML0",
    "cycleAnchorDateOfPrincipalRedemption": "2026-02-05T00:00:00", "cycleOfPrincipalRedemption": "P1ML0",
    "premiumDiscountAtIED": 0, "calendar": "NC", "businessDayConvention": "NOS",
    "endOfMonthConvention": "SD",
}

# RBI reference example: Rs 50,000 at "2% per month flat", 12 months, Rs 2,000 processing fee.
RBI_TERMS = {
    "principal": 50000, "rate_pct": 2, "rate_period": "month", "rate_type": "flat",
    "tenure_months": 12, "processing_fee": 2000, "disbursal_date": "2026-10-01",
}
RBI_TEXT = "Rs 50,000 loan at 2% per month flat for 12 months with Rs 2,000 processing fee"

UNREACHABLE = "http://127.0.0.1:9"  # nothing listens on the discard port


# ════════════════════════════════════════════════════════════════════════════
#  EMI / IRR / APR maths
# ════════════════════════════════════════════════════════════════════════════
def test_flat_emi_matches_rbi_example():
    # 2% per month flat = 24% a year flat
    assert lt.flat_emi(50000, 0.24, 12) == pytest.approx(5166.6667, abs=1e-3)


def test_reducing_emi_standard_formula():
    assert lt.reducing_emi(100000, 0.12, 12) == pytest.approx(8884.88, abs=0.01)


def test_reducing_emi_zero_rate():
    assert lt.reducing_emi(12000, 0.0, 12) == pytest.approx(1000.0)


def test_equivalent_reducing_rate_of_flat_loan_is_41_7_pct():
    emi = lt.flat_emi(50000, 0.24, 12)
    assert 12 * lt.monthly_irr(50000, [emi] * 12) == pytest.approx(0.417, abs=0.0005)


def test_apr_with_fee_is_50_1_pct():
    emi = lt.flat_emi(50000, 0.24, 12)
    assert lt.apr_from_cashflows([-48000] + [emi] * 12) == pytest.approx(0.501, abs=0.0005)


def test_apr_accepts_borrower_sign_convention():
    emi = lt.flat_emi(50000, 0.24, 12)
    assert lt.apr_from_cashflows([48000] + [-emi] * 12) == pytest.approx(0.501, abs=0.0005)


def test_apr_is_periodic_irr_times_12_not_compounded():
    emi = lt.reducing_emi(100000, 0.12, 24)
    assert lt.apr_from_cashflows([-100000] + [emi] * 24) == pytest.approx(0.12, abs=1e-9)


def test_monthly_irr_handles_zero_and_negative_rates():
    assert lt.monthly_irr(1200, [100] * 12) == pytest.approx(0.0, abs=1e-12)
    assert lt.monthly_irr(1200, [90] * 12) < 0


def test_monthly_irr_rejects_bad_input():
    with pytest.raises(ValueError):
        lt.monthly_irr(0, [100])
    with pytest.raises(ValueError):
        lt.monthly_irr(1000, [])


# ════════════════════════════════════════════════════════════════════════════
#  Rule-based offer parser
# ════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("text, expected", [
    (RBI_TEXT,
     dict(principal=50000, rate_pct=2, rate_period="month", rate_type="flat",
          tenure_months=12, processing_fee=2000)),
    ("₹5 lakh personal loan at 14% p.a. for 3 years, processing fee 1.5%",
     dict(principal=500000, rate_pct=14, rate_period="year", rate_type="reducing",
          tenure_months=36, processing_fee=7500)),
    ("INR 2.5 lakh at 18% per annum reducing balance for 24 months",
     dict(principal=250000, rate_pct=18, rate_period="year", rate_type="reducing",
          tenure_months=24, processing_fee=0)),
    ("50k at 1.5% monthly flat, 18 months tenure, processing charges Rs. 1,500",
     dict(principal=50000, rate_pct=1.5, rate_period="month", rate_type="flat",
          tenure_months=18, processing_fee=1500)),
    ("Loan of Rs.1,00,000 at 12% a year flat for 2 yrs",
     dict(principal=100000, rate_pct=12, rate_period="year", rate_type="flat",
          tenure_months=24, processing_fee=0)),
    ("Get 3 lakhs instantly! Interest 1.25% p.m. flat, 2% processing fee, tenure 1 year",
     dict(principal=300000, rate_pct=1.25, rate_period="month", rate_type="flat",
          tenure_months=12, processing_fee=6000)),
    ("12% yearly, INR 75000, 6 months",
     dict(principal=75000, rate_pct=12, rate_period="year", rate_type="reducing",
          tenure_months=6, processing_fee=0)),
])
def test_parse_offer_rules(text, expected):
    out = lt.parse_offer_rules(text)
    assert out["missing"] == []
    for key, value in expected.items():
        if isinstance(value, str):
            assert out["terms"][key] == value, key
        else:
            assert out["terms"][key] == pytest.approx(value), key


def test_parse_offer_rules_reports_missing_fields():
    out = lt.parse_offer_rules("They offered me a loan at 2% per month")
    assert set(out["missing"]) == {"principal", "tenure_months"}
    assert out["terms"]["rate_pct"] == pytest.approx(2)
    assert out["terms"]["rate_period"] == "month"


def test_parse_offer_rules_records_default_assumptions():
    out = lt.parse_offer_rules("Rs 1 lakh at 12% per annum for 12 months")
    assert out["terms"]["rate_type"] == "reducing"
    assert out["terms"]["processing_fee"] == 0
    joined = " ".join(out["assumptions"]).lower()
    assert "reducing" in joined and "fee" in joined


def test_parse_offer_rules_reads_stated_emi_and_dates():
    out = lt.parse_offer_rules(
        "Loan Rs 2,00,000 at 16% p.a. for 24 months, EMI Rs 9,793, "
        "sanctioned on 2026-10-01 and disbursed on 2026-10-05")
    assert out["terms"]["emi"] == pytest.approx(9793)
    assert out["terms"]["principal"] == pytest.approx(200000)
    assert out["terms"]["sanction_date"] == "2026-10-01"
    assert out["terms"]["disbursal_date"] == "2026-10-05"


# ════════════════════════════════════════════════════════════════════════════
#  LLM parser (fake client — no key / network needed)
# ════════════════════════════════════════════════════════════════════════════
class FakeLLMClient:
    """Mimics the api_server get_llm_client() wrapper: client.chat.completions.create(...)."""

    def __init__(self, content=None, exc=None):
        self.content, self.exc, self.calls = content, exc, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, response_format=None, **kwargs):
        self.calls.append({"model": model, "messages": messages, "response_format": response_format})
        if self.exc:
            raise self.exc
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


LLM_JSON = json.dumps({
    "principal": 50000, "rate_pct": 2, "rate_period": "month", "rate_type": "flat",
    "tenure_months": 12, "processing_fee": 2000, "processing_fee_pct": None, "emi": None,
    "disbursal_date": None, "sanction_date": None, "lender_name": None,
})


def test_parse_offer_llm_normalises_json_and_requests_json_mode():
    fake = FakeLLMClient(content=LLM_JSON)
    out = lt.parse_offer_llm("ரூ.50,000 கடன், மாதம் 2% flat, 12 மாதம், ரூ.2,000 processing fee",
                             "ta", fake, "test-model")
    assert out["terms"]["principal"] == pytest.approx(50000)
    assert out["terms"]["rate_type"] == "flat"
    assert out["terms"]["processing_fee"] == pytest.approx(2000)
    assert out["missing"] == []
    call = fake.calls[0]
    assert call["model"] == "test-model"
    assert call["response_format"] == {"type": "json_object"}
    assert "Tamil" in call["messages"][-1]["content"]


def test_parse_offer_without_api_key_uses_rules(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    created = []
    out = lt.parse_offer(RBI_TEXT, "en", client_factory=lambda: created.append(1), model="m")
    assert out["parser"] == "rules"
    assert created == []  # the LLM client is never even constructed
    assert out["terms"]["principal"] == pytest.approx(50000)


def test_parse_offer_with_api_key_uses_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-for-test")
    out = lt.parse_offer("रु 50,000 का लोन, 2% प्रति माह flat, 12 महीने", "hi",
                         client_factory=lambda: FakeLLMClient(content=LLM_JSON), model="m")
    assert out["parser"] == "llm"
    assert out["terms"]["tenure_months"] == 12


@pytest.mark.parametrize("client", [
    FakeLLMClient(exc=RuntimeError("boom: API down")),
    FakeLLMClient(content="this is not json"),
])
def test_parse_offer_falls_back_to_rules_when_llm_fails(monkeypatch, client):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-for-test")
    out = lt.parse_offer(RBI_TEXT, "en", client_factory=lambda: client, model="m")
    assert out["parser"] == "rules"
    assert out["llm_error"]
    assert out["terms"]["processing_fee"] == pytest.approx(2000)


# ════════════════════════════════════════════════════════════════════════════
#  Offer check (local engine — offline)
# ════════════════════════════════════════════════════════════════════════════
def test_check_offer_rbi_example_local_engine():
    r = lt.check_offer(RBI_TERMS, use_actus=False)
    assert r["engine"] == "local-fallback"
    assert r["emi"] == pytest.approx(5166.67, abs=0.1)
    assert r["apr_pct"] == pytest.approx(50.1, abs=0.05)
    assert r["equivalent_reducing_rate_pct"] == pytest.approx(41.7, abs=0.05)
    assert r["advertised_annual_rate_pct"] == pytest.approx(24)
    assert r["advertised_rate_text"] == "2% per month flat ≈ 24% a year"
    assert r["fees"] == pytest.approx(2000)
    assert r["net_disbursed"] == pytest.approx(48000)
    assert r["total_payable"] == pytest.approx(62000, abs=0.5)
    assert r["total_interest"] == pytest.approx(12000, abs=0.5)
    assert r["total_cost_of_credit"] == pytest.approx(14000, abs=0.5)
    sched = r["schedule"]
    assert len(sched) == 12
    assert sched[0]["date"] == "2026-11-01" and sched[-1]["date"] == "2027-10-01"
    assert sum(row["principal"] for row in sched) == pytest.approx(50000, abs=0.05)
    assert sched[-1]["balance"] == pytest.approx(0, abs=0.01)
    assert all(row["emi"] == pytest.approx(5166.67, abs=0.02) for row in sched)


def test_check_offer_builds_the_specified_actus_contract():
    c = lt.check_offer(RBI_TERMS, use_actus=False)["actus_contract"]
    assert c["contractType"] == "ANN" and c["contractRole"] == "RPA"
    assert c["dayCountConvention"] == "30E360" and c["currency"] == "INR"
    assert c["notionalPrincipal"] == pytest.approx(50000)
    assert c["premiumDiscountAtIED"] == pytest.approx(-2000)
    assert c["nominalInterestRate"] == pytest.approx(0.41703121289747935, rel=1e-9)
    assert c["initialExchangeDate"] == "2026-10-01T00:00:00"
    assert c["statusDate"] == "2026-09-30T00:00:00"
    assert c["contractDealDate"] == "2026-09-30T00:00:00"  # no sanction date -> statusDate
    assert c["cycleAnchorDateOfInterestPayment"] == "2026-11-01T00:00:00"
    assert c["cycleAnchorDateOfPrincipalRedemption"] == "2026-11-01T00:00:00"
    assert c["cycleOfInterestPayment"] == "P1ML0" and c["cycleOfPrincipalRedemption"] == "P1ML0"
    assert c["maturityDate"] == "2027-10-01T00:00:00"


def test_check_offer_uses_sanction_date_as_deal_date():
    terms = dict(RBI_TERMS, sanction_date="2026-09-20")
    c = lt.check_offer(terms, use_actus=False)["actus_contract"]
    assert c["contractDealDate"] == "2026-09-20T00:00:00"


def test_check_offer_reducing_offer_apr_equals_rate_without_fees():
    terms = {"principal": 500000, "rate_pct": 14, "rate_period": "year", "rate_type": "reducing",
             "tenure_months": 36, "processing_fee": 0, "disbursal_date": "2026-10-01"}
    r = lt.check_offer(terms, use_actus=False)
    assert r["apr_pct"] == pytest.approx(14.0, abs=0.01)
    assert r["equivalent_reducing_rate_pct"] == pytest.approx(14.0, abs=0.01)
    assert r["emi"] == pytest.approx(lt.reducing_emi(500000, 0.14, 36), abs=0.01)
    assert r["advertised_rate_text"] == "14% a year reducing"


def test_check_offer_stated_emi_wins_over_formula():
    terms = dict(RBI_TERMS, emi=5500)
    r = lt.check_offer(terms, use_actus=False)
    assert r["emi"] == pytest.approx(5500, abs=0.05)
    assert r["apr_pct"] > 50.1


def test_check_offer_defaults_disbursal_date_to_tomorrow():
    terms = {k: v for k, v in RBI_TERMS.items() if k != "disbursal_date"}
    r = lt.check_offer(terms, use_actus=False)
    assert r["disbursal_date"] == (date.today() + timedelta(days=1)).isoformat()


def test_check_offer_month_end_disbursal_keeps_twelve_regular_dates():
    terms = dict(RBI_TERMS, disbursal_date="2027-01-31")
    r = lt.check_offer(terms, use_actus=False)
    dates = [row["date"] for row in r["schedule"]]
    assert len(dates) == 12
    assert dates[0] == "2027-02-28" and dates[1] == "2027-03-28" and dates[-1] == "2028-01-28"


@pytest.mark.parametrize("bad", [
    dict(RBI_TERMS, principal=0),
    dict(RBI_TERMS, tenure_months=0),
    dict(RBI_TERMS, processing_fee=50000),
    dict(RBI_TERMS, rate_period="fortnight"),
    dict(RBI_TERMS, disbursal_date="31/31/2026"),
])
def test_check_offer_rejects_invalid_terms(bad):
    with pytest.raises(ValueError):
        lt.check_offer(bad, use_actus=False)


def test_check_offer_falls_back_locally_when_actus_unreachable():
    r = lt.check_offer(RBI_TERMS, url=UNREACHABLE, retry_delay=0)
    assert r["engine"] == "local-fallback"
    assert r["engine_note"]
    assert r["apr_pct"] == pytest.approx(50.1, abs=0.05)
    assert len(r["schedule"]) == 12


# ════════════════════════════════════════════════════════════════════════════
#  Loan-book check (local engine / fake ACTUS runner — offline)
# ════════════════════════════════════════════════════════════════════════════
def _row(**overrides):
    row = {
        "loan_id": "L1", "segment": "Retail", "principal": "100000", "annual_rate_pct": "12",
        "tenure_months": "12", "sanction_date": "2026-01-03", "disbursal_date": "2026-01-10",
        "first_emi_date": "2026-02-05", "advance_emis": "0", "emi_charged": "8884.88",
        "first_interest_charged": "854.79",
    }
    row.update({k: str(v) for k, v in overrides.items()})
    return row


def test_book_contract_follows_spec():
    c = lt.book_contract(lt.normalize_book_row(_row(advance_emis=1)), "L1")
    assert c["contractType"] == "ANN" and c["dayCountConvention"] == "A365"
    assert c["initialExchangeDate"] == "2026-01-10T00:00:00"
    assert c["contractDealDate"] == "2026-01-03T00:00:00"
    assert c["cycleAnchorDateOfInterestPayment"] == "2026-02-05T00:00:00"
    assert c["cycleAnchorDateOfPrincipalRedemption"] == "2026-02-05T00:00:00"
    assert c["notionalPrincipal"] == pytest.approx(100000 - 8884.88)
    # 11 remaining EMIs: 2026-02-05 + 10 months
    assert c["maturityDate"] == "2026-12-05T00:00:00"


def test_check_loan_book_classifies_each_pattern():
    rows = [
        _row(loan_id="OK1"),
        _row(loan_id="SAN", first_interest_charged=f"{100000 * 0.12 * 33 / 365:.2f}"),
        _row(loan_id="FULL", first_interest_charged="1000.00"),
        _row(loan_id="ADV", advance_emis="1", first_interest_charged="854.79"),
        _row(loan_id="UNX", first_interest_charged="1500.00"),
        _row(loan_id="BAD", disbursal_date="not-a-date"),
    ]
    out = lt.check_loan_book(rows, use_actus=False)
    by_id = {loan["loan_id"]: loan for loan in out["loans"]}

    assert by_id["OK1"]["status"] == "ok"
    assert by_id["OK1"]["correct"] == pytest.approx(854.79, abs=0.01)

    san = by_id["SAN"]
    assert san["status"] == "flagged" and san["pattern"] == "sanction_date_interest"
    assert san["excess"] == pytest.approx(100000 * 0.12 * 7 / 365, abs=0.02)
    assert "7 extra days" in san["explanation"]

    assert by_id["FULL"]["pattern"] == "full_month_interest"
    assert by_id["FULL"]["excess"] == pytest.approx(1000 - 854.79, abs=0.02)

    adv = by_id["ADV"]
    assert adv["pattern"] == "advance_emi_full_principal"
    assert adv["correct"] == pytest.approx((100000 - 8884.88) * 0.12 * 26 / 365, abs=0.01)
    assert adv["excess"] == pytest.approx(8884.88 * 0.12 * 26 / 365, abs=0.02)

    assert by_id["UNX"]["pattern"] == "unexplained"
    assert by_id["BAD"]["status"] == "error" and by_id["BAD"]["explanation"]

    s = out["summary"]
    assert (s["loans_checked"], s["ok"], s["flagged"], s["errors"]) == (6, 1, 4, 1)
    assert s["by_pattern"]["sanction_date_interest"]["count"] == 1
    assert s["by_pattern"]["unexplained"]["count"] == 1
    flagged_total = sum(l["excess"] for l in out["loans"] if l["status"] == "flagged")
    assert s["total_excess"] == pytest.approx(flagged_total, abs=0.01)
    assert s["engine"] == "local-fallback"
    assert s["elapsed_seconds"] >= 0


def test_check_loan_book_tolerance_is_max_1_rupee_or_half_percent():
    # correct = 854.79 -> tolerance = max(1, 4.27) = 4.27
    out = lt.check_loan_book([
        _row(loan_id="IN", first_interest_charged="858.79"),   # +4.00 -> ok
        _row(loan_id="OUT", first_interest_charged="859.89"),  # +5.10 -> flagged
    ], use_actus=False)
    status = {l["loan_id"]: l["status"] for l in out["loans"]}
    assert status == {"IN": "ok", "OUT": "flagged"}


def test_check_loan_book_sends_chunks_of_100_and_reports_actus_rejections():
    rows = [_row(loan_id=f"L{i:03d}") for i in range(250)]
    batches = []

    def fake_runner(contracts, **kwargs):
        batches.append(len(contracts))
        results = []
        for c in contracts:
            if c["contractID"] == "L007":
                results.append({"contractID": "L007", "status": "Failure",
                                "message": "org.actus.AttributeConversionException", "events": []})
                continue
            ip = c["notionalPrincipal"] * c["nominalInterestRate"] * 26 / 365
            results.append({"contractID": c["contractID"], "status": "Success", "message": "",
                            "events": [{"type": "IED", "time": "2026-01-10T00:00", "payoff": -c["notionalPrincipal"]},
                                       {"type": "IP", "time": "2026-02-05T00:00", "payoff": ip}]})
        return results

    out = lt.check_loan_book(rows, runner=fake_runner)
    assert sorted(batches, reverse=True) == [100, 100, 50]
    bad = next(l for l in out["loans"] if l["loan_id"] == "L007")
    assert bad["status"] == "error" and "AttributeConversionException" in bad["explanation"]
    assert out["summary"]["engine"] == "ACTUS"
    assert out["summary"]["actus_calls"] == 3
    assert out["summary"]["ok"] == 249 and out["summary"]["errors"] == 1


def test_check_loan_book_falls_back_locally_when_actus_unreachable():
    out = lt.check_loan_book([_row(), _row(loan_id="SAN", first_interest_charged="1084.93")],
                             url=UNREACHABLE, retry_delay=0)
    assert out["summary"]["engine"] == "local-fallback"
    assert out["summary"]["flagged"] == 1


def test_read_loan_book_csv_validates_header():
    text = ",".join(BOOK_COLUMNS) + "\n" + ",".join(_row().values()) + "\n"
    rows = lt.read_loan_book_csv("\ufeff" + text)  # tolerate a UTF-8 BOM (Excel)
    assert len(rows) == 1 and rows[0]["loan_id"] == "L1"
    with pytest.raises(ValueError):
        lt.read_loan_book_csv("loan_id,principal\nL1,100\n")


# ════════════════════════════════════════════════════════════════════════════
#  KFS (Key Facts Statement) HTML
# ════════════════════════════════════════════════════════════════════════════
def test_build_kfs_html_contains_rbi_sections():
    result = lt.check_offer(RBI_TERMS, use_actus=False)
    result["engine"] = "ACTUS"  # render as if the engine computed it
    html = lt.build_kfs_html(result, lender_name="Acme <Finance>")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "Key Facts Statement (illustrative, RBI format)" in html
    assert "Part 1" in html and "Annex B" in html and "Annex C" in html
    assert "50.10%" in html and "41.70%" in html
    assert "5,166.67" in html and "48,000.00" in html and "62,000.00" in html
    assert html.count('class="sched-row"') == 12
    assert "@page" in html and "A4" in html
    assert "Acme &lt;Finance&gt;" in html  # user input is escaped
    assert "Computed with the ACTUS open-standard engine. Illustrative, not legal advice." in html
    assert "<script src" not in html and "<link" not in html  # self-contained


def test_build_kfs_html_is_honest_about_local_fallback():
    html = lt.build_kfs_html(lt.check_offer(RBI_TERMS, use_actus=False))
    assert "Computed with the ACTUS open-standard engine." not in html
    assert "Illustrative, not legal advice." in html


# ════════════════════════════════════════════════════════════════════════════
#  Demo loan book (deterministic generator + seeded errors)
# ════════════════════════════════════════════════════════════════════════════
def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_loan_book", DEMO_DIR / "generate_loan_book.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _demo_rows():
    with DEMO_CSV.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_demo_book_file_is_reproducible_from_generator(tmp_path):
    gen = _load_generator()
    out = tmp_path / "book.csv"
    gen.write_csv(gen.generate_loan_book(), out)
    assert out.read_bytes() == DEMO_CSV.read_bytes()


def test_demo_book_shape_and_ranges():
    rows = _demo_rows()
    assert len(rows) == 500
    assert list(rows[0].keys()) == BOOK_COLUMNS
    assert len({r["loan_id"] for r in rows}) == 500
    for r in rows:
        assert r["segment"] in ("Retail", "MSME")
        assert 50_000 <= float(r["principal"]) <= 2_500_000
        assert 9 <= float(r["annual_rate_pct"]) <= 24
        assert 12 <= int(r["tenure_months"]) <= 84
        sanction, disbursal, first = (date.fromisoformat(r[k]) for k in
                                      ("sanction_date", "disbursal_date", "first_emi_date"))
        assert sanction.year == disbursal.year == first.year == 2026
        assert 1 <= (disbursal - sanction).days <= 15
        assert (first.year * 12 + first.month) - (disbursal.year * 12 + disbursal.month) == 1
        assert int(r["advance_emis"]) in (0, 1)
    assert len({date.fromisoformat(r["first_emi_date"]).day for r in rows}) == 1  # fixed EMI day


def test_demo_book_has_exactly_the_35_seeded_errors():
    out = lt.check_loan_book(_demo_rows(), use_actus=False)
    s = out["summary"]
    assert (s["loans_checked"], s["flagged"], s["errors"]) == (500, 35, 0)
    counts = {k: v["count"] for k, v in s["by_pattern"].items() if v["count"]}
    assert counts == {"sanction_date_interest": 18, "full_month_interest": 10,
                      "advance_emi_full_principal": 7}
    correct_advance = [l for l, r in zip(out["loans"], _demo_rows())
                       if l["status"] == "ok" and r["advance_emis"] == "1"]
    assert len(correct_advance) == 40


# ════════════════════════════════════════════════════════════════════════════
#  LIVE ACTUS integration (skipped when the server is unreachable)
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def live_url():
    url = lt.actus_url()
    try:
        res = httpx.post(f"{url}/eventsBatch", json={"contracts": [T1], "riskFactors": []}, timeout=20)
        res.raise_for_status()
    except Exception as exc:  # pragma: no cover - depends on network
        pytest.skip(f"ACTUS server unreachable at {url}: {exc}")
    return url


def test_live_actus_charges_interest_from_disbursal_date(live_url):
    events = lt.run_actus([T1], url=live_url)[0]["events"]
    first_ip = next(e for e in events if e["type"] == "IP")
    assert first_ip["time"].startswith("2026-02-05")
    assert first_ip["payoff"] == pytest.approx(854.79, abs=0.005)  # 100000 x 12% x 26/365


def test_live_actus_fee_reduces_ied_payoff(live_url):
    contract = dict(T1, contractID="fee", notionalPrincipal=50000, premiumDiscountAtIED=-2000,
                    dayCountConvention="30E360", nominalInterestRate=0.4170)
    events = lt.run_actus([contract], url=live_url)[0]["events"]
    ied = next(e for e in events if e["type"] == "IED")
    assert ied["payoff"] == pytest.approx(-48000)


def test_live_check_offer_rbi_example(live_url):
    r = lt.check_offer(RBI_TERMS, url=live_url)
    assert r["engine"] == "ACTUS"
    assert r["apr_pct"] == pytest.approx(50.1, abs=0.05)
    assert r["emi"] == pytest.approx(5166.67, abs=0.1)
    assert r["net_disbursed"] == pytest.approx(48000)


@pytest.mark.parametrize("terms", [
    RBI_TERMS,
    dict(RBI_TERMS, disbursal_date="2027-01-31"),
    {"principal": 500000, "rate_pct": 14, "rate_period": "year", "rate_type": "reducing",
     "tenure_months": 36, "processing_fee": 7500, "disbursal_date": "2026-10-15"},
])
def test_live_local_fallback_reproduces_actus_schedule(live_url, terms):
    remote = lt.check_offer(terms, url=live_url)
    local = lt.check_offer(terms, use_actus=False)
    assert remote["engine"] == "ACTUS"
    assert len(remote["schedule"]) == len(local["schedule"])
    for a, b in zip(remote["schedule"], local["schedule"]):
        assert a["date"] == b["date"]
        for key in ("emi", "interest", "principal", "balance"):
            assert a[key] == pytest.approx(b[key], abs=0.01), (a["date"], key)
    assert remote["apr_pct"] == pytest.approx(local["apr_pct"], abs=0.005)


def test_live_demo_book_correct_loans_match_actus_within_5_paise(live_url):
    gen = _load_generator()
    rows, labels = gen.build_book()
    sample = [r for r in rows if labels[r["loan_id"]] is None and r["advance_emis"] == "1"][:5]
    sample += [r for r in rows if labels[r["loan_id"]] is None and r["advance_emis"] == "0"][:10]
    contracts = [lt.book_contract(lt.normalize_book_row(r), r["loan_id"]) for r in sample]
    results = {res.get("contractID") or res.get("contractId"): res for res in lt.run_actus(contracts, url=live_url)}
    for r in sample:
        first_ip = next(e for e in results[r["loan_id"]]["events"] if e["type"] == "IP")
        assert float(r["first_interest_charged"]) == pytest.approx(first_ip["payoff"], abs=0.05), r["loan_id"]


def test_live_demo_book_full_check_finds_35_errors(live_url):
    out = lt.check_loan_book(_demo_rows(), url=live_url)
    s = out["summary"]
    assert s["engine"] == "ACTUS" and s["actus_calls"] == 5
    assert (s["loans_checked"], s["flagged"], s["errors"]) == (500, 35, 0)
    counts = {k: v["count"] for k, v in s["by_pattern"].items() if v["count"]}
    assert counts == {"sanction_date_interest": 18, "full_month_interest": 10,
                      "advance_emi_full_principal": 7}
