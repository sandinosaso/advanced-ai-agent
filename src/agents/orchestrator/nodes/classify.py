"""
Classify node - routes question to SQL, RAG, or General agent
"""

from langchain_core.messages import HumanMessage, AIMessage

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext, truncate_messages_if_needed
from src.agents.orchestrator.routing import classify_question


def classify_node(state: AgentState, ctx: OrchestratorContext) -> AgentState:
    """Classify question and set next_step for routing."""
    question = state["question"]
    messages = state.get("messages", [])

    # Ensure current question is in messages
    if not messages:
        state = dict(state)
        state["messages"] = [HumanMessage(content=question)]
    else:
        last_msg = messages[-1]
        if not (isinstance(last_msg, HumanMessage) and last_msg.content == question):
            state = dict(state)
            state["messages"] = list(state["messages"]) + [HumanMessage(content=question)]

    state = truncate_messages_if_needed(state, ctx)
    messages = state.get("messages", [])

    classification = classify_question(question, messages, ctx)

    state = dict(state)
    state["next_step"] = classification
    state["messages"] = list(state["messages"]) + [
        AIMessage(content=f"Routing to {classification.upper()} agent...")
    ]

    return state
