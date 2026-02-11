"""
Tests for SQL correction node.

The simplified correction agent relies on the actual MySQL error message
being passed to the LLM (no hardcoded handling per error type). These tests
verify the prompt structure and that the implementation is in place.

Manual testing: After deploying, re-run a query that previously failed with
e.g. GROUP BY error (only_full_group_by) or unknown column; the correction
agent should receive the full error and fix the query. Legacy implementation
is available as correct_sql_node_legacy if you need to revert.
"""

import re
from pathlib import Path


def test_correction_module_has_simplified_prompt_structure():
    """Simplified correct_sql_node prompt must include raw error and failed SQL."""
    root = Path(__file__).resolve().parent.parent
    path = root / "src" / "agents" / "sql" / "nodes" / "correction.py"
    with open(path, "r") as f:
        content = f.read()
    # New prompt uses these exact labels so the LLM sees the real error
    assert "ERROR MESSAGE:" in content, "Prompt should pass through the actual error"
    assert "FAILED SQL:" in content, "Prompt should include the failed query"
    assert "COMMON ERROR PATTERNS" in content, "Static hints should be present"
    assert "correct_sql_node_legacy" in content, "Legacy backup should exist"


def test_common_error_patterns_are_static_hints():
    """Common patterns are hints only, not conditional on error type."""
    root = Path(__file__).resolve().parent.parent
    path = root / "src" / "agents" / "sql" / "nodes" / "correction.py"
    with open(path, "r") as f:
        content = f.read()
    # Extract the constant
    start = content.find('_COMMON_ERROR_PATTERNS = """')
    end = content.find('"""', start + len('_COMMON_ERROR_PATTERNS = """') + 1) + 3
    block = content[start:end]
    assert "GROUP BY" in block
    assert "Unknown column" in block or "unknown column" in block.lower()
    assert "Duplicate table" in block or "Duplicate" in block
    assert "Missing table" in block or "required JOIN" in block
