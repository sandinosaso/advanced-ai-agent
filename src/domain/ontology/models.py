"""
Domain ontology data models

Represents how business concepts map to database schema.
"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class DomainResolution:
    """Represents how a domain term resolves to database schema"""
    term: str
    entity: str
    tables: List[str]
    filters: List[Dict[str, Any]]
    confidence: float
    resolution_strategy: str  # "primary", "secondary", "fallback"
