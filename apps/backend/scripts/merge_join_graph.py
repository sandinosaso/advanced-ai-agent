import json
import os
from collections import defaultdict

ARTIFACTS = os.path.join(os.path.dirname(__file__), "../artifacts")
RAW_PATH = os.path.join(ARTIFACTS, "join_graph_raw.json")
ASSOC_PATH = os.path.join(ARTIFACTS, "associations.json")
MANUAL_PATH = os.path.join(ARTIFACTS, "join_graph_manual.json")
OUT_PATH = os.path.join(ARTIFACTS, "join_graph_merged.json")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def relationship_key(rel):
    # Use a tuple of main fields for deduplication
    return (
        rel.get("from_table"),
        rel.get("from_column"),
        rel.get("to_table"),
        rel.get("to_column"),
        rel.get("type"),
    )

def merge_relationships(*rels_lists):
    merged = {}
    for rels in rels_lists:
        for rel in rels:
            key = relationship_key(rel)
            if key in merged:
                # Merge sources/evidence if needed
                existing = merged[key]
                # Merge sources
                sources = set(existing.get("sources", []))
                for src in [existing.get("type"), rel.get("type")]:
                    if src: sources.add(src)
                existing["sources"] = sorted(sources)
                # Optionally merge evidence
                if "evidence" in rel and rel["evidence"] != existing.get("evidence"):
                    if not isinstance(existing["evidence"], list):
                        existing["evidence"] = [existing["evidence"]]
                    existing["evidence"].append(rel["evidence"])
            else:
                merged[key] = rel.copy()
                merged[key]["sources"] = [rel.get("type")]
    return list(merged.values())

def main():
    print("Loading artifacts...")
    raw = load_json(RAW_PATH)
    assoc = load_json(ASSOC_PATH)
    manual = load_json(MANUAL_PATH)

    # Merge all relationships
    merged_relationships = merge_relationships(
        raw.get("relationships", []),
        assoc.get("relationships", []),
        manual.get("relationships", []),
    )

    # Merge all tables (raw is canonical, but you could merge columns if needed)
    tables = raw.get("tables", {})

    merged = {
        "version": 1,
        "tables": tables,
        "relationships": merged_relationships,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"✅ Wrote merged join graph: {OUT_PATH}")
    print(f"Tables: {len(tables)} | Relationships: {len(merged_relationships)}")

if __name__ == "__main__":
    main()