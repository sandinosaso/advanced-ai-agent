"""
SQL agent context - dependencies for workflow nodes
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SQLContext:
    """Context holding dependencies for SQL workflow nodes"""

    join_graph: Dict[str, Any]
    path_finder: Any  # JoinPathFinder
    domain_ontology: Optional[Any]  # DomainOntology or None
    llm: Any  # LangChain ChatModel
    sql_tool: Any  # SQLQueryTool
