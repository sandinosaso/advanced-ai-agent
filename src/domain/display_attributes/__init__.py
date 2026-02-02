"""
Display Attributes Module

Manages display attribute configuration for SQL query generation.
Defines which columns should be selected by default for each table and concept.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from src.utils.logging import logger
from src.domain.ontology.models import DisplayAttributes, ConceptDisplayRules


class DisplayAttributesManager:
    """
    Manages display attribute configuration and resolution.
    
    Responsibilities:
    - Load display attributes registry from JSON
    - Resolve display columns for tables and concepts
    - Build prompt context for SQL generation
    - Handle template relationships
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize display attributes manager.
        
        Args:
            registry_path: Path to display_attributes_registry.json
        """
        if registry_path is None:
            from src.config.settings import settings
            registry_path = settings.display_attributes_registry_path
        
        self.registry_path = Path(registry_path)
        self.registry: Dict[str, Any] = {}
        self.tables_config: Dict[str, DisplayAttributes] = {}
        self.concepts_config: Dict[str, ConceptDisplayRules] = {}
        
        # Load registry if it exists
        if self.registry_path.exists():
            self._load_registry()
        else:
            logger.warning(f"Display attributes registry not found at {self.registry_path}")
    
    def _load_registry(self) -> None:
        """Load display attributes registry from JSON file."""
        try:
            with open(self.registry_path, 'r') as f:
                self.registry = json.load(f)
            
            # Parse tables configuration
            tables_data = self.registry.get("tables", {})
            for table_name, config in tables_data.items():
                self.tables_config[table_name] = DisplayAttributes(
                    table=table_name,
                    display_columns=config.get("display_columns", ["id"]),
                    primary_label=config.get("primary_label", []),
                    template_relationship=config.get("template_relationship"),
                    description=config.get("description")
                )
            
            # Parse concepts configuration
            concepts_data = self.registry.get("concepts", {})
            for concept_name, config in concepts_data.items():
                self.concepts_config[concept_name] = ConceptDisplayRules(
                    concept=concept_name,
                    tables=config.get("tables", []),
                    display_override=config.get("display_override", {}),
                    required_joins=config.get("required_joins", []),
                    description=config.get("description")
                )
            
            logger.info(
                f"Loaded display attributes registry: {len(self.tables_config)} tables, "
                f"{len(self.concepts_config)} concepts"
            )
        except Exception as e:
            logger.error(f"Failed to load display attributes registry: {e}")
            self.registry = {}
    
    def get_display_columns(
        self, 
        table: str, 
        concept: Optional[str] = None,
        include_id: bool = True
    ) -> List[str]:
        """
        Get display columns for a table, optionally filtered by concept.
        
        Args:
            table: Table name
            concept: Optional concept name for context-specific overrides
            include_id: Whether to always include 'id' column
        
        Returns:
            List of column names to display
        """
        # Check for concept-specific override first
        if concept and concept in self.concepts_config:
            concept_config = self.concepts_config[concept]
            if table in concept_config.display_override:
                columns = concept_config.display_override[table].copy()
                if include_id and "id" not in columns:
                    columns.insert(0, "id")
                return columns
        
        # Fall back to table default configuration
        if table in self.tables_config:
            columns = self.tables_config[table].display_columns.copy()
            if include_id and "id" not in columns:
                columns.insert(0, "id")
            return columns
        
        # No configuration found, return just id
        return ["id"] if include_id else []
    
    def get_primary_label(self, table: str) -> List[str]:
        """
        Get primary label columns for a table (human-readable identifiers).
        
        Args:
            table: Table name
        
        Returns:
            List of primary label column names
        """
        if table in self.tables_config:
            return self.tables_config[table].primary_label.copy()
        return []
    
    def get_template_relationship(self, table: str) -> Optional[Dict[str, Any]]:
        """
        Get template relationship configuration for a table.
        
        Args:
            table: Table name
        
        Returns:
            Template relationship config or None
        """
        if table in self.tables_config:
            return self.tables_config[table].template_relationship
        return None
    
    def get_tables_with_template_relationships(self, tables: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get all template relationships for a list of tables.
        
        Args:
            tables: List of table names
        
        Returns:
            Dict mapping table names to their template relationship configs
        """
        result = {}
        for table in tables:
            template_rel = self.get_template_relationship(table)
            if template_rel:
                result[table] = template_rel
        return result
    
    def resolve_concept_display(
        self, 
        concept: str, 
        tables: List[str]
    ) -> Dict[str, List[str]]:
        """
        Resolve display columns for a concept across multiple tables.
        
        Args:
            concept: Concept name
            tables: List of table names involved in the query
        
        Returns:
            Dict mapping table names to their display columns
        """
        result = {}
        
        if concept in self.concepts_config:
            concept_config = self.concepts_config[concept]
            
            # Use concept-specific overrides
            for table in tables:
                if table in concept_config.display_override:
                    result[table] = concept_config.display_override[table].copy()
                else:
                    # Fall back to table default
                    result[table] = self.get_display_columns(table, concept=None)
        else:
            # No concept config, use table defaults
            for table in tables:
                result[table] = self.get_display_columns(table, concept=None)
        
        return result
    
    def get_concept_required_tables(self, concept: str) -> List[str]:
        """
        Get tables required for a concept (including template tables).
        
        Args:
            concept: Concept name
        
        Returns:
            List of required table names
        """
        if concept in self.concepts_config:
            return self.concepts_config[concept].tables.copy()
        return []
    
    def get_concept_required_joins(self, concept: str) -> List[str]:
        """
        Get required join conditions for a concept.
        
        Args:
            concept: Concept name
        
        Returns:
            List of join condition strings
        """
        if concept in self.concepts_config:
            return self.concepts_config[concept].required_joins.copy()
        return []
    
    def build_display_context(
        self, 
        tables: List[str], 
        concept: Optional[str] = None,
        max_examples: int = 5
    ) -> str:
        """
        Build prompt context for display column selection.
        
        Args:
            tables: List of table names in the query
            concept: Optional concept name for context
            max_examples: Maximum number of examples to include
        
        Returns:
            Formatted string for prompt injection
        """
        if not tables:
            return ""
        
        lines = []
        lines.append("DISPLAY COLUMN GUIDELINES:")
        lines.append("=" * 70)
        
        # Add concept-specific guidance if applicable
        if concept and concept in self.concepts_config:
            concept_config = self.concepts_config[concept]
            if concept_config.description:
                lines.append(f"\nConcept: {concept}")
                lines.append(f"  {concept_config.description}")
            
            # Show required joins for concept
            if concept_config.required_joins:
                lines.append(f"\n  Required joins:")
                for join in concept_config.required_joins:
                    lines.append(f"    - {join}")
        
        # Add table-specific display columns
        lines.append("\nRecommended display columns by table:")
        
        example_count = 0
        for table in sorted(tables):
            if example_count >= max_examples:
                lines.append(f"  ... and {len(tables) - example_count} more tables")
                break
            
            display_cols = self.get_display_columns(table, concept=concept)
            primary_label = self.get_primary_label(table)
            
            if display_cols:
                lines.append(f"\n  {table}:")
                lines.append(f"    Display: {', '.join(display_cols)}")
                if primary_label:
                    lines.append(f"    Primary label: {', '.join(primary_label)}")
                
                # Add template relationship info
                template_rel = self.get_template_relationship(table)
                if template_rel:
                    template_table = template_rel.get("template_table")
                    template_cols = template_rel.get("template_columns", [])
                    lines.append(
                        f"    Template: Include {template_table}.{', '.join(template_cols)} "
                        f"for human-readable name"
                    )
                
                example_count += 1
        
        lines.append("\n" + "=" * 70)
        lines.append(
            "IMPORTANT: Always prefer human-readable columns (name, firstName/lastName, "
            "description) over IDs when displaying results to users."
        )
        
        return "\n".join(lines)
    
    def get_all_required_tables_for_display(
        self, 
        base_tables: List[str],
        concept: Optional[str] = None
    ) -> Set[str]:
        """
        Get all tables needed for display, including template tables.
        
        Args:
            base_tables: Base tables selected for the query
            concept: Optional concept name
        
        Returns:
            Set of all table names needed (including template tables)
        """
        all_tables = set(base_tables)
        
        # Add concept-required tables
        if concept:
            concept_tables = self.get_concept_required_tables(concept)
            all_tables.update(concept_tables)
        
        # Add template tables for tables with template relationships
        for table in base_tables:
            template_rel = self.get_template_relationship(table)
            if template_rel:
                # Add template table
                template_table = template_rel.get("template_table")
                if template_table:
                    all_tables.add(template_table)
                
                # Add via tables (bridge tables)
                via_tables = template_rel.get("via_tables", [])
                all_tables.update(via_tables)
        
        return all_tables
    
    def has_configuration(self, table: str) -> bool:
        """
        Check if a table has display configuration.
        
        Args:
            table: Table name
        
        Returns:
            True if configuration exists
        """
        return table in self.tables_config
    
    def get_concept_names(self) -> List[str]:
        """Get all configured concept names."""
        return list(self.concepts_config.keys())
    
    def get_table_names(self) -> List[str]:
        """Get all configured table names."""
        return list(self.tables_config.keys())
