"""Regression: a log line must never turn an API request into a 500.

On Windows a piped stdout (log file, service manager, IDE preview) defaults to
cp1252 with errors="strict". /loan/check-offer logs "2% per month flat ≈ 24% a year";
U+2248 is not in cp1252, so the print raised inside the request. The chat pipeline
(─ → ✅), /voice-contract (→) and the XBRL generator (✅) print the same way.
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]   # project root

SCRIPT = """
from fastapi.testclient import TestClient
import backend.api_server as api
import loan_truth

def _offline(*args, **kwargs):
    raise loan_truth.ActusUnavailable("offline for this test")

loan_truth.run_actus = _offline
client = TestClient(api.app)
r = client.post("/loan/check-offer", json={"terms": {
    "principal": 50000, "rate_pct": 2, "rate_period": "month", "rate_type": "flat",
    "tenure_months": 12, "processing_fee": 2000}})
print("STATUS", r.status_code, round(r.json()["apr_pct"], 1))
print("SYMBOLS \\u2192 \\u2705 \\u2500 \\u20b9")
"""


def test_api_survives_a_strict_cp1252_stdout():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    proc = subprocess.run([sys.executable, "-c", SCRIPT], cwd=PROJECT_ROOT, env=env,
                          capture_output=True, timeout=300)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    assert proc.returncode == 0, err[-3000:]
    assert "STATUS 200 50.1" in out
    assert "SYMBOLS → ✅ ─ ₹" in out
