"""
Grader Agent — TrueTerms (Corrected)
========================================
Key fix: Contract-type documents (actus_contract, postman_contract) are
NEVER filtered out by the LLM grader — they are always treated as relevant.
The LLM grader is only applied to non-contract chunks (dictionary entries,
about-pages) which can genuinely be irrelevant to a query.

This prevents the common failure where the grader removes contract JSON
because it "looks like data, not an answer."
"""

import json
import os
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.grader_prompts import (
    GRADER_SYSTEM_PROMPT,
    GRADER_USER_TEMPLATE,
    ANSWER_GRADER_SYSTEM_PROMPT,
    ANSWER_GRADER_USER_TEMPLATE,
)

# Document types that are always relevant for contract queries
CONTRACT_DOC_TYPES = {"actus_contract", "postman_contract"}


def grade_documents(
    query: str,
    documents: List[dict],
    llm_client,
    model: str,
    distance_threshold: float = 1.5,   # relaxed from 1.2
) -> List[dict]:
    print(f"  [GRADER] Grading {len(documents)} documents...")
    relevant_docs = []

    for i, doc in enumerate(documents):
        doc_type = doc.get("metadata", {}).get("type", "")
        source = doc.get("source", doc.get("metadata", {}).get("filename", "?"))
        distance = doc.get("distance", 0)

        # Always keep contract documents — never LLM-grade them
        if doc_type in CONTRACT_DOC_TYPES:
            relevant_docs.append(doc)
            print(f"    [{i+1}] ✅ KEPT (contract doc)     — {source}")
            continue

        # Fast distance filter for non-contract docs
        if distance > distance_threshold:
            print(f"    [{i+1}] SKIP (distance={distance:.4f}) — {source}")
            continue

        # Fast keyword overlap check — no LLM call needed
        query_words = set(query.lower().split())
        doc_text    = doc.get('text', '').lower()
        overlap     = sum(1 for w in query_words if len(w) > 3 and w in doc_text)
        score       = "yes" if overlap > 0 or distance < 1.2 else "no"

        if score == "yes":
            relevant_docs.append(doc)
            print(f"    [{i+1}] ✅ RELEVANT (overlap={overlap}, dist={distance:.3f}) — {source}")
        else:
            print(f"    [{i+1}] ❌ FILTERED (overlap={overlap}, dist={distance:.3f}) — {source}")

    print(f"  [GRADER] {len(relevant_docs)}/{len(documents)} passed")
    return relevant_docs


def grade_answer(query: str, answer: str, llm_client, model: str) -> str:
    user_message = ANSWER_GRADER_USER_TEMPLATE.format(query=query, answer=answer)

    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ANSWER_GRADER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        score = result.get("binary_score", "yes")
    except Exception as e:
        print(f"  [ANSWER GRADER] Error: {e} — default yes")
        score = "yes"

    print(f"  [ANSWER GRADER] Resolves question: {score}")
    return score
