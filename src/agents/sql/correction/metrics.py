"""
Correction metrics - track success rates for deterministic vs LLM fixes.

This module provides observability into the correction system:
- Which error types are most common
- Which fixes succeed deterministically vs need LLM
- Which errors still fail after correction

Use this data to:
- Identify new error patterns to add deterministic fixers for
- Tune the LLM prompts for remaining ambiguous cases
- Monitor correction system health
"""

from collections import Counter
from typing import Dict, Optional
from loguru import logger

from src.agents.sql.correction.error_types import SQLErrorType


# Global metrics (in-memory for now; could be persisted to DB/Redis)
correction_metrics: Dict[str, Counter] = {
    "deterministic_fixes": Counter(),  # {GROUP_BY_VIOLATION: 45, DUPLICATE_ALIAS: 12}
    "llm_fixes": Counter(),            # {UNKNOWN_COLUMN: 23, OTHER: 8}
    "failures": Counter(),             # {GROUP_BY_VIOLATION: 2, OTHER: 5}
}


def record_fix(
    error_type: SQLErrorType,
    method: str,
    success: bool,
    attempt_num: int = 1
) -> None:
    """
    Record a correction attempt.
    
    Args:
        error_type: Semantic error type (from normalization)
        method: How the fix was attempted ("deterministic_group_by", "llm_fallback", etc.)
        success: Whether the fix succeeded
        attempt_num: Which attempt this was (1, 2, 3)
        
    Example:
        >>> record_fix(SQLErrorType.GROUP_BY_VIOLATION, "deterministic_group_by", success=True)
        >>> correction_metrics["deterministic_fixes"][SQLErrorType.GROUP_BY_VIOLATION]
        1
    """
    error_name = error_type.value
    
    if success:
        if method.startswith("deterministic"):
            correction_metrics["deterministic_fixes"][error_name] += 1
            logger.debug(f"✅ Recorded deterministic fix: {error_name} via {method}")
        elif method.startswith("llm"):
            correction_metrics["llm_fixes"][error_name] += 1
            logger.debug(f"✅ Recorded LLM fix: {error_name} via {method}")
    else:
        correction_metrics["failures"][error_name] += 1
        logger.debug(f"❌ Recorded failure: {error_name} (attempt {attempt_num})")


def get_metrics_summary() -> Dict[str, any]:
    """
    Get a summary of correction metrics.
    
    Returns:
        Dict with correction statistics
        
    Example:
        >>> summary = get_metrics_summary()
        >>> summary["total_deterministic"]
        57
        >>> summary["deterministic_rate"]
        0.85
    """
    total_deterministic = sum(correction_metrics["deterministic_fixes"].values())
    total_llm = sum(correction_metrics["llm_fixes"].values())
    total_failures = sum(correction_metrics["failures"].values())
    total_attempts = total_deterministic + total_llm + total_failures
    
    return {
        "total_attempts": total_attempts,
        "total_deterministic": total_deterministic,
        "total_llm": total_llm,
        "total_failures": total_failures,
        "deterministic_rate": total_deterministic / total_attempts if total_attempts > 0 else 0.0,
        "success_rate": (total_deterministic + total_llm) / total_attempts if total_attempts > 0 else 0.0,
        "by_error_type": {
            "deterministic": dict(correction_metrics["deterministic_fixes"]),
            "llm": dict(correction_metrics["llm_fixes"]),
            "failures": dict(correction_metrics["failures"]),
        }
    }


def log_metrics_summary() -> None:
    """
    Log a summary of correction metrics at INFO level.
    
    Useful for debugging and monitoring correction system health.
    """
    summary = get_metrics_summary()
    
    if summary["total_attempts"] == 0:
        logger.info("No correction attempts recorded yet")
        return
    
    logger.info("=" * 60)
    logger.info("SQL CORRECTION METRICS")
    logger.info("=" * 60)
    logger.info(f"Total attempts: {summary['total_attempts']}")
    logger.info(f"Deterministic fixes: {summary['total_deterministic']} ({summary['deterministic_rate']:.1%})")
    logger.info(f"LLM fixes: {summary['total_llm']}")
    logger.info(f"Failures: {summary['total_failures']}")
    logger.info(f"Overall success rate: {summary['success_rate']:.1%}")
    logger.info("=" * 60)
    
    # Top error types
    all_errors = Counter()
    for category in ["deterministic", "llm", "failures"]:
        for error_type, count in summary["by_error_type"][category].items():
            all_errors[error_type] += count
    
    if all_errors:
        logger.info("Top error types:")
        for error_type, count in all_errors.most_common(5):
            logger.info(f"  - {error_type}: {count}")


def reset_metrics() -> None:
    """Reset all metrics (useful for testing)."""
    correction_metrics["deterministic_fixes"].clear()
    correction_metrics["llm_fixes"].clear()
    correction_metrics["failures"].clear()
    logger.debug("Correction metrics reset")
