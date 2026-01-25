# Documentation

This directory contains the consolidated documentation for the Advanced AI Agent system.

## Core Documentation

### 📐 [ARCHITECTURE.md](./ARCHITECTURE.md)
**System architecture and design**

- System components and workflows
- Agent architecture (Orchestrator, SQL, RAG)
- Join graph pipeline
- Path finder implementation
- Secure views architecture
- API architecture
- Data flow diagrams
- Performance characteristics

**Read this first** to understand how the system works.

### 🛠️ [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
**How to use, configure, and extend the system**

- Quick start and installation
- Building the join graph
- Running the system
- Adding new features
- Configuration options
- Troubleshooting
- Performance optimization
- Deployment checklist

**Use this** for day-to-day development and operations.

### 📚 [REFERENCE.md](./REFERENCE.md)
**Quick reference for configurations and commands**

- Environment variables
- Configuration options
- API endpoints
- Command reference
- Troubleshooting quick fixes
- Cost estimation
- Performance benchmarks

**Use this** as a quick lookup guide.

## Specialized Documentation

Detailed documentation on specific topics is available in the [`specialized/`](./specialized/) folder:

- **[JOIN_GRAPH_PIPELINE.md](./specialized/JOIN_GRAPH_PIPELINE.md)** - Detailed documentation on the join graph pipeline and how relationships are discovered.

- **[SECURE_VIEWS_ARCHITECTURE.md](./specialized/SECURE_VIEWS_ARCHITECTURE.md)** - Comprehensive guide to the secure views architecture and how it prevents LLM hallucinations.

- **[PATH_FINDER_IMPLEMENTATION.md](./specialized/PATH_FINDER_IMPLEMENTATION.md)** - Documentation on the path finder implementation using Dijkstra's algorithm.

- **[MODEL_LIMITS_AND_COSTS.md](./specialized/MODEL_LIMITS_AND_COSTS.md)** - Reference for OpenAI model limits, costs, and optimization strategies.

- **[MYSQL_SESSION_VARIABLES.md](./specialized/MYSQL_SESSION_VARIABLES.md)** - Documentation on MySQL session variables for secure views.

## Documentation Structure

The documentation is organized into:

- **3 core documents** (in root): Architecture, Implementation Guide, and Reference
- **5 specialized documents** (in `specialized/`): Deep dives on specific topics
- **README.md**: This file - documentation index

All historical phase documentation has been removed as information has been consolidated into the core documents.

## Getting Started

1. **New to the project?** Start with [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Setting up?** Follow [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
3. **Need quick info?** Check [REFERENCE.md](./REFERENCE.md)
4. **Working on specific feature?** See specialized docs

## Contributing

When updating documentation:

1. **Architecture changes**: Update [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **New features**: Update [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
3. **Configuration changes**: Update [REFERENCE.md](./REFERENCE.md)
4. **Specialized topics**: Update the relevant specialized doc

Keep documentation up-to-date with code changes!
