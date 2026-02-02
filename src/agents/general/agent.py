"""
General Agent - Answers general knowledge questions

Handles questions that don't require SQL or RAG (e.g., definitions, explanations).
"""

from typing import List, Optional, Sequence
from loguru import logger

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from src.llm.client import create_llm
from src.config.settings import settings


class GeneralAgent:
    """
    General knowledge agent.

    Answers questions that don't require database or document retrieval.
    Uses conversation history for context.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        Initialize general agent.

        Args:
            llm: LangChain chat model (defaults to create_llm)
            model: Model name override
            temperature: Temperature override
        """
        self.llm = llm or create_llm(
            model=model,
            temperature=temperature if temperature is not None else settings.orchestrator_temperature,
            max_completion_tokens=settings.max_output_tokens
        )
        logger.info("Initialized GeneralAgent")

    def answer(self, question: str, messages: Sequence[BaseMessage]) -> str:
        """
        Answer a general knowledge question.

        Args:
            question: User question
            messages: Conversation history (will be used for context)

        Returns:
            Answer string
        """
        logger.info(f"General agent question: '{question}'")
        logger.info(f"General agent received {len(messages)} messages for context")

        # Add system message to instruct the LLM to use conversation history
        system_message = SystemMessage(content="""You are a helpful AI assistant with access to the conversation history.

IMPORTANT: You have full access to our conversation history. When asked about:
- Previous questions: Review the conversation and list what the user asked
- What we discussed: Summarize topics from our conversation
- Earlier responses: Reference specific answers you gave before
- Context from history: Use previous messages to provide relevant answers

The conversation history is provided in the messages above. Use it to give accurate, context-aware responses.""")
        
        messages_for_llm = [system_message] + list(messages)
        if not isinstance(messages_for_llm[-1], HumanMessage):
            messages_for_llm.append(HumanMessage(content=question))
        
        logger.debug(f"Sending {len(messages_for_llm)} messages to LLM (including system message)")
        if len(messages_for_llm) > 2:  # system + at least 1 previous + current
            logger.debug(f"Previous messages included: {len(messages_for_llm) - 2} messages")

        response = self.llm.invoke(messages_for_llm)
        answer = (
            response.content
            if hasattr(response, "content") and response.content
            else "I couldn't generate an answer. Please try again."
        )

        return answer
