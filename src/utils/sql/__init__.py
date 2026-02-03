"""
SQL-related utilities for secure views and database operations.
"""

from .secure_views import (
    SECURE_VIEW_MAP,
    SECURE_VIEWS,
    is_secure_table,
    to_secure_view,
    from_secure_view,
    rewrite_secure_tables,
    extract_tables_from_sql,
    validate_tables_exist,
    get_secure_view_for_entity,
    log_secure_view_config,
)

# Backward compatibility - re-export everything that was in src.sql
__all__ = [
    "SECURE_VIEW_MAP",
    "SECURE_VIEWS",
    "is_secure_table",
    "to_secure_view",
    "from_secure_view",
    "rewrite_secure_tables",
    "extract_tables_from_sql",
    "validate_tables_exist",
    "get_secure_view_for_entity",
    "log_secure_view_config",
]

__all__ = [
    "SECURE_VIEW_MAP",
    "SECURE_VIEWS",
    "is_secure_table",
    "to_secure_view",
    "from_secure_view",
    "rewrite_secure_tables",
    "extract_tables_from_sql",
    "validate_tables_exist",
    "get_secure_view_for_entity",
    "log_secure_view_config",
]
