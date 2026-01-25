from __future__ import annotations

import json
import os
import time
import uuid
import functools
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from src.utils.config import settings
from src.utils.logger import logger
from src.utils.path_finder import JoinPathFinder
from src.tools.sql_tool import sql_tool
from src.sql.secure_views import (
    SECURE_VIEW_MAP,
    rewrite_secure_tables,
    validate_tables_exist,
    is_secure_table,
    to_secure_view
)

# TODO change it for join_graph_validated.json when ready
JOIN_GRAPH_PATH = os.path.join("artifacts", "join_graph_merged.json")


class SQLGraphState(TypedDict):
    question: str
    tables: List[str]
    allowed_relationships: List[Dict[str, Any]]
    join_plan: str
    sql: str
    result: Optional[str]
    retries: int
    final_answer: Optional[str]


def load_join_graph() -> Dict[str, Any]:
    with open(JOIN_GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def trace_step(step_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, state, *args, **kwargs):
            trace_id = state.get('trace_id') or str(uuid.uuid4())
            state['trace_id'] = trace_id
            start = time.time()
            logger.info(f"[TRACE] step_start: {step_name} | trace_id={trace_id} | input_keys={list(state.keys())}")
            try:
                result = func(self, state, *args, **kwargs)
                duration = time.time() - start
                logger.info(f"[TRACE] step_end: {step_name} | trace_id={trace_id} | duration_ms={int(duration * 1000)} | output_keys={list(result.keys())}")
                return result
            except Exception as e:
                logger.error(f"[TRACE] step_error: {step_name} | trace_id={trace_id} | error={e} | state_keys={list(state.keys())}")
                raise
        return wrapper
    return decorator


class SQLGraphAgent:
    """
    LangGraph-based SQL agent:

    NL Question
       ↓
    [Table Selector]
       ↓
    [Join Planner]
       ↓
    [SQL Generator]
       ↓
    [Execution + Validator]
       ↓
    Answer
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            max_completion_tokens=settings.max_output_tokens,
        )
        self.join_graph = load_join_graph()
        
        # Initialize path finder for efficient transitive join path discovery
        self.path_finder = JoinPathFinder(
            self.join_graph["relationships"],
            confidence_threshold=0.70
        )
        
        self.workflow = self._build()

        logger.info("SQLGraphAgent initialized with path finder")

    # 1) Table Selector
    @trace_step('select_tables')
    def _select_tables(self, state: SQLGraphState) -> SQLGraphState:
        """
        Select minimal set of tables needed to answer the question.
        
        IMPORTANT: This works with ACTUAL tables/views from the join graph.
        - Join graph contains real tables (both base tables and secure views)
        - We select based on what exists, not what we want to rewrite
        - Rewriting happens later in SQL generation
        """
        all_tables = list(self.join_graph["tables"].keys())

        prompt = f"""
Select ONLY the minimal set of tables needed to answer the question.

Rules:
- Return 3 to 8 tables only
- Select from ACTUAL available tables (join graph reflects reality)
- If unsure, return fewer tables
- DO NOT invent table names that don't exist

Available tables (subset shown if large):
{', '.join(all_tables[:250])}

Question: {state['question']}

Return ONLY a JSON array of table names that ACTUALLY EXIST in the list above. No explanation, no markdown, no text, just the array.
"""
        logger.info(f"[PROMPT] select_tables prompt:\n{prompt}")
        raw = self.llm.invoke(prompt).content.strip()
        logger.info(f"Raw LLM output: {raw}")
        try:
            tables = json.loads(raw)
            tables = [t for t in tables if t in self.join_graph["tables"]]
        except Exception as e:
            logger.warning(f"Failed to parse table selection: {e}. Raw output: {raw}")
            # Fallback: use safe defaults based on question
            q = state["question"].lower()
            fallback = []
            if "work" in q:
                for t in ["employee", "workOrder", "workTime", "crew", "employeeCrew"]:
                    if t in self.join_graph["tables"]:
                        fallback.append(t)
            elif "employee" in q:
                if "employee" in self.join_graph["tables"]:
                    fallback.append("employee")
            if not fallback:
                fallback = list(all_tables[:5])
            tables = fallback
            logger.info(f"Fallback selected tables: {tables}")
        logger.info(f"Selected tables: {tables}")
        state["tables"] = tables
        return state

    # 2) Build allowed relationships for those tables (including transitive paths)
    @trace_step('filter_relationships')
    def _filter_relationships(self, state: SQLGraphState) -> SQLGraphState:
        """
        Filter and expand relationships to include transitive join paths.
        
        This step:
        1. Finds direct relationships between selected tables
        2. Uses path finder to discover transitive paths (multi-hop joins)
        3. Expands allowed relationships to include both direct and transitive paths
        """
        rels = self.join_graph["relationships"]
        selected = set(state["tables"])

        # Keep direct relationships:
        # - edges where both endpoints are in selected tables
        # - confidence threshold
        CONF_THRESH = 0.70

        direct_relationships = [
            r for r in rels
            if r["from_table"] in selected
            and r["to_table"] in selected
            and float(r.get("confidence", 0)) >= CONF_THRESH
        ]

        logger.info(
            f"Found {len(direct_relationships)} direct relationships between {len(selected)} tables"
        )

        # Expand with transitive paths using path finder
        # This finds shortest paths between tables that aren't directly connected
        expanded_relationships = self.path_finder.expand_relationships(
            tables=list(selected),
            direct_relationships=direct_relationships,
            max_hops=4
        )

        logger.info(
            f"Expanded to {len(expanded_relationships)} relationships "
            f"(added {len(expanded_relationships) - len(direct_relationships)} transitive paths)"
        )

        # Log some example paths for debugging
        if len(expanded_relationships) > len(direct_relationships):
            # Find a transitive path example
            for table1 in selected:
                for table2 in selected:
                    if table1 != table2:
                        path = self.path_finder.find_shortest_path(table1, table2, max_hops=4)
                        if path and len(path) > 1:
                            path_desc = self.path_finder.get_path_description(path)
                            logger.debug(f"Example transitive path: {path_desc}")
                            break
                else:
                    continue
                break

        state["allowed_relationships"] = expanded_relationships
        return state

    # 3) Join Planner (correctness anchor)
    @trace_step('plan_joins')
    def _plan_joins(self, state: SQLGraphState) -> SQLGraphState:
        """
        Plan the join path(s) using allowed relationships (including transitive paths).
        
        This uses graph algorithms to find optimal join paths, then uses LLM
        to validate and format the plan.
        """
        selected_tables = state['tables']
        allowed_rels = state['allowed_relationships']
        
        # Use path finder to suggest optimal paths between selected tables
        # This provides concrete paths that the LLM can validate
        suggested_paths = []
        for i, table1 in enumerate(selected_tables):
            for table2 in selected_tables[i+1:]:
                path = self.path_finder.find_shortest_path(table1, table2, max_hops=4)
                if path:
                    path_desc = self.path_finder.get_path_description(path)
                    suggested_paths.append({
                        "from": table1,
                        "to": table2,
                        "path": path_desc,
                        "hops": len(path)
                    })
        
        # Format relationships for prompt (limit to avoid token bloat)
        rels_display = allowed_rels[:50]  # Limit to first 50 for prompt size
        
        prompt = f"""
You are planning SQL joins. You MUST ONLY use the allowed relationships.

Selected tables:
{selected_tables}

Direct and transitive relationships available (use only these):
{json.dumps(rels_display, indent=2)}

Suggested optimal paths (from graph algorithm):
{json.dumps(suggested_paths, indent=2) if suggested_paths else "No paths found"}

Task:
- Propose the minimal join path(s) needed for the question.
- Prefer shorter paths (fewer hops) when multiple options exist.
- Use cardinality to prefer safer joins (N:1 / 1:1 over N:N).
- You can use the suggested paths above, or construct your own from allowed relationships.
- If no allowed join path exists, say "NO_JOIN_PATH".

Question: {state['question']}

Output format:
JOIN_PATH:
- tableA.col = tableB.col (cardinality, confidence)
- ...

NOTES:
- brief reasoning about path choice
"""
        logger.info(f"[PROMPT] plan_joins prompt:\n{prompt}")
        state["join_plan"] = self.llm.invoke(prompt).content
        return state

    # 4) SQL Generator
    @trace_step('generate_sql')
    def _generate_sql(self, state: SQLGraphState) -> SQLGraphState:
        """
        Generate SQL query based on join plan.
        
        CRITICAL: LLM generates SQL using logical table names (e.g., 'employee', 'workOrder').
        The rewrite_secure_tables() function will automatically convert them to secure views.
        
        This separation ensures:
        - LLM doesn't hallucinate secure_* variants for tables that don't need them
        - Rewriting is deterministic and based on SECURE_VIEW_MAP
        - No more secure_inspections errors
        """
        table_schemas = []
        for table_name in state["tables"]:
            if table_name in self.join_graph["tables"]:
                columns = self.join_graph["tables"][table_name].get("columns", [])
                table_schemas.append(f"{table_name}: {', '.join(columns[:20])}")
        schema_context = "\n".join(table_schemas)

        prompt = f"""
Generate a MySQL SELECT query using ONLY the columns shown below.

Table schemas (ACTUAL columns - use these exact names):
{schema_context}

Rules:
- Use ONLY columns listed above (do NOT use snake_case like start_date, use startTime)
- Use ONLY joins explicitly listed in JOIN_PATH
- Use LIMIT {settings.max_query_rows} unless it's an aggregate COUNT/SUM/etc
- Keep it simple (minimal joins)
- Use logical table names (workOrder not secure_workorder)
- DO NOT add secure_ prefix - the system handles that automatically

Question: {state['question']}

Selected tables: {state['tables']}

Join plan: {state['join_plan']}

Return ONLY the SQL query, nothing else.
"""
        logger.info(f"[PROMPT] generate_sql prompt:\n{prompt}")
        raw_sql = self.llm.invoke(prompt).content.strip()
        if raw_sql.startswith("```"):
            lines = raw_sql.split("\n")
            raw_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
        logger.info(f"Generated SQL (before rewriting): {raw_sql}")
        rewritten_sql = rewrite_secure_tables(raw_sql)
        logger.info(f"Rewritten SQL (after secure view conversion): {rewritten_sql}")
        state["sql"] = rewritten_sql
        return state

    # 5) Execution + Validator (retry-on-empty)
    @trace_step('execute_and_validate')
    def _execute_and_validate(self, state: SQLGraphState) -> SQLGraphState:
        logger.info(f"Executing SQL: {state['sql']}")

        try:
            res = sql_tool.run_query(state["sql"])
        except Exception as e:
            # hard fail -> no retry unless you want it
            state["result"] = f"Error executing query: {e}"
            return state

        # Normalize "empty" – depends on SQLDatabase.run formatting
        is_empty = (res is None) or (str(res).strip() == "") or ("[]" in str(res).strip())

        # If empty and we haven't retried: ask the generator to reconsider joins/filters
        if is_empty and state["retries"] < 1:
            state["retries"] += 1

            # Inject feedback into join plan and regenerate SQL once
            feedback = f"""
The query returned an empty result set.
Re-check join direction, join keys, and filters (dates especially).
If date filters exist, ensure you're filtering on the correct table columns.
"""

            # Update join_plan using feedback (keeps constraints)
            state["join_plan"] = state["join_plan"] + "\n\n" + feedback
            # Signal to go back to SQL generation (not table selection)
            state["result"] = None
            return state

        state["result"] = str(res)
        return state

    # 6) Final answer formatting (minimal)
    @trace_step('finalize')
    def _finalize(self, state: SQLGraphState) -> SQLGraphState:
        if state.get("result") is None:
            state["final_answer"] = "No result."
            return state

        # You can optionally add a tiny "explain result" prompt if needed.
        # For now keep pass-through (like your orchestrator finalize philosophy).
        state["final_answer"] = state["result"]
        return state

    def _route_after_execute(self, state: SQLGraphState) -> str:
        # If we set retries and result is None, we want to regenerate SQL
        if state["retries"] > 0 and state.get("result") is None:
            return "generate_sql"
        return "finalize"

    def _build(self):
        g = StateGraph(SQLGraphState)
        g.add_node("select_tables", self._select_tables)
        g.add_node("filter_relationships", self._filter_relationships)
        g.add_node("plan_joins", self._plan_joins)
        g.add_node("generate_sql", self._generate_sql)
        g.add_node("execute", self._execute_and_validate)
        g.add_node("finalize", self._finalize)

        g.set_entry_point("select_tables")
        g.add_edge("select_tables", "filter_relationships")
        g.add_edge("filter_relationships", "plan_joins")
        g.add_edge("plan_joins", "generate_sql")
        g.add_edge("generate_sql", "execute")

        g.add_conditional_edges(
            "execute",
            self._route_after_execute,
            {
                "generate_sql": "generate_sql",
                "finalize": "finalize",
            },
        )

        g.add_edge("finalize", END)
        return g.compile()

    def query(self, question: str) -> str:
        state: SQLGraphState = {
            "question": question,
            "tables": [],
            "allowed_relationships": [],
            "join_plan": "",
            "sql": "",
            "result": None,
            "retries": 0,
            "final_answer": None,
        }
        out = self.workflow.invoke(state)
        return out.get("final_answer") or "No answer generated."
