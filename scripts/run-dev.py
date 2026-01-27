"""
FastAPI Development Server

Run the Field Service Intelligence Agent API in development mode.

Usage:
    python scripts/run-dev.py
    # OR
    uv run python scripts/run-dev.py
    # OR (after activating venv)
    source .venv/bin/activate
    python scripts/run-dev.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

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
        reload=True,
        log_level="info",
        access_log=True,
        reload_dirs=[str(project_root / "src")]
    )


if __name__ == "__main__":
    main()
