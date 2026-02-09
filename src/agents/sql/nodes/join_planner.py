"""
Join planner nodes - filter relationships and plan joins
"""

import json
from loguru import logger

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.utils import trace_step
from src.config.settings import settings
from src.domain.ontology.formatter import format_domain_context
from src.agents.sql.planning import (
    find_bridge_tables,
    get_bridges_on_paths,
    get_domain_bridges,
    get_exclude_bridge_patterns,
    get_excluded_columns,
    build_scoped_join_hints,
    get_join_type_hints,
)
from src.agents.sql.prompt_helpers import build_bridge_table_example


def filter_relationships_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Filter and expand relationships to include transitive join paths.
    """
    state = dict(state)
    rels = ctx.join_graph["relationships"]
    selected = set(state["tables"])
    confidence_threshold = settings.sql_confidence_threshold

    direct_relationships = [
        r
        for r in rels
        if r["from_table"] in selected
        and r["to_table"] in selected
        and float(r.get("confidence", 0)) >= confidence_threshold
    ]

    logger.info(f"Found {len(direct_relationships)} direct relationships between {len(selected)} tables")

    expanded_relationships = ctx.path_finder.expand_relationships(
        tables=list(selected),
        direct_relationships=direct_relationships,
        max_hops=4,
    )

    logger.info(
        f"Expanded to {len(expanded_relationships)} relationships "
        f"(added {len(expanded_relationships) - len(direct_relationships)} transitive paths)"
    )

    # Get table metadata and exclusion patterns BEFORE bridge discovery
    table_metadata = ctx.join_graph.get("table_metadata", {})
    exclude_patterns = get_exclude_bridge_patterns(
        state.get("domain_resolutions", []), ctx.domain_ontology
    )
    
    # Find bridge tables with semantic filtering
    candidate_bridges = find_bridge_tables(
        selected, 
        rels, 
        ctx.join_graph["tables"], 
        table_metadata=table_metadata,
        exclude_patterns=exclude_patterns,
        confidence_threshold=confidence_threshold
    )
    on_path = get_bridges_on_paths(selected, ctx.path_finder)
    domain_bridges = get_domain_bridges(
        state.get("domain_resolutions", []), ctx.domain_ontology, ctx.join_graph["tables"]
    )
    relevant = on_path | (domain_bridges & candidate_bridges)
    # Note: exclude_patterns already applied in find_bridge_tables, but keep for safety
    if exclude_patterns:
        relevant = {t for t in relevant if not any(p.lower() in t.lower() for p in exclude_patterns)}
    if relevant:
        bridge_tables = relevant
    elif candidate_bridges:
        bridge_tables = candidate_bridges
    else:
        bridge_tables = set()

    if bridge_tables:
        logger.info(f"Auto-adding {len(bridge_tables)} bridge tables: {bridge_tables}")
        selected.update(bridge_tables)
        state["tables"] = list(selected)

    excluded_columns = get_excluded_columns(
        state.get("domain_resolutions", []), ctx.domain_ontology, ctx.join_graph["tables"]
    )
    if excluded_columns:
        before = len(expanded_relationships)
        expanded_relationships = [
            r
            for r in expanded_relationships
            if r.get("from_column") not in excluded_columns.get(r.get("from_table"), set())
            and r.get("to_column") not in excluded_columns.get(r.get("to_table"), set())
        ]
        if len(expanded_relationships) < before:
            logger.info(f"Filtered {before - len(expanded_relationships)} relationships using domain exclude_columns")

    state["allowed_relationships"] = expanded_relationships
    return state


def plan_joins_node(state: SQLGraphState, ctx: SQLContext) -> SQLGraphState:
    """
    Plan the join path(s) using allowed relationships.
    """
    state = dict(state)
    selected_tables = state["tables"]
    allowed_rels = state["allowed_relationships"]

    excluded_columns = get_excluded_columns(
        state.get("domain_resolutions", []), ctx.domain_ontology, ctx.join_graph["tables"]
    )
    suggested_paths = []
    for i, table1 in enumerate(selected_tables):
        for table2 in selected_tables[i + 1 :]:
            path = ctx.path_finder.find_shortest_path(table1, table2, max_hops=4)
            if path:
                if excluded_columns and any(
                    rel.get("from_column") in excluded_columns.get(rel.get("from_table"), set())
                    or rel.get("to_column") in excluded_columns.get(rel.get("to_table"), set())
                    for rel in path
                ):
                    continue
                path_desc = ctx.path_finder.get_path_description(path)
                tables_in_path = set()
                avg_confidence = (
                    sum(float(rel.get("confidence", 0.5)) for rel in path) / len(path)
                    if path
                    else 0
                )

                for rel in path:
                    tables_in_path.add(rel["from_table"])
                    tables_in_path.add(rel["to_table"])

                suggested_paths.append(
                    {
                        "from": table1,
                        "to": table2,
                        "path": path_desc,
                        "hops": len(path),
                        "confidence_sort": avg_confidence,
                        "tables_used": sorted(tables_in_path),
                        "join_steps": [
                            f"{rel['from_table']}.{rel['from_column']} = {rel['to_table']}.{rel['to_column']}"
                            for rel in path
                        ],
                    }
                )

    suggested_paths.sort(key=lambda x: (x["hops"], -x["confidence_sort"]))
    suggested_paths = suggested_paths[:settings.sql_max_suggested_paths]

    # When anchor_table is set, prefer paths that start FROM the anchor so the LLM generates correct FROM clause
    anchor_table = state.get("anchor_table")
    if anchor_table and suggested_paths:
        with_anchor_first = [p for p in suggested_paths if p.get("from") == anchor_table]
        other_paths = [p for p in suggested_paths if p.get("from") != anchor_table]
        if with_anchor_first:
            suggested_paths = with_anchor_first + other_paths

    for path in suggested_paths:
        path.pop("confidence_sort", None)

    rels_display = allowed_rels[:settings.sql_max_relationships_display]

    domain_filter_hints = ""
    domain_resolutions = state.get("domain_resolutions", [])
    if domain_resolutions:
        domain_filter_hints = "\n" + format_domain_context(domain_resolutions) + "\n"
        domain_filter_hints += "IMPORTANT: Plan joins to include tables needed for domain filters.\n"
        domain_filter_hints += "The WHERE clause will filter based on these domain concepts.\n"
    
    # Add display attributes hints for template relationships
    display_hints = ""
    if settings.display_attributes_enabled and ctx.display_attributes:
        template_rels = ctx.display_attributes.get_tables_with_template_relationships(selected_tables)
        if template_rels:
            display_hints = "\n\nDISPLAY ATTRIBUTES - TEMPLATE RELATIONSHIPS:\n"
            display_hints += "The following tables need joins to their templates for human-readable names:\n"
            for table, rel_config in template_rels.items():
                template_table = rel_config.get("template_table")
                via_tables = rel_config.get("via_tables", [])
                if via_tables:
                    path = f"{table} → {' → '.join(via_tables)} → {template_table}"
                else:
                    path = f"{table} → {template_table}"
                display_hints += f"  - {path}\n"
            display_hints += "IMPORTANT: Include these joins in your plan to show descriptive names.\n"
    
    # Inject required joins from domain terms
    domain_required_joins = []
    if ctx.domain_ontology and domain_resolutions:
        for res in domain_resolutions:
            required_joins = res.get("required_joins", [])
            if required_joins:
                for join_condition in required_joins:
                    # Parse join condition to extract tables and columns
                    # Format: "table1.col1 = table2.col2"
                    domain_required_joins.append({
                        "condition": join_condition,
                        "term": res.get("term"),
                        "note": f"Required by domain term '{res.get('term')}'"
                    })
                logger.info(
                    f"Domain term '{res.get('term')}' requires {len(required_joins)} joins"
                )
    
    if domain_required_joins:
        state["domain_required_joins"] = domain_required_joins
    
    def _build_domain_joins_hint(joins_list):
        """Build hint section for domain-required joins in join planner prompt"""
        if not joins_list:
            return ""
        hint = "\n\n" + "=" * 70 + "\n"
        hint += "DOMAIN-REQUIRED JOINS (MUST INCLUDE IN JOIN_PATH)\n"
        hint += "=" * 70 + "\n"
        hint += "The following joins are REQUIRED by domain concepts:\n\n"
        for dj in joins_list:
            hint += f"- JOIN: {dj['condition']} (N:1, 1.00)\n"
            hint += f"  Reason: {dj['note']}\n"
        hint += "\nThese joins are MANDATORY. You MUST include them in your JOIN_PATH.\n"
        hint += "They ensure that human-readable names and domain-specific data are available.\n"
        hint += "=" * 70 + "\n"
        return hint

    selected_set = set(selected_tables)
    if ctx.domain_ontology and domain_resolutions:
        terms_registry = ctx.domain_ontology.registry.get("terms", {})
        for res in domain_resolutions:
            term = res.get("term")
            if not term or term not in terms_registry:
                continue
            primary = terms_registry[term].get("resolution", {}).get("primary", {})
            anchor = primary.get("anchor_table")
            chain_tables = primary.get("tables", [])
            if (
                anchor
                and len(chain_tables) >= 2
                and set(chain_tables).issubset(selected_set)
            ):
                chain_str = " → ".join(chain_tables)
                domain_filter_hints += f"\nPREFERRED JOIN CHAIN for this domain (use in JOIN_PATH, in order): {chain_str}\n"
                domain_filter_hints += "Include all tables in this chain; do not skip to a shorter path.\n"
                break

    bridge_example = build_bridge_table_example(ctx.join_graph)

    anchor_instruction = ""
    if state.get("anchor_table"):
        anchor_instruction = f"\nCRITICAL - ANCHOR TABLE: The first table in JOIN_PATH must be '{state['anchor_table']}'. Start with a step like: - JOIN: {state['anchor_table']}.<column> = <other>.<column> so the generated SQL uses FROM {state['anchor_table']} and returns all rows.\n"
    
    # Get scoped join hints
    scoped_join_hints = build_scoped_join_hints(
        state.get("domain_resolutions", []),
        ctx.domain_ontology,
        ctx.join_graph
    )
    
    # Get join type hints (LEFT JOIN vs JOIN)
    join_type_hints = get_join_type_hints(selected_tables, ctx.join_graph)

    prompt = f"""
You are planning SQL joins. You MUST ONLY use the allowed relationships.

Selected tables:
{selected_tables}

{"=" * 70}
CRITICAL: USE THE SUGGESTED PATHS BELOW - THEY ARE COMPUTED BY THE GRAPH ALGORITHM
{"=" * 70}

Suggested optimal paths (from graph algorithm):
These paths are computed by the graph algorithm and include ALL bridge tables needed.
{json.dumps(suggested_paths, indent=2) if suggested_paths else "No paths found"}

Direct and transitive relationships available (for reference only - prefer suggested paths):
{json.dumps(rels_display[:settings.sql_max_relationships_in_prompt], indent=2)}
{anchor_instruction}
{domain_filter_hints}
{display_hints}
{_build_domain_joins_hint(domain_required_joins)}
{join_type_hints}
{scoped_join_hints}
Task:
- PRIMARY: Use the suggested paths above - they are computed by the graph algorithm and are correct
- CRITICAL (when anchor table is set): The FIRST table in your JOIN_PATH must be the primary entity. Start with a step where that table is on the left (e.g. - JOIN: workOrder.id = crew.workOrderId). This ensures the SQL uses FROM workOrder and returns all rows for that entity; starting from another table (e.g. user or expense) will return too few rows.
- PREFER DIRECT RELATIONSHIPS: When two tables have a direct foreign key, use it directly (e.g., workTime.employeeId -> employee.id)
- AVOID UNNECESSARY BRIDGES: Do NOT add bridge tables if a direct path already exists between the tables
  * Example: If workTime has employeeId FK to employee, DO NOT use employeeCrew as a bridge
  * Example: If workTime has workTimeTypeId FK to workTimeType, DO NOT use employeeRoleWorkTimeType as a bridge
- If a PREFERRED JOIN CHAIN is stated above for this domain, USE THAT CHAIN in order (do not use a shorter path that skips tables in the chain)
- If a suggested path exists for the tables you need to connect, USE IT EXACTLY as shown
- Only construct your own path if no suggested path exists
- Prefer shorter paths (fewer hops) when multiple options exist, unless a PREFERRED JOIN CHAIN is given
- Use cardinality to prefer safer joins (N:1 / 1:1 over N:N)
- CRITICAL: {bridge_example} Only use bridge tables when NO direct path exists between the tables.
- CRITICAL: If SCOPED JOIN REQUIREMENTS are listed above, combine multiple conditions into ONE JOIN step using AND
- CRITICAL: Prefix each join with the correct type (LEFT JOIN or JOIN) as specified in JOIN TYPE REQUIREMENTS
- If no allowed join path exists, say "NO_JOIN_PATH".

Question: {state['question']}

Output format:
JOIN_PATH:
- JOIN: tableA.col = tableB.col (cardinality, confidence)
- JOIN: tableB.col = tableC.col (cardinality, confidence)  # if bridge table needed
- LEFT JOIN: tableX.col = tableY.col (cardinality, confidence)
 AND tableY.col2 = tableZ.col2 (cardinality, confidence)  # if compound/scoped join needed
- ...

NOTES:
- brief reasoning about path choice
- explicitly state if using bridge tables and why
- mention which tables use LEFT JOIN and why

IMPORTANT: Do NOT include SQL code in this response. Only provide the JOIN_PATH and NOTES as specified above.
"""

    logger.debug(f"[PROMPT] plan_joins prompt:\n{prompt}")
    response = ctx.llm.invoke(prompt)
    state["join_plan"] = str(response.content) if hasattr(response, "content") and response.content else ""
    return state
