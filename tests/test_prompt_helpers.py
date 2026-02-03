"""
Test prompt_helpers utility functions to ensure they work correctly.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.sql.prompt_helpers import (
    get_sample_table_names,
    get_sample_relationships,
    get_name_label_columns_map,
    get_sample_bridge_path,
    build_name_label_examples,
    build_bridge_table_example,
    build_duplicate_join_example,
    get_most_connected_tables,
    build_column_mismatch_example,
)


def test_get_sample_table_names():
    """Test getting sample table names from join graph."""
    join_graph = {
        "tables": {
            "employee": {},
            "workOrder": {},
            "crew": {},
        },
        "relationships": [
            {"from_table": "employee", "to_table": "crew"},
            {"from_table": "employee", "to_table": "workOrder"},
        ]
    }
    
    result = get_sample_table_names(join_graph, n=2)
    assert len(result) <= 2
    assert all(t in join_graph["tables"] for t in result)
    print("✓ get_sample_table_names works")


def test_get_name_label_columns_map():
    """Test detecting name/label columns."""
    join_graph = {
        "tables": {
            "employee": {"columns": ["id", "firstName", "lastName", "email"]},
            "crew": {"columns": ["id", "name", "description"]},
            "workOrder": {"columns": ["id", "status", "customerId"]},
        }
    }
    
    result = get_name_label_columns_map(join_graph)
    assert "employee" in result
    assert "firstName" in result["employee"]
    assert "lastName" in result["employee"]
    assert "crew" in result
    assert "name" in result["crew"]
    assert "workOrder" not in result  # No name columns
    print("✓ get_name_label_columns_map works")


def test_build_name_label_examples():
    """Test building name/label examples."""
    join_graph = {
        "tables": {
            "employee": {"columns": ["id", "firstName", "lastName"]},
            "crew": {"columns": ["id", "name"]},
        }
    }
    
    result = build_name_label_examples(join_graph, max_examples=2)
    assert "employee" in result or "crew" in result
    assert "IMPORTANT FOR NAME/LABEL REQUESTS" in result
    print("✓ build_name_label_examples works")


def test_build_bridge_table_example():
    """Test building bridge table example."""
    join_graph = {
        "tables": {"a": {}, "b": {}, "c": {}},
        "relationships": [
            {"from_table": "a", "to_table": "b", "from_column": "bId", "to_column": "id"},
            {"from_table": "b", "to_table": "c", "from_column": "cId", "to_column": "id"},
        ]
    }
    
    result = build_bridge_table_example(join_graph)
    assert "bridge table" in result.lower()
    assert "intermediate tables" in result.lower()
    print("✓ build_bridge_table_example works")


def test_get_most_connected_tables():
    """Test getting most connected tables."""
    join_graph = {
        "tables": {"a": {}, "b": {}, "c": {}, "d": {}},
        "relationships": [
            {"from_table": "a", "to_table": "b"},
            {"from_table": "a", "to_table": "c"},
            {"from_table": "a", "to_table": "d"},
            {"from_table": "b", "to_table": "c"},
        ]
    }
    
    result = get_most_connected_tables(join_graph, n=2)
    assert len(result) <= 2
    # 'a' should be most connected (3 relationships)
    assert result[0] == "a"
    print("✓ get_most_connected_tables works")


def test_empty_join_graph():
    """Test functions handle empty join graph gracefully."""
    empty_graph = {"tables": {}, "relationships": []}
    
    assert get_sample_table_names(empty_graph) == []
    assert get_name_label_columns_map(empty_graph) == {}
    assert build_name_label_examples(empty_graph) == ""
    assert "bridge table" in build_bridge_table_example(empty_graph).lower()
    assert get_most_connected_tables(empty_graph) == []
    print("✓ Empty join graph handled gracefully")


def test_none_join_graph():
    """Test functions handle None join graph gracefully."""
    assert get_sample_table_names(None) == []
    assert get_name_label_columns_map(None) == {}
    assert build_name_label_examples(None) == ""
    assert "bridge table" in build_bridge_table_example(None).lower()
    assert get_most_connected_tables(None) == []
    print("✓ None join graph handled gracefully")


if __name__ == "__main__":
    print("Testing prompt_helpers utilities...\n")
    
    test_get_sample_table_names()
    test_get_name_label_columns_map()
    test_build_name_label_examples()
    test_build_bridge_table_example()
    test_get_most_connected_tables()
    test_empty_join_graph()
    test_none_join_graph()
    
    print("\n✅ All tests passed!")
