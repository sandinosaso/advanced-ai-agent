"""
General agent node - executes general knowledge questions
"""

from langchain_core.messages import AIMessage
from loguru import logger

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext, truncate_messages_if_needed


def execute_general_node(state: AgentState, ctx: OrchestratorContext) -> AgentState:
    """Execute general agent for questions that don't require SQL or RAG."""
    state = truncate_messages_if_needed(state, ctx)
    question = state["question"]
    state = dict(state)

    general_agent = getattr(ctx, "general_agent", None)
    if general_agent is None:
        from src.agents.general.agent import GeneralAgent
        general_agent = GeneralAgent(llm=ctx.llm)
        ctx.general_agent = general_agent

    logger.info(f"Executing general agent for: '{question}'")

    try:
        messages = state.get("messages", [])
        logger.info(f"General agent received {len(messages)} messages in conversation history")
        if messages:
            logger.debug(f"Message types: {[type(m).__name__ for m in messages]}")
            logger.debug(f"Last 3 messages: {[m.content[:100] if hasattr(m, 'content') else str(m)[:100] for m in messages[-3:]]}")
        answer = general_agent.answer(question=question, messages=messages)
        state["general_result"] = answer
        state["messages"] = list(state.get("messages", [])) + [
            AIMessage(content=f"General Answer: {answer}")
        ]
        state["next_step"] = "finalize"
    except Exception as e:
        logger.error(f"General agent error: {e}")
        state["general_result"] = f"Error: {str(e)}"
        state["next_step"] = "finalize"

    return state
