# Quick Reference Guide

This document provides quick reference information for the AI Agent system, including configuration, APIs, registries, and troubleshooting.

## Key Registries

The system uses several JSON registries to manage behavior:

| Registry | Location | Purpose |
|----------|----------|---------|
| **Domain Registry** | `artifacts/domain_registry.json` | Maps business terms to database schema |
| **Display Attributes** | `artifacts/display_attributes_registry.json` | Defines display columns and labels for tables |
| **Join Graph** | `artifacts/join_graph_merged.json` | Table relationships and join paths |
| **Secure Views** | `src/utils/sql/secure_views.py` | Encrypted table mappings |

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `127.0.0.1` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PWD` | - | MySQL password |
| `DB_NAME` | `crewos` | Database name |
| `DB_ENCRYPT_KEY` | - | Encryption key for secure views |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model |
| `OPENAI_TEMPERATURE` | `0.1` | Generation temperature |
| `MAX_OUTPUT_TOKENS` | `4000` | Max tokens in response |
| `MAX_QUERY_ROWS` | `100` | Max rows from SQL queries |
| `SQL_AGENT_MAX_ITERATIONS` | `15` | Max SQL agent reasoning steps |
| `SQL_SAMPLE_ROWS` | `1` | Sample rows per table in schema |

### Model Limits

| Model | Context Window | Max Output | Input Cost | Output Cost |
|-------|---------------|------------|------------|-------------|
| `gpt-4o-mini` | 128K | 16K | $0.150/1M | $0.600/1M |
| `gpt-4o` | 128K | 16K | $2.50/1M | $10.00/1M |

## Domain Registry Reference

### Overview

The domain registry maps business terminology to database schema locations.

**Location**: `artifacts/domain_registry.json`

### Structure

```json
{
  "version": 1,
  "description": "Domain vocabulary registry",
  "terms": {
    "crane": {
      "entity": "asset",
      "description": "Heavy lifting equipment",
      "resolution": {
        "primary": {
          "table": "asset",
          "columns": ["name", "manufacturer", "modelNumber"],
          "match_type": "text_search",
          "confidence": 0.95
        },
        "secondary": {
          "table": "assetType",
          "column": "name",
          "match_type": "text_search",
          "confidence": 0.5
        }
      }
    }
  }
}
```

### Match Types

| Type | Description | Example |
|------|-------------|---------|
| `text_search` | Case-insensitive LIKE search | `LOWER(asset.name) LIKE '%crane%'` |
| `boolean` | Boolean column match | `isActionItem = true` |
| `structural` | Table grouping without filters | Groups parent-child tables |
| `exact` | Exact value match | Status codes, enum values |

### Resolution Strategies

| Strategy | Priority | Use Case |
|----------|----------|----------|
| `primary` | Highest (0.95) | Direct table/column mapping |
| `secondary` | Medium (0.5) | Alternative locations |
| `fallback` | Lowest (0.3) | Generic search |

## Display Attributes Reference

### Overview

Defines human-readable display columns and primary labels for tables.

**Location**: `artifacts/display_attributes_registry.json`

### Structure

```json
{
  "version": 1,
  "description": "Display attributes for tables",
  "tables": {
    "asset": {
      "display_columns": ["id", "name", "modelNumber", "serialNumber"],
      "primary_label": ["name"]
    },
    "employee": {
      "display_columns": ["id", "firstName", "lastName", "email"],
      "primary_label": ["firstName", "lastName"]
    }
  }
}
```

### Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `display_columns` | Columns to show in results | `["id", "name", "modelNumber"]` |
| `primary_label` | Human-readable identifier | `["firstName", "lastName"]` |

### Usage

Used by SQL agent to:
- Select relevant columns in `SELECT` statements
- Format results with human-readable labels
- Reduce unnecessary columns in queries
- Improve response clarity

## Secure Views Reference

### Current Secure Views

```python
SECURE_VIEW_MAP = {
    "user": "secure_user",
    "employee": "secure_employee",
    "workOrder": "secure_workorder",
    "customer": "secure_customer",
    "customerLocation": "secure_customerlocation",
    "customerContact": "secure_customercontact",
}
```

**Location**: `src/utils/sql/secure_views.py`

### Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `is_secure_table(table)` | Check if table needs secure view | `is_secure_table("employee")` → `True` |
| `to_secure_view(table)` | Convert to secure view | `to_secure_view("employee")` → `"secure_employee"` |
| `rewrite_secure_tables(sql)` | Rewrite SQL query | `rewrite_secure_tables("SELECT * FROM employee")` → `"SELECT * FROM secure_employee"` |
| `validate_tables_exist(sql, tables)` | Validate tables exist | Raises `ValueError` if invalid |

## Join Graph Reference

### File Locations

| File | Purpose | Generated By |
|------|---------|--------------|
| `artifacts/join_graph_raw.json` | DB introspection results | `scripts/build_join_graph.py` |
| `artifacts/join_graph_manual.json` | Manual relationship overrides | Manual curation |
| `artifacts/associations.json` | Node.js model associations | External script |
| `artifacts/join_graph_merged.json` | Merged from all sources | `scripts/merge_join_graph.py` |
| `artifacts/join_graph_validated.json` | LLM-validated graph | `scripts/validate_join_graph_llm.py` |
| `artifacts/join_graph_paths.json` | Path finder index | `scripts/build_join_graph_paths.py` |
| `artifacts/domain_registry.json` | Business term to schema mappings | Manual curation |
| `artifacts/display_attributes_registry.json` | Display column specifications | Manual curation |

### Graph Structure

```json
{
  "version": 1,
  "tables": {
    "table_name": {
      "columns": ["col1", "col2", ...],
      "unique_columns": ["id"]
    }
  },
  "relationships": [
    {
      "from_table": "table1",
      "from_column": "col1",
      "to_table": "table2",
      "to_column": "id",
      "type": "foreign_key",
      "confidence": 1.0,
      "cardinality": "N:1"
    }
  ]
}
```

### Relationship Types

| Type | Confidence | Source |
|------|------------|--------|
| `foreign_key` | 1.0 | Database FK constraint |
| `business` | 0.7-0.9 | Node.js associations |
| `manual` | 0.8-1.0 | Manual overrides |
| `heuristic` | 0.5-0.7 | Naming convention inference |

## Path Finder Reference

### Usage

```python
from src.sql.graph.path_finder import JoinPathFinder

# Initialize
path_finder = JoinPathFinder(relationships, confidence_threshold=0.7)

# Find shortest path
path = path_finder.find_shortest_path("employee", "customer", max_hops=4)

# Expand relationships
expanded = path_finder.expand_relationships(
    tables=["employee", "workOrder"],
    direct_relationships=direct_rels,
    max_hops=4
)
```

### Performance

- **Time Complexity**: O((V + E) log V)
- **Space Complexity**: O(V + E)
- **Typical Performance**: < 100ms per path
- **Caching**: Automatic (in-memory)

## API Reference

### Endpoints

#### Health Check

```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "fsia-api",
  "version": "1.0.0"
}
```

#### Chat Stream

```
POST /internal/chat/stream
```

**Request**:
```json
{
  "input": {
    "message": "How many technicians are active?"
  },
  "conversation": {
    "id": "conv-uuid",
    "user_id": "user-id",
    "company_id": "company-id"
  }
}
```

**Response** (SSE):
```
data: {"event":"route_decision","route":"sql"}

data: {"event":"tool_start","tool":"sql_agent"}

data: {"event":"token","channel":"final","content":"There"}

data: {"event":"complete","stats":{"tokens":15}}
```

### Event Types

| Event | Fields | Description |
|-------|--------|-------------|
| `route_decision` | `route` | SQL, RAG, or GENERAL routing decision |
| `tool_start` | `tool` | Tool execution started |
| `token` | `channel`, `content` | Content token |
| `complete` | `stats` | Stream finished |
| `error` | `error` | Error occurred |

## SQL Agent Reference

### Workflow Steps

1. **Table Selector**: Selects 3-8 relevant tables
2. **Filter Relationships**: Finds direct relationships
3. **Path Finder**: Discovers transitive paths
4. **Join Planner**: Plans optimal join path
5. **SQL Generator**: Generates SQL query
6. **Secure Rewriter**: Rewrites secure tables
7. **Validator**: Validates tables exist
8. **Executor**: Executes query

### State Schema

```python
class SQLGraphState(TypedDict):
    question: str
    tables: List[str]
    allowed_relationships: List[Dict]
    join_plan: str
    sql: str
    result: Optional[str]
    retries: int
    final_answer: Optional[str]
```

## RAG Agent Reference

### Collections

| Collection | Purpose | Documents |
|-----------|---------|-----------|
| `company_handbook` | Company policies | ~100 chunks |
| `compliance_documents` | OSHA, FLSA, state | ~50 chunks |
| `all_documents` | Combined collection | ~150 chunks |

### Search Parameters

```python
# Vector search
results = vector_store.search(
    query="overtime rules",
    k=5,  # Top 5 results
    metadata_filter={"source": "company_handbook"}
)

# Hybrid search
results = vector_store.hybrid_search(
    query="overtime rules",
    k=10,
    keyword_boost=0.3  # 30% keyword, 70% vector
)
```

## Troubleshooting Quick Reference

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Table 'secure_xyz' doesn't exist` | Hallucinated table | Check `SECURE_VIEW_MAP`, rebuild join graph |
| `context_length_exceeded` | Too many tokens | Reduce `sql_sample_rows`, limit tables |
| `No path found` | Tables not connected | Check relationships, increase `max_hops` |
| `Views return NULL` | Missing encryption key | Set `DB_ENCRYPT_KEY` in `.env` |
| `CORS error` | Origin not allowed | Update CORS in `src/api/app.py` |

### Debug Commands

```bash
# Check join graph stats
python -c "import json; g=json.load(open('artifacts/join_graph_merged.json')); print(f'Tables: {len(g[\"tables\"])}, Relationships: {len(g[\"relationships\"])}')"

# Test secure views
python scripts/test_secure_views.py

# Test path finder
python -c "from src.sql.graph.path_finder import JoinPathFinder; ..."

# Check MySQL connection
python -c "from src.infra.database import get_database; db = get_database(); print('Connected')"

# Test API
curl http://localhost:8000/health
```

## File Structure Reference

```
api-ai-agent/
├── src/
│   ├── agents/
│   │   ├── orchestrator/
│   │   │   ├── agent.py             # Main orchestrator
│   │   │   ├── context.py           # Context management
│   │   │   ├── formatter.py         # Response formatting
│   │   │   ├── nodes/               # Orchestrator workflow nodes
│   │   │   │   ├── classify.py      # Question classification
│   │   │   │   ├── finalize.py      # Response finalization
│   │   │   │   ├── general_agent.py # General agent node
│   │   │   │   ├── rag_agent.py     # RAG agent node
│   │   │   │   └── sql_agent.py     # SQL agent node
│   │   │   ├── routing.py           # Routing logic
│   │   │   └── state.py             # State definitions
│   │   ├── sql/
│   │   │   ├── agent.py             # SQL agent implementation
│   │   │   ├── context.py           # SQL context management
│   │   │   ├── nodes/               # SQL workflow nodes
│   │   │   │   ├── correction.py    # SQL error correction
│   │   │   │   ├── domain.py        # Domain extraction
│   │   │   │   ├── executor.py      # SQL execution
│   │   │   │   ├── finalize.py      # Result finalization
│   │   │   │   ├── followup.py      # Followup suggestions
│   │   │   │   ├── join_planner.py  # Join planning
│   │   │   │   ├── sql_generator.py # SQL generation
│   │   │   │   ├── table_selector.py # Table selection
│   │   │   │   └── validator.py     # Pre-validation
│   │   │   ├── planning/            # SQL planning utilities
│   │   │   │   ├── bridge_tables.py # Bridge table detection
│   │   │   │   ├── domain_filters.py # Domain filter building
│   │   │   │   └── join_utils.py    # Join utilities
│   │   │   ├── prompt_helpers.py    # Prompt formatting
│   │   │   ├── state.py             # SQL state definitions
│   │   │   ├── utils.py             # SQL utilities
│   │   │   └── workflow.py          # SQL workflow definition
│   │   ├── rag/
│   │   │   ├── agent.py             # RAG agent implementation
│   │   │   └── prompts.py           # RAG prompts
│   │   └── general/
│   │       └── agent.py             # General agent implementation
│   ├── api/
│   │   ├── app.py                   # FastAPI application
│   │   ├── routes/
│   │   │   └── chat.py              # Chat endpoints
│   │   └── schemas/
│   │       ├── chat.py              # Chat schemas
│   │       └── conversation.py      # Conversation schemas
│   ├── config/
│   │   ├── constants.py             # Application constants
│   │   └── settings.py              # Configuration settings
│   ├── domain/
│   │   ├── display_attributes/      # Display attributes logic
│   │   └── ontology/                # Domain ontology logic
│   │       ├── extractor.py         # Term extraction
│   │       ├── formatter.py         # Context formatting
│   │       ├── models.py            # Domain models
│   │       └── resolver.py          # Term resolution
│   ├── infra/
│   │   ├── database.py              # Database infrastructure
│   │   └── vector_store.py          # Vector store infrastructure
│   ├── llm/
│   │   ├── client.py                # LLM client
│   │   └── embeddings.py            # Embedding service
│   ├── memory/
│   │   ├── conversation_store.py    # Conversation storage
│   │   └── query_memory.py          # Query memory
│   ├── models/
│   │   ├── conversation_db.py       # Conversation database
│   │   ├── database.py              # Database models
│   │   └── domain.py                # Domain models
│   ├── sql/
│   │   ├── execution/
│   │   │   ├── executor.py          # SQL executor
│   │   │   └── secure_rewriter.py   # Secure view rewriter
│   │   └── graph/
│   │       ├── join_graph.py        # Join graph loader
│   │       └── path_finder.py       # Path finder (Dijkstra)
│   ├── tools/
│   │   └── sql_tool.py              # SQL tool wrapper
│   └── utils/
│       ├── errors.py                # Error definitions
│       ├── logger.py                # Logger utilities
│       ├── logging.py               # Logging configuration
│       ├── rag/
│       │   ├── auto_populate.py     # Auto-populate RAG
│       │   ├── chunking_strategies.py # Chunking strategies
│       │   ├── chunking.py          # Chunking logic
│       │   ├── embedding_service.py # Embedding service
│       │   └── vector_store.py      # Vector store
│       └── sql/
│           └── secure_views.py      # Secure views utilities
├── scripts/
│   ├── build_join_graph.py          # Build raw graph from DB
│   ├── merge_join_graph.py          # Merge all graph sources
│   ├── validate_join_graph_llm.py   # LLM validation
│   ├── build_join_graph_paths.py    # Build path index
│   ├── check_vector_store.py        # Check vector store
│   ├── populate_vector_store.py     # Populate vector store
│   ├── test_classification.py       # Test classification
│   ├── test_secure_views.py         # Test secure views
│   ├── run-dev.py                   # Run development server
│   └── run-prod.py                  # Run production server
├── artifacts/
│   ├── join_graph_raw.json          # Raw graph from DB
│   ├── join_graph_merged.json       # Merged graph
│   ├── join_graph_validated.json    # LLM-validated graph
│   ├── join_graph_paths.json        # Path finder index
│   ├── join_graph_manual.json       # Manual relationship overrides
│   ├── associations.json            # Node.js associations
│   ├── domain_registry.json         # Domain term mappings
│   └── display_attributes_registry.json # Display attributes config
├── data/
│   ├── conversations.db             # SQLite conversation storage
│   └── embeddings_cache/            # Embedding cache
└── tests/
    ├── test_classification.py       # Classification tests
    ├── test_domain_ontology.py      # Domain ontology tests
    ├── test_display_attributes.py   # Display attributes tests
    └── test_internal_api.py         # API integration tests
```

## Command Reference

### Build Commands

```bash
# Build join graph from database
python scripts/build_join_graph.py

# Merge graphs (raw + manual + associations)
python scripts/merge_join_graph.py

# Validate graph with LLM
python scripts/validate_join_graph_llm.py

# Build path index for efficient lookups
python scripts/build_join_graph_paths.py

# Full pipeline (run all in sequence)
python scripts/build_join_graph.py && \
python scripts/merge_join_graph.py && \
python scripts/validate_join_graph_llm.py && \
python scripts/build_join_graph_paths.py
```

### Run Commands

```bash
# Start API server (development)
python scripts/run-dev.py

# Start API server (production)
python scripts/run-prod.py

# Test classification
python scripts/test_classification.py

# Test secure views
python scripts/test_secure_views.py

# Populate vector store
python scripts/populate_vector_store.py

# Check vector store
python scripts/check_vector_store.py
```

### Test Commands

```bash
# API health check
curl http://localhost:8000/health

# Streaming chat
curl -N -X POST http://localhost:8000/internal/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"input":{"message":"test"},"conversation":{"id":"test"}}'

# Python test
python test_internal_api.py
```

## Cost Estimation

### Per Query Cost (gpt-4o-mini)

| Component | Tokens | Cost |
|-----------|--------|------|
| Classification | ~500 | $0.00008 |
| SQL Generation | ~2,000 | $0.00030 |
| Query Execution | - | - |
| Final Answer | ~500 | $0.00030 |
| **Total** | **~3,000** | **~$0.00068** |

### Monthly Cost (100 queries/day)

- **Input**: 100 × 3,000 × 30 / 1M × $0.150 = **$1.35**
- **Output**: 100 × 500 × 30 / 1M × $0.600 = **$0.90**
- **Total**: **~$2.25/month**

## Performance Benchmarks

### SQL Agent

| Operation | Time | Notes |
|-----------|------|-------|
| Table Selection | 1-2s | LLM call |
| Path Finding | <100ms | Dijkstra |
| SQL Generation | 1-2s | LLM call |
| Query Execution | 0.5-5s | DB dependent |
| **Total** | **3-10s** | End-to-end |

### RAG Agent

| Operation | Time | Notes |
|-----------|------|-------|
| Query Embedding | <100ms | Cached: <1ms |
| Vector Search | 10-50ms | ChromaDB |
| LLM Generation | 1-3s | Context dependent |
| **Total** | **1-4s** | End-to-end |

## MySQL Session Variables

| Variable | Purpose | Set By |
|----------|---------|--------|
| `@aesKey` | Encryption key | `DB_ENCRYPT_KEY` env var |
| `@customerIds` | Customer filter | Future: User context |
| `@workOrderIds` | Work order filter | Future: Request context |
| `@serviceLocationIds` | Location filter | Future: Permissions |

**Set automatically** on connection via SQLAlchemy event listener.

## Logging Reference

### Log Levels

- `DEBUG`: Detailed debugging info
- `INFO`: General information
- `WARNING`: Warnings
- `ERROR`: Errors
- `SUCCESS`: Success messages (loguru)

### Trace Format

```
[TRACE] step_start: select_tables | trace_id=uuid | input_keys=[...]
[TRACE] step_end: select_tables | trace_id=uuid | duration_ms=1234 | output_keys=[...]
[TRACE] step_error: select_tables | trace_id=uuid | error=... | state_keys=[...]
```

## Quick Fixes

### Fix: Context Length Exceeded

```python
# Reduce schema size
SQL_SAMPLE_ROWS=1  # Was 3
SQL_MAX_TABLES_IN_CONTEXT=20  # Was 122
```

### Fix: Slow Queries

```python
# Add LIMIT to all queries
MAX_QUERY_ROWS=100

# Reduce table selection
# In sql_graph_agent.py, limit to 3-5 tables
```

### Fix: Missing Secure Views

```python
# Add to SECURE_VIEW_MAP
SECURE_VIEW_MAP["newtable"] = "secure_newtable"

# Rebuild join graph
python scripts/build_join_graph.py
```

### Fix: Path Finder Not Working

```python
# Check confidence threshold
confidence_threshold=0.70  # Lower if needed

# Increase max hops
max_hops=4  # Increase to 5-6 if needed
```
