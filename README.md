# Advanced AI Agent

A Python-based AI agent system for natural language to SQL conversion with RAG capabilities, built using LangGraph, OpenAI, and MySQL.

## Features

- **SQL Graph Agent**: LangGraph-based agent that converts natural language queries to SQL
- **RAG Agent**: Retrieval-Augmented Generation for document-based question answering
- **Orchestrator Agent**: Routes queries between SQL, RAG, and General agents
- **Secure Views**: Automatic rewriting of sensitive tables to secure views
- **Join Path Finding**: Efficient graph-based join path discovery (Dijkstra)
- **Semantic Role System**: Table metadata (instance, bridge, satellite, assignment, configuration) to avoid unnecessary bridge tables and prefer direct foreign keys
- **Bridge Table Discovery**: Logic that only adds bridge tables when no direct path exists; excludes assignment/configuration tables
- **Domain Ontology**: Maps business terms to schema (tables, filters, scoped joins)
- **Display Attributes**: Human-readable column selection and template relationships for SQL results
- **Scoped Joins**: Template-instance scoping for form data (inspections, safety, service)
- **Follow-up Memory**: Context-aware handling of follow-up questions with previous query results
- **Error Correction**: Automatic SQL error detection and correction

## Tech Stack

### Core
- **Python** – 3.11+
- **UV** – Fast Python package manager
- **FastAPI** – Web framework for API server

### AI/ML
- **LangChain** – Agent framework
- **LangGraph** – Workflow orchestration
- **OpenAI** – LLM provider (gpt-4o-mini, gpt-4o) – Optional, can use Ollama instead
- **Ollama** – Local LLM provider for offline operation (optional)
- **ChromaDB** – Vector database for RAG
- **Sentence Transformers** – Local embeddings for offline operation

### Database
- **MySQL** – Primary database (100+ tables)
- **SQLAlchemy** – Database toolkit

### Core Libraries
- **Pydantic** – Data validation and settings
- **PyYAML** – Configuration management
- **python-dotenv** – Environment variables
- **Loguru** – Advanced logging

## Project Structure

```
api-ai-agent/
├── src/
│   ├── agents/
│   │   ├── orchestrator/          # Routing, classify, sql/rag/general nodes
│   │   ├── sql/                   # SQL Graph Agent
│   │   │   ├── nodes/             # table_selector, join_planner, sql_generator, executor, etc.
│   │   │   ├── planning/          # bridge_tables, domain_filters, scoped_joins
│   │   │   ├── workflow.py
│   │   │   └── context.py
│   │   ├── rag/
│   │   └── general/
│   ├── api/                       # FastAPI app, routes, schemas
│   ├── domain/
│   │   ├── ontology/              # Domain term extraction & resolution
│   │   └── display_attributes/   # Display columns & template relationships
│   ├── sql/                       # Execution, secure rewriter, join_graph loader
│   ├── utils/
│   │   ├── path_finder.py         # Join path finder (Dijkstra)
│   │   └── rag/                   # Chunking, embeddings, vector store
│   ├── memory/                    # Conversation store, query result memory
│   ├── llm/                       # LLM client, embeddings
│   ├── infra/                     # Database, vector store
│   └── config/                    # Settings, constants
├── scripts/
│   ├── run-dev.py                 # Development server
│   ├── run-prod.py                # Production server
│   ├── run_tests.sh               # Unit tests
│   ├── build_join_graph.py        # Build join graph from DB
│   └── ...
├── artifacts/
│   ├── join_graph_merged.json     # Merged join graph (FK + manual + heuristic)
│   ├── join_graph_manual.json    # Manual relationships + table_metadata (semantic roles)
│   ├── domain_registry.json       # Business term → schema mapping
│   └── display_attributes_registry.json
├── tests/
├── docs/                          # Architecture and specialized docs
├── .env.example
├── pyproject.toml
└── requirements.txt
```

## Setup

### Prerequisites
- Python 3.11+
- UV package manager
- MySQL database
- (Optional) Ollama for offline/local operation

### Installation

1. **Run setup script:**
   ```bash
   bash scripts/setup.sh
   ```

2. **Or manually:**
   ```bash
   # Create virtual environment
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   uv pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Copy `.env.example` to `.env` and configure:
   
   **For OpenAI (default, requires internet):**
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-key-here
   OPENAI_MODEL=gpt-4o-mini
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PWD=your_password
   DB_NAME=crewos
   DB_ENCRYPT_KEY=your_encryption_key
   ```
   
   **For Ollama (offline/local operation):**
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   OLLAMA_EMBEDDING_MODEL=all-MiniLM-L6-v2
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PWD=your_password
   DB_NAME=crewos
   DB_ENCRYPT_KEY=your_encryption_key
   ```

### Using Ollama for Offline Operation

To run the system without internet access using local models:

1. **Install Ollama:**
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Or download from https://ollama.com
   ```

2. **Pull a model:**
   ```bash
   # Recommended models:
   ollama pull llama3          # Good general-purpose model (8B)
   ollama pull codellama       # Better for SQL generation
   ollama pull mistral         # Smaller, faster alternative
   ```

3. **Start Ollama server:**
   ```bash
   # Option 1: Use the provided script (recommended)
   bash scripts/start-ollama.sh
   
   # Option 2: Start manually
   ollama serve
   # Server runs on http://localhost:11434 by default
   ```

4. **Configure `.env`:**
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   OLLAMA_EMBEDDING_MODEL=all-MiniLM-L6-v2
   ```
   
   Note: `OLLAMA_EMBEDDING_MODEL` uses sentence-transformers (local), not Ollama's API.

5. **Model Recommendations:**
   - **SQL Generation**: `codellama` or `llama3` (8B+) – requires strong reasoning
   - **RAG/General**: `llama3` (7B+) or `mistral` (7B) – good balance
   - **Embeddings**: `all-MiniLM-L6-v2` (fast) or `all-mpnet-base-v2` (better quality)

## Running the Application

### Development Mode
```bash
python scripts/run-dev.py
```

### Production Mode
```bash
python scripts/run-prod.py
```

The API will be available at:
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Chat Streaming**: POST http://localhost:8000/api/chat/stream

## Testing

```bash
sh scripts/run_tests.sh
```

Runs unit tests (excluding tests that require the API server).

## Documentation

Full documentation lives in the **`docs/`** directory.

### Core docs (in `docs/`)

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, components, join graph pipeline, **semantic role system**, path finder, secure views, data flow |
| [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) | Setup, join graph build, configuration, deployment |
| [docs/REFERENCE.md](docs/REFERENCE.md) | Environment variables, API endpoints, commands, troubleshooting |

### Specialized docs (in `docs/specialized/`)

| Topic | Document |
|-------|----------|
| SQL Agent, Join Graph, Path Finder | [SQL_AGENT_AND_JOIN_GRAPH.md](docs/specialized/SQL_AGENT_AND_JOIN_GRAPH.md) |
| **Semantic Role System** (bridge tables, table roles) | [SEMANTIC_ROLE_SYSTEM.md](docs/specialized/SEMANTIC_ROLE_SYSTEM.md) |
| Domain Ontology & template scoping | [DOMAIN_ONTOLOGY.md](docs/specialized/DOMAIN_ONTOLOGY.md) |
| Display Attributes | [DISPLAY_ATTRIBUTES.md](docs/specialized/DISPLAY_ATTRIBUTES.md) |
| Scoped Joins (template-instance) | [SCOPED_JOINS_IMPLEMENTATION.md](docs/specialized/SCOPED_JOINS_IMPLEMENTATION.md) |
| Secure Views & DB session variables | [SECURE_VIEWS_AND_DATABASE.md](docs/specialized/SECURE_VIEWS_AND_DATABASE.md) |
| RAG & Vector Store | [RAG_AND_VECTOR_STORE.md](docs/specialized/RAG_AND_VECTOR_STORE.md) |
| Follow-up Memory | [FOLLOWUP_QUESTIONS_MEMORY.md](docs/specialized/FOLLOWUP_QUESTIONS_MEMORY.md) |
| BFF Integration & model limits | [INTEGRATION_AND_REFERENCE.md](docs/specialized/INTEGRATION_AND_REFERENCE.md) |

### Quick links

- **New to the project?** Start with [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **Semantic roles / bridge tables:** [docs/specialized/SEMANTIC_ROLE_SYSTEM.md](docs/specialized/SEMANTIC_ROLE_SYSTEM.md).
- **Full doc index:** [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md).

## Available Scripts

| Script | Description |
|--------|-------------|
| `scripts/run-dev.py` | Development server with auto-reload |
| `scripts/run-prod.py` | Production server |
| `scripts/run_tests.sh` | Run unit tests |
| `scripts/setup.sh` | Initial setup |
| `scripts/start-ollama.sh` | Start Ollama server (offline operation) |
| `scripts/populate_vector_store.py` | Populate RAG vector store |
| `scripts/build_join_graph.py` | Build join graph from database schema |
| `scripts/build_join_graph_paths.py` | Generate join paths for SQL agent |

## License

[Your License Here]
