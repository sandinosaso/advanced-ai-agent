"""
RAG Agent prompt templates
"""

from typing import List
from src.infra.vector_store import SearchResult
from src.config.settings import settings


def get_rag_system_instructions() -> str:
    """Get RAG system instructions with configurable system name."""
    return f"""You are a helpful assistant for {settings.system_name}. Answer the question based ONLY on the provided context from the user manual.

IMPORTANT RULES:
- Only use information from the context below
- If the answer is not in the context, say "I don't have that information in the user manual"
- Cite which source(s) you used (e.g., "According to the user manual...")
- Be specific and accurate
- If multiple sources conflict, mention both
- Provide step-by-step instructions when applicable"""


# Keep the constant for backward compatibility, but use the function for new code
RAG_SYSTEM_INSTRUCTIONS = get_rag_system_instructions()


def build_rag_prompt(question: str, chunks: List[SearchResult], max_chunks: int = 5) -> str:
    """
    Build prompt with retrieved context.

    Args:
        question: User question
        chunks: Retrieved chunks
        max_chunks: Maximum chunks to include in context

    Returns:
        Formatted prompt
    """
    context_parts = []
    for i, chunk in enumerate(chunks[:max_chunks], 1):
        source = chunk.metadata.get('source', 'unknown')
        section = chunk.metadata.get('section_title', '')

        context_parts.append(f"[Source {i}: {source}]")
        if section:
            context_parts.append(f"Section: {section}")
        context_parts.append(chunk.text)
        context_parts.append("")  # Blank line

    context = "\n".join(context_parts)

    prompt = f"""{get_rag_system_instructions()}

CONTEXT FROM USER MANUAL:
{context}

QUESTION: {question}

ANSWER:"""

    return prompt
