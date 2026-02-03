"""
Populate vector store with user manual documents

This script:
1. Loads all markdown files from data/manual/ directory
2. Chunks them using appropriate strategies
3. Generates embeddings with caching
4. Stores in ChromaDB collections
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from loguru import logger

from src.utils.rag.chunking_strategies import (
    chunk_document,
    DocumentStructureChunking,
    RecursiveChunking
)
from src.llm.embeddings import EmbeddingService
from src.infra.vector_store import VectorStore


def get_project_root() -> Path:
    """Get project root directory"""
    # This file is at scripts/populate_vector_store.py
    # Project root is parent of scripts/
    return Path(__file__).parent.parent


def load_manual_documents(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all markdown files from data/manual/ directory
    
    Args:
        data_dir: Path to data directory (project_root/data)
    
    Returns:
        List of document dictionaries with name, text, type, collection, and metadata
    """
    manual_dir = data_dir / "manual"
    
    if not manual_dir.exists():
        logger.error(f"Manual directory not found: {manual_dir}")
        return []
    
    documents = []
    
    # Find all markdown files
    md_files = sorted(manual_dir.glob("*.md"))
    
    if not md_files:
        logger.warning(f"No markdown files found in {manual_dir}")
        return []
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract module name from filename (e.g., "core", "customers", "work-orders")
            module_name = md_file.stem
            
            # Try to extract version from file header if present
            version = "1.0"  # Default version
            lines = content.split('\n', 10)
            for line in lines:
                if 'version' in line.lower() or 'Version' in line:
                    # Try to extract version number
                    version_match = re.search(r'(\d+\.\d+)', line)
                    if version_match:
                        version = version_match.group(1)
                        break
            
            documents.append({
                "name": f"User Manual - {module_name.replace('-', ' ').title()}",
                "text": content,
                "type": "manual",
                "collection": "manual",
                "metadata": {
                    "source": module_name,
                    "document_type": "user_manual",
                    "module": module_name,
                    "file_path": str(md_file.relative_to(data_dir)),
                    "version": version
                }
            })
            
            logger.debug(f"Loaded manual document: {md_file.name} ({len(content):,} chars)")
            
        except Exception as e:
            logger.error(f"Failed to load {md_file}: {e}")
            continue
    
    return documents


def populate_vector_store(reset: bool = False) -> None:
    """
    Populate vector store with user manual documents
    
    Args:
        reset: If True, delete existing collections first
    """
    logger.info("="*60)
    logger.info("Populating Vector Store with User Manual Documents")
    logger.info("="*60)
    
    # Get project root and data directory
    project_root = get_project_root()
    data_dir = project_root / "data"
    
    # Initialize services
    embedding_service = EmbeddingService(enable_cache=True)
    vector_store = VectorStore(embedding_service=embedding_service)
    
    if reset:
        logger.warning("Resetting all collections...")
        vector_store.reset_all()
    
    # Load manual documents from data/manual/ directory
    documents = load_manual_documents(data_dir)
    
    if not documents:
        logger.error("No documents loaded. Exiting.")
        return
    
    logger.info(f"Loaded {len(documents)} manual document(s)")
    
    total_chunks = 0
    
    for doc in documents:
        logger.info(f"\nProcessing: {doc['name']}")
        logger.info(f"  Length: {len(doc['text']):,} characters")
        
        # Chunk document using appropriate strategy
        if doc['type'] == 'manual':
            # Use document structure chunking for well-structured markdown docs
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
    """Test search functionality with system usage queries"""
    logger.info("\n" + "="*60)
    logger.info("Testing Search Functionality")
    logger.info("="*60 + "\n")
    
    vector_store = VectorStore()
    
    test_queries = [
        ("How do I create a work order?", "all"),
        ("How do I add a customer location?", "manual"),
        ("What are the steps to complete an inspection?", "all"),
        ("How do I filter work orders by status?", "manual"),
        ("What permissions are needed for the core module?", "all"),
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
    
    logger.info("\n✓ Vector store ready for RAG pipeline with user manual!")
