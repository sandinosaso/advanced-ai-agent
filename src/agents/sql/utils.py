"""
SQL agent utilities
"""

import functools
import re
import time
import uuid
from typing import Optional
from loguru import logger


def entity_to_id_field(entity: str) -> Optional[str]:
    """
    Map referenced_entity (e.g. 'inspection', 'work order') to the standard id field name
    (e.g. inspectionId, workOrderId) so the SQL generator can filter by the main table's PK.
    """
    if not entity or not isinstance(entity, str):
        return None
    s = entity.strip()
    if not s:
        return None
    if s.endswith("Id"):
        return s
    parts = re.sub(r"([A-Z])", r" \1", s).split()
    if not parts:
        return None
    camel = parts[0].lower() + "".join(p.title() for p in parts[1:])
    return f"{camel}Id" if camel else None


def trace_step(step_name: str):
    """Decorator for tracing workflow step execution."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(state, ctx, *args, **kwargs):
            trace_id = state.get("trace_id") or str(uuid.uuid4())
            state = dict(state)
            state["trace_id"] = trace_id
            start = time.time()
            logger.info(
                f"[TRACE] step_start: {step_name} | trace_id={trace_id} | input_keys={list(state.keys())}"
            )
            try:
                result = func(state, ctx, *args, **kwargs)
                duration = time.time() - start
                logger.info(
                    f"[TRACE] step_end: {step_name} | trace_id={trace_id} | "
                    f"duration_ms={int(duration * 1000)} | output_keys={list(result.keys())}"
                )
                return result
            except Exception as e:
                logger.error(
                    f"[TRACE] step_error: {step_name} | trace_id={trace_id} | "
                    f"error={e} | state_keys={list(state.keys())}"
                )
                raise

        return wrapper

    return decorator
