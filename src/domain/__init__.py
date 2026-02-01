"""
Domain layer - Business vocabulary and ontology
"""

from src.domain.ontology import DomainOntology, DomainResolution
from src.domain.ontology.formatter import (
    format_domain_context,
    format_domain_context_for_table_selection,
    build_where_clauses,
)

__all__ = [
    "DomainOntology",
    "DomainResolution",
    "format_domain_context",
    "format_domain_context_for_table_selection",
    "build_where_clauses",
]
