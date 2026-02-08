"""
Test domain registry patterns (payroll, crew lead, dynamic attributes, default table filters)

Tests that the agent respects these patterns when resolving terms and generating SQL.
"""

import unittest
from typing import Dict, Any, List
from src.domain.ontology import DomainOntology
from src.domain.ontology.formatter import (
    format_domain_context,
    format_domain_context_for_table_selection,
    build_where_clauses
)


def get_default_table_filter_clauses(selected_tables: List[str], registry: Dict[str, Any]) -> List[str]:
    """
    Build WHERE clause fragments from default table filters.
    
    Args:
        selected_tables: List of selected table names
        registry: Domain registry dictionary
        
    Returns:
        List of WHERE clause strings for tables with default filters
    """
    if not registry:
        return []
    
    default_filters = registry.get("default_table_filters", {})
    if not default_filters:
        return []
    
    clauses = []
    for table in selected_tables:
        if table in default_filters:
            filters = default_filters[table]
            for filter_def in filters:
                column = filter_def.get("column")
                value = filter_def.get("value")
                if column and value is not None:
                    # Format value based on type
                    if isinstance(value, bool):
                        value_str = "true" if value else "false"
                    elif isinstance(value, str):
                        value_str = f"'{value}'"
                    else:
                        value_str = str(value)
                    
                    clause = f"{table}.{column} = {value_str}"
                    clauses.append(clause)
    
    return clauses


class TestDomainRegistryPatterns(unittest.TestCase):
    """Test domain registry patterns"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.ontology = DomainOntology()
        self.registry = self.ontology.registry
    
    def test_registry_has_three_new_terms(self):
        """Test that registry includes the three new terms"""
        terms = self.registry.get("terms", {})
        
        # Check that the three new terms exist
        self.assertIn("payroll_rules", terms)
        self.assertIn("crew_lead", terms)
        self.assertIn("common_dynamic_attributes", terms)
    
    def test_registry_has_default_table_filters(self):
        """Test that registry has default_table_filters at top level"""
        self.assertIn("default_table_filters", self.registry)
        
        default_filters = self.registry["default_table_filters"]
        
        # Check expected tables
        self.assertIn("workOrder", default_filters)
        self.assertIn("employee", default_filters)
        self.assertIn("customer", default_filters)
        self.assertIn("inspection", default_filters)
        
        # Check workOrder has isInternal filter
        wo_filters = default_filters["workOrder"]
        self.assertTrue(any(f.get("column") == "isInternal" and f.get("value") == 0 for f in wo_filters))
        
        # Check customer has both isInternal and isActive filters
        customer_filters = default_filters["customer"]
        self.assertTrue(any(f.get("column") == "isInternal" and f.get("value") == 0 for f in customer_filters))
        self.assertTrue(any(f.get("column") == "isActive" and f.get("value") == 1 for f in customer_filters))
    
    def test_payroll_rules_resolution(self):
        """Test that payroll_rules resolves correctly with detailed calculation hints"""
        resolution = self.ontology.resolve_domain_term("payroll_rules")
        
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.term, "payroll_rules")
        self.assertEqual(resolution.entity, "payroll_calculation")
        
        # Check tables
        self.assertIn("workTime", resolution.tables)
        self.assertIn("crewWorkDay", resolution.tables)
        
        # Check hints contain logic_hint with detailed formulas
        self.assertIsNotNone(resolution.hints)
        self.assertIn("logic_hint", resolution.hints)
        logic_hint = resolution.hints["logic_hint"]
        
        # Verify key components of payroll calculation logic
        self.assertIn("DAYOFWEEK", logic_hint)
        self.assertIn("LEAST", logic_hint, "Should contain LEAST for regular time cap")
        self.assertIn("GREATEST", logic_hint, "Should contain GREATEST for overtime calculation")
        self.assertIn("8", logic_hint, "Should contain the 8-hour threshold")
        self.assertIn("Group by employee and DATE", logic_hint, "Should specify grouping requirement")
        self.assertIn("DO NOT use workTimeType", logic_hint, "Should explicitly warn against using workTimeType")
        
        # Verify all three formula types are present
        self.assertIn("Regular Time", logic_hint)
        self.assertIn("OverTime", logic_hint)
        self.assertIn("Double Time", logic_hint)
        
        # Verify Sunday logic (DAYOFWEEK=1)
        self.assertIn("DAYOFWEEK(date)=1", logic_hint, "Should specify Sunday as DAYOFWEEK=1")
        
        # Verify extra (term-specific attributes) is in resolution.extra, not primary
        self.assertIsNotNone(resolution.extra, "Should have extra dict for term-specific attributes")
        self.assertEqual(resolution.extra.get("regular_hours_threshold"), 8)
        self.assertIn("V1_RULES.md", resolution.extra.get("rule_source", ""))
    
    def test_payroll_extra_extraction_via_helper(self):
        """Test that get_resolution_extra extracts regular_hours_threshold from extra"""
        from src.domain.ontology.formatter import get_resolution_extra
        
        resolution = self.ontology.resolve_domain_term("payroll_rules")
        res_dict = {
            "term": resolution.term,
            "extra": resolution.extra,
        }
        
        threshold = get_resolution_extra(res_dict, "regular_hours_threshold")
        self.assertEqual(threshold, 8)
        
        rule_source = get_resolution_extra(res_dict, "rule_source")
        self.assertIn("V1_RULES.md", rule_source or "")
    
    def test_payroll_alias_extraction(self):
        """Test that 'payroll' alias is extracted from questions"""
        # The extractor should recognize "payroll" from the alias
        terms = self.ontology.extract_domain_terms("I want a Payroll report for employees")
        
        # Should extract payroll_rules via the "payroll" alias
        self.assertIn("payroll_rules", terms, "Should extract payroll_rules when question mentions 'Payroll'")
    
    def test_payroll_exclude_bridge_patterns(self):
        """Test that payroll_rules has exclude_bridge_patterns to prevent unwanted joins"""
        from src.agents.sql.planning import get_exclude_bridge_patterns
        
        resolution = self.ontology.resolve_domain_term("payroll_rules")
        
        # Build domain resolutions list as expected by get_exclude_bridge_patterns
        domain_resolutions = [{
            "term": "payroll_rules",
            "entity": resolution.entity,
            "tables": resolution.tables,
            "confidence": resolution.confidence
        }]
        
        patterns = get_exclude_bridge_patterns(domain_resolutions, self.ontology)
        
        # Should exclude satellite tables that cause 0 rows
        self.assertIn("expense", patterns, "Should exclude expense table")
        self.assertIn("attachment", patterns, "Should exclude attachment table")
        self.assertIn("workTimeType", patterns, "Should exclude workTimeType (we calculate, not read)")
        self.assertIn("payrollEntry", patterns, "Should exclude payrollEntry (output table)")
        self.assertIn("payrollBatch", patterns, "Should exclude payrollBatch (output table)")
    
    def test_crew_lead_resolution(self):
        """Test that crew_lead resolves correctly with boolean filter"""
        resolution = self.ontology.resolve_domain_term("crew_lead")
        
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.term, "crew_lead")
        self.assertEqual(resolution.entity, "crew_leadership")
        
        # Check tables
        self.assertIn("employeeCrew", resolution.tables)
        self.assertIn("crew", resolution.tables)
        self.assertIn("workOrder", resolution.tables)
        self.assertIn("employee", resolution.tables)
        
        # Check filters include isLead = 1
        self.assertEqual(len(resolution.filters), 1)
        filter_def = resolution.filters[0]
        self.assertEqual(filter_def["table"], "employeeCrew")
        self.assertEqual(filter_def["column"], "isLead")
        self.assertEqual(filter_def["value"], 1)
        self.assertEqual(filter_def["match_type"], "boolean")
    
    def test_common_dynamic_attributes_resolution(self):
        """Test that common_dynamic_attributes resolves correctly with hints"""
        resolution = self.ontology.resolve_domain_term("common_dynamic_attributes")
        
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.term, "common_dynamic_attributes")
        self.assertEqual(resolution.entity, "dynamic_attributes")
        
        # Check hints contain dynamic_attribute_keys and extraction_pattern
        self.assertIsNotNone(resolution.hints)
        self.assertIn("dynamic_attribute_keys", resolution.hints)
        self.assertIn("extraction_pattern", resolution.hints)
        
        # Check entity keys
        keys = resolution.hints["dynamic_attribute_keys"]
        self.assertIn("workOrder", keys)
        self.assertIn("asset", keys)
        
        # Check extraction pattern
        pattern = resolution.hints["extraction_pattern"]
        self.assertIn("JSON_UNQUOTE", pattern)
        self.assertIn("JSON_EXTRACT", pattern)
    
    def test_default_table_filter_clauses(self):
        """Test that get_default_table_filter_clauses returns correct clauses"""
        selected_tables = ["workOrder", "employee", "customer"]
        
        clauses = get_default_table_filter_clauses(selected_tables, self.registry)
        
        # Should have clauses for all selected tables
        self.assertGreater(len(clauses), 0)
        
        # Check workOrder.isInternal = 0
        self.assertTrue(any("workOrder.isInternal = 0" in clause for clause in clauses))
        
        # Check employee.isInternal = 0
        self.assertTrue(any("employee.isInternal = 0" in clause for clause in clauses))
        
        # Check customer has both filters
        self.assertTrue(any("customer.isInternal = 0" in clause for clause in clauses))
        self.assertTrue(any("customer.isActive = 1" in clause for clause in clauses))
    
    def test_default_table_filter_clauses_empty_for_non_configured_tables(self):
        """Test that tables without default filters don't generate clauses"""
        selected_tables = ["asset", "location"]  # Tables not in default_table_filters
        
        clauses = get_default_table_filter_clauses(selected_tables, self.registry)
        
        # Should be empty since these tables don't have default filters
        self.assertEqual(len(clauses), 0)
    
    def test_formatter_includes_payroll_hints(self):
        """Test that formatter includes payroll logic hints"""
        resolution = self.ontology.resolve_domain_term("payroll_rules")
        
        # Convert to dict format as expected by formatter
        res_dict = {
            "term": resolution.term,
            "entity": resolution.entity,
            "tables": resolution.tables,
            "filters": resolution.filters,
            "confidence": resolution.confidence,
            "strategy": resolution.resolution_strategy,
            "hints": resolution.hints
        }
        
        formatted = format_domain_context([res_dict])
        
        # Check that logic hint is in the formatted output
        self.assertIn("Calculation hint:", formatted)
        self.assertIn("DAYOFWEEK", formatted)
    
    def test_formatter_includes_dynamic_attribute_hints(self):
        """Test that formatter includes dynamic attribute hints"""
        resolution = self.ontology.resolve_domain_term("common_dynamic_attributes")
        
        # Convert to dict format
        res_dict = {
            "term": resolution.term,
            "entity": resolution.entity,
            "tables": resolution.tables,
            "filters": resolution.filters,
            "confidence": resolution.confidence,
            "strategy": resolution.resolution_strategy,
            "hints": resolution.hints
        }
        
        formatted = format_domain_context([res_dict])
        
        # Check that dynamic attribute keys and extraction pattern are in output
        self.assertIn("Dynamic attribute keys:", formatted)
        self.assertIn("workOrder:", formatted)
        self.assertIn("asset:", formatted)
        self.assertIn("Extraction pattern:", formatted)
        self.assertIn("JSON_UNQUOTE", formatted)
    
    def test_build_where_clauses_for_crew_lead(self):
        """Test that build_where_clauses produces correct WHERE fragment for crew_lead"""
        resolution = self.ontology.resolve_domain_term("crew_lead")
        
        # Convert to dict format
        res_dict = {
            "term": resolution.term,
            "entity": resolution.entity,
            "tables": resolution.tables,
            "filters": resolution.filters,
            "confidence": resolution.confidence,
            "strategy": resolution.resolution_strategy
        }
        
        clauses = build_where_clauses([res_dict])
        
        # Should have one clause for isLead
        self.assertEqual(len(clauses), 1)
        self.assertIn("employeeCrew.isLead", clauses[0])
        self.assertIn("= 1", clauses[0])
    
    def test_aliases_in_registry(self):
        """Test that new terms have aliases defined"""
        terms = self.registry.get("terms", {})
        
        # Check payroll_rules has "payroll" alias
        payroll = terms.get("payroll_rules", {})
        self.assertIn("aliases", payroll)
        self.assertIn("payroll", payroll["aliases"])
        
        # Check crew_lead has aliases
        crew_lead = terms.get("crew_lead", {})
        self.assertIn("aliases", crew_lead)
        self.assertTrue(any(a in ["lead", "crew lead"] for a in crew_lead["aliases"]))
        
        # Check common_dynamic_attributes has aliases
        dyn_attrs = terms.get("common_dynamic_attributes", {})
        self.assertIn("aliases", dyn_attrs)
        self.assertTrue(any(a in ["dynamic attribute", "custom attribute"] for a in dyn_attrs["aliases"]))


if __name__ == '__main__':
    unittest.main()
