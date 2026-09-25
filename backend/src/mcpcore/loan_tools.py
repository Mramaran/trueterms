"""
TrueTerms — loan-check MCP tools
================================
Lets any MCP client (Claude Desktop, a bank's AI assistant) ask the ACTUS engine for a
loan's true cost instead of doing the arithmetic itself. Thin adapters over loan_truth.py,
the same logic behind the /loan/* API endpoints.

Registered by src/mcpcore/tools.py.

Author: EMBER SYNDICATE
"""
import csv
from pathlib import Path

from mcp import types

import loan_truth

DEMO_BOOK = Path(loan_truth.__file__).resolve().parent / "demo_data" / "demo_loan_book.csv"
MAX_BOOK_ROWS = 5000   # same cap as POST /loan/check-book

OFFER_TERMS = ("principal", "rate_pct", "rate_period", "rate_type", "tenure_months",
               "processing_fee", "processing_fee_pct", "emi", "disbursal_date", "sanction_date")
OFFER_RESULT = ("engine", "engine_note", "advertised_rate_text", "advertised_annual_rate_pct",
                "apr_pct", "apr_method", "equivalent_reducing_rate_pct", "emi", "lender_emi",
                "total_payable", "total_interest", "fees", "total_cost_of_credit", "net_disbursed",
                "disbursal_date", "first_emi_date", "maturity_date", "actus_url", "actus_contract")
FLAGGED_FIELDS = ("loan_id", "pattern", "charged", "correct", "excess", "explanation")

LOAN_TOOLS = [
    types.Tool(
        name="check-loan-offer",
        description=(
            "Independently check a loan offer on the open ACTUS engine: EMI, total cost and the "
            "true APR by RBI's Key Facts Statement method (monthly IRR x 12, fees included). "
            "Use this instead of computing loan maths yourself. Handles flat-rate offers "
            "('2% per month flat'). The answer includes the ACTUS contract, so anyone can re-run it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "principal": {"type": "number", "description": "Loan amount in rupees"},
                "rate_pct": {"type": "number",
                             "description": "Quoted rate in percent: 2 for '2% per month', 14 for '14% p.a.'"},
                "rate_period": {"type": "string", "enum": ["month", "year"], "default": "year"},
                "rate_type": {"type": "string", "enum": ["flat", "reducing"], "default": "reducing",
                              "description": "flat = interest on the original amount for the whole tenure"},
                "tenure_months": {"type": "integer", "description": "Number of monthly instalments"},
                "processing_fee": {"type": "number", "description": "Upfront fee in rupees (default 0)"},
                "processing_fee_pct": {"type": "number",
                                       "description": "Upfront fee as % of the loan, if not given in rupees"},
                "emi": {"type": "number", "description": "The lender's stated EMI, if any (overrides the formula)"},
                "disbursal_date": {"type": "string", "description": "YYYY-MM-DD (default: tomorrow)"},
                "sanction_date": {"type": "string", "description": "YYYY-MM-DD, if known"},
                "include_schedule": {"type": "boolean", "default": False,
                                     "description": "Also return every instalment (date, EMI, interest, principal, balance)"},
            },
            "required": ["principal", "rate_pct", "tenure_months"],
        },
    ),
    types.Tool(
        name="check-loan-book",
        description=(
            "Check a lender's loan book for the overcharging RBI found in its 29 Apr 2024 circular: "
            "interest from the sanction date instead of disbursal, a full month's interest for a part "
            "month, and interest on EMIs collected in advance. Each loan's first-period interest is "
            "recomputed on the ACTUS engine and compared with what was charged. Returns totals, "
            "per-pattern counts and the worst flagged loans with plain-English explanations. "
            "Give exactly one of csv_text, csv_path or use_demo_book."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": (
                    "CSV with columns: loan_id, segment, principal, annual_rate_pct, tenure_months, "
                    "sanction_date, disbursal_date, first_emi_date, advance_emis, emi_charged, "
                    "first_interest_charged")},
                "csv_path": {"type": "string", "description": "Absolute path to a .csv file with those columns"},
                "use_demo_book": {"type": "boolean",
                                  "description": "Check the bundled synthetic 500-loan demo book (35 seeded errors)"},
                "max_flagged": {"type": "integer", "default": 25,
                                "description": "How many flagged loans to list, largest overcharge first"},
            },
            "required": [],
        },
    ),
]
LOAN_TOOL_NAMES = {tool.name for tool in LOAN_TOOLS}


def run_loan_tool(name: str, arguments: dict) -> dict:
    """Run one loan tool; bad input comes back as {"error": ...} for the calling assistant to read."""
    handler = {"check-loan-offer": _check_offer, "check-loan-book": _check_book}[name]
    try:
        return handler(arguments or {})
    except (ValueError, OSError, csv.Error) as exc:
        return {"error": str(exc), "tool": name}


def _check_offer(arguments: dict) -> dict:
    terms = {key: arguments[key] for key in OFFER_TERMS if arguments.get(key) not in (None, "")}
    result = loan_truth.check_offer(terms)
    out = {key: result[key] for key in OFFER_RESULT}
    if arguments.get("include_schedule"):
        out["schedule"] = result["schedule"]
    return out


def _check_book(arguments: dict) -> dict:
    sources = [key for key in ("csv_text", "csv_path", "use_demo_book") if arguments.get(key)]
    if len(sources) != 1:
        raise ValueError("Give exactly one of csv_text, csv_path or use_demo_book.")
    if arguments.get("csv_path"):
        path = Path(arguments["csv_path"]).expanduser()
        if path.suffix.lower() != ".csv":
            raise ValueError(f"csv_path must point to a .csv file, got '{path.name}'.")
        text = path.read_text(encoding="utf-8-sig")
    elif arguments.get("use_demo_book"):
        text = DEMO_BOOK.read_text(encoding="utf-8")
    else:
        text = arguments["csv_text"]

    rows = loan_truth.read_loan_book_csv(text)
    if not rows:
        raise ValueError("The CSV has a header but no loan rows.")
    if len(rows) > MAX_BOOK_ROWS:
        raise ValueError(f"Too many rows ({len(rows):,}); the limit is {MAX_BOOK_ROWS:,} loans per check.")

    result = loan_truth.check_loan_book(rows)
    flagged = sorted((loan for loan in result["loans"] if loan["status"] == "flagged"),
                     key=lambda loan: loan["excess"], reverse=True)
    limit = max(0, int(arguments.get("max_flagged", 25)))
    return {
        "summary": result["summary"],
        "flagged_loans": [{key: loan.get(key) for key in FLAGGED_FIELDS} for loan in flagged[:limit]],
        "flagged_not_listed": max(0, len(flagged) - limit),
        "rows_with_errors": [{"loan_id": loan["loan_id"], "explanation": loan.get("explanation")}
                             for loan in result["loans"] if loan["status"] == "error"][:20],
    }
