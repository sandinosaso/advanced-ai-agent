"""
SQL Query Agent for natural language database queries.
Converts natural language questions into SQL and executes them safely.
"""

from typing import Dict, Any, Optional
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI

from ..tools.sql_tool import sql_tool
from ..utils.config import settings
from ..utils.logger import logger


class SQLQueryAgent:
    """
    Agent that answers questions by querying the FSIA database.
    Uses LangChain SQL agent to convert natural language to SQL.
    """
    
    def __init__(self):
        """Initialize the SQL query agent."""
        # Create LLM for agent
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0  # Deterministic for SQL
        )
        
        # Create SQL agent with toolkit
        self.agent = create_sql_agent(
            llm=self.llm,
            toolkit=sql_tool.get_toolkit(),
            agent_type="openai-tools",  # Modern agent type for OpenAI models
            verbose=True,  # Show reasoning steps
            handle_parsing_errors=True
        )
        
        logger.info("SQL Query Agent initialized")
    
    def query(self, question: str) -> str:
        """
        Answer a question by querying the database.
        
        Args:
            question: Natural language question about the data
            
        Returns:
            Answer to the question based on database query
            
        Example:
            >>> agent = SQLQueryAgent()
            >>> agent.query("How many technicians are active?")
            "There are 10 active technicians."
        """
        logger.info(f"Processing question: {question}")
        
        try:
            # Run agent to answer question
            result = self.agent.invoke({"input": question})
            
            # Extract answer from result
            answer = result.get("output", "No answer generated")
            
            logger.success(f"Question answered successfully")
            return answer
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            logger.error(error_msg)
            return f"I encountered an error: {str(e)}"
    
    def get_schema_info(self) -> str:
        """
        Get database schema information.
        
        Returns:
            String describing the database schema
        """
        return sql_tool.get_table_info()


# Example usage and common queries
EXAMPLE_QUERIES = [
    "How many technicians are active?",
    "How many hours did technicians work last week?",
    "Which jobs are over budget?",
    "Show me all pending work logs",
    "What are the most common skills among technicians?",
    "How many jobs are in progress?",
    "What is the total amount of approved expenses?",
    "Which technicians logged more than 40 hours in a week?",
    "List all schedule rules with error severity",
    "What is the average hourly rate for full-time technicians?"
]
