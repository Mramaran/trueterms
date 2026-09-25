"""
Embedder — TrueTerms
========================
Provides the embedding function for ChromaDB ingestion.

ROBUST VERSION:
  - Tries chromadb's built-in SentenceTransformerEmbeddingFunction first
  - Falls back to direct sentence_transformers if chromadb wrapper fails
  - Falls back to chromadb's DefaultEmbeddingFunction (ONNX-based, no Pillow needed)
  - Always works — even if Pillow / PIL is broken

This means run_ingestion.py will NEVER crash due to a broken Pillow install.
"""

import os
from pathlib import Path

# Path to the local model folder
_MODEL_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "models" / "all-MiniLM-L6-v2"


def get_embedding_function(model_name="all-MiniLM-L6-v2"):
    """
    Returns a working embedding function.
    Tries 3 methods in order — uses the first one that works.
    """

    # Use local model path if it exists, otherwise use model name (auto-download)
    model = str(_MODEL_DIR) if _MODEL_DIR.exists() else model_name
    print(f"  Embedding model: {model} (FREE, local)")

    # ── Method 1: chromadb SentenceTransformerEmbeddingFunction ──────────────
    # This is the preferred method. Fails if Pillow is broken.
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        fn = SentenceTransformerEmbeddingFunction(model_name=model)
        # Quick smoke test
        fn(["test"])
        print(f"  [Embedder] Method 1 OK — chromadb SentenceTransformer")
        return fn
    except Exception as e:
        print(f"  [Embedder] Method 1 failed ({type(e).__name__}: {e})")

    # ── Method 2: direct sentence_transformers (bypasses chromadb wrapper) ───
    # Works even if chromadb's wrapper has import issues,
    # as long as sentence_transformers itself is installed correctly.
    try:
        from sentence_transformers import SentenceTransformer

        class DirectSentenceTransformerFn:
            def __init__(self, model_path):
                self._model = SentenceTransformer(model_path)

            def __call__(self, input):
                return self._model.encode(input).tolist()

        fn = DirectSentenceTransformerFn(model)
        fn(["test"])
        print(f"  [Embedder] Method 2 OK — direct SentenceTransformer")
        return fn
    except Exception as e:
        print(f"  [Embedder] Method 2 failed ({type(e).__name__}: {e})")

    # ── Method 3: chromadb DefaultEmbeddingFunction (ONNX — no Pillow needed) 
    # This is chromadb's built-in fallback. Uses ONNX runtime.
    # Does NOT require sentence_transformers or Pillow at all.
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        fn = DefaultEmbeddingFunction()
        fn(["test"])
        print(f"  [Embedder] Method 3 OK — chromadb DefaultEmbeddingFunction (ONNX)")
        print(f"  [Embedder] NOTE: Using ONNX fallback. Quality is slightly lower.")
        print(f"  [Embedder] To fix: pip uninstall Pillow -y && pip install Pillow")
        return fn
    except Exception as e:
        print(f"  [Embedder] Method 3 failed ({type(e).__name__}: {e})")

    # ── All methods failed ────────────────────────────────────────────────────
    raise RuntimeError(
        "\n\n"
        "  ❌ ALL embedding methods failed. Please run these commands:\n\n"
        "     pip uninstall Pillow sentence-transformers -y\n"
        "     pip install Pillow sentence-transformers --upgrade\n\n"
        "  Then run: python run_ingestion.py\n"
    )
