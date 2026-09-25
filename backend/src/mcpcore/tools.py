"""
TrueTerms — MCP Core Tools
==============================
Mirrors ZK-PRET: pretmcpcore/tools.ts → registerPRETTools()

All TrueTerms tools are registered here (the loan checks live in loan_tools.py).
Called by src/mcpserver/server.py → register_actus_tools()

Author: EMBER SYNDICATE
"""

import json
import asyncio
from mcp.server import Server
from mcp import types

# ── TrueTerms internals ────────────────────────────────────────────────────
from graph.graph import run_query
from backend.config import LLM_MODEL, UNIFIED_COLLECTION_NAME
from db.vector_store import get_vector_store
from src.mcpcore.loan_tools import LOAN_TOOLS, LOAN_TOOL_NAMES, run_loan_tool


# ═══════════════════════════════════════════════════════════════════════════
#  Supported ACTUS contract types (Full official list — 32 types)
#  Source: https://www.actusfrf.org/taxonomy & actus-dictionary-taxonomy.json
#
#  Family: Basic         — Fundamental fixed-income and ownership instruments
#  Family: Combined      — Derivatives and structured products
#  Family: Credit Enh.  — Credit Enhancement instruments
# ═══════════════════════════════════════════════════════════════════════════
ACTUS_CONTRACT_TYPES = {

    # ── BASIC: Fixed Income ──────────────────────────────────────────────
    "PAM":   "Principal at Maturity [Basic/Fixed Income] — Principal paid at IED, repaid at MD. Fixed & variable rates. Covers bonds, bullet loans, term deposits.",
    "ANN":   "Annuity [Basic/Fixed Income] — Fixed periodic payments covering interest + amortised principal till MD. Covers mortgages, leasing contracts.",
    "LAM":   "Linear Amortiser [Basic/Fixed Income] — Equal principal repayments periodically; interest reduces accordingly. Covers amortising loans.",
    "NAM":   "Negative Amortiser [Basic/Fixed Income] — Payment less than interest; outstanding balance grows; MD shifts. Variable rate only. Covers ARM mortgages.",
    "ANX":   "Exotic Annuity [Basic/Fixed Income] — Exotic ANN with step-ups on principal/interest rates. Highly flexible irregular principal payments. Covers teaser rate loans.",
    "LAX":   "Exotic Linear Amortiser [Basic/Fixed Income] — Exotic LAM with step-ups on principal/interest rates. Covers teaser rate mortgages.",
    "NAX":   "Exotic Negative Amortiser [Basic/Fixed Income] — Exotic NAM with step-ups on principal/interest rates and variable MD. Covers variable-MD mortgages.",
    "CLM":   "Call Money [Basic/Fixed Income] — Loans rolled over until called; repaid after notice period. Covers interbank call loans.",
    "UMP":   "Undefined Maturity Profile [Basic/Fixed Income] — Principal paid in/out without fixed schedule; interest capitalised periodically. Covers savings accounts, current accounts.",
    "PBN":   "Perpetual Bonds [Basic/Fixed Income] — Bonds with no maturity date; interest paid indefinitely unless terminated. Covers consoles, war loans.",

    # ── BASIC: Ownership ─────────────────────────────────────────────────
    "CSH":   "Cash [Basic/Ownership] — Cash or cash-equivalent position. Covers deposits at central banks.",
    "STK":   "Stock [Basic/Ownership] — Equity instrument bought at market price, follows an index. Covers all straight stocks.",
    "COM":   "Commodity [Basic/Ownership] — Tracks movements of physical commodities. Covers oil, gas, electricity, real estate.",

    # ── COMBINED: Symmetric ──────────────────────────────────────────────
    "FXOUT": "Foreign Exchange Outright [Combined/Symmetric] — Two parties exchange fixed cash flows in different currencies at a future date. Covers FX forwards, underlying of FX options & futures.",
    "SWAPS": "Swap [Combined/Symmetric] — Exchange of two basic CTs (PAM, ANN etc.); one fixed, one variable. Covers all swap varieties including cross-currency and basis swaps.",
    "SWPPV": "Plain Vanilla Swap [Combined/Symmetric] — Two identical PAMs: one leg fixed, one variable. Covers 90%+ of interest rate swaps.",

    # ── COMBINED: Asymmetric ─────────────────────────────────────────────
    "OPTNS": "Option [Combined/Asymmetric] — Straight option pay-off for any basic CT as underlying. Supports European, American, Bermudan options on rates, FX, stocks.",
    "FUTUR": "Future [Combined/Asymmetric] — Tracks value changes of any basic CT as underlying; handles margin calls. Covers interest rate, FX, stock, commodity futures.",
    "CAPFL": "Cap/Floor [Combined/Asymmetric] — Interest rate option expressed as maximum or minimum rate. Covers caps and floor options.",
    "BCS":   "Boundary Controlled Switch [Combined/Asymmetric] — Derivative with sub-contract legs activated/extinguished when underlying price hits a boundary. Covers knock-in/knock-out barrier options, bonus contracts.",
    "BNDCP": "Convertible Note [Combined/Asymmetric] — Bond with call/put option; if exercised, underlying bond ceases to exist. Covers callable and puttable bonds or loans.",
    "BNDWR": "Warrant [Combined/Asymmetric] — Bond with a warrant; if option is exercised, underlying bond continues to exist. Covers warrants.",
    "CDSWP": "Credit Default Swap [Combined/Asymmetric] — Payment triggered if one or more underlying counterparties default. Covers all credit default swap varieties.",
    "CLNTE": "Credit Linked Note [Combined/Asymmetric] — Security with an embedded Credit Default Swap (CDSWP).",
    "TRSWP": "Total Return Swap [Combined/Asymmetric] — One party pays fixed/variable rate; other party pays total return (income + capital gains) of an underlying asset.",
    "EXOTi": "EXOTi [Combined/Asymmetric] — Placeholder for exotic options (knock-in/out, barrier, ladder, rainbow). Relevance subject to future market demand.",

    # ── COMBINED: Securitization ─────────────────────────────────────────
    "SCRCR": "Securitization Credit Risk [Combined/Securitization] — Contracts ranked by credit default; lower tranches absorb first losses. Covers CDOs.",
    "SCRMR": "Securitization Market Risk [Combined/Securitization] — All underlying contracts treated equally; buyer gets proportional cash flows. Covers ABS, MBS, interest-only and principal-only tranches.",

    # ── CREDIT ENHANCEMENT ───────────────────────────────────────────────
    "CEG":   "Guarantee [Credit Enhancement] — Guarantor covers debtor exposure to obligee. Covers personal/government guarantees, CDO underlyings.",
    "CEC":   "Collateral [Credit Enhancement] — Collateral covers debtor exposure to obligee. Covers mortgage collateral, financial/physical collateral coverage.",
    "MAR":   "Margining [Credit Enhancement] — Traces value changes and margin categories (initial and variation margin). Covers margin contracts in central depositories.",
    "REP":   "Repurchase Agreement [Credit Enhancement] — Controls and manages sale and repurchase of assets. Covers classical repo and reverse repo agreements.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  Lazy singleton — LLM client
# ═══════════════════════════════════════════════════════════════════════════
_llm_client = None

def _get_client():
    global _llm_client
    if _llm_client is None:
        from backend.anthropic_client import get_llm_client
        _llm_client = get_llm_client()
    return _llm_client


# ═══════════════════════════════════════════════════════════════════════════
#  register_actus_tools() — mirrors registerPRETTools() in tools.ts
# ═══════════════════════════════════════════════════════════════════════════
def register_actus_tools(server: Server) -> None:
    """Register all TrueTerms tools on the MCP server instance."""

    # ── list_tools ────────────────────────────────────────────────────────
    @server.list_tools()
    async def list_tools() -> list:
        return [
            types.Tool(
                name="query-trueterms",
                description=(
                    "Send any ACTUS-related question through the TrueTerms agentic RAG pipeline. "
                    "Auto-routes to vectorstore (ACTUS standards, example contracts, about-ACTUS docs) "
                    "or web-search when local docs are insufficient. "
                    "Use for: term definitions, event descriptions, state variables, "
                    "applicability rules, contract comparisons, and general ACTUS questions."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Your ACTUS question — e.g. 'what is nominalInterestRate', "
                                "'what events does PAM produce', 'explain scalingEffect'"
                            )
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of docs to retrieve from vectorstore (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),

            types.Tool(
                name="generate-actus-contract",
                description=(
                    "Generate a complete, valid ACTUS financial contract JSON in Postman/API format "
                    "for a specific contract type. Output can be POSTed directly to the ACTUS server. "
                    "Supported (32 types): "
                    "Basic/Fixed Income: PAM, ANN, LAM, NAM, ANX, LAX, NAX, CLM, UMP, PBN | "
                    "Basic/Ownership: CSH, STK, COM | "
                    "Combined/Symmetric: FXOUT, SWAPS, SWPPV | "
                    "Combined/Asymmetric: OPTNS, FUTUR, CAPFL, BCS, BNDCP, BNDWR, CDSWP, CLNTE, TRSWP, EXOTi | "
                    "Combined/Securitization: SCRCR, SCRMR | "
                    "Credit Enhancement: CEG, CEC, MAR, REP"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contract_type": {
                            "type": "string",
                            "description": "ACTUS contract type acronym (e.g. 'PAM', 'ANN', 'LAM')"
                        },
                        "with_risk_factor": {
                            "type": "boolean",
                            "description": "Include a market rate / yield curve risk factor (default: false)",
                            "default": False
                        },
                        "additional_requirements": {
                            "type": "string",
                            "description": "Extra context: 'floating rate', '5-year maturity', 'quarterly payments'",
                            "default": ""
                        }
                    },
                    "required": ["contract_type"]
                }
            ),

            types.Tool(
                name="search-actus-standards",
                description=(
                    "Search the ACTUS dictionary and standards collection directly in ChromaDB. "
                    "Fastest lookup for term definitions, applicability rules, event descriptions, "
                    "or state variable meanings — no agentic pipeline overhead."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": (
                                "Term to search — e.g. 'cycleOfPrincipalRedemption', "
                                "'IPCI event', 'scalingEffect', 'nominalInterestRate'"
                            )
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Max results to return (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["search_term"]
                }
            ),

            types.Tool(
                name="run-actus-ingestion",
                description=(
                    "Re-run ACTUS document ingestion pipeline — reloads all data collections "
                    "(standards, example contracts, about-ACTUS) into ChromaDB. "
                    "Use after adding new documents or to refresh the vectorstore. ~30-60 seconds."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),

            types.Tool(
                name="get-actus-contract-types",
                description=(
                    "Return the full list of supported ACTUS contract type acronyms with descriptions. "
                    "Call this first to discover what generate-actus-contract supports."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),

            types.Tool(
                name="parse-xbrl-file",
                description=(
                    "Parse an XBRL or XML financial report file and extract ACTUS-compatible "
                    "contract fields (notionalPrincipal, nominalInterestRate, maturityDate, etc.). "
                    "Supports IFRS XBRL (RBI/India/EU), US-GAAP XBRL (SEC EDGAR), and "
                    "Generic financial XML. Returns suggested ACTUS contract payload with "
                    "confidence score. Use the returned payload directly with generate-actus-contract "
                    "or POST to /run-contract to execute it on the ACTUS server. "
                    "Ideal for: RBI bank filings, SEC 10-K/10-Q, GLEIF entity XBRL reports, "
                    "trade finance instrument data."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                "Absolute path to the XBRL/XML file on disk. "
                                "e.g. C:/reports/bank_filing.xml or /data/ifrs_report.xbrl"
                            )
                        },
                        "auto_run": {
                            "type": "boolean",
                            "description": (
                                "If true and confidence >= 60%, automatically POST the extracted "
                                "contract payload to the ACTUS server and return cash flow events. "
                                "Default: false (just parse and return extracted fields)."
                            ),
                            "default": False
                        }
                    },
                    "required": ["file_path"]
                }
            ),

            *LOAN_TOOLS,   # check-loan-offer, check-loan-book
        ]

    # ── call_tool ─────────────────────────────────────────────────────────
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        # FIX: use get_running_loop() instead of get_event_loop().
        # get_event_loop() is deprecated in Python 3.10+ when called inside
        # an already-running async context and raises RuntimeError in 3.12+.
        loop = asyncio.get_running_loop()

        # ── 1. query-trueterms ──────────────────────────────────────
        if name == "query-trueterms":
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: run_query(
                        query=arguments["query"],
                        llm_client=_get_client(),
                        model=LLM_MODEL,
                        n_results=int(arguments.get("n_results", 10)),
                    )
                )
                return [types.TextContent(type="text", text=json.dumps({
                    "query":               result["query"],
                    "answer":              result["answer"],
                    "route_taken":         result["route_taken"],
                    "documents_retrieved": result["documents_retrieved"],
                    "documents_used":      result["documents_used"],
                    "hallucination_check": result["hallucination_check"],
                    "iterations":          result["iterations"],
                    "sources":             result.get("sources", []),
                }, indent=2))]
            except Exception as exc:
                return [types.TextContent(type="text",
                    text=json.dumps({"error": str(exc), "tool": name}, indent=2))]

        # ── 2. generate-actus-contract ────────────────────────────────
        elif name == "generate-actus-contract":
            try:
                ct      = arguments["contract_type"].upper().strip()
                with_rf = bool(arguments.get("with_risk_factor", False))
                extra   = arguments.get("additional_requirements", "").strip()

                if ct not in ACTUS_CONTRACT_TYPES:
                    known = ", ".join(ACTUS_CONTRACT_TYPES.keys())
                    return [types.TextContent(type="text",
                        text=json.dumps({"error": f"Unknown type '{ct}'. Supported: {known}"}, indent=2))]

                rf_phrase    = "with risk factor" if with_rf else ""
                extra_phrase = f". Additional requirements: {extra}" if extra else ""
                query        = f"generate a {ct} contract {rf_phrase}{extra_phrase}".strip()

                result = await loop.run_in_executor(
                    None,
                    lambda: run_query(
                        query=query,
                        llm_client=_get_client(),
                        model=LLM_MODEL,
                        n_results=10
                    )
                )
                return [types.TextContent(type="text", text=json.dumps({
                    "contract_type":       ct,
                    "description":         ACTUS_CONTRACT_TYPES[ct],
                    "with_risk_factor":    with_rf,
                    "generated_contract":  result["answer"],
                    "sources":             result.get("sources", []),
                    "route_taken":         result["route_taken"],
                    "hallucination_check": result["hallucination_check"],
                }, indent=2))]
            except Exception as exc:
                return [types.TextContent(type="text",
                    text=json.dumps({"error": str(exc), "tool": name}, indent=2))]

        # ── 3. search-actus-standards ─────────────────────────────────
        elif name == "search-actus-standards":
            try:
                vs   = await loop.run_in_executor(
                    None, lambda: get_vector_store(UNIFIED_COLLECTION_NAME)
                )
                docs = await loop.run_in_executor(
                    None,
                    lambda: vs.query(
                        query_texts=[arguments["search_term"]],
                        n_results=int(arguments.get("n_results", 5)),
                        include=["documents", "metadatas", "distances"]
                    )
                )
                results = [
                    {
                        "content":   d[:800],
                        "source":    m.get("source", "unknown"),
                        "relevance": round(1.0 - dist, 4) if dist is not None else None
                    }
                    for d, m, dist in zip(
                        docs.get("documents", [[]])[0],
                        docs.get("metadatas",  [[]])[0],
                        docs.get("distances",  [[]])[0],
                    )
                ]
                return [types.TextContent(type="text", text=json.dumps({
                    "search_term": arguments["search_term"],
                    "results":     results,
                    "count":       len(results)
                }, indent=2))]
            except Exception as exc:
                return [types.TextContent(type="text",
                    text=json.dumps({"error": str(exc), "tool": name}, indent=2))]

        # ── 4. run-actus-ingestion ────────────────────────────────────
        elif name == "run-actus-ingestion":
            try:
                from ingestion.indexer import run_full_ingestion
                await loop.run_in_executor(None, run_full_ingestion)
                return [types.TextContent(type="text", text=json.dumps({
                    "status":  "success",
                    "message": "ACTUS ingestion completed. ChromaDB updated."
                }, indent=2))]
            except Exception as exc:
                return [types.TextContent(type="text",
                    text=json.dumps({"error": str(exc), "tool": name}, indent=2))]

        # ── 5. get-actus-contract-types ───────────────────────────────
        elif name == "get-actus-contract-types":
            return [types.TextContent(type="text", text=json.dumps({
                "supported_contract_types": [
                    {"acronym": k, "description": v}
                    for k, v in ACTUS_CONTRACT_TYPES.items()
                ],
                "total": len(ACTUS_CONTRACT_TYPES),
                "tip": (
                    "Call 'generate-actus-contract' with any acronym above. "
                    "Call 'query-trueterms' for questions about any contract type."
                ),
            }, indent=2))]

        # ── 6. parse-xbrl-file ────────────────────────────────────────────
        elif name == "parse-xbrl-file":
            try:
                from pathlib import Path as _Path
                import httpx as _httpx
                from backend.xbrl_parser import parse_xbrl

                file_path = _Path(arguments["file_path"].strip())
                auto_run  = bool(arguments.get("auto_run", False))

                # ── Read file ───────────────────────────────────────────
                if not file_path.exists():
                    return [types.TextContent(type="text", text=json.dumps({
                        "error": f"File not found: {file_path}",
                        "tip": "Provide an absolute path to the XBRL/XML file."
                    }, indent=2))]

                allowed_exts = {'.xml', '.xbrl', '.xsd'}
                if file_path.suffix.lower() not in allowed_exts:
                    return [types.TextContent(type="text", text=json.dumps({
                        "error": f"Unsupported file type '{file_path.suffix}'. Use .xml, .xbrl, or .xsd"
                    }, indent=2))]

                file_content = await loop.run_in_executor(
                    None, lambda: file_path.read_text(encoding='utf-8', errors='replace')
                )

                # ── Detect standard ──────────────────────────────────────
                fc_lower = file_content.lower()
                if 'ifrs' in fc_lower or 'xbrl.ifrs.org' in file_content:
                    standard = "IFRS XBRL"
                elif 'us-gaap' in fc_lower or 'fasb.org' in file_content:
                    standard = "US-GAAP XBRL"
                elif 'rbi' in fc_lower or 'in-bfsi' in fc_lower:
                    standard = "RBI / India XBRL (IFRS-aligned)"
                else:
                    standard = "Generic Financial XML"

                # ── Parse ────────────────────────────────────────────────
                result = await loop.run_in_executor(None, lambda: parse_xbrl(file_content))

                if not result.get('success'):
                    return [types.TextContent(type="text", text=json.dumps({
                        "error": result.get('error', 'XBRL parsing failed'),
                        "file": str(file_path)
                    }, indent=2))]

                suggested  = result.get('suggested_contracts', [])
                confidence = suggested[0]['confidence'] if suggested else 0
                payload    = suggested[0]['payload']    if suggested else None
                ready      = confidence >= 60 and payload is not None

                response_data = {
                    "success":           True,
                    "file":              str(file_path),
                    "standard_detected": standard,
                    "instruments_found": len(result.get('instruments', [])),
                    "confidence":        confidence,
                    "ready_to_run":      ready,
                    "warnings":          result.get('warnings', []),
                    "raw_fields_count":  len(result.get('raw_fields', {})),
                    "suggested_contracts": suggested,
                }

                # ── Auto-run on ACTUS server if requested and confident ────
                if auto_run and ready and payload:
                    ACTUS_URL = "http://34.203.247.32:8083/eventsBatch"
                    try:
                        async with _httpx.AsyncClient(verify=False, timeout=30.0) as http:
                            actus_resp = await http.post(
                                ACTUS_URL, json=payload,
                                headers={"Content-Type": "application/json"}
                            )
                            actus_resp.raise_for_status()
                            response_data["actus_events"] = actus_resp.json()
                            response_data["actus_status"] = "success"
                    except Exception as actus_err:
                        response_data["actus_status"] = f"failed: {str(actus_err)}"
                        response_data["actus_events"] = None
                elif auto_run and not ready:
                    response_data["actus_status"] = (
                        f"auto_run skipped — confidence {confidence}% < 60% threshold. "
                        "Add more ACTUS fields to the XBRL file or use generate-actus-contract."
                    )

                return [types.TextContent(type="text", text=json.dumps(response_data, indent=2))]

            except Exception as exc:
                import traceback
                return [types.TextContent(type="text", text=json.dumps({
                    "error": str(exc),
                    "tool":  name,
                    "trace": traceback.format_exc()
                }, indent=2))]

        # ── 7-8. check-loan-offer / check-loan-book ───────────────────────
        elif name in LOAN_TOOL_NAMES:
            try:
                result = await loop.run_in_executor(None, lambda: run_loan_tool(name, arguments or {}))
            except Exception as exc:
                result = {"error": str(exc), "tool": name}
            return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        # ── Unknown tool ──────────────────────────────────────────────────
        else:
            return [types.TextContent(type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2))]
