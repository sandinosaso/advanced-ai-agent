"""
Domain term extraction and resolution nodes
"""

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.agents.sql.prompt_helpers import (
    get_domain_entities_with_atomic_signals,
    get_entity_id_field_map,
)


def extract_domain_terms_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Extract domain-specific business terms from the question.
    """
    state = dict(state)
    if not ctx.domain_ontology or not settings.domain_extraction_enabled:
        state["domain_terms"] = []
        state["domain_resolutions"] = []
        return state

    question = state["question"]

    # For follow-up questions, pass implied atomic signals from context.
    # The LLM often returns [] for terse follow-ups, but we know from follow-up detection
    # what entity is referenced. This allows compound terms to be resolved correctly.
    implied_signals: list[str] = []
    
    # Get entities that require atomic signals from domain registry
    atomic_signal_entities = get_domain_entities_with_atomic_signals(ctx.domain_ontology)
    
    if state.get("is_followup") and state.get("referenced_entity"):
        entity = state["referenced_entity"]
        if entity and entity.lower() in atomic_signal_entities:
            implied_signals = [entity.lower()]
    elif state.get("is_followup") and state.get("referenced_ids"):
        # Infer entity from referenced_ids when referenced_entity not set
        rid = state["referenced_ids"]
        entity_id_map = get_entity_id_field_map(ctx.domain_ontology)
        
        # Build reverse map: idField -> entity
        id_to_entity = {v: k for k, v in entity_id_map.items()}
        
        # Check which ID fields are present and map to entities
        for id_field in rid.keys():
            if id_field in id_to_entity:
                entity = id_to_entity[id_field]
                if entity in atomic_signal_entities:
                    implied_signals = [entity]
                    break

    try:
        domain_terms = ctx.domain_ontology.extract_domain_terms(
            question, implied_atomic_signals=implied_signals if implied_signals else None
        )
        state["domain_terms"] = domain_terms
        state["domain_resolutions"] = []

        logger.info(f"Extracted {len(domain_terms)} domain terms: {domain_terms}")
    except Exception as e:
        logger.error(f"Failed to extract domain terms: {e}")
        state["domain_terms"] = []
        state["domain_resolutions"] = []

    return state


def resolve_domain_terms_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Resolve domain terms to schema locations.
    """
    state = dict(state)
    if not ctx.domain_ontology:
        return state

    domain_terms = state.get("domain_terms", [])
    resolutions = []

    for term in domain_terms:
        try:
            resolution = ctx.domain_ontology.resolve_domain_term(term)
            if resolution:
                resolutions.append(
                    {
                        "term": resolution.term,
                        "entity": resolution.entity,
                        "tables": resolution.tables,
                        "filters": resolution.filters,
                        "confidence": resolution.confidence,
                        "strategy": resolution.resolution_strategy,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to resolve domain term '{term}': {e}")

    state["domain_resolutions"] = resolutions

    if resolutions:
        logger.info(f"Resolved {len(resolutions)} domain terms to schema:")
        for res in resolutions:
            logger.info(f"  - '{res['term']}' → tables: {res['tables']}, filters: {len(res['filters'])}")
    else:
        logger.debug("No domain terms resolved")

    return state
