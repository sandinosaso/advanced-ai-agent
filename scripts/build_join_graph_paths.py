"""
Script to build a path index for efficient join path lookup.

Instead of computing ALL paths between ALL pairs (exponential complexity),
this script creates a lightweight index structure that enables fast
on-demand path finding using Dijkstra's algorithm.

- Input: artifacts/join_graph_merged.json
- Output: artifacts/join_graph_paths.json (path index metadata)

The path finder utility (src/utils/path_finder.py) uses this index
to compute shortest paths on-demand for selected tables.
"""
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.path_finder import JoinPathFinder

ARTIFACTS = os.path.join(os.path.dirname(__file__), "../artifacts")
MERGED_PATH = os.path.join(ARTIFACTS, "join_graph_merged.json")
OUT_PATH = os.path.join(ARTIFACTS, "join_graph_paths.json")

CONF_THRESH = 0.7
MAX_HOPS = 4


def build_path_index():
    """
    Build a lightweight path index.
    
    Instead of precomputing all paths, we:
    1. Load the join graph
    2. Create a path finder instance
    3. Save metadata about the graph structure
    4. The path finder will compute paths on-demand
    """
    print(f"Loading join graph from: {MERGED_PATH}")
    with open(MERGED_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    relationships = graph["relationships"]
    tables = list(graph["tables"].keys())
    
    print(f"Graph stats:")
    print(f"  - Tables: {len(tables)}")
    print(f"  - Relationships: {len(relationships)}")
    
    # Filter relationships by confidence
    high_conf_rels = [
        r for r in relationships 
        if float(r.get("confidence", 0)) >= CONF_THRESH
    ]
    print(f"  - High-confidence relationships (≥{CONF_THRESH}): {len(high_conf_rels)}")
    
    # Build path finder to validate graph structure
    print("\nBuilding path finder...")
    path_finder = JoinPathFinder(relationships, confidence_threshold=CONF_THRESH)
    
    # Test path finding on a few sample pairs to validate
    print("\nValidating path finder with sample paths...")
    sample_tables = tables[:min(5, len(tables))]
    sample_paths = 0
    for i, start in enumerate(sample_tables):
        for end in sample_tables[i+1:]:
            path = path_finder.find_shortest_path(start, end, max_hops=MAX_HOPS)
            if path:
                sample_paths += 1
                print(f"  ✓ {start} → {end}: {len(path)} hops")
    
    print(f"\nFound {sample_paths} sample paths (validation)")
    
    # Create index metadata
    index = {
        "version": 2,
        "metadata": {
            "total_tables": len(tables),
            "total_relationships": len(relationships),
            "high_confidence_relationships": len(high_conf_rels),
            "confidence_threshold": CONF_THRESH,
            "max_hops": MAX_HOPS,
            "path_finder_class": "JoinPathFinder",
            "path_finder_module": "src.utils.path_finder"
        },
        "note": (
            "This index enables on-demand path finding. "
            "Use JoinPathFinder.find_shortest_path() to compute paths between selected tables. "
            "Paths are computed using Dijkstra's algorithm for efficiency."
        )
    }
    
    # Save index
    print(f"\nWriting path index to: {OUT_PATH}")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    
    print(f"✅ Path index created successfully!")
    print(f"\nUsage:")
    print(f"  from src.utils.path_finder import JoinPathFinder")
    print(f"  path_finder = JoinPathFinder(relationships)")
    print(f"  path = path_finder.find_shortest_path('table1', 'table2', max_hops={MAX_HOPS})")


if __name__ == "__main__":
    build_path_index()
