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
)


@trace_step("filter_relationships")
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

    candidate_bridges = find_bridge_tables(
        selected, rels, ctx.join_graph["tables"], confidence_threshold=confidence_threshold
    )
    on_path = get_bridges_on_paths(selected, ctx.path_finder)
    domain_bridges = get_domain_bridges(
        state.get("domain_resolutions", []), ctx.domain_ontology, ctx.join_graph["tables"]
    )
    relevant = on_path | (domain_bridges & candidate_bridges)
    exclude_patterns = get_exclude_bridge_patterns(
        state.get("domain_resolutions", []), ctx.domain_ontology
    )
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


@trace_step("plan_joins")
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

    for path in suggested_paths:
        path.pop("confidence_sort", None)

    rels_display = allowed_rels[:settings.sql_max_relationships_display]

    crew_to_employee_path = None
    for path_info in suggested_paths:
        if (path_info["from"] == "crew" and path_info["to"] == "employee") or (
            path_info["from"] == "employee" and path_info["to"] == "crew"
        ):
            crew_to_employee_path = path_info
            break

    relevant_path_section = ""
    if crew_to_employee_path:
        relevant_path_section = f"""
{"=" * 70}
MOST RELEVANT PATH FOR THIS QUESTION:
{"=" * 70}
To connect crew to employee, use this EXACT path from the suggestions above:

  Path: {crew_to_employee_path['path']}
  Tables needed: {', '.join(crew_to_employee_path['tables_used'])}

  JOIN_PATH steps (copy these EXACTLY):
{chr(10).join(f"  - {step}" for step in crew_to_employee_path['join_steps'])}

  DO NOT create your own path - use the one above!
{"=" * 70}
"""

    domain_filter_hints = ""
    domain_resolutions = state.get("domain_resolutions", [])
    if domain_resolutions:
        domain_filter_hints = "\n" + format_domain_context(domain_resolutions) + "\n"
        domain_filter_hints += "IMPORTANT: Plan joins to include tables needed for domain filters.\n"
        domain_filter_hints += "The WHERE clause will filter based on these domain concepts.\n"

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

{relevant_path_section}

Direct and transitive relationships available (for reference only - prefer suggested paths):
{json.dumps(rels_display[:settings.sql_max_relationships_in_prompt], indent=2)}
{domain_filter_hints}
Task:
- PRIMARY: Use the suggested paths above - they are computed by the graph algorithm and are correct
- If a PREFERRED JOIN CHAIN is stated above for this domain, USE THAT CHAIN in order (do not use a shorter path that skips tables in the chain)
- If a suggested path exists for the tables you need to connect, USE IT EXACTLY as shown
- Only construct your own path if no suggested path exists
- Prefer shorter paths (fewer hops) when multiple options exist, unless a PREFERRED JOIN CHAIN is given
- Use cardinality to prefer safer joins (N:1 / 1:1 over N:N)
- CRITICAL: If connecting two tables requires a bridge table (like 'user' connecting 'crew' to 'employee'),
  you MUST include ALL intermediate tables in the JOIN_PATH. Do NOT skip bridge tables.
- If no allowed join path exists, say "NO_JOIN_PATH".

Question: {state['question']}

Output format:
JOIN_PATH:
- tableA.col = tableB.col (cardinality, confidence)
- tableB.col = tableC.col (cardinality, confidence)  # if bridge table needed
- ...

NOTES:
- brief reasoning about path choice
- explicitly state if using bridge tables and why
"""

    logger.debug(f"[PROMPT] plan_joins prompt:\n{prompt}")
    response = ctx.llm.invoke(prompt)
    state["join_plan"] = str(response.content) if hasattr(response, "content") and response.content else ""
    return state
