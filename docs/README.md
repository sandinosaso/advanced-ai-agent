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

Detailed documentation on specific topics is available in the [`specialized/`](./specialized/) folder. See [specialized/README.md](./specialized/README.md) for the full index.

| Topic | Document |
|-------|----------|
| SQL Agent, Join Graph, Path Finder, Audit Filtering | [SQL_AGENT_AND_JOIN_GRAPH.md](./specialized/SQL_AGENT_AND_JOIN_GRAPH.md) |
| Secure Views & Database Session Variables | [SECURE_VIEWS_AND_DATABASE.md](./specialized/SECURE_VIEWS_AND_DATABASE.md) |
| Domain Ontology & Template Scoping | [DOMAIN_ONTOLOGY.md](./specialized/DOMAIN_ONTOLOGY.md) |
| RAG & Vector Store | [RAG_AND_VECTOR_STORE.md](./specialized/RAG_AND_VECTOR_STORE.md) |
| Follow-up Memory | [FOLLOWUP_QUESTIONS_MEMORY.md](./specialized/FOLLOWUP_QUESTIONS_MEMORY.md) |
| BFF Integration & Model Limits | [INTEGRATION_AND_REFERENCE.md](./specialized/INTEGRATION_AND_REFERENCE.md) |

## Documentation Structure

- **3 core documents** (in root): Architecture, Implementation Guide, Reference
- **6 specialized documents** (in `specialized/`): Deep dives grouped by topic
- **specialized/README.md**: Index of specialized docs

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
