"""
Orchestrator workflow state
"""

from typing import Annotated, TypedDict, Dict, Any, Sequence, List

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State for the orchestrator workflow"""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    question: str
    next_step: str
    sql_result: str | None
    sql_structured_result: List[Dict[str, Any]] | None  # Structured array from SQL agent for BFF
    rag_result: str | None
    general_result: str | None  # General LLM response for non-SQL/non-RAG questions
    final_answer: str | None
    final_structured_data: List[Dict[str, Any]] | None  # Structured data for final answer (BFF markdown)
    query_result_memory: List[Dict[str, Any]] | None  # Memory of recent query results for follow-ups
