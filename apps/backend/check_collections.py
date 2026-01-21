"""Check what's in the vector store collections"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from services.vector_store import VectorStore
from services.embedding_service import EmbeddingService

vs = VectorStore(embedding_service=EmbeddingService())

# Check compliance documents
coll = vs.client.get_collection('compliance_documents')
docs = coll.get(limit=20)

print(f"\n{'='*80}")
print(f"COMPLIANCE DOCUMENTS COLLECTION: {len(docs['documents'])} chunks")
print(f"{'='*80}\n")

for i, (doc, meta) in enumerate(zip(docs['documents'][:10], docs['metadatas'][:10]), 1):
    print(f"{i}. Source: {meta.get('source', 'unknown')} | Type: {meta.get('doc_type', 'unknown')}")
    print(f"   Text preview: {doc[:100]}...")
    print()

# Check for OSHA specifically
print(f"\n{'='*80}")
print("SEARCHING FOR OSHA IN COMPLIANCE DOCS")
print(f"{'='*80}\n")

osha_chunks = [
    (i, doc, meta) for i, (doc, meta) in enumerate(zip(docs['documents'], docs['metadatas']))
    if 'osha' in meta.get('source', '').lower() or 'osha' in doc.lower()[:200]
]

print(f"Found {len(osha_chunks)} chunks with 'OSHA' content")
for i, doc, meta in osha_chunks[:3]:
    print(f"\nChunk {i}:")
    print(f"Source: {meta.get('source')}")
    print(f"Preview: {doc[:200]}...")
