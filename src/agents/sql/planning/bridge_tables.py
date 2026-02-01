"""
Bridge table discovery for SQL join planning
"""

from typing import Dict, Any, List, Set
from loguru import logger


def find_bridge_tables(
    selected_tables: set,
    relationships: List[Dict[str, Any]],
    join_graph_tables: dict,
    confidence_threshold: float = 0.9
) -> set:
    """
    Find bridge tables that connect two selected tables with high confidence.
    """
    bridge_tables = set()
    selected_lower = {t.lower() for t in selected_tables}
    table_name_map = {t.lower(): t for t in join_graph_tables.keys()}
    table_connections: Dict[str, set] = {}

    for rel in relationships:
        from_table_orig = rel.get("from_table", "")
        to_table_orig = rel.get("to_table", "")
        from_table_lower = from_table_orig.lower()
        to_table_lower = to_table_orig.lower()
        confidence = float(rel.get("confidence", 0))

        if confidence < confidence_threshold:
            continue

        if from_table_lower in selected_lower and to_table_lower not in selected_lower:
            if to_table_lower not in table_connections:
                table_connections[to_table_lower] = set()
            table_connections[to_table_lower].add(from_table_orig)

        if to_table_lower in selected_lower and from_table_lower not in selected_lower:
            if from_table_lower not in table_connections:
                table_connections[from_table_lower] = set()
            table_connections[from_table_lower].add(to_table_orig)

    for table_name_lower, connected_tables in table_connections.items():
        canonical_connected = {
            table_name_map.get(t.lower(), t) for t in connected_tables if t
        }
        if len(canonical_connected) >= 2:
            if table_name_lower in table_name_map:
                original_name = table_name_map[table_name_lower]
                bridge_tables.add(original_name)
                logger.info(
                    f"Found bridge table '{original_name}' connecting "
                    f"{len(canonical_connected)} selected tables: {list(canonical_connected)}"
                )

    return bridge_tables


def get_bridges_on_paths(
    selected_tables: set,
    path_finder
) -> set:
    """Return tables on shortest paths between selected tables."""
    on_path = set()
    selected_list = list(selected_tables)
    for i, t1 in enumerate(selected_list):
        for t2 in selected_list[i + 1:]:
            if t1 == t2:
                continue
            path = path_finder.find_shortest_path(t1, t2, max_hops=4)
            if not path:
                continue
            for rel in path:
                on_path.add(rel.get("from_table"))
                on_path.add(rel.get("to_table"))
    return on_path - selected_tables


def get_domain_bridges(
    domain_resolutions: List[Dict[str, Any]],
    domain_ontology,
    join_graph_tables: dict
) -> set:
    """Return preferred bridge tables from domain registry."""
    if not domain_resolutions or not domain_ontology:
        return set()
    terms_registry = domain_ontology.registry.get("terms", {})
    out = set()
    for res in domain_resolutions:
        term = res.get("term")
        if not term or term not in terms_registry:
            continue
        primary = terms_registry[term].get("resolution", {}).get("primary", {})
        bridge_list = primary.get("bridge_tables", [])
        for t in bridge_list:
            if t in join_graph_tables:
                out.add(t)
    return out


def get_exclude_bridge_patterns(
    domain_resolutions: List[Dict[str, Any]],
    domain_ontology
) -> List[str]:
    """Return substrings that should exclude a bridge table."""
    if not domain_resolutions or not domain_ontology:
        return []
    terms_registry = domain_ontology.registry.get("terms", {})
    patterns: List[str] = []
    for res in domain_resolutions:
        term = res.get("term")
        if not term or term not in terms_registry:
            continue
        primary = terms_registry[term].get("resolution", {}).get("primary", {})
        for p in primary.get("exclude_bridge_patterns", []):
            if p and p not in patterns:
                patterns.append(p)
    return patterns
