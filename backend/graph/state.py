from typing import List, Optional
from typing_extensions import TypedDict

class GraphState(TypedDict):
    query: str
    language: Optional[str]
    rewritten_query: Optional[str]
    route: Optional[str]
    documents: Optional[List[dict]]
    filtered_docs: Optional[List[dict]]
    answer: Optional[str]
    sources: Optional[List[str]]
    hallucination: Optional[str]
    answer_grade: Optional[str]
    iterations: int
    web_results: Optional[List[dict]]
    query_complexity: Optional[str]   # 'simple' | 'complex'
