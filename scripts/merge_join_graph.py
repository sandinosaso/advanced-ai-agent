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

def deep_merge_dict(base, override):
    """
    Deep merge where override values take precedence.
    
    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge_dict(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists like scoped_conditions, override completely
            result[key] = value
        else:
            # Override or add the value
            result[key] = value
    return result

def merge_relationships(*rels_lists):
    """
    Merge relationships with priority to later lists (manual overrides).
    
    Args:
        rels_lists: Variable number of relationship lists to merge
        
    Returns:
        List of merged relationships
    """
    merged = {}
    
    for i, rels in enumerate(rels_lists):
        is_manual = i == len(rels_lists) - 1  # Last list has highest priority
        
        for rel in rels:
            key = relationship_key(rel)
            
            if key in merged:
                existing = merged[key]
                
                if is_manual:
                    # Manual overrides: deep merge with manual taking precedence
                    merged[key] = deep_merge_dict(existing, rel)
                else:
                    # Auto-generated: merge sources carefully
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

def merge_table_metadata(*metadata_dicts):
    """
    Merge table metadata with manual taking priority.
    
    Args:
        metadata_dicts: Variable number of metadata dicts, last one is manual
        
    Returns:
        Merged table metadata dictionary
    """
    merged = {}
    
    for metadata in metadata_dicts:
        for table, meta in metadata.items():
            if table in merged:
                # Deep merge: manual overrides auto-generated
                merged[table] = deep_merge_dict(merged[table], meta)
            else:
                merged[table] = meta.copy()
    
    return merged

def main():
    print("Loading artifacts...")
    raw = load_json(RAW_PATH)
    assoc = load_json(ASSOC_PATH)
    manual = load_json(MANUAL_PATH)

    # Merge relationships (manual has priority - last in list)
    merged_relationships = merge_relationships(
        raw.get("relationships", []),
        assoc.get("relationships", []),
        manual.get("relationships", []),  # LAST = highest priority
    )

    # Merge table metadata (manual has priority - last in list)
    merged_metadata = merge_table_metadata(
        raw.get("table_metadata", {}),
        manual.get("table_metadata", {}),  # LAST = highest priority
    )

    # Tables from raw (canonical schema)
    tables = raw.get("tables", {})

    merged = {
        "version": 1,
        "tables": tables,
        "relationships": merged_relationships,
        "table_metadata": merged_metadata,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    
    print(f"✅ Wrote merged join graph: {OUT_PATH}")
    print(f"Tables: {len(tables)} | Relationships: {len(merged_relationships)} | Metadata: {len(merged_metadata)}")

if __name__ == "__main__":
    main()