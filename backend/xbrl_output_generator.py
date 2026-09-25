"""
TrueTerms - XBRL Output Generator
Maps ACTUS cash flow events to XBRL taxonomy concepts (IFRS + US-GAAP)
Phase 3 of the proposal: AI Assists Compliance Reporting
"""

from datetime import datetime
from typing import List, Dict, Any


# ─────────────────────────────────────────────
# ACTUS EVENT → XBRL MAPPING TABLES
# ─────────────────────────────────────────────

IFRS_MAPPINGS = {
    "IED": {
        "tag": "ifrs-full:PrincipalAmountOfLoansGranted",
        "label": "Principal Amount of Loans Granted",
        "description": "Initial exchange of principal — loan disbursement",
        "element_type": "monetary",
    },
    "IP": {
        "tag": "ifrs-full:InterestIncomeOnFinancialAssetsAtAmortisedCost",
        "label": "Interest Income on Financial Assets",
        "description": "Periodic interest payment on loan",
        "element_type": "monetary",
    },
    "PR": {
        "tag": "ifrs-full:RepaymentsOfBorrowings",
        "label": "Repayments of Borrowings",
        "description": "Principal redemption / repayment",
        "element_type": "monetary",
    },
    "MD": {
        "tag": "ifrs-full:MaturityDateOfFinancialInstrument",
        "label": "Maturity Date of Financial Instrument",
        "description": "Contract maturity — final settlement date",
        "element_type": "date",
    },
    "RR": {
        "tag": "ifrs-full:NominalInterestRate",
        "label": "Nominal Interest Rate Reset",
        "description": "Interest rate reset event",
        "element_type": "decimal",
    },
    "FP": {
        "tag": "ifrs-full:FeeAndCommissionIncome",
        "label": "Fee and Commission Income",
        "description": "Fee payment on financial instrument",
        "element_type": "monetary",
    },
    "PY": {
        "tag": "ifrs-full:PenaltiesAndFinesPayable",
        "label": "Penalties and Fines Payable",
        "description": "Penalty payment event",
        "element_type": "monetary",
    },
    "AD": {
        "tag": "ifrs-full:AccruedInterestOnBorrowings",
        "label": "Accrued Interest on Borrowings",
        "description": "Accrued interest accumulation",
        "element_type": "monetary",
    },
    "SC": {
        "tag": "ifrs-full:NotionalAmountOfDerivativeFinancialInstruments",
        "label": "Notional Amount (Scaling)",
        "description": "Notional scaling adjustment",
        "element_type": "monetary",
    },
    "CE": {
        "tag": "ifrs-full:CashAndCashEquivalents",
        "label": "Credit Enhancement / Cash Event",
        "description": "Credit enhancement or cash collateral event",
        "element_type": "monetary",
    },
}

USGAAP_MAPPINGS = {
    "IED": {
        "tag": "us-gaap:ProceedsFromIssuanceOfLongTermDebt",
        "label": "Proceeds from Issuance of Long-Term Debt",
        "description": "Initial exchange of principal — loan proceeds received",
        "element_type": "monetary",
    },
    "IP": {
        "tag": "us-gaap:InterestIncomeExpenseNet",
        "label": "Interest Income (Expense), Net",
        "description": "Periodic interest payment — net interest income/expense",
        "element_type": "monetary",
    },
    "PR": {
        "tag": "us-gaap:RepaymentsOfLongTermDebt",
        "label": "Repayments of Long-Term Debt",
        "description": "Principal redemption payment",
        "element_type": "monetary",
    },
    "MD": {
        "tag": "us-gaap:DebtInstrumentMaturityDate",
        "label": "Debt Instrument, Maturity Date",
        "description": "Contract maturity date",
        "element_type": "date",
    },
    "RR": {
        "tag": "us-gaap:DebtInstrumentInterestRateStatedPercentage",
        "label": "Debt Instrument Interest Rate, Stated Percentage",
        "description": "Interest rate reset",
        "element_type": "decimal",
    },
    "FP": {
        "tag": "us-gaap:NoninterestIncome",
        "label": "Noninterest Income — Fees",
        "description": "Fee income on financial instrument",
        "element_type": "monetary",
    },
    "PY": {
        "tag": "us-gaap:LossContingencyAccrualPayments",
        "label": "Loss Contingency Accrual, Payments",
        "description": "Penalty payment",
        "element_type": "monetary",
    },
    "AD": {
        "tag": "us-gaap:InterestPayableCurrentAndNoncurrent",
        "label": "Interest Payable",
        "description": "Accrued interest on debt",
        "element_type": "monetary",
    },
    "SC": {
        "tag": "us-gaap:DerivativeNotionalAmount",
        "label": "Derivative, Notional Amount",
        "description": "Notional scaling adjustment",
        "element_type": "monetary",
    },
    "CE": {
        "tag": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "label": "Cash and Cash Equivalents",
        "description": "Cash collateral / credit enhancement event",
        "element_type": "monetary",
    },
}


# ─────────────────────────────────────────────
# MAIN GENERATOR FUNCTION
# ─────────────────────────────────────────────

def generate_xbrl_report(
    actus_events: List[Dict[str, Any]],
    contract_info: Dict[str, Any],
    taxonomy: str = "both"
) -> Dict[str, Any]:
    """
    Takes ACTUS cash flow events and generates XBRL compliance report.

    Args:
        actus_events: List of ACTUS event dicts with keys: type, time, payoff, currency
        contract_info: Contract metadata (contractType, currency, notionalPrincipal, etc.)
        taxonomy: "ifrs", "usgaap", or "both"

    Returns:
        dict with mapped_events, ifrs_xml, usgaap_xml, summary
    """

    currency = contract_info.get("currency", "USD")
    contract_type = contract_info.get("contractType", "PAM")
    reporting_date = datetime.now().strftime("%Y-%m-%d")

    # Build mapped events table
    mapped_events = []

    for event in actus_events:
        event_type = event.get("type", event.get("eventType", ""))
        event_time = event.get("time", event.get("eventDate", event.get("date", "")))
        payoff = event.get("payoff", event.get("amount", event.get("cashflow", 0)))

        try:
            payoff_val = float(payoff) if payoff is not None else 0.0
        except (ValueError, TypeError):
            payoff_val = 0.0

        ifrs = IFRS_MAPPINGS.get(event_type, {
            "tag": f"ifrs-full:OtherFinancialEvent_{event_type}",
            "label": f"Other Financial Event ({event_type})",
            "description": "Unmapped ACTUS event",
            "element_type": "monetary",
        })

        usgaap = USGAAP_MAPPINGS.get(event_type, {
            "tag": f"us-gaap:OtherFinancialEvent_{event_type}",
            "label": f"Other Financial Event ({event_type})",
            "description": "Unmapped ACTUS event",
            "element_type": "monetary",
        })

        mapped_events.append({
            "actus_event": event_type,
            "date": event_time,
            "amount": payoff_val,
            "currency": currency,
            "ifrs_tag": ifrs["tag"],
            "ifrs_label": ifrs["label"],
            "ifrs_description": ifrs["description"],
            "usgaap_tag": usgaap["tag"],
            "usgaap_label": usgaap["label"],
            "usgaap_description": usgaap["description"],
            "element_type": ifrs["element_type"],
        })

    # Summary stats
    total_interest = sum(e["amount"] for e in mapped_events if e["actus_event"] == "IP")
    total_principal = sum(abs(e["amount"]) for e in mapped_events if e["actus_event"] in ("PR", "IED"))
    event_types_found = list(set(e["actus_event"] for e in mapped_events))

    summary = {
        "total_events": len(mapped_events),
        "event_types": event_types_found,
        "total_interest_payments": round(total_interest, 2),
        "total_principal_movements": round(total_principal, 2),
        "currency": currency,
        "contract_type": contract_type,
        "reporting_date": reporting_date,
        "taxonomies_mapped": ["IFRS", "US-GAAP"] if taxonomy == "both" else [taxonomy.upper()],
    }

    ifrs_xml = _build_xbrl_xml(mapped_events, contract_info, "ifrs", reporting_date)
    usgaap_xml = _build_xbrl_xml(mapped_events, contract_info, "usgaap", reporting_date)

    return {
        "success": True,
        "mapped_events": mapped_events,
        "summary": summary,
        "ifrs_xml": ifrs_xml,
        "usgaap_xml": usgaap_xml,
        "reporting_date": reporting_date,
    }


def _build_xbrl_xml(
    mapped_events: List[Dict],
    contract_info: Dict,
    taxonomy: str,
    reporting_date: str,
) -> str:
    """Build a valid XBRL instance document."""

    currency = contract_info.get("currency", "USD")
    contract_id = contract_info.get("contractID", "CONTRACT-001")

    if taxonomy == "ifrs":
        ns_prefix = "ifrs-full"
        ns_uri = "https://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full"
        schema_ref = "https://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full"
        tag_key = "ifrs_tag"
        label_key = "ifrs_label"
    else:
        ns_prefix = "us-gaap"
        ns_uri = "http://fasb.org/us-gaap/2023-01-31"
        schema_ref = "http://fasb.org/us-gaap/2023-01-31"
        tag_key = "usgaap_tag"
        label_key = "usgaap_label"

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<!--')
    lines.append('  TrueTerms - XBRL Compliance Report')
    lines.append(f'  Taxonomy: {"IFRS (International Financial Reporting Standards)" if taxonomy == "ifrs" else "US-GAAP (Generally Accepted Accounting Principles)"}')
    lines.append(f'  Contract ID: {contract_id}')
    lines.append(f'  Generated: {reporting_date}')
    lines.append('  Generated by: TrueTerms AI Compliance Module')
    lines.append('-->')
    lines.append(f'<xbrl')
    lines.append(f'  xmlns="{schema_ref}"')
    lines.append(f'  xmlns:{ns_prefix}="{ns_uri}"')
    lines.append(f'  xmlns:xbrli="http://www.xbrl.org/2003/instance"')
    lines.append(f'  xmlns:iso4217="http://www.xbrl.org/2003/iso4217"')
    lines.append(f'  xmlns:xlink="http://www.w3.org/1999/xlink"')
    lines.append(f'  xmlns:link="http://www.xbrl.org/2003/linkbase"')
    lines.append(f'  xmlns:actus="http://actus-rulesfact.org/2023/actus">')
    lines.append('')
    lines.append('  <!-- Schema Reference -->')
    lines.append(f'  <link:schemaRef xlink:type="simple" xlink:href="{schema_ref}"/>')
    lines.append('')
    lines.append('  <!-- Reporting Context -->')
    lines.append('  <xbrli:context id="reportingPeriod">')
    lines.append('    <xbrli:entity>')
    lines.append(f'      <xbrli:identifier scheme="http://actus-rulesfact.org">{contract_id}</xbrli:identifier>')
    lines.append('    </xbrli:entity>')
    lines.append('    <xbrli:period>')
    lines.append(f'      <xbrli:instant>{reporting_date}</xbrli:instant>')
    lines.append('    </xbrli:period>')
    lines.append('  </xbrli:context>')
    lines.append('')
    lines.append('  <!-- Currency Unit -->')
    lines.append(f'  <xbrli:unit id="{currency}">')
    lines.append(f'    <xbrli:measure>iso4217:{currency}</xbrli:measure>')
    lines.append('  </xbrli:unit>')
    lines.append('')
    lines.append('  <!-- Contract Metadata -->')
    lines.append(f'  <actus:contractType contextRef="reportingPeriod">{contract_info.get("contractType", "PAM")}</actus:contractType>')
    lines.append(f'  <actus:contractID contextRef="reportingPeriod">{contract_id}</actus:contractID>')
    if contract_info.get("notionalPrincipal"):
        lines.append(f'  <actus:notionalPrincipal contextRef="reportingPeriod" unitRef="{currency}" decimals="2">{contract_info.get("notionalPrincipal")}</actus:notionalPrincipal>')
    if contract_info.get("nominalInterestRate"):
        lines.append(f'  <actus:nominalInterestRate contextRef="reportingPeriod" decimals="4">{contract_info.get("nominalInterestRate")}</actus:nominalInterestRate>')
    lines.append('')
    lines.append(f'  <!-- ACTUS Cash Flow Events mapped to {taxonomy.upper()} XBRL Tags -->')

    for i, event in enumerate(mapped_events):
        tag_full = event[tag_key]
        element = tag_full.split(":", 1)[1] if ":" in tag_full else tag_full

        event_type = event["actus_event"]
        date = event["date"]
        amount = event["amount"]
        elem_type = event["element_type"]
        context_id = f"event_{event_type}_{i}"

        lines.append(f'  <xbrli:context id="{context_id}">')
        lines.append('    <xbrli:entity>')
        lines.append(f'      <xbrli:identifier scheme="http://actus-rulesfact.org">{contract_id}</xbrli:identifier>')
        lines.append('    </xbrli:entity>')
        lines.append('    <xbrli:period>')
        date_clean = str(date)[:10] if date else reporting_date
        lines.append(f'      <xbrli:instant>{date_clean}</xbrli:instant>')
        lines.append('    </xbrli:period>')
        lines.append('  </xbrli:context>')
        lines.append(f'  <!-- ACTUS Event: {event_type} | {event[label_key]} -->')

        if elem_type == "date":
            lines.append(f'  <{ns_prefix}:{element} contextRef="{context_id}">{str(date)[:10]}</{ns_prefix}:{element}>')
        elif elem_type == "decimal":
            lines.append(f'  <{ns_prefix}:{element} contextRef="{context_id}" decimals="4">{amount}</{ns_prefix}:{element}>')
        else:
            lines.append(f'  <{ns_prefix}:{element} contextRef="{context_id}" unitRef="{currency}" decimals="2">{round(amount, 2)}</{ns_prefix}:{element}>')
        lines.append('')

    lines.append('</xbrl>')
    xml_str = "\n".join(lines)

    # ── Self-validate: catch XML errors before sending to client ──
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(xml_str)
    except ET.ParseError as e:
        import re as _re
        # Return error-annotated XML so developer can see exactly what failed
        error_comment = f"<!-- XBRL VALIDATION ERROR: {e} -->\n"
        xml_str = error_comment + xml_str
        print(f"[XBRL-GENERATOR] XML parse error ({taxonomy}): {e}")
    else:
        print(f"[XBRL-GENERATOR] ✅ {taxonomy.upper()} XML is valid ({len(lines)} lines, {len(mapped_events)} events)")

    return xml_str
