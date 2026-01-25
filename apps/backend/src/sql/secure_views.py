"""
Secure View Management - Single Source of Truth

This module defines which tables MUST be accessed via secure views.
This is the authoritative source - no other code should guess about secure_* variants.

Architecture:
- Physical tables: What exists in MySQL (user, employee, workOrder, etc.)
- Secure views: Explicit, curated views that decrypt data (secure_user, secure_employee, etc.)
- Logical entities: What the user means ("employee", "work order", etc.)

Only SOME logical entities map to secure views. All others map directly to base tables.
This mapping is explicit and defined here.
"""

import re
from typing import Set, Optional
from loguru import logger


# ============================================================================
# Single Source of Truth: Tables that MUST use secure views
# ============================================================================

SECURE_VIEW_MAP = {
    "user": "secure_user",
    "customerLocation": "secure_customerlocation",
    "customerContact": "secure_customercontact",
    "employee": "secure_employee",
    "workOrder": "secure_workorder",
    "customer": "secure_customer",
}

# Reverse mapping for validation
SECURE_VIEWS = set(SECURE_VIEW_MAP.values())


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
    # Check both exact match and lowercase match for flexibility
    return table in SECURE_VIEW_MAP or table.lower() in {k.lower() for k in SECURE_VIEW_MAP.keys()}


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
    # Try exact match first
    if table in SECURE_VIEW_MAP:
        return SECURE_VIEW_MAP[table]
    
    # Try case-insensitive match
    for base_table, secure_view in SECURE_VIEW_MAP.items():
        if table.lower() == base_table.lower():
            return secure_view
    
    # No match, return original
    return table


def rewrite_secure_tables(sql: str) -> str:
    """
    Replace base tables with secure views ONLY for allow-listed tables.
    
    Uses word boundary matching to avoid partial matches.
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
    """
    rewritten_sql = sql
    replacements_made = []
    
    for base_table, secure_view in SECURE_VIEW_MAP.items():
        # Use word boundaries to avoid partial matches
        # Case-insensitive replacement preserves the original case in non-matching parts
        pattern = rf"\b{re.escape(base_table)}\b"
        
        # Check if replacement would happen
        if re.search(pattern, rewritten_sql, flags=re.IGNORECASE):
            replacements_made.append(f"{base_table} → {secure_view}")
        
        # Replace with case-insensitive flag
        rewritten_sql = re.sub(
            pattern,
            secure_view,
            rewritten_sql,
            flags=re.IGNORECASE
        )
    
    # Log rewrites for observability
    if replacements_made:
        logger.debug(f"Rewrote secure tables: {', '.join(replacements_made)}")
    
    return rewritten_sql


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
    
    if normalized in SECURE_VIEW_MAP:
        return SECURE_VIEW_MAP[normalized]
    
    return None


# ============================================================================
# Validation on Import (Fail Fast)
# ============================================================================

def _validate_secure_view_map():
    """
    Validatevalues follow secure_* pattern.
    """
    for base, secure in SECURE_VIEW_MAP.items():
        # Ensure values follow secure_* pattern
        if not secure.startswith("secure_"):
            raise ValueError(
                f"SECURE_VIEW_MAP values must start with 'secure_': '{secure}'"
            )
        
        # Warn if mapping doesn't follow expected lowercase pattern in secure view
        expected_suffix = base.lower()
        actual_suffix = secure.replace("secure_", "")
        if actual_suffix != expected_suffix:
            logger.debug(
                f"SECURE_VIEW_MAP: '{base}' → '{secure}' (view suffix: {actual_suffix} vs expected: {expected_suffix})"
            )


# Run validation on import
_validate_secure_view_map()


# ============================================================================
# Logging/Debug Utilities
# ============================================================================

def log_secure_view_config():
    """Log the current secure view configuration for debugging."""
    logger.info(f"Secure view mappings ({len(SECURE_VIEW_MAP)} tables):")
    for base, secure in sorted(SECURE_VIEW_MAP.items()):
        logger.info(f"  {base:20} → {secure}")


if __name__ == "__main__":
    # Self-test
    print("Testing secure_views.py")
    print("=" * 60)
    
    # Test is_secure_table
    assert is_secure_table("employee") == True
    assert is_secure_table("EMPLOYEE") == True
    assert is_secure_table("inspections") == False
    print("✅ is_secure_table tests passed")
    
    # Test to_secure_view
    assert to_secure_view("employee") == "secure_employee"
    assert to_secure_view("EMPLOYEE") == "secure_employee"
    assert to_secure_view("inspections") == "inspections"
    print("✅ to_secure_view tests passed")
    
    # Test rewrite_secure_tables
    sql1 = "SELECT * FROM employee WHERE id = 1"
    assert "secure_employee" in rewrite_secure_tables(sql1)
    
    sql2 = "SELECT * FROM inspections WHERE id = 1"
    assert "secure_inspections" not in rewrite_secure_tables(sql2)
    assert "inspections" in rewrite_secure_tables(sql2)
    
    sql3 = "SELECT e.name FROM employee e JOIN workOrder wo ON e.id = wo.employeeId"
    rewritten = rewrite_secure_tables(sql3)
    assert "secure_employee" in rewritten
    assert "secure_workorder" in rewritten
    print("✅ rewrite_secure_tables tests passed")
    
    # Test extract_tables_from_sql
    tables = extract_tables_from_sql("SELECT * FROM employee JOIN worktime ON employee.id = worktime.employeeId")
    assert "employee" in tables
    assert "worktime" in tables
    print("✅ extract_tables_from_sql tests passed")
    
    # Test validate_tables_exist
    known = {"secure_employee", "inspections", "worktime"}
    try:
        validate_tables_exist("SELECT * FROM secure_employee", known)
        print("✅ validate_tables_exist passed for valid table")
    except ValueError:
        print("❌ validate_tables_exist failed for valid table")
    
    try:
        validate_tables_exist("SELECT * FROM secure_inspections", known)
        print("❌ validate_tables_exist should have raised ValueError")
    except ValueError:
        print("✅ validate_tables_exist correctly raised ValueError for invalid table")
    
    print("=" * 60)
    print("All tests passed! ✅")
    log_secure_view_config()
