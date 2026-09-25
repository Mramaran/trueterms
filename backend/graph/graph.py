import os, sys
from pathlib import Path
from functools import partial

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from graph.state import GraphState
from graph.nodes import (node_router, node_retrieve, node_grade_documents,
    node_generate, node_check_hallucination, node_grade_answer,
    node_rewrite, node_web_search, node_generate_from_web)
from graph.edges import (edge_route_query, edge_after_grading,
    edge_after_hallucination, edge_after_answer_grade)
from backend.config import UNIFIED_COLLECTION_NAME


def build_graph(llm_client, model, n_results=5):
    from langgraph.graph import StateGraph, END
    workflow = StateGraph(GraphState)

    workflow.add_node("router",              partial(node_router,             llm_client=llm_client, model=model))
    workflow.add_node("retrieve",            partial(node_retrieve,           collection_name=UNIFIED_COLLECTION_NAME, n_results=n_results))
    workflow.add_node("grade_docs",          partial(node_grade_documents,    llm_client=llm_client, model=model))
    workflow.add_node("generate",            partial(node_generate,           llm_client=llm_client, model=model))
    workflow.add_node("hallucination_check", partial(node_check_hallucination,llm_client=llm_client, model=model))
    workflow.add_node("grade_answer",        partial(node_grade_answer,       llm_client=llm_client, model=model))
    workflow.add_node("rewrite",             partial(node_rewrite,            llm_client=llm_client, model=model))
    workflow.add_node("web_search",          node_web_search)
    workflow.add_node("generate_from_web",   partial(node_generate_from_web,  llm_client=llm_client, model=model))

    workflow.set_entry_point("router")
    workflow.add_conditional_edges("router",     edge_route_query,        {"retrieve": "retrieve", "web_search": "web_search"})
    workflow.add_edge("retrieve", "grade_docs")
    workflow.add_conditional_edges("grade_docs", edge_after_grading,      {"generate": "generate", "rewrite": "rewrite", "web_search": "web_search"})
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("web_search", "generate_from_web")
    workflow.add_edge("generate", "hallucination_check")
    workflow.add_edge("generate_from_web", END)
    workflow.add_conditional_edges("hallucination_check", edge_after_hallucination, {"grade_answer": "grade_answer", "generate": "generate"})
    workflow.add_conditional_edges("grade_answer", edge_after_answer_grade, {"END": END, "rewrite": "rewrite"})

    return workflow.compile()


_graph_cache = {}

def run_query(query, llm_client, model, n_results=5, language='en'):
    print(f"\n{'='*60}\n  TRUETERMS PIPELINE\n  Query: {query}\n{'='*60}")
    cache_key = f"{model}_{n_results}"
    if cache_key not in _graph_cache:
        _graph_cache[cache_key] = build_graph(llm_client, model, n_results)
        print("  [GRAPH] Built and cached")
    app = _graph_cache[cache_key]

    initial_state: GraphState = {
        "query": query, "language": language, "rewritten_query": None, "route": None,
        "documents": None, "filtered_docs": None, "answer": None,
        "sources": None, "hallucination": None, "answer_grade": None,
        "iterations": 0, "web_results": None, "query_complexity": None,
    }

    final_state = app.invoke(initial_state)
    print(f"\n{'='*60}\n  PIPELINE COMPLETE | Route: {final_state.get('route')} | Iterations: {final_state.get('iterations',0)}\n{'='*60}")

    complexity = final_state.get('query_complexity', 'complex')
    print(f"  [MODE] {complexity.upper()} — {'fast path (grading skipped)' if complexity == 'simple' else 'full pipeline'}")

    return {
        "query":                query,
        "answer":               final_state.get("answer", "No answer generated."),
        "sources":              final_state.get("sources", []),
        "route_taken":          final_state.get("route", "vectorstore"),
        "documents_retrieved":  len(final_state.get("documents") or []),
        "documents_used":       len(final_state.get("filtered_docs") or []),
        "hallucination_check":  final_state.get("hallucination", "N/A"),
        "iterations":           final_state.get("iterations", 0),
        "query_complexity":     complexity,
    }
