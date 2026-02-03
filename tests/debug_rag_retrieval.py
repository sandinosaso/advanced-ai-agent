"""
Debug script to see what chunks are being retrieved for OSHA question
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from services.vector_store import VectorStore
from services.embedding_service import EmbeddingService

def debug_search(question: str):
    """Show what chunks are retrieved for a question"""
    print(f"\n{'='*80}")
    print(f"QUESTION: {question}")
    print(f"{'='*80}\n")
    
    # Initialize services
    embedding_service = EmbeddingService()
    vector_store = VectorStore(embedding_service=embedding_service)
    
    # Search
    results = vector_store.search(
        query=question,
        collection_type="all",
        k=5
    )
    
    print(f"Found {len(results)} chunks:\n")
    
    for i, result in enumerate(results, 1):
        print(f"--- CHUNK {i} ---")
        print(f"Similarity: {result.similarity:.4f}")
        print(f"Source: {result.metadata.get('source', 'unknown')}")
        print(f"Content ({len(result.text)} chars):")
        print(result.text[:500])  # First 500 chars
        if len(result.text) > 500:
            print(f"... (truncated, {len(result.text) - 500} more chars)")
        print()

if __name__ == "__main__":
    # Test the OSHA question
    debug_search("As a worker can I request an OSHA inspection?")
    
    # Also test a more general OSHA search
    print("\n" + "="*80)
    print("TESTING MORE GENERAL SEARCH")
    print("="*80)
    debug_search("employee rights under OSHA")
