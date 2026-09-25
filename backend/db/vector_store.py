import chromadb
from pathlib import Path

def get_chroma_client(persist_dir):
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ChromaDB: {persist_dir}")
    return chromadb.PersistentClient(path=str(persist_dir))

def get_or_create_collection(client, collection_name, embedding_function=None):
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )

def list_collections(client):
    collections = client.list_collections()
    for col in collections:
        print(f"  Collection: {col.name} | Docs: {col.count()}")
    return collections

def get_vector_store(collection_name: str):
    """Get a ChromaDB collection by name — used by the MCP server."""
    from backend.config import CHROMA_DB_DIR
    client = get_chroma_client(CHROMA_DB_DIR)
    return get_or_create_collection(client, collection_name)
