# Integration & Reference

## Overview

This document covers BFF integration (structured data → markdown) and OpenAI model limits/costs reference.

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

- `structured_data` is included in the **first token** of the `final` channel only
- If present, the BFF should convert to markdown (table or list)
- If `null`, use `content` as-is (backward compatible)

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

- Use `gpt-4o-mini` for classification and RAG
- Reduce schema size (fewer tables, fewer sample rows)
- Implement dynamic table loading where possible
