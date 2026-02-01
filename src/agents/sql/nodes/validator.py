"""
SQL pre-execution validation node
"""

import re
from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.sql.execution.secure_rewriter import from_secure_view
from src.agents.sql.planning import extract_tables_from_join_plan


@trace_step("validate_sql")
def validate_sql_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Validate SQL before execution to catch column/join errors early.
    """
    state = dict(state)
    if not settings.sql_pre_validation_enabled:
        state["validation_errors"] = None
        return state

    sql = state.get("sql", "")
    if not sql:
        state["validation_errors"] = None
        return state

    errors = []

    pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b"
    matches = re.findall(pattern, sql)

    all_tables = set(state.get("tables", []))
    join_plan_text = state.get("join_plan", "")
    tables_from_join_plan = extract_tables_from_join_plan(
        join_plan_text, ctx.join_graph["tables"]
    )
    all_tables.update(tables_from_join_plan)

    table_name_map = {t.lower(): t for t in ctx.join_graph["tables"].keys()}

    for table_name, column_name in matches:
        check_table = from_secure_view(table_name)

        if check_table.lower() in table_name_map:
            actual_table = table_name_map[check_table.lower()]
            if actual_table in ctx.join_graph["tables"]:
                columns = ctx.join_graph["tables"][actual_table].get("columns", [])
                if column_name not in columns:
                    possible_tables = []
                    for t in all_tables:
                        if t in ctx.join_graph["tables"]:
                            t_columns = ctx.join_graph["tables"][t].get("columns", [])
                            if column_name in t_columns:
                                possible_tables.append(t)

                    if possible_tables:
                        error_msg = (
                            f"Column '{column_name}' does NOT exist in table '{check_table}'. "
                            f"Found in: {', '.join(possible_tables)}. "
                            f"Available columns in {check_table}: {', '.join(columns[:settings.sql_max_columns_in_validation])}"
                        )
                    else:
                        error_msg = (
                            f"Column '{column_name}' does NOT exist in table '{check_table}'. "
                            f"Available columns: {', '.join(columns[:settings.sql_max_columns_in_validation])}"
                        )
                    errors.append(error_msg)
                    logger.warning(f"Validation error: {error_msg}")

    if errors:
        state["validation_errors"] = errors
        state["last_sql_error"] = " | ".join(errors)
        logger.error(f"SQL validation failed with {len(errors)} errors")
    else:
        state["validation_errors"] = None
        logger.debug("SQL validation passed")

    return state
