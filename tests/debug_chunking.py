"""Debug chunking of OSHA document"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from services.mock_documents import FEDERAL_COMPLIANCE_OSHA
from utils.chunking_strategies import DocumentStructureChunking, RecursiveChunking, chunk_document

# Try document structure chunking
print("="*80)
print("TESTING DOCUMENT STRUCTURE CHUNKING")
print("="*80)

strategy = DocumentStructureChunking(chunk_size=1000, chunk_overlap=100)
chunks = chunk_document(
    document_text=FEDERAL_COMPLIANCE_OSHA,
    document_type="compliance",
    strategy=strategy
)

print(f"\nTotal chunks created: {len(chunks)}")
print(f"OSHA document length: {len(FEDERAL_COMPLIANCE_OSHA):,} characters")

# Find chunks containing "Employee Rights"
employee_rights_chunks = [
    (i, chunk) for i, chunk in enumerate(chunks)
    if 'employee rights' in chunk.text.lower() or 'request an osha inspection' in chunk.text.lower()
]

print(f"\n{'='*80}")
print(f"CHUNKS CONTAINING 'EMPLOYEE RIGHTS' OR 'REQUEST AN OSHA INSPECTION': {len(employee_rights_chunks)}")
print(f"{'='*80}\n")

for i, chunk in employee_rights_chunks:
    print(f"\n--- CHUNK {i} ---")
    print(f"Length: {len(chunk.text)} chars")
    print(f"Section: {chunk.metadata.get('section_title', 'N/A')}")
    print(f"Text:\n{chunk.text}\n")

if not employee_rights_chunks:
    print("NO CHUNKS FOUND WITH EMPLOYEE RIGHTS CONTENT!")
    print("\nShowing first 5 chunks instead:")
    for i, chunk in enumerate(chunks[:5]):
        print(f"\n--- CHUNK {i} ---")
        print(f"Length: {len(chunk.text)} chars")
        print(f"Section: {chunk.metadata.get('section_title', 'N/A')}")
        print(f"Preview: {chunk.text[:200]}...")

# Also test with recursive chunking
print(f"\n\n{'='*80}")
print("TESTING RECURSIVE CHUNKING")
print(f"{'='*80}")

strategy2 = RecursiveChunking(chunk_size=1000, chunk_overlap=100)
chunks2 = chunk_document(
    document_text=FEDERAL_COMPLIANCE_OSHA,
    document_type="compliance",
    strategy=strategy2
)

print(f"\nTotal chunks created: {len(chunks2)}")

employee_rights_chunks2 = [
    (i, chunk) for i, chunk in enumerate(chunks2)
    if 'employee rights' in chunk.text.lower() or 'request an osha inspection' in chunk.text.lower()
]

print(f"Chunks with employee rights: {len(employee_rights_chunks2)}")

if employee_rights_chunks2:
    print("\nFirst matching chunk:")
    i, chunk = employee_rights_chunks2[0]
    print(f"Length: {len(chunk.text)} chars")
    print(f"Text:\n{chunk.text}\n")
