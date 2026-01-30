# Vector Store Quick Reference

## ❓ Do I need to repopulate on every server restart?

**NO!** ✅ The vector store is **persistent** (stored in SQLite on disk).

## 📦 What's Stored

```
data/vector_store/chroma.sqlite3  ← All embeddings, documents, metadata
data/embeddings_cache/*.json      ← Cached embeddings (saves API costs)
```

## 🚀 When to Populate

| Situation | Need to Populate? |
|-----------|------------------|
| First time setup | ✅ Yes |
| Server restart | ❌ No (persists) |
| Document updates | ✅ Yes |
| Corruption error | ✅ Yes (with reset) |

## 📋 Commands

```bash
# First setup or after doc changes
python scripts/populate_vector_store.py

# Clean slate (fixes corruption)
python scripts/populate_vector_store.py --reset

# Quick fix (automated)
./scripts/reset_and_populate_rag.sh

# Check status
python -m src.utils.rag.auto_populate
```

## 🔍 Auto-Check on Startup

The server now automatically checks on startup:

### ✅ Healthy
```
✅ Vector store ready: 289 total documents across 2 collections
```

### ⚠️ Empty
```
⚠️  Vector store is EMPTY!
   Run: python scripts/populate_vector_store.py
```

### ❌ Error
```
⚠️  Failed to check vector store: [error]
   RAG agent may not function correctly
```

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| RAG returns "no information" | Populate: `python scripts/populate_vector_store.py` |
| "Collection UUID does not exist" | Reset: `./scripts/reset_and_populate_rag.sh` |
| Slow embeddings | Check cache hits in logs |
| Outdated responses | Repopulate: `python scripts/populate_vector_store.py --reset` |

## 📚 More Info

See: `docs/VECTOR_STORE_PERSISTENCE.md`
