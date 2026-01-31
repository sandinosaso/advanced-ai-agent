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
from dataclasses import dataclass

from src.utils.logger import logger
from src.utils.config import create_llm, settings


@dataclass
class DomainResolution:
    """Represents how a domain term resolves to database schema"""
    term: str
    entity: str
    tables: List[str]
    filters: List[Dict[str, Any]]
    confidence: float
    resolution_strategy: str  # "primary", "secondary", "fallback"


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
        self.llm = None  # Lazy initialization for term extraction
        
        # Load registry if it exists
        if self.registry_path.exists():
            self.load_registry()
            logger.info(f"Loaded domain registry with {len(self.registry.get('terms', {}))} terms")
        else:
            logger.warning(f"Domain registry not found at {self.registry_path}")
    
    def load_registry(self) -> None:
        """Load domain vocabulary registry from JSON file"""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load domain registry: {e}")
            self.registry = {"version": 1, "terms": {}}
    
    def _get_llm(self):
        """Lazy initialization of LLM for term extraction"""
        if self.llm is None:
            self.llm = create_llm(temperature=0, max_completion_tokens=settings.max_output_tokens)
        return self.llm

    @staticmethod
    def _term_to_phrase(term: str) -> str:
        """Convert registry term key to a short phrase for examples (e.g. action_item -> 'action items')."""
        return term.replace("_", " ").strip()

    def _get_extraction_task_instructions(self) -> str:
        """
        Build task instructions for domain term extraction from the registry only.
        No hardcoded term names. Compound terms (containing '_') get a strict rule.
        """
        terms = self.registry.get("terms", {})
        known_terms = list(terms.keys())
        if not known_terms:
            return "Return ONLY a JSON array of term keys from the known terms list. Match case-insensitively."

        lines = [
            "Identify which known business terms are explicitly or clearly implied by the question.",
            "Return ONLY a JSON array of term keys from the known terms list.",
            "Match terms case-insensitively.",
        ]
        compound_terms = [t for t in known_terms if "_" in t]
        if compound_terms:
            parts_rule = (
                "Terms containing '_' are compound concepts (e.g. "
                + ", ".join(f'"{t}"' for t in compound_terms[:3])
                + ("..." if len(compound_terms) > 3 else "")
                + "). Only extract a compound term when the question reflects BOTH parts of the concept "
                "(e.g. for 'X_y' both X and y must be present or clearly implied). "
                "If only one part is mentioned, do not include that compound term."
            )
            lines.append(parts_rule)
        if terms:
            desc_lines = []
            for term in list(terms.keys())[:8]:
                desc = terms[term].get("description", "")
                if desc:
                    desc_lines.append(f'  * "{term}": {desc}')
            if desc_lines:
                lines.append("Term meanings (from registry):")
                lines.extend(desc_lines)
        return "\n".join([f"- {line}" if not line.startswith("  ") else line for line in lines])

    def _get_extraction_examples(self) -> str:
        """
        Build extraction examples from the registry only.
        Uses first terms; for compound terms, includes an example where only one part is present.
        """
        terms = self.registry.get("terms", {})
        known_terms = list(terms.keys())
        if not known_terms:
            return ""

        examples = []
        simple_terms = [t for t in known_terms if "_" not in t][:3]
        for term in simple_terms:
            phrase = self._term_to_phrase(term)
            examples.append(f'- "Find {phrase}" → ["{term}"]')
        if len(known_terms) >= 2 and simple_terms:
            other = next((t for t in known_terms if t != simple_terms[0]), simple_terms[0])
            phrase0 = self._term_to_phrase(simple_terms[0])
            phrase1 = self._term_to_phrase(other)
            examples.append(f'- "Show {phrase0} with {phrase1}" → ["{simple_terms[0]}", "{other}"]')
        compound_terms = [t for t in known_terms if "_" in t]
        for term in compound_terms[:2]:
            phrase = self._term_to_phrase(term)
            parts = term.split("_")
            first_part = parts[0] if parts else ""
            examples.append(f'- "Find {phrase}" (both concepts present) → ["{term}"]')
            examples.append(f'- "Find {first_part} only" (one concept; no "{term}") → [] or other terms only')
        return "\n".join(examples)

    def extract_domain_terms(self, question: str) -> List[str]:
        """
        Extract domain-specific business terms from natural language question.
        
        Uses LLM to identify business concepts that might need special schema resolution.
        
        Args:
            question: Natural language question
            
        Returns:
            List of domain terms found in the question
            
        Example:
            "Find work orders with crane inspections that have action items"
            → ["crane", "action_item"]
        """
        if not settings.domain_extraction_enabled:
            logger.debug("Domain extraction disabled")
            return []
        
        # Get list of known terms from registry
        known_terms = list(self.registry.get("terms", {}).keys())
        
        if not known_terms:
            logger.debug("No terms in domain registry, skipping extraction")
            return []

        task_instructions = self._get_extraction_task_instructions()
        examples = self._get_extraction_examples()
        
        prompt = f"""Extract domain-specific business terms from this question.

Known business terms (from domain vocabulary):
{', '.join(known_terms)}

Question: {question}

Task:
{task_instructions}

Examples (generated from registry):
{examples}

CRITICAL: Return ONLY the raw JSON array with no markdown formatting.
Do NOT wrap in ```json``` code blocks.
Just return: ["term1", "term2"]"""

        try:
            llm = self._get_llm()
            response = llm.invoke(prompt)
            raw = str(response.content).strip() if hasattr(response, 'content') and response.content else "[]"
            
            # Clean up markdown code blocks if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                # Remove first line (```json or ```) and last line (```)
                if len(lines) > 2:
                    raw = "\n".join(lines[1:-1]).strip()
                else:
                    raw = "[]"
            
            # Parse JSON response
            if raw.startswith('['):
                terms = json.loads(raw)
                # Validate that all terms exist in registry
                valid_terms = [t for t in terms if t in self.registry.get("terms", {})]
                logger.info(f"Extracted domain terms: {valid_terms}")
                return valid_terms
            else:
                logger.warning(f"Invalid JSON response from LLM: {raw}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to extract domain terms: {e}")
            return []
    
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
            return self._build_resolution(term, entity, resolution["primary"], "primary")
        
        # Try secondary
        if "secondary" in resolution:
            return self._build_resolution(term, entity, resolution["secondary"], "secondary")
        
        # Try fallback
        if "fallback" in resolution:
            return self._build_resolution(term, entity, resolution["fallback"], "fallback")
        
        logger.warning(f"No resolution strategies found for term '{term}'")
        return None
    
    def _build_resolution(
        self,
        term: str,
        entity: str,
        strategy_config: Dict[str, Any],
        strategy_name: str
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
        
        resolution = DomainResolution(
            term=term,
            entity=entity,
            tables=tables,
            filters=filters,
            confidence=confidence,
            resolution_strategy=strategy_name
        )
        
        logger.debug(f"Resolved '{term}' using {strategy_name} strategy: {len(tables)} tables, {len(filters)} filters")
        
        return resolution
    
    def get_all_domain_terms(self) -> List[str]:
        """Get list of all known domain terms"""
        return list(self.registry.get("terms", {}).keys())
    
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


def format_domain_context_for_table_selection(resolutions: List[Dict[str, Any]]) -> str:
    """
    Format domain resolutions for table selection prompt (tables only, no filters).
    
    This lightweight version only shows required tables to avoid token bloat.
    Filters are injected later in SQL generation where they're actually used.
    
    Args:
        resolutions: List of resolved domain terms (as dicts)
        
    Returns:
        Formatted string for table selection prompt
    """
    if not resolutions:
        return ""
    
    lines = ["Domain Context (business concepts mapped to schema):"]
    lines.append("=" * 70)
    
    for res in resolutions:
        lines.append(f"\nConcept: '{res['term']}' ({res['entity']})")
        lines.append(f"  Tables needed: {', '.join(res['tables'])}")
        lines.append(f"  Confidence: {res['confidence']} (strategy: {res['strategy']})")
    
    lines.append("=" * 70)
    return "\n".join(lines)


def format_domain_context(resolutions: List[Dict[str, Any]]) -> str:
    """
    Format domain resolutions into human-readable context for prompts.
    
    Used to inject domain understanding into join planning and SQL generation prompts.
    Includes both tables and filters.
    
    Args:
        resolutions: List of resolved domain terms (as dicts)
        
    Returns:
        Formatted string for prompt injection
    """
    if not resolutions:
        return ""
    
    lines = ["Domain Context (business concepts mapped to schema):"]
    lines.append("=" * 70)
    
    for res in resolutions:
        lines.append(f"\nConcept: '{res['term']}' ({res['entity']})")
        lines.append(f"  Tables needed: {', '.join(res['tables'])}")
        
        # Only show filters if they exist (structural matches have no filters)
        if res['filters']:
            lines.append(f"  Filters to apply:")
            for f in res['filters']:
                # Show LOWER() wrapper if case-insensitive
                if f.get("case_insensitive"):
                    column_ref = f"LOWER({f['table']}.{f['column']})"
                else:
                    column_ref = f"{f['table']}.{f['column']}"
                
                if f.get("match_type") == "boolean":
                    lines.append(f"    - {column_ref} {f['operator']} {f['value']}")
                else:
                    lines.append(f"    - {column_ref} {f['operator']} '{f['value']}'")
        else:
            lines.append(f"  Note: Structural grouping (no filters needed)")
        
        lines.append(f"  Confidence: {res['confidence']} (strategy: {res['strategy']})")
    
    lines.append("=" * 70)
    return "\n".join(lines)


def build_where_clauses(resolutions: List[Dict[str, Any]]) -> List[str]:
    """
    Build SQL WHERE clause fragments from domain resolutions.
    
    Args:
        resolutions: List of resolved domain terms (as dicts)
        
    Returns:
        List of WHERE clause strings to be AND'd together
        
    Example:
        [
            "assetType.name ILIKE '%crane%'",
            "inspectionQuestionAnswer.isActionItem = true"
        ]
    """
    where_clauses = []
    
    for res in resolutions:
        # Group OR conditions together
        or_conditions = []
        and_conditions = []
        
        for f in res['filters']:
            table = f['table']
            column = f['column']
            operator = f['operator']
            value = f['value']
            
            # Format value based on type
            if isinstance(value, bool):
                value_str = "true" if value else "false"
            elif isinstance(value, str):
                value_str = f"'{value}'"
            else:
                value_str = str(value)
            
            # Apply case-insensitive matching if specified
            if f.get("case_insensitive"):
                column_ref = f"LOWER({table}.{column})"
            else:
                column_ref = f"{table}.{column}"
            
            clause = f"{column_ref} {operator} {value_str}"
            
            if f.get("or_condition"):
                or_conditions.append(clause)
            else:
                and_conditions.append(clause)
        
        # Add OR conditions as a group
        if or_conditions:
            if len(or_conditions) == 1:
                where_clauses.append(or_conditions[0])
            else:
                where_clauses.append(f"({' OR '.join(or_conditions)})")
        
        # Add AND conditions individually
        where_clauses.extend(and_conditions)
    
    return where_clauses
