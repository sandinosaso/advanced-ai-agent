"""
RAG agent node - executes system usage/document questions
"""

from langchain_core.messages import AIMessage
from loguru import logger

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext
from src.agents.rag.agent import RAGAgent
from src.config.settings import settings


def execute_rag_node(state: AgentState, ctx: OrchestratorContext) -> AgentState:
    """Execute RAG agent for system usage questions."""
    question = state["question"]
    state = dict(state)

    if not settings.enable_rag_agent:
        logger.info("RAG agent is disabled")
        state["rag_result"] = "📚 RAG Agent is not enabled. Please enable it via ENABLE_RAG_AGENT=true in your .env file."
        state["messages"] = list(state.get("messages", [])) + [AIMessage(content=state["rag_result"])]
        state["next_step"] = "finalize"
        return state

    # Lazy init RAG agent from context (stored on ctx by agent.py)
    rag_agent = getattr(ctx, "rag_agent", None)
    if rag_agent is None:
        logger.info("Lazy initializing RAG agent")
        rag_agent = RAGAgent()
        ctx.rag_agent = rag_agent

    logger.info(f"Executing RAG agent for: '{question}'")

    try:
        response = rag_agent.answer(question, collection="all", k=5)
        state["rag_result"] = response.answer
        state["messages"] = list(state.get("messages", [])) + [
            AIMessage(content=f"RAG Answer: {response.answer}")
        ]
        state["next_step"] = "finalize"
    except Exception as e:
        logger.error(f"RAG agent error: {e}")
        state["rag_result"] = f"Error: {str(e)}"
        state["next_step"] = "finalize"

    return state
