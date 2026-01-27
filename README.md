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
- **OpenAI** - LLM provider (gpt-4o-mini, gpt-4o)
- **ChromaDB** - Vector database for RAG

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
   ```env
   OPENAI_API_KEY=your-key-here
   DATABASE_URL=mysql+pymysql://user:password@host:port/database
   ```

4. **Configure database:**
   Edit `config/config.yaml` with your database settings

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
