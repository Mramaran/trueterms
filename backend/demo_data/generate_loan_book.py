"""
Deterministic generator for the TrueTerms demo loan book
=======================================================

    python backend/demo_data/generate_loan_book.py                  # writes demo_loan_book.csv
    python backend/demo_data/generate_loan_book.py --spot-check 12  # ...and compares with live ACTUS

500 retail / MSME loans disbursed in 2026: Rs 50,000 to Rs 25,00,000, 9-24% p.a. reducing,
12-84 months. Sanction is 1-15 days before disbursal; the first EMI falls on a fixed day
(the 5th) of the following month.

Correct loans charge exactly what ACTUS computes for the first period (A365, interest from
the disbursal date, rounded to paise). 40 correct loans collect one EMI in advance.
Exactly 35 errors are seeded, following the RBI circular of 29 Apr 2024:
  18 x sanction_date_interest      interest charged from the sanction date
  10 x full_month_interest         full month's interest for a first period under 30 days
   7 x advance_emi_full_principal  advance EMI collected, interest on the full principal

Fixed random seed, so the CSV is reproducible (tests regenerate it and compare bytes).
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

import loan_truth as lt  # noqa: E402  (needs the backend folder on sys.path)

SEED = 20240429                 # date of the RBI circular
N_LOANS = 500
EMI_DAY = 5                     # every first EMI is on the 5th of the following month
N_CORRECT_ADVANCE = 40
SEEDED = {"advance_emi_full_principal": 7, "full_month_interest": 10, "sanction_date_interest": 18}
MIN_SEEDED_EXCESS = 50.0        # every seeded error is clearly visible (>= Rs 50)
MIN_PATTERN_MARGIN = 5.0        # other patterns' expected excess must be >= Rs 5 away
FIRST_DISBURSAL = date(2026, 1, 16)   # sanction (up to 15 days earlier) stays in 2026
LAST_DISBURSAL = date(2026, 11, 25)   # first EMI (5 Dec at the latest) stays in 2026
TENURES = (12, 18, 24, 36, 48, 60, 72, 84)
OUT_CSV = HERE / "demo_loan_book.csv"


def _first_emi(disbursal: date) -> date:
    year, month = (disbursal.year + 1, 1) if disbursal.month == 12 else (disbursal.year, disbursal.month + 1)
    return date(year, month, EMI_DAY)


def _emi(principal: float, rate: float, tenure: int, advance: int) -> float:
    """
    Standard reducing EMI. With advance EMIs the borrower pays `advance` EMIs at
    disbursal and the rest monthly, so principal = advance*EMI + EMI*annuity_factor,
    i.e. the EMI is the standard reducing EMI of the notional left after the advance.
    """
    if advance == 0:
        return round(lt.reducing_emi(principal, rate, tenure), 2)
    per_rupee = lt.reducing_emi(1.0, rate, tenure - advance)
    return round(principal / (advance + 1.0 / per_rupee), 2)


def _draw_loan(rng: random.Random, number: int) -> dict:
    segment = "MSME" if rng.random() < 0.3 else "Retail"
    if segment == "Retail":
        principal = rng.randrange(50_000, 1_000_001, 5_000)
        rate_pct = rng.randrange(1050, 2401, 25) / 100        # 10.50% .. 24.00%
        tenure = rng.choice(TENURES[:6])                       # 12 .. 60 months
    else:
        principal = rng.randrange(500_000, 2_500_001, 25_000)
        rate_pct = rng.randrange(900, 1801, 25) / 100         # 9.00% .. 18.00%
        tenure = rng.choice(TENURES)                           # 12 .. 84 months
    disbursal = FIRST_DISBURSAL + timedelta(days=rng.randrange((LAST_DISBURSAL - FIRST_DISBURSAL).days + 1))
    return {
        "loan_id": f"LN-2026-{number:04d}", "segment": segment, "principal": principal,
        "rate_pct": rate_pct, "tenure": tenure, "disbursal": disbursal,
        "sanction": disbursal - timedelta(days=rng.randint(1, 15)),
        "first_emi": _first_emi(disbursal), "advance": 0,
    }


def _to_row(loan: dict, charged: float | None = None) -> dict:
    """CSV row (all strings). Without `charged`, the first interest is the correct ACTUS figure."""
    emi = _emi(loan["principal"], loan["rate_pct"] / 100, loan["tenure"], loan["advance"])
    row = {
        "loan_id": loan["loan_id"], "segment": loan["segment"], "principal": str(loan["principal"]),
        "annual_rate_pct": f"{loan['rate_pct']:.2f}", "tenure_months": str(loan["tenure"]),
        "sanction_date": loan["sanction"].isoformat(), "disbursal_date": loan["disbursal"].isoformat(),
        "first_emi_date": loan["first_emi"].isoformat(), "advance_emis": str(loan["advance"]),
        "emi_charged": f"{emi:.2f}", "first_interest_charged": "0.00",
    }
    if charged is None:
        charged = round(_correct_interest(row), 2)
    row["first_interest_charged"] = f"{charged:.2f}"
    return row


def _correct_interest(row: dict) -> float:
    """What ACTUS computes for the first IP event: notional x r x days / 365 (A365)."""
    norm = lt.normalize_book_row(row)
    return norm["notional"] * norm["rate"] * norm["days_first"] / 365.0


def _seeded_charge(loan: dict, pattern: str) -> float:
    p, r = loan["principal"], loan["rate_pct"] / 100
    if pattern == "sanction_date_interest":        # interest from sanction date, not disbursal
        return round(p * r * (loan["first_emi"] - loan["sanction"]).days / 365, 2)
    if pattern == "full_month_interest":           # full month's interest for a part month
        return round(p * r / 12, 2)
    if pattern == "advance_emi_full_principal":    # interest on full principal despite advance EMI
        return round(p * r * (loan["first_emi"] - loan["disbursal"]).days / 365, 2)
    raise ValueError(pattern)


def _eligible(loan: dict, pattern: str) -> bool:
    days = (loan["first_emi"] - loan["disbursal"]).days
    if pattern == "full_month_interest":
        # only a genuinely short first period: under 30 days and shorter than one month
        if not (days < 30 and loan["first_emi"] < lt.add_months(loan["disbursal"], 1)):
            return False
    row = _to_row(loan, _seeded_charge(loan, pattern))
    norm = lt.normalize_book_row(row)
    correct = _correct_interest(row)
    excess = norm["charged"] - correct
    candidates = lt.expected_excesses(norm, correct)
    if pattern not in candidates or excess < MIN_SEEDED_EXCESS:
        return False
    others_clear = all(abs(excess - value) >= MIN_PATTERN_MARGIN
                       for name, value in candidates.items() if name != pattern)
    return others_clear and lt.classify_first_interest(norm, correct)[1] == pattern


def build_book(seed: int = SEED) -> tuple[list[dict], dict]:
    """Return (rows, labels); labels[loan_id] is the seeded pattern or None for a correct loan."""
    rng = random.Random(seed)
    loans = [_draw_loan(rng, number) for number in range(1, N_LOANS + 1)]
    order = list(range(N_LOANS))
    rng.shuffle(order)

    labels = {loan["loan_id"]: None for loan in loans}
    taken: set[int] = set()

    # Advance-EMI errors first (they need a large EMI to be visible), then the rest.
    for pattern in ("advance_emi_full_principal", "full_month_interest", "sanction_date_interest"):
        wanted = SEEDED[pattern]
        for index in order:
            if wanted == 0:
                break
            if index in taken:
                continue
            loan = loans[index]
            loan["advance"] = 1 if pattern == "advance_emi_full_principal" else 0
            if _eligible(loan, pattern):
                labels[loan["loan_id"]] = pattern
                taken.add(index)
                wanted -= 1
            else:
                loan["advance"] = 0
        if wanted:
            raise RuntimeError(f"could not seed enough {pattern} errors")

    # 40 correct loans that collected one EMI in advance.
    correct_advance = [i for i in order if i not in taken][:N_CORRECT_ADVANCE]
    for index in correct_advance:
        loans[index]["advance"] = 1

    rows = []
    for loan in loans:
        pattern = labels[loan["loan_id"]]
        rows.append(_to_row(loan, _seeded_charge(loan, pattern) if pattern else None))
    return rows, labels


def generate_loan_book(seed: int = SEED) -> list[dict]:
    return build_book(seed)[0]


def write_csv(rows: list[dict], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=lt.BOOK_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def spot_check(rows: list[dict], labels: dict, count: int = 12, url: str | None = None) -> float:
    """Compare correct loans' first_interest_charged with live ACTUS; returns the max |diff|."""
    correct = [r for r in rows if labels[r["loan_id"]] is None]
    sample = [r for r in correct if r["advance_emis"] == "1"][: max(1, count // 3)]
    sample += [r for r in correct if r["advance_emis"] == "0"][: count - len(sample)]
    contracts = [lt.book_contract(lt.normalize_book_row(r), r["loan_id"]) for r in sample]
    results = {lt._result_id(res): res for res in lt.run_actus(contracts, url=url)}
    worst = 0.0
    print(f"\nSpot-check against live ACTUS ({url or lt.actus_url()}):")
    print(f"  {'loan_id':<14}{'adv':>4}{'CSV charged':>14}{'ACTUS first IP':>17}{'diff':>9}")
    for r in sample:
        first_ip = next(e for e in results[r["loan_id"]]["events"] if e["type"] == "IP")
        diff = float(r["first_interest_charged"]) - first_ip["payoff"]
        worst = max(worst, abs(diff))
        print(f"  {r['loan_id']:<14}{r['advance_emis']:>4}{float(r['first_interest_charged']):>14,.2f}"
              f"{first_ip['payoff']:>17,.4f}{diff:>9.4f}")
    print(f"  max |diff| = Rs {worst:.4f} (must be <= 0.05)")
    return worst


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate the deterministic TrueTerms demo loan book.")
    parser.add_argument("--out", default=str(OUT_CSV), help="output CSV path")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--spot-check", type=int, default=0, metavar="N",
                        help="compare N correct loans with the live ACTUS engine")
    args = parser.parse_args(argv)

    rows, labels = build_book(args.seed)
    write_csv(rows, Path(args.out))
    seeded = Counter(v for v in labels.values() if v)
    advance_correct = sum(1 for r in rows if r["advance_emis"] == "1" and labels[r["loan_id"]] is None)
    print(f"Wrote {len(rows)} loans to {args.out}")
    print(f"Seeded errors: {sum(seeded.values())} {dict(seeded)}; correct loans with 1 advance EMI: {advance_correct}")

    check = lt.check_loan_book(rows, use_actus=False)["summary"]   # self-check, local engine
    found = {k: v["count"] for k, v in check["by_pattern"].items() if v["count"]}
    print(f"Local self-check: flagged {check['flagged']} {found}, total excess Rs {check['total_excess']:,.2f}")
    if check["flagged"] != sum(SEEDED.values()) or found != SEEDED:
        print("ERROR: self-check does not match the seeded errors")
        return 1

    if args.spot_check:
        if spot_check(rows, labels, args.spot_check) > 0.05:
            print("ERROR: spot-check difference above Rs 0.05")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
