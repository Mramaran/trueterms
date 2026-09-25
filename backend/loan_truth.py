"""
TrueTerms — independent loan-verification engine
================================================
AI (or a rule-based parser) reads a loan, the open ACTUS engine computes every
rupee, and we compare the result with what the lender charged.

Anchored on two RBI rules:
  1. RBI circular of 29 Apr 2024: lenders were found charging interest from the
     sanction date instead of the disbursal date, charging interest for the whole
     month, and collecting EMIs in advance while charging interest on the full
     principal. Refunds were ordered.
  2. RBI Key Facts Statement (KFS) rule, effective 1 Oct 2024: every retail/MSME
     loan needs an APR computation sheet plus a repayment schedule.

RBI APR convention used throughout: APR = periodic (monthly) IRR x 12, computed on
the net disbursed amount. No compounding and no XIRR.

Pure logic plus a small ACTUS client. Dependencies: Python stdlib + httpx.
"""
from __future__ import annotations

import calendar
import csv
import html as _html
import io
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import httpx

# ── Constants ────────────────────────────────────────────────────────────────
ACTUS_DEFAULT_URL = "http://34.203.247.32:8083"   # same default as api_server.py
PERIODS_PER_YEAR = 12
BOOK_CHUNK_SIZE = 100                              # contracts per /eventsBatch call

BOOK_COLUMNS = [
    "loan_id", "segment", "principal", "annual_rate_pct", "tenure_months",
    "sanction_date", "disbursal_date", "first_emi_date", "advance_emis",
    "emi_charged", "first_interest_charged",
]

PATTERNS = (
    "sanction_date_interest",
    "full_month_interest",
    "advance_emi_full_principal",
    "unexplained",
)
PATTERN_LABELS = {
    "sanction_date_interest": "Interest charged from the sanction date, not the disbursal date",
    "full_month_interest": "Full month's interest charged for a part month",
    "advance_emi_full_principal": "Advance EMI collected but interest charged on the full principal",
    "unexplained": "Overcharge that matches no known pattern",
}

REQUIRED_OFFER_FIELDS = ("principal", "rate_pct", "tenure_months")
LANGUAGE_NAMES = {
    "en": "English", "ta": "Tamil", "hi": "Hindi",
    "tanglish": "Tanglish (Tamil + English mixed)", "auto": "an Indian language or English",
}


class ActusUnavailable(RuntimeError):
    """Raised when the ACTUS server cannot be reached after all retries."""


def actus_url() -> str:
    """ACTUS server base URL (env ACTUS_SERVER_URL, read at call time)."""
    return os.environ.get("ACTUS_SERVER_URL", ACTUS_DEFAULT_URL).rstrip("/")


# ════════════════════════════════════════════════════════════════════════════
#  Small helpers: dates, numbers, money formatting
# ════════════════════════════════════════════════════════════════════════════
def add_months(d: date, months: int) -> date:
    """Calendar month arithmetic, clamping to month end (31 Jan + 1 month = 28 Feb)."""
    years, month_index = divmod(d.month - 1 + months, 12)
    year, month = d.year + years, month_index + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


_DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y",
                 "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y")


def parse_date(value) -> date:
    """Parse ISO (YYYY-MM-DD[T...]) or common Indian formats (DD-MM-YYYY, DD/MM/YYYY)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError("date is empty")
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            pass
    else:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"invalid date: {text!r}")


def _iso_dt(d: date) -> str:
    return f"{d.isoformat()}T00:00:00"


def _to_float(value, name: str) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{name} is required")
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        cleaned = re.sub(r"[₹,\s]|rs\.?|inr", "", str(value).strip().lower())
        try:
            number = float(cleaned)
        except ValueError:
            raise ValueError(f"{name} must be a number (got {value!r})") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be a finite number")
    return number


def format_inr(amount: float, decimals: int = 2) -> str:
    """Indian digit grouping: 2500000 -> '25,00,000.00'."""
    negative = amount < 0
    text = f"{abs(amount):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return ("-" if negative else "") + whole + (f".{frac}" if frac else "")


def _fmt_pct(value: float) -> str:
    """2.0 -> '2', 1.25 -> '1.25', 41.703 -> '41.7'."""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _inr(amount: float) -> str:
    return f"₹{format_inr(amount)}"


# ════════════════════════════════════════════════════════════════════════════
#  EMI / IRR / APR
# ════════════════════════════════════════════════════════════════════════════
def flat_emi(principal: float, annual_rate: float, months: int) -> float:
    """Flat-rate EMI: interest on the ORIGINAL principal for the whole tenure."""
    if months <= 0:
        raise ValueError("months must be positive")
    return (principal + principal * annual_rate * months / 12.0) / months


def reducing_emi(principal: float, annual_rate: float, months: int) -> float:
    """Standard reducing-balance EMI with monthly rate annual_rate / 12."""
    if months <= 0:
        raise ValueError("months must be positive")
    i = annual_rate / 12.0
    if abs(i) < 1e-15:
        return principal / months
    return principal * i / (1.0 - (1.0 + i) ** (-months))


def _npv(rate: float, net: float, payments: list[float]) -> float:
    total, factor = -net, 1.0
    for payment in payments:
        factor /= (1.0 + rate)
        if payment:
            total += payment * factor
    return total


def monthly_irr(net_disbursed: float, payments) -> float:
    """
    Periodic IRR by bisection: the rate i with  net = sum(p_k / (1+i)^k),  k = 1..n.
    Robust for zero and negative rates. NPV is strictly decreasing in i because all
    payments are non-negative, so a sign change brackets exactly one root.
    """
    net = float(net_disbursed)
    pays = [float(p) for p in payments]
    if not pays:
        raise ValueError("at least one payment is required")
    if not net > 0:
        raise ValueError("net disbursed amount must be positive")
    if any(p < 0 for p in pays) or sum(pays) <= 0:
        raise ValueError("payments must be non-negative and not all zero")

    lo, hi = -0.99, 10.0
    while _npv(hi, net, pays) > 0 and hi < 1e6:   # absurd rates: widen the bracket
        hi *= 10.0
    if _npv(lo, net, pays) < 0 or _npv(hi, net, pays) > 0:
        raise ValueError("IRR could not be bracketed")
    for _ in range(300):
        mid = (lo + hi) / 2.0
        if _npv(mid, net, pays) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-15:
            break
    return (lo + hi) / 2.0


def apr_from_cashflows(cashflows, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """
    RBI KFS APR: periods_per_year x periodic IRR (no compounding, not XIRR).
    cashflows[0] is the net disbursal at t=0, cashflows[k] the instalment at period k.
    Either sign convention works (lender: -net, +payments; borrower: +net, -payments).
    """
    flows = [float(x) for x in cashflows]
    if len(flows) < 2:
        raise ValueError("need a disbursal and at least one payment")
    if flows[0] > 0:
        flows = [-x for x in flows]
    return periods_per_year * monthly_irr(-flows[0], flows[1:])


# ════════════════════════════════════════════════════════════════════════════
#  Offer parsing — rules (English) and LLM (Tamil / Hindi / English)
# ════════════════════════════════════════════════════════════════════════════
_NUM = r"\d+(?:\.\d+)?"
_CURRENCY = r"(?<![a-z])(?:rs\.?|inr|rupees?|rupaye|rupaiya)"
_UNIT_MULTIPLIER = {"lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5,
                    "crore": 1e7, "crores": 1e7, "cr": 1e7, "thousand": 1e3, "k": 1e3}

AMOUNT_RE = re.compile(
    rf"(?P<cur>{_CURRENCY})?\s*(?P<num>{_NUM})"
    r"(?P<unit>\s*(?:lakhs|lakh|lacs|lac|crores|crore|cr|thousand|k)(?![a-z])|l(?![a-z]))?"
    rf"(?P<cur2>\s*(?:{_CURRENCY})(?![a-z]))?"
    r"(?!\s*%|\d|\.\d|\s*(?:percent|per\s*cent))"
)
PCT_RE = re.compile(rf"(?P<num>{_NUM})\s*(?:%|percent(?![a-z])|per\s*cent(?![a-z]))")
TENURE_RE = re.compile(
    rf"(?P<num>{_NUM})\s*-?\s*(?P<unit>months|month|mths|mth|mnths|mnth|mos|mo|years|year|yrs|yr"
    r"|emis|instalments|installments)(?![a-z])")
TENURE_NO_UNIT_RE = re.compile(r"tenure\s*(?:of|is|:|-)?\s*(?P<num>\d+)(?![\d.%])(?!\s*(?:years?|yrs?|months?))")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4}")

_MONTH_PERIOD_RE = re.compile(
    r"per\s*month|a\s*month|every\s*month|each\s*month|monthly|(?<![a-z])p\.?\s*m\.?(?![a-z])"
    r"|/\s*(?:month|mo)(?![a-z])|per\s*mensem")
_YEAR_PERIOD_RE = re.compile(
    r"per\s*annum|per\s*year|a\s*year|every\s*year|each\s*year|yearly|annually|annual"
    r"|(?<![a-z])p\.?\s*a\.?(?![a-z])|/\s*(?:year|yr|annum)(?![a-z])")
_FEE_KW_RE = re.compile(
    r"processing\s*(?:fees?|charges?)|processing|file\s*charges?|admin(?:istrative)?\s*(?:fees?|charges?)"
    r"|upfront\s*(?:fees?|charges?)|(?<![a-z])fees?(?![a-z])")
_EMI_KW_RE = re.compile(r"(?<![a-z])emi(?![a-z])|monthly\s*instal+ment|instal+ment\s*amount|monthly\s*payment")
_RATE_CONTEXT_RE = re.compile(r"interest|rate|roi|flat|reducing|diminishing")
_LOAN_CONTEXT_RE = re.compile(r"loan|amount|principal|borrow|sanction")


def _normalise_text(text: str) -> str:
    t = str(text or "").lower().replace("₹", " rs ")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)          # 1,00,000 -> 100000
    return re.sub(r"\s+", " ", t).strip()


def _has_rate_words(fragment: str) -> bool:
    return bool(_RATE_CONTEXT_RE.search(fragment) or _MONTH_PERIOD_RE.search(fragment)
                or _YEAR_PERIOD_RE.search(fragment))


def _window_before(t: str, pos: int, width: int = 35) -> str:
    """Text just before pos, cut after the previous number (so it belongs to this number only)."""
    before = t[max(0, pos - width):pos]
    digits = list(re.finditer(r"\d", before))
    return before[digits[-1].end():] if digits else before


def _window_after(t: str, pos: int, width: int = 40) -> str:
    """Text just after pos, cut before the next number."""
    after = t[pos:pos + width]
    next_digit = re.search(r"\d", after)
    return after[:next_digit.start()] if next_digit else after


def _is_fee_percent(t: str, m) -> bool:
    """'processing fee 1.5%' / '2% processing fee' / '2% of the loan as fee' -> fee, not interest."""
    before = _window_before(t, m.start())
    keywords = list(_FEE_KW_RE.finditer(before))
    if keywords and not _has_rate_words(before[keywords[-1].end():]):
        return True
    after = _window_after(t, m.end())
    keyword = _FEE_KW_RE.search(after)
    return bool(keyword and keyword.start() <= 25 and not _has_rate_words(after[:keyword.start()]))


def _amount_value(match) -> float:
    value = float(match.group("num"))
    unit = (match.group("unit") or "").strip()
    return value * _UNIT_MULTIPLIER.get(unit, 1.0)


def _is_marked(match) -> bool:
    return bool(match.group("cur") or match.group("unit") or match.group("cur2"))


def _overlaps(span, spans) -> bool:
    return any(span[0] < s[1] and s[0] < span[1] for s in spans)


def _gap_has_digit(t: str, start: int, end: int) -> bool:
    return bool(re.search(r"\d", t[start:end]))


def _empty_terms() -> dict:
    return {
        "principal": None, "rate_pct": None, "rate_period": None, "rate_type": None,
        "tenure_months": None, "processing_fee": None, "processing_fee_pct": None,
        "emi": None, "disbursal_date": None, "sanction_date": None, "lender_name": None,
    }


def parse_offer_rules(text: str) -> dict:
    """
    Rule-based English offer parser. Handles Rs/INR/₹, Indian commas, lakh/crore/k,
    '% per month / p.m. / monthly' vs '% per annum / p.a. / a year / yearly',
    flat vs reducing, tenure in months or years, processing fee as amount or %.
    Returns {"terms": {...}, "missing": [...], "assumptions": [...]}.
    """
    t = _normalise_text(text)
    raw = _empty_terms()
    notes = []

    # Dates first (and blank them out so '2026' is never read as an amount).
    for m in DATE_RE.finditer(t):
        before = t[max(0, m.start() - 30):m.start()]
        try:
            iso = parse_date(m.group()).isoformat()
        except ValueError:
            continue
        if "sanction" in before and not raw["sanction_date"]:
            raw["sanction_date"] = iso
        elif "disburs" in before and not raw["disbursal_date"]:
            raw["disbursal_date"] = iso
    t_nodates = DATE_RE.sub(lambda m: " " * len(m.group()), t)

    used = []  # spans already claimed by rate / fee / tenure / emi

    # ── Percentages: interest rate vs processing-fee percentage ──────────────
    fee_pct_match, rate_candidates = None, []
    for m in PCT_RE.finditer(t_nodates):
        if _is_fee_percent(t_nodates, m):
            fee_pct_match = fee_pct_match or m
        else:
            rate_candidates.append(m)
    # Prefer a percentage that sits next to rate words ("interest 14%", "2% per month flat").
    rate_match = next((m for m in rate_candidates
                       if _has_rate_words(_window_before(t_nodates, m.start()))
                       or _has_rate_words(_window_after(t_nodates, m.end()))), None)
    rate_match = rate_match or (rate_candidates[0] if rate_candidates else None)

    if rate_match:
        used.append(rate_match.span())
        raw["rate_pct"] = float(rate_match.group("num"))
        after = _window_after(t_nodates, rate_match.end(), 45)
        before = _window_before(t_nodates, rate_match.start(), 30)
        m_after, y_after = _MONTH_PERIOD_RE.search(after), _YEAR_PERIOD_RE.search(after)
        if m_after or y_after:
            month_first = m_after and (not y_after or m_after.start() < y_after.start())
            raw["rate_period"] = "month" if month_first else "year"
        elif _MONTH_PERIOD_RE.search(before):
            raw["rate_period"] = "month"
        elif _YEAR_PERIOD_RE.search(before):
            raw["rate_period"] = "year"
        else:
            notes.append("Rate period not stated: assumed per year.")
        # Rate type: look next to the quoted rate first, then for explicit phrases anywhere.
        near = f"{before} {after}"
        if re.search(r"(?<![a-z])flat(?![a-z])", near) or re.search(r"flat\s*(?:rate|interest)", t_nodates):
            raw["rate_type"] = "flat"
        elif re.search(r"reducing|diminishing|declining", near) or \
                re.search(r"(?:reducing|diminishing|declining)\s*(?:balance|rate|interest)", t_nodates):
            raw["rate_type"] = "reducing"

    # ── Tenure ───────────────────────────────────────────────────────────────
    for m in TENURE_RE.finditer(t_nodates):
        if _overlaps(m.span(), used):
            continue
        value = float(m.group("num"))
        months = value * 12 if m.group("unit").startswith(("y",)) else value
        raw["tenure_months"] = int(round(months))
        used.append(m.span())
        break
    if raw["tenure_months"] is None:
        m = TENURE_NO_UNIT_RE.search(t_nodates)
        if m:
            raw["tenure_months"] = int(m.group("num"))
            used.append(m.span())
            notes.append("Tenure unit not stated: assumed months.")

    amounts = [m for m in AMOUNT_RE.finditer(t_nodates)
               if m.group("num") and not _overlaps(m.span("num"), used)]

    # ── Processing fee ───────────────────────────────────────────────────────
    if fee_pct_match is not None:
        raw["processing_fee_pct"] = float(fee_pct_match.group("num"))
        used.append(fee_pct_match.span())
    else:
        for kw in _FEE_KW_RE.finditer(t_nodates):
            found = None
            for m in amounts:  # first number after the keyword (no other digits in between)
                if kw.end() <= m.start("num") <= kw.end() + 30 and not _gap_has_digit(t_nodates, kw.end(), m.start("num")):
                    found = m
                    break
            if found is None:
                for m in reversed(amounts):  # "Rs 2,000 processing fee"
                    if kw.start() - 25 <= m.end() <= kw.start() and _is_marked(m) \
                            and not _gap_has_digit(t_nodates, m.end(), kw.start()):
                        found = m
                        break
            if found is not None:
                raw["processing_fee"] = _amount_value(found)
                used.append(found.span())
                break

    # ── Stated EMI ───────────────────────────────────────────────────────────
    for kw in _EMI_KW_RE.finditer(t_nodates):
        found = None
        for m in amounts:
            if _overlaps(m.span(), used):
                continue
            if kw.end() <= m.start("num") <= kw.end() + 25 and not _gap_has_digit(t_nodates, kw.end(), m.start("num")):
                found = m
                break
        if found is None:
            for m in reversed(amounts):
                if _overlaps(m.span(), used):
                    continue
                if kw.start() - 15 <= m.end() <= kw.start() and _is_marked(m) \
                        and not _gap_has_digit(t_nodates, m.end(), kw.start()):
                    found = m
                    break
        if found is not None and _amount_value(found) >= 100:
            raw["emi"] = _amount_value(found)
            used.append(found.span())
            break

    # ── Principal: largest currency/unit-marked amount not used elsewhere ────
    candidates = [m for m in amounts if _is_marked(m) and not _overlaps(m.span(), used)]
    if not candidates:
        candidates = [m for m in amounts if not _overlaps(m.span(), used) and _amount_value(m) >= 1000
                      and _LOAN_CONTEXT_RE.search(t_nodates[max(0, m.start() - 30):m.end() + 30])]
    if candidates:
        best = max(candidates, key=_amount_value)
        raw["principal"] = _amount_value(best)

    return _finalise_terms(raw, notes)


def _norm_period(value) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    v = str(value).strip().lower().replace(".", "").replace("_", " ")
    if v in ("month", "monthly", "per month", "pm", "a month", "mo", "months", "p m"):
        return "month"
    if v in ("year", "yearly", "annual", "annually", "per annum", "pa", "per year", "a year", "years", "p a", "annum"):
        return "year"
    raise ValueError(f"rate_period must be 'month' or 'year' (got {value!r})")


def _norm_type(value) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    v = str(value).strip().lower()
    if v.startswith("flat"):
        return "flat"
    if v.startswith(("reducing", "diminishing", "declining")) or v == "reducing balance":
        return "reducing"
    raise ValueError(f"rate_type must be 'flat' or 'reducing' (got {value!r})")


def _finalise_terms(raw: dict, notes: list | None = None) -> dict:
    """Shared by the rules and LLM parsers: coerce, default, list missing fields."""
    notes = list(notes or [])
    terms = _empty_terms()

    def num(key):
        value = raw.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        try:
            return _to_float(value, key)
        except ValueError:
            notes.append(f"Ignored unreadable {key}: {value!r}.")
            return None

    terms["principal"] = num("principal")
    terms["rate_pct"] = num("rate_pct")
    tenure = num("tenure_months")
    if tenure is None and num("tenure_years") is not None:
        tenure = num("tenure_years") * 12
    terms["tenure_months"] = int(round(tenure)) if tenure is not None else None
    terms["emi"] = num("emi")

    try:
        terms["rate_period"] = _norm_period(raw.get("rate_period"))
    except ValueError:
        terms["rate_period"] = None
    if terms["rate_period"] is None and terms["rate_pct"] is not None:
        terms["rate_period"] = "year"
        if not any("period" in n for n in notes):
            notes.append("Rate period not stated: assumed per year.")

    try:
        terms["rate_type"] = _norm_type(raw.get("rate_type"))
    except ValueError:
        terms["rate_type"] = None
    if terms["rate_type"] is None:
        terms["rate_type"] = "reducing"
        notes.append("Rate type not stated: assumed reducing balance (say 'flat' if the lender quoted a flat rate).")

    fee, fee_pct = num("processing_fee"), num("processing_fee_pct")
    terms["processing_fee_pct"] = fee_pct
    if fee is None and fee_pct is not None and terms["principal"]:
        fee = round(terms["principal"] * fee_pct / 100.0, 2)
        notes.append(f"Processing fee {_fmt_pct(fee_pct)}% of {_inr(terms['principal'])} = {_inr(fee)}.")
    if fee is None:
        fee = 0.0
        notes.append("Processing fee not mentioned: assumed ₹0.")
    terms["processing_fee"] = fee

    for key in ("disbursal_date", "sanction_date"):
        value = raw.get(key)
        if value:
            try:
                terms[key] = parse_date(value).isoformat()
            except ValueError:
                notes.append(f"Ignored unreadable {key}: {value!r}.")
    if raw.get("lender_name"):
        terms["lender_name"] = str(raw["lender_name"]).strip()[:120]

    missing = [k for k in REQUIRED_OFFER_FIELDS if terms[k] is None]
    return {"terms": terms, "missing": missing, "assumptions": notes}


def _llm_prompt(text: str, language: str) -> str:
    lang_name = LANGUAGE_NAMES.get((language or "en").lower(), language or "English")
    return f"""You extract loan-offer terms for an Indian loan-verification tool.
The offer text below is in {lang_name}. It may mix Tamil, Hindi and English and may be a speech transcript.

Offer text:
\"\"\"{text}\"\"\"

Return ONLY a JSON object with exactly these keys:
{{
  "principal": number in rupees or null,
  "rate_pct": the interest rate exactly as quoted, in percent (2 for "2%"), or null,
  "rate_period": "month" or "year" or null,
  "rate_type": "flat" or "reducing" or null,
  "tenure_months": integer or null,
  "processing_fee": number in rupees or null,
  "processing_fee_pct": number (percent of the loan amount) or null,
  "emi": number in rupees or null,
  "disbursal_date": "YYYY-MM-DD" or null,
  "sanction_date": "YYYY-MM-DD" or null,
  "lender_name": string or null
}}

Rules:
- 1 lakh = 100000 and 1 crore = 10000000. Tamil: ஆயிரம் = thousand, லட்சம் = lakh, கோடி = crore.
  Hindi: हज़ार/हजार = thousand, लाख = lakh, करोड़ = crore.
- "% per month", "p.m.", "monthly", "மாதம்", "மாதத்திற்கு", "प्रति माह", "महीना" mean rate_period "month".
  "% per annum", "p.a.", "yearly", "a year", "ஆண்டுக்கு", "வருடத்திற்கு", "प्रति वर्ष", "सालाना" mean "year".
- rate_type is "flat" only if the text says flat (फ्लैट, பிளாட், flat); "reducing" only if it says
  reducing / diminishing balance; otherwise null.
- Convert a tenure given in years to months.
- Do not guess: use null for anything not stated. No text outside the JSON object."""


def _extract_json_object(content: str) -> dict:
    content = (content or "").strip()
    try:
        data = json.loads(content)
    except ValueError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("LLM did not return a JSON object") from None
        data = json.loads(match.group())
    if not isinstance(data, dict):
        raise ValueError("LLM JSON is not an object")
    return data


def parse_offer_llm(text: str, language: str, client, model: str) -> dict:
    """
    Parse an offer in Tamil / Hindi / English with the project's LLM wrapper
    (client.chat.completions.create(..., response_format={"type": "json_object"})).
    Raises on any failure so the caller can fall back to the rules parser.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _llm_prompt(text, language)}],
        response_format={"type": "json_object"},
    )
    data = _extract_json_object(response.choices[0].message.content)
    raw = {k: data.get(k) for k in _empty_terms()}
    if data.get("tenure_years") is not None and raw["tenure_months"] is None:
        raw["tenure_years"] = data["tenure_years"]
    return _finalise_terms(raw)


def parse_offer(text: str, language: str = "en", client_factory=None, model: str | None = None) -> dict:
    """
    Endpoint logic for /loan/parse-offer: use the LLM only if ANTHROPIC_API_KEY is set
    and the call succeeds; otherwise fall back to the rules parser.
    Adds parser = "llm" | "rules" (and llm_error when the LLM was tried and failed).
    """
    text = str(text or "").strip()
    if not text:
        raise ValueError("offer text is empty")
    llm_error = None
    if os.environ.get("ANTHROPIC_API_KEY") and client_factory is not None:
        try:
            result = parse_offer_llm(text, language, client_factory(), model or "")
            result.update(parser="llm", language=language)
            return result
        except Exception as exc:  # any LLM/network/JSON problem -> rules
            llm_error = f"{type(exc).__name__}: {exc}"[:300]
    result = parse_offer_rules(text)
    result.update(parser="rules", language=language)
    if llm_error:
        result["llm_error"] = llm_error
    return result


# ════════════════════════════════════════════════════════════════════════════
#  ACTUS client
# ════════════════════════════════════════════════════════════════════════════
def run_actus(contracts, url: str | None = None, attempts: int = 3,
              retry_delay: float = 1.0, timeout: float = 90.0) -> list:
    """POST {"contracts": [...], "riskFactors": []} to /eventsBatch, retrying on failure."""
    endpoint = f"{(url or actus_url()).rstrip('/')}/eventsBatch"
    payload = {"contracts": list(contracts), "riskFactors": []}
    last_error = "no attempt made"
    for attempt in range(1, max(1, attempts) + 1):
        try:
            response = httpx.post(endpoint, json=payload, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list):
                    raise ValueError("unexpected ACTUS response shape")
                return data
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < attempts and retry_delay:
            time.sleep(retry_delay)
    raise ActusUnavailable(f"ACTUS server unavailable after {attempts} attempts ({endpoint}): {last_error}")


def _result_id(result: dict) -> str:
    return str(result.get("contractID") or result.get("contractId") or "")


def _yf_30e360(d1: date, d2: date) -> float:
    day1, day2 = min(d1.day, 30), min(d2.day, 30)
    return (360 * (d2.year - d1.year) + 30 * (d2.month - d1.month) + (day2 - day1)) / 360.0


def _yf_a365(d1: date, d2: date) -> float:
    return (d2 - d1).days / 365.0


_YEAR_FRACTIONS = {"30E360": _yf_30e360, "A365": _yf_a365}


def local_annuity_events(contract: dict) -> list:
    """
    Local re-implementation of the ACTUS ANN events we use (IED, PR/MD, IP) for the
    fallback path: equal instalments that amortise the notional exactly to zero with
    the contract's day-count year fractions (this is what ACTUS computes).
    """
    year_fraction = _YEAR_FRACTIONS[contract.get("dayCountConvention", "30E360")]
    notional = float(contract["notionalPrincipal"])
    rate = float(contract["nominalInterestRate"])
    premium = float(contract.get("premiumDiscountAtIED") or 0.0)
    ied = parse_date(contract["initialExchangeDate"])
    anchor = parse_date(contract["cycleAnchorDateOfPrincipalRedemption"])
    maturity = parse_date(contract["maturityDate"])

    dates, k = [], 0
    while add_months(anchor, k) < maturity:
        dates.append(add_months(anchor, k))
        k += 1
    dates.append(maturity)

    prev = [ied] + dates[:-1]
    growth = [1.0 + rate * year_fraction(a, b) for a, b in zip(prev, dates)]
    product_all, denominator = 1.0, 0.0
    for g in growth:
        product_all *= g
    for i in range(len(growth)):
        tail = 1.0
        for g in growth[i + 1:]:
            tail *= g
        denominator += tail
    annuity = notional * product_all / denominator

    stamp = lambda d: f"{d.isoformat()}T00:00"  # noqa: E731 - ACTUS style timestamps
    events = [{"type": "IED", "time": stamp(ied), "payoff": -(notional + premium),
               "currency": contract.get("currency", "INR"), "nominalValue": notional}]
    balance, currency = notional, contract.get("currency", "INR")
    for index, (start, end) in enumerate(zip(prev, dates)):
        interest = balance * rate * year_fraction(start, end)
        last = index == len(dates) - 1
        principal = balance if last else annuity - interest
        balance = 0.0 if last else balance - principal
        events.append({"type": "MD" if last else "PR", "time": stamp(end), "payoff": principal,
                       "currency": currency, "nominalValue": balance})
        events.append({"type": "IP", "time": stamp(end), "payoff": interest,
                       "currency": currency, "nominalValue": balance})
    return events


def schedule_from_events(events: list) -> tuple[float, list]:
    """
    Turn ACTUS events into (net_disbursed, rows). Rows are one per payment date:
    interest = IP, principal = PR + MD, emi = their sum, balance = notional after the date.
    """
    net = 0.0
    by_date: dict[str, dict] = {}
    for event in events:
        kind = event.get("type")
        payoff = float(event.get("payoff") or 0.0)
        if kind == "IED":
            net += -payoff
            continue
        if kind not in ("IP", "PR", "MD"):
            continue  # PRF (annuity fixing) etc. carry no cash
        day = str(event.get("time", ""))[:10]
        row = by_date.setdefault(day, {"date": day, "interest": 0.0, "principal": 0.0, "balance": None})
        if kind == "IP":
            row["interest"] += payoff
        else:
            row["principal"] += payoff
        if event.get("nominalValue") is not None:
            value = abs(float(event["nominalValue"]))
            row["balance"] = value if row["balance"] is None else min(row["balance"], value)
    rows = [by_date[d] for d in sorted(by_date)]
    for row in rows:
        row["emi"] = row["interest"] + row["principal"]
    return net, rows


# ════════════════════════════════════════════════════════════════════════════
#  Offer check
# ════════════════════════════════════════════════════════════════════════════
def normalize_offer_terms(terms: dict) -> dict:
    if not isinstance(terms, dict):
        raise ValueError("terms must be an object")
    principal = _to_float(terms.get("principal"), "principal")
    if principal <= 0:
        raise ValueError("principal must be positive")
    rate_pct = _to_float(terms.get("rate_pct", terms.get("rate")), "rate_pct")
    if not 0 <= rate_pct <= 100:
        raise ValueError("rate_pct must be between 0 and 100")
    rate_period = _norm_period(terms.get("rate_period")) or "year"
    rate_type = _norm_type(terms.get("rate_type")) or "reducing"
    tenure_raw = _to_float(terms.get("tenure_months"), "tenure_months")
    tenure = int(round(tenure_raw))
    if not 1 <= tenure <= 600:
        raise ValueError("tenure_months must be between 1 and 600")

    fee_value = terms.get("processing_fee")
    if (fee_value is None or fee_value == "") and terms.get("processing_fee_pct") not in (None, ""):
        fee = principal * _to_float(terms["processing_fee_pct"], "processing_fee_pct") / 100.0
    else:
        fee = 0.0 if fee_value in (None, "") else _to_float(fee_value, "processing_fee")
    if fee < 0 or fee >= principal:
        raise ValueError("processing_fee must be at least 0 and less than the principal")

    emi = terms.get("emi")
    emi = None if emi in (None, "") else _to_float(emi, "emi")
    if emi is not None and emi <= 0:
        raise ValueError("emi must be positive")

    disbursal = parse_date(terms["disbursal_date"]) if terms.get("disbursal_date") else date.today() + timedelta(days=1)
    sanction = parse_date(terms["sanction_date"]) if terms.get("sanction_date") else None
    if sanction and sanction > disbursal:
        raise ValueError("sanction_date cannot be after disbursal_date")

    return {
        "principal": principal, "rate_pct": rate_pct, "rate_period": rate_period,
        "rate_type": rate_type, "tenure_months": tenure, "processing_fee": round(fee, 2),
        "emi": emi, "disbursal_date": disbursal, "sanction_date": sanction,
        "lender_name": (str(terms.get("lender_name")).strip()[:120] if terms.get("lender_name") else None),
    }


def advertised_rate_text(rate_pct: float, rate_period: str, rate_type: str) -> str:
    if rate_period == "month":
        return f"{_fmt_pct(rate_pct)}% per month {rate_type} ≈ {_fmt_pct(rate_pct * 12)}% a year"
    return f"{_fmt_pct(rate_pct)}% a year {rate_type}"


def build_offer_contract(norm: dict, annual_rate: float) -> dict:
    """ACTUS ANN at the equivalent reducing rate (30E360), fee as premiumDiscountAtIED."""
    disbursal = norm["disbursal_date"]
    first_payment = add_months(disbursal, 1)
    maturity = add_months(first_payment, norm["tenure_months"] - 1)
    status_date = disbursal - timedelta(days=1)
    fee = norm["processing_fee"]
    return {
        "contractType": "ANN",
        "contractID": f"TT-OFFER-{disbursal:%Y%m%d}",
        "contractRole": "RPA",
        "statusDate": _iso_dt(status_date),
        "contractDealDate": _iso_dt(norm["sanction_date"] or status_date),
        "initialExchangeDate": _iso_dt(disbursal),
        "maturityDate": _iso_dt(maturity),
        "notionalPrincipal": norm["principal"],
        "nominalInterestRate": annual_rate,
        "currency": "INR",
        "dayCountConvention": "30E360",
        "cycleAnchorDateOfInterestPayment": _iso_dt(first_payment),
        "cycleOfInterestPayment": "P1ML0",
        "cycleAnchorDateOfPrincipalRedemption": _iso_dt(first_payment),
        "cycleOfPrincipalRedemption": "P1ML0",
        "premiumDiscountAtIED": -fee if fee else 0,
        "calendar": "NC",
        "businessDayConvention": "NOS",
        "endOfMonthConvention": "SD",
    }


def check_offer(terms: dict, url: str | None = None, use_actus: bool = True, attempts: int = 3,
                retry_delay: float = 1.0, timeout: float = 30.0, runner=None) -> dict:
    """
    Compute the lender EMI (flat / reducing / stated), the equivalent reducing rate
    (12 x IRR without fees) and the APR (with fees); run the loan on ACTUS as an ANN
    and derive the schedule and the APR from the ACTUS cash flows. Falls back to a
    local computation (engine = "local-fallback") if ACTUS is unreachable.
    """
    norm = normalize_offer_terms(terms)
    principal, n = norm["principal"], norm["tenure_months"]
    advertised_annual = norm["rate_pct"] * (12 if norm["rate_period"] == "month" else 1)
    annual_rate = advertised_annual / 100.0

    if norm["emi"] is not None:
        lender_emi, emi_basis = norm["emi"], "stated"
    elif norm["rate_type"] == "flat":
        lender_emi, emi_basis = flat_emi(principal, annual_rate, n), "flat"
    else:
        lender_emi, emi_basis = reducing_emi(principal, annual_rate, n), "reducing"
    equivalent_rate = 12 * monthly_irr(principal, [lender_emi] * n)

    contract = build_offer_contract(norm, equivalent_rate)
    base_url = (url or actus_url()).rstrip("/")
    runner = runner or run_actus
    events, engine_note = None, None
    if use_actus:
        try:
            result = runner([contract], url=base_url, attempts=attempts, retry_delay=retry_delay, timeout=timeout)[0]
            if str(result.get("status", "")).lower() != "success":
                raise ActusUnavailable(f"ACTUS rejected the contract: {result.get('message') or 'unknown error'}")
            actus_events = result.get("events") or []
            if not any(e.get("type") == "IED" for e in actus_events):
                raise ActusUnavailable("ACTUS returned no IED event")
            events = actus_events
        except Exception as exc:
            engine_note = str(exc)
    else:
        engine_note = "ACTUS call skipped: local engine requested."
    engine = "ACTUS" if events is not None else "local-fallback"
    if events is None:
        events = local_annuity_events(contract)

    net, rows = schedule_from_events(events)
    payments = [row["emi"] for row in rows]
    apr = apr_from_cashflows([-net] + payments)
    total_payable = sum(payments)
    total_interest = sum(row["interest"] for row in rows)
    fees = principal - net

    schedule, opening = [], principal
    for number, row in enumerate(rows, start=1):
        balance = row["balance"] if row["balance"] is not None else max(opening - row["principal"], 0.0)
        schedule.append({
            "n": number, "date": row["date"], "opening_balance": round(opening, 2),
            "emi": round(row["emi"], 2), "interest": round(row["interest"], 2),
            "principal": round(row["principal"], 2), "balance": round(balance, 2),
        })
        opening = balance

    return {
        "engine": engine,
        "engine_note": engine_note,
        "actus_url": base_url if engine == "ACTUS" else None,
        "terms": {**norm, "disbursal_date": norm["disbursal_date"].isoformat(),
                  "sanction_date": norm["sanction_date"].isoformat() if norm["sanction_date"] else None},
        "principal": principal,
        "tenure_months": n,
        "rate_pct": norm["rate_pct"],
        "rate_period": norm["rate_period"],
        "rate_type": norm["rate_type"],
        "advertised_rate_text": advertised_rate_text(norm["rate_pct"], norm["rate_period"], norm["rate_type"]),
        "advertised_annual_rate_pct": round(advertised_annual, 4),
        "emi_basis": emi_basis,
        "lender_emi": round(lender_emi, 2),
        "emi": round(payments[0], 2) if payments else None,
        "equivalent_reducing_rate": equivalent_rate,
        "equivalent_reducing_rate_pct": round(equivalent_rate * 100, 2),
        "apr": apr,
        "apr_pct": round(apr * 100, 2),
        "apr_method": "RBI KFS: APR = monthly IRR of net disbursal vs instalments x 12 (no compounding)",
        "fees": round(fees, 2),
        "net_disbursed": round(net, 2),
        "total_payable": round(total_payable, 2),
        "total_interest": round(total_interest, 2),
        "total_cost_of_credit": round(total_interest + fees, 2),
        "disbursal_date": norm["disbursal_date"].isoformat(),
        "sanction_date": norm["sanction_date"].isoformat() if norm["sanction_date"] else None,
        "first_emi_date": schedule[0]["date"] if schedule else None,
        "maturity_date": schedule[-1]["date"] if schedule else None,
        "actus_contract": contract,
        "schedule": schedule,
    }


# ════════════════════════════════════════════════════════════════════════════
#  Loan-book check (RBI 29 Apr 2024 circular patterns)
# ════════════════════════════════════════════════════════════════════════════
def read_loan_book_csv(text: str) -> list[dict]:
    """Parse CSV text (UTF-8, BOM tolerated) and validate the header."""
    text = str(text or "").lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in BOOK_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(missing)}. Expected: {', '.join(BOOK_COLUMNS)}")
    rows = []
    for row in reader:
        clean = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k is not None}
        if any(clean.get(c) for c in BOOK_COLUMNS):
            rows.append(clean)
    return rows


def normalize_book_row(row: dict) -> dict:
    loan_id = str(row.get("loan_id") or "").strip()
    if not loan_id:
        raise ValueError("loan_id is missing")
    principal = _to_float(row.get("principal"), "principal")
    rate_pct = _to_float(row.get("annual_rate_pct"), "annual_rate_pct")
    tenure = int(round(_to_float(row.get("tenure_months"), "tenure_months")))
    sanction = parse_date(row.get("sanction_date"))
    disbursal = parse_date(row.get("disbursal_date"))
    first_emi = parse_date(row.get("first_emi_date"))
    advance_raw = row.get("advance_emis")
    advance = 0 if advance_raw in (None, "") else int(round(_to_float(advance_raw, "advance_emis")))
    emi_raw = row.get("emi_charged")
    emi = 0.0 if emi_raw in (None, "") else _to_float(emi_raw, "emi_charged")
    charged = _to_float(row.get("first_interest_charged"), "first_interest_charged")

    if principal <= 0:
        raise ValueError("principal must be positive")
    if not 0 <= rate_pct <= 100:
        raise ValueError("annual_rate_pct must be between 0 and 100")
    if tenure < 1:
        raise ValueError("tenure_months must be at least 1")
    if first_emi <= disbursal:
        raise ValueError("first_emi_date must be after disbursal_date")
    if sanction > disbursal:
        raise ValueError("sanction_date is after disbursal_date")
    if advance < 0 or advance >= tenure:
        raise ValueError("advance_emis must be between 0 and tenure_months - 1")
    if advance and emi <= 0:
        raise ValueError("emi_charged is required when advance EMIs were collected")
    notional = principal - advance * emi
    if notional <= 0:
        raise ValueError("advance EMIs exceed the principal")

    return {
        "loan_id": loan_id, "segment": str(row.get("segment") or "").strip(),
        "principal": principal, "rate_pct": rate_pct, "rate": rate_pct / 100.0, "tenure": tenure,
        "sanction": sanction, "disbursal": disbursal, "first_emi": first_emi,
        "advance": advance, "emi": emi, "charged": charged,
        "notional": round(notional, 2), "n_remaining": tenure - advance,
        "days_first": (first_emi - disbursal).days, "gap_days": (disbursal - sanction).days,
    }


def book_contract(norm: dict, contract_id: str) -> dict:
    """ACTUS ANN for one book loan: A365, interest from the disbursal date."""
    maturity = add_months(norm["first_emi"], norm["n_remaining"] - 1)
    return {
        "contractType": "ANN",
        "contractID": contract_id,
        "contractRole": "RPA",
        "statusDate": _iso_dt(norm["disbursal"] - timedelta(days=1)),
        "contractDealDate": _iso_dt(norm["sanction"]),
        "initialExchangeDate": _iso_dt(norm["disbursal"]),
        "maturityDate": _iso_dt(maturity),
        "notionalPrincipal": norm["notional"],
        "nominalInterestRate": norm["rate"],
        "currency": "INR",
        "dayCountConvention": "A365",
        "cycleAnchorDateOfInterestPayment": _iso_dt(norm["first_emi"]),
        "cycleOfInterestPayment": "P1ML0",
        "cycleAnchorDateOfPrincipalRedemption": _iso_dt(norm["first_emi"]),
        "cycleOfPrincipalRedemption": "P1ML0",
        "premiumDiscountAtIED": 0,
        "calendar": "NC",
        "businessDayConvention": "NOS",
        "endOfMonthConvention": "SD",
    }


def _loan_base(norm: dict | None, loan_id: str, row: dict) -> dict:
    return {
        "loan_id": loan_id,
        "segment": (norm or {}).get("segment") or str(row.get("segment") or ""),
        "principal": (norm or {}).get("principal"),
        "disbursal_date": norm["disbursal"].isoformat() if norm else row.get("disbursal_date"),
        "sanction_date": norm["sanction"].isoformat() if norm else row.get("sanction_date"),
        "first_emi_date": norm["first_emi"].isoformat() if norm else row.get("first_emi_date"),
        "advance_emis": (norm or {}).get("advance"),
        "status": None, "pattern": None, "charged": None, "correct": None, "excess": None,
        "explanation": "", "engine": None,
    }


def expected_excesses(norm: dict, correct: float) -> dict:
    """
    Overcharge each RBI-circular pattern would produce for this loan:
      sanction_date_interest     principal x r x (disbursal - sanction days) / 365
      full_month_interest        principal x r / 12 - correct   (first period < 1 month, no advance EMI)
      advance_emi_full_principal advance_emis x EMI x r x days(disbursal -> first EMI) / 365
    """
    candidates = {}
    if norm["gap_days"] > 0:
        candidates["sanction_date_interest"] = norm["principal"] * norm["rate"] * norm["gap_days"] / 365.0
    if norm["advance"] == 0 and norm["first_emi"] < add_months(norm["disbursal"], 1):
        candidates["full_month_interest"] = norm["principal"] * norm["rate"] / 12.0 - correct
    if norm["advance"] > 0:
        candidates["advance_emi_full_principal"] = (norm["advance"] * norm["emi"] * norm["rate"]
                                                    * norm["days_first"] / 365.0)
    return candidates


def classify_first_interest(norm: dict, correct: float) -> tuple[str, str | None, float, str]:
    """
    Compare the lender's first-period interest with the ACTUS figure.
    OK when |diff| <= max(Rs 1, 0.5% of correct); otherwise the closest expected excess
    (within Rs 1) names the pattern, else "unexplained".
    Returns (status, pattern, excess, explanation).
    """
    charged = norm["charged"]
    diff = charged - correct
    tolerance = max(1.0, 0.005 * abs(correct))
    if abs(diff) <= tolerance:
        return "ok", None, diff, f"Matches the ACTUS-computed first-period interest ({_inr(correct)})."

    days = norm["days_first"]
    candidates = expected_excesses(norm, correct)
    pattern = "unexplained"
    if candidates:
        best = min(candidates, key=lambda key: abs(diff - candidates[key]))
        if abs(diff - candidates[best]) <= 1.0:
            pattern = best

    if pattern == "sanction_date_interest":
        gap = norm["gap_days"]
        text = (f"Interest charged from the sanction date ({norm['sanction'].isoformat()}) instead of the "
                f"disbursal date ({norm['disbursal'].isoformat()}): {gap} extra day{'s' if gap != 1 else ''}, "
                f"{_inr(diff)} overcharged.")
    elif pattern == "full_month_interest":
        text = (f"Full month's interest ({_inr(charged)}) charged for a first period of only {days} days; "
                f"interest from the disbursal date is {_inr(correct)} ({_inr(diff)} overcharged).")
    elif pattern == "advance_emi_full_principal":
        count = norm["advance"]
        text = (f"{count} EMI{'s' if count != 1 else ''} of {_inr(norm['emi'])} collected in advance, but interest "
                f"charged on the full principal {_inr(norm['principal'])} instead of the {_inr(norm['notional'])} "
                f"actually outstanding ({_inr(diff)} overcharged).")
    else:
        direction = "more" if diff > 0 else "less"
        text = (f"Charged {_inr(abs(diff))} {direction} than the ACTUS-computed {_inr(correct)}; "
                f"does not match a known RBI-circular pattern.")
    return "flagged", pattern, diff, text


def check_loan_book(rows, url: str | None = None, use_actus: bool = True, chunk_size: int = BOOK_CHUNK_SIZE,
                    attempts: int = 3, retry_delay: float = 1.0, timeout: float = 120.0,
                    runner=None, max_workers: int = 4) -> dict:
    """
    Check every loan's first-period interest against ACTUS (A365, interest from the
    disbursal date), sending chunks of `chunk_size` contracts per /eventsBatch call.
    """
    started = time.perf_counter()
    rows = list(rows)
    base_url = (url or actus_url()).rstrip("/")
    runner = runner or run_actus
    loans: list[dict | None] = [None] * len(rows)

    prepared, seen_ids = [], {}
    for index, row in enumerate(rows):
        loan_id = str(row.get("loan_id") or "").strip() or f"row-{index + 1}"
        try:
            norm = normalize_book_row(row)
        except (ValueError, TypeError) as exc:
            result = _loan_base(None, loan_id, row)
            result.update(status="error", explanation=f"Invalid row: {exc}")
            loans[index] = result
            continue
        seen_ids[loan_id] = seen_ids.get(loan_id, 0) + 1
        contract_id = loan_id if seen_ids[loan_id] == 1 else f"{loan_id}#{seen_ids[loan_id]}"
        prepared.append((index, norm, book_contract(norm, contract_id)))

    chunks = [prepared[i:i + chunk_size] for i in range(0, len(prepared), max(1, chunk_size))]

    def evaluate(chunk):
        if not use_actus:
            return "local-fallback", None, "ACTUS call skipped: local engine requested."
        try:
            results = runner([c for _, _, c in chunk], url=base_url, attempts=attempts,
                             retry_delay=retry_delay, timeout=timeout)
            return "ACTUS", results, None
        except Exception as exc:
            return "local-fallback", None, str(exc)

    outcomes = []
    if chunks:
        with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(chunks)))) as pool:
            outcomes = list(pool.map(evaluate, chunks))

    engines, notes, actus_calls = set(), [], 0
    for chunk, (engine, results, note) in zip(chunks, outcomes):
        engines.add(engine)
        if note and note not in notes:
            notes.append(note)
        by_id = {}
        if engine == "ACTUS":
            actus_calls += 1
            by_id = {_result_id(r): r for r in results if isinstance(r, dict)}
        for position, (index, norm, contract) in enumerate(chunk):
            result = _loan_base(norm, norm["loan_id"], rows[index])
            result["engine"] = engine
            if engine == "ACTUS":
                actus = by_id.get(contract["contractID"])
                if actus is None and position < len(results) and isinstance(results[position], dict):
                    actus = results[position]
                if actus is None:
                    result.update(status="error", explanation="ACTUS returned no result for this loan.")
                    loans[index] = result
                    continue
                if str(actus.get("status", "")).lower() != "success":
                    result.update(status="error",
                                  explanation=f"ACTUS rejected the contract: {actus.get('message') or 'unknown error'}")
                    loans[index] = result
                    continue
                first_ip = next((e for e in actus.get("events") or [] if e.get("type") == "IP"), None)
                if first_ip is None:
                    result.update(status="error", explanation="ACTUS returned no interest payment (IP) event.")
                    loans[index] = result
                    continue
                correct = float(first_ip.get("payoff") or 0.0)
            else:
                correct = norm["notional"] * norm["rate"] * norm["days_first"] / 365.0
            status, pattern, excess, text = classify_first_interest(norm, correct)
            result.update(status=status, pattern=pattern, charged=round(norm["charged"], 2),
                          correct=round(correct, 2), excess=round(excess, 2), explanation=text)
            loans[index] = result

    by_pattern = {p: {"count": 0, "amount": 0.0, "label": PATTERN_LABELS[p]} for p in PATTERNS}
    ok = flagged = errors = 0
    total_excess = 0.0
    for loan in loans:
        if loan["status"] == "ok":
            ok += 1
        elif loan["status"] == "flagged":
            flagged += 1
            total_excess += loan["excess"]
            by_pattern[loan["pattern"]]["count"] += 1
            by_pattern[loan["pattern"]]["amount"] += loan["excess"]
        else:
            errors += 1
    for bucket in by_pattern.values():
        bucket["amount"] = round(bucket["amount"], 2)

    if engines == {"ACTUS"}:
        engine = "ACTUS"
    elif engines == {"local-fallback"}:
        engine = "local-fallback"
    elif engines:
        engine = "mixed"
    else:
        engine = "none"

    return {
        "summary": {
            "loans_checked": len(rows), "ok": ok, "flagged": flagged, "errors": errors,
            "total_excess": round(total_excess, 2), "by_pattern": by_pattern,
            "engine": engine, "engine_note": "; ".join(notes) or None,
            "actus_url": base_url if "ACTUS" in engines else None,
            "actus_calls": actus_calls, "chunk_size": chunk_size,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        },
        "loans": loans,
    }


# ════════════════════════════════════════════════════════════════════════════
#  KFS — Key Facts Statement (illustrative, RBI format)
# ════════════════════════════════════════════════════════════════════════════
def _long_date(iso: str | None) -> str:
    if not iso:
        return "—"
    return parse_date(iso).strftime("%d %b %Y")


def _ordinal(day: int) -> str:
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


_KFS_CSS = """
@page { size: A4; margin: 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, Helvetica, sans-serif; color: #111827; margin: 0; background: #f3f4f6; font-size: 12.5px; line-height: 1.45; }
.sheet { max-width: 210mm; margin: 16px auto; background: #ffffff; padding: 14mm 12mm; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
h1 { font-size: 20px; margin: 0 0 2px; letter-spacing: -.2px; }
h2 { font-size: 14px; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #1e3a8a; color: #1e3a8a; }
.sub { color: #4b5563; margin: 0 0 12px; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 12px; color: #374151; margin-bottom: 6px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; }
.badge.actus { background: #dcfce7; color: #166534; }
.badge.local { background: #fef3c7; color: #92400e; }
.apr-box { display: flex; gap: 12px; margin: 12px 0 4px; }
.apr-box div { flex: 1; border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 12px; }
.apr-box .label { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #6b7280; }
.apr-box .value { font-size: 20px; font-weight: 800; }
.apr-box .true .value { color: #b91c1c; }
table { width: 100%; border-collapse: collapse; margin-top: 4px; }
th, td { border: 1px solid #d1d5db; padding: 5px 7px; text-align: left; vertical-align: top; }
th { background: #eef2ff; font-weight: 700; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
td.sl { width: 34px; text-align: center; color: #4b5563; }
tr.total td { font-weight: 700; background: #f9fafb; }
.note { font-size: 11px; color: #4b5563; margin-top: 6px; }
.footer { margin-top: 22px; padding-top: 8px; border-top: 1px solid #d1d5db; font-size: 11px; color: #4b5563; }
.toolbar { max-width: 210mm; margin: 12px auto 0; text-align: right; }
.toolbar button { font: inherit; padding: 7px 14px; border-radius: 6px; border: 1px solid #1e3a8a; background: #1e3a8a; color: #fff; cursor: pointer; }
@media print {
  body { background: #fff; }
  .sheet { box-shadow: none; margin: 0; padding: 0; max-width: none; }
  .no-print { display: none !important; }
  h2 { break-after: avoid; }
  tr { break-inside: avoid; }
  thead { display: table-header-group; }
}
"""


def build_kfs_html(offer_result: dict, lender_name: str | None = None) -> str:
    """Self-contained, printable A4 KFS: Part 1, Annex B (APR computation), Annex C (schedule)."""
    r = offer_result
    esc = _html.escape
    lender_value = lender_name or (r.get("terms") or {}).get("lender_name")
    lender = esc(str(lender_value)) if lender_value else "Not stated"
    schedule = r.get("schedule") or []
    n = len(schedule)
    emi = r.get("emi") or 0.0
    first_date = r.get("first_emi_date")
    due_day = _ordinal(parse_date(first_date).day) if first_date else "—"
    fees, principal = r.get("fees") or 0.0, r.get("principal") or 0.0
    is_actus = r.get("engine") == "ACTUS"
    engine_badge = ('<span class="badge actus">Computed by ACTUS engine</span>' if is_actus
                    else '<span class="badge local">Local fallback (ACTUS unreachable)</span>')
    rate_text = esc(r.get("advertised_rate_text") or "")
    eq_rate = f"{r.get('equivalent_reducing_rate_pct', 0):.2f}%"
    apr = f"{r.get('apr_pct', 0):.2f}%"
    today = date.today().strftime("%d %b %Y")

    def money(value):
        return f"₹{format_inr(value or 0.0)}"

    part1 = [
        ("1", "Loan amount (sanctioned)", money(principal)),
        ("2", "Loan term", f"{r.get('tenure_months')} months"),
        ("3", "Instalment details",
         f"Type: Equated Monthly Instalments (EMI)<br>Number of EMIs: {n}<br>EMI amount: {money(emi)}"
         f"<br>Commencement of repayment: {_long_date(first_date)}"),
        ("4", "Interest rate (%) and type",
         f"As advertised: {rate_text} (fixed)<br>Equivalent reducing-balance rate: {eq_rate} a year"),
        ("5", "Fees / charges", f"Processing fee: {money(fees)} (payable to the lender, deducted at disbursal)"),
        ("6", "Annual Percentage Rate (APR)", f"<strong>{apr}</strong>"),
    ]
    annex_b = [
        ("1", "Sanctioned loan amount", money(principal)),
        ("2", "Loan term / number and amount of EMIs",
         f"{r.get('tenure_months')} months; {n} monthly EMIs of {money(emi)}; first EMI on {_long_date(first_date)}"),
        ("3", "Interest rate type", "Fixed"),
        ("4", "Rate of interest", f"{rate_text}; equivalent reducing-balance rate {eq_rate} a year"),
        ("5", "Total interest amount to be charged during the entire tenor", money(r.get("total_interest"))),
        ("6", "Fee / charges payable (processing fee)", money(fees)),
        ("7", "Net disbursed amount (1 &minus; 6)", money(r.get("net_disbursed"))),
        ("8", "Total amount to be paid by the borrower (1 + 5)", money(principal + (r.get("total_interest") or 0.0))),
        ("9", "Annual Percentage Rate: effective annualised interest rate, computed on the net disbursed amount "
              "using the IRR approach and reducing balance method (monthly IRR &times; 12)", f"<strong>{apr}</strong>"),
        ("10", "Schedule of disbursement", f"Single disbursal on {_long_date(r.get('disbursal_date'))}"),
        ("11", "Due date of payment of instalment and interest", f"{due_day} of every month from {_long_date(first_date)}"),
        ("", "Total cost of credit (interest + fees)", money(r.get("total_cost_of_credit"))),
    ]

    def kv_rows(items):
        return "\n".join(f'<tr><td class="sl">{esc(sl)}</td><td>{label}</td><td>{value}</td></tr>'
                         for sl, label, value in items)

    sched_rows = "\n".join(
        f'<tr class="sched-row"><td class="sl">{row["n"]}</td><td>{_long_date(row["date"])}</td>'
        f'<td class="num">{format_inr(row["opening_balance"])}</td><td class="num">{format_inr(row["principal"])}</td>'
        f'<td class="num">{format_inr(row["interest"])}</td><td class="num">{format_inr(row["emi"])}</td>'
        f'<td class="num">{format_inr(row["balance"])}</td></tr>'
        for row in schedule)
    # Totals from the unrounded engine figures (summing rounded rows can drift by a few paise).
    totals = (f'<tr class="total"><td></td><td>Total</td><td></td>'
              f'<td class="num">{format_inr(principal)}</td>'
              f'<td class="num">{format_inr(r.get("total_interest") or 0.0)}</td>'
              f'<td class="num">{format_inr(r.get("total_payable") or 0.0)}</td><td></td></tr>')

    footer = ("Computed with the ACTUS open-standard engine. Illustrative, not legal advice." if is_actus else
              "Computed locally with the same ACTUS ANN conventions because the ACTUS engine was unreachable. "
              "Illustrative, not legal advice.")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Key Facts Statement (illustrative)</title>
<style>{_KFS_CSS}</style>
</head>
<body>
<div class="toolbar no-print"><button type="button" onclick="window.print()">Print / Save as PDF</button></div>
<div class="sheet">
  <h1>Key Facts Statement (illustrative, RBI format)</h1>
  <p class="sub">Format of the RBI directions on Key Facts Statement for loans &amp; advances (effective 1 October 2024).</p>
  <div class="meta">
    <span><strong>Lender:</strong> {lender}</span>
    <span><strong>Prepared:</strong> {today}</span>
    <span><strong>Loan type:</strong> Retail / MSME term loan (EMI)</span>
    <span>{engine_badge}</span>
  </div>
  <div class="apr-box">
    <div><div class="label">Advertised rate</div><div class="value">{rate_text}</div></div>
    <div class="true"><div class="label">Annual Percentage Rate (APR)</div><div class="value">{apr}</div></div>
  </div>

  <h2>Part 1 &mdash; Interest rate and fees / charges</h2>
  <table><thead><tr><th>Sl.</th><th>Parameter</th><th>Details</th></tr></thead>
  <tbody>
{kv_rows(part1)}
  </tbody></table>

  <h2>Annex B &mdash; Illustration for computation of APR</h2>
  <table><thead><tr><th>Sl.</th><th>Parameter</th><th>Details</th></tr></thead>
  <tbody>
{kv_rows(annex_b)}
  </tbody></table>
  <p class="note">APR follows the RBI convention: the monthly internal rate of return of the net disbursed amount against the
  instalments, multiplied by 12 (no compounding).</p>

  <h2>Annex C &mdash; Repayment schedule</h2>
  <table><thead><tr><th>No.</th><th>Due date</th><th class="num">Outstanding principal (₹)</th>
  <th class="num">Principal (₹)</th><th class="num">Interest (₹)</th><th class="num">Instalment (₹)</th>
  <th class="num">Balance after (₹)</th></tr></thead>
  <tbody>
{sched_rows}
{totals}
  </tbody></table>

  <div class="footer">{footer}</div>
</div>
</body>
</html>
"""
