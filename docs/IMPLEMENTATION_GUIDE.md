# Implementation Guide

## Quick Start

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Node.js 20+ (for BFF layer)
- OpenAI API key (or Ollama for local)

### Installation

```bash
# Navigate to api-ai-agent project root
cd api-ai-agent

# Create venv and install dependencies with uv
uv venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows
uv sync --extra dev --extra api

# Or use the setup script
./scripts/setup.sh

# Configure environment
cp .env.example .env
# Edit .env with your credentials (OPENAI_API_KEY, DB_*, etc.)
```

### Environment Variables

Key variables (see `.env.example` for full list):

```bash
# Database
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PWD=your_password
DB_NAME=crewos
DB_ENCRYPT_KEY=your_encryption_key

# LLM (OpenAI or Ollama)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1

# Optional: Ollama for local operation
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
```

## Building the Join Graph

The join graph is essential for the SQL agent to understand table relationships.

### Step 1: Build Raw Graph

```bash
cd api-ai-agent
uv run python scripts/build_join_graph.py
```

**Output**: `artifacts/join_graph_raw.json`

**What it does**:
- Inspects MySQL schema using SQLAlchemy
- Extracts foreign keys
- Infers relationships from naming conventions
- Captures table schemas and columns

### Step 2: Merge Sources (Optional)

If you have Node.js associations or manual overrides:

```bash
uv run python scripts/merge_join_graph.py
```

**Inputs**:
- `artifacts/join_graph_raw.json` (from Step 1)
- `artifacts/associations.json` (from Node.js, optional)
- `artifacts/join_graph_manual.json` (manual, optional)

**Output**: `artifacts/join_graph_merged.json`

### Step 3: Validate (Recommended)

```bash
uv run python scripts/validate_join_graph_llm.py
```

**Output**: `artifacts/join_graph_validated.json`

**What it does**:
- Validates heuristic relationships
- Removes invalid connections
- Increases confidence scores

### Step 4: Build Path Index

```bash
uv run python scripts/build_join_graph_paths.py
```

**Output**: `artifacts/join_graph_paths.json`

**What it does**:
- Creates metadata index for path finder
- Validates path finder functionality
- Does NOT precompute all paths (efficient!)

## RAG & Vector Store

Before RAG queries work, populate the vector store:

```bash
# First setup or after document changes
uv run python scripts/populate_vector_store.py

# Clean slate (fixes corruption)
uv run python scripts/populate_vector_store.py --reset

# Quick fix
./scripts/reset_and_populate_rag.sh
```

Source documents live in `data/manual/`. The server checks vector store status on startup. See [RAG_AND_VECTOR_STORE.md](./specialized/RAG_AND_VECTOR_STORE.md) for details.

## Running the System

### Development Server

```bash
cd api-ai-agent
uv run python scripts/run-dev.py
```

Server starts at: `http://localhost:8000`

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Chat stream: `POST http://localhost:8000/internal/chat/stream`

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Streaming chat (internal API - used by BFF)
curl -N -X POST http://localhost:8000/internal/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"message": "How many technicians are active?"},
    "conversation": {
      "id": "test-123",
      "user_id": "user-456",
      "company_id": "company-789"
    }
  }'
```

### Production Server

```bash
uv run python scripts/run-prod.py
```

## Adding New Secure Views

When you add a new encrypted table that needs a secure view:

### Step 1: Create MySQL View

```sql
CREATE VIEW secure_newtable AS
SELECT 
    id,
    AES_DECRYPT(encryptedField, @aesKey) AS decryptedField,
    -- other fields
FROM newtable;
```

### Step 2: Configure base table list

The secure view mapping is discovered from the database at runtime. Add the base table name to the `SECURE_BASE_TABLES` environment variable in `.env` (comma-separated). The system matches base tables to views whose names start with `secure_` (e.g. `newtable` → `secure_newtable`).

**File**: `.env`

```bash
SECURE_BASE_TABLES=user,customer,employee,workOrder,newtable
```

**Implementation**: `src/utils/sql/secure_views.py` (uses `get_secure_view_map()` after `initialize_secure_view_map()` at startup).

### Step 3: Rebuild Join Graph

```bash
uv run python scripts/build_join_graph.py
```

### Step 4: Test

```bash
uv run python scripts/test_secure_views.py
```

## Configuring the SQL Agent

Settings are in `src/config/settings.py` and can be overridden via `.env`:

### Table Selection

- `sql_max_tables_in_selection_prompt` – Max tables shown to LLM (default: 250)
- `sql_max_fallback_tables` – Fallback when LLM fails (default: 5)

Table selection logic: `src/agents/sql/nodes/table_selector.py`

### Path Finding

- `sql_confidence_threshold` – Minimum confidence for relationships (default: 0.70)

Path finder: `src/sql/graph/path_finder.py`, used in `src/agents/sql/nodes/join_planner.py`

### SQL Generation & Correction

- `sql_correction_max_attempts` – Max retries on validation/execution failure (default: 3)
- `max_query_rows` – Max rows returned (default: 100)
- `sql_sample_rows` – Sample rows per table (default: 1)

### Domain Ontology

- `domain_extraction_enabled` – Enable LLM-based term extraction
- `domain_registry_path` – Path to `artifacts/domain_registry.json`

See [DOMAIN_ONTOLOGY.md](./specialized/DOMAIN_ONTOLOGY.md).

## Project Structure

```
api-ai-agent/
├── src/
│   ├── agents/
│   │   ├── orchestrator/     # Routes to SQL/RAG/General
│   │   ├── sql/              # SQL agent (modular nodes)
│   │   ├── rag/              # RAG agent
│   │   └── general/          # General Q&A agent
│   ├── api/                  # FastAPI app, routes
│   ├── config/               # settings.py, constants.py
│   ├── domain/ontology/      # Domain vocabulary
│   ├── sql/graph/            # Join graph, path finder
│   ├── sql/execution/        # SQL execution, secure rewriter
│   ├── memory/               # Query memory, conversation store
│   ├── llm/                  # LLM client, embeddings
│   └── infra/                # Database, vector store
├── scripts/                  # run-dev, run-prod, build_join_graph, etc.
├── tests/
├── artifacts/                # join_graph_*.json, domain_registry.json
└── data/                     # vector_store, manual/, conversations.db
```

## Extending the System

### Adding a New Agent

1. Create agent under `src/agents/<name>/` with `agent.py`, `state.py`, etc.
2. Add routing logic in `src/agents/orchestrator/nodes/classify.py`
3. Wire the agent in `src/agents/orchestrator/nodes/` routing and finalize logic

### Adding Domain Terms

Edit `artifacts/domain_registry.json` – no code changes needed. See [DOMAIN_ONTOLOGY.md](./specialized/DOMAIN_ONTOLOGY.md).

## Troubleshooting

### SQL Agent Issues

#### "Table doesn't exist" errors

1. Check join graph: `cat artifacts/join_graph_merged.json | grep "table_name"`
2. Rebuild join graph if missing
3. Check secure view mapping: ensure base table is in `SECURE_BASE_TABLES` (`.env`) and the `secure_*` view exists in MySQL; see `src/utils/sql/secure_views.py`.

#### Slow query performance

1. Reduce table selection (limit to 3–5 tables)
2. Add LIMIT clauses to queries
3. Check MySQL indexes on join columns
4. Reduce `sql_sample_rows` in settings

#### Context length exceeded

1. Reduce `sql_sample_rows` (default: 1)
2. Lower `sql_max_tables_in_context`
3. Reduce `max_query_rows`
4. Lower `sql_max_relationships_in_prompt`, `sql_max_suggested_paths`

### Path Finder Issues

#### Path finder not finding paths

1. Check `sql_confidence_threshold` (default 0.7)
2. Verify relationships in join graph
3. Inspect `src/sql/graph/path_finder.py` and `join_planner.py`

### Secure Views Issues

#### Views return NULL

1. Ensure `DB_ENCRYPT_KEY` is set in `.env`
2. Verify key matches database encryption key
3. Check MySQL: `SELECT @aesKey;`
4. Restart application

#### "secure_xyz doesn't exist"

1. Verify view in MySQL: `SHOW TABLES LIKE 'secure_%';`
2. Add the base table to `SECURE_BASE_TABLES` in `.env` (see `src/utils/sql/secure_views.py`; mapping is discovered from the DB at startup)
3. Rebuild join graph

### RAG Issues

#### RAG returns no information

1. Populate vector store: `uv run python scripts/populate_vector_store.py`
2. Check startup logs for vector store status

#### "Collection does not exist"

```bash
./scripts/reset_and_populate_rag.sh
```

### API Issues

#### Streaming not working

1. Use `curl -N` (no buffering)
2. Check SSE headers
3. Verify EventSource support in client

#### CORS errors

Update `src/api/app.py` CORS `allow_origins` for your frontend URL.

## Performance Optimization

### SQL Agent

1. **Reduce schema size**: `sql_sample_rows=1`, `sql_max_columns_in_schema=50`
2. **Limit tables**: `sql_max_tables_in_context`, `sql_max_relationships_in_prompt`
3. **Token limits**: `max_context_tokens`, `max_output_tokens`

### RAG Agent

1. Check embedding cache hits in logs
2. Reduce chunk size in `src/utils/rag/chunking_strategies.py`
3. Limit retrieved chunks in RAG agent

## Testing

### Unit Tests

```bash
./scripts/run_tests.sh
```

Excludes `test_internal_api.py` (requires running API). For full tests:

```bash
./scripts/run_tests.sh --all
```

### Test Secure Views

```bash
uv run python scripts/test_secure_views.py
```

### Test Classification

```bash
uv run python scripts/test_classification.py
```

## Deployment

### Production Checklist

- [ ] Set all environment variables
- [ ] Configure `DB_ENCRYPT_KEY` securely (use secrets manager)
- [ ] Rebuild join graph with validated relationships
- [ ] Test secure views with real encryption key
- [ ] Configure CORS for production domain
- [ ] Set up monitoring and logging
- [ ] Populate vector store if using RAG
- [ ] Test API endpoints

### GitLab CI

The project includes `.gitlab-ci.yml`:

- **Test stage**: Runs on MRs with `run-tests` label targeting `develop` or `main`
- **Deploy stage**: SSH deploy to prod on `main` (requires `SSH_PRIVATE_KEY` CI variable)

## Specialized Documentation

- [SQL Agent & Join Graph](./specialized/SQL_AGENT_AND_JOIN_GRAPH.md)
- [Secure Views & Database](./specialized/SECURE_VIEWS_AND_DATABASE.md)
- [Domain Ontology](./specialized/DOMAIN_ONTOLOGY.md)
- [RAG & Vector Store](./specialized/RAG_AND_VECTOR_STORE.md)
- [Follow-up Memory](./specialized/FOLLOWUP_QUESTIONS_MEMORY.md)
- [Integration & Reference](./specialized/INTEGRATION_AND_REFERENCE.md)
