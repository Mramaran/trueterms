ROUTER_SYSTEM_PROMPT = """Route user questions to the correct source.

1. "vectorstore" — for ALL ACTUS questions: contract types (PAM, ANN, LAM, NAM...), 
   fields, events, examples, generation, simulation, risk factors, scenarios
2. "web_search" — ONLY for real-time data or topics clearly outside ACTUS

Default to "vectorstore" for any ACTUS-related question.

Respond ONLY with JSON: {"datasource": "vectorstore"} or {"datasource": "web_search"}"""

ROUTER_USER_TEMPLATE = """Route this question: {query}"""

REWRITER_SYSTEM_PROMPT = """Rewrite queries using ACTUS terminology for better retrieval. Return ONLY the rewritten string."""
REWRITER_USER_TEMPLATE = """Rewrite for ACTUS retrieval: {query}"""
