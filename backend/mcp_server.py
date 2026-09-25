"""
TrueTerms — Root Entry Point
=================================
Claude Desktop config points here.
Delegates to src/mcpserver/index.py

Structure (mirrors ZK-PRET):
    mcp_server.py              ← claude_desktop_config.json points here
    src/
        mcpserver/
            index.py           ← mirrors pretmcpserver/index.ts
            server.py          ← mirrors pretmcpserver/server.ts
        mcpcore/
            tools.py           ← mirrors pretmcpcore/tools.ts

Author: EMBER SYNDICATE
"""

import os
import sys
import asyncio
from pathlib import Path

# ── PROJECT ROOT on sys.path ─────────────────────────────────────────────────
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(PROJECT_ROOT))
# Modules import both flat ("src.mcpcore", "graph") and as "backend.config", so the folder
# above backend/ must be importable too, as it is when uvicorn runs the web API.
sys.path.insert(1, str(PROJECT_ROOT.parent))
os.chdir(PROJECT_ROOT)

# ── Load .env ────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Delegate to src/mcpserver/index.py ───────────────────────────────────────
from src.mcpserver.index import main

if __name__ == "__main__":
    asyncio.run(main())
