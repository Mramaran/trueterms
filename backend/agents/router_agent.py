"""
Router Agent
============
Routes the query to either the vector store or web search.

ACTUS-related questions → always routed to the vector store (your data source).
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.router_prompts import ROUTER_SYSTEM_PROMPT, ROUTER_USER_TEMPLATE


# ACTUS keywords — always route to vectorstore
_ACTUS_KW = [
    'actus','pam','ann','lam','lax','clm','ump','csh','stk','optns','futur',
    'swaps','capfl','swppv','ceg','cec','mrgng','opcl','clmo','bcs','stf',
    'rpo','invst','linda','vom','scrmr','rrf','prf','fxout','iref','nam',
    'contract','maturity','principal','interest rate','amortiz','notional',
    'nominal','cash flow','risk factor','generate','explain','what is',
    'how does','show me','coupon','mortgage','annuity','derivative',
]
# Web-only keywords
_WEB_KW = ['news today','latest news','current price','stock price','weather']

def route_query(query: str, llm_client, model: str) -> dict:
    q = query.lower()
    if any(k in q for k in _WEB_KW):
        print(f"  [ROUTER] → web_search (fast keyword, no LLM)")
        return {"datasource": "web_search"}
    # Default always vectorstore for this domain app — no LLM call needed
    print(f"  [ROUTER] → vectorstore (fast keyword, no LLM)")
    return {"datasource": "vectorstore"}
