"""
Prompt helper utilities for generating dynamic examples from artifacts.

These utilities extract real examples from join graph and domain registry
to inject into prompts, avoiding hardcoded business-specific examples.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import random


def get_sample_table_names(join_graph: Dict[str, Any], n: int = 3) -> List[str]:
    """
    Get N sample table names from join graph.
    
    Prioritizes tables with more relationships (more central in the schema).
    
    Args:
        join_graph: Join graph containing tables and relationships
        n: Number of sample tables to return
        
    Returns:
        List of table names
    """
    if not join_graph or "tables" not in join_graph:
        return []
    
    tables = list(join_graph["tables"].keys())
    if not tables:
        return []
    
    # Count relationships per table for prioritization
    relationships = join_graph.get("relationships", [])
    table_rel_count = {}
    for rel in relationships:
        from_table = rel.get("from_table")
        to_table = rel.get("to_table")
        if from_table:
            table_rel_count[from_table] = table_rel_count.get(from_table, 0) + 1
        if to_table:
            table_rel_count[to_table] = table_rel_count.get(to_table, 0) + 1
    
    # Sort by relationship count (descending)
    sorted_tables = sorted(tables, key=lambda t: table_rel_count.get(t, 0), reverse=True)
    
    return sorted_tables[:min(n, len(sorted_tables))]


def get_sample_relationships(join_graph: Dict[str, Any], n: int = 2) -> List[Dict[str, Any]]:
    """
    Get N sample relationships from join graph.
    
    Args:
        join_graph: Join graph containing relationships
        n: Number of sample relationships to return
        
    Returns:
        List of relationship dicts
    """
    if not join_graph or "relationships" not in join_graph:
        return []
    
    relationships = join_graph.get("relationships", [])
    if not relationships:
        return []
    
    # Prioritize high-confidence relationships
    sorted_rels = sorted(
        relationships,
        key=lambda r: float(r.get("confidence", 0)),
        reverse=True
    )
    
    return sorted_rels[:min(n, len(sorted_rels))]


def get_name_label_columns_map(join_graph: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Build map of tables to their name/label columns.
    
    Detects common name patterns: name, firstName/lastName, label, title, etc.
    
    Args:
        join_graph: Join graph containing table schemas
        
    Returns:
        Dict mapping table names to list of name/label columns
    """
    if not join_graph or "tables" not in join_graph:
        return {}
    
    name_patterns = {"name", "label", "title", "description"}
    name_pair_patterns = {("firstName", "lastName"), ("first_name", "last_name")}
    
    result = {}
    
    for table_name, table_info in join_graph["tables"].items():
        columns = table_info.get("columns", [])
        name_cols = []
        
        # Check for single name columns
        for col in columns:
            if col.lower() in name_patterns:
                name_cols.append(col)
        
        # Check for name pairs
        for pair in name_pair_patterns:
            if all(p in columns for p in pair):
                name_cols.extend(pair)
        
        if name_cols:
            result[table_name] = name_cols
    
    return result


def get_sample_bridge_path(join_graph: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Find a real bridge table path for examples.
    
    A bridge path is one where tableA connects to tableC via tableB.
    
    Args:
        join_graph: Join graph containing relationships
        
    Returns:
        Dict with 'from_table', 'bridge_table', 'to_table', and 'steps' or None
    """
    if not join_graph or "relationships" not in join_graph:
        return None
    
    relationships = join_graph.get("relationships", [])
    if len(relationships) < 2:
        return None
    
    # Build adjacency map
    adjacency = {}
    for rel in relationships:
        from_t = rel.get("from_table")
        to_t = rel.get("to_table")
        if from_t and to_t:
            if from_t not in adjacency:
                adjacency[from_t] = []
            adjacency[from_t].append((to_t, rel))
    
    # Find a 2-hop path
    for table_a, neighbors in adjacency.items():
        for table_b, rel1 in neighbors:
            if table_b in adjacency:
                for table_c, rel2 in adjacency[table_b]:
                    if table_c != table_a:  # Avoid cycles
                        return {
                            "from_table": table_a,
                            "bridge_table": table_b,
                            "to_table": table_c,
                            "steps": [
                                f"{rel1['from_table']}.{rel1['from_column']} = {rel1['to_table']}.{rel1['to_column']}",
                                f"{rel2['from_table']}.{rel2['from_column']} = {rel2['to_table']}.{rel2['to_column']}"
                            ]
                        }
    
    return None


def get_domain_entities_with_atomic_signals(domain_ontology: Any) -> List[str]:
    """
    Extract entities that require atomic signals from domain registry.
    
    Args:
        domain_ontology: DomainOntology instance
        
    Returns:
        List of entity names that have requires_atomic_signals
    """
    if not domain_ontology or not hasattr(domain_ontology, "registry"):
        return []
    
    registry = domain_ontology.registry
    if not registry or "terms" not in registry:
        return []
    
    entities = set()
    for term_name, term_data in registry["terms"].items():
        if "requires_atomic_signals" in term_data:
            signals = term_data["requires_atomic_signals"]
            if isinstance(signals, list):
                entities.update(signals)
    
    return sorted(list(entities))


def get_entity_id_field_map(domain_ontology: Any) -> Dict[str, str]:
    """
    Build map of entity names to their ID field patterns.
    
    Args:
        domain_ontology: DomainOntology instance
        
    Returns:
        Dict mapping entity names to ID field names (e.g., {"inspection": "inspectionId"})
    """
    if not domain_ontology or not hasattr(domain_ontology, "registry"):
        return {}
    
    registry = domain_ontology.registry
    if not registry or "terms" not in registry:
        return {}
    
    entity_map = {}
    for term_name, term_data in registry["terms"].items():
        entity = term_data.get("entity")
        if entity and entity not in entity_map:
            # Convert entity to ID field format
            # e.g., "inspection" -> "inspectionId"
            entity_map[entity] = f"{entity}Id"
    
    return entity_map


def build_name_label_examples(join_graph: Dict[str, Any], max_examples: int = 4) -> str:
    """
    Build dynamic name/label column examples from join graph.
    
    Args:
        join_graph: Join graph containing table schemas
        max_examples: Maximum number of examples to generate
        
    Returns:
        Formatted string with examples or empty string
    """
    name_map = get_name_label_columns_map(join_graph)
    if not name_map:
        return ""
    
    examples = []
    for table, cols in list(name_map.items())[:max_examples]:
        if len(cols) == 1:
            examples.append(f'  * {table}: use "{cols[0]}" column for name/label')
        elif "firstName" in cols and "lastName" in cols:
            examples.append(
                f'  * {table}: use "firstName" and "lastName" for name '
                f'(can use CONCAT(firstName, \' \', lastName) AS {table}Name)'
            )
        else:
            col_list = '", "'.join(cols)
            examples.append(f'  * {table}: use "{col_list}" columns for name/label')
    
    if examples:
        return "IMPORTANT FOR NAME/LABEL REQUESTS:\n- If the question asks for \"names\" or \"labels\" instead of IDs, select the appropriate name/label columns:\n" + "\n".join(examples) + "\n- When replacing an ID with a name, make sure to SELECT the name column(s) and JOIN to the table that has the name"
    
    return ""


def build_bridge_table_example(join_graph: Dict[str, Any]) -> str:
    """
    Build a dynamic bridge table example from join graph.
    
    Args:
        join_graph: Join graph containing relationships
        
    Returns:
        Example string or generic placeholder
    """
    bridge_path = get_sample_bridge_path(join_graph)
    
    if bridge_path:
        return (
            f"If connecting two tables requires a bridge table "
            f"(like '{bridge_path['bridge_table']}' connecting "
            f"'{bridge_path['from_table']}' to '{bridge_path['to_table']}'), "
            f"you MUST include ALL intermediate tables in the JOIN_PATH."
        )
    
    # Generic fallback
    return (
        "If connecting two tables requires a bridge table "
        "(like 'bridgeTable' connecting 'tableA' to 'tableB'), "
        "you MUST include ALL intermediate tables in the JOIN_PATH."
    )


def build_duplicate_join_example(join_graph: Dict[str, Any]) -> str:
    """
    Build a dynamic duplicate join error example from join graph.
    
    Args:
        join_graph: Join graph containing relationships
        
    Returns:
        Example string with real or generic table names
    """
    # Try to find a table with multiple foreign keys
    if join_graph and "tables" in join_graph:
        for table_name, table_info in join_graph["tables"].items():
            columns = table_info.get("columns", [])
            fk_cols = [c for c in columns if c.endswith("Id") and c != "id"]
            
            if len(fk_cols) >= 2:
                # Found a table with multiple FKs
                fk1, fk2 = fk_cols[:2]
                ref_table1 = fk1.replace("Id", "")
                ref_table2 = fk2.replace("Id", "")
                
                return f"""COMMON CAUSES:
1. Same table joined twice with different conditions:
   BAD:
   JOIN {table_name} ON {table_name}.{fk1} = {ref_table1}.id
   JOIN {table_name} ON {table_name}.{fk2} = {ref_table2}.id

   GOOD (pick the most direct path):
   JOIN {table_name} ON {table_name}.{fk2} = {ref_table2}.id

2. Trying to use multiple join paths to the same table:
   - Choose the SHORTEST path with HIGHEST confidence
   - Use direct foreign key relationships when available
   - NOT indirect paths through multiple tables"""
    
    # Generic fallback
    return """COMMON CAUSES:
1. Same table joined twice with different conditions:
   BAD:
   JOIN tableA ON tableA.fkId1 = tableB.id
   JOIN tableA ON tableA.fkId2 = tableC.id

   GOOD (pick the most direct path):
   JOIN tableA ON tableA.fkId2 = tableC.id

2. Trying to use multiple join paths to the same table:
   - Choose the SHORTEST path with HIGHEST confidence
   - Use direct foreign key relationships when available
   - NOT indirect paths through multiple tables"""


def get_most_connected_tables(join_graph: Dict[str, Any], n: int = 5) -> List[str]:
    """
    Get the N most connected tables from join graph (for fallback selection).
    
    Args:
        join_graph: Join graph containing tables and relationships
        n: Number of tables to return
        
    Returns:
        List of table names sorted by connectivity
    """
    if not join_graph or "tables" not in join_graph:
        return []
    
    tables = list(join_graph["tables"].keys())
    if not tables:
        return []
    
    # Count relationships per table
    relationships = join_graph.get("relationships", [])
    table_rel_count = {}
    for table in tables:
        table_rel_count[table] = 0
    
    for rel in relationships:
        from_table = rel.get("from_table")
        to_table = rel.get("to_table")
        if from_table in table_rel_count:
            table_rel_count[from_table] += 1
        if to_table in table_rel_count:
            table_rel_count[to_table] += 1
    
    # Sort by relationship count (descending)
    sorted_tables = sorted(
        tables,
        key=lambda t: table_rel_count.get(t, 0),
        reverse=True
    )
    
    return sorted_tables[:min(n, len(sorted_tables))]


def build_column_mismatch_example(join_graph: Dict[str, Any]) -> str:
    """
    Build a dynamic column mismatch example from join graph.
    
    Args:
        join_graph: Join graph containing table schemas
        
    Returns:
        Example string or generic message
    """
    # Try to find a real example where columns exist in one table but not another
    if join_graph and "tables" in join_graph:
        tables = join_graph["tables"]
        table_names = list(tables.keys())
        
        if len(table_names) >= 2:
            # Look for columns that exist in one table but not another
            for i, table1 in enumerate(table_names[:3]):
                cols1 = set(tables[table1].get("columns", []))
                for table2 in table_names[i+1:i+3]:
                    cols2 = set(tables[table2].get("columns", []))
                    
                    # Find columns unique to table1
                    unique_to_1 = cols1 - cols2
                    if unique_to_1:
                        sample_cols = list(unique_to_1)[:2]
                        if len(sample_cols) == 2:
                            return f"- Do NOT assume columns exist in the wrong table (e.g., {sample_cols[0]}/{sample_cols[1]} are in {table1} table, NOT in {table2} table)"
                        elif len(sample_cols) == 1:
                            return f"- Do NOT assume columns exist in the wrong table (e.g., {sample_cols[0]} is in {table1} table, NOT in {table2} table)"
    
    # Generic fallback
    return "- Do NOT assume columns exist in the wrong table - verify each column exists in the table you're referencing"
