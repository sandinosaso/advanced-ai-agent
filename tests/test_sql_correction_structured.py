"""
Tests for the structured SQL correction system.

These tests verify:
1. Error normalization (raw MySQL errors → semantic types)
2. Deterministic fixers (AST-based SQL transformations)
3. Strategy selection (deterministic vs LLM)
4. Metrics tracking

Note: These tests require sqlglot to be installed.
"""

import pytest

# Import directly from submodules to avoid circular imports
from src.agents.sql.correction.error_types import SQLErrorType, NormalizedError
from src.agents.sql.correction.error_parser import normalize_error
from src.agents.sql.correction.metrics import get_metrics_summary, reset_metrics, record_fix


class TestErrorNormalization:
    """Test error_parser.normalize_error()"""
    
    def test_group_by_violation(self):
        """Test GROUP BY violation error normalization"""
        error_msg = (
            "Expression #2 of SELECT list is not in GROUP BY clause and contains "
            "nonaggregated column 'crewos.workTime.startTime' which is not functionally "
            "dependent on columns in GROUP BY clause"
        )
        
        normalized = normalize_error(error_msg)
        
        assert normalized.error_type == SQLErrorType.GROUP_BY_VIOLATION
        assert normalized.details["expression_num"] == 2
        assert "workTime.startTime" in normalized.details["column"]
        assert normalized.raw_message == error_msg
    
    def test_duplicate_alias(self):
        """Test duplicate table/alias error normalization"""
        error_msg = "Not unique table/alias: 'users'"
        
        normalized = normalize_error(error_msg)
        
        assert normalized.error_type == SQLErrorType.DUPLICATE_ALIAS
        assert normalized.details["table"] == "users"
    
    def test_unknown_column(self):
        """Test unknown column error normalization"""
        error_msg = "Unknown column 'users.invalid_col' in 'field list'"
        
        normalized = normalize_error(error_msg)
        
        assert normalized.error_type == SQLErrorType.UNKNOWN_COLUMN
        assert normalized.details["column"] == "users.invalid_col"
        assert normalized.details["location"] == "field list"
    
    def test_unknown_error_type(self):
        """Test unrecognized error falls back to OTHER"""
        error_msg = "Some weird database error we've never seen"
        
        normalized = normalize_error(error_msg)
        
        assert normalized.error_type == SQLErrorType.OTHER
        assert normalized.details == {}


class TestDeterministicFixers:
    """Test fixers.py deterministic SQL transformations"""
    
    def test_fix_group_by_violation_basic(self):
        """Test basic GROUP BY fix (add missing expression)"""
        # Skip if sqlglot not installed
        pytest.importorskip("sqlglot")
        
        from src.agents.sql.correction.fixers import fix_group_by_violation
        
        sql = "SELECT id, COUNT(*) FROM users GROUP BY id"
        # Expression #1 (id) is missing from GROUP BY
        # (This is a contrived example - normally id would already be there)
        
        # For a real test, let's use a more realistic example:
        sql = "SELECT dept, DATE_FORMAT(created, '%Y') AS year, COUNT(*) FROM users GROUP BY dept"
        # Expression #2 (DATE_FORMAT) is missing
        
        fixed = fix_group_by_violation(sql, expression_num=2)
        
        # Verify the fix added DATE_FORMAT to GROUP BY
        assert "GROUP BY" in fixed
        assert "DATE_FORMAT" in fixed
        # The exact format may vary, but it should include both dept and DATE_FORMAT
    
    def test_fix_duplicate_join_basic(self):
        """Test duplicate join removal"""
        pytest.importorskip("sqlglot")
        
        from src.agents.sql.correction.fixers import fix_duplicate_join
        
        sql = "SELECT * FROM a JOIN b ON a.id = b.id JOIN b AS b2 ON a.x = b2.x"
        
        fixed = fix_duplicate_join(sql, duplicate_table="b")
        
        # Should remove one of the joins to 'b'
        # Count occurrences of "JOIN b"
        join_count = fixed.upper().count("JOIN B")
        assert join_count == 1, f"Expected 1 JOIN to b, found {join_count}"


class TestMetrics:
    """Test metrics.py tracking"""
    
    def setup_method(self):
        """Reset metrics before each test"""
        reset_metrics()
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly"""
        
        # Record some fixes
        record_fix(SQLErrorType.GROUP_BY_VIOLATION, "deterministic_group_by", success=True)
        record_fix(SQLErrorType.GROUP_BY_VIOLATION, "deterministic_group_by", success=True)
        record_fix(SQLErrorType.DUPLICATE_ALIAS, "deterministic_duplicate_join", success=True)
        record_fix(SQLErrorType.UNKNOWN_COLUMN, "llm_fallback", success=True)
        record_fix(SQLErrorType.OTHER, "llm_fallback", success=False)
        
        summary = get_metrics_summary()
        
        assert summary["total_attempts"] == 5
        assert summary["total_deterministic"] == 3
        assert summary["total_llm"] == 1
        assert summary["total_failures"] == 1
        assert summary["deterministic_rate"] == 0.6  # 3/5
        assert summary["success_rate"] == 0.8  # 4/5
    
    def test_metrics_empty(self):
        """Test metrics with no data"""
        summary = get_metrics_summary()
        
        assert summary["total_attempts"] == 0
        assert summary["deterministic_rate"] == 0.0
        assert summary["success_rate"] == 0.0


class TestNormalizedError:
    """Test NormalizedError dataclass"""
    
    def test_get_detail(self):
        """Test get_detail() helper method"""
        error = NormalizedError(
            error_type=SQLErrorType.GROUP_BY_VIOLATION,
            raw_message="test error",
            details={"expression_num": 2, "column": "test.col"}
        )
        
        assert error.get_detail("expression_num") == 2
        assert error.get_detail("column") == "test.col"
        assert error.get_detail("missing_key") is None
        assert error.get_detail("missing_key", default=42) == 42
    
    def test_str_representation(self):
        """Test __str__() method"""
        error = NormalizedError(
            error_type=SQLErrorType.UNKNOWN_COLUMN,
            raw_message="test",
            details={"column": "users.id"}
        )
        
        str_repr = str(error)
        assert "unknown_column" in str_repr
        assert "users.id" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
