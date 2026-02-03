"""
RAG Agent - Answer generation from retrieved chunks

Retrieves relevant chunks from vector store and generates natural language answers.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_core.messages import HumanMessage
from loguru import logger

from src.infra.vector_store import VectorStore, SearchResult
from src.llm.client import create_llm
from src.config.settings import settings
from src.agents.rag.prompts import build_rag_prompt


@dataclass
class RAGResponse:
    """Response from RAG agent with sources"""
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]


class RAGAgent:
    """
    Retrieval-Augmented Generation agent

    Answers questions by:
    1. Retrieving relevant chunks from vector store
    2. Constructing context-rich prompt
    3. Generating answer with LLM
    4. Providing source attribution
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_context_chunks: int = 5
    ):
        """
        Initialize RAG agent

        Args:
            vector_store: Vector store for retrieval
            model: LLM model for generation (defaults to provider-specific model)
            temperature: Generation temperature (defaults to settings.openai_temperature)
            max_context_chunks: Max chunks to include in context
        """
        self.vector_store = vector_store or VectorStore()
        self.llm = create_llm(
            model=model,
            temperature=temperature if temperature is not None else settings.openai_temperature
        )
        self.max_context_chunks = max_context_chunks

        logger.info(f"Initialized RAGAgent (max_chunks={max_context_chunks})")

    def answer(
        self,
        question: str,
        collection: str = "all",
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> RAGResponse:
        """
        Answer a question using RAG

        Args:
            question: User question
            collection: Which collection to search
            k: Number of chunks to retrieve
            metadata_filter: Optional metadata filters

        Returns:
            RAG response with answer and sources
        """
        logger.info(f"RAG question: '{question}' (collection={collection}, k={k})")

        # Retrieve relevant chunks
        chunks = self.vector_store.search(
            query=question,
            collection_type=collection,
            k=k,
            metadata_filter=metadata_filter
        )

        if not chunks:
            logger.warning("No relevant chunks found")
            return RAGResponse(
                question=question,
                answer="I don't have any relevant information in the user manual to answer that question.",
                sources=[],
                confidence=0.0,
                metadata={"collection": collection, "chunks_found": 0}
            )

        # Calculate average confidence
        avg_confidence = sum(c.similarity for c in chunks) / len(chunks)

        # Build prompt with context
        prompt = build_rag_prompt(question, chunks, self.max_context_chunks)

        # Generate answer using LangChain chat model
        logger.debug(f"Calling LLM with {len(chunks)} chunks as context")
        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        answer = response.content
        if not answer:
            answer = "I couldn't generate an answer. Please try again."

        # Extract sources
        sources = []
        for chunk in chunks:
            sources.append({
                "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                "metadata": chunk.metadata,
                "similarity": chunk.similarity,
                "rank": chunk.rank
            })

        logger.info(f"Generated answer ({len(answer)} chars) with {len(sources)} sources")

        return RAGResponse(
            question=question,
            answer=answer,
            sources=sources,
            confidence=avg_confidence,
            metadata={
                "collection": collection,
                "chunks_retrieved": len(chunks),
                "provider": settings.llm_provider
            }
        )

    def answer_with_explanation(self, question: str, **kwargs) -> str:
        """
        Answer question and format with sources

        Args:
            question: User question
            **kwargs: Additional arguments for answer()

        Returns:
            Formatted answer with sources
        """
        response = self.answer(question, **kwargs)

        output = []
        output.append(f"Question: {response.question}")
        output.append("")
        output.append("Answer:")
        output.append(response.answer)
        output.append("")
        output.append(f"Confidence: {response.confidence:.2%}")
        output.append("")
        output.append("Sources:")
        for source in response.sources:
            output.append(f"  [{source['rank']}] {source['metadata'].get('source', 'unknown')} "
                         f"(similarity: {source['similarity']:.3f})")
            if 'section_title' in source['metadata']:
                output.append(f"      Section: {source['metadata']['section_title']}")

        return "\n".join(output)
