"""
SQL correction system - deterministic fixes and error normalization.

This package provides a structured approach to SQL error correction:
1. Error normalization: Convert raw DB errors to semantic types
2. Strategy selection: Decide between deterministic fix vs LLM
3. Deterministic fixers: AST-based SQL transformations (no LLM)
4. LLM disambiguation: Only for ambiguous cases
"""

from src.agents.sql.correction.error_types import SQLErrorType, NormalizedError
from src.agents.sql.correction.error_parser import normalize_error
from src.agents.sql.correction.fixers import fix_group_by_violation, fix_duplicate_join
from src.agents.sql.correction.metrics import (
    record_fix,
    get_metrics_summary,
    log_metrics_summary,
    reset_metrics,
)

# Import strategies conditionally to avoid circular imports
try:
    from src.agents.sql.correction.strategies import CorrectionStrategy, select_strategy
    _STRATEGIES_AVAILABLE = True
except ImportError:
    _STRATEGIES_AVAILABLE = False
    CorrectionStrategy = None
    select_strategy = None

__all__ = [
    "SQLErrorType",
    "NormalizedError",
    "normalize_error",
    "fix_group_by_violation",
    "fix_duplicate_join",
    "CorrectionStrategy",
    "select_strategy",
    "record_fix",
    "get_metrics_summary",
    "log_metrics_summary",
    "reset_metrics",
]
