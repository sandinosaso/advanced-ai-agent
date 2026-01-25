"""
Auto-build Join Graph from MySQL schema.

Extracts:
- Tables + columns
- Hard relationships (foreign keys)
- Soft relationships (heuristic column matching)

Output:
- join_graph.json
"""

import json
from collections import defaultdict
from sqlalchemy import inspect
from src.models.database import get_database


OUTPUT_FILE = "join_graph.json"


def normalize(name: str) -> str:
    """Normalize identifiers for comparison"""
    return name.lower().replace("_", "")


def build_join_graph():
    db = get_database()
    engine = db.engine
    inspector = inspect(engine)

    graph = {
        "tables": {},
        "relationships": []
    }

    # --------------------------------------------------
    # 1. Extract tables + columns
    # --------------------------------------------------
    table_columns = {}

    for table in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns(table)]
        graph["tables"][table] = {"columns": columns}
        table_columns[table] = columns

    # --------------------------------------------------
    # 2. Hard relationships (Foreign Keys)
    # --------------------------------------------------
    for table in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table):
            if not fk["referred_table"]:
                continue

            graph["relationships"].append({
                "from_table": table,
                "from_column": fk["constrained_columns"][0],
                "to_table": fk["referred_table"],
                "to_column": fk["referred_columns"][0],
                "type": "foreign_key",
                "confidence": 1.0
            })

    # --------------------------------------------------
    # 3. Heuristic relationships (soft)
    # --------------------------------------------------
    for table, columns in table_columns.items():
        for col in columns:
            if not col.lower().endswith("id"):
                continue

            col_root = normalize(col[:-2])  # employeeId → employee

            for target_table, target_columns in table_columns.items():
                if table == target_table:
                    continue

                if "id" not in target_columns:
                    continue

                if col_root in normalize(target_table):
                    graph["relationships"].append({
                        "from_table": table,
                        "from_column": col,
                        "to_table": target_table,
                        "to_column": "id",
                        "type": "heuristic",
                        "confidence": 0.75
                    })

    return graph


def main():
    graph = build_join_graph()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"✅ Join graph written to {OUTPUT_FILE}")
    print(f"Tables: {len(graph['tables'])}")
    print(f"Relationships: {len(graph['relationships'])}")


if __name__ == "__main__":
    main()
