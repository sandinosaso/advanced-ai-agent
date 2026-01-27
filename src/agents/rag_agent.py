"""
RAG Agent for Phase 3 - Answer generation from retrieved chunks

Retrieves relevant chunks from vector store and generates natural language answers.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from openai import OpenAI
from loguru import logger

from src.utils.rag.vector_store import VectorStore, SearchResult
from src.utils.rag.embedding_service import EmbeddingService


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
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_context_chunks: int = 5
    ):
        """
        Initialize RAG agent
        
        Args:
            vector_store: Vector store for retrieval
            model: OpenAI model for generation
            temperature: Generation temperature (0-1)
            max_context_chunks: Max chunks to include in context
        """
        self.vector_store = vector_store or VectorStore()
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature
        self.max_context_chunks = max_context_chunks
        
        logger.info(f"Initialized RAGAgent (model={model}, max_chunks={max_context_chunks})")
    
    def _build_prompt(self, question: str, chunks: List[SearchResult]) -> str:
        """
        Build prompt with retrieved context
        
        Args:
            question: User question
            chunks: Retrieved chunks
        
        Returns:
            Formatted prompt
        """
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks[:self.max_context_chunks], 1):
            source = chunk.metadata.get('source', 'unknown')
            section = chunk.metadata.get('section_title', '')
            
            context_parts.append(f"[Source {i}: {source}]")
            if section:
                context_parts.append(f"Section: {section}")
            context_parts.append(chunk.text)
            context_parts.append("")  # Blank line
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are a helpful assistant for Field Service Solutions Inc. Answer the question based ONLY on the provided context from company documents.

IMPORTANT RULES:
- Only use information from the context below
- If the answer is not in the context, say "I don't have that information in the company documents"
- Cite which source(s) you used (e.g., "According to the company handbook...")
- Be specific and accurate
- If multiple sources conflict, mention both

CONTEXT FROM COMPANY DOCUMENTS:
{context}

QUESTION: {question}

ANSWER:"""
        
        return prompt
    
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
                answer="I don't have any relevant information in the company documents to answer that question.",
                sources=[],
                confidence=0.0,
                metadata={"collection": collection, "chunks_found": 0}
            )
        
        # Calculate average confidence
        avg_confidence = sum(c.similarity for c in chunks) / len(chunks)
        
        # Build prompt with context
        prompt = self._build_prompt(question, chunks)
        
        # Generate answer
        logger.debug(f"Calling LLM with {len(chunks)} chunks as context")
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        answer = response.choices[0].message.content
        
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
                "model": self.model,
                "temperature": self.temperature
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


if __name__ == "__main__":
    # Quick test
    print("Testing RAG Agent...\n")
    
    agent = RAGAgent(max_context_chunks=3)
    
    test_questions = [
        "What are the overtime rules?",
        "What safety equipment is required for electrical work?",
        "How do I submit expense reports?",
        "What is the company policy on PTO?",
    ]
    
    for question in test_questions:
        print("=" * 80)
        result = agent.answer_with_explanation(question)
        print(result)
        print()
