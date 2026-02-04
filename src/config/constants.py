"""
Application constants

Centralized constants used across the application.
"""

from typing import Set

# ============================================================================
# Secure View Mappings
# ============================================================================
# NOTE: Secure view mappings are now dynamically discovered from the database
# See src.utils.sql.secure_views for the implementation
# Use get_secure_view_map() and get_secure_views() instead of these constants


# ============================================================================
# SQL Constants
# ============================================================================

# Audit columns to exclude from join planning
# These columns are for tracking metadata, not for establishing semantic relationships
AUDIT_COLUMNS: Set[str] = {'createdBy', 'updatedBy', 'createdAt', 'updatedAt'}
