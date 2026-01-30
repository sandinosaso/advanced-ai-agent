#!/bin/bash

# Fix Empty RAG Collection
# This script populates the vector store with user manual documents

set -e  # Exit on error

echo "======================================================================"
echo "Fix: Empty RAG Collection"
echo "======================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "📂 Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Check if manual documents exist
echo ""
echo "1️⃣  Checking for manual documents..."
MANUAL_DIR="$PROJECT_ROOT/data/manual"

if [ ! -d "$MANUAL_DIR" ]; then
    echo "❌ Manual directory not found: $MANUAL_DIR"
    exit 1
fi

MD_COUNT=$(find "$MANUAL_DIR" -name "*.md" | wc -l | tr -d ' ')
echo "✅ Found $MD_COUNT markdown files in data/manual/"
ls -1 "$MANUAL_DIR"/*.md 2>/dev/null || echo "No .md files found"

# Run populate script
echo ""
echo "2️⃣  Populating vector store..."
echo "   This will:"
echo "   - Reset the empty collection"
echo "   - Load all manual documents"
echo "   - Generate embeddings"
echo "   - Store in ChromaDB"
echo ""

python scripts/populate_vector_store.py --reset

echo ""
echo "======================================================================"
echo "✅ Vector store has been populated!"
echo "======================================================================"
echo ""
echo "📝 Next steps:"
echo "   1. Restart your API server (if it's running)"
echo "   2. Try asking: 'How do I create a work order?'"
echo "   3. The RAG agent should now return information from the manual"
echo ""
echo "======================================================================"
