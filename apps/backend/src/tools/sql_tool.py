"""
SQL database tool for querying the FSIA database.
Provides safe, read-only access to database through natural language.
"""

from typing import List, Optional
from sqlalchemy import create_engine, inspect
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

from ..models.database import DATABASE_URL
from ..utils.config import settings
from ..utils.logger import logger


class FSIASQLTool:
    """
    SQL query tool for Field Service Intelligence Agent database.
    Provides safe, read-only access to the database.
    """
    
    def __init__(self):
        """Initialize SQL database connection and toolkit."""
        # Create SQLAlchemy engine for LangChain
        self.engine = create_engine(DATABASE_URL)
        
        # Create LangChain SQL Database wrapper
        self.db = SQLDatabase(
            engine=self.engine,
            include_tables=["technicians", "jobs", "work_logs", "expenses", "schedule_rules"],
            sample_rows_in_table_info=3  # Include sample rows in schema for better context
        )
        
        # Initialize LLM for SQL agent
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0  # Deterministic for SQL generation
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
    
    def run_query(self, query: str) -> str:
        """
        Execute a SQL query (read-only).
        
        Args:
            query: SQL SELECT query to execute
            
        Returns:
            Query results as string
            
        Raises:
            ValueError: If query contains forbidden operations
        """
        # Safety check: only allow SELECT queries
        query_upper = query.strip().upper()
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                raise ValueError(
                    f"Query contains forbidden keyword '{keyword}'. "
                    "Only SELECT queries are allowed for safety."
                )
        
        logger.info(f"Executing SQL query: {query[:100]}...")
        
        try:
            result = self.db.run(query)
            logger.success(f"Query executed successfully, returned {len(str(result))} characters")
            return str(result)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_toolkit(self) -> SQLDatabaseToolkit:
        """
        Get the LangChain SQL toolkit for agent use.
        
        Returns:
            SQLDatabaseToolkit instance
        """
        return self.toolkit
    
    def __repr__(self) -> str:
        return f"<FSIASQLTool tables={self.get_table_names()}>"


# Create global instance
sql_tool = FSIASQLTool()
