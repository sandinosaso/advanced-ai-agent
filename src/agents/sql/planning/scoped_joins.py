"""
Scoped joins planning utilities

This module handles compound join conditions where a table requires multiple
join predicates (scoped joins). For example, inspectionQuestionAnswer needs
both inspectionId and inspectionQuestionId to properly scope answers.
"""

from typing import Dict, Any, List, Set
from loguru import logger
import re


def get_required_join_constraints(
    domain_resolutions: List[Dict[str, Any]],
    domain_ontology
) -> List[Dict[str, Any]]:
    """
    Extract required join constraints from domain registry.
    
    Args:
        domain_resolutions: Resolved domain terms from the query
        domain_ontology: Domain ontology instance
        
    Returns:
        List of constraint dicts with structure:
        {
            "table": "tableName",
            "conditions": ["table.col1 = other.col2", ...],
            "note": "explanation"
        }
    """
    if not domain_resolutions or not domain_ontology:
        return []
    
    terms_registry = domain_ontology.registry.get("terms", {})
    constraints = []
    
    for res in domain_resolutions:
        term = res.get("term")
        if not term or term not in terms_registry:
            continue
            
        primary = terms_registry[term].get("resolution", {}).get("primary", {})
        required_constraints = primary.get("required_join_constraints", [])
        
        for constraint in required_constraints:
            if constraint not in constraints:
                constraints.append(constraint)
                logger.info(
                    f"Found required join constraint for {constraint.get('table')}: "
                    f"{len(constraint.get('conditions', []))} conditions"
                )
    
    return constraints


def get_scoped_conditions_from_graph(
    join_graph: Dict[str, Any],
    selected_tables: Set[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract scoped conditions from join graph relationships.
    
    Args:
        join_graph: Join graph with relationships
        selected_tables: Set of selected table names
        
    Returns:
        Dict mapping table names to their scoped conditions:
        {
            "tableName": [
                {
                    "also_requires": "otherTable",
                    "condition": "table.col = other.col",
                    "reason": "explanation"
                }
            ]
        }
    """
    relationships = join_graph.get("relationships", [])
    scoped_by_table = {}
    
    for rel in relationships:
        # Look for relationships with scoped_conditions
        scoped_conditions = rel.get("scoped_conditions", [])
        if not scoped_conditions:
            continue
        
        from_table = rel.get("from_table")
        if from_table not in selected_tables:
            continue
        
        # Check if the required tables are also selected
        for scoped_cond in scoped_conditions:
            also_requires = scoped_cond.get("also_requires")
            if also_requires and also_requires in selected_tables:
                if from_table not in scoped_by_table:
                    scoped_by_table[from_table] = []
                scoped_by_table[from_table].append(scoped_cond)
                logger.debug(
                    f"Found scoped condition for {from_table}: requires {also_requires}"
                )
    
    return scoped_by_table


def validate_scoped_joins(
    sql: str,
    required_constraints: List[Dict[str, Any]]
) -> List[str]:
    """
    Validate that required scoped join constraints are present in SQL.
    
    Args:
        sql: Generated SQL query
        required_constraints: List of required constraint dicts
        
    Returns:
        List of missing constraint descriptions (empty if all present)
    """
    if not required_constraints:
        return []
    
    missing = []
    sql_normalized = " ".join(sql.upper().split())
    
    for constraint in required_constraints:
        table = constraint.get("table")
        conditions = constraint.get("conditions", [])
        
        for condition in conditions:
            # Normalize the condition for comparison
            condition_normalized = " ".join(condition.upper().split())
            # Remove common SQL keywords that might vary
            condition_core = condition_normalized.replace("=", " = ")
            
            # Extract the key parts: table.column = other.column
            parts = [p.strip() for p in condition_core.split("=")]
            if len(parts) != 2:
                continue
            
            left, right = parts
            
            # Check if both sides appear in the SQL (order might vary)
            if (left in sql_normalized and right in sql_normalized) or \
               (right in sql_normalized and left in sql_normalized):
                # Condition appears to be present
                continue
            else:
                missing.append(f"{table}: {condition}")
                logger.warning(f"Missing scoped join constraint: {condition}")
    
    return missing


def build_scoped_join_hints(
    domain_resolutions: List[Dict[str, Any]],
    domain_ontology,
    join_graph: Dict[str, Any]
) -> str:
    """
    Build prompt hints for LLM about required scoped joins.
    
    Args:
        domain_resolutions: Resolved domain terms
        domain_ontology: Domain ontology instance
        join_graph: Join graph with relationships
        
    Returns:
        Formatted string with scoped join requirements for prompt
    """
    constraints = get_required_join_constraints(domain_resolutions, domain_ontology)
    
    if not constraints:
        return ""
    
    hints = "\n" + "=" * 70 + "\n"
    hints += "SCOPED JOIN REQUIREMENTS (CRITICAL)\n"
    hints += "=" * 70 + "\n"
    hints += "Some tables require COMPOUND join conditions (multiple AND predicates).\n"
    hints += "You MUST combine ALL conditions into ONE join step using AND:\n\n"
    
    for constraint in constraints:
        table = constraint.get("table")
        conditions = constraint.get("conditions", [])
        note = constraint.get("note", "")
        
        # Determine if this table should use LEFT JOIN
        table_metadata = join_graph.get("table_metadata", {}).get(table, {})
        join_type = "LEFT JOIN" if table_metadata.get("category") == "form_data" else "JOIN"
        
        hints += f"When joining to table '{table}', use ALL these conditions in ONE step:\n"
        if conditions:
            # Show them as a single join step formatted for JOIN_PATH with join type
            hints += f"- {join_type}: {conditions[0]} (N:1, 1.00)\n"
            for condition in conditions[1:]:
                hints += f" AND {condition} (N:1, 1.00)\n"
        if note:
            hints += f"  Reason: {note}\n"
        
        # Add additional note about LEFT JOIN for form_data
        if join_type == "LEFT JOIN":
            hints += f"  Note: Use LEFT JOIN because {table} is optional (may not exist for all parents)\n"
        hints += "\n"
    
    hints += "IMPORTANT: Do NOT split these into separate join steps!\n"
    hints += "Combine them with AND on the same line in JOIN_PATH.\n"
    hints += "=" * 70 + "\n"
    
    return hints


def extract_scoped_tables_from_constraints(
    required_constraints: List[Dict[str, Any]]
) -> Set[str]:
    """
    Extract all table names mentioned in required constraints.
    
    This is useful for ensuring all required tables are included in
    the table selection process.
    
    Args:
        required_constraints: List of required constraint dicts
        
    Returns:
        Set of table names mentioned in constraints
    """
    tables = set()
    
    for constraint in required_constraints:
        # Add the main table
        table = constraint.get("table")
        if table:
            tables.add(table)
        
        # Extract tables from conditions
        conditions = constraint.get("conditions", [])
        for condition in conditions:
            # Parse table names from conditions like "table1.col = table2.col"
            # Match table names before dots
            matches = re.findall(r'(\w+)\.', condition)
            tables.update(matches)
    
    return tables


def determine_join_type_for_table(
    table: str,
    join_graph: Dict[str, Any],
    selected_tables: Set[str]
) -> str:
    """
    Determine if a table should use LEFT JOIN based on its semantic role.
    
    Args:
        table: Table name to check
        join_graph: Join graph with table metadata
        selected_tables: Set of currently selected tables
        
    Returns:
        "LEFT JOIN" if table should use left join, otherwise "JOIN"
        
    Rules:
    - If table has category="form_data", use LEFT JOIN
      (these are optional user-generated content like answers)
    - If table has requires_scoping=true, use LEFT JOIN
      (scoped children may not exist for all parents)
    - Otherwise use default JOIN
    """
    table_metadata = join_graph.get("table_metadata", {})
    metadata = table_metadata.get(table, {})
    
    # Check if this is form_data (optional user content)
    category = metadata.get("category")
    if category == "form_data":
        logger.debug(f"Table {table} is form_data, using LEFT JOIN")
        return "LEFT JOIN"
    
    # Check if requires scoping (may not exist for all parents)
    requires_scoping = metadata.get("requires_scoping", False)
    if requires_scoping:
        logger.debug(f"Table {table} requires scoping, using LEFT JOIN")
        return "LEFT JOIN"
    
    # Default to INNER JOIN
    return "JOIN"


def get_join_type_hints(
    selected_tables: List[str],
    join_graph: Dict[str, Any]
) -> str:
    """
    Build hints about which tables should use LEFT JOIN vs JOIN.
    
    Args:
        selected_tables: List of selected table names
        join_graph: Join graph with table metadata
        
    Returns:
        Formatted string with join type hints for prompt
    """
    hints = "\n" + "=" * 70 + "\n"
    hints += "JOIN TYPE REQUIREMENTS\n"
    hints += "=" * 70 + "\n"
    
    left_join_tables = []
    inner_join_tables = []
    
    selected_set = set(selected_tables)
    for table in selected_tables:
        join_type = determine_join_type_for_table(table, join_graph, selected_set)
        if join_type == "LEFT JOIN":
            left_join_tables.append(table)
        else:
            inner_join_tables.append(table)
    
    if left_join_tables:
        hints += "\nUse LEFT JOIN for these tables (optional data, may not exist):\n"
        for table in left_join_tables:
            table_metadata = join_graph.get("table_metadata", {}).get(table, {})
            category = table_metadata.get("category", "")
            reason = f"({category})" if category else "(optional)"
            hints += f"  - {table}: LEFT JOIN {reason}\n"
    
    if inner_join_tables:
        hints += "\nUse JOIN for these tables (required data):\n"
        for table in inner_join_tables[:5]:  # Show first 5 to avoid clutter
            hints += f"  - {table}: JOIN\n"
        if len(inner_join_tables) > 5:
            hints += f"  ... and {len(inner_join_tables) - 5} more\n"
    
    hints += "\nWhen outputting JOIN_PATH, prefix each join with its type:\n"
    hints += "- LEFT JOIN: tableX.col = tableY.col (N:1, 1.00)  # for optional tables\n"
    hints += "- JOIN: tableA.col = tableB.col (N:1, 1.00)  # for required tables\n"
    hints += "=" * 70 + "\n"
    
    return hints


def get_scoped_join_type(
    from_table: str,
    to_table: str,
    join_graph: Dict[str, Any]
) -> str:
    """
    Determine if a join between two tables requires scoped conditions.
    
    Args:
        from_table: Source table name
        to_table: Target table name
        join_graph: Join graph with relationships
        
    Returns:
        "scoped_child" if scoped conditions required, otherwise "standard"
    """
    relationships = join_graph.get("relationships", [])
    
    for rel in relationships:
        if (rel.get("from_table") == from_table and 
            rel.get("to_table") == to_table):
            rel_type = rel.get("type", "foreign_key")
            if rel_type == "scoped_child":
                return "scoped_child"
    
    return "standard"
