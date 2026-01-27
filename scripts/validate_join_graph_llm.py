"""
LLM validation pass for heuristic relationships.

Input:
- artifacts/join_graph_raw.json

Output:
- artifacts/join_graph_validated.json

Approach:
- Only validate relationships where type == "heuristic"
- Provide the LLM: table names, columns, and (optionally) a few sample rows
- LLM returns YES/NO + confidence 0..1 + brief reason
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, Any, List, Tuple
from langchain_openai import ChatOpenAI
from sqlalchemy import text

from src.models.database import get_database
from src.utils.config import settings


RAW_PATH = os.path.join("artifacts", "join_graph_raw.json")
OUT_PATH = os.path.join("artifacts", "join_graph_validated.json")


def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def fetch_samples(table: str, columns: List[str], limit: int = 3) -> List[Dict[str, Any]]:
    """
    Pull a few sample rows for grounding. Keep it tiny to control cost.
    """
    db = get_database()
    engine = db.engine

    # pick a safe subset of columns: avoid huge text/blob
    chosen = columns[: min(len(columns), 8)]
    cols_sql = ", ".join([f"`{c}`" for c in chosen])

    q = text(f"SELECT {cols_sql} FROM `{table}` LIMIT :lim")
    with engine.connect() as conn:
        rows = conn.execute(q, {"lim": limit}).mappings().all()
        return [dict(r) for r in rows]


def parse_llm_answer(s: str) -> Tuple[bool, float, str]:
    """
    Expected format:
    VALID: YES|NO
    CONFIDENCE: 0.xx
    REASON: ...
    """
    valid = bool(re.search(r"VALID:\s*YES", s, re.I))
    conf_m = re.search(r"CONFIDENCE:\s*([0-1](?:\.\d+)?)", s, re.I)
    conf = float(conf_m.group(1)) if conf_m else (0.5 if valid else 0.2)
    reason_m = re.search(r"REASON:\s*(.*)", s, re.I | re.S)
    reason = (reason_m.group(1).strip() if reason_m else s.strip())[:500]
    return valid, max(0.0, min(1.0, conf)), reason


def main():
    ensure_dir(OUT_PATH)

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        max_completion_tokens=300,
    )

    tables = graph["tables"]
    rels = graph["relationships"]

    validated = []
    for r in rels:
        if r["type"] != "heuristic":
            validated.append(r)
            continue

        ft, fc = r["from_table"], r["from_column"]
        tt, tc = r["to_table"], r["to_column"]

        from_cols = tables.get(ft, {}).get("columns", [])
        to_cols = tables.get(tt, {}).get("columns", [])

        # Optional sampling (can be disabled if too slow or permissions restricted)
        from_samples = fetch_samples(ft, from_cols, limit=3) if from_cols else []
        to_samples = fetch_samples(tt, to_cols, limit=3) if to_cols else []

        prompt = f"""
You are validating a proposed database relationship for SQL join correctness.

Proposed relationship:
- FROM: {ft}.{fc}
- TO:   {tt}.{tc}
- Proposed cardinality: {r.get("cardinality", "unknown")}

FROM table columns: {from_cols}
TO table columns: {to_cols}

FROM sample rows (up to 3): {from_samples}
TO sample rows (up to 3): {to_samples}

Question:
Is this relationship a semantically valid foreign-key-like join in a typical business schema?
If unsure, answer NO.

Return exactly this format:

VALID: YES or NO
CONFIDENCE: 0.xx
REASON: one short reason
"""
        resp = llm.invoke(prompt).content
        is_valid, conf, reason = parse_llm_answer(resp)

        # Promote/demote confidence
        if is_valid:
            r["confidence"] = max(r.get("confidence", 0.7), conf)
            r["evidence"]["llm_validated"] = True
        else:
            r["confidence"] = min(r.get("confidence", 0.7), 0.25)
            r["evidence"]["llm_validated"] = False

        r["evidence"]["llm_reason"] = reason

        validated.append(r)

    graph_out = {
        **graph,
        "validated_version": 1,
        "relationships": validated,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_out, f, indent=2)

    print(f"✅ Wrote validated join graph: {OUT_PATH}")
    print(f"Relationships: {len(validated)}")


if __name__ == "__main__":
    main()
