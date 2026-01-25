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
            temperature=0,  # Deterministic for SQL
            max_completion_tokens=settings.max_output_tokens  # Limit output tokens
        )
        
        # Agent prefix with instructions about secure views
        agent_prefix = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct MySQL query to run, then look at the results of the query and return the answer.

IMPORTANT: The database uses secure views for sensitive data. Always use these views:
- secure_user (not user)
- secure_customerlocation (not customerlocation)
- secure_customercontact (not customercontact)
- secure_employee (not employee)
- secure_workorder (not workorder)
- secure_customer (not customer)

These secure views have encryption already handled and will return readable data.

IMPORTANT: Always use LIMIT clauses to prevent large result sets:
- Use LIMIT {max_rows} at the end of SELECT queries
- Default to LIMIT 100 unless user specifies a different amount
- For counts/aggregates, no LIMIT needed

CRITICAL - Keep queries simple and avoid unnecessary joins:
- The workTime table contains: employeeId, startTime, endTime, hours, crewWorkDayId
- When filtering workTime by date, use w.startTime or w.endTime (NOT work order dates)
- Only join to secure_workorder if you need work order specific info (customer, location, status)
- crewWorkDayId links to crewWorkDay table, NOT to work order IDs

Common query patterns:
1. Employee hours by period:
   SELECT e.firstName, e.lastName, SUM(w.hours)
   FROM workTime w
   JOIN secure_employee e ON w.employeeId = e.id
   WHERE w.startTime BETWEEN 'start' AND 'end'
   GROUP BY e.id

2. Work orders with employee info:
   SELECT wo.*, e.firstName
   FROM secure_workorder wo
   JOIN secure_employee e ON wo.employeeId = e.id
   WHERE wo.startDate BETWEEN 'start' AND 'end'

3. Customer work orders:
   SELECT c.customerName, wo.workOrderNumber
   FROM secure_customer c
   JOIN secure_workorder wo ON c.id = wo.customerId
""".format(max_rows=settings.max_query_rows)
        
        # Create SQL agent with toolkit
        self.agent = create_sql_agent(
            llm=self.llm,
            toolkit=sql_tool.get_toolkit(),
            agent_type="openai-tools",  # Modern agent type for OpenAI models
            verbose=True,  # Show reasoning steps
            handle_parsing_errors=True,
            prefix=agent_prefix,  # Add custom instructions
            max_iterations=settings.sql_agent_max_iterations  # Limit reasoning steps
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
