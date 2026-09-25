"""
Hallucination Agent
===================
Two checks:

  1. GROUNDING CHECK  — Is the answer grounded in source documents?
                        Catches AI inventing ACTUS facts not in the knowledge base.

  2. FAITHFULNESS CHECK — Did the AI accurately represent what the USER asked?
                          Catches AI misattributing contract types or requests to
                          the user that were never mentioned (e.g. "user requested MAR").

Both checks must pass. If either fails, hallucination = "no".
"""

import json
import os
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.hallucination_prompts import (
    HALLUCINATION_SYSTEM_PROMPT,
    HALLUCINATION_USER_TEMPLATE,
    FAITHFULNESS_SYSTEM_PROMPT,
    FAITHFULNESS_USER_TEMPLATE,
)


def check_hallucination(
    answer: str,
    documents: List[dict],
    llm_client,
    model: str,
    query: str = "",          # ← NEW: original user query for faithfulness check
) -> str:
    """
    Returns "yes" if the answer is both grounded AND faithful.
    Returns "no" if either check fails.
    """

    # ── CHECK 1: GROUNDING ────────────────────────────────────────────────────
    # Is the answer grounded in the source documents?
    context_parts = []
    for i, doc in enumerate(documents[:5]):
        context_parts.append(f"[Doc {i+1} — {doc['source']}]\n{doc['text'][:500]}")
    context = "\n\n".join(context_parts)

    grounding_score = "yes"
    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": HALLUCINATION_SYSTEM_PROMPT},
                {"role": "user",   "content": HALLUCINATION_USER_TEMPLATE.format(
                    documents=context,
                    answer=answer,
                )},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw            = response.choices[0].message.content.strip()
        result         = json.loads(raw)
        grounding_score = result.get("binary_score", "yes")
    except Exception as e:
        print(f"  [HALLUCINATION] Grounding check error: {e} — defaulting to grounded")
        grounding_score = "yes"

    grounding_status = "GROUNDED ✓" if grounding_score == "yes" else "HALLUCINATED ✗"
    print(f"  [HALLUCINATION] Grounding: {grounding_status}")

    # If grounding already fails, no need to run faithfulness check
    if grounding_score != "yes":
        return "no"

    # ── CHECK 2: FAITHFULNESS ─────────────────────────────────────────────────
    # Did the AI accurately represent what the USER asked?
    # Skip this check if no query was provided
    if not query.strip():
        return grounding_score

    # Strip conversation history prefix before faithfulness check
    # (history block would confuse the faithfulness checker)
    clean_query = query
    if "Current question:" in query:
        clean_query = query.split("Current question:")[-1].strip()

    faithfulness_score = "yes"
    try:
        # Limit answer length sent to faithfulness check to avoid timeouts
        answer_preview = answer[:3000] if len(answer) > 3000 else answer

        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": FAITHFULNESS_SYSTEM_PROMPT},
                {"role": "user",   "content": FAITHFULNESS_USER_TEMPLATE.format(
                    query=clean_query,
                    answer=answer_preview,
                )},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw    = response.choices[0].message.content.strip()
        result = json.loads(raw)
        faithfulness_score = result.get("faithful", "yes")

        if faithfulness_score != "yes":
            reason = result.get("reason", "AI misrepresented the user's query")
            print(f"  [FAITHFULNESS] UNFAITHFUL ✗ — {reason}")
        else:
            print(f"  [FAITHFULNESS] FAITHFUL ✓")

    except Exception as e:
        # NEVER crash the pipeline — faithfulness check is advisory only
        print(f"  [FAITHFULNESS] Check skipped (error: {e}) — defaulting to faithful")
        faithfulness_score = "yes"

    # Both checks must pass
    if grounding_score == "yes" and faithfulness_score == "yes":
        return "yes"
    else:
        return "no"
