"""
Query Result Memory for Follow-up Questions

Stores recent SQL query results to enable natural follow-up conversations.
Users can ask "show me the questions for that inspection" and the system
will remember the inspection ID from the previous query.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from loguru import logger
import re


class QueryResult:
    """Represents a stored query result with metadata"""
    
    def __init__(
        self,
        question: str,
        structured_data: List[Dict[str, Any]],
        sql_query: Optional[str] = None,
        tables_used: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ):
        self.question = question
        self.structured_data = structured_data
        self.sql_query = sql_query
        self.tables_used = tables_used or []
        self.timestamp = timestamp or datetime.now().isoformat()
        self.row_count = len(structured_data) if structured_data else 0
        
        # Extract identifiers on initialization
        self.identifiers = self._extract_identifiers()
    
    def _extract_identifiers(self) -> Dict[str, List[Any]]:
        """
        Extract ID fields from structured data.
        
        Looks for columns ending in 'Id' or 'id' and extracts unique values.
        
        Returns:
            Dict mapping ID field names to lists of unique values
        """
        if not self.structured_data:
            return {}
        
        identifiers = {}
        
        # Get all column names from first row
        if len(self.structured_data) > 0:
            first_row = self.structured_data[0]
            
            # Find ID columns (ending with 'Id' or 'id')
            id_columns = [
                col for col in first_row.keys()
                if col.endswith('Id') or col.endswith('id') or col == 'id'
            ]
            
            # Extract unique values for each ID column
            for col in id_columns:
                values = set()
                for row in self.structured_data:
                    val = row.get(col)
                    if val is not None:
                        values.add(val)
                
                if values:
                    identifiers[col] = list(values)
        
        return identifiers
    
    def get_sample_rows(self, n: int = 2) -> List[Dict[str, Any]]:
        """Get first N rows as sample"""
        return self.structured_data[:n] if self.structured_data else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "question": self.question,
            "structured_data": self.structured_data,
            "sql_query": self.sql_query,
            "tables_used": self.tables_used,
            "timestamp": self.timestamp,
            "row_count": self.row_count,
            "identifiers": self.identifiers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryResult':
        """Create QueryResult from dictionary"""
        return cls(
            question=data.get("question", ""),
            structured_data=data.get("structured_data", []),
            sql_query=data.get("sql_query"),
            tables_used=data.get("tables_used"),
            timestamp=data.get("timestamp")
        )


class QueryResultMemory:
    """
    Manages memory of recent query results for follow-up questions.
    
    Stores the last N SQL query results with:
    - Structured data (actual result arrays)
    - Key identifiers (extracted IDs)
    - Metadata (timestamp, tables, row count)
    - Smart summaries (sample rows + all unique IDs)
    """
    
    def __init__(self, max_results: int = 5):
        """
        Initialize query result memory.
        
        Args:
            max_results: Maximum number of results to keep (default: 5)
        """
        self.max_results = max_results
        self.results: List[QueryResult] = []
    
    def add_result(
        self,
        question: str,
        structured_data: List[Dict[str, Any]],
        sql_query: Optional[str] = None,
        tables_used: Optional[List[str]] = None
    ) -> None:
        """
        Add a new query result to memory.
        
        Args:
            question: The user's question
            structured_data: The query result as list of dicts
            sql_query: The SQL query that was executed
            tables_used: List of tables used in the query
        """
        if not structured_data:
            logger.debug("Skipping empty result - no data to remember")
            return
        
        result = QueryResult(
            question=question,
            structured_data=structured_data,
            sql_query=sql_query,
            tables_used=tables_used
        )
        
        self.results.append(result)
        
        # Keep only last N results
        if len(self.results) > self.max_results:
            self.results = self.results[-self.max_results:]
        
        logger.info(
            f"Added query result to memory: {result.row_count} rows, "
            f"{len(result.identifiers)} ID fields, "
            f"memory size: {len(self.results)}/{self.max_results}"
        )
    
    def get_recent_results(self, n: int = 3) -> List[QueryResult]:
        """
        Get the N most recent query results.
        
        Args:
            n: Number of results to retrieve (default: 3)
        
        Returns:
            List of QueryResult objects (most recent first)
        """
        return list(reversed(self.results[-n:]))
    
    def get_all_identifiers(self, n: int = 3) -> Dict[str, List[Any]]:
        """
        Get all identifiers from the last N results.
        
        Args:
            n: Number of recent results to consider
        
        Returns:
            Dict mapping ID field names to lists of unique values
        """
        recent = self.get_recent_results(n)
        all_ids = {}
        
        for result in recent:
            for id_field, values in result.identifiers.items():
                if id_field not in all_ids:
                    all_ids[id_field] = []
                all_ids[id_field].extend(values)
        
        # Deduplicate values for each field
        for id_field in all_ids:
            all_ids[id_field] = list(set(all_ids[id_field]))
        
        return all_ids
    
    def format_for_context(
        self,
        n: int = 3,
        max_tokens: int = 2000,
        include_sample_rows: bool = True
    ) -> str:
        """
        Format recent results as context string for LLM prompts.
        
        Creates a smart summary with:
        - Questions asked
        - Tables used
        - Key identifiers found
        - Sample rows (optional)
        
        Args:
            n: Number of recent results to include
            max_tokens: Approximate max tokens (rough estimate: 4 chars = 1 token)
            include_sample_rows: Whether to include sample data rows
        
        Returns:
            Formatted context string
        """
        recent = self.get_recent_results(n)
        
        if not recent:
            return ""
        
        context_parts = ["PREVIOUS QUERY RESULTS (for context):"]
        context_parts.append("=" * 60)
        
        for i, result in enumerate(recent, 1):
            context_parts.append(f"\n{i}. Question: {result.question}")
            context_parts.append(f"   Tables used: {', '.join(result.tables_used) if result.tables_used else 'N/A'}")
            context_parts.append(f"   Rows returned: {result.row_count}")
            
            # Add identifiers
            if result.identifiers:
                context_parts.append("   Key IDs found:")
                for id_field, values in result.identifiers.items():
                    # Limit to first 5 IDs per field to avoid token bloat
                    display_values = values[:5]
                    more_text = f" (and {len(values) - 5} more)" if len(values) > 5 else ""
                    context_parts.append(f"     - {id_field}: {display_values}{more_text}")
                # When we have "id" and tables_used, tell the model that "id" is the main table's PK
                if "id" in result.identifiers and result.tables_used:
                    main_table = result.tables_used[0] if result.tables_used else None
                    if main_table:
                        context_parts.append(f"   (The 'id' above is the primary key of the main result table: {main_table})")
            
            # Add sample rows if requested and available
            if include_sample_rows and result.row_count > 0:
                sample = result.get_sample_rows(2)
                context_parts.append(f"   Sample data (first {len(sample)} rows):")
                for row_idx, row in enumerate(sample, 1):
                    # Limit columns shown to avoid token bloat
                    row_preview = {k: v for k, v in list(row.items())[:6]}
                    if len(row) > 6:
                        row_preview["..."] = f"({len(row) - 6} more columns)"
                    context_parts.append(f"     Row {row_idx}: {row_preview}")
        
        context_parts.append("=" * 60)
        
        context_str = "\n".join(context_parts)
        
        # Rough token estimate (4 chars ≈ 1 token)
        estimated_tokens = len(context_str) // 4
        
        # If too long, remove sample rows
        if estimated_tokens > max_tokens and include_sample_rows:
            logger.debug(f"Context too long ({estimated_tokens} tokens), removing sample rows")
            return self.format_for_context(n, max_tokens, include_sample_rows=False)
        
        # If still too long, reduce number of results
        if estimated_tokens > max_tokens and n > 1:
            logger.debug(f"Context still too long ({estimated_tokens} tokens), reducing to {n-1} results")
            return self.format_for_context(n - 1, max_tokens, include_sample_rows=False)
        
        return context_str
    
    def clear(self) -> None:
        """Clear all stored results"""
        self.results = []
        logger.debug("Cleared query result memory")
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """
        Serialize memory to dictionary for checkpoint persistence.
        
        Returns:
            List of result dictionaries
        """
        return [result.to_dict() for result in self.results]
    
    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]], max_results: int = 5) -> 'QueryResultMemory':
        """
        Deserialize memory from dictionary (from checkpoint).
        
        Args:
            data: List of result dictionaries
            max_results: Maximum number of results to keep
        
        Returns:
            QueryResultMemory instance
        """
        memory = cls(max_results=max_results)
        memory.results = [QueryResult.from_dict(item) for item in data]
        return memory
    
    def __len__(self) -> int:
        """Return number of stored results"""
        return len(self.results)
    
    def __bool__(self) -> bool:
        """Return True if memory has any results"""
        return len(self.results) > 0
