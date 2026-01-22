"""
FastAPI Development Server

Run the Field Service Intelligence Agent API in development mode.

Usage:
    python run_api.py

The server will start on http://localhost:8000 with:
- Auto-reload on code changes
- Interactive API docs at /docs
- Alternative docs at /redoc
- Health check at /health
- Chat streaming at /api/chat/stream
"""

import uvicorn
from loguru import logger


def main():
    """Start the FastAPI development server"""
    logger.info("="*80)
    logger.info("Field Service Intelligence Agent - API Server")
    logger.info("="*80)
    logger.info("")
    logger.info("Starting FastAPI development server...")
    logger.info("Server will be available at: http://localhost:8000")
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("Health Check: http://localhost:8000/health")
    logger.info("Chat Streaming: POST http://localhost:8000/api/chat/stream")
    logger.info("")
    logger.info("Press CTRL+C to stop the server")
    logger.info("="*80)
    
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info",
        access_log=True,
        reload_dirs=["src"]  # Only watch src directory for changes
    )


if __name__ == "__main__":
    main()
