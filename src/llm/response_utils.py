"""
LLM response utilities for handling multi-format model outputs.

Supports both:
- Simple string responses (gpt-4o-mini, gpt-4, etc.)
- Structured content blocks with reasoning (gpt-5.2-pro, o1, etc.)
"""

from typing import Any, Optional
from loguru import logger


def extract_text_from_response(response: Any) -> str:
    """
    Extract text content from LLM response (handles all formats).

    Supports:
    - Simple string: "text here"
    - Structured blocks: [{'type': 'reasoning', ...}, {'type': 'text', 'text': '...'}]
    - LangChain AIMessage with content attribute

    Args:
        response: LLM response (AIMessage, dict, str, or list)

    Returns:
        Extracted text content as string

    Example:
        # Old model
        response.content = "SELECT * FROM users"
        extract_text_from_response(response) -> "SELECT * FROM users"

        # New model with reasoning
        response.content = [
            {'type': 'reasoning', 'text': '...'},
            {'type': 'text', 'text': 'SELECT * FROM users'}
        ]
        extract_text_from_response(response) -> "SELECT * FROM users"
    """
    # Extract content attribute if it exists (LangChain AIMessage)
    content = response.content if hasattr(response, "content") else response

    if not content:
        return ""

    # Handle string content (old models)
    if isinstance(content, str):
        return content

    # Handle structured content blocks (new models)
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                # Extract text from 'text' type blocks
                if block.get("type") == "text" and "text" in block:
                    text_parts.append(block["text"])
                # Fallback: any dict with 'text' key
                elif "text" in block and block.get("type") != "reasoning":
                    text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)

        result = "".join(text_parts)
        if result:
            return result

        # If no text blocks found, log warning and return empty
        content_preview = str(content)[:200] if len(str(content)) > 200 else content
        logger.warning(f"No text blocks found in structured response: {content_preview}")
        return ""

    # Fallback: convert to string
    return str(content)


def extract_reasoning_from_response(response: Any) -> Optional[str]:
    """
    Extract reasoning steps from structured LLM response (if present).

    New models like gpt-5.2-pro include reasoning blocks that explain their thinking.
    These can be optionally streamed to the user for transparency.

    Args:
        response: LLM response

    Returns:
        Reasoning text if present, None otherwise
    """
    content = response.content if hasattr(response, "content") else response

    if not isinstance(content, list):
        return None

    reasoning_parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "reasoning":
            if "text" in block:
                reasoning_parts.append(block["text"])
            elif "summary" in block and block["summary"]:
                reasoning_parts.append(" ".join(str(s) for s in block["summary"]))

    return "\n".join(reasoning_parts) if reasoning_parts else None
