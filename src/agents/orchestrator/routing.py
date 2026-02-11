"""
Orchestrator routing - question classification logic
"""

from typing import Literal, List, Sequence, Any
from loguru import logger

from langchain_core.messages import HumanMessage, AIMessage

from src.agents.orchestrator.context import OrchestratorContext
from src.llm.response_utils import extract_text_from_response


def _build_sql_examples(business_entities: List[str]) -> str:
    """Build dynamic SQL classification examples from business entities."""
    if not business_entities or len(business_entities) < 2:
        return """- "How many active records are there?"
- "Which items are currently in progress?"
- "Show me the details for items that are active"
- "What types are available in the system?"
- "List all names"
- "Do the same but show the name instead of the ID" (if previous query was SQL)"""
    
    # Use first few entities to build examples
    entity1 = business_entities[0]
    entity2 = business_entities[1] if len(business_entities) > 1 else business_entities[0]
    entity3 = business_entities[2] if len(business_entities) > 2 else business_entities[0]
    
    return f"""- "How many active {entity1} are there?"
- "How many {entity2} are there?"
- "Which {entity3} are currently in progress?"
- "Show me the {entity1} details for items that are active"
- "What are the {entity2} types available?" ← IMPORTANT: Asking about entity types = SQL
- "List the {entity1} available in the system" ← IMPORTANT: "available in system" = data query
- "What {entity3} exist?" ← Queries existing business data
- "Show me all {entity2} types" ← Lists business configuration data
- "List all {entity1} names" ← Queries business entities
- "Do the same but show the name instead of the ID" (if previous query was SQL)
- "Show me the same data with {entity2} names" (if previous query was SQL)
- "Add the {entity3} to the previous result" (if previous query was SQL)
- "For that {entity1} I want the {entity2}" ← IMPORTANT: Follow-up asking for related data = SQL
- "I want questions and answers for that {entity3}" ← IMPORTANT: Retrieve related data = SQL"""


def _build_rag_examples(business_entities: List[str]) -> str:
    """Build dynamic RAG classification examples from business entities."""
    if not business_entities or len(business_entities) < 2:
        return """- "How do I create a new record?"
- "How do I add an item?"
- "What are the steps to complete a task?"
- "How do I view details?"
- "How do I filter items?"
- "What permissions are needed to access the module?"
- "How do I add a related record?"
- "How do I assign an item to another?\""""
    
    # Use first few entities to build examples
    entity1 = business_entities[0]
    entity2 = business_entities[1] if len(business_entities) > 1 else business_entities[0]
    entity3 = business_entities[2] if len(business_entities) > 2 else business_entities[0]
    
    return f"""- "How do I create a {entity1}?"
- "How do I add a {entity2}?"
- "What are the steps to complete a {entity3}?"
- "How do I view {entity1} details?"
- "How do I filter {entity2}?"
- "What permissions are needed to access the {entity1} module?"
- "How do I add a {entity2}?"
- "How do I assign a {entity3} to a {entity1}?\""""


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
    
    # Generate dynamic examples from business entities
    sql_examples = _build_sql_examples(business_entities)
    rag_examples = _build_rag_examples(business_entities)
    entity_list = ", ".join(business_entities[:10]) if business_entities else "entities"

    # Build context from recent messages to understand follow-ups
    recent_context = ""
    if len(messages) > 1:
        recent_messages = messages[-4:] if len(messages) > 4 else messages[:-1]
        context_parts = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                context_parts.append(f"User: {extract_text_from_response(msg)}")
            elif isinstance(msg, AIMessage):
                content = extract_text_from_response(msg)
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
{sql_examples}

**RAG** - ONLY if question asks about:
- System usage, how-to questions, feature explanations
- How to use specific features or modules in the system
- Step-by-step instructions for completing tasks
- Feature descriptions and capabilities
- System navigation and workflows
- MUST be answerable from user manual/system documentation

RAG Examples:
{rag_examples}

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
1. **CRITICAL**: If the question mentions ANY business entities ({entity_list}) → SQL
2. **CRITICAL**: Questions like "What [entity] types are available/exist?" or "List [entities]" → SQL (not GENERAL)
3. If asking for CURRENT DATA or STATISTICS from the database → SQL
4. If asking about HOW TO USE THE SYSTEM or SYSTEM FEATURES from user manual → RAG
5. If asking about GENERAL KNOWLEDGE or non-business topics → GENERAL
6. If unsure between SQL and RAG, prefer SQL for data queries, RAG for system usage queries
7. If question doesn't clearly fit SQL or RAG → GENERAL
8. **CRITICAL**: If the conversation context shows a previous SQL query was just executed, and the current question references "that [entity]", "for that [entity]", "the [entity]", "from above", etc., classify as SQL
9. **CRITICAL**: Follow-up questions that want to retrieve/show/display data related to a previous query result (e.g., "show questions and answers for that inspection", "get the details", "I want [data] for that [entity]") should be classified as SQL
10. **CRITICAL**: "I want [data] for/from [entity]" means "retrieve/show me [data]" → SQL (not "how to create"){recent_context}
Current question: {question}

Respond with ONLY one word: SQL, RAG, or GENERAL"""

    try:
        response = ctx.llm.invoke([HumanMessage(content=classification_prompt)])
        classification = extract_text_from_response(response).strip().upper() or "GENERAL"
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
