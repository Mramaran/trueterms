"""
TrueTerms — Query (Corrected)
==================================
Usage:
  python query.py "generate a PAM contract"
  python query.py "generate a PAM contract with risk factor"
  python query.py "generate an ANN contract"
  python query.py "generate a LAM contract"
  python query.py "what is nominalInterestRate"
  python query.py "what ACTUS events does PAM produce"
  python query.py              ← interactive mode
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.anthropic_client import get_llm_client
from graph.graph import run_query
from backend.config import LLM_MODEL


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("\n" + "="*60)
        print("  TrueTerms — Interactive Query Mode")
        print("  Examples:")
        print('    generate a PAM contract')
        print('    generate a PAM contract with risk factor')
        print('    generate an ANN contract')
        print('    generate an ANN contract with risk factor')
        print('    generate a LAM contract')
        print('    what is nominalInterestRate')
        print("  Type 'quit' to exit")
        print("="*60 + "\n")
        query = input("  Your question: ").strip()

    if not query or query.lower() in ("quit", "exit"):
        print("  Goodbye!")
        return

    try:
        llm_client = get_llm_client()
    except ValueError as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)

    model = LLM_MODEL
    print(f"\n  Model : {model}")
    print(f"  Query : {query}\n")

    result = run_query(
        query=query,
        llm_client=llm_client,
        model=model,
        n_results=10,   # increased — more contract examples = better generation
    )

    print(f"\n{'='*60}")
    print(f"  ANSWER")
    print(f"{'='*60}\n")
    print(result['answer'])

    print(f"\n{'─'*60}")
    print(f"  Route      : {result['route_taken']}")
    print(f"  Docs used  : {result['documents_used']}/{result['documents_retrieved']}")
    print(f"  Grounded   : {result['hallucination_check']}")
    print(f"  Iterations : {result['iterations']}")
    if result['sources']:
        print(f"  Sources:")
        for s in result['sources']:
            print(f"    ✅ {s}")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
