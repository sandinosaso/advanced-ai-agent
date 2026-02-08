"""
SQL agent workflow state
"""

from typing import TypedDict, List, Dict, Any, Optional


class SQLGraphState(TypedDict):
    """State for the SQL workflow"""
    question: str
    domain_terms: List[str]
    domain_resolutions: List[Dict[str, Any]]
    tables: List[str]
    allowed_relationships: List[Dict[str, Any]]
    join_plan: str
    sql: str
    result: Optional[str]
    column_names: Optional[List[str]]
    retries: int
    final_answer: Optional[str]
    structured_result: Optional[List[Dict[str, Any]]]
    sql_correction_attempts: int
    last_sql_error: Optional[str]
    correction_history: Optional[List[Dict[str, Any]]]
    validation_errors: Optional[List[str]]
    previous_results: Optional[List[Dict[str, Any]]]
    is_followup: bool
    referenced_ids: Optional[Dict[str, List]]
    referenced_entity: Optional[str]  # e.g. "inspection", "workOrder" - from follow-up detection
    query_resolved: Optional[bool]  # False when we gave up after retries (DB/validation error)
    anchor_table: Optional[str]  # Primary table for FROM clause (workOrder, asset, etc.)
