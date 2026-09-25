"""
Web Search Agent
================
Used only as a fallback when the answer is not found in the vector store.

Uses DuckDuckGo — free and does not require an API key.
"""

import os
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))


def web_search(query: str, max_results: int = 5) -> List[dict]:
    return _duckduckgo_search(query, max_results)


def _duckduckgo_search(query: str, max_results: int) -> List[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url":     r.get("href", ""),
                })
        print(f"  [WEB SEARCH] {len(results)} results for: \"{query[:60]}\"")
        return results
    except ImportError:
        print(f"  [WEB SEARCH] Install: pip install duckduckgo-search")
        return []
    except Exception as e:
        print(f"  [WEB SEARCH] Failed: {e}")
        return []
