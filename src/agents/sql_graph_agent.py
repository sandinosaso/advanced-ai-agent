from __future__ import annotations

import json
import os
import time
import uuid
import functools
import ast
import re
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from src.utils.config import settings, create_llm
from src.utils.logger import logger
from src.utils.path_finder import JoinPathFinder
from src.tools.sql_tool import sql_tool
from src.utils.sql.secure_views import (
    rewrite_secure_tables,
    from_secure_view
)

# TODO change it for join_graph_validated.json when ready
# Find project root (this file is at src/agents/sql_graph_agent.py)
_project_root = Path(__file__).parent.parent.parent
JOIN_GRAPH_PATH = _project_root / "artifacts" / "join_graph_merged.json"


class SQLGraphState(TypedDict):
    question: str
    tables: List[str]
    allowed_relationships: List[Dict[str, Any]]
    join_plan: str
    sql: str
    result: Optional[str]
    column_names: Optional[List[str]]  # Column names from SQL query result
    retries: int
    final_answer: Optional[str]
    structured_result: Optional[List[Dict[str, Any]]]  # Structured array for BFF markdown conversion
    sql_correction_attempts: int  # Track correction attempts
    last_sql_error: Optional[str]  # Store last SQL error message
    correction_history: Optional[List[Dict[str, Any]]]  # Track correction attempts
    validation_errors: Optional[List[str]]  # Pre-execution validation errors


def load_join_graph() -> Dict[str, Any]:
    with open(str(JOIN_GRAPH_PATH), "r", encoding="utf-8") as f:
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
    LangGraph-based SQL agent for natural language to SQL conversion.
    
    Uses graph algorithms (Dijkstra) to discover optimal join paths between tables
    in a MySQL database with 100+ tables.

    Workflow:
    NL Question
       ↓
    [Table Selector] - LLM selects 5-10 relevant tables from 100+
       ↓
    [Filter Relationships] - Filters relationships by confidence threshold
       ↓
    [Path Finder] - Uses Dijkstra to find shortest join paths
       ↓
    [Join Planner] - LLM plans joins using discovered paths
       ↓
    [SQL Generator] - LLM generates SQL with proper joins
       ↓
    [Secure Rewriter] - Rewrites to use secure views for encrypted tables
       ↓
    [Pre-Validation] - Validates columns/joins before execution
       ↓
    [Execute] - Executes SQL query
       ↓
    [Correction Agent] - Fixes errors if validation/execution fails (iterative)
       ↓
    [Finalize] - Formats result (structured + raw)
       ↓
    Answer
    """

    def __init__(self):
        self.llm = create_llm(
            temperature=0,
            max_completion_tokens=settings.max_output_tokens,
        )
        self.join_graph = load_join_graph()
        
        # Initialize path finder for efficient transitive join path discovery
        self.path_finder = JoinPathFinder(
            self.join_graph["relationships"],
            confidence_threshold=settings.sql_confidence_threshold
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
Select the set of tables needed to answer the question.

Rules:
- Return 3 to 8 tables (prefer fewer tables that you need to answer the question)
- Select from ACTUAL available tables (join graph reflects reality)
- If unsure, return fewer tables
- DO NOT invent table names that don't exist

Available tables (subset shown if large):
{', '.join(all_tables[:settings.sql_max_tables_in_selection_prompt])}

Question: {state['question']}

Return ONLY a JSON array of table names that ACTUALLY EXIST in the list above. No explanation, no markdown, no text, just the array.
"""
        logger.info(f"[PROMPT] select_tables prompt:\n{prompt}")
        response = self.llm.invoke(prompt)
        raw = str(response.content).strip() if hasattr(response, 'content') and response.content else ""
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
                fallback = list(all_tables[:settings.sql_max_fallback_tables])
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
        # - confidence threshold (configurable via settings.sql_confidence_threshold)
        confidence_threshold = settings.sql_confidence_threshold

        direct_relationships = [
            r for r in rels
            if r["from_table"] in selected
            and r["to_table"] in selected
            and float(r.get("confidence", 0)) >= confidence_threshold
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
        
        # Automatically add bridge tables that connect two selected tables with high confidence
        # This ensures we include tables like employeeCrew when both crew and employee are selected
        bridge_tables = self._find_bridge_tables(selected, rels, confidence_threshold=0.9)
        if bridge_tables:
            logger.info(f"Auto-adding {len(bridge_tables)} bridge tables: {bridge_tables}")
            selected.update(bridge_tables)
            state["tables"] = list(selected)  # Update state with bridge tables

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
                    # Extract all tables in the path (including bridge tables)
                    tables_in_path = set()
                    # Calculate average confidence for path ranking
                    avg_confidence = sum(float(rel.get('confidence', 0.5)) for rel in path) / len(path) if path else 0
                    
                    for rel in path:
                        tables_in_path.add(rel['from_table'])
                        tables_in_path.add(rel['to_table'])
                    
                    suggested_paths.append({
                        "from": table1,
                        "to": table2,
                        "path": path_desc,
                        "hops": len(path),
                        "confidence_sort": avg_confidence,  # For sorting only, not in JSON
                        "tables_used": sorted(tables_in_path),  # Include bridge tables
                        "join_steps": [
                            f"{rel['from_table']}.{rel['from_column']} = {rel['to_table']}.{rel['to_column']}"
                            for rel in path
                        ]
                    })
        
        # Sort paths by relevance: shortest paths first, then by confidence
        suggested_paths.sort(key=lambda x: (x['hops'], -x['confidence_sort']))
        
        # Limit suggested paths to avoid token bloat (this is the main culprit!)
        # With 10 tables = 45 possible paths. Limiting to top 15 most relevant paths.
        suggested_paths = suggested_paths[:settings.sql_max_suggested_paths]
        
        # Remove sorting field before JSON serialization
        for path in suggested_paths:
            path.pop('confidence_sort', None)
        
        # Format relationships for prompt (limit to avoid token bloat)
        rels_display = allowed_rels[:settings.sql_max_relationships_display]
        
        # Find the most relevant suggested path for connecting crew to employee
        crew_to_employee_path = None
        for path_info in suggested_paths:
            if (path_info['from'] == 'crew' and path_info['to'] == 'employee') or \
               (path_info['from'] == 'employee' and path_info['to'] == 'crew'):
                crew_to_employee_path = path_info
                break
        
        # Build the most relevant path section
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
{json.dumps(rels_display[:settings.sql_max_relationships_in_prompt], indent=2)}  # Limited to avoid confusion

Task:
- PRIMARY: Use the suggested paths above - they are computed by the graph algorithm and are correct
- If a suggested path exists for the tables you need to connect, USE IT EXACTLY as shown
- Only construct your own path if no suggested path exists
- Prefer shorter paths (fewer hops) when multiple options exist
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
        logger.info(f"[PROMPT] plan_joins prompt:\n{prompt}")
        response = self.llm.invoke(prompt)
        state["join_plan"] = str(response.content) if hasattr(response, 'content') and response.content else ""
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
        - Rewriting is deterministic and based on the secure views system
        - No more secure_inspections errors
        """
        # Extract all tables mentioned in the join plan (including bridge tables)
        join_plan_text = state.get('join_plan', '')
        tables_from_join_plan = self._extract_tables_from_join_plan(join_plan_text)
        
        # Combine selected tables with tables from join plan (bridge tables)
        # This gives us ALL tables that will be used in the query
        all_tables = set(state["tables"]) | tables_from_join_plan
        
        # Build table schemas for ALL tables (selected + bridge) with their actual columns
        # This ensures the LLM knows exactly what columns are available in each table
        table_schemas = []
        for table_name in sorted(all_tables):
            if table_name in self.join_graph["tables"]:
                columns = self.join_graph["tables"][table_name].get("columns", [])
                # Show columns up to configured limit so LLM has complete information
                columns_str = ', '.join(columns[:settings.sql_max_columns_in_schema])
                if len(columns) > settings.sql_max_columns_in_schema:
                    columns_str += f" ... ({len(columns)} total columns)"
                table_schemas.append(f"{table_name}: {columns_str}")
            else:
                # Log warning if table not found in join graph
                logger.warning(f"Table '{table_name}' mentioned in join plan but not found in join graph")
        
        schema_context = "\n".join(table_schemas)

        # Parse JOIN_PATH to extract explicit join steps
        join_path_steps = self._parse_join_path_steps(state.get('join_plan', ''))
        
        prompt = f"""
Generate a MySQL SELECT query using ONLY the columns shown below.

All tables needed for this query (with their actual columns):
{schema_context}

CRITICAL RULES:
- Use ONLY the columns listed above for each table - do NOT guess or invent column names
- Follow the JOIN_PATH EXACTLY step by step - do NOT skip any tables or steps
- Include ALL tables shown above in your FROM/JOIN clauses
- Do NOT try to join tables directly if JOIN_PATH shows they require a bridge table
- Do NOT assume columns exist in the wrong table (e.g., firstName/lastName are in employee table, NOT in crew table)
- Use LIMIT {settings.max_query_rows} unless it's an aggregate COUNT/SUM/etc
- Use logical table names (workOrder not secure_workorder)
- DO NOT add secure_ prefix - the system handles that automatically

Question: {state['question']}

Join plan (follow this EXACTLY, step by step):
{state['join_plan']}

{"EXPLICIT JOIN STEPS (follow these in order):" + chr(10) + chr(10).join(f"{i+1}. {step}" for i, step in enumerate(join_path_steps)) if join_path_steps else ""}

IMPORTANT: If JOIN_PATH shows multiple steps (e.g., crew.createdBy = user.id, then user.employeeId = employee.id), 
you MUST include BOTH joins in your SQL. Do NOT skip the bridge table (user) and try to join crew directly to employee.

Return ONLY the SQL query, nothing else.
"""
        logger.info(f"[PROMPT] generate_sql prompt:\n{prompt}")
        response = self.llm.invoke(prompt)
        raw_sql = str(response.content).strip() if hasattr(response, 'content') and response.content else ""
        if raw_sql.startswith("```"):
            lines = raw_sql.split("\n")
            raw_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
        logger.info(f"Generated SQL (before rewriting): {raw_sql}")
        rewritten_sql = rewrite_secure_tables(raw_sql)
        logger.info(f"Rewritten SQL (after secure view conversion): {rewritten_sql}")
        state["sql"] = rewritten_sql
        return state
    
    # Pre-execution SQL Validation
    @trace_step('validate_sql')
    def _validate_sql_before_execution(self, state: SQLGraphState) -> SQLGraphState:
        """
        Validate SQL before execution to catch column/join errors early.
        
        Checks:
        - Column names exist in their respective tables
        - Table.column references are valid
        - Join columns exist in the tables being joined
        """
        if not settings.sql_pre_validation_enabled:
            state["validation_errors"] = None
            return state
        
        sql = state.get("sql", "")
        if not sql:
            state["validation_errors"] = None
            return state
        
        errors = []
        
        # Extract all table.column references from SQL
        # Pattern matches: table.column in SELECT, WHERE, JOIN, ON, etc.
        import re
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, sql)
        
        # Get all tables that might be used (from state and join plan)
        all_tables = set(state.get("tables", []))
        join_plan_text = state.get("join_plan", "")
        tables_from_join_plan = self._extract_tables_from_join_plan(join_plan_text)
        all_tables.update(tables_from_join_plan)
        
        # Create mapping of table names (handle secure views)
        table_name_map = {t.lower(): t for t in self.join_graph["tables"].keys()}
        
        for table_name, column_name in matches:
            # Convert secure view to base table for lookup (single source of truth)
            check_table = from_secure_view(table_name)
            
            # Check if table exists in join graph
            if check_table.lower() in table_name_map:
                actual_table = table_name_map[check_table.lower()]
                if actual_table in self.join_graph["tables"]:
                    columns = self.join_graph["tables"][actual_table].get("columns", [])
                    if column_name not in columns:
                        # Column doesn't exist - find where it might be
                        possible_tables = []
                        for t in all_tables:
                            if t in self.join_graph["tables"]:
                                t_columns = self.join_graph["tables"][t].get("columns", [])
                                if column_name in t_columns:
                                    possible_tables.append(t)
                        
                        if possible_tables:
                            error_msg = (
                                f"Column '{column_name}' does NOT exist in table '{check_table}'. "
                                f"Found in: {', '.join(possible_tables)}. "
                                f"Available columns in {check_table}: {', '.join(columns[:settings.sql_max_columns_in_validation])}"
                            )
                        else:
                            error_msg = (
                                f"Column '{column_name}' does NOT exist in table '{check_table}'. "
                                f"Available columns: {', '.join(columns[:settings.sql_max_columns_in_validation])}"
                            )
                        errors.append(error_msg)
                        logger.warning(f"Validation error: {error_msg}")
        
        if errors:
            state["validation_errors"] = errors
            logger.error(f"SQL validation failed with {len(errors)} errors")
        else:
            state["validation_errors"] = None
            logger.debug("SQL validation passed")
        
        return state
    
    def _find_bridge_tables(self, selected_tables: set, relationships: List[Dict[str, Any]], confidence_threshold: float = 0.9) -> set:
        """
        Find bridge tables that connect two selected tables with high confidence.
        
        A bridge table is one that:
        1. Has foreign keys to at least 2 selected tables
        2. Has confidence >= threshold for those relationships
        3. Is not already in the selected tables
        
        This ensures we include tables like employeeCrew when both crew and employee are selected.
        """
        bridge_tables = set()
        selected_lower = {t.lower() for t in selected_tables}
        
        # Create a mapping of original table names (case-sensitive) to lowercase
        table_name_map = {t.lower(): t for t in self.join_graph["tables"].keys()}
        
        # Count how many selected tables each potential bridge table connects to
        table_connections = {}  # table_name_lower -> set of selected tables (original case) it connects to
        
        for rel in relationships:
            from_table_orig = rel.get("from_table", "")
            to_table_orig = rel.get("to_table", "")
            from_table_lower = from_table_orig.lower()
            to_table_lower = to_table_orig.lower()
            confidence = float(rel.get("confidence", 0))
            
            # Skip if confidence too low
            if confidence < confidence_threshold:
                continue
            
            # Check if this relationship connects a selected table to a potential bridge table
            if from_table_lower in selected_lower and to_table_lower not in selected_lower:
                # to_table is a potential bridge table connecting from_table
                if to_table_lower not in table_connections:
                    table_connections[to_table_lower] = set()
                table_connections[to_table_lower].add(from_table_orig)  # Store original case
            
            if to_table_lower in selected_lower and from_table_lower not in selected_lower:
                # from_table is a potential bridge table connecting to_table
                if from_table_lower not in table_connections:
                    table_connections[from_table_lower] = set()
                table_connections[from_table_lower].add(to_table_orig)  # Store original case
        
        # Find tables that connect 2+ selected tables (these are bridge tables)
        for table_name_lower, connected_tables in table_connections.items():
            if len(connected_tables) >= 2:
                # This table connects multiple selected tables - it's a bridge table
                # Get original case name from join graph
                if table_name_lower in table_name_map:
                    original_name = table_name_map[table_name_lower]
                    bridge_tables.add(original_name)
                    logger.info(f"Found bridge table '{original_name}' connecting {len(connected_tables)} selected tables: {list(connected_tables)}")
        
        return bridge_tables
    
    def _extract_tables_from_join_plan(self, join_plan: str) -> set:
        """
        Extract table names mentioned in the join plan.
        
        This includes bridge tables that weren't in the initial selection
        but are needed for the joins (e.g., 'user' table connecting crew to employee).
        
        Only extracts from the JOIN_PATH section to avoid matching explanatory text.
        
        Args:
            join_plan: The join plan text from _plan_joins
            
        Returns:
            Set of table names mentioned in the join plan
        """
        import re
        tables = set()
        
        # First, extract only the JOIN_PATH section to avoid matching explanatory text
        join_path_match = re.search(r'JOIN_PATH:.*?(?=NOTES:|$)', join_plan, re.IGNORECASE | re.DOTALL)
        if not join_path_match:
            # Fallback: look for lines starting with "-" (bullet points in JOIN_PATH)
            join_path_match = re.search(r'(?:JOIN_PATH:.*?)?(-.*?)(?=NOTES:|$)', join_plan, re.IGNORECASE | re.DOTALL)
        
        join_path_text = join_path_match.group(0) if join_path_match else join_plan
        
        # Pattern to match table names in JOIN_PATH format:
        # - tableA.col = tableB.col
        # - tableA.col = tableB.col (cardinality, confidence)
        # Only match in lines that look like join specifications (start with - or contain =)
        pattern = r'(?:^|\n)\s*[-•]\s*([a-zA-Z_][a-zA-Z0-9_]*)\.[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)\.[a-zA-Z_][a-zA-Z0-9_]*'
        
        matches = re.finditer(pattern, join_path_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            table1 = match.group(1)
            table2 = match.group(2)
            # Only add if they look like valid table names (not common words)
            if table1.lower() not in ['the', 'a', 'an', 'and', 'or', 'path', 'connects', 'joins']:
                tables.add(table1)
            if table2.lower() not in ['the', 'a', 'an', 'and', 'or', 'path', 'connects', 'joins']:
                tables.add(table2)
        
        # Validate against known tables in join graph
        valid_tables = set()
        for table in tables:
            if table in self.join_graph["tables"]:
                valid_tables.add(table)
            # Also check case-insensitive
            for known_table in self.join_graph["tables"].keys():
                if table.lower() == known_table.lower():
                    valid_tables.add(known_table)
                    break
        
        return valid_tables
    
    def _parse_join_path_steps(self, join_plan: str) -> List[str]:
        """
        Parse JOIN_PATH section to extract explicit join steps.
        
        Returns a list of join steps in order, e.g.:
        ["crew.createdBy = user.id", "user.employeeId = employee.id"]
        
        This helps the SQL generator follow the path exactly.
        """
        import re
        steps = []
        
        # Extract JOIN_PATH section
        join_path_match = re.search(r'JOIN_PATH:.*?(?=NOTES:|$)', join_plan, re.IGNORECASE | re.DOTALL)
        if not join_path_match:
            return steps
        
        join_path_text = join_path_match.group(0)
        
        # Pattern to match join steps: - tableA.col = tableB.col
        pattern = r'[-•]\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)'
        
        matches = re.finditer(pattern, join_path_text, re.IGNORECASE)
        for match in matches:
            left_side = match.group(1)
            right_side = match.group(2)
            steps.append(f"{left_side} = {right_side}")
        
        return steps

    # SQL Correction Agent
    @trace_step('correct_sql')
    def _correct_sql(self, state: SQLGraphState) -> SQLGraphState:
        """
        Focused correction agent that fixes SQL errors with minimal context.
        
        This agent receives:
        - Failed SQL query
        - Specific error message
        - Relevant table schemas (only tables used in query)
        - Relevant relationships (only relationships between used tables)
        - Correction history (previous attempts)
        """
        sql = state.get("sql", "")
        validation_errors = state.get("validation_errors")
        if validation_errors:
            error_message = state.get("last_sql_error") or " | ".join(validation_errors)
        else:
            error_message = state.get("last_sql_error") or "Unknown error"
        correction_attempts = state.get("sql_correction_attempts", 0)
        
        # Check max attempts
        if correction_attempts >= settings.sql_correction_max_attempts:
            logger.error(f"Max correction attempts ({settings.sql_correction_max_attempts}) reached")
            state["result"] = f"Error: Could not fix SQL after {settings.sql_correction_max_attempts} attempts. Last error: {error_message}"
            return state
        
        # Increment attempts
        state["sql_correction_attempts"] = correction_attempts + 1
        
        # Get tables used in the SQL query
        import re
        # Extract from FROM and JOIN clauses
        table_pattern = r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables_in_sql = set(re.findall(table_pattern, sql, re.IGNORECASE))
        # Also extract from table.column patterns (SELECT, WHERE, ON, etc.)
        column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
        for table, _ in re.findall(column_pattern, sql):
            # Convert secure view to base table for lookup (single source of truth)
            base_table = from_secure_view(table)
            tables_in_sql.add(base_table)
        
        # Build relevant table schemas (only tables used in query)
        table_schemas = []
        for table_name in sorted(tables_in_sql):
            # table_name is already base table (from_secure_view was applied above)
            if table_name in self.join_graph["tables"]:
                columns = self.join_graph["tables"][table_name].get("columns", [])
                columns_str = ', '.join(columns[:settings.sql_max_columns_in_correction])
                if len(columns) > settings.sql_max_columns_in_correction:
                    columns_str += f" ... ({len(columns)} total columns)"
                table_schemas.append(f"{table_name}: {columns_str}")
        
        # Get relevant relationships (only between tables in query)
        relevant_relationships = []
        for rel in state.get("allowed_relationships", []):
            from_table = rel.get("from_table", "")
            to_table = rel.get("to_table", "")
            # Convert secure views to base tables for comparison (single source of truth)
            from_base = from_secure_view(from_table)
            to_base = from_secure_view(to_table)
            # Include if either table is in the query (for joins)
            if from_base in tables_in_sql or to_base in tables_in_sql:
                relevant_relationships.append(rel)
        
        # Build correction history
        correction_history = state.get("correction_history") or []
        history_text = ""
        if correction_history:
            history_text = "\nPrevious correction attempts:\n"
            for i, attempt in enumerate(correction_history[-3:], 1):  # Show last 3 attempts
                history_text += f"{i}. Error: {attempt.get('error', 'Unknown')}\n"
                sql_preview = attempt.get('sql', 'N/A')
                if len(sql_preview) > settings.sql_max_sql_history_length:
                    sql_preview = sql_preview[:settings.sql_max_sql_history_length] + "..."
                history_text += f"   Attempted fix: {sql_preview}\n"
        
        # Detect specific error types for targeted instructions
        is_group_by_error = "GROUP BY" in error_message.upper() or "not in GROUP BY" in error_message.upper() or "only_full_group_by" in error_message.lower()
        
        group_by_instructions = ""
        if is_group_by_error:
            # Extract the problematic expression from error message if possible
            import re
            expr_match = re.search(r"Expression #(\d+)", error_message)
            expr_num = expr_match.group(1) if expr_match else None
            
            # Try to extract the column/expression mentioned in error
            column_match = re.search(r"column ['\"]([^'\"]+)['\"]", error_message)
            problem_column = column_match.group(1) if column_match else None
            
            expr_hint = ""
            if expr_num:
                expr_hint = f"\nThe error mentions Expression #{expr_num} in the SELECT list. "
            if problem_column:
                expr_hint += f"The problematic column/expression is: {problem_column}"
            
            group_by_instructions = f"""
CRITICAL GROUP BY RULES (MySQL ONLY_FULL_GROUP_BY mode):
{expr_hint}

- Every non-aggregated column/expression in SELECT must either:
  1. Be in GROUP BY with the EXACT same expression, OR
  2. Be functionally dependent on columns in GROUP BY

COMMON FIXES:
- If SELECT has: DATE_FORMAT(DATE(column), 'format'), GROUP BY must have: DATE_FORMAT(DATE(column), 'format')
- If SELECT has: DATE(column), GROUP BY must have: DATE(column) (NOT just 'column')
- If SELECT has: CONCAT(col1, col2), GROUP BY must have: CONCAT(col1, col2)
- If SELECT has: column AS alias, GROUP BY can use either 'column' or the full expression

EXAMPLE FIX:
  SELECT DATE_FORMAT(DATE(createdAt), '%Y-%m-%d') AS date, SUM(hours)
  FROM workTime
  GROUP BY DATE_FORMAT(DATE(createdAt), '%Y-%m-%d')  -- Must match SELECT exactly
"""
        
        # Build focused prompt
        prompt = f"""You are a SQL correction agent. Fix this SQL error:

ERROR: {error_message}

FAILED SQL:
{sql}

RELEVANT TABLE SCHEMAS (only tables used in the query above):
{chr(10).join(table_schemas) if table_schemas else "No tables found"}

RELEVANT RELATIONSHIPS (only between tables in query):
{json.dumps(relevant_relationships[:settings.sql_max_relationships_in_prompt], indent=2) if relevant_relationships else "No relationships found"}
{history_text}

INSTRUCTIONS:
1. Analyze the error message carefully
2. Check the table schemas to find where the column actually exists
3. Fix the SQL query by:
   - Using the correct table name for each column
   - Ensuring all columns exist in their respective tables
   - Fixing any join conditions that reference wrong columns
{group_by_instructions}
4. Return ONLY the corrected SQL query, nothing else
5. Do NOT add comments or explanations

CORRECTED SQL QUERY:"""
        
        logger.info(f"[PROMPT] correct_sql prompt (attempt {correction_attempts + 1}):\n{prompt}")
        
        try:
            response = self.llm.invoke(prompt)
            corrected_sql = str(response.content).strip() if hasattr(response, 'content') and response.content else ""
            
            # Clean up if wrapped in code blocks
            if corrected_sql.startswith("```"):
                lines = corrected_sql.split("\n")
                corrected_sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
            
            # Remove SQL keyword if present
            if corrected_sql.upper().startswith("SQL"):
                corrected_sql = corrected_sql[3:].strip()
            
            logger.info(f"Corrected SQL (attempt {correction_attempts + 1}): {corrected_sql[:200]}...")
            
            # Apply secure view rewriting
            rewritten_sql = rewrite_secure_tables(corrected_sql)
            
            # Update state
            state["sql"] = rewritten_sql
            state["last_sql_error"] = None  # Clear error for next validation
            
            # Add to correction history
            if state.get("correction_history") is None:
                state["correction_history"] = []
            correction_history = state["correction_history"]
            if correction_history is not None:
                correction_history.append({
                    "attempt": correction_attempts + 1,
                    "error": error_message,
                    "sql": corrected_sql[:settings.sql_max_sql_history_length]  # Truncate for storage
                })
            
            return state
            
        except Exception as e:
            logger.error(f"Error in correction agent: {e}")
            state["result"] = f"Error in correction agent: {str(e)}"
            return state

    # 5) Execution + Validator (retry-on-empty)
    @trace_step('execute_and_validate')
    def _execute_and_validate(self, state: SQLGraphState) -> SQLGraphState:
        logger.info(f"Executing SQL: {state['sql']}")

        try:
            # Use run_query_with_columns to get both result and column names
            res, column_names = sql_tool.run_query_with_columns(state["sql"])
            state["column_names"] = column_names
            logger.debug(f"Query returned {len(column_names)} columns: {column_names}")
            
            # Clear any previous errors on success
            state["last_sql_error"] = None
            state["validation_errors"] = None
            
        except Exception as e:
            # Extract error message
            error_str = str(e)
            state["last_sql_error"] = error_str
            state["column_names"] = None
            
            # Check if we should route to correction agent
            correction_attempts = state.get("sql_correction_attempts", 0)
            if correction_attempts < settings.sql_correction_max_attempts:
                logger.warning(f"SQL execution error (attempt {correction_attempts + 1}): {error_str[:200]}")
                # Route to correction agent - signal by setting result to None
                state["result"] = None
                return state
            else:
                # Max attempts reached - hard fail
                logger.error(f"Max correction attempts reached. Final error: {error_str}")
                state["result"] = f"Error executing query after {settings.sql_correction_max_attempts} correction attempts: {error_str}"
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
            state["column_names"] = None
            return state

        state["result"] = str(res)
        return state

    def _parse_sql_result(self, raw_result: str, column_names: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Parse SQL result into structured data with proper column names.
        
        Handles multiple formats:
        1. JSON arrays: [{"col1": "val1", ...}, ...]
        2. Python tuple strings: [('val1', 'val2', ...), ...] - uses column_names if provided
        3. Python dict strings: [{'col1': 'val1', ...}, ...]
        
        Args:
            raw_result: Raw SQL result string
            column_names: Optional list of column names from the query result
            
        Returns:
            List of dictionaries with proper column names, or None if parsing fails
        """
        if not raw_result or not raw_result.strip():
            return None
        
        result_str = str(raw_result).strip()
        
        # Try JSON first (most common for LangChain SQLDatabase)
        try:
            if result_str.startswith('[') or result_str.startswith('{'):
                parsed = json.loads(result_str)
                if isinstance(parsed, list):
                    # Ensure all items are dicts
                    structured = []
                    for item in parsed:
                        if isinstance(item, dict):
                            structured.append(item)
                        elif isinstance(item, (list, tuple)):
                            # Convert tuple/list to dict with actual column names if available
                            if column_names and len(column_names) == len(item):
                                structured.append({column_names[i]: val for i, val in enumerate(item)})
                            else:
                                # Fallback to generic keys if column names don't match
                                structured.append({f"col_{i}": val for i, val in enumerate(item)})
                        else:
                            structured.append({"value": item})
                    return structured if structured else None
                elif isinstance(parsed, dict):
                    return [parsed]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        
        # Try parsing Python literal (handles tuple strings like [('val1', 'val2'), ...])
        try:
            if result_str.startswith('['):
                # Preprocess: replace datetime.date(...) and datetime.datetime(...) with string representation
                preprocessed = result_str
                
                # Replace datetime.date(...) patterns: datetime.date(2025, 7, 16) -> '2025-07-16'
                date_pattern = r'datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)'
                def replace_date(match):
                    year, month, day = match.groups()
                    return f"'{year}-{month.zfill(2)}-{day.zfill(2)}'"
                preprocessed = re.sub(date_pattern, replace_date, preprocessed)
                
                # Replace datetime.datetime(...) patterns with ISO format string
                # datetime.datetime(2025, 7, 16, 12, 30, 45) -> '2025-07-16T12:30:45'
                datetime_pattern = r'datetime\.datetime\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+))?(?:,\s*(\d+))?(?:,\s*(\d+))?\)'
                def replace_datetime(match):
                    groups = match.groups()
                    year, month, day = groups[0], groups[1], groups[2]
                    hour = groups[3] if groups[3] else '0'
                    minute = groups[4] if groups[4] else '0'
                    second = groups[5] if groups[5] else '0'
                    return f"'{year}-{month.zfill(2)}-{day.zfill(2)}T{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}'"
                preprocessed = re.sub(datetime_pattern, replace_datetime, preprocessed)
                
                # Also handle None -> None (keep as-is, but ensure it's valid Python)
                # None is already valid in Python literals
                
                # Parse as Python literal
                parsed = ast.literal_eval(preprocessed)
                
                if isinstance(parsed, list) and len(parsed) > 0:
                    # Convert list of tuples to list of dicts
                    structured = []
                    for row in parsed:
                        if isinstance(row, (list, tuple)):
                            # Convert tuple/list to dict with actual column names if available
                            row_dict = {}
                            for i, val in enumerate(row):
                                # Use column name if available, otherwise use generic key
                                col_name = column_names[i] if column_names and i < len(column_names) else f"col_{i}"
                                
                                # Convert values to JSON-serializable types
                                if val is None:
                                    row_dict[col_name] = None
                                elif isinstance(val, (str, int, float, bool)):
                                    row_dict[col_name] = val
                                else:
                                    # Convert other types to string
                                    row_dict[col_name] = str(val)
                            structured.append(row_dict)
                        elif isinstance(row, dict):
                            # Already a dict, but ensure values are JSON-serializable
                            clean_dict = {}
                            for k, v in row.items():
                                if v is None or isinstance(v, (str, int, float, bool, list, dict)):
                                    clean_dict[k] = v
                                else:
                                    clean_dict[k] = str(v)
                            structured.append(clean_dict)
                        else:
                            structured.append({"value": str(row) if row is not None else None})
                    return structured if structured else None
        except (ValueError, SyntaxError, TypeError) as e:
            logger.debug(f"Failed to parse Python literal: {e}, result_str preview: {result_str[:200]}")
            pass
        
        return None

    # 6) Final answer formatting (structured data for BFF)
    @trace_step('finalize')
    def _finalize(self, state: SQLGraphState) -> SQLGraphState:
        """
        Finalize SQL result and parse structured data for BFF markdown conversion.
        
        Returns both raw string (for backward compatibility) and structured array
        (for Node.js BFF to convert to markdown).
        """
        if state.get("result") is None:
            state["final_answer"] = "No result."
            state["structured_result"] = None
            return state

        raw_result = state.get("result")
        column_names = state.get("column_names")
        
        # Parse structured data from various formats, using column names if available
        if raw_result is None:
            structured_data = None
        else:
            structured_data = self._parse_sql_result(raw_result, column_names)
        
        # Store both structured and raw for flexibility
        state["final_answer"] = raw_result  # Raw for backward compatibility
        state["structured_result"] = structured_data  # Structured for BFF markdown conversion
        
        if structured_data:
            logger.info(f"✅ Parsed structured data: {len(structured_data)} items")
            if len(structured_data) > 0:
                logger.debug(f"First item keys: {list(structured_data[0].keys())}")
        else:
            logger.debug(f"⚠️ Could not parse structured data from result (length: {len(str(raw_result))} chars)")
            logger.debug(f"Result preview: {str(raw_result)[:200]}...")
        
        return state

    def _route_after_validation(self, state: SQLGraphState) -> str:
        """
        Route after pre-execution validation.
        
        Returns:
            "execute" if validation passed
            "correct_sql" if validation failed and can retry
            "finalize" if validation failed and max attempts reached
        """
        validation_errors = state.get("validation_errors")
        if not validation_errors:
            # Validation passed - proceed to execution
            return "execute"
        
        # Validation failed - check if we can correct
        correction_attempts = state.get("sql_correction_attempts", 0)
        if correction_attempts < settings.sql_correction_max_attempts:
            # Store validation errors as last_sql_error for correction agent
            state["last_sql_error"] = " | ".join(validation_errors)
            logger.info(f"Validation failed, routing to correction agent (attempt {correction_attempts + 1})")
            return "correct_sql"
        else:
            # Max attempts reached - fail
            logger.error(f"Max correction attempts reached. Validation errors: {validation_errors}")
            state["result"] = f"SQL validation failed after {settings.sql_correction_max_attempts} attempts. Errors: {' | '.join(validation_errors)}"
            return "finalize"
    
    def _route_after_execute(self, state: SQLGraphState) -> str:
        """
        Route after SQL execution.
        
        Returns:
            "finalize" if execution succeeded
            "correct_sql" if execution failed and can retry
            "generate_sql" if empty result and can retry
            "finalize" if max attempts reached
        """
        result = state.get("result")
        
        # If result is None, it means execution failed and we should correct
        if result is None:
            correction_attempts = state.get("sql_correction_attempts", 0)
            if correction_attempts < settings.sql_correction_max_attempts:
                logger.info(f"Execution failed, routing to correction agent (attempt {correction_attempts + 1})")
                return "correct_sql"
            else:
                # Max attempts reached - finalize with error
                return "finalize"
        
        # If result contains error message, finalize
        if isinstance(result, str) and result.startswith("Error"):
            return "finalize"
        
        # If we set retries and result is None, we want to regenerate SQL (empty result retry)
        if state["retries"] > 0 and result is None:
            return "generate_sql"
        
        # Success - finalize
        return "finalize"
    
    def _route_after_correction(self, state: SQLGraphState) -> str:
        """
        Route after SQL correction.
        
        Always routes back to validation to check the corrected SQL.
        """
        return "validate_sql"

    def _build(self):
        g = StateGraph(SQLGraphState)
        g.add_node("select_tables", self._select_tables)
        g.add_node("filter_relationships", self._filter_relationships)
        g.add_node("plan_joins", self._plan_joins)
        g.add_node("generate_sql", self._generate_sql)
        g.add_node("validate_sql", self._validate_sql_before_execution)
        g.add_node("correct_sql", self._correct_sql)
        g.add_node("execute", self._execute_and_validate)
        g.add_node("finalize", self._finalize)

        g.set_entry_point("select_tables")
        g.add_edge("select_tables", "filter_relationships")
        g.add_edge("filter_relationships", "plan_joins")
        g.add_edge("plan_joins", "generate_sql")
        g.add_edge("generate_sql", "validate_sql")

        # Route after validation: execute (if valid) or correct_sql (if invalid) or finalize (if max attempts)
        g.add_conditional_edges(
            "validate_sql",
            self._route_after_validation,
            {
                "execute": "execute",
                "correct_sql": "correct_sql",
                "finalize": "finalize",
            },
        )

        # Route after correction: always go back to validation
        g.add_edge("correct_sql", "validate_sql")

        # Route after execute: finalize (if success) or correct_sql (if error) or generate_sql (if empty retry)
        g.add_conditional_edges(
            "execute",
            self._route_after_execute,
            {
                "finalize": "finalize",
                "correct_sql": "correct_sql",
                "generate_sql": "generate_sql",
            },
        )

        g.add_edge("finalize", END)
        return g.compile()

    def query(self, question: str) -> str:
        """
        Query the database and return the answer.
        
        Returns the final_answer string. For structured data, use query_with_structured().
        """
        state: SQLGraphState = {
            "question": question,
            "tables": [],
            "allowed_relationships": [],
            "join_plan": "",
            "sql": "",
            "result": None,
            "column_names": None,
            "retries": 0,
            "final_answer": None,
            "structured_result": None,
            "sql_correction_attempts": 0,
            "last_sql_error": None,
            "correction_history": None,
            "validation_errors": None,
        }
        out = self.workflow.invoke(state)
        return out.get("final_answer") or "No answer generated."
    
    def query_with_structured(self, question: str) -> Dict[str, Any]:
        """
        Query the database and return both answer and structured data.
        
        Returns:
            Dict with 'answer' (str) and 'structured_result' (List[Dict] | None)
        """
        state: SQLGraphState = {
            "question": question,
            "tables": [],
            "allowed_relationships": [],
            "join_plan": "",
            "sql": "",
            "result": None,
            "column_names": None,
            "retries": 0,
            "final_answer": None,
            "structured_result": None,
            "sql_correction_attempts": 0,
            "last_sql_error": None,
            "correction_history": None,
            "validation_errors": None,
        }
        out = self.workflow.invoke(state)
        return {
            "answer": out.get("final_answer") or "No answer generated.",
            "structured_result": out.get("structured_result")
        }
