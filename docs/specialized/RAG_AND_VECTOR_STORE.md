# RAG Agent & Vector Store

## Overview

The RAG agent uses ChromaDB with persistent storage. Embeddings and documents are stored on disk and persist between server restarts. No repopulation is needed on restart.

---

## Do I Need to Repopulate?

| Situation | Need to Populate? |
|-----------|-------------------|
| First time setup | Yes |
| Server restart | No (persists) |
| Document updates | Yes |
| Corruption error | Yes (with `--reset`) |

---

## Storage Location

Paths are resolved from the `api-ai-agent` project root (`PROJECT_ROOT` in `src/config/settings.py`):

```
api-ai-agent/
├── data/
│   ├── vector_store/           # ChromaDB (embeddings, documents)
│   │   └── chroma.sqlite3
│   ├── embeddings_cache/       # Cached embeddings (saves API costs)
│   └── manual/                 # Source .md files
```

---

## Commands

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

---

## Auto-Check on Startup

The server checks vector store status on startup:

### Healthy
```
✅ Vector store ready: 289 total documents across 2 collections
```

### Empty
```
⚠️  Vector store is EMPTY!
   RAG queries will not work until vector store is populated.
   Run: python scripts/populate_vector_store.py
```

### Error
```
⚠️  Failed to check vector store: [error message]
```

---

## When to Populate

1. **First setup** – Vector store doesn't exist yet
2. **Manual documents change** – You updated `.md` files in `data/manual/`
3. **Corruption** – ChromaDB database is corrupted (rare)
4. **Clean slate** – You want to completely reset

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| RAG returns "no information" | Populate: `python scripts/populate_vector_store.py` |
| "Collection UUID does not exist" | Reset: `./scripts/reset_and_populate_rag.sh` |
| Slow embeddings | Check cache hits in logs |
| Outdated responses | Repopulate: `python scripts/populate_vector_store.py --reset` |

---

## Deployment

1. **Initial setup**: Run populate script once
2. **Document updates**: Re-run populate when docs change
3. **Backups**: Backup `data/vector_store/` directory
4. **Docker**: Mount `data/vector_store` and `data/embeddings_cache` as volumes

---

## Related Files

- `src/infra/vector_store.py` – ChromaDB setup
- `src/utils/rag/` – Vector store, embeddings, auto_populate
- `scripts/populate_vector_store.py`
- `scripts/reset_and_populate_rag.sh`
