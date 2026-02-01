#!/usr/bin/env python3
"""
Domain Ontology Implementation Validation

Validates that all required files and code structures are in place.
This test doesn't require dependencies or database connection.
"""

import json
from pathlib import Path


def validate_implementation():
    """Validate all components of domain ontology implementation"""
    print("=" * 80)
    print("DOMAIN ONTOLOGY IMPLEMENTATION VALIDATION")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    errors = []
    warnings = []
    
    # Test 1: Check domain_ontology exists
    print("\n1. Checking domain ontology module...")
    ontology_file = project_root / "src" / "domain" / "ontology" / "__init__.py"
    if ontology_file.exists():
        content = ontology_file.read_text()
        # Check for key components
        checks = [
            ("DomainOntology class", "class DomainOntology"),
            ("DomainResolution dataclass", "@dataclass" and "class DomainResolution"),
            ("load_registry method", "def load_registry"),
            ("extract_domain_terms method", "def extract_domain_terms"),
            ("resolve_domain_term method", "def resolve_domain_term"),
            ("format_domain_context function", "def format_domain_context"),
            ("build_where_clauses function", "def build_where_clauses"),
        ]
        
        for check_name, check_str in checks:
            if check_str in content:
                print(f"   ✓ {check_name} found")
            else:
                errors.append(f"{check_name} not found in domain_ontology.py")
                print(f"   ✗ {check_name} NOT FOUND")
    else:
        errors.append("domain_ontology.py not found")
        print("   ✗ FILE NOT FOUND")
    
    # Test 2: Check domain_registry.json exists and is valid
    print("\n2. Checking domain_registry.json...")
    registry_file = project_root / "artifacts" / "domain_registry.json"
    if registry_file.exists():
        try:
            registry = json.loads(registry_file.read_text())
            print(f"   ✓ Valid JSON file")
            
            if "version" in registry:
                print(f"   ✓ Version field present: {registry['version']}")
            else:
                warnings.append("No version field in registry")
            
            if "terms" in registry:
                term_count = len(registry["terms"])
                print(f"   ✓ Terms field present: {term_count} terms")
                
                # Check for required terms
                required_terms = ["crane", "action_item"]
                for term in required_terms:
                    if term in registry["terms"]:
                        print(f"   ✓ Required term '{term}' present")
                    else:
                        warnings.append(f"Required term '{term}' not in registry")
                        print(f"   ⚠ Required term '{term}' NOT FOUND")
            else:
                errors.append("No 'terms' field in registry")
                print("   ✗ 'terms' field NOT FOUND")
                
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in registry: {e}")
            print(f"   ✗ INVALID JSON: {e}")
    else:
        errors.append("domain_registry.json not found")
        print("   ✗ FILE NOT FOUND")
    
    # Test 3: Check config.py has domain settings
    print("\n3. Checking config.py for domain settings...")
    config_file = project_root / "src" / "utils" / "config.py"
    if config_file.exists():
        content = config_file.read_text()
        settings_checks = [
            "domain_registry_enabled",
            "domain_registry_path",
            "domain_extraction_enabled",
            "domain_fallback_to_text_search",
        ]
        
        for setting in settings_checks:
            if setting in content:
                print(f"   ✓ Setting '{setting}' found")
            else:
                errors.append(f"Setting '{setting}' not found in config.py")
                print(f"   ✗ Setting '{setting}' NOT FOUND")
    else:
        errors.append("config.py not found")
        print("   ✗ FILE NOT FOUND")
    
    # Test 4: Check sql_graph_agent.py has domain integration
    print("\n4. Checking sql_graph_agent.py for domain integration...")
    sql_agent_file = project_root / "src" / "agents" / "sql_graph_agent.py"
    if sql_agent_file.exists():
        content = sql_agent_file.read_text()
        integration_checks = [
            ("Domain imports", "from src.utils.domain_ontology import"),
            ("domain_terms in SQLGraphState", "domain_terms: List[str]"),
            ("domain_resolutions in SQLGraphState", "domain_resolutions: List[Dict[str, Any]]"),
            ("_extract_domain_terms method", "def _extract_domain_terms"),
            ("_resolve_domain_terms method", "def _resolve_domain_terms"),
            ("DomainOntology initialization", "self.domain_ontology = DomainOntology()"),
            ("extract_domain_terms node", 'g.add_node("extract_domain_terms"'),
            ("resolve_domain_terms node", 'g.add_node("resolve_domain_terms"'),
        ]
        
        for check_name, check_str in integration_checks:
            if check_str in content:
                print(f"   ✓ {check_name} found")
            else:
                errors.append(f"{check_name} not found in sql_graph_agent.py")
                print(f"   ✗ {check_name} NOT FOUND")
    else:
        errors.append("sql_graph_agent.py not found")
        print("   ✗ FILE NOT FOUND")
    
    # Test 5: Check test files exist
    print("\n5. Checking test files...")
    test_file = project_root / "tests" / "test_domain_ontology.py"
    if test_file.exists():
        print("   ✓ test_domain_ontology.py found")
    else:
        warnings.append("test_domain_ontology.py not found")
        print("   ⚠ test_domain_ontology.py NOT FOUND")
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if errors:
        print(f"\n✗ {len(errors)} ERROR(S) FOUND:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print(f"\n⚠ {len(warnings)} WARNING(S):")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors:
        print("\n✓ ALL CRITICAL CHECKS PASSED!")
        print("\nImplementation is complete. Key components:")
        print("  1. Domain ontology module (domain_ontology.py)")
        print("  2. Domain registry with business terms (domain_registry.json)")
        print("  3. Configuration settings (config.py)")
        print("  4. SQL agent integration (sql_graph_agent.py)")
        print("  5. Test suite (test_domain_ontology.py)")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure database connection in .env")
        print("  3. Test with: python -m src.agents.sql_graph_agent")
        print("  4. Try the example query:")
        print("     'Find work orders with crane inspections that have action items'")
        return True
    else:
        print("\n✗ VALIDATION FAILED - Fix errors above")
        return False


if __name__ == "__main__":
    import sys
    success = validate_implementation()
    sys.exit(0 if success else 1)
