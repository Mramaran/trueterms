"""
Document Chunker — TrueTerms (Corrected)
============================================
Contract documents (type=actus_contract / postman_contract) are NEVER split.
They must remain whole so the generator receives a structurally complete
example to mirror.

Only large text documents (dictionaries, about-pages) are chunked.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Types that must NEVER be split — each is already one atomic unit
NO_CHUNK_TYPES = {"actus_contract", "postman_contract", "actus_dictionary"}


def chunk_documents(documents, chunk_size=1000, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunked_docs = []
    skipped_chunk = 0
    did_chunk = 0

    for doc in documents:
        text = doc["text"]
        metadata = doc["metadata"].copy()
        doc_type = metadata.get("type", "")

        # Contract and dictionary entries: always store as-is (no splitting)
        if doc_type in NO_CHUNK_TYPES or len(text) <= chunk_size:
            metadata["chunk_index"] = 0
            metadata["total_chunks"] = 1
            chunked_docs.append({"text": text, "metadata": metadata})
            skipped_chunk += 1
            continue

        # Chunk large narrative/text documents
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            m = metadata.copy()
            m["chunk_index"] = i
            m["total_chunks"] = len(chunks)
            chunked_docs.append({"text": chunk, "metadata": m})
        did_chunk += 1

    print(f"  Chunked: {len(documents)} docs → {len(chunked_docs)} chunks "
          f"({skipped_chunk} kept intact, {did_chunk} split)")
    return chunked_docs
