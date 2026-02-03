"""
SQL agent node - executes database queries
"""

from langchain_core.messages import AIMessage

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext
from src.config.settings import settings
from src.memory.query_memory import QueryResultMemory
from loguru import logger


def execute_sql_node(state: AgentState, ctx: OrchestratorContext) -> AgentState:
    """Execute SQL agent for database queries."""
    question = state["question"]
    state = dict(state)

    if not settings.enable_sql_agent:
        logger.info("SQL agent is disabled")
        state["sql_result"] = "🔧 SQL Agent is not enabled. Please enable it via ENABLE_SQL_AGENT=true in your .env file."
        state["sql_structured_result"] = None
        state["messages"] = list(state.get("messages", [])) + [AIMessage(content=state["sql_result"])]
        state["next_step"] = "finalize"
        return state

    if ctx.sql_agent is None:
        state["sql_result"] = "Error: SQL agent was not initialized"
        state["sql_structured_result"] = None
        state["next_step"] = "finalize"
        return state

    logger.info(f"Executing SQL agent for: '{question}'")

    try:
        previous_results = state.get("query_result_memory")
        result = ctx.sql_agent.query_with_structured(
            question=question,
            previous_results=previous_results
        )
        state["sql_result"] = result["answer"]
        state["sql_structured_result"] = result.get("structured_result")
        state["messages"] = list(state.get("messages", [])) + [
            AIMessage(content=f"SQL Result: {result['answer']}")
        ]
        state["next_step"] = "finalize"

        if result.get("structured_result"):
            if previous_results:
                memory = QueryResultMemory.from_dict(
                    previous_results,
                    max_results=settings.query_result_memory_size
                )
            else:
                memory = QueryResultMemory(max_results=settings.query_result_memory_size)
            memory.add_result(
                question=question,
                structured_data=result["structured_result"],
                sql_query=result.get("sql_query"),
                tables_used=result.get("tables_used")
            )
            state["query_result_memory"] = memory.to_dict()
            logger.info(f"Stored query result in memory: {len(memory)} results total")

    except Exception as e:
        logger.error(f"SQL agent error: {e}")
        state["sql_result"] = f"Error: {str(e)}"
        state["sql_structured_result"] = None
        state["next_step"] = "finalize"

    return state
