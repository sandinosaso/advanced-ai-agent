"""
FastAPI Production Server

Run the Field Service Intelligence Agent API in production mode.

Usage:
    python scripts/run-prod.py
    # OR
    uv run python scripts/run-prod.py
    # OR (after activating venv)
    source .venv/bin/activate
    python scripts/run-prod.py
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
    """Start the FastAPI production server"""
    logger.info("="*80)
    logger.info("Field Service Intelligence Agent - API Server (Production)")
    logger.info("="*80)
    logger.info("")
    logger.info("Starting FastAPI production server...")
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
        reload=False,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
