# Implementation Guide

## Quick Start

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Node.js 20+ (for BFF layer)
- OpenAI API key

### Installation

```bash
# Install Python dependencies
cd apps/backend
uv venv
source .venv/bin/activate
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

```bash
# Database
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PWD=your_password
DB_NAME=crewos
DB_ENCRYPT_KEY=your_encryption_key

# OpenAI
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1
```

## Building the Join Graph

The join graph is essential for the SQL agent to understand table relationships.

### Step 1: Build Raw Graph

```bash
cd apps/backend
python scripts/build_join_graph.py
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
# Merge all sources
python scripts/merge_join_graph.py
```

**Inputs**:
- `artifacts/join_graph_raw.json` (from Step 1)
- `artifacts/associations.json` (from Node.js, optional)
- `artifacts/join_graph_manual.json` (manual, optional)

**Output**: `artifacts/join_graph_merged.json`

### Step 3: Validate (Recommended)

```bash
# LLM validation of relationships
python scripts/validate_join_graph_llm.py
```

**Output**: `artifacts/join_graph_validated.json`

**What it does**:
- Validates heuristic relationships
- Removes invalid connections
- Increases confidence scores

### Step 4: Build Path Index

```bash
# Create path finder index
python scripts/build_join_graph_paths.py
```

**Output**: `artifacts/join_graph_paths.json`

**What it does**:
- Creates metadata index for path finder
- Validates path finder functionality
- Does NOT precompute all paths (efficient!)

## Running the System

### Development Server

```bash
# Start FastAPI server
cd apps/backend
python run_api.py
```

Server starts at: `http://localhost:8000`

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Streaming chat
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

### Interactive Testing

```bash
# Test orchestrator directly
python demo_orchestrator.py

# Test SQL agent
python test_phase2_sql_agent.py

# Test RAG agent
python test_phase3_rag.py
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

### Step 2: Update SECURE_VIEW_MAP

**File**: `src/sql/secure_views.py`

```python
SECURE_VIEW_MAP = {
    # ... existing mappings ...
    "newtable": "secure_newtable",  # Add here
}
```

### Step 3: Rebuild Join Graph

```bash
python scripts/build_join_graph.py
```

The join graph will automatically include the new secure view.

### Step 4: Test

```bash
python scripts/test_secure_views.py
```

## Configuring the SQL Agent

### Table Selection

The agent selects 3-8 tables per query. To adjust:

**File**: `src/agents/sql_graph_agent.py`

```python
# In _select_tables() prompt
prompt = f"""
Select ONLY the minimal set of tables needed to answer the question.

Rules:
- Return 3 to 8 tables only  # Adjust range here
- Select from ACTUAL available tables
...
"""
```

### Path Finding

Configure path finder:

**File**: `src/agents/sql_graph_agent.py`

```python
self.path_finder = JoinPathFinder(
    self.join_graph["relationships"],
    confidence_threshold=0.70,  # Adjust threshold
    max_hops=4  # Adjust max hops
)
```

### SQL Generation

Configure SQL limits:

**File**: `src/utils/config.py`

```python
@dataclass
class Settings:
    max_query_rows: int = 100  # Max rows returned
    sql_agent_max_iterations: int = 15  # Max reasoning steps
    sql_sample_rows: int = 1  # Sample rows per table
```

## Extending the System

### Adding a New Agent

1. **Create agent class**:

```python
# src/agents/my_agent.py
from langgraph.graph import StateGraph

class MyAgent:
    def __init__(self):
        self.llm = ChatOpenAI(...)
        self.workflow = self._build()
    
    def _build(self):
        graph = StateGraph(MyState)
        # Add nodes and edges
        return graph.compile()
    
    def query(self, question: str) -> str:
        result = self.workflow.invoke({"question": question})
        return result["answer"]
```

2. **Integrate into orchestrator**:

```python
# src/agents/orchestrator_agent.py
from src.agents.my_agent import MyAgent

class OrchestratorAgent:
    def __init__(self):
        self.my_agent = MyAgent()
        # ... update classification logic
```

### Adding Custom Tools

1. **Create tool**:

```python
# src/tools/my_tool.py
from langchain.tools import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    
    def _run(self, query: str) -> str:
        # Tool logic
        return result
```

2. **Register in agent**:

```python
# In agent __init__
from src.tools.my_tool import MyTool

tools = [MyTool()]
agent = create_agent(llm, tools)
```

## Troubleshooting

### SQL Agent Issues

#### Problem: "Table doesn't exist" errors

**Solution**:
1. Check join graph includes the table:
   ```bash
   cat artifacts/join_graph_merged.json | grep "table_name"
   ```
2. Rebuild join graph if missing
3. Check secure view mapping if it's an encrypted table

#### Problem: Slow query performance

**Solution**:
1. Reduce table selection (limit to 3-5 tables)
2. Add LIMIT clauses to queries
3. Check MySQL indexes on join columns
4. Reduce `sql_sample_rows` in config

#### Problem: Context length exceeded

**Solution**:
1. Reduce `sql_sample_rows` from 3 to 1
2. Limit tables in context (use `include_tables`)
3. Reduce `max_query_rows`
4. Upgrade to model with larger context window

### Path Finder Issues

#### Problem: Path finder not finding paths

**Solution**:
1. Check relationship confidence threshold (default 0.7)
2. Verify relationships exist in join graph
3. Increase `max_hops` if needed
4. Check logs for path finder errors

#### Problem: Path finder too slow

**Solution**:
1. Path finder should be <100ms - if slower, check:
   - Number of relationships (should be <2000)
   - Cache hit rate (should be high for repeated queries)
   - Graph structure (check for cycles)

### Secure Views Issues

#### Problem: Views return NULL

**Solution**:
1. Check `DB_ENCRYPT_KEY` is set in `.env`
2. Verify key matches encryption key used in database
3. Check MySQL session variables are set:
   ```sql
   SELECT @aesKey;
   ```
4. Restart application to reload environment

#### Problem: "secure_xyz doesn't exist" errors

**Solution**:
1. Verify view exists in MySQL:
   ```sql
   SHOW TABLES LIKE 'secure_%';
   ```
2. Check `SECURE_VIEW_MAP` includes the table
3. Rebuild join graph after adding view

### API Issues

#### Problem: Streaming not working

**Solution**:
1. Check SSE headers are set correctly
2. Verify `X-Accel-Buffering: no` header
3. Test with `curl -N` flag (no buffering)
4. Check browser EventSource support

#### Problem: CORS errors

**Solution**:
1. Update CORS origins in `src/api/app.py`:
   ```python
   allow_origins=["http://localhost:3000"]  # Your frontend URL
   ```
2. Restart server after changes

## Performance Optimization

### SQL Agent Optimization

1. **Reduce Schema Size**:
   ```python
   # In sql_tool.py
   self.db = SQLDatabase(
       sample_rows_in_table_info=1,  # Reduce from 3
       max_string_length=100,  # Truncate long strings
   )
   ```

2. **Limit Table Context**:
   ```python
   # Only load relevant tables
   relevant_tables = analyze_query(user_query)
   db = SQLDatabase(include_tables=relevant_tables)
   ```

3. **Cache Common Queries**:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def cached_query(query_hash: str):
       # Cache query results
   ```

### Path Finder Optimization

1. **Precompute Common Paths**:
   ```python
   # Precompute employee → workOrder path
   common_paths = {
       ("employee", "workOrder"): path_finder.find_shortest_path(...)
   }
   ```

2. **Increase Cache Size**:
   ```python
   # Path finder caches automatically
   # Increase if needed by adjusting cache in JoinPathFinder
   ```

### RAG Agent Optimization

1. **Reduce Chunk Size**:
   ```python
   # In chunking_strategies.py
   chunk_size = 500  # Reduce from 1000
   ```

2. **Limit Retrieved Chunks**:
   ```python
   # In rag_agent.py
   results = vector_store.search(query, k=5)  # Reduce from 10
   ```

3. **Enable Embedding Cache**:
   ```python
   # Already enabled by default
   # Check cache hit rate in logs
   ```

## Monitoring and Debugging

### Enable Debug Logging

```python
# In src/utils/logger.py or environment
LOG_LEVEL=DEBUG
```

### Trace SQL Agent Steps

The SQL agent includes trace decorators:

```python
@trace_step('select_tables')
def _select_tables(self, state):
    # Automatically logs:
    # - Step start/end
    # - Duration
    # - Input/output keys
    # - Errors
```

### Monitor Token Usage

```python
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = agent.query(question)
    print(f"Tokens: {cb.total_tokens}")
    print(f"Cost: ${cb.total_cost:.4f}")
```

### Check Join Graph Stats

```bash
python -c "
import json
with open('artifacts/join_graph_merged.json') as f:
    g = json.load(f)
    print(f'Tables: {len(g[\"tables\"])}')
    print(f'Relationships: {len(g[\"relationships\"])}')
"
```

## Testing

### Unit Tests

```bash
# Test secure views
python scripts/test_secure_views.py

# Test path finder
python -c "from src.utils.path_finder import JoinPathFinder; ..."
```

### Integration Tests

```bash
# Test SQL agent
python test_phase2_sql_agent.py

# Test orchestrator
python test_phase4_orchestrator.py

# Test API
python test_internal_api.py
```

### Manual Testing

```bash
# Test specific query
python -c "
from src.agents.orchestrator_agent import OrchestratorAgent
agent = OrchestratorAgent()
result = agent.ask('How many employees are there?')
print(result['answer'])
"
```

## Deployment

### Production Checklist

- [ ] Set all environment variables
- [ ] Configure `DB_ENCRYPT_KEY` securely (use secrets manager)
- [ ] Rebuild join graph with validated relationships
- [ ] Test secure views with real encryption key
- [ ] Configure CORS for production domain
- [ ] Set up monitoring and logging
- [ ] Configure connection pooling appropriately
- [ ] Test API endpoints
- [ ] Load test with expected query volume

### Environment-Specific Configs

```bash
# Development
OPENAI_MODEL=gpt-4o-mini
SQL_SAMPLE_ROWS=3
MAX_QUERY_ROWS=500

# Production
OPENAI_MODEL=gpt-4o-mini
SQL_SAMPLE_ROWS=1
MAX_QUERY_ROWS=100
```

## Common Patterns

### Pattern 1: Multi-Hop Join Discovery

The path finder automatically discovers paths like:
```
employee → workTime → workOrder → customer
```

No manual configuration needed - just ensure relationships are in join graph.

### Pattern 2: Secure View Rewriting

Always use logical table names in prompts:
```python
# ✅ Good
prompt = "Use table names: employee, workOrder, inspections"

# ❌ Bad
prompt = "Use secure_employee, secure_workorder"
```

System handles rewriting automatically.

### Pattern 3: Error Handling

```python
try:
    result = sql_agent.query(question)
except ValueError as e:
    # Table validation error
    logger.error(f"Invalid table: {e}")
except Exception as e:
    # Other errors
    logger.error(f"Query failed: {e}")
```

## Best Practices

1. **Always use LIMIT clauses** in generated SQL
2. **Validate tables exist** before execution
3. **Cache embeddings** to reduce costs
4. **Monitor token usage** to avoid overages
5. **Rebuild join graph** after schema changes
6. **Test secure views** after adding new encrypted tables
7. **Use validated join graph** in production
8. **Log all queries** for debugging
9. **Set appropriate timeouts** for long-running queries
10. **Use connection pooling** for performance
