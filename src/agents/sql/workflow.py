"""
SQL agent workflow - graph construction
"""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.nodes import (
    detect_followup_node,
    extract_domain_terms_node,
    resolve_domain_terms_node,
    select_tables_node,
    filter_relationships_node,
    plan_joins_node,
    generate_sql_node,
    validate_sql_node,
    correct_sql_node,
    execute_node,
    finalize_node,
)
from src.config.settings import settings


def _route_after_validation(state: SQLGraphState) -> str:
    """Route after pre-execution validation."""
    validation_errors = state.get("validation_errors")
    if not validation_errors:
        return "execute"

    correction_attempts = state.get("sql_correction_attempts", 0)
    if correction_attempts < settings.sql_correction_max_attempts:
        logger.info(f"Validation failed, routing to correction agent (attempt {correction_attempts + 1})")
        return "correct_sql"
    else:
        logger.error(f"Max correction attempts reached. Validation errors: {validation_errors}")
        state["result"] = None
        state["query_resolved"] = False
        return "finalize"


def _route_after_execute(state: SQLGraphState) -> str:
    """Route after SQL execution."""
    result = state.get("result")

    if result is None:
        correction_attempts = state.get("sql_correction_attempts", 0)
        if correction_attempts < settings.sql_correction_max_attempts:
            logger.info(f"Execution failed, routing to correction agent (attempt {correction_attempts + 1})")
            return "correct_sql"
        else:
            return "finalize"

    if isinstance(result, str) and result.startswith("Error"):
        return "finalize"

    if state["retries"] > 0 and result is None:
        return "generate_sql"

    return "finalize"


def build_sql_workflow(ctx: SQLContext):
    """
    Build the SQL workflow graph with context bound to nodes.
    """
    g = StateGraph(SQLGraphState)

    g.add_node("detect_followup", lambda s: detect_followup_node(s, ctx))
    g.add_node("extract_domain_terms", lambda s: extract_domain_terms_node(s, ctx))
    g.add_node("resolve_domain_terms", lambda s: resolve_domain_terms_node(s, ctx))
    g.add_node("select_tables", lambda s: select_tables_node(s, ctx))
    g.add_node("filter_relationships", lambda s: filter_relationships_node(s, ctx))
    g.add_node("plan_joins", lambda s: plan_joins_node(s, ctx))
    g.add_node("generate_sql", lambda s: generate_sql_node(s, ctx))
    g.add_node("validate_sql", lambda s: validate_sql_node(s, ctx))
    g.add_node("correct_sql", lambda s: correct_sql_node(s, ctx))
    g.add_node("execute", lambda s: execute_node(s, ctx))
    g.add_node("finalize", lambda s: finalize_node(s, ctx))

    g.set_entry_point("detect_followup")
    g.add_edge("detect_followup", "extract_domain_terms")
    g.add_edge("extract_domain_terms", "resolve_domain_terms")
    g.add_edge("resolve_domain_terms", "select_tables")
    g.add_edge("select_tables", "filter_relationships")
    g.add_edge("filter_relationships", "plan_joins")
    g.add_edge("plan_joins", "generate_sql")
    g.add_edge("generate_sql", "validate_sql")

    g.add_conditional_edges(
        "validate_sql",
        _route_after_validation,
        {
            "execute": "execute",
            "correct_sql": "correct_sql",
            "finalize": "finalize",
        },
    )

    g.add_edge("correct_sql", "validate_sql")

    g.add_conditional_edges(
        "execute",
        _route_after_execute,
        {
            "finalize": "finalize",
            "correct_sql": "correct_sql",
            "generate_sql": "generate_sql",
        },
    )

    g.add_edge("finalize", END)
    return g.compile()
