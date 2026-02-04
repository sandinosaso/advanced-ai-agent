"""
SQL correction node - fixes SQL errors with focused context
"""

import json
import re
from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.sql.execution.secure_rewriter import rewrite_secure_tables, from_secure_view
from src.agents.sql.prompt_helpers import build_duplicate_join_example
from src.agents.sql.planning import get_required_join_constraints


def _extract_sql_from_markdown(text: str) -> str:
    """
    Extract SQL from a markdown code block anywhere in the text.
    
    Looks for ```sql or ``` code blocks and returns the content inside.
    If no code block is found, returns the original text.
    
    Args:
        text: Text that may contain markdown code blocks
        
    Returns:
        SQL content from inside code block, or original text if no block found
        
    Examples:
        >>> text = "Here is the query:\\n```sql\\nSELECT * FROM table\\n```"
        >>> _extract_sql_from_markdown(text)
        "SELECT * FROM table"
    """
    # Try to find a code block with optional 'sql' language tag
    # Pattern: ``` or ```sql, then content, then closing ```
    pattern = r'```(?:sql)?\s*\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if match:
        sql_content = match.group(1).strip()
        logger.debug(f"Extracted SQL from markdown code block ({len(sql_content)} chars)")
        return sql_content
    
    # No code block found - return original text
    return text


def _build_alias_to_base_table_map(sql: str) -> dict:
    """
    Build a mapping from table aliases to their base table names.
    
    Parses FROM/JOIN clauses to extract (table, alias) pairs.
    Handles both explicit AS and implicit aliasing:
    - FROM inspection AS i
    - FROM inspection i
    - JOIN secure_workorder w
    - LEFT JOIN secure_employee se
    
    Args:
        sql: SQL query string
        
    Returns:
        Dict mapping alias -> base_table (after from_secure_view conversion)
        
    Examples:
        >>> sql = "FROM inspection i JOIN secure_workorder w ON i.id = w.inspectionId"
        >>> _build_alias_to_base_table_map(sql)
        {'i': 'inspection', 'w': 'workOrder'}
    """
    alias_map = {}
    
    # Pattern to capture: FROM/JOIN table_name [AS] alias [ON ...]
    # This captures the table name and an optional alias (with or without AS)
    # We need to handle cases like:
    #   FROM table_name alias
    #   FROM table_name AS alias
    #   JOIN table_name alias ON ...
    #   LEFT JOIN table_name alias ON ...
    
    # Match: (LEFT/RIGHT/INNER/OUTER)? (FROM|JOIN) table_name [AS] potential_alias
    # The potential_alias is valid if it's followed by ON/WHERE/JOIN/comma/EOF, not a comparison operator
    pattern = r'\b(?:FROM|(?:LEFT\s+|RIGHT\s+|INNER\s+|OUTER\s+)?JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\b'
    
    for match in re.finditer(pattern, sql, re.IGNORECASE):
        table_name = match.group(1)
        potential_alias = match.group(2)
        
        # Check if potential_alias is actually an alias (not ON, WHERE, JOIN, etc.)
        # Aliases are typically short (1-3 chars) or meaningful abbreviations
        # SQL keywords that might appear after table name: ON, WHERE, JOIN, INNER, LEFT, RIGHT, etc.
        sql_keywords = {'ON', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'CROSS', 
                       'AND', 'OR', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'UNION', 'EXCEPT'}
        
        if potential_alias and potential_alias.upper() not in sql_keywords:
            # It's likely an alias
            base_table = from_secure_view(table_name)
            alias_map[potential_alias] = base_table
            logger.debug(f"Found alias: {potential_alias} -> {table_name} (base: {base_table})")
    
    return alias_map


def correct_sql_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Focused correction agent that fixes SQL errors.
    """
    state = dict(state)
    sql = state.get("sql", "")
    validation_errors = state.get("validation_errors")
    if validation_errors:
        # Format validation errors as a numbered list for clarity
        error_list = "\n".join([f"{i+1}. {err}" for i, err in enumerate(validation_errors)])
        error_message = error_list
    else:
        error_message = state.get("last_sql_error") or "Unknown error"
    correction_attempts = state.get("sql_correction_attempts", 0)

    if correction_attempts >= settings.sql_correction_max_attempts:
        logger.error(f"Max correction attempts ({settings.sql_correction_max_attempts}) reached. Last error: {error_message[:200]}")
        state["result"] = None
        state["query_resolved"] = False
        return state

    state["sql_correction_attempts"] = correction_attempts + 1

    # Build alias -> base_table mapping from FROM/JOIN clauses
    alias_map = _build_alias_to_base_table_map(sql)
    logger.debug(f"Alias map: {alias_map}")

    # Extract table names from FROM/JOIN clauses (these are real table/view names)
    table_pattern = r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    tables_in_sql = set()
    for table in re.findall(table_pattern, sql, re.IGNORECASE):
        base_table = from_secure_view(table)
        tables_in_sql.add(base_table)

    # Extract table names from column qualifiers (table.column or alias.column)
    # Use alias map to resolve aliases to their base table names
    column_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)"
    for qualifier, _ in re.findall(column_pattern, sql):
        # Check if qualifier is an alias first
        if qualifier in alias_map:
            # It's an alias - add the base table it refers to
            base_table = alias_map[qualifier]
            tables_in_sql.add(base_table)
        else:
            # It's a direct table/view reference - convert to base table
            base_table = from_secure_view(qualifier)
            tables_in_sql.add(base_table)

    # Filter to only tables that exist in join_graph to avoid spurious warnings
    valid_tables_in_sql = {t for t in tables_in_sql if t in ctx.join_graph["tables"]}
    
    # Log both sets for debugging
    logger.info(f"Tables found in SQL query (after conversion to base tables): {sorted(tables_in_sql)}")
    if len(valid_tables_in_sql) < len(tables_in_sql):
        skipped = tables_in_sql - valid_tables_in_sql
        logger.debug(f"Skipped tables not in join_graph: {sorted(skipped)}")
    
    # Use only valid tables for schema and relationships
    tables_in_sql = valid_tables_in_sql

    # Build a map of table -> errors for that table (for better error presentation)
    error_by_table = {}
    if validation_errors:
        for err in validation_errors:
            # Extract table name from error like "Column 'X' does NOT exist in table 'workOrder'"
            match = re.search(r"in table '([^']+)'", err)
            if match:
                table_name = match.group(1)
                if table_name not in error_by_table:
                    error_by_table[table_name] = []
                error_by_table[table_name].append(err)

    table_schemas = []
    for table_name in sorted(tables_in_sql):
        if table_name in ctx.join_graph["tables"]:
            columns = ctx.join_graph["tables"][table_name].get("columns", [])
            columns_str = ", ".join(columns[:settings.sql_max_columns_in_correction])
            if len(columns) > settings.sql_max_columns_in_correction:
                columns_str += f" ... ({len(columns)} total columns)"
            
            schema_line = f"{table_name}: {columns_str}"
            
            # If there are errors for this table, add them right after the schema
            if table_name in error_by_table:
                schema_line += "\n  ERRORS FOR THIS TABLE:"
                for err in error_by_table[table_name]:
                    schema_line += f"\n    - {err}"
            
            table_schemas.append(schema_line)

    relevant_relationships = []
    for rel in state.get("allowed_relationships", []):
        from_table = rel.get("from_table", "")
        to_table = rel.get("to_table", "")
        from_base = from_secure_view(from_table)
        to_base = from_secure_view(to_table)
        if from_base in tables_in_sql or to_base in tables_in_sql:
            relevant_relationships.append(rel)

    correction_history = state.get("correction_history") or []
    history_text = ""
    if correction_history:
        history_text = "\nPrevious correction attempts:\n"
        for i, attempt in enumerate(correction_history[-3:], 1):
            history_text += f"{i}. Error: {attempt.get('error', 'Unknown')}\n"
            sql_preview = attempt.get("sql", "N/A")
            if len(sql_preview) > settings.sql_max_sql_history_length:
                sql_preview = sql_preview[: settings.sql_max_sql_history_length] + "..."
            history_text += f"   Attempted fix: {sql_preview}\n"

    is_group_by_error = (
        "GROUP BY" in error_message.upper()
        or "not in GROUP BY" in error_message.upper()
        or "only_full_group_by" in error_message.lower()
    )
    is_duplicate_table_error = "Not unique table/alias" in error_message or "1066" in error_message

    group_by_instructions = ""
    duplicate_table_instructions = ""

    if is_duplicate_table_error:
        duplicate_example = build_duplicate_join_example(ctx.join_graph)
        duplicate_table_instructions = f"""
CRITICAL: DUPLICATE TABLE/ALIAS ERROR DETECTED

The error "Not unique table/alias" means you are joining the same table multiple times.

{duplicate_example}

FIX STRATEGY:
- Identify which table appears in multiple JOIN clauses
- Keep ONLY the most direct join (fewest hops, highest confidence)
- Remove all other joins to that table
- If you need multiple conditions, combine them in the WHERE clause instead
"""

    if is_group_by_error:
        expr_match = re.search(r"Expression #(\d+)", error_message)
        expr_num = expr_match.group(1) if expr_match else None

        column_match = re.search(r"column ['\"]([^'\"]+)['\"]", error_message)
        problem_column = column_match.group(1) if column_match else None

        expr_hint = ""
        if expr_num:
            expr_hint = f"\nThe error mentions Expression #{expr_num} in the SELECT list. "
        if problem_column:
            expr_hint += f"The problematic column/expression is: {problem_column}"

        group_by_instructions = f"""
CRITICAL GROUP BY RULES (MySQL ONLY_FULL_GROUP_BY mode):
{expr_hint}

- Every non-aggregated column/expression in SELECT must either:
  1. Be in GROUP BY with the EXACT same expression, OR
  2. Be functionally dependent on columns in GROUP BY

COMMON FIXES:
- If SELECT has: DATE_FORMAT(DATE(column), 'format'), GROUP BY must have: DATE_FORMAT(DATE(column), 'format')
- If SELECT has: DATE(column), GROUP BY must have: DATE(column) (NOT just 'column')
- If SELECT has: CONCAT(col1, col2), GROUP BY must have: CONCAT(col1, col2)
- If SELECT has: column AS alias, GROUP BY can use either 'column' or the full expression

EXAMPLE FIX:
  SELECT DATE_FORMAT(DATE(createdAt), '%Y-%m-%d') AS date, SUM(hours)
  FROM workTime
  GROUP BY DATE_FORMAT(DATE(createdAt), '%Y-%m-%d')  -- Must match SELECT exactly
"""

    # Get scoped join requirements
    scoped_join_warning = ""
    required_constraints = get_required_join_constraints(
        state.get("domain_resolutions", []),
        ctx.domain_ontology
    )
    if required_constraints:
        scoped_join_warning = "\n\n⚠️ CRITICAL - SCOPED JOIN REQUIREMENTS:\n"
        scoped_join_warning += "Some tables require COMPOUND join conditions (multiple AND predicates).\n"
        scoped_join_warning += "You MUST preserve ALL join conditions, especially AND clauses:\n\n"
        for constraint in required_constraints:
            table = constraint.get("table")
            conditions = constraint.get("conditions", [])
            note = constraint.get("note", "")
            scoped_join_warning += f"Table '{table}' requires ALL these conditions:\n"
            for condition in conditions:
                scoped_join_warning += f"  - {condition}\n"
            if note:
                scoped_join_warning += f"Reason: {note}\n"
        scoped_join_warning += "\nWhen fixing join errors, you MUST keep compound AND conditions intact!\n"
        scoped_join_warning += "Only fix the column/table names - DO NOT remove AND predicates.\n"
    
    # Add join type preservation warning
    join_type_warning = "\n\n⚠️ CRITICAL - JOIN TYPE PRESERVATION:\n"
    join_type_warning += "When fixing joins, preserve the join type (LEFT JOIN vs JOIN):\n"
    join_type_warning += "- DO NOT convert LEFT JOIN to JOIN - this changes query semantics\n"
    join_type_warning += "- LEFT JOINs are used for optional data (e.g., answers that may not exist)\n"
    join_type_warning += "- Only fix the join conditions/columns - keep the join type as-is\n"

    prompt = f"""You are a SQL correction agent. Fix this SQL error:

ERROR: {error_message}

FAILED SQL:
{sql}

RELEVANT TABLE SCHEMAS (only tables used in the query above):
{chr(10).join(table_schemas) if table_schemas else "No tables found"}

RELEVANT RELATIONSHIPS (only between tables in query):
{json.dumps(relevant_relationships[:settings.sql_max_relationships_in_prompt], indent=2) if relevant_relationships else "No relationships found"}
{history_text}
{scoped_join_warning}
{join_type_warning}

INSTRUCTIONS:
1. Analyze the error message carefully - each numbered error shows the wrong column and available columns
2. Check the table schemas to find where the column actually exists
3. **CRITICAL: Column names are CASE-SENSITIVE and must match the schema EXACTLY**
   - Use camelCase as shown in the schema (e.g., workOrderNumber, NOT work_order_number)
   - Use exact column names from "Available columns:" in the error messages
   - The database uses camelCase naming (customerId, workOrderNumber, createdAt, etc.)
4. Fix the SQL query by:
   - Using the correct table name for each column
   - Ensuring all columns exist in their respective tables with EXACT case matching
   - Fixing any join conditions that reference wrong columns
   - If same table appears in multiple JOINs, keep only the most direct path
   - CRITICAL: Preserve ALL compound join conditions (AND clauses) - only fix column/table names
   - CRITICAL: Preserve join types (LEFT JOIN vs JOIN) - do NOT change them
{duplicate_table_instructions}{group_by_instructions}
5. Return ONLY the corrected SQL query, nothing else
6. Do NOT add comments or explanations

CORRECTED SQL QUERY:"""

    logger.info(f"[PROMPT] correct_sql prompt (attempt {correction_attempts + 1}):\n")
    logger.debug(f"[PROMPT] correct_sql prompt {prompt}")
    try:
        response = ctx.llm.invoke(prompt)
        corrected_sql = str(response.content).strip() if hasattr(response, "content") and response.content else ""

        # First, try to extract SQL from a markdown code block anywhere in the response
        corrected_sql = _extract_sql_from_markdown(corrected_sql)

        # Legacy cleanup: handle case where response starts with ``` but wasn't caught by markdown extraction
        if corrected_sql.startswith("```"):
            lines = corrected_sql.split("\n")
            corrected_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        # Strip leading "SQL" keyword if present
        if corrected_sql.upper().startswith("SQL"):
            corrected_sql = corrected_sql[3:].strip()

        logger.info(f"Corrected SQL (attempt {correction_attempts + 1}): {corrected_sql[:200]}...")

        rewritten_sql = rewrite_secure_tables(corrected_sql)

        state["sql"] = rewritten_sql
        state["last_sql_error"] = None

        if state.get("correction_history") is None:
            state["correction_history"] = []
        correction_history = state["correction_history"]
        if correction_history is not None:
            correction_history.append(
                {
                    "attempt": correction_attempts + 1,
                    "error": error_message,
                    "sql": corrected_sql[: settings.sql_max_sql_history_length],
                }
            )

        return state

    except Exception as e:
        logger.error(f"Error in correction agent: {e}")
        state["result"] = None
        state["query_resolved"] = False
        return state
