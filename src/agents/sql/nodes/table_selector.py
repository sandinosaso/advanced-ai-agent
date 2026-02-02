"""
Table selector node
"""

import json
from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.domain.ontology.formatter import format_domain_context_for_table_selection
from src.memory.query_memory import QueryResultMemory


def select_tables_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Select minimal set of tables needed to answer the question.
    """
    state = dict(state)
    all_tables = list(ctx.join_graph["tables"].keys())

    followup_context = ""
    if state.get("is_followup") and state.get("previous_results"):
        temp_memory = QueryResultMemory.from_dict(
            state["previous_results"],
            max_results=settings.query_result_memory_size,
        )

        recent = temp_memory.get_recent_results(n=1)
        if recent:
            last_result = recent[0]
            referenced_ids = state.get("referenced_ids", {})

            followup_context = f"""
FOLLOW-UP QUESTION CONTEXT:
This is a follow-up to a previous query. Use the context below to guide your table selection.

Previous Question: {last_result.question}
Tables Used Previously: {', '.join(last_result.tables_used) if last_result.tables_used else 'N/A'}
Rows Returned: {last_result.row_count}

Key IDs Available (you can use these directly in WHERE clauses):
"""
            if referenced_ids:
                for id_field, values in referenced_ids.items():
                    display_values = values[:5]
                    more = f" (and {len(values) - 5} more)" if len(values) > 5 else ""
                    followup_context += f"  - {id_field}: {display_values}{more}\n"
            else:
                followup_context += "  (No specific IDs extracted - use tables from previous query)\n"

            followup_context += """
INSTRUCTIONS FOR FOLLOW-UP:
- You already have the IDs above - use them directly in your WHERE clause
- Select tables needed to answer the NEW information requested
- You may need to include some tables from the previous query to join with the IDs
- Don't rebuild the entire previous query - we already have the target IDs
"""

    domain_context = ""
    domain_required_tables = set()

    domain_resolutions = state.get("domain_resolutions", [])
    if domain_resolutions:
        domain_context = "\n" + format_domain_context_for_table_selection(domain_resolutions) + "\n"

        for res in domain_resolutions:
            domain_required_tables.update(res.get("tables", []))

        if domain_required_tables:
            domain_context += f"\nIMPORTANT: Domain concepts require these tables: {', '.join(sorted(domain_required_tables))}\n"
            domain_context += "You MUST include these tables in your selection.\n"

    prompt = f"""
Select the set of tables needed to answer the question.

Rules:
- Return 3 to 8 tables (prefer fewer tables that you need to answer the question)
- Select from ACTUAL available tables (join graph reflects reality)
- If unsure, return fewer tables
- DO NOT invent table names that don't exist
- Prefer always to show labels/name or any column with text instead of IDS use IDS just for joining tables/ grouping but not to show in the result unless explicitly asked for
  (make sure to include the table that has those names)
{followup_context}{domain_context}
Available tables (subset shown if large):
{', '.join(all_tables[:settings.sql_max_tables_in_selection_prompt])}

Question: {state['question']}

Return ONLY a JSON array of table names that ACTUALLY EXIST in the list above. No explanation, no markdown, no text, just the array.
"""

    logger.info(f"[PROMPT] select_tables prompt:\n{prompt}")
    response = ctx.llm.invoke(prompt)
    raw = str(response.content).strip() if hasattr(response, "content") and response.content else ""
    logger.info(f"Raw LLM output: {raw}")

    try:
        tables = json.loads(raw)
        tables = [t for t in tables if t in ctx.join_graph["tables"]]

        for table in domain_required_tables:
            if table in ctx.join_graph["tables"] and table not in tables:
                tables.append(table)
                logger.info(f"Added domain-required table: {table}")
    except Exception as e:
        logger.warning(f"Failed to parse table selection: {e}. Raw output: {raw}")
        q = state["question"].lower()
        fallback = []
        if "work" in q:
            for t in ["employee", "workOrder", "workTime", "crew", "employeeCrew"]:
                if t in ctx.join_graph["tables"]:
                    fallback.append(t)
        elif "employee" in q:
            if "employee" in ctx.join_graph["tables"]:
                fallback.append("employee")
        if not fallback:
            fallback = list(all_tables[:settings.sql_max_fallback_tables])
        tables = fallback
        logger.info(f"Fallback selected tables: {tables}")

    logger.info(f"Selected tables: {tables}")
    state["tables"] = tables
    return state
