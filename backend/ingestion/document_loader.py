"""
Document Loader — TrueTerms (Corrected)
==========================================
Loads contract data files WITHOUT chunking contract JSON objects.
Each complete contract payload is stored as one unit so the generator
always receives a structurally complete example to mirror.

Supports:
  .txt  — curl command files (extracts embedded JSON payload intact)
  .json — Postman collections (each item body stored as one doc)
  .md   — plain text
"""

import json
import re
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_json_from_curl(text: str):
    """
    Pull the JSON payload out of a curl --data '...' command.
    Returns the parsed dict and the raw JSON string, or (None, None).
    """
    # Match --data '...' or --data "..."
    m = re.search(r"--data\s+'(.*?)'\s+http", text, re.DOTALL)
    if not m:
        m = re.search(r'--data\s+"(.*?)"\s+http', text, re.DOTALL)
    if not m:
        return None, None
    raw = m.group(1).strip()
    try:
        parsed = json.loads(raw)
        return parsed, raw
    except json.JSONDecodeError:
        return None, raw


def _contract_type_from_payload(payload: dict) -> str:
    """Infer the primary contract type from a payload dict."""
    contracts = payload.get("contracts", [])
    if contracts:
        return contracts[0].get("contractType", "UNKNOWN")
    return "UNKNOWN"


def _has_risk_factors(payload: dict) -> bool:
    rf = payload.get("riskFactors", [])
    return bool(rf)


def _describe_payload(payload: dict, filename: str) -> str:
    """
    Build a rich human-readable description of a contract payload.
    This is what gets embedded — rich text so the embedding model
    can find it semantically.
    """
    ct = _contract_type_from_payload(payload)
    has_rf = _has_risk_factors(payload)
    rf_label = "WITH risk factors" if has_rf else "WITHOUT risk factors"

    contracts = payload.get("contracts", [])
    lines = [
        f"ACTUS contract example: {ct} {rf_label}",
        f"Source file: {filename}",
        f"Number of contracts: {len(contracts)}",
        "",
    ]

    for i, c in enumerate(contracts):
        lines.append(f"Contract {i+1}:")
        for k, v in c.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    if has_rf:
        for rf in payload.get("riskFactors", []):
            lines.append(f"Risk factor marketObjectCode: {rf.get('marketObjectCode', '')}")
            lines.append(f"  base: {rf.get('base', '')}")
            data_pts = rf.get("data", [])
            if data_pts:
                lines.append(f"  data points: {len(data_pts)}")
                lines.append(f"  first: {data_pts[0]}")
                lines.append(f"  last:  {data_pts[-1]}")
            lines.append("")

    # Append the raw JSON so the generator can copy field patterns exactly
    lines.append("EXACT JSON PAYLOAD (copy field names and value formats from this):")
    lines.append(json.dumps(payload, indent=2))

    return "\n".join(lines)


# ── File-type loaders ─────────────────────────────────────────────────────────

def _load_curl_txt(file_path: Path):
    """Load a .txt curl command file — extract and store the JSON payload intact."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [SKIP] Cannot read {file_path.name}: {e}")
        return []

    payload, raw_json = _extract_json_from_curl(text)
    if payload is None:
        # Not a curl file — treat as plain text
        return [{
            "text": text,
            "metadata": {
                "source": str(file_path),
                "filename": file_path.name,
                "type": "txt",
                "contract_type": "UNKNOWN",
                "has_risk_factors": False,
            }
        }]

    ct = _contract_type_from_payload(payload)
    has_rf = _has_risk_factors(payload)
    description = _describe_payload(payload, file_path.name)

    print(f"  [OK] {file_path.name} — {ct} {'w/' if has_rf else 'no'} risk factors")
    return [{
        "text": description,
        "metadata": {
            "source": str(file_path),
            "filename": file_path.name,
            "type": "actus_contract",
            "contract_type": ct,
            "has_risk_factors": has_rf,
            "raw_json": json.dumps(payload),   # stored in metadata for direct use
        }
    }]


def _load_postman_collection(data: dict, file_path: Path):
    """Extract each Postman request body as one document."""
    docs = []
    items = data.get("item", [])
    collection_name = data.get("info", {}).get("name", file_path.name)

    for item in items:
        name = item.get("name", "Unknown")
        body_raw = item.get("request", {}).get("body", {}).get("raw", "")
        if not body_raw.strip():
            continue

        try:
            payload = json.loads(body_raw)
        except json.JSONDecodeError:
            # Body is not JSON (natural language input format) — store as-is
            docs.append({
                "text": f"Postman example: {name}\nCollection: {collection_name}\nBody: {body_raw}",
                "metadata": {
                    "source": str(file_path),
                    "filename": file_path.name,
                    "type": "postman_example",
                    "example_name": name,
                    "contract_type": "UNKNOWN",
                    "has_risk_factors": False,
                }
            })
            continue

        ct = _contract_type_from_payload(payload)
        has_rf = _has_risk_factors(payload)
        description = _describe_payload(payload, f"{collection_name}/{name}")

        docs.append({
            "text": description,
            "metadata": {
                "source": str(file_path),
                "filename": file_path.name,
                "type": "postman_contract",
                "example_name": name,
                "contract_type": ct,
                "has_risk_factors": has_rf,
                "raw_json": json.dumps(payload),
            }
        })

    print(f"  [OK] Postman: {len(docs)} examples from {file_path.name}")
    return docs


def _load_actus_dictionary(data: dict, file_path: Path):
    """Load ACTUS dictionary JSON — each entry becomes one document."""
    docs = []
    for section_key, section_val in data.items():
        if section_key == "version":
            continue
        if isinstance(section_val, dict):
            for entry_id, entry in section_val.items():
                if isinstance(entry, dict):
                    parts = [f"[{section_key.upper()} - {entry_id}]"]
                    for field, val in entry.items():
                        if isinstance(val, list):
                            val = ", ".join(str(v) for v in val) if val else "N/A"
                        parts.append(f"{field}: {val}")
                    docs.append({
                        "text": "\n".join(parts),
                        "metadata": {
                            "source": str(file_path),
                            "filename": file_path.name,
                            "type": "actus_dictionary",
                            "dictionary_section": section_key,
                            "entry_id": entry_id,
                        }
                    })
    print(f"  [OK] Dictionary: {len(docs)} entries from {file_path.name}")
    return docs


def load_single_file(file_path):
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    name = file_path.name

    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [SKIP] Cannot read {name}: {e}")
        return []

    if not raw.strip():
        print(f"  [SKIP] Empty: {name}")
        return []

    if suffix == ".txt":
        return _load_curl_txt(file_path)

    if suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  [SKIP] Invalid JSON {name}: {e}")
            return []

        # Distinguish Postman collections from ACTUS dictionary files
        if "item" in data:
            return _load_postman_collection(data, file_path)
        elif "dictionary" in name.lower() or "taxonomy" in name.lower() or "terms" in name.lower() or "applicability" in name.lower():
            return _load_actus_dictionary(data, file_path)
        else:
            # Generic JSON — store as-is
            return [{
                "text": raw,
                "metadata": {
                    "source": str(file_path),
                    "filename": name,
                    "type": "json",
                }
            }]

    if suffix in (".md",):
        return [{
            "text": raw,
            "metadata": {
                "source": str(file_path),
                "filename": name,
                "type": "md",
            }
        }]

    print(f"  [SKIP] Unsupported: {name}")
    return []


def load_collection(collection_dir):
    collection_dir = Path(collection_dir)
    if not collection_dir.exists():
        print(f"[ERROR] Not found: {collection_dir}")
        return []

    print(f"\n{'='*60}\nLoading: {collection_dir.name}\n{'='*60}")
    all_docs = []
    for f in sorted(collection_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            all_docs.extend(load_single_file(f))

    print(f"  TOTAL: {len(all_docs)} documents from {collection_dir.name}")
    return all_docs
