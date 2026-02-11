"""
Bridge table discovery for SQL join planning
"""

from typing import Dict, Any, List, Set
from collections import deque
from loguru import logger


def find_bridge_tables(
    selected_tables: set,
    relationships: List[Dict[str, Any]],
    join_graph_tables: dict,
    table_metadata: dict = None,
    exclude_patterns: List[str] = None,
    confidence_threshold: float = 0.9
) -> set:
    """
    Find bridge tables that connect two selected tables with high confidence.
    
    Args:
        selected_tables: Set of already selected tables
        relationships: List of relationship dicts from join graph
        join_graph_tables: Dict of all tables in join graph
        table_metadata: Dict of table metadata with semantic roles (NEW)
        exclude_patterns: List of patterns to exclude from bridges (NEW)
        confidence_threshold: Minimum confidence for relationships
        
    Returns:
        Set of bridge table names
        
    Changes from original:
        - Hard-filter satellite tables (role='satellite') before connectivity analysis
        - Apply exclude_patterns during discovery (not after)
        - Prioritize content_child and bridge roles over satellite
        - Check for direct paths first - only add bridges if no direct path exists
        - Exclude assignment/configuration tables unless explicitly needed
    """
    bridge_tables = set()
    selected_lower = {t.lower() for t in selected_tables}
    table_name_map = {t.lower(): t for t in join_graph_tables.keys()}
    table_connections: Dict[str, set] = {}
    table_metadata = table_metadata or {}
    exclude_patterns = exclude_patterns or []
    
    # Build a map of direct connections between selected tables
    direct_connections: Dict[str, Set[str]] = {}
    for rel in relationships:
        from_table_orig = rel.get("from_table", "")
        to_table_orig = rel.get("to_table", "")
        from_table_lower = from_table_orig.lower()
        to_table_lower = to_table_orig.lower()
        confidence = float(rel.get("confidence", 0))
        
        if confidence < confidence_threshold:
            continue
            
        # Track direct connections between selected tables
        if from_table_lower in selected_lower and to_table_lower in selected_lower:
            if from_table_orig not in direct_connections:
                direct_connections[from_table_orig] = set()
            if to_table_orig not in direct_connections:
                direct_connections[to_table_orig] = set()
            direct_connections[from_table_orig].add(to_table_orig)
            direct_connections[to_table_orig].add(from_table_orig)

    def should_exclude_table(table_name: str) -> bool:
        """Check if table should be excluded from bridge consideration."""
        metadata = table_metadata.get(table_name, {})
        
        # Check if explicitly marked as non-bridge
        if metadata.get("use_as_bridge") is False:
            logger.debug(f"Excluding table '{table_name}' - marked as use_as_bridge=false")
            return True
        
        # Check semantic role - exclude satellites
        role = metadata.get("role")
        
        if role == "satellite":
            logger.debug(f"Excluding satellite table '{table_name}' from bridge discovery")
            return True
        
        # Exclude assignment/configuration tables - they are not true bridges
        if role in ("assignment", "configuration"):
            logger.debug(f"Excluding {role} table '{table_name}' from bridge discovery")
            return True
        
        # Check exclusion patterns
        for pattern in exclude_patterns:
            if pattern.lower() in table_name.lower():
                logger.debug(f"Excluding table '{table_name}' matching pattern '{pattern}'")
                return True
        
        return False
    
    def has_direct_path(table1: str, table2: str) -> bool:
        """Check if two tables have a direct relationship."""
        return table2 in direct_connections.get(table1, set())
    
    def has_path_through_selected(table1: str, table2: str, selected_tables: set) -> bool:
        """
        Check if two tables can be connected through already-selected tables.
        
        Uses BFS to find if a path exists using only selected tables as intermediates.
        This prevents adding unnecessary bridge tables when a transitive path already
        exists through the selected tables.
        
        Args:
            table1: First table
            table2: Second table
            selected_tables: Set of already-selected table names
            
        Returns:
            True if a path exists through selected tables, False otherwise
            
        Example:
            Selected: ['workOrder', 'crew', 'employeeCrew', 'employee']
            Check: has_path_through_selected('workOrder', 'employee', selected)
            Result: True (path: workOrder → crew → employeeCrew → employee)
        """
        # Direct connection (1-hop)
        if table2 in direct_connections.get(table1, set()):
            return True
        
        # BFS to find transitive path through selected tables only
        visited = set()
        queue = deque([table1])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            # Found target
            if current == table2:
                logger.debug(f"Found path from {table1} to {table2} through selected tables")
                return True
            
            # Explore neighbors that are in selected_tables
            for neighbor in direct_connections.get(current, set()):
                if neighbor in selected_tables and neighbor not in visited:
                    queue.append(neighbor)
        
        logger.debug(f"No path from {table1} to {table2} through selected tables")
        return False

    for rel in relationships:
        from_table_orig = rel.get("from_table", "")
        to_table_orig = rel.get("to_table", "")
        from_table_lower = from_table_orig.lower()
        to_table_lower = to_table_orig.lower()
        confidence = float(rel.get("confidence", 0))

        if confidence < confidence_threshold:
            continue

        # Check if either table should be excluded
        if should_exclude_table(from_table_orig) or should_exclude_table(to_table_orig):
            continue

        if from_table_lower in selected_lower and to_table_lower not in selected_lower:
            if to_table_lower not in table_connections:
                table_connections[to_table_lower] = set()
            table_connections[to_table_lower].add(from_table_orig)

        if to_table_lower in selected_lower and from_table_lower not in selected_lower:
            if from_table_lower not in table_connections:
                table_connections[from_table_lower] = set()
            table_connections[from_table_lower].add(to_table_orig)

    # Score tables by connectivity and semantic role
    for table_name_lower, connected_tables in table_connections.items():
        canonical_connected = {
            table_name_map.get(t.lower(), t) for t in connected_tables if t
        }
        if len(canonical_connected) >= 2:
            if table_name_lower in table_name_map:
                original_name = table_name_map[table_name_lower]
                
                # Double-check exclusion (defensive)
                if should_exclude_table(original_name):
                    continue
                
                # Get semantic role and metadata
                metadata = table_metadata.get(original_name, {})
                role = metadata.get("role", "unknown")
                exclude_as_bridge_for = metadata.get("exclude_as_bridge_for", [])
                
                # Check if this table is explicitly excluded as a bridge for any connected tables
                if exclude_as_bridge_for:
                    should_skip = False
                    for excluded_table in exclude_as_bridge_for:
                        if excluded_table in canonical_connected:
                            logger.debug(
                                f"Skipping bridge table '{original_name}' - explicitly excluded "
                                f"for table '{excluded_table}' in metadata"
                            )
                            should_skip = True
                            break
                    if should_skip:
                        continue
                
                # Check if paths already exist between all connected tables (direct or transitive)
                # If so, this bridge is not needed
                connected_list = list(canonical_connected)
                all_have_path = True
                for i, t1 in enumerate(connected_list):
                    for t2 in connected_list[i + 1:]:
                        # Check both direct AND transitive paths through selected tables
                        if not has_path_through_selected(t1, t2, selected_lower):
                            all_have_path = False
                            break
                    if not all_have_path:
                        break
                
                if all_have_path:
                    logger.info(
                        f"Skipping bridge table '{original_name}' - paths already exist "
                        f"between connected tables (direct or through selected): {list(canonical_connected)}"
                    )
                    continue
                
                bridge_tables.add(original_name)
                logger.info(
                    f"Found bridge table '{original_name}' (role: {role}) connecting "
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
