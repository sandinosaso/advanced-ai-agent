"""
SQL generator node
"""

from typing import Any, Dict, List

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.domain.ontology.formatter import build_where_clauses
from src.sql.execution.secure_rewriter import rewrite_secure_tables
from src.agents.sql.planning import (
    extract_tables_from_join_plan,
    parse_join_path_steps,
    get_excluded_columns,
)
from src.agents.sql.prompt_helpers import (
    build_name_label_examples,
    build_bridge_table_example,
    build_column_mismatch_example,
    build_display_attributes_examples,
)


def _build_domain_filter_instructions(state: SQLGraphState) -> str:
    """Build instructions for domain filters in SQL generation prompt"""
    domain_resolutions = state.get("domain_resolutions", [])
    if not domain_resolutions:
        return ""

    where_clauses = build_where_clauses(domain_resolutions)
    if not where_clauses:
        return ""

    instructions = "\n\nDOMAIN FILTER REQUIREMENTS:\n"
    instructions += "You MUST include these WHERE clause conditions to filter by domain concepts:\n"
    for clause in where_clauses:
        instructions += f"  - {clause}\n"
    instructions += "\nCombine these with AND in your WHERE clause.\n"

    return instructions


def _deduplicate_joins(sql: str) -> str:
    """Remove duplicate JOIN clauses from SQL."""
    lines = sql.split("\n")
    seen_joins = set()
    seen_tables = set()
    deduplicated_lines = []

    for line in lines:
        normalized = " ".join(line.strip().split())
        normalized_upper = normalized.upper()

        if normalized_upper.startswith("JOIN "):
            parts = normalized.split()
            if len(parts) >= 2:
                table_name = parts[1].lower()

                if normalized in seen_joins:
                    logger.warning(f"Removed exact duplicate JOIN: {normalized}")
                    continue

                if table_name in seen_tables:
                    logger.warning(f"Removed duplicate table JOIN: {table_name} (already joined)")
                    continue

                seen_joins.add(normalized)
                seen_tables.add(table_name)
                deduplicated_lines.append(line)
            else:
                deduplicated_lines.append(line)
        else:
            deduplicated_lines.append(line)

    return "\n".join(deduplicated_lines)


def _inject_domain_filters(sql: str, domain_resolutions: List[Dict[str, Any]]) -> str:
    """Inject domain filter WHERE clauses into generated SQL."""
    where_clauses = build_where_clauses(domain_resolutions)
    if not where_clauses:
        return sql

    sql_upper = sql.upper()

    if "WHERE" in sql_upper:
        where_pos = sql_upper.find("WHERE")
        where_content = sql[where_pos:].lower()

        filters_needed = []
        for clause in where_clauses:
            clause_parts = clause.lower().split()
            if len(clause_parts) >= 1:
                column_part = clause_parts[0]
                if column_part not in where_content:
                    filters_needed.append(clause)

        if filters_needed:
            insert_keywords = ["GROUP BY", "HAVING", "ORDER BY", "LIMIT"]
            insert_pos = len(sql)
            for keyword in insert_keywords:
                pos = sql_upper.find(keyword, where_pos)
                if pos != -1 and pos < insert_pos:
                    insert_pos = pos

            filter_str = " AND " + " AND ".join(filters_needed)
            sql = sql[:insert_pos].rstrip() + filter_str + " " + sql[insert_pos:]
    else:
        insert_keywords = ["GROUP BY", "HAVING", "ORDER BY", "LIMIT"]
        insert_pos = len(sql)
        for keyword in insert_keywords:
            pos = sql_upper.find(keyword)
            if pos != -1 and pos < insert_pos:
                insert_pos = pos

        filter_str = "\nWHERE " + " AND ".join(where_clauses)
        sql = sql[:insert_pos].rstrip() + filter_str + "\n" + sql[insert_pos:]

    return sql


def generate_sql_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Generate SQL query based on join plan.
    """
    state = dict(state)
    join_plan_text = state.get("join_plan", "")
    tables_from_join_plan = extract_tables_from_join_plan(
        join_plan_text, ctx.join_graph["tables"]
    )

    all_tables = set(state["tables"]) | tables_from_join_plan

    excluded_columns = get_excluded_columns(
        state.get("domain_resolutions", []), ctx.domain_ontology, ctx.join_graph["tables"]
    )
    table_schemas = []
    forbidden_columns_flat: List[str] = []
    for table_name in sorted(all_tables):
        if table_name in ctx.join_graph["tables"]:
            columns = ctx.join_graph["tables"][table_name].get("columns", [])
            excluded = excluded_columns.get(table_name, set())
            columns = [c for c in columns if c not in excluded]
            if excluded:
                forbidden_columns_flat.extend(f"{table_name}.{c}" for c in excluded)
            columns_str = ", ".join(columns[:settings.sql_max_columns_in_schema])
            if len(columns) > settings.sql_max_columns_in_schema:
                columns_str += f" ... ({len(columns)} total columns)"
            table_schemas.append(f"{table_name}: {columns_str}")
        else:
            logger.warning(
                f"Table '{table_name}' mentioned in join plan but not found in join graph"
            )

    schema_context = "\n".join(table_schemas)
    excluded_columns_hint = ""
    if forbidden_columns_flat:
        excluded_columns_hint = (
            "\n\nDo NOT use these columns (forbidden for this query): "
            + ", ".join(forbidden_columns_flat)
            + "\n"
        )

    join_path_steps = parse_join_path_steps(state.get("join_plan", ""))
    
    # Build dynamic examples from join graph
    name_label_examples = build_name_label_examples(ctx.join_graph, max_examples=4)
    bridge_example = build_bridge_table_example(ctx.join_graph)
    column_mismatch_example = build_column_mismatch_example(ctx.join_graph)
    
    # Build display attributes examples if enabled
    display_attributes_examples = ""
    if settings.display_attributes_enabled and ctx.display_attributes:
        display_attributes_examples = build_display_attributes_examples(
            ctx.display_attributes, 
            list(all_tables), 
            max_examples=5
        )
        if display_attributes_examples:
            logger.info(f"Generated display attributes examples for tables: {list(all_tables)}")
    else:
        logger.warning(
            f"Display attributes not used - enabled: {settings.display_attributes_enabled}, "
            f"ctx.display_attributes: {ctx.display_attributes is not None}"
        )

    followup_where_clause = ""
    if state.get("is_followup") and state.get("referenced_ids"):
        referenced_ids = state["referenced_ids"]

        def _is_real_id(v: Any) -> bool:
            s = str(v).strip()
            if not s or s.startswith("[") or s.endswith("]") or "SPECIFIC_" in s.upper():
                return False
            if s.lower() in ("id1", "id2", "id3", "id"):
                return False
            return True

        followup_where_clause = "\n\nFOLLOW-UP QUERY - USE THESE KNOWN IDs:\n"
        followup_where_clause += "=" * 70 + "\n"
        followup_where_clause += "This is a follow-up question. You have these IDs from the previous query:\n\n"

        where_conditions = []
        for id_field, values in referenced_ids.items():
            real_values = [v for v in values if _is_real_id(v)][:10]
            if not real_values:
                continue
            
            # Extract table name from id_field (e.g., "inspection_id" -> "inspection", "inspectionId" -> "inspection")
            if id_field.endswith("_id"):
                table_name = id_field[:-3]  # Remove "_id" suffix
                column_name = "id"
            elif id_field.endswith("Id") and id_field != "id":
                table_name = id_field[:-2]  # Remove "Id" suffix
                column_name = "id"
            else:
                # If it doesn't follow standard pattern, use as-is
                table_name = id_field
                column_name = id_field
            
            if not table_name:
                continue
            
            # Check if table exists in all_tables (case-insensitive)
            matching_table = None
            for t in all_tables:
                if t.lower() == table_name.lower():
                    matching_table = t
                    break
            
            if matching_table:
                if len(real_values) == 1:
                    where_conditions.append(f"{matching_table}.{column_name} = '{real_values[0]}'")
                else:
                    values_str = "', '".join(str(v) for v in real_values)
                    where_conditions.append(
                        f"{matching_table}.{column_name} IN ('{values_str}')"
                    )

        if where_conditions:
            followup_where_clause += "CRITICAL - Include these WHERE conditions to filter by the referenced IDs:\n"
            for condition in where_conditions:
                followup_where_clause += f"  - {condition}\n"
            followup_where_clause += "\n"
            followup_where_clause += "IMPORTANT:\n"
            followup_where_clause += "- Use these exact IDs in your WHERE clause (copy the values above literally)\n"
            followup_where_clause += "- Do NOT use placeholders like [SPECIFIC_INSPECTION_ID], [ID], or id1/id2\n"
            followup_where_clause += "- Do NOT rebuild the filter from the previous query\n"
            followup_where_clause += "- Focus on selecting the NEW data requested in the current question\n"
            followup_where_clause += "=" * 70 + "\n"

    prompt = f"""
Generate a MySQL SELECT query using ONLY the columns shown below.

All tables needed for this query (with their actual columns):
{schema_context}
{excluded_columns_hint}
CRITICAL RULES:
- Use ONLY the columns listed above for each table - do NOT guess or invent column names
- Follow the JOIN_PATH EXACTLY step by step - do NOT skip any tables or steps
- Include ALL tables shown above in your FROM/JOIN clauses
- Do NOT try to join tables directly if JOIN_PATH shows they require a bridge table
{column_mismatch_example}
- Use LIMIT {settings.max_query_rows} unless it's an aggregate COUNT/SUM/etc
- Use logical table names (not secure_* prefixed versions)
- DO NOT add secure_ prefix - the system handles that automatically

IMPORTANT - SELECT CLAUSE GUIDANCE:
- ALWAYS include human-readable identifiers (name, firstName/lastName, description) in your SELECT, not just IDs
- When using GROUP BY with a table, include the table's display attributes in BOTH SELECT and GROUP BY clauses
  Example: GROUP BY employee.id, employee.firstName, employee.lastName (not just employee.id)
- This applies even to aggregate queries - users need to see WHO/WHAT the aggregates are for
{name_label_examples if name_label_examples else ""}
{display_attributes_examples if display_attributes_examples else ""}
{followup_where_clause}
Question: {state['question']}

Join plan (follow this EXACTLY, step by step):
{state['join_plan']}

{"EXPLICIT JOIN STEPS (follow these in order):" + chr(10) + chr(10).join(f"{i+1}. {step}" for i, step in enumerate(join_path_steps)) if join_path_steps else ""}

IMPORTANT: {bridge_example} Do NOT skip bridge tables and try to join tables directly.
{_build_domain_filter_instructions(state)}
Return ONLY the SQL query, nothing else.
"""

    logger.info(f"[PROMPT] generate_sql prompt:\n{prompt}")
    response = ctx.llm.invoke(prompt)
    raw_sql = str(response.content).strip() if hasattr(response, "content") and response.content else ""
    if raw_sql.startswith("```"):
        lines = raw_sql.split("\n")
        raw_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
    logger.info(f"Generated SQL (before rewriting): {raw_sql}")

    domain_resolutions = state.get("domain_resolutions", [])
    if domain_resolutions:
        raw_sql = _inject_domain_filters(raw_sql, domain_resolutions)
        logger.info("Injected domain filters into SQL")

    raw_sql = _deduplicate_joins(raw_sql)

    rewritten_sql = rewrite_secure_tables(raw_sql)
    logger.info(f"Rewritten SQL (after secure view conversion): {rewritten_sql}")
    state["sql"] = rewritten_sql
    return state
