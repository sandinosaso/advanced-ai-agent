"""
Domain-based column and filter exclusions
"""

from typing import Dict, List, Set


def get_excluded_columns(
    domain_resolutions: List[dict],
    domain_ontology,
    join_graph_tables: dict
) -> Dict[str, Set[str]]:
    """
    Return per-table column names that must not be used when this domain is active.
    """
    if not domain_resolutions or not domain_ontology:
        return {}
    terms_registry = domain_ontology.registry.get("terms", {})
    table_name_map = {t.lower(): t for t in join_graph_tables.keys()}
    out: Dict[str, Set[str]] = {}
    for res in domain_resolutions:
        term = res.get("term")
        if not term or term not in terms_registry:
            continue
        primary = terms_registry[term].get("resolution", {}).get("primary", {})
        exclude = primary.get("exclude_columns", {})
        if not isinstance(exclude, dict):
            continue
        for table, cols in exclude.items():
            if not cols:
                continue
            canonical = table_name_map.get(table.lower(), table)
            if canonical not in out:
                out[canonical] = set()
            for c in cols if isinstance(cols, list) else [cols]:
                if c:
                    out[canonical].add(c)
    return out
