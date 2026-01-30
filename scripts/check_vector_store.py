"""
Quick diagnostic script to check vector store state
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings

def check_vector_store():
    """Check the state of the vector store"""
    
    # Path to vector store
    vector_store_path = project_root / "data" / "vector_store"
    
    print("="*60)
    print("Vector Store Diagnostic")
    print("="*60)
    print(f"\nVector store location: {vector_store_path}")
    print(f"Exists: {vector_store_path.exists()}")
    
    if not vector_store_path.exists():
        print("\n❌ Vector store directory does not exist!")
        print("   Run: python scripts/populate_vector_store.py")
        return
    
    # Connect to ChromaDB
    try:
        client = chromadb.PersistentClient(
            path=str(vector_store_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        
        # List all collections
        collections = client.list_collections()
        
        print(f"\n📊 Collections found: {len(collections)}")
        
        if not collections:
            print("\n❌ No collections found in vector store!")
            print("   This means the vector store has not been populated.")
            print("   Run: python scripts/populate_vector_store.py")
        else:
            print("\nCollection details:")
            total_docs = 0
            for coll in collections:
                count = coll.count()
                total_docs += count
                status = "✅" if count > 0 else "⚠️"
                print(f"  {status} {coll.name}: {count} documents")
            
            print(f"\n📈 Total documents across all collections: {total_docs}")
            
            if total_docs == 0:
                print("\n⚠️  Collections exist but are EMPTY!")
                print("   Run: python scripts/populate_vector_store.py --reset")
        
        # Check manual directory
        manual_dir = project_root / "data" / "manual"
        print(f"\n📁 Manual directory: {manual_dir}")
        print(f"   Exists: {manual_dir.exists()}")
        
        if manual_dir.exists():
            md_files = list(manual_dir.glob("*.md"))
            print(f"   Markdown files: {len(md_files)}")
            for md_file in md_files:
                size_kb = md_file.stat().st_size / 1024
                print(f"     - {md_file.name} ({size_kb:.1f} KB)")
        else:
            print("   ❌ Manual directory not found!")
        
    except Exception as e:
        print(f"\n❌ Error checking vector store: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("\n💡 To populate the vector store:")
    print("   cd /Users/sandinosaso/repos/crewos/api-ai-agent")
    print("   python scripts/populate_vector_store.py --reset")
    print("="*60 + "\n")

if __name__ == "__main__":
    check_vector_store()
