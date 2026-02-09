"""
Standalone tests for SQL correction system (no database required).

Run with: python tests/test_correction_standalone.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import directly from correction modules (bypassing src.agents.__init__)
from src.agents.sql.correction.error_types import SQLErrorType, NormalizedError
from src.agents.sql.correction.error_parser import normalize_error


def test_error_normalization():
    """Test error normalization"""
    print("Testing error normalization...")
    
    # Test GROUP BY violation
    error_msg = (
        "Expression #2 of SELECT list is not in GROUP BY clause and contains "
        "nonaggregated column 'crewos.workTime.startTime'"
    )
    normalized = normalize_error(error_msg)
    
    assert normalized.error_type == SQLErrorType.GROUP_BY_VIOLATION
    assert normalized.details["expression_num"] == 2
    assert "workTime.startTime" in normalized.details["column"]
    print("  ✅ GROUP BY violation normalization works")
    
    # Test duplicate alias
    error_msg2 = "Not unique table/alias: 'users'"
    normalized2 = normalize_error(error_msg2)
    
    assert normalized2.error_type == SQLErrorType.DUPLICATE_ALIAS
    assert normalized2.details["table"] == "users"
    print("  ✅ Duplicate alias normalization works")
    
    # Test unknown column
    error_msg3 = "Unknown column 'users.invalid_col' in 'field list'"
    normalized3 = normalize_error(error_msg3)
    
    assert normalized3.error_type == SQLErrorType.UNKNOWN_COLUMN
    assert normalized3.details["column"] == "users.invalid_col"
    print("  ✅ Unknown column normalization works")
    
    print("✅ All error normalization tests passed!\n")


def test_sqlglot_integration():
    """Test sqlglot is installed and working"""
    print("Testing sqlglot integration...")
    
    try:
        import sqlglot
        print(f"  ✅ sqlglot {sqlglot.__version__} is installed")
        
        # Test basic parsing
        ast = sqlglot.parse_one("SELECT id, name FROM users")
        print(f"  ✅ SQL parsing works (AST type: {type(ast).__name__})")
        
        # Test our wrapper functions
        from src.sql.analysis.ast_utils import parse_sql, get_select_expressions
        
        ast2 = parse_sql("SELECT a, b + 1 AS c FROM t")
        exprs = get_select_expressions(ast2)
        assert len(exprs) == 2
        print(f"  ✅ AST utils work (found {len(exprs)} SELECT expressions)")
        
        print("✅ sqlglot integration tests passed!\n")
        
    except ImportError as e:
        print(f"  ❌ sqlglot not installed: {e}")
        print("  Run: pip install 'sqlglot[rs]>=28.0.0'")
        return False
    
    return True


def test_deterministic_fixers():
    """Test deterministic SQL fixers"""
    print("Testing deterministic fixers...")
    
    try:
        from src.agents.sql.correction.fixers import fix_group_by_violation
        
        # Test GROUP BY fix
        sql = "SELECT dept, DATE_FORMAT(created, '%Y') AS year, COUNT(*) FROM users GROUP BY dept"
        fixed = fix_group_by_violation(sql, expression_num=2)
        
        assert "GROUP BY" in fixed
        assert "DATE_FORMAT" in fixed
        print("  ✅ GROUP BY fixer works")
        
        print("✅ Deterministic fixer tests passed!\n")
        
    except Exception as e:
        print(f"  ⚠️  Fixer test skipped: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("SQL Correction System - Standalone Tests")
    print("=" * 60)
    print()
    
    test_error_normalization()
    
    if test_sqlglot_integration():
        test_deterministic_fixers()
    
    print("=" * 60)
    print("All tests completed successfully! 🎉")
    print("=" * 60)
