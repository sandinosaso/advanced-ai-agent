#!/usr/bin/env python3
"""
Follow-up Question Memory Tests

Tests the QueryResultMemory system and follow-up question detection.
"""

import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.query_memory import QueryResultMemory, QueryResult


def test_query_result_creation():
    """Test QueryResult creation and ID extraction"""
    print("\n" + "=" * 80)
    print("TEST 1: QueryResult Creation and ID Extraction")
    print("=" * 80)
    
    # Sample data with various ID fields
    sample_data = [
        {
            "inspectionId": "abc-123",
            "workOrderId": "def-456",
            "inspectionName": "Crane at the back",
            "status": "IN_PROGRESS",
            "createdAt": "2025-02-17T14:55:04"
        },
        {
            "inspectionId": "abc-123",  # Same inspection
            "workOrderId": "def-456",
            "inspectionName": "Crane at the back",
            "status": "IN_PROGRESS",
            "createdAt": "2025-02-17T14:55:04"
        }
    ]
    
    result = QueryResult(
        question="Find crane inspections for ABC COKE",
        structured_data=sample_data,
        sql_query="SELECT * FROM inspection WHERE ...",
        tables_used=["inspection", "workOrder", "customer"]
    )
    
    # Verify ID extraction
    assert "inspectionId" in result.identifiers, "inspectionId should be extracted"
    assert "workOrderId" in result.identifiers, "workOrderId should be extracted"
    assert result.identifiers["inspectionId"] == ["abc-123"], "Should have unique inspection ID"
    assert result.identifiers["workOrderId"] == ["def-456"], "Should have unique work order ID"
    assert result.row_count == 2, "Should count 2 rows"
    
    print("✓ QueryResult created successfully")
    print(f"  - Extracted IDs: {result.identifiers}")
    print(f"  - Row count: {result.row_count}")
    print(f"  - Tables used: {result.tables_used}")
    
    # Test sample rows
    sample = result.get_sample_rows(1)
    assert len(sample) == 1, "Should return 1 sample row"
    print(f"  - Sample row: {sample[0]}")
    
    print("\n✅ TEST 1 PASSED")
    return True


def test_memory_add_and_retrieve():
    """Test adding results to memory and retrieving them"""
    print("\n" + "=" * 80)
    print("TEST 2: Memory Add and Retrieve")
    print("=" * 80)
    
    memory = QueryResultMemory(max_results=3)
    
    # Add first result
    memory.add_result(
        question="Find crane inspections for ABC COKE",
        structured_data=[
            {"inspectionId": "abc-123", "name": "Crane Inspection 1"}
        ],
        tables_used=["inspection", "workOrder"]
    )
    
    assert len(memory) == 1, "Should have 1 result"
    print(f"✓ Added first result, memory size: {len(memory)}")
    
    # Add second result
    memory.add_result(
        question="Show work orders in progress",
        structured_data=[
            {"workOrderId": "wo-456", "status": "IN_PROGRESS"}
        ],
        tables_used=["workOrder"]
    )
    
    assert len(memory) == 2, "Should have 2 results"
    print(f"✓ Added second result, memory size: {len(memory)}")
    
    # Retrieve recent results
    recent = memory.get_recent_results(n=2)
    assert len(recent) == 2, "Should retrieve 2 recent results"
    assert recent[0].question == "Show work orders in progress", "Most recent should be first"
    assert recent[1].question == "Find crane inspections for ABC COKE", "Older should be second"
    
    print(f"✓ Retrieved {len(recent)} recent results")
    print(f"  - Most recent: {recent[0].question}")
    print(f"  - Second: {recent[1].question}")
    
    # Test max_results limit
    for i in range(5):
        memory.add_result(
            question=f"Query {i}",
            structured_data=[{"id": i}],
            tables_used=["table"]
        )
    
    assert len(memory) == 3, f"Should respect max_results=3, got {len(memory)}"
    print(f"✓ Memory respects max_results limit: {len(memory)}/3")
    
    print("\n✅ TEST 2 PASSED")
    return True


def test_memory_serialization():
    """Test memory serialization for checkpoint persistence"""
    print("\n" + "=" * 80)
    print("TEST 3: Memory Serialization")
    print("=" * 80)
    
    # Create memory with data
    memory = QueryResultMemory(max_results=5)
    memory.add_result(
        question="Find inspections",
        structured_data=[
            {"inspectionId": "abc-123", "name": "Test Inspection"}
        ],
        tables_used=["inspection"]
    )
    
    # Serialize
    serialized = memory.to_dict()
    assert isinstance(serialized, list), "Should serialize to list"
    assert len(serialized) == 1, "Should have 1 serialized result"
    print(f"✓ Serialized to list with {len(serialized)} items")
    
    # Deserialize
    restored = QueryResultMemory.from_dict(serialized, max_results=5)
    assert len(restored) == 1, "Should restore 1 result"
    assert restored.results[0].question == "Find inspections", "Should restore question"
    assert "inspectionId" in restored.results[0].identifiers, "Should restore IDs"
    
    print(f"✓ Deserialized successfully")
    print(f"  - Question: {restored.results[0].question}")
    print(f"  - IDs: {restored.results[0].identifiers}")
    
    print("\n✅ TEST 3 PASSED")
    return True


def test_memory_context_formatting():
    """Test context formatting for LLM prompts"""
    print("\n" + "=" * 80)
    print("TEST 4: Memory Context Formatting")
    print("=" * 80)
    
    memory = QueryResultMemory(max_results=5)
    
    # Add sample results
    memory.add_result(
        question="Find crane inspections for ABC COKE",
        structured_data=[
            {
                "inspectionId": "abc-123",
                "workOrderId": "wo-456",
                "inspectionName": "Crane at the back",
                "status": "IN_PROGRESS"
            }
        ],
        tables_used=["inspection", "workOrder", "customer"]
    )
    
    # Format for context
    context = memory.format_for_context(n=1, max_tokens=2000, include_sample_rows=True)
    
    assert context, "Should generate context string"
    assert "Find crane inspections" in context, "Should include question"
    assert "inspectionId" in context, "Should include ID fields"
    assert "abc-123" in context, "Should include ID values"
    assert "inspection, workOrder, customer" in context, "Should include tables"
    
    print("✓ Context formatted successfully")
    print(f"  - Length: {len(context)} chars (~{len(context)//4} tokens)")
    print("\nContext preview:")
    print("-" * 80)
    print(context[:500] + "..." if len(context) > 500 else context)
    print("-" * 80)
    
    # Test without sample rows (token limit)
    context_no_samples = memory.format_for_context(n=1, max_tokens=500, include_sample_rows=False)
    assert len(context_no_samples) < len(context), "Should be shorter without samples"
    print(f"✓ Context without samples: {len(context_no_samples)} chars")
    
    print("\n✅ TEST 4 PASSED")
    return True


def test_all_identifiers_extraction():
    """Test extracting all identifiers from multiple results"""
    print("\n" + "=" * 80)
    print("TEST 5: All Identifiers Extraction")
    print("=" * 80)
    
    memory = QueryResultMemory(max_results=5)
    
    # Add multiple results with overlapping IDs
    memory.add_result(
        question="Query 1",
        structured_data=[
            {"inspectionId": "abc-123", "workOrderId": "wo-1"}
        ],
        tables_used=["inspection"]
    )
    
    memory.add_result(
        question="Query 2",
        structured_data=[
            {"inspectionId": "abc-123", "workOrderId": "wo-2"},  # Same inspection, different WO
            {"inspectionId": "def-456", "workOrderId": "wo-3"}   # Different inspection
        ],
        tables_used=["inspection"]
    )
    
    # Get all identifiers
    all_ids = memory.get_all_identifiers(n=2)
    
    assert "inspectionId" in all_ids, "Should have inspectionId"
    assert "workOrderId" in all_ids, "Should have workOrderId"
    assert len(all_ids["inspectionId"]) == 2, "Should have 2 unique inspection IDs"
    assert len(all_ids["workOrderId"]) == 3, "Should have 3 unique work order IDs"
    
    print("✓ Extracted all identifiers from multiple results")
    print(f"  - inspectionId: {all_ids['inspectionId']}")
    print(f"  - workOrderId: {all_ids['workOrderId']}")
    
    print("\n✅ TEST 5 PASSED")
    return True


def test_implementation_validation():
    """Validate that all required files and code structures are in place"""
    print("\n" + "=" * 80)
    print("TEST 6: Implementation Validation")
    print("=" * 80)
    
    errors = []
    
    # Check query_memory.py exists
    print("\n1. Checking query_memory.py...")
    memory_file = project_root / "src" / "utils" / "query_memory.py"
    if memory_file.exists():
        content = memory_file.read_text()
        checks = [
            ("QueryResult class", "class QueryResult"),
            ("QueryResultMemory class", "class QueryResultMemory"),
            ("add_result method", "def add_result"),
            ("get_recent_results method", "def get_recent_results"),
            ("format_for_context method", "def format_for_context"),
            ("to_dict method", "def to_dict"),
            ("from_dict method", "def from_dict"),
        ]
        
        for check_name, check_str in checks:
            if check_str in content:
                print(f"   ✓ {check_name} found")
            else:
                errors.append(f"{check_name} not found in query_memory.py")
                print(f"   ✗ {check_name} NOT FOUND")
    else:
        errors.append("query_memory.py not found")
        print("   ✗ FILE NOT FOUND")
    
    # Check sql_graph_agent.py has follow-up support
    print("\n2. Checking sql_graph_agent.py...")
    sql_agent_file = project_root / "src" / "agents" / "sql_graph_agent.py"
    if sql_agent_file.exists():
        content = sql_agent_file.read_text()
        checks = [
            ("previous_results in SQLGraphState", "previous_results"),
            ("is_followup in SQLGraphState", "is_followup"),
            ("referenced_ids in SQLGraphState", "referenced_ids"),
            ("_detect_followup_question method", "def _detect_followup_question"),
            ("detect_followup node", '"detect_followup"'),
        ]
        
        for check_name, check_str in checks:
            if check_str in content:
                print(f"   ✓ {check_name} found")
            else:
                errors.append(f"{check_name} not found in sql_graph_agent.py")
                print(f"   ✗ {check_name} NOT FOUND")
    else:
        errors.append("sql_graph_agent.py not found")
        print("   ✗ FILE NOT FOUND")
    
    # Check orchestrator_agent.py has memory support
    print("\n3. Checking orchestrator_agent.py...")
    orch_file = project_root / "src" / "agents" / "orchestrator_agent.py"
    if orch_file.exists():
        content = orch_file.read_text()
        checks = [
            ("query_result_memory in AgentState", "query_result_memory"),
            ("QueryResultMemory import", "from src.utils.query_memory import QueryResultMemory"),
        ]
        
        for check_name, check_str in checks:
            if check_str in content:
                print(f"   ✓ {check_name} found")
            else:
                errors.append(f"{check_name} not found in orchestrator_agent.py")
                print(f"   ✗ {check_name} NOT FOUND")
    else:
        errors.append("orchestrator_agent.py not found")
        print("   ✗ FILE NOT FOUND")
    
    # Check config.py has settings
    print("\n4. Checking config.py...")
    config_file = project_root / "src" / "utils" / "config.py"
    if config_file.exists():
        content = config_file.read_text()
        checks = [
            ("query_result_memory_size", "query_result_memory_size"),
            ("followup_detection_enabled", "followup_detection_enabled"),
            ("followup_max_context_tokens", "followup_max_context_tokens"),
        ]
        
        for check_name, check_str in checks:
            if check_str in content:
                print(f"   ✓ {check_name} found")
            else:
                errors.append(f"{check_name} not found in config.py")
                print(f"   ✗ {check_name} NOT FOUND")
    else:
        errors.append("config.py not found")
        print("   ✗ FILE NOT FOUND")
    
    if errors:
        print("\n❌ TEST 6 FAILED")
        print("\nErrors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ TEST 6 PASSED")
        return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("FOLLOW-UP QUESTION MEMORY TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("QueryResult Creation", test_query_result_creation),
        ("Memory Add/Retrieve", test_memory_add_and_retrieve),
        ("Memory Serialization", test_memory_serialization),
        ("Context Formatting", test_memory_context_formatting),
        ("All IDs Extraction", test_all_identifiers_extraction),
        ("Implementation Validation", test_implementation_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
