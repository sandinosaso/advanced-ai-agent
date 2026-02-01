"""
Domain Ontology Module

Maps business concepts (like "crane", "action item") to database schema locations.
This enables natural language queries to be resolved to proper SQL constructs.

Example:
    "crane" → assetType.name ILIKE '%crane%'
    "action item" → inspectionQuestionAnswer.isActionItem = true
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.utils.logging import logger
from src.config.settings import settings
from src.domain.ontology.models import DomainResolution
from src.domain.ontology.extractor import DomainTermExtractor
from src.domain.ontology.resolver import DomainTermResolver


class DomainOntology:
    """
    Domain vocabulary registry that maps business concepts to schema.
    
    Responsibilities:
    - Load domain vocabulary from JSON registry
    - Extract domain terms from natural language questions
    - Resolve domain terms to schema locations (tables, columns, filters)
    - Log unresolved terms for continuous improvement
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize domain ontology.
        
        Args:
            registry_path: Path to domain_registry.json (defaults to artifacts/domain_registry.json)
        """
        if registry_path is None:
            registry_path = settings.domain_registry_path
        
        self.registry_path = Path(registry_path)
        self.registry: Dict[str, Any] = {}
        
        # Load registry if it exists
        if self.registry_path.exists():
            self.load_registry()
            logger.info(f"Loaded domain registry with {len(self.registry.get('terms', {}))} terms")
        else:
            logger.warning(f"Domain registry not found at {self.registry_path}")
        
        # Initialize extractor and resolver
        self.extractor = DomainTermExtractor(self.registry)
        self.resolver = DomainTermResolver(self.registry)
    
    def load_registry(self) -> None:
        """Load domain vocabulary registry from JSON file"""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load domain registry: {e}")
            self.registry = {"version": 1, "terms": {}}
    
    def extract_domain_terms(self, question: str) -> List[str]:
        """
        Extract domain-specific business terms from natural language question.
        Two-phase: Pass 1 atomic signals (LLM), Pass 2 compound eligibility (deterministic).
        Returns only registry term keys that pass both phases.
        
        Args:
            question: Natural language question
            
        Returns:
            List of registry term keys found in the question
            
        Example:
            "Find crane inspections" (no "question"/"answer"/"form") → ["crane"]
            "Show questions for that inspection" → ["inspection_questions"] when atomic signals include inspection and question
        """
        return self.extractor.extract_domain_terms(question)
    
    def resolve_domain_term(self, term: str) -> Optional[DomainResolution]:
        """
        Resolve a domain term to schema locations.
        
        Maps business concept to:
        - Tables that need to be included
        - Filter conditions to apply
        - Confidence score
        
        Args:
            term: Domain term to resolve (e.g., "crane", "action_item")
            
        Returns:
            DomainResolution object or None if term not found
            
        Example:
            resolve_domain_term("crane") →
            DomainResolution(
                term="crane",
                entity="asset",
                tables=["asset", "assetType"],
                filters=[{"table": "assetType", "column": "name", "operator": "ILIKE", "value": "%crane%"}],
                confidence=0.9,
                resolution_strategy="primary"
            )
        """
        return self.resolver.resolve_domain_term(term)
    
    def get_all_domain_terms(self) -> List[str]:
        """Get list of all known domain terms"""
        return list(self.registry.get("terms", {}).keys())


# Re-export for backward compatibility
__all__ = [
    "DomainOntology",
    "DomainResolution",
]
