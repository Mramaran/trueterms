# TrueTerms MCP Server — Claude Desktop Configuration
# =========================================================
#
#   Windows : %APPDATA%\Claude\claude_desktop_config.json
#   macOS   : ~/Library/Application Support/Claude/claude_desktop_config.json
#
# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Install / update dependencies (one-time)
#
#   pip install -r requirements.txt
#
# STEP 2 — Verify your .env has ANTHROPIC_API_KEY set
#
# STEP 3 — Paste the JSON block below into claude_desktop_config.json
#          (merge with existing "mcpServers" if you already have other servers)
#
# STEP 4 — Restart Claude Desktop
# ─────────────────────────────────────────────────────────────────────────────

{
  "mcpServers": {

    "trueterms": {
      "command": "python",
      "args": [
        "PATH_TO_YOUR_PROJECT\\mcp_server.py"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE",
        "LLM_MODEL": "claude-sonnet-4-6"
      }
    }

  }
}

# ─────────────────────────────────────────────────────────────────────────────
# VALID MODEL NAMES (Feb 2026) — pick one for LLM_MODEL above:
#
#   claude-haiku-4-5-20251001   → Fast, cheapest  ✅ good for testing
#   claude-sonnet-4-6           → Smart, balanced ✅ recommended for production
#   claude-opus-4-6             → Most powerful,  ✅ highest quality answers
#
# NOTE: Old model strings like "claude-haiku-4-5" or "claude-sonnet-4-5"
#       are no longer valid. Always use the full versioned string above.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE: If you also have the ZK-PRET server registered, merge like this:
#
# {
#   "mcpServers": {
#
#     "PRET-MCP-SERVER": {
#       "command": "node",
#       "args": [
#         "PATH_TO_PRET_SERVER\\index.js"
#       ]
#     },
#
#     "trueterms": {
#       "command": "python",
#       "args": [
#         "PATH_TO_YOUR_PROJECT\\mcp_server.py"
#       ],
#       "env": {
#         "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE",
#         "LLM_MODEL": "claude-sonnet-4-6"
#       }
#     }
#
#   }
# }
# ─────────────────────────────────────────────────────────────────────────────
#
# TOOLS AVAILABLE AFTER RESTART:
#
#   query-trueterms          General ACTUS question → agentic RAG pipeline
#                               (auto-routes: vectorstore or web search)
#
#   generate-actus-contract     Generate PAM / ANN / LAM / ... contract JSON
#                               (ready to POST to ACTUS server)
#
#   search-actus-standards      Direct ChromaDB lookup of ACTUS dictionary
#                               (fast, no agentic pipeline)
#
#   run-actus-ingestion         Reload all documents into ChromaDB
#
#   get-actus-contract-types    List all 17 supported ACTUS contract types
#
# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST (run from terminal before adding to Claude Desktop):
#
#   python query.py "what is nominalInterestRate"
#   python query.py "generate a PAM contract"
# ─────────────────────────────────────────────────────────────────────────────
