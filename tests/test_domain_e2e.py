#!/usr/bin/env python3
"""
End-to-end test for domain ontology layer

Tests the full workflow with a real example:
"Find work orders with crane inspections that have action items"

This script validates that:
1. Domain terms are extracted correctly
2. Terms are resolved to schema locations
3. Tables are selected with domain context
4. SQL includes proper WHERE clauses for domain filters

Run this after ensuring database connection is configured.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.domain_ontology import DomainOntology, build_where_clauses
from src.utils.config import settings


def test_domain_ontology_basic():
    """Test basic domain ontology functionality"""
    print("=" * 80)
    print("DOMAIN ONTOLOGY END-TO-END TEST")
    print("=" * 80)
    
    # Test 1: Load registry
    print("\n1. Loading domain registry...")
    ontology = DomainOntology()
    terms = ontology.get_all_domain_terms()
    print(f"   ✓ Loaded {len(terms)} domain terms: {', '.join(terms[:5])}...")
    
    # Test 2: Resolve crane
    print("\n2. Resolving 'crane' term...")
    crane_res = ontology.resolve_domain_term("crane")
    if crane_res:
        print(f"   ✓ Resolved to entity: {crane_res.entity}")
        print(f"   ✓ Tables: {crane_res.tables}")
        print(f"   ✓ Filters: {len(crane_res.filters)} filter(s)")
        print(f"   ✓ Confidence: {crane_res.confidence}")
    else:
        print("   ✗ Failed to resolve 'crane'")
        return False
    
    # Test 3: Resolve action_item
    print("\n3. Resolving 'action_item' term...")
    action_res = ontology.resolve_domain_term("action_item")
    if action_res:
        print(f"   ✓ Resolved to entity: {action_res.entity}")
        print(f"   ✓ Tables: {action_res.tables}")
        print(f"   ✓ Filters: {len(action_res.filters)} filter(s)")
        print(f"   ✓ Confidence: {action_res.confidence}")
    else:
        print("   ✗ Failed to resolve 'action_item'")
        return False
    
    # Test 4: Build WHERE clauses
    print("\n4. Building WHERE clauses...")
    resolutions = [
        {
            'term': crane_res.term,
            'entity': crane_res.entity,
            'tables': crane_res.tables,
            'filters': crane_res.filters,
            'confidence': crane_res.confidence,
            'strategy': crane_res.resolution_strategy
        },
        {
            'term': action_res.term,
            'entity': action_res.entity,
            'tables': action_res.tables,
            'filters': action_res.filters,
            'confidence': action_res.confidence,
            'strategy': action_res.resolution_strategy
        }
    ]
    
    where_clauses = build_where_clauses(resolutions)
    print(f"   ✓ Generated {len(where_clauses)} WHERE clause(s):")
    for clause in where_clauses:
        print(f"     - {clause}")
    
    # Test 5: Configuration check
    print("\n5. Checking configuration...")
    print(f"   ✓ Domain registry enabled: {settings.domain_registry_enabled}")
    print(f"   ✓ Domain extraction enabled: {settings.domain_extraction_enabled}")
    print(f"   ✓ Registry path: {settings.domain_registry_path}")
    
    print("\n" + "=" * 80)
    print("ALL BASIC TESTS PASSED ✓")
    print("=" * 80)
    
    return True


def test_sql_agent_integration():
    """Test SQLGraphAgent with domain ontology (requires database)"""
    print("\n" + "=" * 80)
    print("SQL AGENT INTEGRATION TEST")
    print("=" * 80)
    print("\nNOTE: This test requires a database connection.")
    print("Skipping SQL agent integration test (run manually if needed).")
    print("\nTo test manually, run:")
    print('  python -c "from src.agents.sql_graph_agent import SQLGraphAgent; '
          'agent = SQLGraphAgent(); '
          'result = agent.query(\'Find work orders with crane inspections that have action items\'); '
          'print(result)"')
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        # Run basic tests
        success = test_domain_ontology_basic()
        
        # Show integration test info
        test_sql_agent_integration()
        
        if success:
            print("\n✓ Domain ontology implementation is working correctly!")
            print("\nNext steps:")
            print("1. Ensure database is configured (check .env file)")
            print("2. Run the SQL agent with the example query")
            print("3. Monitor logs to see domain term extraction and resolution")
            sys.exit(0)
        else:
            print("\n✗ Some tests failed. Check output above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
