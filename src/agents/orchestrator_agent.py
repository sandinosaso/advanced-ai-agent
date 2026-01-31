"""
Orchestrator Agent - Main LangGraph workflow for Phase 4

This is the primary agent that routes questions to:
- SQL Agent (database queries, statistics, calculations)
- RAG Agent (system usage questions, how-to guides from user manual)
- General Agent (general questions that don't require SQL or RAG)

Uses LangGraph to create a stateful workflow with intelligent three-way routing.
"""

from typing import Annotated, TypedDict, Dict, Any, Sequence, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from loguru import logger

from src.agents.sql_graph_agent import SQLGraphAgent
from src.agents.rag_agent import RAGAgent
from src.utils.config import settings, create_llm

# Module-level agent instance (reused across requests)
_shared_agent: Optional['OrchestratorAgent'] = None


def get_orchestrator_agent(checkpointer=None, conversation_db=None, **kwargs) -> 'OrchestratorAgent':
    """
    Get shared agent instance (singleton pattern)
    
    Args:
        checkpointer: LangGraph checkpointer instance
        conversation_db: ConversationDatabase instance for message truncation
        **kwargs: Additional arguments passed to OrchestratorAgent
        
    Returns:
        Shared OrchestratorAgent instance
    """
    global _shared_agent
    if _shared_agent is None or _shared_agent.checkpointer != checkpointer:
        _shared_agent = OrchestratorAgent(
            checkpointer=checkpointer,
            conversation_db=conversation_db,
            **kwargs
        )
    return _shared_agent


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


class OrchestratorAgent:
    """
    Main orchestrator that routes between SQL, RAG, and General agents
    
    Workflow:
    1. Receive question
    2. Classify question type (SQL vs RAG vs GENERAL)
    3. Route to appropriate agent
    4. Generate final answer
    5. Return to user
    """
    
    def __init__(
        self,
        checkpointer=None,
        conversation_db=None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        Initialize orchestrator
        
        Args:
            checkpointer: LangGraph checkpointer instance for state persistence
            conversation_db: ConversationDatabase instance for message truncation
            model: LLM model for routing decisions (defaults to provider-specific model)
            temperature: Generation temperature (defaults to settings.orchestrator_temperature)
        """
        self.checkpointer = checkpointer
        self.conversation_db = conversation_db  # For message truncation only
        
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
        checkpoint_status = "with checkpointing" if checkpointer else "without checkpointing"
        logger.info(f"Initialized OrchestratorAgent with LangGraph workflow (Enabled: {', '.join(agents_enabled) if agents_enabled else 'None'}, {checkpoint_status})")
    
    def _truncate_messages_if_needed(self, state: AgentState) -> AgentState:
        """Truncate messages before LLM calls to respect token limits"""
        messages = state.get("messages", [])
        if self.conversation_db and len(messages) > settings.max_conversation_messages:
            strategy = settings.conversation_memory_strategy
            truncated = self.conversation_db.prepare_messages_for_context(messages, strategy)
            state["messages"] = truncated
        return state
    
    def _classify_question(self, state: AgentState) -> AgentState:
        """
        Classify question to determine routing
        
        Three-way classification:
        - SQL: Database queries requiring data retrieval
        - RAG: System usage questions requiring user manual retrieval
        - GENERAL: General questions that can be answered directly by LLM
        """
        question = state["question"]
        
        # Handle messages - ensure current question is present
        # Messages should already include checkpoint messages + new message (loaded in chat route)
        # But we verify current question is present as defensive programming
        messages = state.get("messages", [])
        
        # Ensure current question is in messages (defensive check)
        if not messages:
            # No messages - first message
            state["messages"] = [HumanMessage(content=question)]
        else:
            # Check if current question is already the last message
            last_msg = messages[-1]
            if not (isinstance(last_msg, HumanMessage) and last_msg.content == question):
                # Current question not present - add it (shouldn't happen, but defensive)
                messages = list(messages)
                messages.append(HumanMessage(content=question))
                state["messages"] = messages
            # Else: current question already present, use as-is
        
        # Truncate messages before LLM call (defensive)
        state = self._truncate_messages_if_needed(state)
        
        # Build context from recent messages to understand follow-ups
        recent_context = ""
        messages = state.get("messages", [])
        if len(messages) > 1:
            # Get last few message pairs to understand context
            recent_messages = messages[-4:] if len(messages) > 4 else messages[:-1]
            context_parts = []
            for msg in recent_messages:
                if isinstance(msg, HumanMessage):
                    context_parts.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    # Only include routing messages or short responses to avoid token bloat
                    content = msg.content
                    if "Routing to" in content or "agent" in content.lower():
                        context_parts.append(f"Assistant: {content}")
                    elif len(content) < 100:
                        context_parts.append(f"Assistant: {content}")
            
            if context_parts:
                recent_context = "\n\nRecent conversation context:\n" + "\n".join(context_parts[-4:]) + "\n"
        
        # Build business domain vocabulary from join graph (cached for performance)
        if not hasattr(self, '_business_entities_cache'):
            try:
                # Dynamically load from SQL agent's join graph if available
                if self.sql_agent and hasattr(self.sql_agent, 'join_graph'):
                    all_tables = list(self.sql_agent.join_graph.get("tables", {}).keys())
                    # Filter out system tables and take most common business entities
                    business_tables = [t for t in all_tables if t not in ['SequelizeMeta', 'deletedEntity', 'syncLog', 'pdfCounter', 'pdfIdentifier', 'authenticationToken']]
                    # Take top 30 most common/recognizable entities to avoid token bloat
                    priority_entities = [
                        "asset", "assetType", "crew", "customer", "employee", "equipment", 
                        "expense", "expenseType", "inspection", "inspectionTemplate", "jobType", 
                        "quote", "service", "serviceLocation", "serviceTemplate",
                        "workOrder", "workOrderStatus", "workTime", "payroll", "safety", 
                        "attachment", "attachmentType", "note", "nonJobTime"
                    ]
                    # Keep priority entities that exist + add other business entities
                    existing_priority = [e for e in priority_entities if e in business_tables]
                    other_entities = [t for t in business_tables if t not in priority_entities][:10]
                    self._business_entities_cache = existing_priority + other_entities
                else:
                    # Fallback to curated list if SQL agent not available
                    self._business_entities_cache = [
                        "asset", "assetType", "crew", "customer", "employee", "equipment", 
                        "expense", "inspection", "job", "quote", "service", "serviceLocation",
                        "workOrder", "workTime", "payroll", "safety", "attachment"
                    ]
            except Exception as e:
                logger.warning(f"Failed to load business entities from join graph: {e}")
                # Fallback list
                self._business_entities_cache = [
                    "asset", "assetType", "crew", "customer", "employee", "equipment", 
                    "expense", "inspection", "job", "quote", "service", "serviceLocation",
                    "workOrder", "workTime", "payroll", "safety", "attachment"
                ]
        
        business_entities = self._business_entities_cache
        
        classification_prompt = f"""Classify this question as SQL, RAG, or GENERAL.

═══════════════════════════════════════════════════════════════════
⚠️  CRITICAL BUSINESS DOMAIN CONTEXT ⚠️
═══════════════════════════════════════════════════════════════════
This system manages: {', '.join(business_entities)}

KEY CLASSIFICATION RULE:
If the question mentions ANY business entity (or related terms like "types", "statuses", "available"), 
classify as SQL unless it's explicitly asking "HOW TO USE" the system.

Examples of business-related questions → SQL:
✓ "What are the [entity] types available?" → SQL (queries database)
✓ "List the [entities] in the system" → SQL (queries database)
✓ "Show me all [entity] statuses" → SQL (queries database)
✗ "How do I create a [entity]?" → RAG (usage question)
═══════════════════════════════════════════════════════════════════

**SQL** - ONLY if question requires:
- Querying specific database records
- Counting, aggregating, or calculating from stored data
- Filtering existing records by criteria
- MUST reference data that exists in the database
- Follow-up questions that modify/refine a previous SQL query

SQL Examples:
- "How many active employees there are?"
- "How many equipment/locations there are?"
- "Which work orders are currently in progress?"
- "Show me the work order details for the work orders that are currently in progress"
- "Give me the name of the lead and employee names for the work orders that are currently in progress"
- "What are the asset types available?" ← IMPORTANT: Asking about business entity types = SQL
- "List the asset types available in the system" ← IMPORTANT: "available in system" = data query
- "What inspection templates exist?" ← Queries existing business data
- "Show me all expense types" ← Lists business configuration data
- "What service locations do we have?" ← Queries business locations
- "List all crew names" ← Queries business entities
- "Do the same but show the location Name instead of the location Id" (if previous query was SQL)
- "Show me the same data but with employee names" (if previous query was SQL)
- "Add the service location to the previous result" (if previous query was SQL)

**RAG** - ONLY if question asks about:
- System usage, how-to questions, feature explanations
- How to use specific features or modules in the system
- Step-by-step instructions for completing tasks
- Feature descriptions and capabilities
- System navigation and workflows
- MUST be answerable from user manual/system documentation

RAG Examples:
- "How do I create a work order?"
- "How do I add a customer?"
- "What are the steps to complete an inspection?"
- "How do I view customer details?"
- "How do I filter work orders?"
- "What permissions are needed to access the core module?"
- "How do I add a customer location?"
- "How do I assign a crew to a work order?"

**GENERAL** - Use for:
- General knowledge questions
- Questions not related to business data or policies
- Explanations, definitions, or general advice
- Questions that don't require database or document access
- Questions about general concepts, technology, or non-business topics

GENERAL Examples:
- "What is machine learning?"
- "What's the weather today?"
- "Explain quantum computing"
- "How does Python work?"
- "What is artificial intelligence?"
- "Tell me a joke"

IMPORTANT RULES:
1. **CRITICAL**: If the question mentions ANY business entities (asset, crew, employee, workOrder, inspection, quote, service, expense, etc.) → SQL
2. **CRITICAL**: Questions like "What [entity] types are available/exist?" or "List [entities]" → SQL (not GENERAL)
3. If asking for CURRENT DATA or STATISTICS from the database → SQL
4. If asking about HOW TO USE THE SYSTEM or SYSTEM FEATURES from user manual → RAG
5. If asking about GENERAL KNOWLEDGE or non-business topics → GENERAL
6. If unsure between SQL and RAG, prefer SQL for data queries, RAG for system usage queries
7. If question doesn't clearly fit SQL or RAG → GENERAL
8. **CRITICAL**: If the conversation context shows a previous SQL query was just executed, and the current question references "the previous result", "the same", "that data", "from above", etc., classify as SQL
9. Follow-up questions that modify a previous query result (e.g., "show X instead of Y", "add column Z") should be classified the same as the original query{recent_context}
Current question: {question}

Respond with ONLY one word: SQL, RAG, or GENERAL"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=classification_prompt)])
            classification = str(response.content).strip().upper() if hasattr(response, 'content') and response.content else "GENERAL"
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
        if classification not in ["SQL", "RAG", "GENERAL"]:
            logger.warning(f"Invalid classification '{classification}', defaulting to GENERAL")
            classification = "GENERAL"
        
        logger.info(f"Question classified as: {classification}")
        
        state["next_step"] = classification.lower()
        state["messages"].append(AIMessage(content=f"Routing to {classification} agent..."))
        
        return state
    
    def _execute_sql_agent(self, state: AgentState) -> AgentState:
        """Execute SQL agent for database queries"""
        from datetime import datetime
        from src.utils.query_memory import QueryResultMemory
        
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
            # Get previous results from memory for follow-up detection
            previous_results = state.get("query_result_memory")
            
            # Get both answer and structured data, passing previous results
            result = self.sql_agent.query_with_structured(
                question=question,
                previous_results=previous_results
            )
            state["sql_result"] = result["answer"]
            state["sql_structured_result"] = result.get("structured_result")
            state["messages"].append(AIMessage(content=f"SQL Result: {result['answer']}"))
            state["next_step"] = "finalize"
            
            # Store result in memory for future follow-up questions
            if result.get("structured_result"):
                # Initialize or load existing memory
                if previous_results:
                    memory = QueryResultMemory.from_dict(
                        previous_results,
                        max_results=settings.query_result_memory_size
                    )
                else:
                    memory = QueryResultMemory(max_results=settings.query_result_memory_size)
                
                # Add new result to memory (with tables_used and sql from SQL agent)
                memory.add_result(
                    question=question,
                    structured_data=result["structured_result"],
                    sql_query=result.get("sql_query"),
                    tables_used=result.get("tables_used")
                )
                
                # Store updated memory in state (will be persisted by checkpoint)
                state["query_result_memory"] = memory.to_dict()
                
                logger.info(f"Stored query result in memory: {len(memory)} results total")
            
        except Exception as e:
            logger.error(f"SQL agent error: {e}")
            state["sql_result"] = f"Error: {str(e)}"
            state["sql_structured_result"] = None
            state["next_step"] = "finalize"
        
        return state
    
    def _execute_rag_agent(self, state: AgentState) -> AgentState:
        """Execute RAG agent for system usage questions"""
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
    
    def _execute_general_agent(self, state: AgentState) -> AgentState:
        """Execute general agent for questions that don't require SQL or RAG"""
        # Truncate messages before LLM call
        state = self._truncate_messages_if_needed(state)
        
        question = state["question"]
        
        logger.info(f"Executing general agent for: '{question}'")
        
        try:
            # Use LLM directly to answer general questions
            # Include conversation history for context
            messages_for_llm = list(state.get("messages", []))
            if not messages_for_llm or not isinstance(messages_for_llm[-1], HumanMessage):
                # Add current question if not already in messages
                messages_for_llm.append(HumanMessage(content=question))
            
            response = self.llm.invoke(messages_for_llm)
            answer = response.content if hasattr(response, 'content') and response.content else "I couldn't generate an answer. Please try again."
            
            state["general_result"] = answer
            state["messages"].append(AIMessage(content=f"General Answer: {answer}"))
            state["next_step"] = "finalize"
        except Exception as e:
            logger.error(f"General agent error: {e}")
            state["general_result"] = f"Error: {str(e)}"
            state["next_step"] = "finalize"
        
        return state
    
    def _finalize_answer(self, state: AgentState) -> AgentState:
        """
        Finalize the answer and prepare for return
        
        For SQL results, we pass through the already-formatted answer with minimal LLM processing.
        This enables streaming while avoiding regeneration/duplication.
        
        Also preserves structured_data for BFF markdown conversion.
        """
        
        # Determine which result to use (priority: SQL > RAG > GENERAL)
        if state.get("sql_result"):
            raw_answer = state["sql_result"]
            # Preserve structured data from SQL agent for BFF
            state["final_structured_data"] = state.get("sql_structured_result")
        elif state.get("rag_result"):
            raw_answer = state["rag_result"]
            state["final_structured_data"] = None  # RAG doesn't have structured data
        elif state.get("general_result"):
            raw_answer = state["general_result"]
            state["final_structured_data"] = None  # General doesn't have structured data
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
        next_step = state.get("next_step", "general")
        
        if next_step == "sql":
            return "sql_agent"
        elif next_step == "rag":
            return "rag_agent"
        else:
            return "general_agent"
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow
        
        Graph structure:
        START → classify → [sql_agent OR rag_agent OR general_agent] → finalize → END
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify", self._classify_question)
        workflow.add_node("sql_agent", self._execute_sql_agent)
        workflow.add_node("rag_agent", self._execute_rag_agent)
        workflow.add_node("general_agent", self._execute_general_agent)
        workflow.add_node("finalize", self._finalize_answer)
        
        # Add edges
        workflow.set_entry_point("classify")
        
        # Conditional routing after classification
        workflow.add_conditional_edges(
            "classify",
            self._route_after_classification,
            {
                "sql_agent": "sql_agent",
                "rag_agent": "rag_agent",
                "general_agent": "general_agent"
            }
        )
        
        # All agents go to finalize
        workflow.add_edge("sql_agent", "finalize")
        workflow.add_edge("rag_agent", "finalize")
        workflow.add_edge("general_agent", "finalize")
        
        # Finalize goes to END
        workflow.add_edge("finalize", END)
        
        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        else:
            return workflow.compile()  # No checkpointing (backward compatible)
    
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
            "general_result": None,
            "final_answer": None,
            "final_structured_data": None,
            "query_result_memory": None
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Determine route taken
        if final_state.get("sql_result"):
            route = "sql"
        elif final_state.get("rag_result"):
            route = "rag"
        else:
            route = "general"
        
        # Extract results
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
    
    async def astream_events(self, input_data: dict, config: Optional[dict] = None, version: str = "v1"):
        """
        Stream events from the LangGraph workflow execution
        
        This is a convenience wrapper around the workflow's astream_events method,
        designed for use with FastAPI streaming endpoints.
        
        Args:
            input_data: Initial state for the workflow (must match AgentState structure)
            config: Configuration dict with thread_id for checkpointing (optional)
            version: Stream events API version (default: "v1")
        
        Yields:
            Event dictionaries from the workflow execution
            
        Example:
            ```python
            config = {"configurable": {"thread_id": "conversation-123"}}
            async for event in agent.astream_events(
                {"question": "How many technicians?", ...},
                config=config,
                version="v1"
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    print(chunk.content)
            ```
        """
        if config:
            async for event in self.workflow.astream_events(input_data, config=config, version=version):
                yield event
        else:
            async for event in self.workflow.astream_events(input_data, version=version):
                yield event

