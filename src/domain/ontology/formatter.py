"""
Domain context formatting for prompts

Formats domain resolutions into human-readable context for LLM prompts.
"""

from typing import Dict, Any, List


def format_domain_context_for_table_selection(resolutions: List[Dict[str, Any]]) -> str:
    """
    Format domain resolutions for table selection prompt (tables only, no filters).
    
    This lightweight version only shows required tables to avoid token bloat.
    Filters are injected later in SQL generation where they're actually used.
    
    Args:
        resolutions: List of resolved domain terms (as dicts)
        
    Returns:
        Formatted string for table selection prompt
    """
    if not resolutions:
        return ""
    
    lines = ["Domain Context (business concepts mapped to schema):"]
    lines.append("=" * 70)
    
    for res in resolutions:
        lines.append(f"\nConcept: '{res['term']}' ({res['entity']})")
        lines.append(f"  Tables needed: {', '.join(res['tables'])}")
        lines.append(f"  Confidence: {res['confidence']} (strategy: {res['strategy']})")
    
    lines.append("=" * 70)
    return "\n".join(lines)


def format_domain_context(resolutions: List[Dict[str, Any]]) -> str:
    """
    Format domain resolutions into human-readable context for prompts.
    
    Used to inject domain understanding into join planning and SQL generation prompts.
    Includes both tables and filters.
    
    Args:
        resolutions: List of resolved domain terms (as dicts)
        
    Returns:
        Formatted string for prompt injection
    """
    if not resolutions:
        return ""
    
    lines = ["Domain Context (business concepts mapped to schema):"]
    lines.append("=" * 70)
    
    for res in resolutions:
        lines.append(f"\nConcept: '{res['term']}' ({res['entity']})")
        lines.append(f"  Tables needed: {', '.join(res['tables'])}")
        
        # Only show filters if they exist (structural matches have no filters)
        if res['filters']:
            lines.append(f"  Filters to apply:")
            for f in res['filters']:
                # Show LOWER() wrapper if case-insensitive
                if f.get("case_insensitive"):
                    column_ref = f"LOWER({f['table']}.{f['column']})"
                else:
                    column_ref = f"{f['table']}.{f['column']}"
                
                if f.get("match_type") == "boolean":
                    lines.append(f"    - {column_ref} {f['operator']} {f['value']}")
                else:
                    lines.append(f"    - {column_ref} {f['operator']} '{f['value']}'")
        else:
            lines.append(f"  Note: Structural grouping (no filters needed)")
        
        lines.append(f"  Confidence: {res['confidence']} (strategy: {res['strategy']})")
    
    lines.append("=" * 70)
    return "\n".join(lines)


def build_where_clauses(resolutions: List[Dict[str, Any]]) -> List[str]:
    """
    Build SQL WHERE clause fragments from domain resolutions.
    
    Args:
        resolutions: List of resolved domain terms (as dicts)
        
    Returns:
        List of WHERE clause strings to be AND'd together
        
    Example:
        [
            "assetType.name ILIKE '%crane%'",
            "inspectionQuestionAnswer.isActionItem = true"
        ]
    """
    where_clauses = []
    
    for res in resolutions:
        # Group OR conditions together
        or_conditions = []
        and_conditions = []
        
        for f in res['filters']:
            table = f['table']
            column = f['column']
            operator = f['operator']
            value = f['value']
            
            # Format value based on type
            if isinstance(value, bool):
                value_str = "true" if value else "false"
            elif isinstance(value, str):
                value_str = f"'{value}'"
            else:
                value_str = str(value)
            
            # Apply case-insensitive matching if specified
            if f.get("case_insensitive"):
                column_ref = f"LOWER({table}.{column})"
            else:
                column_ref = f"{table}.{column}"
            
            clause = f"{column_ref} {operator} {value_str}"
            
            if f.get("or_condition"):
                or_conditions.append(clause)
            else:
                and_conditions.append(clause)
        
        # Add OR conditions as a group
        if or_conditions:
            if len(or_conditions) == 1:
                where_clauses.append(or_conditions[0])
            else:
                where_clauses.append(f"({' OR '.join(or_conditions)})")
        
        # Add AND conditions individually
        where_clauses.extend(and_conditions)
    
    return where_clauses
