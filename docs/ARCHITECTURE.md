# System Architecture

## Overview

This document describes the architecture of the Advanced AI Agent system - an intelligent SQL agent that works with MySQL databases containing 100+ tables. The system uses LangGraph workflows, graph algorithms for join path discovery, and secure views for encrypted data access.

## System Components

```mermaid
graph TB
    User[User Question] --> Orchestrator[Orchestrator Agent]
    Orchestrator --> Classify{Classify Question}
    Classify -->|SQL Query| SQLAgent[SQL Graph Agent]
    Classify -->|Policy/Knowledge| RAGAgent[RAG Agent]
    
    SQLAgent --> TableSelector[Table Selector]
    TableSelector --> PathFinder[Path Finder<br/>Dijkstra Algorithm]
    PathFinder --> JoinPlanner[Join Planner]
    JoinPlanner --> SQLGen[SQL Generator]
    SQLGen --> SecureRewrite[Secure View Rewriter]
    SecureRewrite --> Validator[Table Validator]
    Validator --> Executor[SQL Executor]
    Executor --> MySQL[(MySQL Database<br/>122 Tables)]
    
    RAGAgent --> VectorStore[(ChromaDB<br/>Vector Store)]
    VectorStore --> Embeddings[Embedding Service]
    
    SQLAgent --> Result[Final Answer]
    RAGAgent --> Result
    
    style Orchestrator fill:#4A90E2
    style SQLAgent fill:#50C878
    style RAGAgent fill:#FF6B6B
    style MySQL fill:#F39C12
    style VectorStore fill:#9B59B6
```

## Core Agents

### 1. Orchestrator Agent

The main entry point that routes questions to appropriate agents.

**Location**: `src/agents/orchestrator_agent.py`

**Workflow**:
```mermaid
stateDiagram-v2
    [*] --> Classify
    Classify --> SQL: Database Query
    Classify --> RAG: Policy/Knowledge
    SQL --> Finalize
    RAG --> Finalize
    Finalize --> [*]
```

**Responsibilities**:
- Classifies user questions (SQL vs RAG)
- Routes to SQL Agent or RAG Agent
- Formats final answers
- Manages conversation state

**State Schema**:
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]    # Conversation history
    question: str                   # User question
    next_step: str                  # Routing decision
    sql_result: str | None          # SQL agent output
    rag_result: str | None          # RAG agent output
    final_answer: str | None        # Final response
```

### 2. SQL Graph Agent

Advanced SQL agent that uses graph algorithms to discover optimal join paths.

**Location**: `src/agents/sql_graph_agent.py`

**Workflow**:
```mermaid
graph LR
    A[Question] --> B[Table Selector]
    B --> C[Filter Relationships]
    C --> D[Path Finder<br/>Dijkstra]
    D --> E[Join Planner]
    E --> F[SQL Generator]
    F --> G[Secure Rewriter]
    G --> H[Validator]
    H --> I[Executor]
    I --> J[Result]
    
    style D fill:#FFD700
    style G fill:#FF6B6B
```

**Key Features**:
- **Table Selection**: LLM selects 3-8 relevant tables from 122 available
- **Path Finding**: Uses Dijkstra's algorithm to find shortest join paths
- **Join Planning**: Discovers transitive paths (multi-hop joins)
- **Secure Views**: Automatic rewriting of encrypted tables
- **Validation**: Pre-execution table validation prevents hallucinations

**State Schema**:
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

### 3. RAG Agent

Retrieval-Augmented Generation agent for policy and compliance questions.

**Location**: `src/agents/rag_agent.py`

**Workflow**:
```mermaid
graph LR
    A[Question] --> B[Embed Query]
    B --> C[Vector Search]
    C --> D[Retrieve Top-K]
    D --> E[Build Context]
    E --> F[LLM Generation]
    F --> G[Answer]
    
    style C fill:#9B59B6
```

**Data Sources**:
- Company handbook
- Compliance documents (OSHA, FLSA)
- State regulations
- Work log descriptions

## Join Graph Pipeline

The system uses a sophisticated join graph to understand relationships between 122 tables.

### Pipeline Overview

```mermaid
graph TB
    A[MySQL Database<br/>122 Tables] --> B[DB Introspection<br/>build_join_graph.py]
    C[Node.js Associations<br/>extract_associations.js] --> D[Merge<br/>merge_join_graph.py]
    E[Manual Overrides<br/>join_graph_manual.json] --> D
    B --> D
    D --> F[LLM Validation<br/>validate_join_graph_llm.py]
    F --> G[Validated Graph<br/>join_graph_validated.json]
    
    G --> H[Path Finder<br/>Dijkstra Algorithm]
    H --> I[SQL Agent]
    
    style G fill:#50C878
    style H fill:#FFD700
```

### Graph Structure

```json
{
  "version": 1,
  "tables": {
    "employee": {
      "columns": ["id", "firstName", "lastName", ...],
      "unique_columns": ["id"]
    },
    ...
  },
  "relationships": [
    {
      "from_table": "workTime",
      "from_column": "employeeId",
      "to_table": "employee",
      "to_column": "id",
      "type": "foreign_key",
      "confidence": 1.0,
      "cardinality": "N:1"
    },
    ...
  ]
}
```

### Path Finder

**Location**: `src/utils/path_finder.py`

Uses Dijkstra's algorithm to find shortest join paths between tables:

```python
path_finder = JoinPathFinder(relationships, confidence_threshold=0.7)
path = path_finder.find_shortest_path("employee", "customer", max_hops=4)
# Returns: [rel1, rel2, rel3] - shortest path
```

**Performance**:
- **Before**: Exponential complexity (never finished)
- **After**: O((V + E) log V) - < 100ms per query
- **Caching**: O(1) for repeated paths

## Secure Views Architecture

Prevents LLM hallucination of non-existent `secure_*` tables through explicit mapping.

### Three-Layer Architecture

```mermaid
graph TB
    subgraph "Layer 1: Physical Tables"
        A1[user<br/>encrypted]
        A2[employee<br/>encrypted]
        A3[inspections<br/>not encrypted]
    end
    
    subgraph "Layer 2: Secure Views"
        B1[secure_user]
        B2[secure_employee]
        B3[inspections<br/>no secure view]
    end
    
    subgraph "Layer 3: Logical Entities"
        C1[user/secure_user]
        C2[employee/secure_employee]
        C3[inspections]
    end
    
    A1 --> B1
    A2 --> B2
    A3 --> B3
    
    B1 --> C1
    B2 --> C2
    B3 --> C3
    
    C1 --> D[SECURE_VIEW_MAP]
    C2 --> D
    C3 -.->|not in map| D
    
    style D fill:#FF6B6B
```

### Secure View Map

**Location**: `src/sql/secure_views.py`

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

**Key Rules**:
1. Only tables in `SECURE_VIEW_MAP` get `secure_*` variants
2. LLM uses logical names (e.g., `employee`)
3. System rewrites deterministically (`employee` → `secure_employee`)
4. Validation prevents hallucinations before execution

### Rewriting Flow

```mermaid
sequenceDiagram
    participant LLM
    participant Rewriter
    participant Validator
    participant MySQL
    
    LLM->>Rewriter: SELECT * FROM employee
    Rewriter->>Rewriter: Check SECURE_VIEW_MAP
    Rewriter->>Rewriter: employee → secure_employee
    Rewriter->>Validator: SELECT * FROM secure_employee
    Validator->>Validator: Check table exists
    Validator->>MySQL: Execute query
    MySQL-->>Validator: Decrypted results
    Validator-->>LLM: Results
```

## API Architecture

### Internal API Service

The system exposes a FastAPI internal service following the Backend-for-Frontend (BFF) pattern.

**Location**: `src/api/`

**Architecture**:
```mermaid
graph LR
    Browser[Browser] --> NodeJS[Node.js BFF<br/>Auth, UX]
    NodeJS --> FastAPI[FastAPI<br/>Internal API]
    FastAPI --> Orchestrator[Orchestrator Agent]
    
    style NodeJS fill:#4A90E2
    style FastAPI fill:#50C878
```

### Endpoint

**POST** `/internal/chat/stream`

**Request**:
```json
{
  "input": {
    "message": "How many technicians are active?"
  },
  "conversation": {
    "id": "conv-uuid-123",
    "user_id": "user-456",
    "company_id": "company-789"
  }
}
```

**Response** (Server-Sent Events):
```
data: {"event":"route_decision","route":"sql"}

data: {"event":"tool_start","tool":"sql_agent"}

data: {"event":"token","channel":"final","content":"There"}

data: {"event":"token","channel":"final","content":" are 10"}

data: {"event":"complete","stats":{"tokens":15}}
```

### Event Types

| Event | Description |
|-------|-------------|
| `route_decision` | Agent routing decision (SQL/RAG) |
| `tool_start` | Tool execution beginning |
| `token` | Content token with channel |
| `complete` | Stream finished |
| `error` | Error occurred |

## Data Flow

### SQL Query Flow

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant SQLAgent
    participant PathFinder
    participant SQLGen
    participant Rewriter
    participant MySQL
    
    User->>Orchestrator: "Show employees who worked >20h"
    Orchestrator->>SQLAgent: Route to SQL
    SQLAgent->>SQLAgent: Select tables: [employee, workTime]
    SQLAgent->>PathFinder: Find path employee → workTime
    PathFinder-->>SQLAgent: Direct relationship
    SQLAgent->>SQLGen: Generate SQL with joins
    SQLGen-->>SQLAgent: SELECT e.* FROM employee e...
    SQLAgent->>Rewriter: Rewrite secure tables
    Rewriter-->>SQLAgent: SELECT e.* FROM secure_employee e...
    SQLAgent->>MySQL: Execute query
    MySQL-->>SQLAgent: Results
    SQLAgent-->>Orchestrator: "10 employees worked >20h"
    Orchestrator-->>User: Final answer
```

### RAG Query Flow

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant RAGAgent
    participant Embedding
    participant VectorStore
    participant LLM
    
    User->>Orchestrator: "What are overtime rules?"
    Orchestrator->>RAGAgent: Route to RAG
    RAGAgent->>Embedding: Embed query
    Embedding-->>RAGAgent: Query vector
    RAGAgent->>VectorStore: Search similar chunks
    VectorStore-->>RAGAgent: Top 5 chunks
    RAGAgent->>LLM: Generate answer from chunks
    LLM-->>RAGAgent: "Overtime is paid at 1.5x..."
    RAGAgent-->>Orchestrator: Answer with sources
    Orchestrator-->>User: Final answer
```

## Database Configuration

### MySQL Connection

**Location**: `src/models/database.py`

**Connection String**:
```python
mysql+pymysql://{user}:{password}@{host}:{port}/{database}
```

**Connection Pooling**:
- Pool size: 5
- Max overflow: 10
- Pool recycle: 3600 seconds
- Pool pre-ping: Enabled

### Session Variables

MySQL session variables are set automatically on connection:

```python
SET @aesKey = '{encryption_key}'
SET @customerIds = NULL
SET @workOrderIds = NULL
SET @serviceLocationIds = NULL
```

**Purpose**: Enable secure views to decrypt encrypted fields using `AES_DECRYPT()`.

## Security Architecture

### Secure Views Access Control

1. **Base tables excluded**: Encrypted base tables are hidden from SQL agent
2. **Secure views exposed**: Only secure views are visible in schema
3. **Automatic rewriting**: System rewrites queries to use secure views
4. **Validation**: All table references validated before execution

### Encryption Flow

```mermaid
graph LR
    A[Application] -->|AES_ENCRYPT| B["Base Table<br/>Encrypted"]
    B -->|AES_DECRYPT with @aesKey| C["Secure View<br/>Decrypted"]
    C -->|SELECT| D[SQL Agent]
    
    style B fill:#FF6B6B
    style C fill:#50C878
```

## Performance Characteristics

### SQL Agent Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Table Selection | 1-2s | LLM call |
| Path Finding | <100ms | Dijkstra algorithm |
| SQL Generation | 1-2s | LLM call |
| Query Execution | 0.5-5s | Depends on query |
| **Total** | **3-10s** | End-to-end |

### RAG Agent Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Query Embedding | <100ms | Cached: <1ms |
| Vector Search | 10-50ms | ChromaDB |
| LLM Generation | 1-3s | Depends on context |
| **Total** | **1-4s** | End-to-end |

### Caching Strategy

- **Embeddings**: Disk cache (`data/embeddings_cache/`)
- **Path Finder**: In-memory cache (per session)
- **Join Graph**: Loaded once at startup

## Scalability Considerations

### Current Limits

- **Tables**: 122 (tested)
- **Relationships**: 1,801
- **Max Hops**: 4 (configurable)
- **Context Window**: 128K tokens (gpt-4o-mini)

### Optimization Strategies

1. **Table Selection**: Limit to 3-8 tables per query
2. **Schema Sampling**: Reduce sample rows (currently 1-3)
3. **Path Caching**: Cache computed paths
4. **Query Limits**: Always use LIMIT clauses

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | OpenAI GPT-4o-mini | Natural language understanding |
| **Workflow** | LangGraph | Agent orchestration |
| **Database** | MySQL + SQLAlchemy | Data storage |
| **Vector DB** | ChromaDB | Document embeddings |
| **API** | FastAPI | Internal service |
| **Streaming** | Server-Sent Events | Real-time responses |
| **Path Finding** | Dijkstra Algorithm | Join path discovery |

## Key Design Decisions

### 1. Graph-Based Join Discovery

**Why**: Traditional SQL agents struggle with 100+ tables. Graph algorithms find optimal paths efficiently.

**How**: Dijkstra's algorithm finds shortest paths between selected tables.

**Benefit**: Discovers multi-hop joins automatically.

### 2. Secure Views Pattern

**Why**: Prevents LLM from hallucinating non-existent `secure_*` tables.

**How**: Explicit mapping + deterministic rewriting + validation.

**Benefit**: Zero hallucination errors, fail-fast validation.

### 3. Internal API Pattern

**Why**: Separates AI logic from frontend concerns.

**How**: BFF pattern - Node.js handles auth/UX, Python handles agents.

**Benefit**: Clean separation, reusable, secure.

### 4. On-Demand Path Finding

**Why**: Precomputing all paths is exponential.

**How**: Compute paths only for selected tables using Dijkstra.

**Benefit**: Efficient, scalable, cached.

## Future Enhancements

1. **Memory Management**: Conversation history with LangGraph checkpointing
2. **Query Optimization**: Cost-based query plan analysis
3. **Semantic Table Selection**: Use embeddings to find relevant tables
4. **Multi-Tenancy**: Company-specific data isolation
5. **Monitoring**: LangSmith integration, metrics, tracing
