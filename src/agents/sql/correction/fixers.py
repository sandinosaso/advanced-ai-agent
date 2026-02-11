"""
Deterministic SQL fixers using sqlglot AST transformations.

These functions fix common SQL errors without LLM involvement:
- GROUP BY violations: Add missing SELECT expressions to GROUP BY
- Duplicate joins: Remove redundant joins to the same table
- Unknown columns: Replace with correct table reference (when unambiguous)

All fixers are pure functions: SQL in, SQL out. No side effects, no LLM calls.
"""

from typing import Optional
from loguru import logger
from sqlglot import exp
from src.sql.analysis.ast_utils import (
    parse_sql,
    get_select_expressions,
    get_group_by_expressions,
    find_duplicate_joins,
)


def fix_group_by_violation(sql: str, expression_num: int, dialect: str = "mysql") -> str:
    """
    Fix GROUP BY violation by adding the missing SELECT expression to GROUP BY.
    
    This is a deterministic fix - no LLM needed. When MySQL says "Expression #N
    is not in GROUP BY", we parse the SELECT clause, get the N-th expression,
    and add it to GROUP BY using AST manipulation.
    
    Args:
        sql: Failed SQL query
        expression_num: Which SELECT expression is missing (1-indexed)
        dialect: SQL dialect (default: "mysql")
        
    Returns:
        Fixed SQL with the expression added to GROUP BY
        
    Raises:
        ValueError: If expression_num is out of range
        sqlglot.errors.ParseError: If SQL is invalid
        
    Example:
        >>> sql = "SELECT id, DATE_FORMAT(created, '%Y') AS year, COUNT(*) FROM users GROUP BY id"
        >>> fixed = fix_group_by_violation(sql, expression_num=2)
        >>> # Result: GROUP BY id, DATE_FORMAT(created, '%Y')
    """
    logger.info(f"Attempting deterministic GROUP BY fix for expression #{expression_num}")
    
    # Parse SQL into AST
    ast = parse_sql(sql, dialect=dialect)
    
    # Get SELECT expressions
    select_exprs = get_select_expressions(ast)
    
    if not (0 < expression_num <= len(select_exprs)):
        raise ValueError(
            f"Expression #{expression_num} out of range (SELECT has {len(select_exprs)} expressions)"
        )
    
    # Get the missing expression (1-indexed in MySQL errors, 0-indexed in list)
    missing_expr = select_exprs[expression_num - 1]
    logger.debug(f"Missing expression: {missing_expr.sql(dialect=dialect)}")
    
    # Find or create GROUP BY clause
    group_by = ast.find(exp.Group)
    
    if group_by:
        # GROUP BY exists - add the missing expression
        # Check if it's already there (shouldn't be, but be safe)
        existing_exprs = list(group_by.expressions)
        missing_sql = missing_expr.sql(dialect=dialect)
        
        already_present = any(
            e.sql(dialect=dialect) == missing_sql for e in existing_exprs
        )
        
        if already_present:
            logger.warning(f"Expression already in GROUP BY: {missing_sql}")
            return sql  # No change needed
        
        # Add the missing expression
        group_by.append("expressions", missing_expr.copy())
        logger.info(f"Added expression to existing GROUP BY: {missing_sql}")
    else:
        # No GROUP BY - create one with the missing expression
        # This is unusual (error usually means GROUP BY exists but is incomplete)
        logger.warning("No GROUP BY found; creating new GROUP BY clause")
        ast.set("group", exp.Group(expressions=[missing_expr.copy()]))
    
    # Convert AST back to SQL
    fixed_sql = ast.sql(dialect=dialect)
    logger.info(f"GROUP BY fix applied successfully")
    return fixed_sql


def fix_duplicate_join(sql: str, duplicate_table: str, dialect: str = "mysql") -> str:
    """
    Fix duplicate join by removing redundant joins to the same table.
    
    Strategy: Keep the first join (usually the shortest path), remove others.
    
    Args:
        sql: Failed SQL query
        duplicate_table: Name of the table joined multiple times
        dialect: SQL dialect (default: "mysql")
        
    Returns:
        Fixed SQL with duplicate joins removed
        
    Example:
        >>> sql = "SELECT * FROM a JOIN b ON a.id = b.id JOIN b AS b2 ON a.x = b2.x"
        >>> fixed = fix_duplicate_join(sql, duplicate_table="b")
        >>> # Result: Only first JOIN to b remains
    """
    logger.info(f"Attempting deterministic duplicate join fix for table '{duplicate_table}'")
    
    # Parse SQL into AST
    ast = parse_sql(sql, dialect=dialect)
    
    # Find duplicate joins
    duplicates = find_duplicate_joins(ast)
    
    # Find the specific duplicate we're fixing
    target_duplicate = None
    for dup in duplicates:
        if dup["table"].lower() == duplicate_table.lower():
            target_duplicate = dup
            break
    
    if not target_duplicate:
        logger.warning(f"No duplicate joins found for table '{duplicate_table}'")
        return sql  # No change needed
    
    # Keep the first join, remove others
    join_nodes = target_duplicate["join_nodes"]
    logger.info(f"Found {len(join_nodes)} joins to '{duplicate_table}', keeping first, removing {len(join_nodes) - 1}")
    
    for join_node in join_nodes[1:]:
        # Remove the join from the AST
        join_node.pop()
        logger.debug(f"Removed duplicate join to '{duplicate_table}'")
    
    # Convert AST back to SQL
    fixed_sql = ast.sql(dialect=dialect)
    logger.info(f"Duplicate join fix applied successfully")
    return fixed_sql
