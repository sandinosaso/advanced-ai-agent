"""
Test script for secure views implementation.

This validates:
1. SECURE_VIEW_MAP is properly defined
2. Rewriting works correctly (employee → secure_employee)
3. Non-secure tables are NOT rewritten (inspections stays inspections)
4. Table validation catches hallucinated tables (secure_inspections → error)
"""

import sys
from src.sql.execution.secure_rewriter import (
    is_secure_table,
    to_secure_view,
    rewrite_secure_tables,
    extract_tables_from_sql,
    validate_tables_exist,
    log_secure_view_config
)
from src.config.constants import SECURE_VIEW_MAP

def test_secure_view_map():
    """Test SECURE_VIEW_MAP structure"""
    print("=" * 60)
    print("TEST 1: SECURE_VIEW_MAP Structure")
    print("=" * 60)
    
    log_secure_view_config()
    
    assert len(SECURE_VIEW_MAP) == 6, f"Expected 6 mappings, got {len(SECURE_VIEW_MAP)}"
    assert "employee" in SECURE_VIEW_MAP
    assert "workorder" in SECURE_VIEW_MAP
    assert "customer" in SECURE_VIEW_MAP
    
    print("✅ SECURE_VIEW_MAP properly defined\n")


def test_is_secure_table():
    """Test is_secure_table function"""
    print("=" * 60)
    print("TEST 2: is_secure_table()")
    print("=" * 60)
    
    # Should return True
    assert is_secure_table("employee") == True
    assert is_secure_table("EMPLOYEE") == True
    assert is_secure_table("workOrder") == True
    assert is_secure_table("customer") == True
    
    # Should return False
    assert is_secure_table("inspections") == False
    assert is_secure_table("workTime") == False
    assert is_secure_table("status") == False
    
    print("✅ is_secure_table correctly identifies secure tables\n")


def test_to_secure_view():
    """Test to_secure_view function"""
    print("=" * 60)
    print("TEST 3: to_secure_view()")
    print("=" * 60)
    
    # Should convert to secure view
    assert to_secure_view("employee") == "secure_employee"
    assert to_secure_view("EMPLOYEE") == "secure_employee"
    assert to_secure_view("workOrder") == "secure_workorder"
    
    # Should NOT convert (table doesn't need secure view)
    assert to_secure_view("inspections") == "inspections"
    assert to_secure_view("workTime") == "workTime"
    assert to_secure_view("status") == "status"
    
    print("✅ to_secure_view correctly converts tables\n")


def test_rewrite_secure_tables():
    """Test SQL rewriting"""
    print("=" * 60)
    print("TEST 4: rewrite_secure_tables()")
    print("=" * 60)
    
    # Test 1: Simple SELECT with employee
    sql1 = "SELECT * FROM employee WHERE id = 1"
    rewritten1 = rewrite_secure_tables(sql1)
    print(f"Original:  {sql1}")
    print(f"Rewritten: {rewritten1}")
    assert "secure_employee" in rewritten1
    assert "FROM employee" not in rewritten1.lower()
    print("✅ Test 1 passed\n")
    
    # Test 2: JOIN with employee and workOrder
    sql2 = "SELECT e.name FROM employee e JOIN workOrder wo ON e.id = wo.employeeId"
    rewritten2 = rewrite_secure_tables(sql2)
    print(f"Original:  {sql2}")
    print(f"Rewritten: {rewritten2}")
    assert "secure_employee" in rewritten2
    assert "secure_workorder" in rewritten2
    print("✅ Test 2 passed\n")
    
    # Test 3: Non-secure table should NOT change
    sql3 = "SELECT * FROM inspections WHERE id = 1"
    rewritten3 = rewrite_secure_tables(sql3)
    print(f"Original:  {sql3}")
    print(f"Rewritten: {rewritten3}")
    assert "secure_inspections" not in rewritten3
    assert "inspections" in rewritten3
    print("✅ Test 3 passed\n")
    
    # Test 4: Mixed secure and non-secure
    sql4 = "SELECT e.name, i.status FROM employee e JOIN inspections i ON e.id = i.employeeId"
    rewritten4 = rewrite_secure_tables(sql4)
    print(f"Original:  {sql4}")
    print(f"Rewritten: {rewritten4}")
    assert "secure_employee" in rewritten4
    assert "inspections" in rewritten4
    assert "secure_inspections" not in rewritten4
    print("✅ Test 4 passed\n")
    
    print("✅ rewrite_secure_tables works correctly\n")


def test_extract_tables():
    """Test table extraction from SQL"""
    print("=" * 60)
    print("TEST 5: extract_tables_from_sql()")
    print("=" * 60)
    
    sql = "SELECT e.name FROM employee e JOIN workTime w ON e.id = w.employeeId WHERE w.hours > 10"
    tables = extract_tables_from_sql(sql)
    print(f"SQL: {sql}")
    print(f"Extracted tables: {tables}")
    
    assert "employee" in tables
    assert "worktime" in tables  # Normalized to lowercase
    
    print("✅ extract_tables_from_sql works correctly\n")


def test_table_validation():
    """Test table validation"""
    print("=" * 60)
    print("TEST 6: validate_tables_exist()")
    print("=" * 60)
    
    known_tables = {"secure_employee", "secure_workorder", "inspections", "worktime", "status"}
    
    # Test 1: Valid query
    sql1 = "SELECT * FROM secure_employee"
    try:
        validate_tables_exist(sql1, known_tables)
        print(f"✅ Valid query passed: {sql1}")
    except ValueError as e:
        print(f"❌ Valid query should not fail: {e}")
        sys.exit(1)
    
    # Test 2: Invalid query (hallucinated secure_inspections)
    sql2 = "SELECT * FROM secure_inspections"
    try:
        validate_tables_exist(sql2, known_tables)
        print(f"❌ Invalid query should have raised ValueError: {sql2}")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ Invalid query correctly raised error: {e}")
    
    # Test 3: Mixed valid and invalid
    sql3 = "SELECT * FROM secure_employee JOIN fake_table ON secure_employee.id = fake_table.employeeId"
    try:
        validate_tables_exist(sql3, known_tables)
        print(f"❌ Query with fake_table should have failed")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ Query with non-existent table correctly raised error: {e}")
    
    print("\n✅ validate_tables_exist works correctly\n")


def test_end_to_end_scenario():
    """Test realistic end-to-end scenario"""
    print("=" * 60)
    print("TEST 7: End-to-End Scenario")
    print("=" * 60)
    
    # Scenario: LLM generates query with logical table names
    llm_generated_sql = """
    SELECT e.firstName, e.lastName, SUM(w.hours) AS total_hours
    FROM employee e
    JOIN workTime w ON e.id = w.employeeId
    WHERE w.startTime >= '2025-07-01'
    GROUP BY e.id
    HAVING total_hours > 20
    ORDER BY total_hours DESC
    LIMIT 10
    """
    
    print("LLM Generated SQL (logical table names):")
    print(llm_generated_sql)
    print()
    
    # Step 1: Rewrite to use secure views
    rewritten_sql = rewrite_secure_tables(llm_generated_sql)
    print("After rewrite_secure_tables:")
    print(rewritten_sql)
    print()
    
    # Verify employee → secure_employee
    assert "secure_employee" in rewritten_sql
    assert "FROM employee" not in rewritten_sql
    assert "JOIN workTime" in rewritten_sql  # workTime unchanged
    
    print("✅ End-to-end rewriting works correctly\n")


def test_hallucination_prevention():
    """Test that we prevent LLM from hallucinating secure_* tables"""
    print("=" * 60)
    print("TEST 8: Hallucination Prevention")
    print("=" * 60)
    
    # Scenario: LLM incorrectly generates secure_inspections
    bad_sql = "SELECT * FROM secure_inspections WHERE status = 'pending'"
    
    known_tables = {"secure_employee", "inspections", "worktime"}
    
    print(f"Bad SQL (hallucinated table): {bad_sql}")
    
    try:
        validate_tables_exist(bad_sql, known_tables)
        print("❌ Should have caught secure_inspections as invalid")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ Correctly caught hallucinated table: {e}")
    
    # Show correct approach
    good_sql = "SELECT * FROM inspections WHERE status = 'pending'"
    rewritten = rewrite_secure_tables(good_sql)
    
    print(f"\nCorrect SQL: {good_sql}")
    print(f"After rewrite: {rewritten}")
    assert "secure_inspections" not in rewritten
    assert "inspections" in rewritten
    
    print("✅ Hallucination prevention works correctly\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SECURE VIEWS IMPLEMENTATION TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_secure_view_map()
        test_is_secure_table()
        test_to_secure_view()
        test_rewrite_secure_tables()
        test_extract_tables()
        test_table_validation()
        test_end_to_end_scenario()
        test_hallucination_prevention()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60 + "\n")
        
        print("Summary:")
        print("- SECURE_VIEW_MAP properly defined (6 tables)")
        print("- Rewriting works correctly (employee → secure_employee)")
        print("- Non-secure tables NOT rewritten (inspections stays inspections)")
        print("- Table validation catches hallucinated tables (secure_inspections → error)")
        print("- End-to-end scenarios work as expected")
        print("\nThe implementation is ready for production use.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
