"""
Join graph loading and caching

Loads the join graph from JSON and filters audit column relationships.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from src.utils.logging import logger
from src.config.constants import AUDIT_COLUMNS

# Find project root (this file is at src/sql/graph/join_graph.py)
_project_root = Path(__file__).parent.parent.parent.parent
JOIN_GRAPH_PATH = _project_root / "artifacts" / "join_graph_merged.json"

# Cache for loaded graph
_cached_graph: Dict[str, Any] | None = None


def load_join_graph(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load the join graph and filter out audit column relationships.
    
    Audit columns (createdBy, updatedBy, createdAt, updatedAt) are metadata fields
    for tracking changes, not semantic business relationships. They should not be
    used for determining join paths.
    
    Normalizes relationship table names to the canonical keys from graph["tables"]
    so that mixed casing (e.g. InspectionQuestion vs inspectionQuestion) does not
    create duplicate nodes or wrong bridge table counts.
    
    Args:
        force_reload: If True, reload from disk even if cached
        
    Returns:
        Join graph dictionary with tables and relationships
    """
    global _cached_graph
    
    # Return cached graph if available
    if _cached_graph is not None and not force_reload:
        return _cached_graph
    
    with open(str(JOIN_GRAPH_PATH), "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    # Canonical table names: map lowercased name -> key from graph["tables"]
    table_keys = list(graph["tables"].keys())
    canonical_by_lower = {t.lower(): t for t in table_keys}

    def canonical_table(name: str) -> str:
        if not name:
            return name
        return canonical_by_lower.get(name.lower(), name)

    # Filter out audit column relationships
    original_count = len(graph["relationships"])
    filtered_rels = [
        r for r in graph["relationships"]
        if r["from_column"] not in AUDIT_COLUMNS
    ]
    # Normalize from_table / to_table to canonical keys so path finder and bridge logic see one node per table
    graph["relationships"] = []
    for r in filtered_rels:
        r = dict(r)
        r["from_table"] = canonical_table(r.get("from_table", ""))
        r["to_table"] = canonical_table(r.get("to_table", ""))
        graph["relationships"].append(r)
    filtered_count = original_count - len(graph["relationships"])

    logger.info(
        f"Loaded join graph: {len(graph['tables'])} tables, {len(graph['relationships'])} relationships "
        f"(filtered {filtered_count} audit column relationships)"
    )
    
    # Cache the graph
    _cached_graph = graph
    
    return graph


def get_table_names() -> list[str]:
    """
    Get list of all table names from the join graph.
    
    Returns:
        List of table names
    """
    graph = load_join_graph()
    return list(graph["tables"].keys())


def get_relationships() -> list[Dict[str, Any]]:
    """
    Get list of all relationships from the join graph.
    
    Returns:
        List of relationship dictionaries
    """
    graph = load_join_graph()
    return graph["relationships"]
