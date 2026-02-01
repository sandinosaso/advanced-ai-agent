"""
Orchestrator formatter - final answer preparation
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage

from src.agents.orchestrator.state import AgentState


def finalize_answer(state: AgentState, llm) -> AgentState:
    """
    Finalize the answer and prepare for return.

    For SQL results, we pass through the already-formatted answer with minimal LLM processing.
    This enables streaming while avoiding regeneration/duplication.

    Also preserves structured_data for BFF markdown conversion.
    """
    if state.get("sql_result"):
        raw_answer = state["sql_result"]
        state["final_structured_data"] = state.get("sql_structured_result")
    elif state.get("rag_result"):
        raw_answer = state["rag_result"]
        state["final_structured_data"] = None
    elif state.get("general_result"):
        raw_answer = state["general_result"]
        state["final_structured_data"] = None
    else:
        raw_answer = "I couldn't find an answer to your question."
        state["final_structured_data"] = None

    finalize_prompt = f"""Return the following answer exactly as provided:

{raw_answer}"""

    final_response = llm.invoke(finalize_prompt)
    final_answer = final_response.content

    state["final_answer"] = final_answer
    state["messages"] = list(state.get("messages", [])) + [AIMessage(content=final_answer)]
    state["next_step"] = "end"

    return state
