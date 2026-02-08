"""
Domain ontology data models

Represents how business concepts map to database schema.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class DomainResolution:
    """Represents how a domain term resolves to database schema"""
    term: str
    entity: str
    tables: List[str]
    filters: List[Dict[str, Any]]
    confidence: float
    resolution_strategy: str  # "primary", "secondary", "fallback"
    hints: Optional[Dict[str, Any]] = None  # Optional hints for payroll logic, dynamic attributes, etc.
    extra: Optional[Dict[str, Any]] = None  # Term-specific attributes (e.g. regular_hours_threshold, rule_source)


@dataclass
class DisplayAttributes:
    """Display attributes configuration for a table"""
    table: str
    display_columns: List[str]
    primary_label: List[str]
    template_relationship: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


@dataclass
class ConceptDisplayRules:
    """Display rules for a business concept"""
    concept: str
    tables: List[str]
    display_override: Dict[str, List[str]]
    required_joins: List[str] = field(default_factory=list)
    description: Optional[str] = None
