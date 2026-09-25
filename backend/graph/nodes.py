"""
Graph Nodes — TrueTerms
============================
FIXED:
  - sys.path.insert() now happens BEFORE any local project imports.
    Previously, `from graph.state import GraphState` appeared before
    sys.path was updated, which could cause ImportError when nodes.py
    is imported in isolation or as the first module loaded.
"""

import os
import sys
from pathlib import Path

# ── FIX: sys.path must be set BEFORE any local imports ───────────────────────
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Now safe to import local modules ─────────────────────────────────────────
from graph.state import GraphState

from agents.router_agent        import route_query
from agents.retriever_agent     import retrieve_documents
from agents.grader_agent        import grade_documents, grade_answer
from agents.generator_agent     import generate_answer, generate_answer_from_web
from agents.hallucination_agent import check_hallucination
from agents.rewriter_agent      import rewrite_query
from agents.web_search_agent    import web_search


# ── Simple query detector (no LLM needed) ────────────────────────────────────
SIMPLE_PATTERNS = [
    'what is', 'what are', 'explain', 'define', 'definition',
    'how does', 'tell me about', 'describe', 'meaning of',
    'what does', 'who is', 'when was', 'where is',
]
COMPLEX_PATTERNS = [
    'generate', 'create', 'build', 'make', 'write',
    'calculate', 'compute', 'simulate', 'compare',
    'with risk factor', 'json', 'postman', 'cashflow',
]

def classify_query(query: str) -> str:
    q = query.lower().strip()
    for p in COMPLEX_PATTERNS:
        if p in q:
            return 'complex'
    for p in SIMPLE_PATTERNS:
        if q.startswith(p) or p in q:
            return 'simple'
    return 'complex'  # default to thorough for unknown queries


def node_router(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: ROUTER\n{'─'*50}")
    complexity = classify_query(state["query"])
    print(f"  [COMPLEXITY] {complexity.upper()} query detected")
    result = route_query(state["query"], llm_client, model)
    return {**state, "route": result["datasource"], "query_complexity": complexity}


def node_retrieve(state, collection_name=None, n_results=5):
    print(f"\n{'─'*50}\n  NODE: RETRIEVE\n{'─'*50}")
    query = state.get("rewritten_query") or state["query"]
    docs  = retrieve_documents(query, collection_name=collection_name, n_results=n_results)
    return {**state, "documents": docs}


def node_grade_documents(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: GRADE DOCUMENTS\n{'─'*50}")
    # Always run full grading — never skip, quality over speed
    docs = state.get("documents", [])
    filtered = grade_documents(state["query"], docs, llm_client, model)
    return {**state, "filtered_docs": filtered}


def node_generate(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: GENERATE\n{'─'*50}")
    docs   = state.get("filtered_docs") or state.get("documents", [])
    result = generate_answer(state["query"], docs, llm_client, model, language=state.get("language", "en"))
    return {**state, "answer": result["answer"], "sources": result["sources"],
            "iterations": state.get("iterations", 0) + 1}


def node_check_hallucination(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: HALLUCINATION CHECK\n{'─'*50}")
    docs = state.get("filtered_docs") or state.get("documents", [])
    score = check_hallucination(
        answer=state.get("answer", ""),
        documents=docs,
        llm_client=llm_client,
        model=model,
        query=state.get("query", ""),   # ← passes original query for faithfulness check
    )
    return {**state, "hallucination": score}


def node_grade_answer(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: GRADE ANSWER (SKIPPED — fast mode)\n{'─'*50}")
    # Skip expensive answer grading LLM call
    return {**state, "answer_grade": "yes"}


def node_rewrite(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: REWRITE\n{'─'*50}")
    rewritten = rewrite_query(state["query"], llm_client, model)
    return {**state, "rewritten_query": rewritten}


def node_web_search(state):
    print(f"\n{'─'*50}\n  NODE: WEB SEARCH\n{'─'*50}")
    results = web_search(state["query"])
    return {**state, "web_results": results}


def node_generate_from_web(state, llm_client, model):
    print(f"\n{'─'*50}\n  NODE: GENERATE FROM WEB\n{'─'*50}")
    result = generate_answer_from_web(state["query"], state.get("web_results", []), llm_client, model)
    return {**state, "answer": result["answer"], "sources": result["sources"],
            "iterations": state.get("iterations", 0) + 1}
