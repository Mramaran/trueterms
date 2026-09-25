"""
Graph Edges — TrueTerms
===========================
FIXED:
  - edge_after_hallucination: Added clear comments explaining the
    counter-intuitive naming convention:
      "yes" = answer IS grounded in docs (NOT hallucinated) → proceed
      "no"  = answer IS hallucinated (NOT grounded)         → regenerate
    This matches the hallucination_prompts.py definition:
      "yes" = every claim is traceable to the documents (grounded)
      "no"  = answer contains facts not in documents (hallucinated)
"""

from graph.state import GraphState

MAX_ITERATIONS = 3


def edge_route_query(state: GraphState) -> str:
    route = state.get("route", "vectorstore")
    print(f"  [EDGE] route → {route}")
    return "web_search" if route == "web_search" else "retrieve"


def edge_after_grading(state: GraphState) -> str:
    filtered   = state.get("filtered_docs", [])
    iterations = state.get("iterations", 0)

    if filtered:
        print(f"  [EDGE] grading → generate ({len(filtered)} docs)")
        return "generate"
    if iterations < MAX_ITERATIONS:
        print(f"  [EDGE] grading → rewrite (no relevant docs)")
        return "rewrite"
    print(f"  [EDGE] grading → web_search (max iterations reached)")
    return "web_search"


def edge_after_hallucination(state: GraphState) -> str:
    """
    Routing after hallucination check.

    IMPORTANT — naming convention (matches hallucination_prompts.py):
      hallucination == "yes"  →  answer IS grounded (NOT hallucinated)  → continue to grade_answer
      hallucination == "no"   →  answer IS hallucinated (NOT grounded)  → regenerate

    This is intentionally named from the perspective of the grounding check,
    NOT from the perspective of "is there a hallucination?".
    """
    hallucination = state.get("hallucination", "yes")
    iterations    = state.get("iterations", 0)

    if hallucination == "yes":
        # "yes" = grounded → proceed to grade the answer quality
        print(f"  [EDGE] hallucination → grade_answer (answer is GROUNDED ✓)")
        return "grade_answer"

    # "no" = hallucinated → try to regenerate
    if iterations < MAX_ITERATIONS:
        print(f"  [EDGE] hallucination → generate (answer HALLUCINATED ✗, regenerating...)")
        return "generate"

    # Max iterations reached — pass through anyway to avoid infinite loop
    print(f"  [EDGE] hallucination → grade_answer (max iterations reached, passing through)")
    return "grade_answer"


def edge_after_answer_grade(state: GraphState) -> str:
    """
    Routing after answer quality grade.
      answer_grade == "yes"  →  answer resolves the question → END
      answer_grade == "no"   →  answer does not resolve      → rewrite and retry
    """
    answer_grade = state.get("answer_grade", "yes")
    iterations   = state.get("iterations", 0)

    if answer_grade == "yes":
        print(f"  [EDGE] answer_grade → END (question resolved ✓)")
        return "END"
    if iterations < MAX_ITERATIONS:
        print(f"  [EDGE] answer_grade → rewrite (answer insufficient, retrying...)")
        return "rewrite"

    print(f"  [EDGE] answer_grade → END (max iterations reached)")
    return "END"
