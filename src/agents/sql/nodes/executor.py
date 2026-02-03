"""
SQL execution node
"""

import ast
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings


def _parse_sql_result(
    raw_result: str, column_names: Optional[List[str]] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Parse SQL result into structured data with proper column names.
    """
    if not raw_result or not raw_result.strip():
        return None

    result_str = str(raw_result).strip()

    try:
        if result_str.startswith("[") or result_str.startswith("{"):
            parsed = json.loads(result_str)
            if isinstance(parsed, list):
                structured = []
                for item in parsed:
                    if isinstance(item, dict):
                        structured.append(item)
                    elif isinstance(item, (list, tuple)):
                        if column_names and len(column_names) == len(item):
                            structured.append(
                                {column_names[i]: val for i, val in enumerate(item)}
                            )
                        else:
                            structured.append(
                                {f"col_{i}": val for i, val in enumerate(item)}
                            )
                    else:
                        structured.append({"value": item})
                return structured if structured else None
            elif isinstance(parsed, dict):
                return [parsed]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    try:
        if result_str.startswith("["):
            preprocessed = result_str

            date_pattern = r"datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)"

            def replace_date(match):
                year, month, day = match.groups()
                return f"'{year}-{month.zfill(2)}-{day.zfill(2)}'"

            preprocessed = re.sub(date_pattern, replace_date, preprocessed)

            datetime_pattern = r"datetime\.datetime\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+))?(?:,\s*(\d+))?(?:,\s*(\d+))?\)"

            def replace_datetime(match):
                groups = match.groups()
                year, month, day = groups[0], groups[1], groups[2]
                hour = groups[3] if groups[3] else "0"
                minute = groups[4] if groups[4] else "0"
                second = groups[5] if groups[5] else "0"
                return f"'{year}-{month.zfill(2)}-{day.zfill(2)}T{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}'"

            preprocessed = re.sub(datetime_pattern, replace_datetime, preprocessed)

            parsed = ast.literal_eval(preprocessed)

            if isinstance(parsed, list) and len(parsed) > 0:
                structured = []
                for row in parsed:
                    if isinstance(row, (list, tuple)):
                        row_dict = {}
                        for i, val in enumerate(row):
                            col_name = (
                                column_names[i]
                                if column_names and i < len(column_names)
                                else f"col_{i}"
                            )
                            if val is None:
                                row_dict[col_name] = None
                            elif isinstance(val, (str, int, float, bool)):
                                row_dict[col_name] = val
                            else:
                                row_dict[col_name] = str(val)
                        structured.append(row_dict)
                    elif isinstance(row, dict):
                        clean_dict = {}
                        for k, v in row.items():
                            if v is None or isinstance(
                                v, (str, int, float, bool, list, dict)
                            ):
                                clean_dict[k] = v
                            else:
                                clean_dict[k] = str(v)
                        structured.append(clean_dict)
                    else:
                        structured.append(
                            {"value": str(row) if row is not None else None}
                        )
                return structured if structured else None
    except (ValueError, SyntaxError, TypeError) as e:
        logger.debug(
            f"Failed to parse Python literal: {e}, result_str preview: {result_str[:200]}"
        )
        pass

    return None


def execute_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Execute SQL and validate result.
    """
    state = dict(state)
    logger.info(f"Executing SQL: {state['sql']}")

    try:
        res, column_names = ctx.sql_tool.run_query_with_columns(state["sql"])
        state["column_names"] = column_names
        logger.debug(f"Query returned {len(column_names)} columns: {column_names}")

        state["last_sql_error"] = None
        state["validation_errors"] = None

    except Exception as e:
        error_str = str(e)
        state["last_sql_error"] = error_str
        state["column_names"] = None

        correction_attempts = state.get("sql_correction_attempts", 0)
        if correction_attempts < settings.sql_correction_max_attempts:
            logger.warning(f"SQL execution error (attempt {correction_attempts + 1}): {error_str[:200]}")
            state["result"] = None
            return state
        else:
            logger.error(f"Max correction attempts reached. Final error: {error_str}")
            state["result"] = None
            state["query_resolved"] = False
            return state

    is_empty = (
        res is None
        or (str(res).strip() == "")
        or ("[]" in str(res).strip())
    )

    if is_empty and state["retries"] < 1:
        state["retries"] += 1

        feedback = """
The query returned an empty result set.
Re-check join direction, join keys, and filters (dates especially).
If date filters exist, ensure you're filtering on the correct table columns.
"""

        state["join_plan"] = state["join_plan"] + "\n\n" + feedback
        state["result"] = None
        state["column_names"] = None
        return state

    state["result"] = str(res)
    return state
