"""
Vector store service using ChromaDB for Phase 3 RAG implementation

Handles:
- Multiple collections (handbook, compliance, receipts, work_logs)
- Metadata filtering
- Similarity search with configurable k
- Hybrid search (vector + keyword filtering)
- Persistent storage
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from loguru import logger

from src.utils.rag.embedding_service import EmbeddingService


@dataclass
class SearchResult:
    """Single search result with score"""
    text: str
    metadata: Dict[str, Any]
    distance: float  # Lower is better (cosine distance)
    similarity: float  # 0-1, higher is better
    rank: int
    
    def __repr__(self) -> str:
        preview = self.text[:80] + "..." if len(self.text) > 80 else self.text
        return f"SearchResult(rank={self.rank}, similarity={self.similarity:.3f}, text='{preview}')"


class VectorStore:
    """
    ChromaDB-based vector store for RAG
    
    Manages multiple collections for different document types
    with metadata filtering and hybrid search capabilities.
    """
    
    COLLECTION_NAMES = {
        "handbook": "company_handbook",
        "compliance": "compliance_documents",
        "receipts": "expense_receipts",
        "work_logs": "work_log_descriptions",
        "all": "all_documents"  # Combined collection
    }
    
    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize vector store
        
        Args:
            persist_directory: Directory for persistent storage
            embedding_service: Service for generating embeddings
        """
        if persist_directory is None:
            # Find project root (this file is at src/utils/rag/vector_store.py)
            project_root = Path(__file__).parent.parent.parent.parent
            persist_directory = project_root / "data" / "vector_store"
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Embedding service
        self.embedding_service = embedding_service or EmbeddingService()
        
        # Collection cache
        self.collections: Dict[str, chromadb.Collection] = {}
        
        logger.info(f"Initialized VectorStore at {persist_directory}")
        self._log_collections()
    
    def _log_collections(self) -> None:
        """Log existing collections"""
        collections = self.client.list_collections()
        if collections:
            logger.info(f"Found {len(collections)} existing collections:")
            for coll in collections:
                count = coll.count()
                logger.info(f"  - {coll.name}: {count} documents")
        else:
            logger.info("No existing collections found")
    
    def get_or_create_collection(
        self,
        collection_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> chromadb.Collection:
        """
        Get or create a collection
        
        Args:
            collection_type: Type key (handbook, compliance, etc.)
            metadata: Optional collection-level metadata
        
        Returns:
            ChromaDB collection
        """
        collection_name = self.COLLECTION_NAMES.get(collection_type, collection_type)
        
        if collection_name in self.collections:
            return self.collections[collection_name]
        
        # Create or get collection
        # Note: ChromaDB uses its own embedding function, but we'll pass
        # embeddings directly so we can use our caching service
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or {"type": collection_type}
        )
        
        self.collections[collection_name] = collection
        logger.debug(f"Got collection '{collection_name}' ({collection.count()} docs)")
        
        return collection
    
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        collection_type: str = "all",
        batch_size: int = 100
    ) -> int:
        """
        Add chunks to vector store
        
        Args:
            chunks: List of chunks with text, metadata, and optionally embeddings
            collection_type: Which collection to add to
            batch_size: Batch size for adding documents
        
        Returns:
            Number of chunks added
        """
        if not chunks:
            logger.warning("No chunks to add")
            return 0
        
        collection = self.get_or_create_collection(collection_type)
        
        # Check if chunks have embeddings, otherwise generate them
        if "embedding" not in chunks[0]:
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_service.embed_texts(texts)
            
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding
        
        # Add in batches
        added = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Prepare data for ChromaDB
            # Use source from metadata to create unique IDs across collections
            ids = []
            for j, chunk in enumerate(batch):
                source = chunk.get("metadata", {}).get("source", "unknown")
                chunk_idx = chunk.get("metadata", {}).get("chunk_index", i+j)
                ids.append(f"{source}_{chunk_idx}_{i+j}")
            
            texts = [chunk["text"] for chunk in batch]
            embeddings = [chunk["embedding"] for chunk in batch]
            metadatas = [chunk.get("metadata", {}) for chunk in batch]
            
            # Add to collection
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            added += len(batch)
            logger.debug(f"Added batch {i//batch_size + 1}: {len(batch)} chunks")
        
        logger.info(f"Added {added} chunks to collection '{collection.name}'")
        return added
    
    def search(
        self,
        query: str,
        collection_type: str = "all",
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        include_distances: bool = True
    ) -> List[SearchResult]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            collection_type: Which collection to search
            k: Number of results to return
            metadata_filter: Optional metadata filters
            include_distances: Whether to include distance scores
        
        Returns:
            List of search results
        """
        collection = self.get_or_create_collection(collection_type)
        
        if collection.count() == 0:
            logger.warning(f"Collection '{collection.name}' is empty")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Build where clause for metadata filtering
        where = metadata_filter if metadata_filter else None
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert to SearchResult objects
        search_results = []
        
        if results and results["documents"]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(documents)
            
            for rank, (text, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                # Convert distance to similarity (0-1, higher is better)
                # ChromaDB uses squared L2 distance, convert to similarity
                similarity = 1.0 / (1.0 + distance)
                
                search_results.append(SearchResult(
                    text=text,
                    metadata=metadata,
                    distance=distance,
                    similarity=similarity,
                    rank=rank + 1
                ))
        
        logger.info(f"Search for '{query[:50]}...' returned {len(search_results)} results")
        return search_results
    
    def hybrid_search(
        self,
        query: str,
        collection_type: str = "all",
        k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        keyword_boost: float = 0.3
    ) -> List[SearchResult]:
        """
        Hybrid search combining vector similarity and keyword matching
        
        Args:
            query: Search query
            collection_type: Which collection to search
            k: Number of results
            metadata_filter: Optional metadata filters
            keyword_boost: Weight for keyword matches (0-1)
        
        Returns:
            Reranked search results
        """
        # Get vector search results
        vector_results = self.search(
            query=query,
            collection_type=collection_type,
            k=k * 2,  # Get more for reranking
            metadata_filter=metadata_filter
        )
        
        # Simple keyword matching (production would use BM25 or similar)
        query_terms = set(query.lower().split())
        
        # Rerank with keyword boost
        for result in vector_results:
            text_terms = set(result.text.lower().split())
            keyword_overlap = len(query_terms & text_terms) / max(len(query_terms), 1)
            
            # Combine scores
            result.similarity = (
                result.similarity * (1 - keyword_boost) +
                keyword_overlap * keyword_boost
            )
        
        # Re-sort by new similarity score
        vector_results.sort(key=lambda r: r.similarity, reverse=True)
        
        # Update ranks
        for i, result in enumerate(vector_results[:k]):
            result.rank = i + 1
        
        return vector_results[:k]
    
    def delete_collection(self, collection_type: str) -> None:
        """Delete a collection"""
        collection_name = self.COLLECTION_NAMES.get(collection_type, collection_type)
        
        try:
            self.client.delete_collection(collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]
            logger.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
    
    def reset_all(self) -> None:
        """Delete all collections (use with caution!)"""
        logger.warning("Resetting all collections...")
        self.client.reset()
        self.collections = {}
        logger.info("All collections deleted")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about vector store"""
        stats = {
            "persist_directory": str(self.persist_directory),
            "collections": {}
        }
        
        for coll_type, coll_name in self.COLLECTION_NAMES.items():
            try:
                coll = self.client.get_collection(coll_name)
                stats["collections"][coll_type] = {
                    "name": coll_name,
                    "count": coll.count(),
                    "metadata": coll.metadata
                }
            except Exception:
                stats["collections"][coll_type] = {
                    "name": coll_name,
                    "count": 0,
                    "metadata": None
                }
        
        return stats
    
    def print_stats(self) -> None:
        """Print statistics"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("Vector Store Statistics")
        print("="*60)
        print(f"Location: {stats['persist_directory']}")
        print("\nCollections:")
        
        total_docs = 0
        for coll_type, coll_info in stats["collections"].items():
            count = coll_info["count"]
            total_docs += count
            status = "✓" if count > 0 else "○"
            print(f"  {status} {coll_type:15} ({coll_info['name']}): {count:5} docs")
        
        print(f"\nTotal documents: {total_docs}")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Quick test
    print("Testing Vector Store...\n")
    
    # Initialize
    vector_store = VectorStore()
    
    # Add some test documents
    test_chunks = [
        {
            "text": "All HVAC technicians must complete annual safety training and certification.",
            "metadata": {"section": "safety", "document": "handbook"}
        },
        {
            "text": "Expense reimbursement requests must include itemized receipts for all purchases over $25.",
            "metadata": {"section": "expenses", "document": "handbook"}
        },
        {
            "text": "Overtime hours are paid at 1.5x the regular hourly rate for hours worked beyond 40 in a week.",
            "metadata": {"section": "compensation", "document": "handbook"}
        }
    ]
    
    print(f"Adding {len(test_chunks)} test documents...\n")
    vector_store.add_chunks(test_chunks, collection_type="handbook")
    
    # Test search
    query = "What are the safety requirements for technicians?"
    print(f"Searching for: '{query}'\n")
    
    results = vector_store.search(query, collection_type="handbook", k=3)
    
    print(f"Found {len(results)} results:\n")
    for result in results:
        print(f"  Rank {result.rank} (similarity: {result.similarity:.3f})")
        print(f"  {result.text}")
        print(f"  Metadata: {result.metadata}\n")
    
    vector_store.print_stats()
