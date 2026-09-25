"""
TrueTerms — MCP Server Entry Point
=======================================
Mirrors ZK-PRET: pretmcpserver/index.ts → main()

Sets up stdio transport and starts the server.

Usage:
    py -3.11 mcp_server.py   ← runs this via mcp_server.py

Author: EMBER SYNDICATE
"""

import os
import sys
import asyncio
from pathlib import Path

# ── PROJECT ROOT on sys.path ─────────────────────────────────────────────────
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# ── Load .env ────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── MCP stdio transport ──────────────────────────────────────────────────────
from mcp.server.stdio import stdio_server

# ── Server setup ─────────────────────────────────────────────────────────────
from src.mcpserver.server import start_server


async def main():
    """
    Entry point — mirrors ZK-PRET index.ts main()

    TypeScript:
        const server = await startServer();
        const transport = new StdioServerTransport();
        await server.connect(transport);

    Python equivalent:
    """
    try:
        server = start_server()

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
