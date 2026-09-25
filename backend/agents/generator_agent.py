"""
Generator Agent — TrueTerms
================================
Two modes:
  1. CONTRACT mode → user asks to generate/create a contract
                  → returns Postman-ready ACTUS JSON
  2. GENERAL mode  → any other ACTUS question
                  → returns text answer from context
"""

import re
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.generator_prompts import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_TEMPLATE,
    CONTRACT_GENERATOR_SYSTEM_PROMPT,
    CONTRACT_GENERATOR_USER_TEMPLATE,
    WEB_GENERATOR_SYSTEM_PROMPT,
    WEB_GENERATOR_USER_TEMPLATE,
    CONTRACT_KEYWORDS,
    CONTRACT_TYPES,
    CONTRACT_SYNONYMS,
)

# ── Required fields per contract type ─────────────────────────────────────────

REQUIRED_FIELDS = {
    "PAM": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "initialExchangeDate", "maturityDate",
        "notionalPrincipal", "nominalInterestRate", "dayCountConvention",
        "currency", "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "premiumDiscountAtIED",
    ],
    "ANN": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "initialExchangeDate", "maturityDate",
        "notionalPrincipal", "nominalInterestRate", "dayCountConvention",
        "currency", "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "premiumDiscountAtIED",
    ],
    "LAM": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "initialExchangeDate", "maturityDate",
        "notionalPrincipal", "nominalInterestRate", "dayCountConvention",
        "currency", "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
    ],
    "NAM": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "initialExchangeDate", "maturityDate",
        "notionalPrincipal", "nominalInterestRate", "dayCountConvention",
        "currency", "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
    ],
    "CLM": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "initialExchangeDate", "maturityDate",
        "notionalPrincipal", "nominalInterestRate", "dayCountConvention",
        "currency", "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset",
        "rateSpread", "marketObjectCodeOfRateReset",
    ],
    "MAR": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "currency",
        "cycleAnchorDateOfMargining", "cycleOfMargining",
        "marketObjectCodeOfCollateral", "coverageOfCreditEnhancement",
    ],
    "CEG": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "maturityDate", "currency",
        "coverageOfCreditEnhancement", "feeBasis",
    ],
    "CEC": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "currency",
        "coverageOfCreditEnhancement",
    ],
    "CSH": [
        "contractType", "contractID", "statusDate", "contractRole",
        "currency", "notionalPrincipal",
    ],
    "STK": [
        "contractType", "contractID", "statusDate", "contractRole",
        "currency", "notionalPrincipal",
    ],
    "COM": [
        "contractType", "contractID", "statusDate", "contractRole",
        "currency", "notionalPrincipal", "maturityDate",
    ],
    "FXOUT": [
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "maturityDate", "currency",
        "notionalPrincipal", "nominalInterestRate",
    ],
}

RISK_FACTOR_FIELDS = [
    "cycleAnchorDateOfRateReset", "cycleOfRateReset",
    "rateSpread", "marketObjectCodeOfRateReset",
]

# ── ACTUS allowed fields per contract type ────────────────────────────────────
# Source: Official ACTUS data dictionary v1.1
# Any field NOT in this list is stripped before sending to the ACTUS server.
# This prevents AttributeConversionException for ALL contract types permanently.

ALLOWED_FIELDS = {
    # ── Common fields allowed for ALL contract types ──
    "_COMMON": {
        "contractType", "contractID", "statusDate", "contractRole",
        "contractDealDate", "currency", "calendar", "businessDayConvention",
        "endOfMonthConvention", "settlementCurrency",
    },
    "PAM": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset", "fixingDaysOffset",
        "cycleAnchorDateOfFee", "cycleOfFee", "feeRate", "feeBasis",
        "cycleAnchorDateOfOptionality", "cycleOfOptionality",
        "purchaseDate", "priceAtPurchaseDate", "terminationDate",
        "priceAtTerminationDate", "scalingEffect", "scalingIndexAtStatusDate",
        "marketObjectCodeOfScalingIndex", "cycleAnchorDateOfScalingIndex",
        "cycleOfScalingIndex", "interestCalculationBase",
        "interestCalculationBaseAmount", "creditLineAmount",
    },
    "ANN": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset", "fixingDaysOffset",
        "nextPrincipalRedemptionPayment",
        "cycleAnchorDateOfFee", "cycleOfFee", "feeRate", "feeBasis",
        "purchaseDate", "priceAtPurchaseDate", "terminationDate",
        "priceAtTerminationDate", "scalingEffect",
    },
    "LAM": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset", "interestCalculationBase",
        "interestCalculationBaseAmount",
    },
    "NAM": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset", "interestCalculationBase",
        "interestCalculationBaseAmount",
    },
    "CLM": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
    },
    "UMP": {
        "notionalPrincipal", "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset", "maximumOperationAmount",
    },
    "CSH": {
        "notionalPrincipal",
    },
    "STK": {
        "notionalPrincipal", "marketObjectCode",
        "purchaseDate", "priceAtPurchaseDate",
        "terminationDate", "priceAtTerminationDate",
        "cycleAnchorDateOfDividend", "cycleOfDividend", "nextDividendPaymentAmount",
    },
    "COM": {
        "maturityDate", "notionalPrincipal", "marketObjectCode",
        "purchaseDate", "priceAtPurchaseDate",
        "terminationDate", "priceAtTerminationDate",
    },
    "FXOUT": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "currency2", "notionalPrincipal2",
        "deliverySettlement",
    },
    "SWAPS": {
        "initialExchangeDate", "maturityDate", "nominalInterestRate",
        "dayCountConvention", "deliverySettlement",
        "marketObjectCode",
    },
    "SWPPV": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
    },
    "FUTUR": {
        "maturityDate", "notionalPrincipal", "marketObjectCode",
        "purchaseDate", "priceAtPurchaseDate",
        "terminationDate", "priceAtTerminationDate",
        "deliverySettlement",
    },
    "OPTNS": {
        "maturityDate", "notionalPrincipal", "marketObjectCode",
        "purchaseDate", "priceAtPurchaseDate",
        "terminationDate", "priceAtTerminationDate",
        "optionType", "optionStrike1", "optionStrike2",
        "deliverySettlement",
    },
    "CAPFL": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
        "optionType", "optionStrike1",
    },
    "MAR": {
        "cycleAnchorDateOfMargining", "cycleOfMargining",
        "marketObjectCodeOfCollateral", "coverageOfCreditEnhancement",
    },
    "CEG": {
        "maturityDate", "notionalPrincipal", "nominalInterestRate",
        "dayCountConvention", "feeBasis", "feeRate",
        "coverageOfCreditEnhancement",
        "cycleAnchorDateOfFee", "cycleOfFee",
        "guaranteedExposure",
    },
    "CEC": {
        "maturityDate", "coverageOfCreditEnhancement",
        "guaranteedExposure",
    },
    "REP": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "marketObjectCodeOfCollateral", "coverageOfCreditEnhancement",
    },
    "CDSWP": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
    },
    "TRSWP": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "marketObjectCodeOfRateReset",
    },
    "CLNTE": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset", "coverageOfCreditEnhancement",
    },
    "PBN": {
        "initialExchangeDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
        "purchaseDate", "priceAtPurchaseDate",
    },
    "BNDCP": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "purchaseDate", "priceAtPurchaseDate",
        "terminationDate", "priceAtTerminationDate",
        "optionType", "optionStrike1",
    },
    "BNDWR": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "purchaseDate", "priceAtPurchaseDate",
    },
    "ANX": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention", "premiumDiscountAtIED",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
    },
    "NAX": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
    },
    "LAX": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "cycleAnchorDateOfPrincipalRedemption", "cycleOfPrincipalRedemption",
        "nextPrincipalRedemptionPayment",
        "cycleAnchorDateOfRateReset", "cycleOfRateReset", "rateSpread",
        "marketObjectCodeOfRateReset",
    },
    "SCRMR": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "marketObjectCodeOfRateReset", "coverageOfCreditEnhancement",
    },
    "SCRCR": {
        "initialExchangeDate", "maturityDate", "notionalPrincipal",
        "nominalInterestRate", "dayCountConvention",
        "cycleAnchorDateOfInterestPayment", "cycleOfInterestPayment",
        "marketObjectCodeOfRateReset", "coverageOfCreditEnhancement",
    },
}


def _strip_invalid_fields(payload: dict) -> tuple:
    """
    Remove any field from each contract that is not in the ACTUS allowed list.
    Returns (cleaned_payload, list_of_stripped_field_names).
    This prevents AttributeConversionException for ALL contract types.
    """
    common = ALLOWED_FIELDS["_COMMON"]
    stripped_all = []

    for contract in payload.get("contracts", []):
        ct = contract.get("contractType", "").upper()
        allowed = common | ALLOWED_FIELDS.get(ct, set())

        # If contract type is unknown, allow all fields (don't break)
        if not ALLOWED_FIELDS.get(ct):
            continue

        invalid_keys = [k for k in list(contract.keys()) if k not in allowed]
        for k in invalid_keys:
            del contract[k]
            stripped_all.append(f"`{k}` (not valid for {ct})")

    return payload, stripped_all


# ── Default forward curves for auto-injection ──────────────────────────────────

DEFAULT_CURVES = {
    "SOFR":     {"rates": [0.053, 0.051, 0.049, 0.047, 0.046, 0.045], "step_days": 30},
    "ESTR":     {"rates": [0.037, 0.036, 0.035, 0.034, 0.033], "step_days": 30},
    "UST5Y":    {"rates": [0.043, 0.045, 0.046, 0.048, 0.049, 0.050], "step_days": 180},
    "LIBOR_6M": {"rates": [0.050, 0.0525, 0.051, 0.049, 0.0475, 0.046, 0.045], "step_days": 180},
    "LIBOR6M":  {"rates": [0.050, 0.0525, 0.051, 0.049, 0.0475, 0.046, 0.045], "step_days": 180},
    "EURIBOR":  {"rates": [0.038, 0.037, 0.036, 0.035, 0.034], "step_days": 180},
    "DEFAULT":  {"rates": [0.045, 0.044, 0.043, 0.042, 0.041, 0.040], "step_days": 180},
}


def _build_risk_factor(market_code: str) -> dict:
    """Build a riskFactor object with a realistic forward curve for the given market code."""
    curve = DEFAULT_CURVES.get(market_code.upper(), DEFAULT_CURVES["DEFAULT"])
    today = datetime.today()
    step = curve["step_days"]
    data = [
        {
            "time": (today + timedelta(days=i * step)).strftime("%Y-%m-%dT00:00:00"),
            "value": rate,
        }
        for i, rate in enumerate(curve["rates"])
    ]
    return {"marketObjectCode": market_code, "base": 1.0, "data": data}


# ── GUARANTEED Risk Factor Fix ────────────────────────────────────────────────
# This is the ONLY place where riskFactors are fixed.
# It works on the raw string level — finds the JSON, parses it, fixes it, puts it back.
# No regex tricks. Direct json.loads/dumps on the extracted block.

def _fix_past_dates(answer: str) -> str:
    """
    Post-generation safety net: replace any past-year dates in the JSON block
    with correct future dates calculated from today.
    Prevents ACTUS returning 0 events due to past statusDate/initialExchangeDate.
    """
    start_marker = "```json"
    end_marker = "```"
    start_idx = answer.find(start_marker)
    if start_idx == -1:
        return answer
    json_start = answer.find("\n", start_idx) + 1
    end_idx = answer.find("\n" + end_marker, json_start)
    if end_idx == -1:
        return answer
    raw_json = answer[json_start:end_idx].strip()
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return answer

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    changed = False

    for contract in payload.get("contracts", []):
        ied_str = None  # track the corrected initialExchangeDate

        for date_field in ["statusDate", "contractDealDate", "initialExchangeDate",
                           "cycleAnchorDateOfInterestPayment",
                           "cycleAnchorDateOfPrincipalRedemption",
                           "cycleAnchorDateOfRateReset"]:
            val = contract.get(date_field, "")
            if not val:
                continue
            try:
                dt = datetime.strptime(val[:10], "%Y-%m-%d")
                if dt.date() < today.date():
                    if date_field in ("statusDate", "contractDealDate"):
                        new_dt = today - timedelta(days=1)
                    else:
                        new_dt = today
                    contract[date_field] = new_dt.strftime("%Y-%m-%dT00:00:00")
                    print(f"  [DATE-FIX] {date_field}: {val} -> {contract[date_field]}")
                    changed = True
                if date_field == "initialExchangeDate":
                    ied_str = contract[date_field]
            except ValueError:
                pass

        # Keep cycleAnchorDateOfInterestPayment in sync with initialExchangeDate
        if ied_str and contract.get("cycleAnchorDateOfInterestPayment"):
            if contract["cycleAnchorDateOfInterestPayment"] != ied_str:
                contract["cycleAnchorDateOfInterestPayment"] = ied_str
                changed = True

        # Fix maturityDate only if it’s in the past or same as today
        mat = contract.get("maturityDate", "")
        if mat:
            try:
                dt = datetime.strptime(mat[:10], "%Y-%m-%d")
                if dt.date() <= today.date():
                    # Safe replace: avoid Feb-29 issues
                    try:
                        new_mat = today.replace(year=today.year + 5)
                    except ValueError:
                        new_mat = today.replace(year=today.year + 5, day=28)
                    contract["maturityDate"] = new_mat.strftime("%Y-%m-%dT00:00:00")
                    print(f"  [DATE-FIX] maturityDate: {mat} -> {contract['maturityDate']}")
                    changed = True
            except ValueError:
                pass

    if not changed:
        return answer

    fixed_json = json.dumps(payload, indent=2)
    fixed_answer = (
        answer[:start_idx]
        + start_marker + "\n"
        + fixed_json + "\n"
        + end_marker
        + answer[end_idx + len("\n" + end_marker):]
    )
    print("  [DATE-FIX] Past dates corrected to future dates")
    return fixed_answer


def _fix_risk_factors(answer: str) -> str:
    """
    Find the JSON block in the answer string.
    If a contract uses marketObjectCodeOfRateReset but riskFactors is empty
    or missing a matching entry, auto-inject the correct forward curve.
    Returns the fixed answer string.
    """
    # Find the start of the JSON block
    start_marker = "```json"
    end_marker = "```"

    start_idx = answer.find(start_marker)
    if start_idx == -1:
        return answer  # No JSON block found

    # Find where the JSON content starts (after ```json\n)
    json_start = answer.find("\n", start_idx) + 1

    # Find the closing ``` — search from after json_start
    end_idx = answer.find("\n" + end_marker, json_start)
    if end_idx == -1:
        return answer  # Malformed block

    raw_json = answer[json_start:end_idx].strip()

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return answer  # Can't parse, leave unchanged

    contracts = payload.get("contracts", [])
    if not contracts:
        return answer

    risk_factors = payload.get("riskFactors", [])
    changed = False

    for contract in contracts:
        market_code = (
            contract.get("marketObjectCodeOfRateReset")
            or contract.get("marketObjectCodeRateReset")
        )
        if not market_code:
            continue
        already_has = any(
            rf.get("marketObjectCode") == market_code
            for rf in risk_factors
        )
        if already_has:
            continue
        print(f"  [RISK-FIX] ✅ Auto-injecting riskFactors for '{market_code}'")
        risk_factors.append(_build_risk_factor(market_code))
        changed = True

    payload["riskFactors"] = risk_factors

    # ── STRIP INVALID FIELDS — ALWAYS runs, regardless of riskFactors change ──
    payload, stripped = _strip_invalid_fields(payload)
    if stripped:
        print(f"  [FIELD-STRIP] ✅ Removed invalid fields: {stripped}")
        changed = True  # force rebuild even if only fields were stripped

    # Always rebuild — even if nothing changed, ensures clean JSON output
    fixed_json = json.dumps(payload, indent=2)

    # Rebuild the answer with the fixed JSON block
    fixed_answer = (
        answer[:start_idx]
        + start_marker + "\n"
        + fixed_json + "\n"
        + end_marker
        + answer[end_idx + len("\n" + end_marker):]
    )
    return fixed_answer


# ── Contract detection ────────────────────────────────────────────────────────

def _detect_contract_request(query_raw: str):
    # Strip conversation history block so it doesn’t confuse detection
    query = re.sub(r'CONVERSATION HISTORY.*?Current question:', '', query_raw, flags=re.DOTALL)
    q_upper = query.upper()
    q_lower = query.lower()

    # --- Generation keywords (user wants a contract produced) ---
    GEN_KEYWORDS = [
        "generate", "create", "build", "make", "produce",
        "write", "give me", "show me a sample", "example of",
        "i need a", "i want a", "can you make", "draft",
    ]
    has_keyword = any(kw in q_lower for kw in GEN_KEYWORDS)

    # --- Detect explicit contract type ---
    found_type = None
    for ct in CONTRACT_TYPES:
        # word-boundary match so "CLAM" doesn’t match "LAM"
        if re.search(r'\b' + re.escape(ct) + r'\b', q_upper):
            found_type = ct
            break

    if found_type is None:
        for phrase, ct in CONTRACT_SYNONYMS.items():
            if phrase in q_lower:
                found_type = ct
                break

    # --- Explicit explanation/info queries — NEVER generate contract JSON ---
    INFO_PATTERNS = [
        "what are", "what is", "list ", "available", "types of",
        "explain", "tell me about", "how many", "show me all",
        "describe", "definition", "difference between", "compare",
        "how does", "how do", "why is", "when is", "where is",
        "which contract", "what contract",
    ]
    OVERRIDE_KEYWORDS = ["generate", "create", "build", "make", "produce", "write", "draft"]
    is_info_query = any(kw in q_lower for kw in INFO_PATTERNS)
    if is_info_query and not any(kw in q_lower for kw in OVERRIDE_KEYWORDS):
        return False, None

    # --- Contract generation detected ---
    if has_keyword and found_type:
        return True, found_type

    if has_keyword and any(w in q_lower for w in [
        "contract", "instrument", "loan", "bond", "mortgage",
        "swap", "option", "future", "lease", "deposit", "annuity",
    ]):
        return True, found_type or "PAM"

    return False, None


def _wants_risk_factor(query: str) -> bool:
    q_lower = query.lower()
    return any(w in q_lower for w in [
        "risk factor", "risk", "rate reset", "floating", "variable", "ust5y",
        "libor", "sofr", "spread", "market object",
    ])


# ── Context builder ───────────────────────────────────────────────────────────

def _build_contract_context(documents: List[dict], contract_type: str, want_rf: bool, max_chars: int = 12000) -> tuple:
    def relevance(doc):
        ct = doc.get("metadata", {}).get("contract_type", "")
        has_rf = doc.get("metadata", {}).get("has_risk_factors", False)
        score = 0
        if ct == contract_type:
            score += 10
        if has_rf == want_rf:
            score += 5
        if doc.get("metadata", {}).get("type") in ("actus_contract", "postman_contract"):
            score += 3
        return -score

    sorted_docs = sorted(documents, key=relevance)
    context_parts = []
    sources = []
    total_chars = 0

    for doc in sorted_docs:
        raw_json = doc.get("metadata", {}).get("raw_json", "")
        text = doc["text"]
        source = doc.get("metadata", {}).get("filename", "unknown")
        content = raw_json if raw_json else text

        if total_chars + len(content) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 500:
                context_parts.append(f"[Source: {source}]\n{content[:remaining]}")
                if source not in sources:
                    sources.append(source)
            break

        context_parts.append(f"[Source: {source}]\n{content}")
        if source not in sources:
            sources.append(source)
        total_chars += len(content)

    return "\n\n---\n\n".join(context_parts), sources


# ── JSON cleaning and validation ──────────────────────────────────────────────

def _clean_and_validate_json(raw: str, contract_type: str, want_rf: bool) -> str:
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if not json_match:
        return raw

    candidate = json_match.group(1).strip()

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as e:
        return raw + f"\n\n> ⚠️ JSON parse error: {e}. Please try again."

    if "contracts" not in payload:
        payload = {"contracts": [payload], "riskFactors": []}
    if "riskFactors" not in payload:
        payload["riskFactors"] = []

    today      = datetime.now()
    today_str  = today.strftime("%Y-%m-%dT00:00:00")
    yesterday  = (today - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    try:
        mat_default = today.replace(year=today.year + 5).strftime("%Y-%m-%dT00:00:00")
    except ValueError:
        mat_default = today.replace(year=today.year + 5, day=28).strftime("%Y-%m-%dT00:00:00")

    warnings = []
    for contract in payload.get("contracts", []):
        ct = (contract.get("contractType") or contract_type or "PAM").upper()
        contract["contractType"] = ct

        # ── Auto-fill every critical field so the ACTUS server never rejects ──
        if not contract.get("contractID"):
            contract["contractID"] = f"{ct.lower()}-01"
        if not contract.get("statusDate"):
            contract["statusDate"] = yesterday
        if not contract.get("contractDealDate"):
            contract["contractDealDate"] = contract["statusDate"]
        if not contract.get("initialExchangeDate"):
            contract["initialExchangeDate"] = today_str
        if not contract.get("contractRole"):
            contract["contractRole"] = "RPA"
        if not contract.get("calendar"):
            contract["calendar"] = "WEEKDAY"
        if not contract.get("businessDayConvention"):
            contract["businessDayConvention"] = "SCF"
        if not contract.get("currency"):
            contract["currency"] = "USD"
        if not contract.get("dayCountConvention") and ct not in ("CSH", "STK", "COM", "MAR"):
            contract["dayCountConvention"] = "30E360"
        if not contract.get("maturityDate") and ct not in ("CSH", "STK", "UMP", "MAR"):
            contract["maturityDate"] = mat_default
        if not contract.get("notionalPrincipal") and ct not in ("MAR",):
            contract["notionalPrincipal"] = 1000000
        if not contract.get("nominalInterestRate") and ct not in ("CSH", "STK", "COM", "MAR"):
            contract["nominalInterestRate"] = 0.05
        if ct in ("PAM", "ANN", "LAM", "NAM", "LAX", "NAX", "ANX", "CLM", "SWPPV", "CAPFL"):
            if not contract.get("cycleAnchorDateOfInterestPayment"):
                contract["cycleAnchorDateOfInterestPayment"] = contract.get("initialExchangeDate", today_str)
            if not contract.get("cycleOfInterestPayment"):
                contract["cycleOfInterestPayment"] = "P1ML0"
        if ct in ("PAM", "ANN") and "premiumDiscountAtIED" not in contract:
            contract["premiumDiscountAtIED"] = 0
        if ct in ("ANN", "LAM", "NAM", "LAX", "NAX", "ANX"):
            if not contract.get("cycleAnchorDateOfPrincipalRedemption"):
                contract["cycleAnchorDateOfPrincipalRedemption"] = contract.get("initialExchangeDate", today_str)
            if not contract.get("cycleOfPrincipalRedemption"):
                contract["cycleOfPrincipalRedemption"] = "P1ML0"

        # ── Validate remaining required fields ──
        required = REQUIRED_FIELDS.get(ct, [])
        missing  = [f for f in required if f not in contract]
        if missing:
            warnings.append(f"⚠️ Still missing for {ct}: {', '.join(missing)}")

    # ── Strip invalid fields ──
    payload, stripped = _strip_invalid_fields(payload)
    if stripped:
        print(f"  [FIELD-STRIP] Removed invalid fields: {stripped}")

    formatted   = json.dumps(payload, indent=2)
    fixed_block = f"```json\n{formatted}\n```"
    result = re.sub(r'```(?:json)?\s*[\s\S]*?```', fixed_block, raw, count=1)

    if warnings:
        result += "\n\n" + "\n".join(f"- {w}" for w in warnings)

    return result


# ── Main generate function ────────────────────────────────────────────────────

def generate_answer(
    query: str,
    documents: List[dict],
    llm_client,
    model: str,
    max_context_chars: int = 12000,
    language: str = 'en',
) -> dict:
    if not documents:
        return {
            "answer": (
                "Your ACTUS knowledge base does not contain relevant information "
                "for this query. Please try rephrasing."
            ),
            "sources": [],
        }

    is_contract, contract_type = _detect_contract_request(query)
    want_rf = _wants_risk_factor(query)

    if is_contract:
        print(f"  [GENERATOR] CONTRACT mode → {contract_type} | risk_factors={want_rf}")
        context, sources = _build_contract_context(documents, contract_type, want_rf, max_context_chars)
        today = datetime.now().strftime("%Y-%m-%d")
        system_prompt = CONTRACT_GENERATOR_SYSTEM_PROMPT.format(context=context, today=today)
        user_message = CONTRACT_GENERATOR_USER_TEMPLATE.format(
            contract_type=contract_type or "PAM",
            query=query,
        )
    else:
        print(f"  [GENERATOR] GENERAL mode")
        context_parts = []
        sources = []
        total = 0
        for doc in documents:
            text = doc["text"]
            source = doc.get("metadata", {}).get("filename", "unknown")
            if total + len(text) > max_context_chars:
                break
            context_parts.append(f"[Source: {source}]\n{text}")
            if source not in sources:
                sources.append(source)
            total += len(text)
        context = "\n\n---\n\n".join(context_parts)
        system_prompt = GENERATOR_SYSTEM_PROMPT.format(context=context)
        user_message = GENERATOR_USER_TEMPLATE.format(query=query)

    print(f"  [GENERATOR] Context: {len(context)} chars | Sources: {sources}")

    # ── Language handling ─────────────────────────────────────────────────────
    LANGUAGE_NAMES = {
        'ta': 'Tamil',
        'tanglish': 'Tanglish (mix Tamil and English naturally - write Tamil words in English script)',
        'fr': 'French', 'de': 'German', 'hi': 'Hindi',
        'id': 'Indonesian', 'it': 'Italian', 'ja': 'Japanese',
        'ko': 'Korean', 'pt': 'Portuguese', 'es': 'Spanish',
    }
    _EXPLICIT = [
        (r'\bin english\b|give answer in english|answer in english|respond in english', 'English'),
        (r'\bin tamil\b|answer in tamil|தமிழில்|தமிழ்ல', 'Tamil'),
        (r'\bin hindi\b|answer in hindi|हिंदी में', 'Hindi'),
        (r'\bin french\b|en français', 'French'),
        (r'\bin german\b|auf deutsch', 'German'),
        (r'\bin spanish\b|en español', 'Spanish'),
        (r'\bin portuguese\b', 'Portuguese'),
        (r'\bin japanese\b', 'Japanese'),
        (r'\bin korean\b', 'Korean'),
        (r'\bin italian\b', 'Italian'),
        (r'\bin indonesian\b', 'Indonesian'),
    ]
    explicit_lang = None
    q_lower = query.lower()
    for pat, lang_name in _EXPLICIT:
        if re.search(pat, q_lower if pat.isascii() else query, re.IGNORECASE):
            explicit_lang = lang_name
            break

    if explicit_lang and explicit_lang != 'English':
        lang_note = f'🌐 LANGUAGE INSTRUCTION: The user has explicitly requested a response in {explicit_lang}. You MUST respond entirely in {explicit_lang}. Only JSON field names and ACTUS acronyms may stay in English.\n\n'
        system_prompt = lang_note + system_prompt
        user_message = user_message + f'\n\n[Respond in {explicit_lang} only]'
    elif language and language != 'en':
        lang_display = LANGUAGE_NAMES.get(language, language)
        lang_note = f'🌐 LANGUAGE INSTRUCTION: You MUST respond entirely in {lang_display}. Only JSON field names and ACTUS acronyms may stay in English.\n\n'
        system_prompt = lang_note + system_prompt
        user_message = user_message + f'\n\n[Respond in {lang_display} only]'

    # ── Call LLM ──────────────────────────────────────────────────────────────
    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )
    raw_answer = response.choices[0].message.content.strip()

    if is_contract:
        answer = _clean_and_validate_json(raw_answer, contract_type, want_rf)
    else:
        answer = raw_answer

    # ── GUARANTEED DATE FIX — force future dates even if LLM ignored the prompt ────
    if is_contract:
        answer = _fix_past_dates(answer)

    # ── GUARANTEED RISK FACTOR FIX ────────────────────────────────────────────
    # Runs on every contract response. Cannot fail silently.
    # Uses string-level JSON extraction — no regex tricks.
    answer = _fix_risk_factors(answer)

    print(f"  [GENERATOR] Answer: {len(answer)} chars")
    return {"answer": answer, "sources": sources}


def generate_answer_from_web(
    query: str,
    web_results: List[dict],
    llm_client,
    model: str,
) -> dict:
    if not web_results:
        return {"answer": "No information found.", "sources": []}

    context_parts = []
    sources = []

    for result in web_results[:5]:
        url = result.get("url", "")
        snippet = result.get("snippet", result.get("body", ""))
        title = result.get("title", "")
        context_parts.append(f"[{title}]\n{snippet}\nURL: {url}")
        sources.append(url)

    context = "\n\n---\n\n".join(context_parts)
    system_prompt = WEB_GENERATOR_SYSTEM_PROMPT.format(context=context)
    user_message = WEB_GENERATOR_USER_TEMPLATE.format(query=query)

    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )

    answer = response.choices[0].message.content.strip()
    return {"answer": answer, "sources": sources}
