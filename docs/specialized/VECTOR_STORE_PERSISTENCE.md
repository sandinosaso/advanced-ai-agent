# Vector Store Persistence & Auto-Population

## Overview

The RAG agent uses **ChromaDB with persistent storage** - all embeddings and documents are stored on disk and persist between server restarts.

## Storage Location

```
/Users/sandinosaso/repos/crewos/api-ai-agent/data/vector_store/
├── chroma.sqlite3          # Main database (collections, metadata, embeddings)
└── [internal ChromaDB files]
```

## Do You Need to Repopulate on Every Restart?

**No!** The vector store is **persistent**:

✅ Data survives server restarts
✅ Embeddings are cached
✅ No need to repopulate unless documents change

## When to Populate

You ONLY need to run `populate_vector_store.py` when:

1. **First setup** - Vector store doesn't exist yet
2. **Manual documents change** - You updated `.md` files in `data/manual/`
3. **Corruption** - ChromaDB database is corrupted (rare)
4. **Clean slate** - You want to completely reset

## Automatic Startup Check

The API server now automatically checks vector store status on startup:

### Healthy Startup
```
🚀 FastAPI application starting...
📊 Checking RAG vector store status...
✅ Vector store ready: 289 total documents across 2 collections
   - manual: 289 documents
   - all: 289 documents
```

### Empty Vector Store
```
🚀 FastAPI application starting...
📊 Checking RAG vector store status...
⚠️  Vector store is EMPTY!
   RAG queries will not work until vector store is populated.
   Run: python scripts/populate_vector_store.py
   Or: ./scripts/reset_and_populate_rag.sh
```

### Error
```
🚀 FastAPI application starting...
📊 Checking RAG vector store status...
⚠️  Failed to check vector store: [error message]
   RAG agent may not function correctly
```

## Automatic Population (Optional)

If you want the server to **automatically populate** an empty vector store on startup:

### Option 1: Modify startup script

Edit `scripts/run-dev.py`:

```python
from src.utils.rag.auto_populate import check_and_populate_if_needed

# Add before starting server
if settings.enable_rag_agent:
    check_and_populate_if_needed()
```

### Option 2: Pre-start script

Create a wrapper script:

```bash
#!/bin/bash
# scripts/start-with-rag-check.sh

cd /Users/sandinosaso/repos/crewos/api-ai-agent

# Check and populate if needed
python -m src.utils.rag.auto_populate --auto-populate

# Start server
python scripts/run-dev.py
```

## Manual Population Commands

### Standard Populate (Recommended)
```bash
python scripts/populate_vector_store.py
```

### Reset and Populate (Clean Slate)
```bash
python scripts/populate_vector_store.py --reset
```

### Quick Fix Script (Handles Corruption)
```bash
./scripts/reset_and_populate_rag.sh
```

## Checking Status

### Via API Startup Logs
Just start the server and check the logs:
```bash
python scripts/run-dev.py
# Look for: "✅ Vector store ready: XXX documents"
```

### Via Python Script
```bash
python -m src.utils.rag.auto_populate
```

Output:
```
Checking vector store status...
✅ Vector store ready with 289 documents
   - manual: 289 docs
   - all: 289 docs
```

### Via Python Console
```python
from src.utils.rag.vector_store import VectorStore

vs = VectorStore()
vs.print_stats()
```

## Persistence Details

### What's Stored
- **Embeddings**: Vector representations of text chunks (1536 dimensions for OpenAI)
- **Documents**: Original text chunks
- **Metadata**: Source file, section titles, chunk indices
- **Collections**: Separate namespaces (manual, all, etc.)

### Storage Format
- **Database**: SQLite (via ChromaDB)
- **Size**: ~2-5 MB for 300 documents
- **Location**: `data/vector_store/chroma.sqlite3`

### Caching
Embeddings are also cached separately:
```
data/embeddings_cache/
└── openai_text-embedding-3-small.json  # 295 cached embeddings
```

This cache prevents re-generating embeddings for unchanged text.

## Deployment Considerations

### Development
- ✅ Vector store persists locally
- ✅ Changes to `.md` files require repopulation
- ✅ Use `--reset` flag to start fresh

### Production
1. **Initial Setup**: Run populate script once
2. **Document Updates**: Re-run populate when docs change
3. **Backups**: Backup `data/vector_store/` directory
4. **Monitoring**: Check startup logs for empty warnings

### Docker
If using Docker, mount the vector store directory:
```yaml
volumes:
  - ./data/vector_store:/app/data/vector_store
  - ./data/embeddings_cache:/app/data/embeddings_cache
```

### CI/CD
Add populate step to deployment:
```bash
# In deployment script
python scripts/populate_vector_store.py
python scripts/run-prod.py
```

## Troubleshooting

### Server starts but RAG doesn't work
**Check:** Startup logs for empty warning
```bash
# If you see: "Vector store is EMPTY!"
python scripts/populate_vector_store.py
```

### "Collection does not exist" error
**Fix:** ChromaDB corruption
```bash
./scripts/reset_and_populate_rag.sh
```

### Embeddings taking too long
**Check:** Cache status
```bash
# Cache should show hits
INFO - Embedding 289 texts: 289 from cache, 0 from API
```

### Out of sync after document changes
**Fix:** Repopulate
```bash
python scripts/populate_vector_store.py --reset
```

## Best Practices

### 1. Version Control
- ✅ Commit manual documents (`data/manual/*.md`)
- ❌ Don't commit vector store (`data/vector_store/`)
- ✅ Commit embeddings cache (`data/embeddings_cache/`) - saves API costs

### 2. Development Workflow
```bash
# Initial setup
git clone repo
python scripts/populate_vector_store.py
python scripts/run-dev.py

# After updating docs
python scripts/populate_vector_store.py --reset
# Server auto-detects changes on restart
```

### 3. Production Workflow
```bash
# Deploy
git pull
python scripts/populate_vector_store.py  # Only if docs changed
python scripts/run-prod.py
```

### 4. Backup Strategy
```bash
# Before major changes
cp -r data/vector_store data/vector_store_backup

# Restore if needed
rm -rf data/vector_store
cp -r data/vector_store_backup data/vector_store
```

## Configuration

Control RAG behavior via `.env`:

```bash
# Enable/disable RAG agent
ENABLE_RAG_AGENT=true

# Embedding settings
EMBEDDING_PROVIDER=openai  # or ollama
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Cache settings
ENABLE_EMBEDDING_CACHE=true
```

## Summary

| Scenario | Action | Command |
|----------|--------|---------|
| First time setup | Populate once | `python scripts/populate_vector_store.py` |
| Server restart | Nothing needed | Data persists automatically |
| Docs updated | Repopulate | `python scripts/populate_vector_store.py --reset` |
| Corruption error | Clean reset | `./scripts/reset_and_populate_rag.sh` |
| Check status | View logs | Look for "Vector store ready" on startup |

**Key Takeaway**: The vector store is **persistent** and **does not need repopulation on every restart**. The server now automatically checks and warns you if it's empty!
