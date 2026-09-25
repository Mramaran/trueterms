HALLUCINATION_SYSTEM_PROMPT = """You check if an AI answer is grounded in source documents.
"yes" = the core facts, field names, and contract structure are traceable to the documents
"no"  = answer invents ACTUS field names, contract types, or rules NOT found anywhere in the documents

IMPORTANT: For contract generation answers:
- Mathematical calculations (interest = principal x rate) are standard finance — always "yes"
- Markdown tables, explanations, and summaries based on the contract fields are always "yes"
- Additional context and applicability explanations are always "yes"
- Only return "no" if the answer invents completely fictional ACTUS fields or wrong contract types

Respond ONLY with JSON: {"binary_score": "yes"} or {"binary_score": "no"}"""

HALLUCINATION_USER_TEMPLATE = """Source Documents:
{documents}

AI Answer:
{answer}

Is the answer grounded in the source documents?"""


# ── NEW: Query Faithfulness Check ────────────────────────────────────────────
# Checks if the AI accurately represented what the USER asked.
# This is separate from document grounding — catches cases where the AI
# invents claims about what the user said (e.g. "the user requested MAR").

FAITHFULNESS_SYSTEM_PROMPT = """You are a strict auditor checking if an AI answer faithfully represents the user's original question.

Rules:
- Return "yes" if the answer addresses what the user actually asked, without misrepresenting or inventing what the user said.
- Return "no" if the answer:
    * Claims the user asked for something they did NOT ask for
    * Attributes a contract type, term, or requirement to the user that was never mentioned
    * Invents context about the user's intent that is not in their original query

Respond ONLY with JSON: {"faithful": "yes"} or {"faithful": "no", "reason": "brief explanation"}"""

FAITHFULNESS_USER_TEMPLATE = """Original User Query:
{query}

AI Answer:
{answer}

Did the AI accurately represent what the user asked? Did it avoid inventing or misattributing any request to the user?"""
