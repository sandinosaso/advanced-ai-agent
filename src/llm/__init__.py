"""
LLM layer - Client and embeddings
"""

from src.llm.client import create_llm
from src.llm.embeddings import EmbeddingService

__all__ = [
    "create_llm",
    "EmbeddingService",
]
