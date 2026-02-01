"""
Conversation database abstraction layer for LangGraph checkpointing.

Provides:
- SQLite checkpoint initialization with WAL mode for concurrency
- Message truncation and memory management
- Cleanup of old conversations
- Abstraction layer for future migration to MySQL/Redis
"""

from pathlib import Path
import asyncio
import aiosqlite
from typing import List, Optional
from langchain_core.messages import BaseMessage
from loguru import logger

try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
except ImportError:
    logger.error("AsyncSqliteSaver not available. Install aiosqlite: pip install aiosqlite")
    raise

from src.config.settings import settings


class ConversationDatabase:
    """Abstraction layer for conversation storage"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize conversation database
        
        Args:
            db_path: Path to SQLite database (defaults to settings.conversation_db_path_resolved)
        """
        self._conn = None  # Store aiosqlite connection to keep it open
        self._checkpointer = None  # Will be set in async_init()
        self._initialized = False
        
        if db_path is None:
            db_path = getattr(settings, 'conversation_db_path_resolved', settings.conversation_db_path)
        
        self.db_path = Path(db_path)
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate write permissions
        if not self.db_path.parent.exists():
            raise PermissionError(f"Cannot create directory: {self.db_path.parent}")
    
    async def async_init(self):
        """Async initialization of AsyncSqliteSaver - call this from lifespan startup"""
        if self._initialized:
            return
        
        try:
            # Create aiosqlite connection with proper settings
            conn = await aiosqlite.connect(
                str(self.db_path),
                timeout=10.0
            )
            
            # Set WAL mode and other pragmas
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            await conn.commit()
            
            # Create AsyncSqliteSaver directly with the connection
            self._checkpointer = AsyncSqliteSaver(conn)
            self._conn = conn  # Store connection to keep it open
            self._initialized = True
            
            logger.info("Initialized AsyncSqliteSaver checkpointer with direct connection")
        except Exception as e:
            logger.error(f"Failed to create AsyncSqliteSaver: {e}")
            raise
    
    @property
    def checkpointer(self):
        """Get checkpointer for LangGraph workflow"""
        if not self._initialized:
            raise RuntimeError("ConversationDatabase not initialized. Call async_init() first.")
        return self._checkpointer
    
    def _setup_wal_mode(self):
        """Enable WAL mode for better SQLite concurrency"""
        # Note: WAL mode is now set when creating the connection in __init__
        # This method is kept for backward compatibility but does nothing
        # The actual WAL setup happens in __init__ when creating the connection
        pass
    
    def get_checkpointer(self):
        """Get checkpointer for LangGraph workflow"""
        return self.checkpointer
    
    async def close(self):
        """Close the aiosqlite connection"""
        if self._conn:
            try:
                await self._conn.close()
                logger.debug("Closed aiosqlite connection")
            except Exception as e:
                logger.warning(f"Error closing aiosqlite connection: {e}")
    
    def truncate_messages(self, messages: List[BaseMessage], max_messages: int) -> List[BaseMessage]:
        """
        Truncate messages to max_messages (keeps most recent)
        
        Args:
            messages: List of messages to truncate
            max_messages: Maximum number of messages to keep
            
        Returns:
            Truncated list of messages (most recent N messages)
        """
        if not messages:
            return messages
        # Simple implementation: keep last N messages
        # Future: can extend to tiered memory (short/medium/long term)
        return list(messages[-max_messages:]) if len(messages) > max_messages else list(messages)
    
    def prepare_messages_for_context(
        self, 
        messages: List[BaseMessage], 
        strategy: str = "simple"
    ) -> List[BaseMessage]:
        """
        Prepare messages for LLM context based on strategy
        
        NOTE: This is ONLY for message processing, NOT storage.
        Storage is handled by LangGraph checkpointing.
        
        Args:
            messages: List of messages to prepare
            strategy: Memory strategy ("simple" or "tiered")
            
        Returns:
            Prepared list of messages for LLM context
        """
        if not messages:
            return messages
            
        max_messages = settings.max_conversation_messages
        
        if strategy == "simple":
            return self.truncate_messages(messages, max_messages)
        elif strategy == "tiered":
            # Future: Implement tiered memory with summarization
            # For now, fall back to simple
            return self.truncate_messages(messages, max_messages)
        else:
            return self.truncate_messages(messages, max_messages)
    
    async def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """
        Delete conversations older than max_age_hours
        
        Uses LangGraph checkpoint API to list and delete threads.
        Note: Timestamp is stored in checkpoint BLOB, so we load checkpoints
        to check their age. For better performance, we limit the check to recent checkpoints.
        
        Args:
            max_age_hours: Maximum age in hours before deletion
            
        Returns:
            Number of conversations deleted
        """
        import datetime
        import json
        
        cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=max_age_hours)
        
        # Use AsyncSqliteSaver's list method to get checkpoints with timestamps
        # Then filter by age and delete old threads
        try:
            if not self._checkpointer:
                logger.warning("Checkpointer not initialized, skipping cleanup")
                return 0
            
            # Get all threads (we'll check their latest checkpoint timestamp)
            async with aiosqlite.connect(str(self.db_path), timeout=10.0) as conn:
                # Get distinct thread_ids
                cursor = await conn.execute("SELECT DISTINCT thread_id FROM checkpoints")
                thread_ids = [row[0] for row in await cursor.fetchall()]
                
                deleted_count = 0
                for thread_id in thread_ids:
                    try:
                        # Get the latest checkpoint for this thread
                        config = {"configurable": {"thread_id": thread_id}}
                        checkpoint_tuple = await self._checkpointer.aget_tuple(config)
                        
                        if checkpoint_tuple:
                            # Check timestamp from checkpoint
                            checkpoint = checkpoint_tuple.checkpoint if hasattr(checkpoint_tuple, 'checkpoint') else checkpoint_tuple[1]
                            if isinstance(checkpoint, dict):
                                ts_str = checkpoint.get("ts")
                                if ts_str:
                                    try:
                                        # Parse timestamp (ISO format)
                                        checkpoint_time = datetime.datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                        if checkpoint_time.tzinfo is None:
                                            checkpoint_time = checkpoint_time.replace(tzinfo=datetime.timezone.utc)
                                        
                                        # If checkpoint is older than cutoff, delete thread
                                        if checkpoint_time < cutoff_time:
                                            await self._checkpointer.adelete_thread(thread_id)
                                            deleted_count += 1
                                    except (ValueError, TypeError) as e:
                                        logger.debug(f"Could not parse timestamp for thread {thread_id}: {e}")
                                        # If we can't parse timestamp, skip this thread
                                        continue
                    except Exception as e:
                        logger.error(f"Failed to check/delete thread {thread_id}: {e}")
                        continue
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old conversations")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            return 0


# Global instance (singleton pattern)
_conversation_db: Optional[ConversationDatabase] = None


def get_conversation_db() -> ConversationDatabase:
    """Get global conversation database instance (singleton)"""
    global _conversation_db
    if _conversation_db is None:
        _conversation_db = ConversationDatabase()
    return _conversation_db
