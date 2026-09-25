"""
Configuration for Agentic RAG TrueTerms
===========================================
FIXED:
  - data_collection_2 fallback path now uses correct folder name
    "data_collection_2_(example_contracts)" (with underscore before parenthesis)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── PROJECT PATHS ───────────────────────────────────────────────────────────
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# Data collections (your source documents)
DATA_DIR         = BASE_DIR / "data_collections"
COLLECTION_1_DIR = DATA_DIR / "data_collection_1(standards)"
COLLECTION_3_DIR = DATA_DIR / "data_collection_3(about_ACTUS)"
COLLECTION_4_DIR = DATA_DIR / "data_collection_4(xbrl_standards)"

# data_collection_2: use the real Contracts_data folder if present,
# otherwise fall back to the bundled example contracts folder.
# FIX: folder name is "data_collection_2_(example_contracts)" — note the underscore before "("
_CONTRACTS_DATA = BASE_DIR.parent / "Contracts_data"
if _CONTRACTS_DATA.exists():
    COLLECTION_2_DIR = _CONTRACTS_DATA
    print(f"[CONFIG] ✅ Using real Contracts_data: {_CONTRACTS_DATA}", file=sys.stderr)
else:
    COLLECTION_2_DIR = DATA_DIR / "data_collection_2_(example_contracts)"
    print(f"[CONFIG] ⚠️  WARNING: Contracts_data folder not found at {_CONTRACTS_DATA}", file=sys.stderr)
    print(f"[CONFIG]    Falling back to example contracts: {COLLECTION_2_DIR}", file=sys.stderr)

# ─── CHROMA DB PATH ──────────────────────────────────────────────────────────
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# ─── EMBEDDING MODEL (FREE, LOCAL) ───────────────────────────────────────────
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ─── CHUNKING SETTINGS ───────────────────────────────────────────────────────
# Larger chunk size for narrative/dictionary text.
# Contract docs are NEVER chunked (handled in document_chunker.py).
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 100

# ─── CHROMADB COLLECTION NAMES ───────────────────────────────────────────────
COLLECTION_NAMES = {
    "standards":         "actus_standards",
    "example_contracts": "actus_example_contracts",
    "about_actus":       "actus_about",
    "xbrl_standards":    "actus_xbrl_standards",
}

UNIFIED_COLLECTION_NAME = "actus_unified"

# ─── ANTHROPIC SETTINGS ──────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Model — uses claude-sonnet-4-6 by default (current active model Feb 2026)
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
