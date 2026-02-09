"""
Correction strategy selection - decides how to fix SQL errors.

This module determines whether an error can be fixed:
1. Deterministically (AST transformation, no LLM)
2. Via LLM disambiguation (multiple valid options, LLM chooses)
3. Via LLM fallback (unknown error type)

The strategy selection is based on:
- Error type (from error normalization)
- Query structure (from AST analysis)
- Schema context (from join graph)
"""

from enum import Enum
from typing import List, Dict, Optional
from loguru import logger

from src.agents.sql.correction.error_types import SQLErrorType, NormalizedError
from src.agents.sql.context import SQLContext


class CorrectionStrategy(Enum):
    """
    Strategy for fixing a SQL error.
    """
    DETERMINISTIC_FIX = "deterministic"      # Use AST fixer (no LLM)
    LLM_DISAMBIGUATION = "llm_choice"        # Multiple valid options (LLM chooses)
    LLM_FALLBACK = "llm_fallback"            # Unknown error type (LLM fixes)


def select_strategy(
    normalized_error: NormalizedError,
    sql: str,
    ctx: SQLContext
) -> CorrectionStrategy:
    """
    Decide how to fix a SQL error.
    
    Args:
        normalized_error: Normalized error with semantic type
        sql: Failed SQL query
        ctx: SQL context (join graph, ontology, etc.)
        
    Returns:
        CorrectionStrategy indicating how to proceed
        
    Example:
        >>> error = NormalizedError(SQLErrorType.GROUP_BY_VIOLATION, "...", {"expression_num": 2})
        >>> strategy = select_strategy(error, sql, ctx)
        >>> strategy
        <CorrectionStrategy.DETERMINISTIC_FIX: 'deterministic'>
    """
    # GROUP BY violations are always deterministic
    if normalized_error.error_type == SQLErrorType.GROUP_BY_VIOLATION:
        if normalized_error.get_detail("expression_num"):
            logger.debug("Strategy: DETERMINISTIC_FIX (GROUP BY violation with expression number)")
            return CorrectionStrategy.DETERMINISTIC_FIX
        else:
            logger.debug("Strategy: LLM_FALLBACK (GROUP BY violation without expression number)")
            return CorrectionStrategy.LLM_FALLBACK
    
    # Duplicate alias is deterministic if we know which table
    if normalized_error.error_type == SQLErrorType.DUPLICATE_ALIAS:
        if normalized_error.get_detail("table"):
            logger.debug("Strategy: DETERMINISTIC_FIX (duplicate alias with table name)")
            return CorrectionStrategy.DETERMINISTIC_FIX
        else:
            logger.debug("Strategy: LLM_FALLBACK (duplicate alias without table name)")
            return CorrectionStrategy.LLM_FALLBACK
    
    # Unknown column - check if it's ambiguous (multiple candidates)
    if normalized_error.error_type == SQLErrorType.UNKNOWN_COLUMN:
        column = normalized_error.get_detail("column")
        if column:
            candidates = _find_column_candidates(column, ctx)
            if len(candidates) == 0:
                logger.debug("Strategy: LLM_FALLBACK (unknown column, no candidates)")
                return CorrectionStrategy.LLM_FALLBACK
            elif len(candidates) == 1:
                logger.debug(f"Strategy: DETERMINISTIC_FIX (unknown column, 1 candidate: {candidates[0]})")
                return CorrectionStrategy.DETERMINISTIC_FIX
            else:
                logger.debug(f"Strategy: LLM_DISAMBIGUATION (unknown column, {len(candidates)} candidates)")
                return CorrectionStrategy.LLM_DISAMBIGUATION
    
    # All other error types: fallback to LLM
    logger.debug(f"Strategy: LLM_FALLBACK (error type: {normalized_error.error_type.value})")
    return CorrectionStrategy.LLM_FALLBACK


def _find_column_candidates(column: str, ctx: SQLContext) -> List[str]:
    """
    Find which tables have a column with the given name.
    
    Args:
        column: Column name (may include table prefix like "users.id" or just "id")
        ctx: SQL context with join graph
        
    Returns:
        List of table names that have this column
        
    Example:
        >>> candidates = _find_column_candidates("id", ctx)
        >>> candidates
        ['user', 'employee', 'workOrder', 'customer']  # All tables with 'id' column
    """
    # Strip table prefix if present (e.g., "users.id" -> "id")
    if "." in column:
        column = column.split(".")[-1]
    
    candidates = []
    for table_name, table_info in ctx.join_graph.get("tables", {}).items():
        columns = table_info.get("columns", [])
        if column in columns:
            candidates.append(table_name)
    
    logger.debug(f"Column '{column}' found in {len(candidates)} tables: {candidates}")
    return candidates
