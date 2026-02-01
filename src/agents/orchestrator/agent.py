"""
Orchestrator Agent - Main LangGraph workflow

Routes questions to SQL, RAG, or General agents.
"""

from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from loguru import logger

from src.agents.sql import SQLGraphAgent
from src.config.settings import settings
from src.llm.client import create_llm

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext
from src.agents.orchestrator.nodes import (
    classify_node,
    execute_sql_node,
    execute_rag_node,
    execute_general_node,
    finalize_node,
)


_shared_agent: Optional["OrchestratorAgent"] = None


def get_orchestrator_agent(checkpointer=None, conversation_db=None, **kwargs) -> "OrchestratorAgent":
    """Get shared orchestrator agent instance (singleton)."""
    global _shared_agent
    if _shared_agent is None or _shared_agent.checkpointer != checkpointer:
        _shared_agent = OrchestratorAgent(
            checkpointer=checkpointer,
            conversation_db=conversation_db,
            **kwargs
        )
    return _shared_agent


def _route_after_classification(state: AgentState) -> str:
    """Determine next node after classification."""
    next_step = state.get("next_step", "general")
    if next_step == "sql":
        return "sql_agent"
    if next_step == "rag":
        return "rag_agent"
    return "general_agent"


class OrchestratorAgent:
    """
    Main orchestrator that routes between SQL, RAG, and General agents.

    Workflow: START → classify → [sql|rag|general] → finalize → END
    """

    def __init__(
        self,
        checkpointer=None,
        conversation_db=None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        self.checkpointer = checkpointer
        self.conversation_db = conversation_db

        self.llm = create_llm(
            model=model,
            temperature=temperature if temperature is not None else settings.orchestrator_temperature,
            max_completion_tokens=settings.max_output_tokens
        )

        sql_agent = SQLGraphAgent() if settings.enable_sql_agent else None
        self.ctx = OrchestratorContext(
            llm=self.llm,
            sql_agent=sql_agent,
            conversation_db=conversation_db
        )

        self.workflow = self._build_workflow()

        agents_enabled = []
        if settings.enable_sql_agent:
            agents_enabled.append("SQL")
        if settings.enable_rag_agent:
            agents_enabled.append("RAG")
        checkpoint_status = "with checkpointing" if checkpointer else "without checkpointing"
        logger.info(
            f"Initialized OrchestratorAgent (Enabled: {', '.join(agents_enabled) or 'None'}, {checkpoint_status})"
        )

    def _build_workflow(self):
        """Build the LangGraph workflow."""
        ctx = self.ctx
        workflow = StateGraph(AgentState)

        workflow.add_node("classify", lambda s: classify_node(s, ctx))
        workflow.add_node("sql_agent", lambda s: execute_sql_node(s, ctx))
        workflow.add_node("rag_agent", lambda s: execute_rag_node(s, ctx))
        workflow.add_node("general_agent", lambda s: execute_general_node(s, ctx))
        workflow.add_node("finalize", lambda s: finalize_node(s, ctx))

        workflow.set_entry_point("classify")
        workflow.add_conditional_edges(
            "classify",
            _route_after_classification,
            {"sql_agent": "sql_agent", "rag_agent": "rag_agent", "general_agent": "general_agent"}
        )
        workflow.add_edge("sql_agent", "finalize")
        workflow.add_edge("rag_agent", "finalize")
        workflow.add_edge("general_agent", "finalize")
        workflow.add_edge("finalize", END)

        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()

    def ask(self, question: str, verbose: bool = True) -> Dict[str, Any]:
        """Ask a question and get routed answer."""
        logger.info(f"\n{'='*80}\nORCHESTRATOR QUESTION: {question}\n{'='*80}")

        initial_state: AgentState = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "next_step": "classify",
            "sql_result": None,
            "sql_structured_result": None,
            "rag_result": None,
            "general_result": None,
            "final_answer": None,
            "final_structured_data": None,
            "query_result_memory": None
        }

        final_state = self.workflow.invoke(initial_state)

        route = "sql" if final_state.get("sql_result") else "rag" if final_state.get("rag_result") else "general"
        result = {
            "question": question,
            "answer": final_state.get("final_answer", "No answer generated"),
            "route": route,
            "sql_result": final_state.get("sql_result"),
            "rag_result": final_state.get("rag_result"),
            "general_result": final_state.get("general_result"),
            "messages": final_state.get("messages", [])
        }

        if verbose:
            logger.info(f"\nRoute taken: {result['route'].upper()}\nAnswer: {result['answer']}\n")
        return result

    def chat(self, question: str) -> str:
        """Simple chat - returns answer string."""
        return self.ask(question, verbose=False)["answer"]

    async def astream_events(self, input_data: dict, config: Optional[dict] = None, version: str = "v1"):
        """Stream events from workflow execution."""
        if config:
            async for event in self.workflow.astream_events(input_data, config=config, version=version):
                yield event
        else:
            async for event in self.workflow.astream_events(input_data, version=version):
                yield event
