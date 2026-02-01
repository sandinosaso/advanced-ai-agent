"""
Domain term extraction and resolution nodes
"""

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings


@trace_step("extract_domain_terms")
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

    try:
        domain_terms = ctx.domain_ontology.extract_domain_terms(question)
        state["domain_terms"] = domain_terms
        state["domain_resolutions"] = []

        logger.info(f"Extracted {len(domain_terms)} domain terms: {domain_terms}")
    except Exception as e:
        logger.error(f"Failed to extract domain terms: {e}")
        state["domain_terms"] = []
        state["domain_resolutions"] = []

    return state


@trace_step("resolve_domain_terms")
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
