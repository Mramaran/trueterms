"""
Rewriter Agent
==============
If the first retrieval fails, it rewrites the query
to retrieve better results.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.rewriter_prompts import REWRITER_SYSTEM_PROMPT, REWRITER_USER_TEMPLATE


def rewrite_query(query: str, llm_client, model: str) -> str:
    user_message = REWRITER_USER_TEMPLATE.format(query=query)

    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0,
    )

    rewritten = response.choices[0].message.content.strip().strip('"').strip("'")
    print(f"  [REWRITER] \"{query}\" → \"{rewritten}\"")
    return rewritten
