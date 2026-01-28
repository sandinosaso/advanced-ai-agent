# Advanced AI Agent

A Python-based AI agent system for natural language to SQL conversion with RAG capabilities, built using LangGraph, OpenAI, and MySQL.

## Features

- **SQL Graph Agent**: LangGraph-based agent that converts natural language queries to SQL
- **RAG Agent**: Retrieval-Augmented Generation for document-based question answering
- **Orchestrator Agent**: Routes queries between SQL and RAG agents
- **Secure Views**: Automatic rewriting of sensitive tables to secure views
- **Join Path Finding**: Efficient graph-based join path discovery
- **Error Correction**: Automatic SQL error detection and correction

## Tech Stack

### Core
- **Python** - 3.11+
- **UV** - Fast Python package manager
- **FastAPI** - Web framework for API server

### AI/ML
- **LangChain** - Agent framework
- **LangGraph** - Workflow orchestration
- **OpenAI** - LLM provider (gpt-4o-mini, gpt-4o) - Optional, can use Ollama instead
- **Ollama** - Local LLM provider for offline operation (optional)
- **ChromaDB** - Vector database for RAG
- **Sentence Transformers** - Local embeddings for offline operation

### Database
- **MySQL** - Primary database (100+ tables)
- **SQLAlchemy** - Database toolkit

### Core Libraries
- **Pydantic** - Data validation and settings
- **PyYAML** - Configuration management
- **python-dotenv** - Environment variables
- **Loguru** - Advanced logging

## Project Structure

```
advanced-ai-agent/
├── src/
│   ├── agents/              # LangGraph agents
│   │   ├── orchestrator_agent.py
│   │   ├── sql_graph_agent.py
│   │   └── rag_agent.py
│   ├── api/                 # FastAPI application
│   │   ├── app.py
│   │   ├── models.py
│   │   └── routes/
│   ├── models/              # Pydantic data models
│   ├── services/            # Service integrations
│   ├── tools/               # Agent tools
│   ├── utils/               # Utilities
│   │   ├── sql/             # SQL utilities (secure views)
│   │   ├── rag/             # RAG utilities (chunking, embeddings, vector store)
│   │   ├── config.py
│   │   └── logger.py
│   └── prompts/             # LLM prompt templates
├── scripts/                 # Utility scripts
│   ├── run-dev.py           # Development server
│   ├── run-prod.py          # Production server
│   ├── setup.sh             # Setup script
│   └── ...                  # Other utility scripts
├── tests/                   # Test files
├── config/                  # Configuration files
├── artifacts/               # Generated artifacts (join graphs)
├── data/                    # Data files
│   ├── vector_store/        # ChromaDB data
│   └── embeddings_cache/    # Cached embeddings
├── docs/                    # Documentation
├── .env.example             # Example environment variables
├── pyproject.toml           # Python dependencies
└── requirements.txt         # Python requirements
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
   - **SQL Generation**: `codellama` or `llama3` (8B+) - requires strong reasoning
   - **RAG/General**: `llama3` (7B+) or `mistral` (7B) - good balance
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

## Available Scripts

- `scripts/run-dev.py` - Start development server with auto-reload
- `scripts/run-prod.py` - Start production server
- `scripts/setup.sh` - Setup script for initial configuration
- `scripts/start-ollama.sh` - Start Ollama server (for offline operation)
- `scripts/populate_vector_store.py` - Populate vector store with documents
- `scripts/build_join_graph.py` - Build join graph from database schema
- `scripts/build_join_graph_paths.py` - Generate join paths for SQL agent

## Documentation

See the `docs/` directory for detailed documentation:
- `ARCHITECTURE.md` - System architecture and design
- `IMPLEMENTATION_GUIDE.md` - Implementation details
- `REFERENCE.md` - API and configuration reference

## License

[Your License Here]
