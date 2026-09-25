"""
Retriever Agent
===============
Searches ChromaDB for chunks that are similar to the query.

Only files from your data_collections are searched.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import UNIFIED_COLLECTION_NAME, CHROMA_DB_DIR, EMBEDDING_MODEL_NAME
from db.vector_store import get_chroma_client, get_or_create_collection
from ingestion.embedder import get_embedding_function

_client       = None
_embedding_fn = None
_collections  = {}


def _get_client_and_embedding():
    global _client, _embedding_fn
    if _client is None:
        _client = get_chroma_client(CHROMA_DB_DIR)
    if _embedding_fn is None:
        _embedding_fn = get_embedding_function(EMBEDDING_MODEL_NAME)
    return _client, _embedding_fn


def retrieve_documents(
    query: str,
    collection_name: Optional[str] = None,
    n_results: int = 5,
) -> List[dict]:
    """
    உங்கள் data source-இல் இருந்து query-க்கு
    closest matching chunks retrieve பண்றது.
    """
    collection_name = collection_name or UNIFIED_COLLECTION_NAME
    client, embedding_fn = _get_client_and_embedding()

    global _collections
    if collection_name not in _collections:
        _collections[collection_name] = get_or_create_collection(
            client, collection_name, embedding_fn
        )

    collection = _collections[collection_name]
    total_docs = collection.count()

    if total_docs == 0:
        print(f"  [RETRIEVER] ⚠️  ChromaDB empty! Run: python run_ingestion.py")
        return []

    n_results = min(n_results, total_docs)
    print(f"  [RETRIEVER] Searching {total_docs} chunks for: \"{query[:60]}\"")

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    documents = []
    for i in range(len(results["documents"][0])):
        text     = results["documents"][0][i]
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        documents.append({
            "text":     text,
            "source":   metadata.get("filename", metadata.get("source", "unknown")),
            "doc_type": metadata.get("type", "unknown"),
            "distance": round(distance, 4),
            "metadata": metadata,
        })

    print(f"  [RETRIEVER] Retrieved {len(documents)} docs:")
    for i, doc in enumerate(documents):
        print(f"    [{i+1}] {doc['source']} (dist={doc['distance']:.4f})")

    return documents
