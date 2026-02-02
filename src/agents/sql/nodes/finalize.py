"""
SQL finalize node - parse result and format for BFF
"""

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.agents.sql.nodes.executor import _parse_sql_result


def finalize_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Finalize SQL result and parse structured data for BFF markdown conversion.
    """
    state = dict(state)
    if state.get("result") is None:
        state["final_answer"] = "No result."
        state["structured_result"] = None
        return state

    raw_result = state.get("result")
    column_names = state.get("column_names")

    if raw_result is None:
        structured_data = None
    else:
        structured_data = _parse_sql_result(raw_result, column_names)

    state["final_answer"] = raw_result
    state["structured_result"] = structured_data

    if structured_data:
        logger.info(f"✅ Parsed structured data: {len(structured_data)} items")
        if len(structured_data) > 0:
            logger.debug(f"First item keys: {list(structured_data[0].keys())}")
    else:
        logger.debug(
            f"⚠️ Could not parse structured data from result (length: {len(str(raw_result))} chars)"
        )
        logger.debug(f"Result preview: {str(raw_result)[:200]}...")

    return state
