"""
TrueTerms — Run Ingestion
=============================
உங்கள் ACTUS_private_Context files எல்லாம்
ChromaDB-ல் load பண்றது. ஒரே ஒரு தடவை மட்டும் run பண்ணுங்க.

HOW TO RUN:
  cd <project folder>
  python run_ingestion.py

WHAT IT DOES:
  data_collection_1 → ACTUS dictionary standards
  data_collection_2 → PAM/ANN example contracts
  data_collection_3 → About ACTUS docs
  → chunks → FREE local embedding → ChromaDB stored

NO API KEY NEEDED for ingestion (embedding is local/free).
"""

import os
import sys
from pathlib import Path

script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

from dotenv import load_dotenv
load_dotenv()

from ingestion.indexer import run_full_ingestion

if __name__ == "__main__":
    run_full_ingestion()
