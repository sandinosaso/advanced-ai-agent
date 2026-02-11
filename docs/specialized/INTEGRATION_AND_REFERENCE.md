# Integration & Reference

## Overview

This document covers BFF integration (structured data → markdown), **cost estimation** for different LLM options, and model limits/costs reference. Use it for integration work and for presenting the system’s cost profile.

---

## 1. BFF Markdown Conversion

### Architecture

```
Python Backend → Node.js BFF → React Frontend
     ↓              ↓              ↓
Structured      Markdown      Renders
Arrays          Conversion    Markdown
```

### Python Backend Output

The Python backend returns `structured_data` in token events:

```json
{
  "event": "token",
  "channel": "final",
  "content": "There are",
  "structured_data": [
    {"id": 1, "name": "John", "count": 10},
    {"id": 2, "name": "Jane", "count": 5}
  ]
}
```

- **`structured_data`** is sent only in the **first token** of the `final` channel (when the answer comes from the SQL agent).
- If present, the BFF should convert it to markdown (table or list).
- If `structured_data` is `null`, use `content` as-is (backward compatible).

### BFF Implementation (Node.js)

1. Create `formatSQLResult(structuredData)` – converts array of objects to markdown table
2. In SSE handler: when `event.structured_data` exists, call formatter and use output instead of raw content
3. For tables: use `| col1 | col2 |` format; limit to ~100 rows for readability

See `base-api` packages for implementation details.

---

## 2. OpenAI Model Limits & Costs

### Token Limits by Model

| Model | Context Window | Max Output | Input ($/1M) | Output ($/1M) |
|-------|----------------|------------|--------------|---------------|
| gpt-5.2-pro | 400,000 | 16,384 | $21.00 | $168.00 |
| gpt-5.2 | 400,000 | 16,384 | $1.75 | $14.00 |
| gpt-4o | 128,000 | 16,384 | $2.50 | $10.00 |
| gpt-4o-mini | 128,000 | 16,384 | $0.15 | $0.60 |
| gpt-3.5-turbo | 16,385 | 4,096 | $0.50 | $1.50 |

*Prices as of January 2026. Check [OpenAI Pricing](https://openai.com/api/pricing/) for updates.*

### Common Causes of Token Overflow

1. **SQL Agent schema** – Full table schemas for 122 tables can exceed 300K tokens. Reduce `sample_rows_in_table_info` or use `include_tables`.
2. **Large query results** – Always use `LIMIT`. Configure `MAX_QUERY_ROWS`.
3. **Long conversation history** – Truncate or summarize old messages.

### Environment Variables

```bash
OPENAI_MODEL=gpt-4o-mini
MAX_OUTPUT_TOKENS=4000
MAX_QUERY_ROWS=100
SQL_SAMPLE_ROWS=2
MAX_CONVERSATION_TOKENS=50000
```

### Cost Optimization

- Use **gpt-4o-mini** (current default) for classification and RAG
- Reduce schema size (fewer tables, fewer sample rows)
- Implement dynamic table loading where possible
- For zero API cost: use **Ollama** when running on our own infrastructure (see Cost Estimation below)

---

## 3. Cost Estimation (Presentation Reference)

This section supports capacity planning and presentations. Query cost depends on complexity and the LLM provider/model.

### Query Token Ranges

Current observed usage per request (input + output, approximate):

| Complexity | Tokens per query | Typical use |
|------------|------------------|-------------|
| **Simple** | ~500 tokens       | Single-step classification, short RAG answer, simple SQL |
| **Medium** | ~1,000 tokens     | Multi-table SQL, RAG with more context |
| **Hard**   | ~1,500–2,000 tokens | Complex SQL with joins, correction loops, long context |

*Actual usage varies with conversation length, schema size, and retries.*

### Cost by Model (OpenAI)

Prices per 1M tokens (input / output). *Check [OpenAI Pricing](https://openai.com/api/pricing/) for current values.*

| Model | Context | Input ($/1M) | Output ($/1M) | Simple (~500 tok) | Hard (~2000 tok) |
|-------|---------|--------------|---------------|-------------------|------------------|
| **gpt-4o-mini** ⭐ | 128K | $0.15 | $0.60 | ~\$0.0002 | ~\$0.0008 |
| gpt-5.2 | 400K | $1.75 | $14.00 | ~\$0.003 | ~\$0.011 |
| gpt-4o | 128K | $2.50 | $10.00 | ~\$0.003 | ~\$0.012 |
| gpt-5.2-pro | 400K | $21.00 | $168.00 | ~\$0.03 | ~\$0.13 |
| gpt-3.5-turbo | 16K | $0.50 | $1.50 | ~\$0.0005 | ~\$0.002 |

**⭐ gpt-4o-mini** is the **current default** in production (`OPENAI_MODEL=gpt-4o-mini`). **gpt-5.2** and **gpt-5.2-pro** offer larger context (400K) and stronger reasoning; use them when quality or agentic tasks justify the higher cost.

*Simple/Hard estimates assume a 70% input / 30% output mix.*

### Embedding Tokens & Cost (RAG)

Embeddings are used for **RAG** (vector search over docs). When using **OpenAI**, the default model is **text-embedding-3-small**.

| Model | Price ($/1M tokens) | Typical use |
|-------|---------------------|-------------|
| **text-embedding-3-small** ⭐ | $0.020 | Default; RAG query + document indexing |
| text-embedding-3-large | $0.130 | Higher quality, higher cost |
| text-embedding-ada-002 | $0.100 | Legacy |

**Token ranges:**

- **Per RAG query**: the user question is embedded once (~10–100 tokens depending on length).
- **Document indexing**: one-time or periodic; total tokens depend on corpus size (e.g. tens of thousands of tokens for a few hundred chunks).

**Example (from runtime stats):**

- ~38,000 embedding tokens → **~\$0.0008** (e.g. indexing run or multiple RAG queries).
- **Cache**: embedding service uses a disk cache; repeated identical texts (e.g. same query or same chunks) do not call the API again, so cache hits cost **\$0**.

**With Ollama:** set `OLLAMA_EMBEDDING_MODEL` (e.g. `all-MiniLM-L6-v2`); embeddings use **sentence-transformers** locally, so **\$0** embedding API cost when using `LLM_PROVIDER=ollama`.

### Ollama (No API Cost on Our Infra)

When the agent runs with **Ollama** on our own infrastructure, **there is no per-token API cost**:

| Option | Cost | When to use |
|--------|------|-------------|
| **Ollama** (self-hosted) | **$0** API cost | Offline, air-gapped, or cost-sensitive deployments; dev/staging |
| OpenAI (gpt-4o-mini) | See table above | Production when cloud LLM is acceptable |

**Configuration** (`.env`):

```bash
# Use Ollama (no OpenAI charges)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434   # or your internal Ollama server
OLLAMA_MODEL=llama3                      # or codellama, mistral, etc.
OLLAMA_EMBEDDING_MODEL=all-MiniLM-L6-v2  # sentence-transformers, local
```

**Notes for presentations:**

- **Default production stack**: OpenAI **gpt-4o-mini** — low cost, 128K context, good for SQL/RAG/classification.
- **Zero-cost option**: **Ollama** on our infra — same integration (BFF, SSE, structured_data), no usage-based fees; ideal for dev or locked-down environments.
- **Scaling**: At ~500–2000 tokens per query, gpt-4o-mini stays in the sub-cent range per request; Ollama adds no marginal token cost.
