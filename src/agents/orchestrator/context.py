"""
Orchestrator context - dependencies passed to workflow nodes
"""

from dataclasses import dataclass
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from src.config.settings import settings


def truncate_messages_if_needed(state: dict, ctx: "OrchestratorContext") -> dict:
    """Truncate messages in state before LLM calls to respect token limits."""
    messages = state.get("messages", [])
    if ctx.conversation_db and len(messages) > settings.max_conversation_messages:
        strategy = settings.conversation_memory_strategy
        state = dict(state)
        state["messages"] = list(ctx.conversation_db.prepare_messages_for_context(messages, strategy))
    return state


# Fallback business entities when SQL agent not available
DEFAULT_BUSINESS_ENTITIES = [
    "asset", "assetType", "crew", "customer", "employee", "equipment",
    "expense", "inspection", "job", "quote", "service", "serviceLocation",
    "workOrder", "workTime", "payroll", "safety", "attachment"
]

SYSTEM_TABLES = {
    "SequelizeMeta", "deletedEntity", "syncLog", "pdfCounter", "pdfIdentifier", "authenticationToken"
}

PRIORITY_ENTITIES = [
    "asset", "assetType", "crew", "customer", "employee", "equipment",
    "expense", "expenseType", "inspection", "inspectionTemplate", "jobType",
    "quote", "service", "serviceLocation", "serviceTemplate",
    "workOrder", "workOrderStatus", "workTime", "payroll", "safety",
    "attachment", "attachmentType", "note", "nonJobTime"
]


@dataclass
class OrchestratorContext:
    """Context holding dependencies for orchestrator nodes"""

    llm: BaseChatModel
    sql_agent: Optional[Any]  # SQLGraphAgent
    conversation_db: Any  # ConversationDatabase or None
    _business_entities_cache: Optional[List[str]] = None
    rag_agent: Optional[Any] = None  # RAGAgent, lazy init
    general_agent: Optional[Any] = None  # GeneralAgent, lazy init

    def get_business_entities(self) -> List[str]:
        """Get business entity list for classification (cached)."""
        if self._business_entities_cache is not None:
            return self._business_entities_cache

        try:
            if self.sql_agent and hasattr(self.sql_agent, "join_graph"):
                all_tables = list(self.sql_agent.join_graph.get("tables", {}).keys())
                business_tables = [t for t in all_tables if t not in SYSTEM_TABLES]
                existing_priority = [e for e in PRIORITY_ENTITIES if e in business_tables]
                other_entities = [t for t in business_tables if t not in PRIORITY_ENTITIES][:10]
                self._business_entities_cache = existing_priority + other_entities
            else:
                self._business_entities_cache = DEFAULT_BUSINESS_ENTITIES.copy()
        except Exception:
            self._business_entities_cache = DEFAULT_BUSINESS_ENTITIES.copy()

        return self._business_entities_cache
