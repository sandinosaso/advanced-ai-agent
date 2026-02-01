"""
Join plan parsing utilities
"""

import re
from typing import List, Set


def extract_tables_from_join_plan(join_plan: str, join_graph_tables: dict) -> set:
    """
    Extract table names mentioned in the join plan.
    """
    tables = set()
    join_path_match = re.search(
        r"JOIN_PATH:.*?(?=NOTES:|$)", join_plan, re.IGNORECASE | re.DOTALL
    )
    if not join_path_match:
        join_path_match = re.search(
            r"(?:JOIN_PATH:.*?)?(-.*?)(?=NOTES:|$)", join_plan, re.IGNORECASE | re.DOTALL
        )
    join_path_text = join_path_match.group(0) if join_path_match else join_plan

    pattern = (
        r"(?:^|\n)\s*[-•]\s*([a-zA-Z_][a-zA-Z0-9_]*)\.[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*"
        r"([a-zA-Z_][a-zA-Z0-9_]*)\.[a-zA-Z_][a-zA-Z0-9_]*"
    )
    matches = re.finditer(pattern, join_path_text, re.IGNORECASE | re.MULTILINE)
    skip_words = {"the", "a", "an", "and", "or", "path", "connects", "joins"}
    for match in matches:
        table1, table2 = match.group(1), match.group(2)
        if table1.lower() not in skip_words:
            tables.add(table1)
        if table2.lower() not in skip_words:
            tables.add(table2)

    valid_tables = set()
    for table in tables:
        if table in join_graph_tables:
            valid_tables.add(table)
        else:
            for known_table in join_graph_tables.keys():
                if table.lower() == known_table.lower():
                    valid_tables.add(known_table)
                    break
    return valid_tables


def parse_join_path_steps(join_plan: str) -> List[str]:
    """
    Parse JOIN_PATH section to extract explicit join steps.
    """
    steps = []
    join_path_match = re.search(
        r"JOIN_PATH:.*?(?=NOTES:|$)", join_plan, re.IGNORECASE | re.DOTALL
    )
    if not join_path_match:
        return steps
    join_path_text = join_path_match.group(0)
    pattern = (
        r"[-•]\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"
        r"([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)"
    )
    matches = re.finditer(pattern, join_path_text, re.IGNORECASE)
    for match in matches:
        left_side = match.group(1)
        right_side = match.group(2)
        steps.append(f"{left_side} = {right_side}")
    return steps
