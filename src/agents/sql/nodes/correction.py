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


def _extract_select_clause(sql: str) -> str:
    """
    Extract the SELECT clause (list of columns/expressions) from a SQL query.
    Used to compare original vs corrected SQL and ensure SELECT wasn't changed.
    """
    if not sql or not sql.strip():
        return ""
    # Match SELECT ... up to the first FROM (word boundary)
    match = re.search(r"\bSELECT\s+(.*?)\s+FROM\s+", sql, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    select_body = match.group(1).strip()
    # Normalize whitespace for comparison
    return " ".join(select_body.split())


def _validate_correction_preserves_select(
    original_sql: str, corrected_sql: str, error_message: str
) -> bool:
    """
    Validate that correction doesn't change SELECT unless error was about SELECT.

    Returns True if correction is valid, False if it improperly changed SELECT.
    """
    err_lower = error_message.lower()
    # Allow SELECT to change only if the error is about the SELECT clause / field list
    if "field list" in err_lower or "in 'select'" in err_lower:
        return True
    original_select = _extract_select_clause(original_sql)
    corrected_select = _extract_select_clause(corrected_sql)
    if original_select != corrected_select:
        logger.warning(
            "Correction changed SELECT clause but error was not about SELECT. "
            "Original: %s... Corrected: %s...",
            original_select[:100] if original_select else "(empty)",
            corrected_select[:100] if corrected_select else "(empty)",
        )
        return False
    return True


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
    Simplified correction agent. Relies on the actual MySQL error message;
    no hardcoded handling per error type. Table schemas and relationships
    provide context; the LLM fixes based on the error text.
    """
    state = dict(state)
    sql = state.get("sql", "")
    validation_errors = state.get("validation_errors")
    if validation_errors:
        error_message = "\n".join([f"{i+1}. {err}" for i, err in enumerate(validation_errors)])
    else:
        error_message = state.get("last_sql_error") or "Unknown error"
    correction_attempts = state.get("sql_correction_attempts", 0)

    if correction_attempts >= settings.sql_correction_max_attempts:
        logger.error(
            f"Max correction attempts ({settings.sql_correction_max_attempts}) reached. Last error: {error_message[:200]}"
        )
        state["result"] = None
        state["query_resolved"] = False
        return state

    state["sql_correction_attempts"] = correction_attempts + 1

    # Tables referenced in the query (for schema and relationship context)
    alias_map = _build_alias_to_base_table_map(sql)
    table_pattern = r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    tables_in_sql = set()
    for table in re.findall(table_pattern, sql, re.IGNORECASE):
        tables_in_sql.add(from_secure_view(table))
    column_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)"
    for qualifier, _ in re.findall(column_pattern, sql):
        tables_in_sql.add(alias_map.get(qualifier, from_secure_view(qualifier)))
    tables_in_sql = {t for t in tables_in_sql if t in ctx.join_graph["tables"]}

    table_schemas = []
    for table_name in sorted(tables_in_sql):
        columns = ctx.join_graph["tables"][table_name].get("columns", [])
        columns_str = ", ".join(columns[: settings.sql_max_columns_in_correction])
        if len(columns) > settings.sql_max_columns_in_correction:
            columns_str += f" ... ({len(columns)} total columns)"
        table_schemas.append(f"{table_name}: {columns_str}")

    relevant_relationships = []
    for rel in state.get("allowed_relationships", []):
        from_base = from_secure_view(rel.get("from_table", ""))
        to_base = from_secure_view(rel.get("to_table", ""))
        if from_base in tables_in_sql or to_base in tables_in_sql:
            relevant_relationships.append(rel)

    history_text = ""
    correction_history = state.get("correction_history") or []
    if correction_history:
        history_text = "\nPREVIOUS ATTEMPTS:\n"
        for i, attempt in enumerate(correction_history[-3:], 1):
            history_text += f"{i}. Error: {attempt.get('error', 'Unknown')[:200]}\n"
            sql_preview = attempt.get("sql", "N/A")
            if len(sql_preview) > settings.sql_max_sql_history_length:
                sql_preview = sql_preview[: settings.sql_max_sql_history_length] + "..."
            history_text += f"   Fix tried: {sql_preview}\n"

    # When MySQL says "Expression #N" it means the N-th item in the SELECT list. Inject a hint so the model fixes the right one.
    expression_hint = ""
    if "Expression #" in error_message and ("GROUP BY" in error_message or "only_full_group_by" in error_message.lower()):
        expr_match = re.search(r"Expression #(\d+)", error_message)
        if expr_match:
            expr_num = int(expr_match.group(1))
            try:
                select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
                if select_match:
                    select_clause = select_match.group(1)
                    depth, expressions, current = 0, [], ""
                    for c in select_clause:
                        if c == "(":
                            depth += 1
                        elif c == ")":
                            depth -= 1
                        elif c == "," and depth == 0:
                            expressions.append(current.strip())
                            current = ""
                            continue
                        current += c
                    if current.strip():
                        expressions.append(current.strip())
                    if 0 < expr_num <= len(expressions):
                        expr = re.sub(r"\s+AS\s+.*$", "", expressions[expr_num - 1], flags=re.IGNORECASE).strip()
                        expression_hint = f"\nIMPORTANT: The error says Expression #{expr_num} (the {expr_num}-th column in SELECT). You MUST add this exact expression to GROUP BY: {expr}\n"
            except Exception:
                pass

    prompt = f"""You are a SQL correction agent. Fix this MySQL query error.

ERROR MESSAGE:
{error_message}
{expression_hint}
FAILED SQL:
{sql}

AVAILABLE TABLES AND COLUMNS (only tables used in the query):
{chr(10).join(table_schemas) if table_schemas else "No tables found"}

AVAILABLE RELATIONSHIPS (between tables in query):
{json.dumps(relevant_relationships[: settings.sql_max_relationships_in_prompt], indent=2) if relevant_relationships else "No relationships found"}
{history_text}
{_COMMON_ERROR_PATTERNS}

INSTRUCTIONS:
1. Read the error message carefully - MySQL errors are descriptive and tell you exactly what is wrong.
2. Identify which part of the query is causing the error.
3. Fix ONLY that specific issue - preserve everything else (SELECT columns, WHERE, JOINs, join types).
4. Column names are CASE-SENSITIVE; use camelCase as shown in the schemas.
5. Return ONLY the corrected SQL query. No markdown code blocks, no comments, no explanation.

CORRECTED SQL QUERY:"""

    prompt_preview = prompt[:500] if len(prompt) > 500 else prompt
    logger.info(
        f"[PROMPT] correct_sql (attempt {correction_attempts + 1}): You are a SQL correction agent. Fix this MySQL query error. Error: {error_message[:250]}..."
    )
    logger.info(f"[PROMPT] correct_sql prompt preview: {prompt_preview}...")
    logger.debug(f"[PROMPT] correct_sql full prompt: {prompt}")
    try:
        response = ctx.llm.invoke(prompt)
        corrected_sql = str(response.content).strip() if hasattr(response, "content") and response.content else ""
        corrected_sql = _extract_sql_from_markdown(corrected_sql)
        if corrected_sql.startswith("```"):
            lines = corrected_sql.split("\n")
            corrected_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
        if corrected_sql.upper().startswith("SQL"):
            corrected_sql = corrected_sql[3:].strip()

        logger.info(f"Corrected SQL (attempt {correction_attempts + 1}): {corrected_sql[:200]}...")

        if not _validate_correction_preserves_select(state["sql"], corrected_sql, error_message):
            logger.warning(
                "Correction agent changed SELECT clause; consider re-running with preserved SELECT."
            )

        rewritten_sql = rewrite_secure_tables(corrected_sql)
        state["sql"] = rewritten_sql
        state["last_sql_error"] = None

        if state.get("correction_history") is None:
            state["correction_history"] = []
        state["correction_history"].append(
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
