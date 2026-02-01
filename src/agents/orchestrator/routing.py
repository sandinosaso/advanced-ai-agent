"""
Orchestrator routing - question classification logic
"""

from typing import Literal, List, Sequence
from loguru import logger

from langchain_core.messages import HumanMessage, AIMessage

from src.agents.orchestrator.context import OrchestratorContext


def classify_question(
    question: str,
    messages: Sequence,
    ctx: OrchestratorContext
) -> Literal["sql", "rag", "general"]:
    """
    Classify question to determine routing.

    Three-way classification:
    - SQL: Database queries requiring data retrieval
    - RAG: System usage questions requiring user manual retrieval
    - GENERAL: General questions that can be answered directly by LLM
    """
    business_entities = ctx.get_business_entities()

    # Build context from recent messages to understand follow-ups
    recent_context = ""
    if len(messages) > 1:
        recent_messages = messages[-4:] if len(messages) > 4 else messages[:-1]
        context_parts = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                context_parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                content = msg.content
                if "Routing to" in content or "agent" in content.lower():
                    context_parts.append(f"Assistant: {content}")
                elif len(content) < 100:
                    context_parts.append(f"Assistant: {content}")
        if context_parts:
            recent_context = "\n\nRecent conversation context:\n" + "\n".join(context_parts[-4:]) + "\n"

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
        response = ctx.llm.invoke([HumanMessage(content=classification_prompt)])
        classification = (
            str(response.content).strip().upper()
            if hasattr(response, "content") and response.content
            else "GENERAL"
        )
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower() or "model" in error_msg.lower():
            from src.config.settings import settings
            if settings.llm_provider == "ollama":
                raise ValueError(
                    f"Ollama model '{settings.ollama_model}' is not available. "
                    f"Please run: ollama pull {settings.ollama_model}"
                ) from e
        raise

    if classification not in ["SQL", "RAG", "GENERAL"]:
        logger.warning(f"Invalid classification '{classification}', defaulting to GENERAL")
        classification = "GENERAL"

    logger.info(f"Question classified as: {classification}")
    return classification.lower()
