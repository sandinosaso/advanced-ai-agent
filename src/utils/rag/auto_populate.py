"""
Auto-populate vector store if empty

This utility checks if the vector store is empty and automatically populates it
if needed. Can be called during application startup.
"""
from pathlib import Path
from loguru import logger

from src.utils.rag.vector_store import VectorStore
from src.utils.rag.embedding_service import EmbeddingService


def check_and_populate_if_needed(force: bool = False) -> bool:
    """
    Check if vector store is empty and populate if needed
    
    Args:
        force: If True, repopulate even if not empty
        
    Returns:
        True if population was performed, False otherwise
    """
    try:
        # Check current status
        vector_store = VectorStore()
        stats = vector_store.get_stats()
        
        total_docs = sum(
            coll_info.get("count", 0) 
            for coll_info in stats.get("collections", {}).values()
        )
        
        if total_docs > 0 and not force:
            logger.debug(f"Vector store already populated with {total_docs} documents")
            return False
        
        if total_docs == 0:
            logger.warning("Vector store is empty - auto-populating...")
        elif force:
            logger.info("Force flag set - repopulating vector store...")
        
        # Import populate function
        import sys
        project_root = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from scripts.populate_vector_store import populate_vector_store
        
        # Populate without reset (unless force)
        populate_vector_store(reset=force)
        
        logger.info("✅ Vector store auto-population complete")
        return True
        
    except Exception as e:
        logger.error(f"Failed to auto-populate vector store: {e}")
        return False


def ensure_vector_store_ready() -> dict:
    """
    Ensure vector store is ready for use
    
    Returns:
        Dictionary with status information
    """
    try:
        vector_store = VectorStore()
        stats = vector_store.get_stats()
        
        total_docs = sum(
            coll_info.get("count", 0) 
            for coll_info in stats.get("collections", {}).values()
        )
        
        if total_docs == 0:
            logger.warning("Vector store is empty")
            return {
                "ready": False,
                "total_documents": 0,
                "collections": {},
                "message": "Vector store is empty. Run: python scripts/populate_vector_store.py"
            }
        
        return {
            "ready": True,
            "total_documents": total_docs,
            "collections": stats.get("collections", {}),
            "message": f"Vector store ready with {total_docs} documents"
        }
        
    except Exception as e:
        logger.error(f"Failed to check vector store: {e}")
        return {
            "ready": False,
            "total_documents": 0,
            "collections": {},
            "error": str(e),
            "message": "Vector store check failed"
        }


if __name__ == "__main__":
    import sys
    
    # Check for --force flag
    force = "--force" in sys.argv
    
    print("Checking vector store status...")
    status = ensure_vector_store_ready()
    
    if status["ready"]:
        print(f"✅ {status['message']}")
        for coll_type, info in status.get("collections", {}).items():
            print(f"   - {coll_type}: {info.get('count', 0)} docs")
    else:
        print(f"⚠️  {status['message']}")
        
        if "--auto-populate" in sys.argv or force:
            print("\nAuto-populating...")
            success = check_and_populate_if_needed(force=force)
            if success:
                print("✅ Vector store populated successfully")
            else:
                print("❌ Failed to populate vector store")
                sys.exit(1)
        else:
            print("\nTo auto-populate, run:")
            print("  python -m src.utils.rag.auto_populate --auto-populate")
