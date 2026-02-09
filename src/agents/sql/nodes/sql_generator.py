"""
SQL generator node
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.domain.ontology.formatter import build_where_clauses, format_domain_context
from src.sql.execution.secure_rewriter import rewrite_secure_tables, from_secure_view, to_secure_view
from src.agents.sql.planning import (
    extract_tables_from_join_plan,
    parse_join_path_steps,
    get_excluded_columns,
    get_required_join_constraints,
    validate_scoped_joins,
)
from src.agents.sql.prompt_helpers import (
    build_name_label_examples,
    build_bridge_table_example,
    build_column_mismatch_example,
    build_display_attributes_examples,
)


def _validate_select_tables(sql: str) -> None:
    """
    Validate that all tables referenced in SELECT are present in FROM/JOIN.
    Logs a warning if a table is referenced in SELECT but not joined.
    """
    if not sql or not sql.strip():
        return
    
    # Extract SELECT clause
    select_match = re.search(r"\bSELECT\s+(.*?)\s+FROM\s+", sql, re.DOTALL | re.IGNORECASE)
    if not select_match:
        return
    select_clause = select_match.group(1)
    
    # Extract table names from SELECT (e.g. "table.column")
    select_tables = set()
    for match in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.[a-zA-Z_]", select_clause):
        select_tables.add(match.group(1))
    
    # Extract tables from FROM/JOIN
    from_join_tables = set()
    # Match FROM table or JOIN table (with or without AS alias)
    for match in re.finditer(
        r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        sql,
        re.IGNORECASE
    ):
        from_join_tables.add(match.group(1))
    
    # Check for missing tables
    missing_tables = select_tables - from_join_tables
    if missing_tables:
        logger.warning(
            f"SELECT references tables not in FROM/JOIN: {missing_tables}. "
            f"This will cause 'Unknown column' errors. "
            f"Make sure template tables are included in join path."
        )


def get_default_table_filter_clauses(selected_tables: List[str], registry: Dict[str, Any]) -> List[str]:
    """
    Build WHERE clause fragments from default table filters.
    
    Args:
        selected_tables: List of selected table names
        registry: Domain registry dictionary
        
    Returns:
        List of WHERE clause strings for tables with default filters
        
    Example:
        For workOrder with isInternal=0: ["workOrder.isInternal = 0"]
    """
    if not registry:
        return []
    
    default_filters = registry.get("default_table_filters", {})
    if not default_filters:
        return []
    
    clauses = []
    for table in selected_tables:
        if table in default_filters:
            filters = default_filters[table]
            for filter_def in filters:
                column = filter_def.get("column")
                value = filter_def.get("value")
                if column and value is not None:
                    # Format value based on type
                    if isinstance(value, bool):
                        value_str = "true" if value else "false"
                    elif isinstance(value, str):
                        value_str = f"'{value}'"
                    else:
                        value_str = str(value)
                    
                    clause = f"{table}.{column} = {value_str}"
                    clauses.append(clause)
    
    return clauses


def _rewrite_sql_from_anchor(sql: str, anchor_table: str) -> str:
    """
    If the query does not start from the anchor table, reorder FROM and JOINs
    so that FROM uses the anchor table. This fixes queries that return too few rows
    (e.g. FROM user JOIN expense JOIN workOrder -> only rows with expense and user).
    """
    if not anchor_table or not sql.strip():
        return sql
    anchor_lower = anchor_table.lower()
    from_match = re.search(r"\bFROM\s+(\w+)\b", sql, re.IGNORECASE)
    if not from_match:
        return sql
    current_from = from_match.group(1)
    base_from = from_secure_view(current_from)
    if base_from.lower() == anchor_lower:
        return sql

    # Find anchor as it may appear in SQL (logical or secure)
    anchor_in_sql = anchor_table
    if to_secure_view(anchor_table) != anchor_table:
        anchor_in_sql = to_secure_view(anchor_table)
    anchor_in_sql_lower = anchor_in_sql.lower()

    # Split into SELECT, FROM+JOINs, and rest (WHERE, GROUP, ORDER, LIMIT)
    parts = re.split(r"\b(WHERE|GROUP\s+BY|ORDER\s+BY|LIMIT)\b", sql, maxsplit=1, flags=re.IGNORECASE)
    main_part = parts[0].strip()
    rest = (" " + " ".join(parts[1:]).strip()) if len(parts) > 1 else ""

    # Parse JOIN lines: "JOIN table ON condition" or "LEFT JOIN table ON condition"
    join_pattern = re.compile(
        r"\b(LEFT\s+JOIN|JOIN)\s+(\w+)\s+ON\s+",
        re.IGNORECASE
    )
    joins_with_conditions: List[Tuple[str, str, str]] = []  # (join_type, table, full_line)
    pos = 0
    while True:
        m = join_pattern.search(main_part, pos)
        if not m:
            break
        join_type, table = m.group(1), m.group(2)
        start = m.start()
        end = m.end()
        # Find end of this ON condition (next JOIN/end of main_part)
        next_join = join_pattern.search(main_part, end)
        cond_end = next_join.start() if next_join else len(main_part)
        cond_part = main_part[end:cond_end].strip()
        # Trim trailing comment or newline
        cond_part = re.sub(r"\s*--.*$", "", cond_part).strip()
        full_line = main_part[start:cond_end].strip()
        joins_with_conditions.append((join_type, table, full_line))
        pos = cond_end

    # Find the JOIN that introduces the anchor table
    anchor_join_idx: Optional[int] = None
    for i, (_, table, full_line) in enumerate(joins_with_conditions):
        if table.lower() == anchor_in_sql_lower:
            anchor_join_idx = i
            break
        if from_secure_view(table).lower() == anchor_lower:
            anchor_join_idx = i
            break
    if anchor_join_idx is None:
        logger.warning(
            f"Anchor table '{anchor_table}' not found in JOINs; cannot rewrite FROM clause"
        )
        return sql

    # Get the condition from the join that introduces anchor; the "other" table is the non-anchor table in the condition
    _, anchor_join_table, anchor_join_line = joins_with_conditions[anchor_join_idx]
    cond_match = re.search(r"\bON\s+(.+)$", anchor_join_line, re.DOTALL | re.IGNORECASE)
    on_condition = cond_match.group(1).strip() if cond_match else ""
    # Parse "table.col = table.col" or "table.col = table.col AND ..." to get the other table (not anchor)
    other_table = anchor_join_table
    for side in re.split(r"\s*=\s*", on_condition, maxsplit=1):
        dot = re.search(r"(\w+)\.\w+", side.strip())
        if dot:
            t = dot.group(1)
            if t.lower() != anchor_in_sql_lower and from_secure_view(t).lower() != anchor_lower:
                other_table = t
                break

    # New first JOIN: JOIN other_table ON condition (anchor is now FROM so we keep condition as-is)
    new_first_join = f"JOIN {other_table} ON {on_condition}"

    # Build new FROM + JOINs: FROM anchor, then the join that was introducing anchor (as JOIN other ON cond)
    select_from_part = re.sub(r"\bFROM\s+\w+\b", f"FROM {anchor_in_sql}", main_part, count=1, flags=re.IGNORECASE)
    select_from_part = re.sub(
        re.escape(joins_with_conditions[anchor_join_idx][2]),
        new_first_join,
        select_from_part,
        count=1,
    )
    # When the anchor was not the first JOIN (anchor_join_idx != 0), the original FROM table is now missing
    # as a JOIN. Replace the first join line (which linked old FROM to next table) with JOIN current_from ON ...
    if anchor_join_idx != 0 and joins_with_conditions:
        first_join_line = joins_with_conditions[0][2]
        first_join_cond = re.search(r"\bON\s+(.+)$", first_join_line, re.DOTALL | re.IGNORECASE)
        first_join_cond_str = first_join_cond.group(1).strip() if first_join_cond else "1=1"
        join_old_from = f"JOIN {current_from} ON {first_join_cond_str}"
        select_from_part = re.sub(re.escape(first_join_line), join_old_from, select_from_part, count=1)

    result = select_from_part + rest
    logger.info(f"Rewrote SQL to start from anchor table '{anchor_table}' (was FROM {current_from})")
    return result


def _build_domain_required_joins_section(state: SQLGraphState) -> str:
    """Build section for domain-required joins that must be included in JOIN_PATH"""
    domain_joins = state.get("domain_required_joins", [])
    
    if not domain_joins:
        return ""
    
    section = "\n\nDOMAIN-REQUIRED JOINS (MUST INCLUDE):\n"
    section += "The following joins are REQUIRED by domain concepts and MUST be included:\n"
    for dj in domain_joins:
        section += f"- JOIN: {dj['condition']} (N:1, 1.00)\n"
        section += f"  Note: {dj['note']}\n"
    section += "\nThese joins are MANDATORY. Include them even if not in suggested paths above.\n"
    section += "They ensure that human-readable names and domain-specific data are available.\n"
    
    return section


def _build_domain_filter_instructions(state: SQLGraphState, ctx: SQLContext) -> str:
    """Build instructions for domain filters and calculation hints in SQL generation prompt"""
    domain_resolutions = state.get("domain_resolutions", [])
    selected_tables = state.get("tables", [])
    
    instructions = ""
    
    # First, include full domain context (with calculation hints)
    if domain_resolutions:
        domain_context = format_domain_context(domain_resolutions)
        if domain_context:
            instructions += "\n\n" + domain_context + "\n"
    
    # Get domain-based WHERE clauses
    domain_clauses = build_where_clauses(domain_resolutions) if domain_resolutions else []
    
    # Get default table filter clauses
    default_clauses = []
    if ctx.domain_ontology and ctx.domain_ontology.registry:
        default_clauses = get_default_table_filter_clauses(selected_tables, ctx.domain_ontology.registry)
    
    # Merge all clauses
    all_clauses = domain_clauses + default_clauses
    
    if all_clauses:
        instructions += "\n\nDOMAIN FILTER REQUIREMENTS:\n"
        instructions += "You MUST include these WHERE clause conditions to filter by domain concepts:\n"
        for clause in all_clauses:
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


def _inject_domain_filters(sql: str, domain_resolutions: List[Dict[str, Any]], default_clauses: List[str] = None) -> str:
    """Inject domain filter WHERE clauses into generated SQL."""
    where_clauses = build_where_clauses(domain_resolutions)
    
    # Merge with default table filter clauses
    if default_clauses:
        where_clauses.extend(default_clauses)
    
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

    anchor_instruction = ""
    if state.get("anchor_table"):
        anchor_instruction = f"""
PRIMARY TABLE INSTRUCTION:
- Start your query with: FROM {state['anchor_table']}
- This is the main entity the user is asking about
- Join other tables TO this primary table

"""

    prompt = f"""
Generate a MySQL SELECT query using ONLY the columns shown below.

All tables needed for this query (with their actual columns):
{schema_context}
{excluded_columns_hint}
{anchor_instruction}
CRITICAL RULES:
- Use ONLY the columns listed above for each table - do NOT guess or invent column names
- DO NOT select id, createdBy, updatedBy, createdAt, updatedAt columns UNLESS:
  * The table is workOrder or inspection (these explicitly show id)
  * The user explicitly asks for IDs or audit fields
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
{_build_domain_required_joins_section(state)}

IMPORTANT: {bridge_example} Only include bridge tables if they are explicitly listed in the JOIN_PATH above. Do NOT add unnecessary bridge tables when direct foreign keys exist.
{_build_domain_filter_instructions(state, ctx)}

CRITICAL FORMATTING: Return ONLY the SQL query. Do NOT wrap it in markdown code blocks (no ```sql). Just return the raw SQL query text.
"""

    logger.info(f"[PROMPT] generate_sql prompt:\n{prompt}")
    response = ctx.llm.invoke(prompt)
    raw_sql = str(response.content).strip() if hasattr(response, "content") and response.content else ""
    if raw_sql.startswith("```"):
        lines = raw_sql.split("\n")
        raw_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
    logger.info(f"Generated SQL (before rewriting): {raw_sql}")

    # Validate that SELECT doesn't reference tables not in FROM/JOIN
    _validate_select_tables(raw_sql)

    domain_resolutions = state.get("domain_resolutions", [])
    
    # Get default table filter clauses
    default_clauses = []
    if ctx.domain_ontology and ctx.domain_ontology.registry:
        selected_tables = state.get("tables", [])
        default_clauses = get_default_table_filter_clauses(selected_tables, ctx.domain_ontology.registry)
    
    # Inject both domain and default table filters
    if domain_resolutions or default_clauses:
        raw_sql = _inject_domain_filters(raw_sql, domain_resolutions, default_clauses)
        logger.info(f"Injected filters into SQL (domain: {len(domain_resolutions)}, default: {len(default_clauses)})")

    raw_sql = _deduplicate_joins(raw_sql)
    
    # Validate scoped joins
    required_constraints = get_required_join_constraints(
        state.get("domain_resolutions", []),
        ctx.domain_ontology
    )
    
    if required_constraints:
        missing_constraints = validate_scoped_joins(raw_sql, required_constraints)
        if missing_constraints:
            logger.warning(f"Missing scoped join constraints: {missing_constraints}")
            # Add to validation notes for potential correction
            state["validation_notes"] = state.get("validation_notes", []) + [
                f"Missing required join constraints: {', '.join(missing_constraints)}"
            ]

    rewritten_sql = rewrite_secure_tables(raw_sql)
    if state.get("anchor_table"):
        rewritten_sql = _rewrite_sql_from_anchor(rewritten_sql, state["anchor_table"])
    logger.info(f"Rewritten SQL (after secure view conversion): {rewritten_sql}")
    state["sql"] = rewritten_sql
    return state
