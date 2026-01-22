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

from src.api.routes import chat
from src.api.models import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    
    Handles startup and shutdown tasks:
    - Startup: Log application start, initialize resources
    - Shutdown: Cleanup resources, close connections
    """
    # Startup
    logger.info("🚀 FastAPI application starting...")
    logger.info("📚 API docs available at http://localhost:8000/docs")
    logger.info("🔄 Streaming endpoint at http://localhost:8000/api/chat/stream")
    
    yield
    
    # Shutdown
    logger.info("🛑 FastAPI application shutting down...")


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
