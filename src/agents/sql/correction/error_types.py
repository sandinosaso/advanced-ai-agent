"""
SQL error type definitions for semantic error classification.

Instead of matching raw MySQL error strings throughout the codebase,
we normalize errors into semantic types that are:
- Database-agnostic
- Version-independent
- Easy to test and extend
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional


class SQLErrorType(Enum):
    """
    Semantic SQL error types.
    
    These represent the *meaning* of an error, not the specific database message.
    """
    # Column/table reference errors
    UNKNOWN_COLUMN = "unknown_column"
    UNKNOWN_TABLE = "unknown_table"
    AMBIGUOUS_COLUMN = "ambiguous_column"
    
    # Join errors
    DUPLICATE_ALIAS = "duplicate_alias"
    MISSING_JOIN = "missing_join"
    INVALID_JOIN_COLUMN = "invalid_join_column"
    
    # GROUP BY errors
    GROUP_BY_VIOLATION = "group_by_violation"
    
    # Syntax errors
    SYNTAX_ERROR = "syntax_error"
    
    # Catch-all for unrecognized errors
    OTHER = "other"


@dataclass
class NormalizedError:
    """
    Normalized representation of a SQL error.
    
    Attributes:
        error_type: Semantic error type (from SQLErrorType enum)
        raw_message: Original error message from the database
        details: Structured error details (e.g., {"expression_num": 2, "column": "workTime.startTime"})
        
    Example:
        >>> error = NormalizedError(
        ...     error_type=SQLErrorType.GROUP_BY_VIOLATION,
        ...     raw_message="Expression #2 of SELECT list is not in GROUP BY clause...",
        ...     details={"expression_num": 2, "column": "workTime.startTime"}
        ... )
        >>> error.error_type
        <SQLErrorType.GROUP_BY_VIOLATION: 'group_by_violation'>
        >>> error.details["expression_num"]
        2
    """
    error_type: SQLErrorType
    raw_message: str
    details: Dict[str, Any]
    
    def __post_init__(self):
        """Validate that error_type is a SQLErrorType enum member."""
        if not isinstance(self.error_type, SQLErrorType):
            raise TypeError(f"error_type must be SQLErrorType, got {type(self.error_type)}")
    
    def get_detail(self, key: str, default: Any = None) -> Any:
        """
        Safely get a detail value with a default.
        
        Args:
            key: Detail key to retrieve
            default: Default value if key not found
            
        Returns:
            Detail value or default
        """
        return self.details.get(key, default)
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"NormalizedError(type={self.error_type.value}, details={self.details})"
