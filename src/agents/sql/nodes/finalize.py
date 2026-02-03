"""
SQL finalize node - parse result and format for BFF
"""

from typing import Optional

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.agents.sql.nodes.executor import _parse_sql_result


def _empty_result_message(question: str) -> str:
    """
    Build a friendly, contextual message when the query returns no data.
    Uses a short preview of the user's question so the response sounds relevant.
    """
    q = (question or "").strip()
    preview = (q[:70] + "…") if len(q) > 70 else q
    if preview:
        return (
            f"I couldn't find any data that matches your request"
            f' about "{preview}". '
            "You could try broadening your criteria—for example, a different time/location range "
            "or less specific filters might return results."
        )
    return (
        "I couldn't find any data that matches your request. "
        "You could try broadening your criteria or adjusting filters to see if that returns results."
    )


def _execution_failed_message(question: str) -> str:
    """
    User-friendly message when the query could not be resolved after all retries
    (DB error, validation error, or correction exhausted). Avoids exposing raw errors.
    """
    q = (question or "").strip()
    preview = (q[:60] + "…") if len(q) > 60 else q
    if preview:
        return (
            "I'm still learning the database and business rules, and I couldn't answer "
            f'your question about "{preview}" this time. '
            "Please try rephrasing or simplifying the question; if it keeps happening, "
            "your team may need to adjust how this is modeled."
        )
    return (
        "I'm still learning the database and business rules, and I couldn't answer "
        "your question this time. Please try rephrasing or simplifying; "
        "if it keeps happening, your team may need to adjust how this is modeled."
    )


def _is_empty_result(
    raw_result: Optional[str], structured_data: Optional[list]
) -> bool:
    """True if the query result is effectively empty (no rows)."""
    if raw_result is None:
        return True
    s = str(raw_result).strip()
    if s in ("", "[]"):
        return True
    if structured_data is not None and len(structured_data) == 0:
        return True
    return False


def _is_error_result(raw_result: Optional[str]) -> bool:
    """True if result looks like an unrecoverable error (should not be shown to user)."""
    if not raw_result:
        return False
    s = str(raw_result).strip()
    return s.startswith("Error") or s.startswith("SQL validation failed")


def finalize_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Finalize SQL result and format for BFF.
    - Empty result → contextual "no data" message.
    - Unresolved after retries (query_resolved=False or result starts with "Error") → friendly "still learning" message.
    - Success → pass through result and set query_resolved=True.
    """
    state = dict(state)
    raw_result = state.get("result")
    query_resolved = state.get("query_resolved")

    # Unresolved after all retries: show friendly message, never raw error
    if query_resolved is False:
        state["final_answer"] = _execution_failed_message(state.get("question") or "")
        state["structured_result"] = None
        state["query_resolved"] = False
        logger.info("Query unresolved after retries: returning friendly 'still learning' message")
        return state

    if raw_result is None:
        state["final_answer"] = _empty_result_message(state.get("question") or "")
        state["structured_result"] = None
        state["query_resolved"] = True
        return state

    column_names = state.get("column_names")
    structured_data = _parse_sql_result(raw_result, column_names) if raw_result else None

    # Backward compat: result is an error string (e.g. from older workflow path)
    if _is_error_result(raw_result):
        state["final_answer"] = _execution_failed_message(state.get("question") or "")
        state["structured_result"] = None
        state["query_resolved"] = False
        logger.info("Error-like result: returning friendly 'still learning' message")
        return state

    if _is_empty_result(raw_result, structured_data):
        state["final_answer"] = _empty_result_message(state.get("question") or "")
        state["structured_result"] = None
        state["query_resolved"] = True
        logger.info("Empty result: returning contextual 'no data' message")
        return state

    state["final_answer"] = raw_result
    state["structured_result"] = structured_data
    state["query_resolved"] = True

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
