"""
TrueTerms — MCP Server Setup
=================================
Mirrors ZK-PRET: pretmcpserver/server.ts → startServer()

Creates the MCP Server instance and registers all tools.
Called by src/mcpserver/index.py

Author: EMBER SYNDICATE
"""

import sys
import builtins
from mcp.server import Server
from backend.config import LLM_MODEL
from src.mcpcore.tools import register_actus_tools

# Keep reference to original print before redirect
_orig_print = builtins.print


def start_server() -> Server:
    """
    Create and configure the TrueTerms MCP server.
    Mirrors ZK-PRET startServer() in server.ts
    """

    _orig_print("Initializing TrueTerms MCP Server...", file=sys.stderr)
    _orig_print(f"  Model   : {LLM_MODEL}", file=sys.stderr)

    # CRITICAL: redirect print → stderr
    # Keeps stdout clean for MCP JSON-RPC protocol
    # Same as ZK-PRET: console.log = console.error
    def _mcp_print(*args, **kwargs):
        kwargs.setdefault("file", sys.stderr)
        _orig_print(*args, **kwargs)
    builtins.print = _mcp_print

    # Create server (mirrors: new McpServer({ name: "PRET-Server", version: "1.0.0" }))
    server = Server("TrueTerms-Server")

    # Register all tools (mirrors: registerPRETTools(server))
    register_actus_tools(server)

    _orig_print("Server is ready to handle requests", file=sys.stderr)

    return server
