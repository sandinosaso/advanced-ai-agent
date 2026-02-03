"""
Finalize node - prepares final answer for return
"""

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext
from src.agents.orchestrator.formatter import finalize_answer


def finalize_node(state: AgentState, ctx: OrchestratorContext) -> AgentState:
    """Finalize answer and prepare for return."""
    return finalize_answer(state, ctx.llm)
