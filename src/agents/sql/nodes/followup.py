"""
Follow-up question detection node
"""

import json
from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step, entity_to_id_field
from src.config.settings import settings
from src.memory.query_memory import QueryResultMemory
from src.agents.sql.prompt_helpers import get_sample_table_names
from src.llm.response_utils import extract_text_from_response


def detect_followup_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Detect if the question is a follow-up referencing previous results.
    """
    state = dict(state)
    logger.info(f"In node follow-up question settings.followup_detection_enabled: {settings.followup_detection_enabled}")
    if not settings.followup_detection_enabled:
        state["is_followup"] = False
        state["referenced_ids"] = None
        state["referenced_entity"] = None
        return state

    previous_results = state.get("previous_results")
    logger.info(f"In node follow-up question I have previous results: {previous_results}")
    if not previous_results:
        state["is_followup"] = False
        state["referenced_ids"] = None
        state["referenced_entity"] = None
        return state

    question = state["question"]

    temp_memory = QueryResultMemory.from_dict(
        previous_results,
        max_results=settings.query_result_memory_size,
    )

    logger.info(f"In node follow-up question I have temp_memory: {temp_memory}")

    context = temp_memory.format_for_context(
        n=3,
        max_tokens=settings.followup_max_context_tokens,
        include_sample_rows=True,
    )

    logger.info(f"In node follow-up question I have context: {context}")

    if not context:
        state["is_followup"] = False
        state["referenced_ids"] = None
        state["referenced_entity"] = None
        return state

    # Get sample entity names from join graph for dynamic examples
    sample_entities = get_sample_table_names(ctx.join_graph, n=3)
    entity_examples = "/".join(sample_entities) if sample_entities else "entity1/entity2/entity3"
    
    # Build ID field examples dynamically
    id_examples = []
    for entity in sample_entities[:2]:
        id_examples.append(f"{entity}Id")
    id_field_examples = ", ".join(id_examples) if id_examples else "entityId, relatedEntityId"

    prompt = f"""Analyze if this question is a follow-up referencing previous query results.

{context}

CURRENT QUESTION: {question}

TASK:
Determine if the current question references the previous results above.

Look for:
- Reference words: "that", "those", "the same", "previous", "from above", "for it", "for them"
- Implicit references: "show me the details" (implies "for that entity from previous query")
- Context-dependent questions that don't make sense without previous results

Respond with ONLY a JSON object (no markdown, no explanation):
{{
  "is_followup": true/false,
  "reasoning": "brief explanation",
  "referenced_entity": "{entity_examples}/etc or null",
  "referenced_ids": {{"{id_field_examples}": ["<field name from Key IDs above>"], ...}} or null
}}

If is_followup=true: set referenced_ids to the KEY NAMES only (e.g. {id_field_examples}) that match the entity being referenced. Use the exact key names from "Key IDs found" above - the system will substitute the actual ID values automatically. Do NOT invent placeholder values like id1 or [SPECIFIC_ID].
If is_followup=false, set referenced_entity and referenced_ids to null.
"""

    try:
        response = ctx.llm.invoke(prompt)
        raw = extract_text_from_response(response).strip()

        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        result = json.loads(raw)

        is_followup = result.get("is_followup", False)
        referenced_ids = result.get("referenced_ids")
        referenced_entity = result.get("referenced_entity")
        reasoning = result.get("reasoning", "")

        if is_followup:
            actual_ids = temp_memory.get_all_identifiers(n=1)
            if actual_ids:
                if referenced_ids and isinstance(referenced_ids, dict):
                    merged = {
                        k: actual_ids[k]
                        for k in referenced_ids
                        if k in actual_ids and actual_ids[k]
                    }
                    referenced_ids = merged if merged else actual_ids
                else:
                    referenced_ids = actual_ids
                if referenced_entity and "id" in actual_ids and actual_ids["id"]:
                    id_field_for_entity = entity_to_id_field(referenced_entity)
                    if id_field_for_entity and (
                        not referenced_ids or id_field_for_entity not in referenced_ids
                    ):
                        referenced_ids = dict(referenced_ids) if referenced_ids else {}
                        referenced_ids[id_field_for_entity] = actual_ids["id"]
            else:
                referenced_ids = None

        state["is_followup"] = is_followup
        state["referenced_ids"] = referenced_ids if is_followup else None
        state["referenced_entity"] = referenced_entity if is_followup else None

        if is_followup:
            logger.info(
                f"✅ Detected follow-up question: entity={referenced_entity}, "
                f"IDs={referenced_ids}, reasoning={reasoning}"
            )
        else:
            logger.info(f"Not a follow-up question: {reasoning}")

    except Exception as e:
        logger.warning(f"Failed to detect follow-up question: {e}. Treating as new question.")
        state["is_followup"] = False
        state["referenced_ids"] = None
        state["referenced_entity"] = None

    return state
