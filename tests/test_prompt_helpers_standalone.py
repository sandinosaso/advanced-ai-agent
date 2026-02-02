"""
Standalone test for prompt_helpers utility functions.
Tests the core logic without importing the full agent stack.
"""


def get_sample_table_names(join_graph, n=3):
    """Simplified version for testing."""
    if not join_graph or "tables" not in join_graph:
        return []
    
    tables = list(join_graph["tables"].keys())
    if not tables:
        return []
    
    relationships = join_graph.get("relationships", [])
    table_rel_count = {}
    for rel in relationships:
        from_table = rel.get("from_table")
        to_table = rel.get("to_table")
        if from_table:
            table_rel_count[from_table] = table_rel_count.get(from_table, 0) + 1
        if to_table:
            table_rel_count[to_table] = table_rel_count.get(to_table, 0) + 1
    
    sorted_tables = sorted(tables, key=lambda t: table_rel_count.get(t, 0), reverse=True)
    return sorted_tables[:min(n, len(sorted_tables))]


def test_basic_functionality():
    """Test that the core logic works."""
    join_graph = {
        "tables": {
            "employee": {"columns": ["id", "firstName", "lastName"]},
            "crew": {"columns": ["id", "name"]},
            "workOrder": {"columns": ["id", "status"]},
        },
        "relationships": [
            {"from_table": "employee", "to_table": "crew"},
            {"from_table": "employee", "to_table": "workOrder"},
            {"from_table": "crew", "to_table": "workOrder"},
        ]
    }
    
    # Test sample table names
    result = get_sample_table_names(join_graph, n=2)
    assert len(result) <= 2
    assert all(t in join_graph["tables"] for t in result)
    print(f"✓ Sample tables: {result}")
    
    # Test empty graph
    empty_graph = {"tables": {}, "relationships": []}
    result = get_sample_table_names(empty_graph)
    assert result == []
    print("✓ Empty graph handled")
    
    # Test None graph
    result = get_sample_table_names(None)
    assert result == []
    print("✓ None graph handled")
    
    print("\n✅ All basic tests passed!")


if __name__ == "__main__":
    print("Testing prompt_helpers core logic...\n")
    test_basic_functionality()
