"""
SQL database tool for querying the database.
Provides safe, read-only access to database through natural language.
"""

import re
from typing import List, Optional, Set, Tuple
from sqlalchemy import create_engine, inspect
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

from ..models.database import get_database
from ..utils.config import settings, create_llm
from ..utils.logger import logger
from ..utils.sql.secure_views import SECURE_VIEW_MAP, rewrite_secure_tables, validate_tables_exist


class SQLQueryTool:
    """
    SQL query tool for database access.
    Provides safe, read-only access to the database.
    """
    
    def __init__(self):
        """Initialize SQL database connection and toolkit."""
        # Get database instance
        db_instance = get_database()
        self.engine = db_instance.engine
        
        # Exclude encrypted base tables - we'll use secure views via rewriting
        # Only the base tables that have secure views should be excluded
        excluded_tables = list(SECURE_VIEW_MAP.keys())
        
        logger.info(f"Excluding encrypted base tables: {', '.join(excluded_tables)}")
        logger.info(f"These will be accessed via: {', '.join(SECURE_VIEW_MAP.values())}")
        
        # Create LangChain SQL Database wrapper
        self.db = SQLDatabase(
            engine=self.engine,
            ignore_tables=excluded_tables,  # Exclude encrypted base tables
            view_support=True,  # Include views in the schema
            sample_rows_in_table_info=settings.sql_sample_rows,  # Configurable sample rows
            max_string_length=100  # Truncate long string values
        )
        
        # Cache available tables for validation
        self._available_tables = set(self.db.get_usable_table_names())
        logger.info(f"Available tables/views: {len(self._available_tables)}")
        
        # Initialize LLM for SQL agent
        self.llm = create_llm(
            temperature=0,  # Deterministic for SQL generation
            max_completion_tokens=settings.max_output_tokens  # Limit output tokens
        )
        
        # Create SQL toolkit
        self.toolkit = SQLDatabaseToolkit(
            db=self.db,
            llm=self.llm
        )
        
        logger.info("SQL Tool initialized with database connection")
    
    def get_table_info(self) -> str:
        """
        Get information about database tables and schema.
        
        Returns:
            String containing table schemas and sample data
        """
        return self.db.get_table_info()
    
    def get_table_names(self) -> List[str]:
        """
        Get list of available table names.
        
        Returns:
            List of table names
        """
        return list(self.db.get_usable_table_names())
    
    def get_available_tables(self) -> Set[str]:
        """
        Get set of available table names for validation.
        
        Returns:
            Set of table names (lowercase)
        """
        return self._available_tables
    
    def _validate_query(self, query: str) -> str:
        """
        Validate and rewrite query for security.
        
        Returns:
            Rewritten query string
        """
        # Safety check: only allow SELECT queries
        query_upper = query.strip().upper()
        
        # First, ensure query starts with SELECT (allows WITH clauses for CTEs)
        if not query_upper.startswith(("SELECT", "WITH")):
            raise ValueError(
                "Query must start with SELECT or WITH. "
                "Only SELECT queries are allowed for safety."
            )
        
        # Use word boundaries to avoid false positives (e.g., "createdBy" contains "CREATE")
        # Check for forbidden keywords as standalone words, not substrings
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        
        for keyword in forbidden_keywords:
            # Use word boundary regex to match only standalone keywords, not substrings
            # \b matches word boundaries (start/end of word, before/after non-word chars)
            # This prevents matching "CREATE" inside "createdBy" or "createdAt"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, query_upper, re.IGNORECASE):
                raise ValueError(
                    f"Query contains forbidden keyword '{keyword}'. "
                    "Only SELECT queries are allowed for safety."
                )
        
        logger.info(f"Original SQL: {query[:200]}...")
        
        # Rewrite base tables to secure views (e.g., employee → secure_employee)
        rewritten_query = rewrite_secure_tables(query)
        
        # Log if rewrite happened
        if rewritten_query != query:
            logger.info(f"Rewritten SQL: {rewritten_query[:200]}...")
        
        # Validate all tables exist
        try:
            validate_tables_exist(rewritten_query, self._available_tables)
        except ValueError as e:
            logger.error(f"Table validation failed: {e}")
            raise
        
        return rewritten_query

    def run_query(self, query: str) -> str:
        """
        Execute a SQL query (read-only) with automatic secure view rewriting.
        
        This method:
        1. Validates the query is read-only
        2. Rewrites base table names to secure views where applicable
        3. Validates all tables exist
        4. Executes the query
        
        Args:
            query: SQL SELECT query to execute
            
        Returns:
            Query results as string
            
        Raises:
            ValueError: If query contains forbidden operations or invalid tables
        """
        rewritten_query = self._validate_query(query)
        
        # Execute the query
        try:
            result = self.db.run(rewritten_query)
            logger.success(f"Query executed successfully, returned {len(str(result))} characters")
            return str(result)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Failed query: {rewritten_query}")
            raise
    
    def run_query_with_columns(self, query: str) -> Tuple[str, List[str]]:
        """
        Execute a SQL query and return both result string and column names.
        
        This method executes the query using SQLAlchemy directly to get column metadata,
        then formats the result as a string for backward compatibility.
        
        Args:
            query: SQL SELECT query to execute
            
        Returns:
            Tuple of (result_string, column_names)
            
        Raises:
            ValueError: If query contains forbidden operations or invalid tables
        """
        from sqlalchemy import text
        
        rewritten_query = self._validate_query(query)
        
        # Execute using SQLAlchemy directly to get column names
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(rewritten_query))
                
                # Get column names from result
                column_names = list(result.keys())
                
                # Fetch all rows
                rows = result.fetchall()
                
                # Format as string (same format as LangChain SQLDatabase.run)
                if not rows:
                    result_string = "[]"
                else:
                    # Convert rows to list of tuples for string representation
                    row_tuples = [tuple(row) for row in rows]
                    result_string = str(row_tuples)
                
                logger.success(f"Query executed successfully, returned {len(rows)} rows with {len(column_names)} columns")
                logger.debug(f"Column names: {column_names}")
                
                return result_string, column_names
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Failed query: {rewritten_query}")
            raise
    
    def get_toolkit(self) -> SQLDatabaseToolkit:
        """
        Get the LangChain SQL toolkit for agent use.
        
        Returns:
            SQLDatabaseToolkit instance
        """
        return self.toolkit
    
    def __repr__(self) -> str:
        return f"<SQLQueryTool tables={self.get_table_names()}>"


# Create global instance
sql_tool = SQLQueryTool()
