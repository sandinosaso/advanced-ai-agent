"""
Populate vector store with Phase 3 documents

This script:
1. Loads all mock documents (handbook, compliance)
2. Chunks them using appropriate strategies
3. Generates embeddings with caching
4. Stores in ChromaDB collections
"""

from pathlib import Path
from loguru import logger

from src.services.mock_documents import (
    COMPANY_HANDBOOK,
    FEDERAL_COMPLIANCE_OSHA,
    FEDERAL_COMPLIANCE_FLSA,
    STATE_COMPLIANCE_EXAMPLE
)
from src.utils.chunking_strategies import (
    chunk_document,
    DocumentStructureChunking,
    RecursiveChunking
)
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore


def populate_vector_store(reset: bool = False) -> None:
    """
    Populate vector store with all documents
    
    Args:
        reset: If True, delete existing collections first
    """
    logger.info("="*60)
    logger.info("Populating Vector Store with Phase 3 Documents")
    logger.info("="*60)
    
    # Initialize services
    embedding_service = EmbeddingService(enable_cache=True)
    vector_store = VectorStore(embedding_service=embedding_service)
    
    if reset:
        logger.warning("Resetting all collections...")
        vector_store.reset_all()
    
    # Document catalog
    documents = [
        {
            "name": "Company Handbook",
            "text": COMPANY_HANDBOOK,
            "type": "handbook",
            "collection": "handbook",
            "metadata": {
                "source": "company_handbook",
                "version": "2026.1",
                "document_type": "handbook"
            }
        },
        {
            "name": "Federal OSHA Compliance",
            "text": FEDERAL_COMPLIANCE_OSHA,
            "type": "compliance",
            "collection": "compliance",
            "metadata": {
                "source": "federal_osha",
                "jurisdiction": "federal",
                "regulation": "OSHA",
                "document_type": "compliance"
            }
        },
        {
            "name": "Federal FLSA Compliance",
            "text": FEDERAL_COMPLIANCE_FLSA,
            "type": "compliance",
            "collection": "compliance",
            "metadata": {
                "source": "federal_flsa",
                "jurisdiction": "federal",
                "regulation": "FLSA",
                "document_type": "compliance"
            }
        },
        {
            "name": "State Compliance (California)",
            "text": STATE_COMPLIANCE_EXAMPLE,
            "type": "compliance",
            "collection": "compliance",
            "metadata": {
                "source": "state_california",
                "jurisdiction": "state",
                "state": "CA",
                "document_type": "compliance"
            }
        }
    ]
    
    total_chunks = 0
    
    for doc in documents:
        logger.info(f"\nProcessing: {doc['name']}")
        logger.info(f"  Length: {len(doc['text']):,} characters")
        
        # Chunk document using appropriate strategy
        if doc['type'] in ('handbook', 'compliance'):
            # Use document structure chunking for well-structured docs
            strategy = DocumentStructureChunking(
                chunk_size=1000,
                chunk_overlap=100
            )
        else:
            # Use recursive chunking for other types
            strategy = RecursiveChunking(
                chunk_size=600,
                chunk_overlap=60
            )
        
        chunks = chunk_document(
            document_text=doc['text'],
            document_type=doc['type'],
            strategy=strategy
        )
        
        logger.info(f"  Created {len(chunks)} chunks")
        
        # Prepare chunks with metadata
        chunk_dicts = []
        for chunk in chunks:
            # Combine document metadata with chunk metadata
            combined_metadata = {
                **doc['metadata'],
                **chunk.metadata,
                "chunk_index": chunk.chunk_index,
                "char_length": len(chunk.text)
            }
            
            chunk_dicts.append({
                "text": chunk.text,
                "metadata": combined_metadata,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char
            })
        
        # Embed chunks (will use cache if available)
        logger.info(f"  Generating embeddings...")
        embedded_chunks = embedding_service.embed_chunks(chunks)
        
        # Add metadata back
        for emb_chunk, chunk_dict in zip(embedded_chunks, chunk_dicts):
            emb_chunk["metadata"] = chunk_dict["metadata"]
        
        # Add to vector store
        logger.info(f"  Adding to collection '{doc['collection']}'...")
        added = vector_store.add_chunks(
            embedded_chunks,
            collection_type=doc['collection']
        )
        
        total_chunks += added
        logger.info(f"  ✓ Added {added} chunks")
        
        # Also add to 'all' collection
        vector_store.add_chunks(
            embedded_chunks,
            collection_type="all"
        )
    
    logger.info("\n" + "="*60)
    logger.info(f"✓ Successfully populated vector store with {total_chunks} total chunks")
    logger.info("="*60)
    
    # Print statistics
    print("\n")
    embedding_service.print_stats()
    vector_store.print_stats()


def test_search() -> None:
    """Test search functionality with sample queries"""
    logger.info("\n" + "="*60)
    logger.info("Testing Search Functionality")
    logger.info("="*60 + "\n")
    
    vector_store = VectorStore()
    
    test_queries = [
        ("What are the overtime rules?", "all"),
        ("What safety equipment is required?", "compliance"),
        ("How do I submit expense reports?", "handbook"),
        ("What is OSHA lockout/tagout?", "compliance"),
        ("What is the company policy on meal breaks?", "all"),
    ]
    
    for query, collection in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"Collection: {collection}")
        print("-" * 60)
        
        results = vector_store.search(
            query=query,
            collection_type=collection,
            k=3
        )
        
        for result in results:
            print(f"\n  Rank {result.rank} (similarity: {result.similarity:.3f})")
            preview = result.text[:150].replace('\n', ' ')
            if len(result.text) > 150:
                preview += "..."
            print(f"  {preview}")
            print(f"  Source: {result.metadata.get('source', 'unknown')}")


if __name__ == "__main__":
    import sys
    
    # Check for --reset flag
    reset = "--reset" in sys.argv
    
    if reset:
        logger.warning("RESET FLAG DETECTED - Will delete existing collections!")
        response = input("Are you sure you want to reset? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Cancelled")
            sys.exit(0)
    
    # Populate vector store
    populate_vector_store(reset=reset)
    
    # Test search if --test flag provided
    if "--test" in sys.argv:
        test_search()
    
    logger.info("\n✓ Vector store ready for Phase 3 RAG pipeline!")
