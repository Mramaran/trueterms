import os, sys, uuid
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (COLLECTION_1_DIR, COLLECTION_2_DIR, COLLECTION_3_DIR, COLLECTION_4_DIR,
    COLLECTION_NAMES, UNIFIED_COLLECTION_NAME, CHROMA_DB_DIR,
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_NAME)
from ingestion.document_loader  import load_collection
from ingestion.document_chunker import chunk_documents
from ingestion.embedder         import get_embedding_function
from db.vector_store            import get_chroma_client, get_or_create_collection, list_collections


def ingest_collection(client, embedding_fn, collection_dir, collection_name):
    print(f"\n{'─'*60}\nINGESTING: {collection_name}\n  Source: {collection_dir}\n{'─'*60}")
    documents = load_collection(collection_dir)
    if not documents:
        print(f"  [WARNING] No documents from {collection_dir}")
        return []

    chunks     = chunk_documents(documents, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    collection = get_or_create_collection(client, collection_name, embedding_fn)

    ids = [f"{collection_name}_{uuid.uuid4().hex[:8]}" for _ in chunks]
    texts     = [c["text"]     for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    batch_size    = 50
    total_batches = (len(ids) + batch_size - 1) // batch_size
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.add(ids=ids[i:end], documents=texts[i:end], metadatas=metadatas[i:end])
        print(f"  Batch {(i//batch_size)+1}/{total_batches}: {end-i} chunks stored")

    print(f"  ✅ DONE: {collection_name} = {collection.count()} chunks")
    return chunks


def run_full_ingestion():
    print(f"\n{'='*60}\n  TRUETERMS — INGESTION\n{'='*60}")
    print(f"  ChromaDB: {CHROMA_DB_DIR}")
    print(f"  Embedding: {EMBEDDING_MODEL_NAME} (FREE, local)")

    client       = get_chroma_client(CHROMA_DB_DIR)
    embedding_fn = get_embedding_function(EMBEDDING_MODEL_NAME)

    all_chunks = []
    all_chunks.extend(ingest_collection(client, embedding_fn, COLLECTION_1_DIR, COLLECTION_NAMES["standards"]))
    all_chunks.extend(ingest_collection(client, embedding_fn, COLLECTION_2_DIR, COLLECTION_NAMES["example_contracts"]))
    all_chunks.extend(ingest_collection(client, embedding_fn, COLLECTION_3_DIR, COLLECTION_NAMES["about_actus"]))
    all_chunks.extend(ingest_collection(client, embedding_fn, COLLECTION_4_DIR, COLLECTION_NAMES["xbrl_standards"]))

    # Unified collection
    print(f"\n{'─'*60}\nCREATING UNIFIED: {UNIFIED_COLLECTION_NAME}\n{'─'*60}")
    unified   = get_or_create_collection(client, UNIFIED_COLLECTION_NAME, embedding_fn)
    ids       = [f"unified_{uuid.uuid4().hex[:8]}" for _ in all_chunks]
    texts     = [c["text"]     for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    batch_size    = 50
    total_batches = (len(ids) + batch_size - 1) // batch_size
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        unified.add(ids=ids[i:end], documents=texts[i:end], metadatas=metadatas[i:end])
        print(f"  Batch {(i//batch_size)+1}/{total_batches}: {end-i} chunks")

    print(f"\n{'='*60}\n  INGESTION COMPLETE\n{'='*60}")
    list_collections(client)
    print(f"\n  ✅ ChromaDB ready at: {CHROMA_DB_DIR}\n{'='*60}\n")

if __name__ == "__main__":
    run_full_ingestion()
