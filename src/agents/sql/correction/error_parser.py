"""
SQL error parser - converts raw database errors to semantic error types.

This module is the ONLY place where we match against database-specific error strings.
All other code works with NormalizedError objects, making the system:
- Database-agnostic (easy to add Postgres, etc.)
- Version-independent (error messages can change)
- Testable (mock NormalizedError instead of raw strings)
"""

import re
from loguru import logger
from src.agents.sql.correction.error_types import SQLErrorType, NormalizedError


def normalize_error(error_message: str) -> NormalizedError:
    """
    Parse a raw database error message into a semantic error type.
    
    This function matches against known error patterns and extracts structured
    details. If no pattern matches, returns SQLErrorType.OTHER.
    
    Args:
        error_message: Raw error message from MySQL (or validation errors)
        
    Returns:
        NormalizedError with semantic type and extracted details
        
    Example:
        >>> error = normalize_error("Expression #2 of SELECT list is not in GROUP BY clause...")
        >>> error.error_type
        <SQLErrorType.GROUP_BY_VIOLATION: 'group_by_violation'>
        >>> error.details["expression_num"]
        2
    """
    # GROUP BY violation (MySQL only_full_group_by mode)
    if _is_group_by_violation(error_message):
        return _parse_group_by_violation(error_message)
    
    # Duplicate table/alias
    if _is_duplicate_alias(error_message):
        return _parse_duplicate_alias(error_message)
    
    # Unknown column
    if _is_unknown_column(error_message):
        return _parse_unknown_column(error_message)
    
    # Unknown table
    if _is_unknown_table(error_message):
        return _parse_unknown_table(error_message)
    
    # Ambiguous column
    if _is_ambiguous_column(error_message):
        return _parse_ambiguous_column(error_message)
    
    # Fallback: unrecognized error
    logger.debug(f"Could not normalize error, classifying as OTHER: {error_message[:100]}")
    return NormalizedError(
        error_type=SQLErrorType.OTHER,
        raw_message=error_message,
        details={}
    )


# ============================================================================
# Pattern Detection Functions
# ============================================================================

def _is_group_by_violation(error_message: str) -> bool:
    """Check if error is a GROUP BY violation."""
    return (
        "Expression #" in error_message and
        ("GROUP BY" in error_message or "only_full_group_by" in error_message.lower())
    )


def _is_duplicate_alias(error_message: str) -> bool:
    """Check if error is a duplicate table/alias."""
    return (
        "Not unique table/alias" in error_message or
        "1066" in error_message  # MySQL error code for duplicate alias
    )


def _is_unknown_column(error_message: str) -> bool:
    """Check if error is an unknown column."""
    return (
        "Unknown column" in error_message or
        "1054" in error_message  # MySQL error code for unknown column
    )


def _is_unknown_table(error_message: str) -> bool:
    """Check if error is an unknown table."""
    return (
        "Unknown table" in error_message or
        "Table" in error_message and "doesn't exist" in error_message or
        "1146" in error_message  # MySQL error code for unknown table
    )


def _is_ambiguous_column(error_message: str) -> bool:
    """Check if error is an ambiguous column reference."""
    return (
        "Ambiguous column" in error_message or
        "Column" in error_message and "is ambiguous" in error_message or
        "1052" in error_message  # MySQL error code for ambiguous column
    )


# ============================================================================
# Error Parsing Functions
# ============================================================================

def _parse_group_by_violation(error_message: str) -> NormalizedError:
    """
    Parse GROUP BY violation error.
    
    Example error:
    "Expression #2 of SELECT list is not in GROUP BY clause and contains 
     nonaggregated column 'crewos.workTime.startTime' which is not functionally 
     dependent on columns in GROUP BY clause"
    """
    details = {}
    
    # Extract expression number
    expr_match = re.search(r"Expression #(\d+)", error_message)
    if expr_match:
        details["expression_num"] = int(expr_match.group(1))
    
    # Extract column name
    column_match = re.search(r"column ['\"]([^'\"]+)['\"]", error_message)
    if column_match:
        details["column"] = column_match.group(1)
    
    logger.debug(f"Parsed GROUP_BY_VIOLATION: {details}")
    return NormalizedError(
        error_type=SQLErrorType.GROUP_BY_VIOLATION,
        raw_message=error_message,
        details=details
    )


def _parse_duplicate_alias(error_message: str) -> NormalizedError:
    """
    Parse duplicate table/alias error.
    
    Example error:
    "Not unique table/alias: 'users'"
    """
    details = {}
    
    # Extract table/alias name
    alias_match = re.search(r"table/alias[:\s]+['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    if alias_match:
        details["table"] = alias_match.group(1)
    
    logger.debug(f"Parsed DUPLICATE_ALIAS: {details}")
    return NormalizedError(
        error_type=SQLErrorType.DUPLICATE_ALIAS,
        raw_message=error_message,
        details=details
    )


def _parse_unknown_column(error_message: str) -> NormalizedError:
    """
    Parse unknown column error.
    
    Example error:
    "Unknown column 'users.invalid_col' in 'field list'"
    """
    details = {}
    
    # Extract column name
    column_match = re.search(r"column ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    if column_match:
        details["column"] = column_match.group(1)
    
    # Extract location (field list, where clause, etc.)
    location_match = re.search(r"in ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    if location_match:
        details["location"] = location_match.group(1)
    
    logger.debug(f"Parsed UNKNOWN_COLUMN: {details}")
    return NormalizedError(
        error_type=SQLErrorType.UNKNOWN_COLUMN,
        raw_message=error_message,
        details=details
    )


def _parse_unknown_table(error_message: str) -> NormalizedError:
    """
    Parse unknown table error.
    
    Example error:
    "Table 'database.invalid_table' doesn't exist"
    """
    details = {}
    
    # Extract table name
    table_match = re.search(r"[Tt]able ['\"]?([^'\"]+)['\"]?", error_message)
    if table_match:
        details["table"] = table_match.group(1)
    
    logger.debug(f"Parsed UNKNOWN_TABLE: {details}")
    return NormalizedError(
        error_type=SQLErrorType.UNKNOWN_TABLE,
        raw_message=error_message,
        details=details
    )


def _parse_ambiguous_column(error_message: str) -> NormalizedError:
    """
    Parse ambiguous column error.
    
    Example error:
    "Column 'id' in field list is ambiguous"
    """
    details = {}
    
    # Extract column name
    column_match = re.search(r"[Cc]olumn ['\"]([^'\"]+)['\"]", error_message)
    if column_match:
        details["column"] = column_match.group(1)
    
    logger.debug(f"Parsed AMBIGUOUS_COLUMN: {details}")
    return NormalizedError(
        error_type=SQLErrorType.AMBIGUOUS_COLUMN,
        raw_message=error_message,
        details=details
    )
