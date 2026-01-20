"""
Main application entry point.
"""

from src.utils.logger import logger
from src.utils.config import settings, load_config


def main():
    """Main application function."""
    logger.info("=== AI Learning Project ===")
    
    # Load configuration
    config = load_config()
    logger.info(f"Application: {config.app.name}")
    logger.info(f"Environment: {config.app.environment}")
    logger.info(f"LLM Model: {config.llm.model}")
    logger.info(f"Vector DB Collection: {config.vector_db.collection_name}")
    
    logger.info("Ready for your next use case!")
    logger.info("Infrastructure includes:")
    logger.info("  ✓ Python 3.11 with UV package manager")
    logger.info("  ✓ LangChain & LangGraph")
    logger.info("  ✓ OpenAI integration")
    logger.info("  ✓ Configuration management")
    logger.info("  ✓ Logging utilities")
    logger.info("  ✓ Nx monorepo structure")
    logger.info("")
    logger.info("Learning objectives ready:")
    logger.info("  • LangGraph workflows")
    logger.info("  • RAG patterns with vector stores")
    logger.info("  • Embeddings & chunking")
    logger.info("  • Memory management")
    logger.info("  • Tool orchestration")


if __name__ == "__main__":
    main()
