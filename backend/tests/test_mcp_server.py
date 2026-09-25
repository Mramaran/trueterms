"""The MCP server (the pitch's "edge") must start from its documented entry point.

Claude Desktop runs `python <project>/backend/mcp_server.py`, which put only backend/ on
sys.path. Several modules import `backend.config`, so startup died with
"ModuleNotFoundError: No module named 'backend'" before any tool was registered.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ENTRY = Path(__file__).resolve().parents[1] / "mcp_server.py"
# ACTUS unreachable: loan tools then run the local engine, so results are deterministic
OFFLINE_ENV = {**os.environ, "ACTUS_SERVER_URL": "http://127.0.0.1:9"}


async def _session(action, env=None):
    # Start from an unrelated folder, as Claude Desktop does
    params = StdioServerParameters(command=sys.executable, args=[str(ENTRY)], cwd=str(Path.home()), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await action(session)


def _run(action, env=None):
    return asyncio.run(asyncio.wait_for(_session(action, env), timeout=240))


async def _tool_names(session):
    return [tool.name for tool in (await session.list_tools()).tools]


def _call(name, arguments):
    async def action(session):
        result = await session.call_tool(name, arguments)
        return json.loads(result.content[0].text)
    return action


def test_mcp_server_starts_from_its_entry_point_and_lists_tools():
    names = _run(_tool_names)
    assert "query-trueterms" in names
    assert {"check-loan-offer", "check-loan-book"} <= set(names)
    assert not any("mentor" in name for name in names)


def test_mcp_check_loan_offer_returns_the_true_apr():
    out = _run(_call("check-loan-offer", {
        "principal": 50000, "rate_pct": 2, "rate_period": "month", "rate_type": "flat",
        "tenure_months": 12, "processing_fee": 2000}), env=OFFLINE_ENV)
    assert out["apr_pct"] == 50.1
    assert out["emi"] == 5166.67


def test_mcp_check_loan_book_explains_a_missing_source():
    out = _run(_call("check-loan-book", {}), env=OFFLINE_ENV)
    assert "exactly one" in out["error"]
