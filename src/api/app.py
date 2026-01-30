"""
Main FastAPI application for Field Service Intelligence Agent

This module creates and configures the FastAPI application with:
- CORS middleware for frontend integration
- API routes (chat streaming)
- Health check endpoint
- Auto-generated API documentation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import asyncio

from src.api.routes import chat
from src.api.models import HealthResponse
from src.models.conversation_db import get_conversation_db
from src.utils.config import settings
from src.utils.rag.vector_store import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    
    Handles startup and shutdown tasks:
    - Startup: Log application start, initialize resources, start cleanup task
    - Shutdown: Cleanup resources, close connections, cancel cleanup task
    """
    # Startup
    logger.info("🚀 FastAPI application starting...")
    logger.info("📚 API docs available at http://localhost:8000/docs")
    logger.info("🔄 Streaming endpoint at http://localhost:8000/api/chat/stream")
    
    # Check vector store status (for RAG agent)
    if settings.enable_rag_agent:
        try:
            logger.info("📊 Checking RAG vector store status...")
            vector_store = VectorStore()
            stats = vector_store.get_stats()
            
            total_docs = sum(
                coll_info.get("count", 0) 
                for coll_info in stats.get("collections", {}).values()
            )
            
            if total_docs == 0:
                logger.warning("⚠️  Vector store is EMPTY!")
                logger.warning("   RAG queries will not work until vector store is populated.")
                logger.warning("   Run: python scripts/populate_vector_store.py")
                logger.warning("   Or: ./scripts/reset_and_populate_rag.sh")
            else:
                logger.info(f"✅ Vector store ready: {total_docs} total documents across {len(stats.get('collections', {}))} collections")
                
                # Log collection details
                for coll_type, coll_info in stats.get("collections", {}).items():
                    count = coll_info.get("count", 0)
                    if count > 0:
                        logger.debug(f"   - {coll_type}: {count} documents")
        except Exception as e:
            logger.error(f"⚠️  Failed to check vector store: {e}")
            logger.warning("   RAG agent may not function correctly")
    
    # Initialize conversation database and run initial cleanup
    conversation_db = get_conversation_db()
    
    # Initialize async connection and checkpointer
    await conversation_db.async_init()
    
    try:
        deleted = await conversation_db.cleanup_old_conversations(max_age_hours=settings.conversation_max_age_hours)
        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old conversations on startup")
    except Exception as e:
        logger.error(f"Initial cleanup failed: {e}")
    
    # Start background cleanup task
    async def periodic_cleanup():
        """Periodically clean up old conversations"""
        while True:
            try:
                await asyncio.sleep(settings.conversation_cleanup_interval_hours * 3600)
                deleted = await conversation_db.cleanup_old_conversations(max_age_hours=settings.conversation_max_age_hours)
                if deleted > 0:
                    logger.info(f"🧹 Periodic cleanup: removed {deleted} old conversations")
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Periodic cleanup failed: {e}")
    
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    logger.info("🛑 FastAPI application shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Cleanup task stopped")
    
    # Close conversation database checkpointer
    try:
        await conversation_db.close()
        logger.info("✅ Conversation database closed")
    except Exception as e:
        logger.warning(f"Error closing conversation database: {e}")


# Create FastAPI application
app = FastAPI(
    title="Field Service Intelligence Agent API",
    description="""
    Streaming chat API for AI-powered field service assistant.
    
    ## Features
    
    * **Real-time streaming** responses using Server-Sent Events (SSE)
    * **Intelligent routing** between SQL and RAG agents
    * **LangGraph orchestration** for multi-step reasoning
    * **Type-safe** requests and responses with Pydantic
    
    ## Usage
    
    Use the `/api/chat/stream` endpoint to send questions and receive
    streaming responses. The agent will automatically route your question
    to the appropriate backend (SQL database or RAG knowledge base).
    
    ## Example
    
    ```bash
    curl -N -X POST http://localhost:8000/api/chat/stream \\
         -H "Content-Type: application/json" \\
         -d '{"message": "How many technicians are active?"}'
    ```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
# In development, we allow requests from the React dev server (localhost:3000)
# In production, update allow_origins to match your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:3005",  # Alternative port
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "service": "Field Service Intelligence Agent API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "chat_stream": "/api/chat/stream"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint
    
    Use this endpoint to verify the service is running.
    Returns service status, name, and version.
    
    Returns:
        HealthResponse with service status
    """
    return HealthResponse(
        status="healthy",
        service="fsia-api",
        version="1.0.0"
    )
