"""
Orchestrator Agent - Main LangGraph workflow for Phase 4

This is the primary agent that routes questions to:
- SQL Agent (database queries, statistics, calculations)
- RAG Agent (policies, compliance, handbook questions)

Uses LangGraph to create a stateful workflow with intelligent routing.
"""

from typing import Annotated, TypedDict, Dict, Any, Sequence, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from loguru import logger

from src.agents.sql_graph_agent import SQLGraphAgent
from src.agents.rag_agent import RAGAgent
from src.utils.config import settings, create_llm


class AgentState(TypedDict):
    """State for the orchestrator workflow"""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    question: str
    next_step: str
    sql_result: str | None
    sql_structured_result: List[Dict[str, Any]] | None  # Structured array from SQL agent for BFF
    rag_result: str | None
    final_answer: str | None
    final_structured_data: List[Dict[str, Any]] | None  # Structured data for final answer (BFF markdown)


class OrchestratorAgent:
    """
    Main orchestrator that routes between SQL and RAG agents
    
    Workflow:
    1. Receive question
    2. Classify question type (SQL vs RAG)
    3. Route to appropriate agent
    4. Generate final answer
    5. Return to user
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        Initialize orchestrator
        
        Args:
            model: LLM model for routing decisions (defaults to provider-specific model)
            temperature: Generation temperature (defaults to settings.orchestrator_temperature)
        """
        self.llm = create_llm(
            model=model,
            temperature=temperature if temperature is not None else settings.orchestrator_temperature,
            max_completion_tokens=settings.max_output_tokens
        )
        
        # Lazy initialization - only create agents if enabled
        self.sql_agent = SQLGraphAgent() if settings.enable_sql_agent else None
        self.rag_agent = None  # Will be initialized lazily when needed
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
        # Log agent status
        agents_enabled = []
        if settings.enable_sql_agent:
            agents_enabled.append("SQL")
        if settings.enable_rag_agent:
            agents_enabled.append("RAG")
        logger.info(f"Initialized OrchestratorAgent with LangGraph workflow (Enabled: {', '.join(agents_enabled) if agents_enabled else 'None'})")
    
    def _classify_question(self, state: AgentState) -> AgentState:
        """
        Classify question to determine routing
        
        SQL questions: statistics, counts, calculations, data queries
        RAG questions: policies, procedures, compliance, rules
        """
        question = state["question"]
        
        classification_prompt = f"""Classify this question as either "SQL" or "RAG".

**SQL** - Use when the question asks about:
- Specific data, numbers, counts, statistics, calculations
- Current database state ("how many", "which", "show me", "list all")
- Work logs, expenses, jobs, technicians, schedules that exist in the database
- Filtering or aggregating existing records

SQL Examples:
- "How many technicians are in the database?"
- "What is the total amount of approved expenses?"
- "Which jobs are currently in progress?"
- "Show me work logs from last week"
- "List all technicians with HVAC skills"

**RAG** - Use when the question asks about:
- Company policies, rules, procedures, guidelines
- Compliance requirements, safety regulations
- How-to information from handbooks or documentation
- General knowledge about company practices
- Definitions or explanations of policies

RAG Examples:
- "What are the overtime rules?"
- "What safety equipment is required for electrical work?"
- "How do I submit expense reports?"
- "What is the company PTO policy?"
- "What are OSHA lockout/tagout requirements?"
- "Explain the meal break policy"

IMPORTANT: If asking about RULES or POLICIES, choose RAG even if it mentions data.
If asking for CURRENT DATA or STATISTICS, choose SQL.

Question: {question}

Respond with ONLY one word: SQL or RAG"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=classification_prompt)])
            classification = str(response.content).strip().upper() if hasattr(response, 'content') and response.content else "RAG"
        except Exception as e:
            error_msg = str(e)
            # Check for common Ollama errors
            if "404" in error_msg or "not found" in error_msg.lower() or "model" in error_msg.lower():
                from src.utils.config import settings
                if settings.llm_provider == "ollama":
                    raise ValueError(
                        f"Ollama model '{settings.ollama_model}' is not available. "
                        f"Please run: ollama pull {settings.ollama_model}"
                    ) from e
            # Re-raise other errors
            raise
        
        # Validate classification
        if classification not in ["SQL", "RAG"]:
            logger.warning(f"Invalid classification '{classification}', defaulting to RAG")
            classification = "RAG"
        
        logger.info(f"Question classified as: {classification}")
        
        state["next_step"] = classification.lower()
        state["messages"].append(AIMessage(content=f"Routing to {classification} agent..."))
        
        return state
    
    def _execute_sql_agent(self, state: AgentState) -> AgentState:
        """Execute SQL agent for database queries"""
        question = state["question"]
        
        # Check if SQL agent is enabled
        if not settings.enable_sql_agent:
            logger.info(f"SQL agent is disabled, returning disabled message")
            state["sql_result"] = "🔧 SQL Agent is not enabled. Please enable it via ENABLE_SQL_AGENT=true in your .env file."
            state["sql_structured_result"] = None
            state["messages"].append(AIMessage(content=state["sql_result"]))
            state["next_step"] = "finalize"
            return state
        
        # Type guard: sql_agent is guaranteed to be not None here
        if self.sql_agent is None:
            state["sql_result"] = "Error: SQL agent was not initialized"
            state["sql_structured_result"] = None
            state["next_step"] = "finalize"
            return state
        
        logger.info(f"Executing SQL agent for: '{question}'")
        
        try:
            # Get both answer and structured data
            result = self.sql_agent.query_with_structured(question)
            state["sql_result"] = result["answer"]
            state["sql_structured_result"] = result.get("structured_result")
            state["messages"].append(AIMessage(content=f"SQL Result: {result['answer']}"))
            state["next_step"] = "finalize"
        except Exception as e:
            logger.error(f"SQL agent error: {e}")
            state["sql_result"] = f"Error: {str(e)}"
            state["sql_structured_result"] = None
            state["next_step"] = "finalize"
        
        return state
    
    def _execute_rag_agent(self, state: AgentState) -> AgentState:
        """Execute RAG agent for handbook/compliance questions"""
        question = state["question"]
        
        # Check if RAG agent is enabled
        if not settings.enable_rag_agent:
            logger.info(f"RAG agent is disabled, returning disabled message")
            state["rag_result"] = "📚 RAG Agent is not enabled. Please enable it via ENABLE_RAG_AGENT=true in your .env file."
            state["messages"].append(AIMessage(content=state["rag_result"]))
            state["next_step"] = "finalize"
            return state
        
        # Lazy initialization of RAG agent (only when needed and enabled)
        # This prevents HF Hub downloads when RAG is disabled
        if self.rag_agent is None:
            logger.info("Lazy initializing RAG agent (this may download models from Hugging Face Hub if using Ollama)")
            self.rag_agent = RAGAgent()
        
        logger.info(f"Executing RAG agent for: '{question}'")
        
        try:
            response = self.rag_agent.answer(question, collection="all", k=5)
            state["rag_result"] = response.answer
            state["messages"].append(AIMessage(content=f"RAG Answer: {response.answer}"))
            state["next_step"] = "finalize"
        except Exception as e:
            logger.error(f"RAG agent error: {e}")
            state["rag_result"] = f"Error: {str(e)}"
            state["next_step"] = "finalize"
        
        return state
    
    def _finalize_answer(self, state: AgentState) -> AgentState:
        """
        Finalize the answer and prepare for return
        
        For SQL results, we pass through the already-formatted answer with minimal LLM processing.
        This enables streaming while avoiding regeneration/duplication.
        
        Also preserves structured_data for BFF markdown conversion.
        """
        
        # Determine which result to use
        if state.get("sql_result"):
            raw_answer = state["sql_result"]
            # Preserve structured data from SQL agent for BFF
            state["final_structured_data"] = state.get("sql_structured_result")
        elif state.get("rag_result"):
            raw_answer = state["rag_result"]
            state["final_structured_data"] = None  # RAG doesn't have structured data
        else:
            raw_answer = "I couldn't find an answer to your question."
            state["final_structured_data"] = None
        
        # Use a minimal prompt to enable streaming without regenerating content
        # The LLM will just pass through the answer, allowing it to stream to the final channel
        finalize_prompt = f"""Return the following answer exactly as provided:

{raw_answer}"""
        
        # Call LLM to enable streaming (this will stream to the final channel)
        final_response = self.llm.invoke(finalize_prompt)
        final_answer = final_response.content
        
        state["final_answer"] = final_answer
        state["messages"].append(AIMessage(content=final_answer))
        state["next_step"] = "end"
        
        return state
    
    def _route_after_classification(self, state: AgentState) -> str:
        """Determine next node after classification"""
        next_step = state.get("next_step", "rag")
        
        if next_step == "sql":
            return "sql_agent"
        else:
            return "rag_agent"
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow
        
        Graph structure:
        START → classify → [sql_agent OR rag_agent] → finalize → END
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify", self._classify_question)
        workflow.add_node("sql_agent", self._execute_sql_agent)
        workflow.add_node("rag_agent", self._execute_rag_agent)
        workflow.add_node("finalize", self._finalize_answer)
        
        # Add edges
        workflow.set_entry_point("classify")
        
        # Conditional routing after classification
        workflow.add_conditional_edges(
            "classify",
            self._route_after_classification,
            {
                "sql_agent": "sql_agent",
                "rag_agent": "rag_agent"
            }
        )
        
        # Both agents go to finalize
        workflow.add_edge("sql_agent", "finalize")
        workflow.add_edge("rag_agent", "finalize")
        
        # Finalize goes to END
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def ask(self, question: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Ask a question and get routed answer
        
        Args:
            question: User question
            verbose: Whether to log workflow steps
        
        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"ORCHESTRATOR QUESTION: {question}")
        logger.info(f"{'='*80}")
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "next_step": "classify",
            "sql_result": None,
            "sql_structured_result": None,
            "rag_result": None,
            "final_answer": None,
            "final_structured_data": None
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Extract results
        result = {
            "question": question,
            "answer": final_state.get("final_answer", "No answer generated"),
            "route": "sql" if final_state.get("sql_result") else "rag",
            "sql_result": final_state.get("sql_result"),
            "rag_result": final_state.get("rag_result"),
            "messages": final_state.get("messages", [])
        }
        
        if verbose:
            logger.info(f"\nRoute taken: {result['route'].upper()}")
            logger.info(f"Answer: {result['answer']}\n")
        
        return result
    
    def chat(self, question: str) -> str:
        """
        Simple chat interface - just returns the answer
        
        Args:
            question: User question
        
        Returns:
            Answer string
        """
        result = self.ask(question, verbose=False)
        return result["answer"]
    
    async def astream_events(self, input_data: dict, version: str = "v1"):
        """
        Stream events from the LangGraph workflow execution
        
        This is a convenience wrapper around the workflow's astream_events method,
        designed for use with FastAPI streaming endpoints.
        
        Args:
            input_data: Initial state for the workflow (must match AgentState structure)
            version: Stream events API version (default: "v1")
        
        Yields:
            Event dictionaries from the workflow execution
            
        Example:
            ```python
            async for event in agent.astream_events(
                {"question": "How many technicians?", "messages": [], ...},
                version="v1"
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    print(chunk.content)
            ```
        """
        async for event in self.workflow.astream_events(input_data, version=version):
            yield event

