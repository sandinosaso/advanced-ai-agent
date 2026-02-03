#!/bin/bash

# Complete RAG Reset and Populate Script
# Fixes ChromaDB corruption and populates vector store in one go

set -e  # Exit on error

echo "======================================================================"
echo "Complete RAG Reset and Populate"
echo "======================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

VECTOR_STORE_DIR="$PROJECT_ROOT/data/vector_store"

echo "📂 Project root: $PROJECT_ROOT"
echo "📦 Vector store: $VECTOR_STORE_DIR"
echo ""

# Check if vector store exists
if [ -d "$VECTOR_STORE_DIR" ]; then
    echo "⚠️  Existing vector store found"
    echo "   This will completely delete and recreate it"
    echo ""
    read -p "   Continue? (yes/no): " response
    
    if [ "$response" != "yes" ]; then
        echo ""
        echo "❌ Cancelled"
        exit 0
    fi
    
    echo ""
    echo "1️⃣  Creating backup..."
    BACKUP_DIR="$PROJECT_ROOT/data/vector_store_backup_$(date +%Y%m%d_%H%M%S)"
    cp -r "$VECTOR_STORE_DIR" "$BACKUP_DIR"
    echo "   ✅ Backup created: $BACKUP_DIR"
    
    echo ""
    echo "2️⃣  Deleting corrupted vector store..."
    rm -rf "$VECTOR_STORE_DIR"
    echo "   ✅ Deleted"
    
    echo ""
    echo "3️⃣  Creating fresh directory..."
    mkdir -p "$VECTOR_STORE_DIR"
    echo "   ✅ Created"
else
    echo "✅ No existing vector store found"
    mkdir -p "$VECTOR_STORE_DIR"
fi

echo ""
echo "4️⃣  Populating vector store with manual documents..."
echo ""

# Run populate script (it will create fresh collections)
python scripts/populate_vector_store.py

echo ""
echo "======================================================================"
echo "✅ Complete! RAG is ready to use"
echo "======================================================================"
echo ""
echo "📝 Next steps:"
echo "   1. Restart your API server (Ctrl+C then restart)"
echo "   2. Try: 'How do I create a work order?'"
echo ""
echo "======================================================================"
