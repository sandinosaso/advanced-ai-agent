"""
Domain term resolution to database schema

Resolves business concepts to tables, columns, and filters.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from src.utils.logging import logger
from src.domain.ontology.models import DomainResolution


class DomainTermResolver:
    """
    Resolves domain terms to database schema locations.
    
    Maps business concepts to:
    - Tables that need to be included
    - Filter conditions to apply
    - Confidence scores
    """
    
    def __init__(self, registry: Dict[str, Any]):
        """
        Initialize resolver with domain registry.
        
        Args:
            registry: Domain registry dictionary
        """
        self.registry = registry
    
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
        terms = self.registry.get("terms", {})
        
        if term not in terms:
            logger.warning(f"Domain term '{term}' not found in registry")
            self._log_unresolved_term(term)
            return None
        
        term_config = terms[term]
        entity = term_config.get("entity", "unknown")
        resolution = term_config.get("resolution", {})
        
        # Try primary resolution first
        if "primary" in resolution:
            return self._build_resolution(term, entity, resolution["primary"], "primary", resolution.get("extra"))
        
        # Try secondary
        if "secondary" in resolution:
            return self._build_resolution(term, entity, resolution["secondary"], "secondary", resolution.get("extra"))
        
        # Try fallback
        if "fallback" in resolution:
            return self._build_resolution(term, entity, resolution["fallback"], "fallback", resolution.get("extra"))
        
        logger.warning(f"No resolution strategies found for term '{term}'")
        return None
    
    def _build_resolution(
        self,
        term: str,
        entity: str,
        strategy_config: Dict[str, Any],
        strategy_name: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> DomainResolution:
        """
        Build DomainResolution from strategy configuration.
        
        Args:
            term: Domain term
            entity: Entity type (e.g., "asset", "inspection_finding")
            strategy_config: Configuration for this resolution strategy
            strategy_name: Name of strategy ("primary", "secondary", "fallback")
            
        Returns:
            DomainResolution object
        """
        tables = []
        filters = []
        
        # Extract table(s)
        if "table" in strategy_config:
            tables.append(strategy_config["table"])
        if "tables" in strategy_config:
            tables.extend(strategy_config["tables"])
        
        # Build filter(s)
        match_type = strategy_config.get("match_type", "exact")
        
        if match_type == "structural":
            # Structural match - just table grouping, no filters needed
            # Used for related tables that should be included together
            # (e.g., inspectionQuestion + inspectionQuestionAnswer)
            pass  # No filters to add
        elif match_type == "boolean":
            # Boolean filter (e.g., isActionItem = true)
            filters.append({
                "table": strategy_config["table"],
                "column": strategy_config["column"],
                "operator": "=",
                "value": strategy_config.get("value", True),
                "match_type": "boolean"
            })
        elif match_type == "semantic" or match_type == "text_search":
            # Text search with case-insensitive LIKE using LOWER()
            # This ensures "Crane", "crane", "CRANE" all match
            column = strategy_config.get("column")
            if column:
                filters.append({
                    "table": strategy_config["table"],
                    "column": column,
                    "operator": "LIKE",
                    "value": f"%{term.lower()}%",
                    "match_type": match_type,
                    "case_insensitive": True  # Flag to wrap column in LOWER()
                })
            # Handle multiple columns for text search
            columns = strategy_config.get("columns", [])
            for col in columns:
                filters.append({
                    "table": strategy_config["table"],
                    "column": col,
                    "operator": "LIKE",
                    "value": f"%{term.lower()}%",
                    "match_type": match_type,
                    "or_condition": True,  # Multiple columns are OR'd together
                    "case_insensitive": True  # Flag to wrap column in LOWER()
                })
        elif match_type == "exact":
            # Exact match
            filters.append({
                "table": strategy_config["table"],
                "column": strategy_config["column"],
                "operator": "=",
                "value": strategy_config.get("value", term),
                "match_type": "exact"
            })
        
        confidence = strategy_config.get("confidence", 0.5)
        
        # Build hints dictionary for special patterns
        hints = {}
        
        # Handle logic_hint (for payroll rules, etc.)
        if "logic" in strategy_config:
            hints["logic_hint"] = strategy_config["logic"]
        elif "logic_hint" in strategy_config:
            hints["logic_hint"] = strategy_config["logic_hint"]
        
        # Handle extraction_pattern if present
        extraction_pattern = strategy_config.get("extraction_pattern")
        if extraction_pattern:
            hints["extraction_pattern"] = extraction_pattern
        
        # Handle display_hint if present
        display_hint = strategy_config.get("display_hint")
        if display_hint:
            hints["display_hint"] = display_hint

        # Merge strategy-level anchor_table into extra (for FROM clause selection)
        resolution_extra = dict(extra) if extra else {}
        if "anchor_table" in strategy_config:
            resolution_extra["anchor_table"] = strategy_config["anchor_table"]
        
        # Extract required joins if present
        required_joins = strategy_config.get("required_joins")

        resolution = DomainResolution(
            term=term,
            entity=entity,
            tables=tables,
            filters=filters,
            confidence=confidence,
            resolution_strategy=strategy_name,
            hints=hints if hints else None,
            extra=resolution_extra if resolution_extra else None,
            required_joins=required_joins if required_joins else None
        )
        
        logger.debug(f"Resolved '{term}' using {strategy_name} strategy: {len(tables)} tables, {len(filters)} filters, hints: {bool(hints)}, required_joins: {len(required_joins) if required_joins else 0}")
        
        return resolution
    
    def _log_unresolved_term(self, term: str) -> None:
        """
        Log unresolved domain term for manual review.
        
        This helps build the domain vocabulary over time by tracking
        terms that users mention but aren't in the registry.
        """
        logger.warning(f"Unresolved domain term: '{term}'")
        
        # TODO: Store in artifacts/unresolved_terms.jsonl for review
        # This would enable a continuous improvement loop where:
        # 1. Users ask questions with new domain terms
        # 2. Terms are logged
        # 3. Admins review logs weekly
        # 4. New terms are added to domain_registry.json
