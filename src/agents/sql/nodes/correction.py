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


def correct_sql_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Focused correction agent that fixes SQL errors.
    """
    state = dict(state)
    sql = state.get("sql", "")
    validation_errors = state.get("validation_errors")
    if validation_errors:
        error_message = state.get("last_sql_error") or " | ".join(validation_errors)
    else:
        error_message = state.get("last_sql_error") or "Unknown error"
    correction_attempts = state.get("sql_correction_attempts", 0)

    if correction_attempts >= settings.sql_correction_max_attempts:
        logger.error(f"Max correction attempts ({settings.sql_correction_max_attempts}) reached. Last error: {error_message[:200]}")
        state["result"] = None
        state["query_resolved"] = False
        return state

    state["sql_correction_attempts"] = correction_attempts + 1

    table_pattern = r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    tables_in_sql = set()
    for table in re.findall(table_pattern, sql, re.IGNORECASE):
        base_table = from_secure_view(table)
        tables_in_sql.add(base_table)

    column_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)"
    for table, _ in re.findall(column_pattern, sql):
        base_table = from_secure_view(table)
        tables_in_sql.add(base_table)

    logger.info(f"Tables found in SQL query (after conversion to base tables): {sorted(tables_in_sql)}")

    table_schemas = []
    for table_name in sorted(tables_in_sql):
        if table_name in ctx.join_graph["tables"]:
            columns = ctx.join_graph["tables"][table_name].get("columns", [])
            columns_str = ", ".join(columns[:settings.sql_max_columns_in_correction])
            if len(columns) > settings.sql_max_columns_in_correction:
                columns_str += f" ... ({len(columns)} total columns)"
            table_schemas.append(f"{table_name}: {columns_str}")
        else:
            logger.warning(f"Table {table_name} not found in join_graph, skipping schema")

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

    prompt = f"""You are a SQL correction agent. Fix this SQL error:

ERROR: {error_message}

FAILED SQL:
{sql}

RELEVANT TABLE SCHEMAS (only tables used in the query above):
{chr(10).join(table_schemas) if table_schemas else "No tables found"}

RELEVANT RELATIONSHIPS (only between tables in query):
{json.dumps(relevant_relationships[:settings.sql_max_relationships_in_prompt], indent=2) if relevant_relationships else "No relationships found"}
{history_text}

INSTRUCTIONS:
1. Analyze the error message carefully
2. Check the table schemas to find where the column actually exists
3. Fix the SQL query by:
   - Using the correct table name for each column
   - Ensuring all columns exist in their respective tables
   - Fixing any join conditions that reference wrong columns
   - If same table appears in multiple JOINs, keep only the most direct path
{duplicate_table_instructions}{group_by_instructions}
4. Return ONLY the corrected SQL query, nothing else
5. Do NOT add comments or explanations

CORRECTED SQL QUERY:"""

    logger.info(f"[PROMPT] correct_sql prompt (attempt {correction_attempts + 1}):\n")
    logger.debug(f"[PROMPT] correct_sql prompt {prompt}")
    try:
        response = ctx.llm.invoke(prompt)
        corrected_sql = str(response.content).strip() if hasattr(response, "content") and response.content else ""

        if corrected_sql.startswith("```"):
            lines = corrected_sql.split("\n")
            corrected_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

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
