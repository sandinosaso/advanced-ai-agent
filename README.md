# AI Learning Project

A project focused on learning advanced AI concepts including LangGraph, RAG, embeddings, and workflow orchestration.

## Learning Objectives

- **LangGraph workflows** - Building multi-step agent workflows
- **RAG patterns** - Retrieval Augmented Generation with vector stores
- **Memory management** - Persistent agent memory
- **Embeddings & chunking** - Text processing and semantic search
- **Tool orchestration** - Integrating multiple APIs
- **Production patterns** - Configuration, error handling, monitoring

## Tech Stack

### Infrastructure
- **Nx Monorepo** - v22.3.3 for workspace management
- **Node.js** - v20.19.6 (locked via .nvmrc)
- **Python** - 3.11.0 via pyenv
- **UV** - Fast Python package manager

### AI/ML
- **LangChain** - Agent framework
- **LangGraph** - Workflow orchestration
- **OpenAI** - LLM provider (gpt-4o-mini)
- **ChromaDB** - Vector database (ready to integrate)

### Core Libraries
- **Pydantic** - Data validation and settings
- **PyYAML** - Configuration management
- **python-dotenv** - Environment variables
- **Loguru** - Advanced logging

## Project Structure

```
apps/backend/
├── config/
│   └── config.yaml          # Application configuration
├── src/
│   ├── agents/              # LangGraph agents (ready for your use case)
│   ├── models/              # Pydantic data models (ready for your use case)
│   ├── services/            # External service integrations (ready for your use case)
│   ├── prompts/             # LLM prompt templates
│   └── utils/
│       ├── logger.py        # Logging utility
│       ├── config.py        # Configuration loader
│       └── chunking.py      # Text chunking utilities
├── main.py                  # Application entry point
└── pyproject.toml          # Python dependencies
```

## Setup

### Prerequisites
- Node.js 20.19.6
- Python 3.11.0 (via pyenv)
- UV package manager

### Installation

1. **Install Node dependencies:**
   ```bash
   npm install
   ```

2. **Set up Python environment:**
   ```bash
   cd apps/backend
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

3. **Configure environment variables:**
   Create `.env` file in `apps/backend/`:
   ```env
   OPENAI_API_KEY=your-key-here
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_TEMPERATURE=0.1
   ```

## Available Scripts

```bash
# Run main application
npm run backend:start

# Run with Python directly
cd apps/backend && python main.py
```

## Next Steps

This project is now a clean slate, ready for your next AI/RAG use case. The infrastructure is in place:

- ✅ Nx monorepo configured
- ✅ Python environment with UV
- ✅ LangChain & LangGraph installed
- ✅ Configuration management
- ✅ Logging utilities
- ✅ Clean project structure

**Ready to implement:**
- Your RAG use case
- LangGraph workflow
- Vector database integration
- Custom agents and tools
