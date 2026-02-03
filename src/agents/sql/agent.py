"""
SQL Graph Agent - Natural language to SQL conversion
"""

from typing import Any, Dict, List, Optional

from src.config.settings import settings
from src.llm.client import create_llm
from src.utils.logging import logger
from src.sql.graph.join_graph import load_join_graph
from src.sql.graph.path_finder import JoinPathFinder
from src.domain.ontology import DomainOntology
from src.domain.display_attributes import DisplayAttributesManager
from src.sql.execution.executor import sql_tool

from src.agents.sql.state import SQLGraphState
from src.agents.sql.context import SQLContext
from src.agents.sql.workflow import build_sql_workflow


class SQLGraphAgent:
    """
    LangGraph-based SQL agent for natural language to SQL conversion.

    Uses graph algorithms (Dijkstra) to discover optimal join paths between tables
    in a MySQL database with 100+ tables.
    """

    def __init__(self):
        self.llm = create_llm(
            temperature=0,
            max_completion_tokens=settings.max_output_tokens,
        )
        self.join_graph = load_join_graph()

        self.path_finder = JoinPathFinder(
            self.join_graph["relationships"],
            confidence_threshold=settings.sql_confidence_threshold,
        )

        if settings.domain_registry_enabled:
            try:
                self.domain_ontology = DomainOntology()
                logger.info("Domain ontology initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize domain ontology: {e}. Proceeding without domain resolution.")
                self.domain_ontology = None
        else:
            self.domain_ontology = None
            logger.info("Domain ontology disabled")
        
        # Initialize display attributes manager
        if settings.display_attributes_enabled:
            try:
                self.display_attributes = DisplayAttributesManager()
                logger.info("Display attributes manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize display attributes: {e}. Proceeding without display attributes.")
                self.display_attributes = None
        else:
            self.display_attributes = None
            logger.info("Display attributes disabled")

        ctx = SQLContext(
            join_graph=self.join_graph,
            path_finder=self.path_finder,
            domain_ontology=self.domain_ontology,
            display_attributes=self.display_attributes,
            llm=self.llm,
            sql_tool=sql_tool,
        )
        self.workflow = build_sql_workflow(ctx)

        logger.info("SQLGraphAgent initialized with path finder")

    def _initial_state(
        self, question: str, previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> SQLGraphState:
        """Create initial workflow state."""
        return {
            "question": question,
            "domain_terms": [],
            "domain_resolutions": [],
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
            "previous_results": previous_results,
            "is_followup": False,
            "referenced_ids": None,
            "query_resolved": True,
        }

    def query(
        self, question: str, previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Query the database and return the answer.
        """
        state = self._initial_state(question, previous_results)
        out = self.workflow.invoke(state)
        return out.get("final_answer") or "No answer generated."

    def query_with_structured(
        self,
        question: str,
        previous_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Query the database and return both answer and structured data.
        """
        state = self._initial_state(question, previous_results)
        out = self.workflow.invoke(state)
        return {
            "answer": out.get("final_answer") or "No answer generated.",
            "structured_result": out.get("structured_result"),
            "tables_used": out.get("tables"),
            "sql_query": out.get("sql"),
            "query_resolved": out.get("query_resolved", True),
        }
