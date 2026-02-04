"""
Secure View Rewriting - SQL Security Layer

This module handles rewriting SQL queries to use secure views for encrypted tables.
This is the ONLY place where secure_* rewriting should happen.

Architecture:
- Physical tables: What exists in MySQL (user, employee, workOrder, etc.)
- Secure views: Explicit, curated views that decrypt data (secure_user, secure_employee, etc.)
- Logical entities: What the user means ("employee", "work order", etc.)

Only SOME logical entities map to secure views. All others map directly to base tables.
This mapping is explicit and defined in config/constants.py.
"""

import re
from typing import Set, Optional
from loguru import logger

from src.utils.sql.secure_views import (
    get_secure_view_map,
    get_secure_views,
    is_secure_table as is_secure_table_util,
    to_secure_view as to_secure_view_util
)


# ============================================================================
# Core Functions
# ============================================================================

def is_secure_table(table: str) -> bool:
    """
    Check if a table requires secure view access.
    
    Args:
        table: Table name (case-insensitive)
        
    Returns:
        True if table must be accessed via secure view
        
    Examples:
        >>> is_secure_table("employee")
        True
        >>> is_secure_table("workOrder")
        True
        >>> is_secure_table("inspections")
        False
    """
    # Delegate to utility function
    return is_secure_table_util(table)


def to_secure_view(table: str) -> str:
    """
    Convert base table to secure view if applicable.
    Otherwise return table unchanged.
    
    Args:
        table: Table name (case-insensitive)
        
    Returns:
        Secure view name if table requires it, otherwise original table
        
    Examples:
        >>> to_secure_view("employee")
        "secure_employee"
        >>> to_secure_view("workOrder")
        "secure_workorder"
        >>> to_secure_view("inspections")
        "inspections"
        >>> to_secure_view("EMPLOYEE")
        "secure_employee"
    """
    # Delegate to utility function
    return to_secure_view_util(table)


def from_secure_view(table: str) -> str:
    """
    Convert secure view to base table if applicable.
    Otherwise return table unchanged.
    
    This is the reverse of to_secure_view().
    
    Args:
        table: Table name (could be secure view or base table)
        
    Returns:
        Base table name if table is a secure view, otherwise original table
        
    Examples:
        >>> from_secure_view("secure_employee")
        "employee"
        >>> from_secure_view("secure_workorder")
        "workOrder"
        >>> from_secure_view("inspections")
        "inspections"
        >>> from_secure_view("employee")
        "employee"
    """
    secure_view_map = get_secure_view_map()
    
    # Check if it's a secure view (exact match)
    for base_table, secure_view in secure_view_map.items():
        if table == secure_view:
            return base_table
        # Case-insensitive match
        if table.lower() == secure_view.lower():
            return base_table
    
    # Check if it starts with secure_ prefix (fallback for edge cases)
    if table.lower().startswith("secure_"):
        suffix = table[7:]  # Remove "secure_" prefix
        # Try to find matching base table
        for base_table, secure_view in secure_view_map.items():
            if suffix.lower() == base_table.lower() or suffix.lower() == secure_view[7:].lower():
                return base_table
    
    # No match, return original
    return table


def rewrite_secure_tables(sql: str) -> str:
    """
    Replace base tables with secure views ONLY for allow-listed tables.
    
    Uses word boundary matching to avoid partial matches, and skips
    replacements inside string literals to preserve data values.
    This is the ONLY place where secure_* rewriting should happen.
    
    Args:
        sql: Original SQL query
        
    Returns:
        SQL with base tables replaced by secure views where applicable
        
    Examples:
        >>> sql = "SELECT * FROM employee WHERE id = 1"
        >>> rewrite_secure_tables(sql)
        "SELECT * FROM secure_employee WHERE id = 1"
        
        >>> sql = "SELECT * FROM inspections WHERE id = 1"
        >>> rewrite_secure_tables(sql)
        "SELECT * FROM inspections WHERE id = 1"  # unchanged
        
        >>> sql = "SELECT e.name FROM employee e JOIN workOrder wo ON e.id = wo.employeeId"
        >>> rewrite_secure_tables(sql)
        "SELECT e.name FROM secure_employee e JOIN secure_workorder wo ON e.id = wo.employeeId"
        
        >>> sql = "SELECT * FROM customer WHERE customerName = 'Main Default Customer'"
        >>> rewrite_secure_tables(sql)
        "SELECT * FROM secure_customer WHERE customerName = 'Main Default Customer'"
    """
    rewritten_sql = sql
    replacements_made = []
    
    secure_view_map = get_secure_view_map()
    for base_table, secure_view in secure_view_map.items():
        # Use word boundaries to avoid partial matches
        # Case-insensitive replacement preserves the original case in non-matching parts
        pattern = rf"\b{re.escape(base_table)}\b"
        
        # Find all matches with their positions
        matches = list(re.finditer(pattern, rewritten_sql, flags=re.IGNORECASE))
        
        if not matches:
            continue
        
        # Track if we'll make any replacements
        will_replace = False
        
        # Build new SQL by processing matches in reverse order (to preserve positions)
        for match in reversed(matches):
            start, end = match.span()
            
            # Check if this match is inside a string literal
            if _is_inside_string_literal(rewritten_sql, start):
                # Skip replacement - this is a data value, not a table/column name
                logger.debug(f"Skipping replacement of '{match.group()}' at position {start} (inside string literal)")
                continue
            
            # Safe to replace - not inside a string literal
            rewritten_sql = rewritten_sql[:start] + secure_view + rewritten_sql[end:]
            will_replace = True
        
        if will_replace:
            replacements_made.append(f"{base_table} → {secure_view}")
    
    # Log rewrites for observability
    if replacements_made:
        logger.debug(f"Rewrote secure tables: {', '.join(replacements_made)}")
    
    return rewritten_sql


def _is_inside_string_literal(sql: str, position: int) -> bool:
    """
    Check if a position in SQL is inside a string literal.
    
    Handles both single quotes (') and double quotes (").
    Takes into account escaped quotes.
    
    Args:
        sql: SQL query string
        position: Character position to check
        
    Returns:
        True if position is inside a string literal, False otherwise
        
    Examples:
        >>> sql = "SELECT * FROM customer WHERE name = 'Main Default Customer'"
        >>> _is_inside_string_literal(sql, 14)  # 'customer' in FROM clause
        False
        >>> _is_inside_string_literal(sql, 52)  # 'Customer' in string value
        True
    """
    # Count quotes before the position
    single_quote_count = 0
    double_quote_count = 0
    i = 0
    
    while i < position:
        char = sql[i]
        
        # Check for escaped quotes (preceded by backslash)
        if i > 0 and sql[i-1] == '\\':
            i += 1
            continue
        
        if char == "'":
            single_quote_count += 1
        elif char == '"':
            double_quote_count += 1
        
        i += 1
    
    # If odd number of quotes before position, we're inside a string
    # Check both single and double quotes
    inside_single_quotes = (single_quote_count % 2) == 1
    inside_double_quotes = (double_quote_count % 2) == 1
    
    return inside_single_quotes or inside_double_quotes


def extract_tables_from_sql(sql: str) -> Set[str]:
    """
    Extract table names from SQL query.
    
    This is a simple heuristic-based extraction. It looks for:
    - FROM tablename
    - JOIN tablename
    - INTO tablename
    
    Args:
        sql: SQL query
        
    Returns:
        Set of table names found in the query
        
    Note:
        This is a best-effort extraction and may not catch all edge cases.
        For production, consider using a proper SQL parser like sqlparse.
    """
    tables = set()
    
    # Normalize SQL for easier parsing
    sql_normalized = sql.upper()
    
    # Patterns to match: FROM table, JOIN table, INTO table
    patterns = [
        r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, sql_normalized)
        for match in matches:
            table_name = match.group(1).lower()
            tables.add(table_name)
    
    return tables


def validate_tables_exist(sql: str, known_tables: Set[str]) -> None:
    """
    Validate that all tables used in SQL exist in the database.
    
    This turns silent LLM drift into fast, debuggable failures.
    
    Args:
        sql: SQL query to validate
        known_tables: Set of valid table names (case-insensitive)
        
    Raises:
        ValueError: If query references non-existent tables
        
    Examples:
        >>> known = {"secure_employee", "inspections", "worktime"}
        >>> sql = "SELECT * FROM secure_employee"
        >>> validate_tables_exist(sql, known)  # OK
        
        >>> sql = "SELECT * FROM secure_inspections"
        >>> validate_tables_exist(sql, known)  # Raises ValueError
    """
    used_tables = extract_tables_from_sql(sql)
    known_tables_lower = {t.lower() for t in known_tables}
    
    invalid_tables = []
    for table in used_tables:
        if table.lower() not in known_tables_lower:
            invalid_tables.append(table)
    
    if invalid_tables:
        error_msg = (
            f"Query references non-existent table(s): {', '.join(invalid_tables)}. "
            f"Available tables: {', '.join(sorted(known_tables_lower))}"
        )
        logger.error(f"Table validation failed: {error_msg}")
        raise ValueError(error_msg)


def get_secure_view_for_entity(entity: str) -> Optional[str]:
    """
    Get the secure view name for a logical entity.
    
    Args:
        entity: Logical entity name (e.g., "employee", "work order")
        
    Returns:
        Secure view name if entity requires one, None otherwise
        
    Examples:
        >>> get_secure_view_for_entity("employee")
        "secure_employee"
        >>> get_secure_view_for_entity("inspection")
        None
    """
    # Normalize entity name (remove spaces, lowercase)
    normalized = entity.lower().replace(" ", "").replace("_", "")
    
    secure_view_map = get_secure_view_map()
    if normalized in secure_view_map:
        return secure_view_map[normalized]
    
    return None


# ============================================================================
# Validation on Import (Fail Fast)
# ============================================================================

# ============================================================================
# Logging/Debug Utilities
# ============================================================================

def log_secure_view_config():
    """Log the current secure view configuration for debugging."""
    secure_view_map = get_secure_view_map()
    logger.info(f"Secure view mappings ({len(secure_view_map)} tables):")
    for base, secure in sorted(secure_view_map.items()):
        logger.info(f"  {base:20} → {secure}")
