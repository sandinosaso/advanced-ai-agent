"""
SQL AST utilities using sqlglot for deterministic query analysis and transformation.

This module provides wrapper functions around sqlglot to:
- Parse SQL into an Abstract Syntax Tree (AST)
- Extract and analyze query components (SELECT, GROUP BY, JOINs)
- Enable deterministic SQL transformations without LLM involvement
"""

from typing import List, Dict, Optional
from loguru import logger
import sqlglot
from sqlglot import exp


def parse_sql(sql: str, dialect: str = "mysql") -> exp.Expression:
    """
    Parse SQL into sqlglot AST.
    
    Args:
        sql: SQL query string
        dialect: SQL dialect (default: "mysql")
        
    Returns:
        sqlglot Expression (AST root)
        
    Raises:
        sqlglot.errors.ParseError: If SQL is invalid
        
    Example:
        >>> ast = parse_sql("SELECT id, name FROM users WHERE active = 1")
        >>> print(type(ast))
        <class 'sqlglot.expressions.Select'>
    """
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        logger.debug(f"Parsed SQL into AST: {type(parsed).__name__}")
        return parsed
    except Exception as e:
        logger.error(f"Failed to parse SQL: {e}")
        raise


def get_select_expressions(ast: exp.Expression) -> List[exp.Expression]:
    """
    Extract SELECT expressions as AST nodes.
    
    Args:
        ast: sqlglot Expression (from parse_sql)
        
    Returns:
        List of Expression nodes from the SELECT clause
        
    Example:
        >>> ast = parse_sql("SELECT id, CONCAT(first, last) AS name FROM users")
        >>> exprs = get_select_expressions(ast)
        >>> len(exprs)
        2
        >>> exprs[0].sql()
        'id'
        >>> exprs[1].sql()
        "CONCAT(first, last)"
    """
    if not isinstance(ast, exp.Select):
        logger.warning(f"Expected Select expression, got {type(ast).__name__}")
        return []
    
    expressions = []
    for select_expr in ast.expressions:
        # If it's an Alias (e.g., "col AS alias"), get the underlying expression
        if isinstance(select_expr, exp.Alias):
            expressions.append(select_expr.this)
        else:
            expressions.append(select_expr)
    
    logger.debug(f"Extracted {len(expressions)} SELECT expressions")
    return expressions


def get_group_by_expressions(ast: exp.Expression) -> List[exp.Expression]:
    """
    Extract GROUP BY expressions as AST nodes.
    
    Args:
        ast: sqlglot Expression (from parse_sql)
        
    Returns:
        List of Expression nodes from the GROUP BY clause (empty if no GROUP BY)
        
    Example:
        >>> ast = parse_sql("SELECT dept, COUNT(*) FROM emp GROUP BY dept")
        >>> exprs = get_group_by_expressions(ast)
        >>> len(exprs)
        1
        >>> exprs[0].sql()
        'dept'
    """
    if not isinstance(ast, exp.Select):
        logger.warning(f"Expected Select expression, got {type(ast).__name__}")
        return []
    
    group_by = ast.find(exp.Group)
    if not group_by:
        logger.debug("No GROUP BY clause found")
        return []
    
    expressions = list(group_by.expressions)
    logger.debug(f"Extracted {len(expressions)} GROUP BY expressions")
    return expressions


def get_table_name_from_join(join_node: exp.Join) -> Optional[str]:
    """
    Extract table name from a JOIN node.
    
    Args:
        join_node: sqlglot Join expression
        
    Returns:
        Table name as string, or None if not found
        
    Example:
        >>> ast = parse_sql("SELECT * FROM a JOIN b ON a.id = b.id")
        >>> joins = list(ast.find_all(exp.Join))
        >>> get_table_name_from_join(joins[0])
        'b'
    """
    if not isinstance(join_node, exp.Join):
        return None
    
    # The joined table is in join_node.this
    table_expr = join_node.this
    
    if isinstance(table_expr, exp.Table):
        return table_expr.name
    elif isinstance(table_expr, exp.Alias):
        # If aliased, get the underlying table
        if isinstance(table_expr.this, exp.Table):
            return table_expr.this.name
    
    return None


def find_duplicate_joins(ast: exp.Expression) -> List[Dict[str, any]]:
    """
    Find tables that are joined multiple times in the query.
    
    Args:
        ast: sqlglot Expression (from parse_sql)
        
    Returns:
        List of dicts with duplicate join info:
        [{"table": "users", "count": 2, "join_nodes": [node1, node2]}]
        
    Example:
        >>> sql = "SELECT * FROM a JOIN b ON a.id = b.id JOIN b AS b2 ON a.x = b2.x"
        >>> ast = parse_sql(sql)
        >>> dupes = find_duplicate_joins(ast)
        >>> dupes[0]["table"]
        'b'
        >>> dupes[0]["count"]
        2
    """
    if not isinstance(ast, exp.Select):
        logger.warning(f"Expected Select expression, got {type(ast).__name__}")
        return []
    
    # Find all JOIN nodes
    joins = list(ast.find_all(exp.Join))
    
    # Count joins per table
    table_joins = {}
    for join in joins:
        table_name = get_table_name_from_join(join)
        if table_name:
            if table_name not in table_joins:
                table_joins[table_name] = []
            table_joins[table_name].append(join)
    
    # Find duplicates (count > 1)
    duplicates = []
    for table, join_nodes in table_joins.items():
        if len(join_nodes) > 1:
            duplicates.append({
                "table": table,
                "count": len(join_nodes),
                "join_nodes": join_nodes
            })
            logger.debug(f"Found {len(join_nodes)} joins to table '{table}'")
    
    return duplicates
