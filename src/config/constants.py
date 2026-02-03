"""
Application constants

Centralized constants used across the application.
"""

from typing import Set

# ============================================================================
# Secure View Mappings
# ============================================================================

# Single Source of Truth: Tables that MUST use secure views
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
# SQL Constants
# ============================================================================

# Audit columns to exclude from join planning
# These columns are for tracking metadata, not for establishing semantic relationships
AUDIT_COLUMNS: Set[str] = {'createdBy', 'updatedBy', 'createdAt', 'updatedAt'}
