"""Check if OSHA chunks are in all_documents collection"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from services.vector_store import VectorStore
from services.embedding_service import EmbeddingService

vs = VectorStore(embedding_service=EmbeddingService())

# Check all_documents collection
all_coll = vs.client.get_collection('all_documents')
all_docs = all_coll.get()

print(f"\n{'='*80}")
print(f"ALL_DOCUMENTS COLLECTION: {len(all_docs['documents'])} chunks total")
print(f"{'='*80}\n")

# Count by source
sources = {}
for meta in all_docs['metadatas']:
    source = meta.get('source', 'unknown')
    sources[source] = sources.get(source, 0) + 1

print("Chunks by source:")
for source, count in sorted(sources.items()):
    print(f"  {source}: {count} chunks")

# Look for OSHA employee rights
print(f"\n{'='*80}")
print("SEARCHING FOR 'EMPLOYEE RIGHTS' IN ALL_DOCUMENTS")
print(f"{'='*80}\n")

employee_rights = [
    (i, doc, meta) for i, (doc, meta) in enumerate(zip(all_docs['documents'], all_docs['metadatas']))
    if 'employee rights' in doc.lower() or 'request an osha inspection' in doc.lower()
]

print(f"Found {len(employee_rights)} chunks with employee rights content\n")

for i, doc, meta in employee_rights[:3]:
    print(f"Chunk index: {i}")
    print(f"Source: {meta.get('source')}")
    print(f"Length: {len(doc)} chars")
    print(f"Preview: {doc[:300]}...")
    print()
