#!/usr/bin/env python3
"""
TrueTerms — Environment Setup & Repair Script
=================================================
Run this ONCE before running ingestion or the MCP server.
It fixes broken packages (especially Pillow) and verifies everything works.

Usage:
    python setup_env.py

Works on: Windows, Mac, Linux
"""

import subprocess
import sys
import os

def run(cmd, label):
    print(f"\n  ▶ {label}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✅ Done")
    else:
        print(f"  ⚠️  Warning: {result.stderr.strip()[:200]}")
    return result.returncode == 0


def check_import(module, label):
    try:
        __import__(module)
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        print(f"  ❌ {label} — {e}")
        return False


print("=" * 60)
print("  TrueTerms — Environment Setup & Repair")
print("=" * 60)
print(f"\n  Python: {sys.version}")
print(f"  Executable: {sys.executable}")

# ── Step 1: Upgrade pip ───────────────────────────────────────
print("\n[1] Upgrading pip...")
run(f'"{sys.executable}" -m pip install --upgrade pip', "pip upgrade")

# ── Step 2: Fix Pillow (most common cause of failures) ────────
print("\n[2] Fixing Pillow (root cause of most ingestion errors)...")
run(f'"{sys.executable}" -m pip uninstall Pillow -y', "uninstall old Pillow")
run(f'"{sys.executable}" -m pip install Pillow --upgrade', "install fresh Pillow")

# ── Step 3: Fix sentence-transformers ─────────────────────────
print("\n[3] Fixing sentence-transformers...")
run(f'"{sys.executable}" -m pip uninstall sentence-transformers -y', "uninstall old sentence-transformers")
run(f'"{sys.executable}" -m pip install sentence-transformers --upgrade', "install fresh sentence-transformers")

# ── Step 4: Fix transformers ───────────────────────────────────
print("\n[4] Fixing transformers...")
run(f'"{sys.executable}" -m pip install transformers --upgrade', "upgrade transformers")

# ── Step 5: Fix chromadb ───────────────────────────────────────
print("\n[5] Ensuring chromadb is installed...")
run(f'"{sys.executable}" -m pip install chromadb --upgrade', "upgrade chromadb")

# ── Step 6: Install all requirements ──────────────────────────
print("\n[6] Installing all requirements from requirements.txt...")
req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
if os.path.exists(req_path):
    run(f'"{sys.executable}" -m pip install -r "{req_path}"', "install requirements.txt")
else:
    print("  ⚠️  requirements.txt not found — skipping")

# ── Step 7: Verify imports ─────────────────────────────────────
print("\n[7] Verifying critical imports...")
ok = True
ok &= check_import("PIL", "Pillow (PIL)")
ok &= check_import("PIL.Image", "PIL.Image")
ok &= check_import("chromadb", "chromadb")
ok &= check_import("sentence_transformers", "sentence_transformers")
ok &= check_import("transformers", "transformers")
ok &= check_import("langchain", "langchain")
ok &= check_import("langgraph", "langgraph")
ok &= check_import("mcp", "mcp")
ok &= check_import("anthropic", "anthropic")
ok &= check_import("dotenv", "python-dotenv")

# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if ok:
    print("  ✅ ALL CHECKS PASSED — Ready to run ingestion!")
    print("\n  Next step:")
    print("     python run_ingestion.py")
else:
    print("  ❌ Some checks failed. Try running:")
    print(f'     "{sys.executable}" -m pip install -r requirements.txt --upgrade')
    print("  Then run this script again.")
print("=" * 60)
