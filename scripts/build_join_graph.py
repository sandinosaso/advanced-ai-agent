"""
Build join graph from MySQL schema via SQLAlchemy inspector.

Outputs:
- artifacts/join_graph_raw.json

Includes:
- tables + columns
- hard relationships from FK metadata
- inferred cardinality using UNIQUE constraints/indexes
- heuristic relationships (soft edges) based on naming conventions
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import inspect
from src.models.database import get_database


OUTPUT_PATH = os.path.join("artifacts", "join_graph_raw.json")


def norm(s: str) -> str:
    return s.lower().replace("_", "").replace("-", "")


@dataclass(frozen=True)
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    type: str  # "foreign_key" | "heuristic"
    confidence: float
    cardinality: str  # "N:1" | "1:1" | "1:N" | "N:N" | "unknown"
    evidence: Dict[str, Any]


def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def get_unique_columns(inspector, table: str) -> set[str]:
    """
    Return a set of columns that are uniquely constrained in the table.
    Uses unique constraints + unique indexes.
    """
    unique_cols: set[str] = set()

    # Unique constraints
    try:
        for uc in inspector.get_unique_constraints(table) or []:
            cols = uc.get("column_names") or []
            if len(cols) == 1:
                unique_cols.add(cols[0])
    except Exception:
        pass

    # Unique indexes
    try:
        for idx in inspector.get_indexes(table) or []:
            if idx.get("unique") and len(idx.get("column_names", [])) == 1:
                unique_cols.add(idx["column_names"][0])
    except Exception:
        pass

    return unique_cols


def infer_cardinality(
    from_table: str,
    from_col: str,
    to_table: str,
    to_col: str,
    unique_map: Dict[str, set[str]],
) -> Tuple[str, Dict[str, Any]]:
    """
    Cardinality inference heuristic (best-effort):
    - If FK column is UNIQUE => (from -> to) is 1:1 (or 0:1) relationship in practice.
      Example: profile.user_id UNIQUE -> user.id
    - Else => many rows in from can refer to one row in to => N:1.
    """
    from_is_unique = from_col in unique_map.get(from_table, set())
    to_is_unique = to_col in unique_map.get(to_table, set())  # usually 'id' unique

    evidence = {
        "from_is_unique": from_is_unique,
        "to_is_unique": to_is_unique,
    }

    if from_is_unique and to_is_unique:
        return "1:1", evidence
    if (not from_is_unique) and to_is_unique:
        return "N:1", evidence

    # Rare weird case: referenced column not unique (should not happen for good FKs)
    return "unknown", evidence


def build_join_graph() -> Dict[str, Any]:
    db = get_database()
    engine = db.engine
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    table_info: Dict[str, Dict[str, Any]] = {}
    table_columns: Dict[str, List[str]] = {}
    unique_map: Dict[str, set[str]] = {}

    # 1) tables + columns + uniques
    for t in tables:
        cols = [c["name"] for c in inspector.get_columns(t)]
        table_columns[t] = cols
        unique_map[t] = get_unique_columns(inspector, t)
        table_info[t] = {
            "columns": cols,
            "unique_columns": sorted(list(unique_map[t])),
        }

    relationships: List[Relationship] = []

    # 2) hard FK relationships
    for t in tables:
        for fk in inspector.get_foreign_keys(t) or []:
            ref_table = fk.get("referred_table")
            ref_cols = fk.get("referred_columns") or []
            src_cols = fk.get("constrained_columns") or []

            if not ref_table or not ref_cols or not src_cols:
                continue

            # handle composite FKs conservatively: store each column pair (or skip if lengths mismatch)
            if len(ref_cols) != len(src_cols):
                continue

            for src_col, ref_col in zip(src_cols, ref_cols):
                cardinality, card_evidence = infer_cardinality(
                    from_table=t,
                    from_col=src_col,
                    to_table=ref_table,
                    to_col=ref_col,
                    unique_map=unique_map,
                )

                relationships.append(
                    Relationship(
                        from_table=t,
                        from_column=src_col,
                        to_table=ref_table,
                        to_column=ref_col,
                        type="foreign_key",
                        confidence=1.0,
                        cardinality=cardinality,
                        evidence={
                            "fk_name": fk.get("name"),
                            "cardinality": card_evidence,
                        },
                    )
                )

    # 3) heuristic relationships (soft)
    # Strategy: columns ending in Id/_id that map to table name containing that stem.
    # Example: employeeId -> secure_employee OR employee
    for t, cols in table_columns.items():
        for col in cols:
            col_l = col.lower()
            if not (col_l.endswith("id") or col_l.endswith("_id")):
                continue

            stem = col_l
            if stem.endswith("_id"):
                stem = stem[:-3]
            elif stem.endswith("id"):
                stem = stem[:-2]
            stem_n = norm(stem)

            if not stem_n:
                continue

            # candidate target tables: those whose normalized name contains stem
            candidates = []
            for target in tables:
                if target == t:
                    continue
                if "id" not in [c.lower() for c in table_columns[target]]:
                    continue
                if stem_n in norm(target):
                    candidates.append(target)

            # Use first matching candidate - SQL rewriter will handle secure view conversion
            for target in candidates:
                # Only add one edge per column (first match) to reduce noise
                # The secure view rewriting happens later in sql_tool.py

                # Heuristic cardinality: assume N:1 unless the col is unique
                from_is_unique = col in unique_map.get(t, set())
                card = "1:1" if from_is_unique else "N:1"

                relationships.append(
                    Relationship(
                        from_table=t,
                        from_column=col,
                        to_table=target,
                        to_column="id",
                        type="heuristic",
                        confidence=0.70,  # pre-validation confidence
                        cardinality=card,
                        evidence={
                            "rule": "column_endswith_id_table_name_match",
                            "stem": stem,
                            "from_is_unique": from_is_unique,
                        },
                    )
                )
                break  # Only add one relationship per column

    return {
        "version": 1,
        "tables": table_info,
        "relationships": [asdict(r) for r in relationships],
    }


def main():
    ensure_dir(OUTPUT_PATH)
    graph = build_join_graph()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    print(f"✅ Wrote join graph: {OUTPUT_PATH}")
    print(f"Tables: {len(graph['tables'])}")
    print(f"Relationships: {len(graph['relationships'])}")


if __name__ == "__main__":
    main()
