# OpenAI Model Limits and Costs Guide

## Overview
This document explains token limits, costs, and configuration options for OpenAI models used in the FSIA AI Agent system.

## Token Limits by Model

| Model | Context Window | Max Output Tokens | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best For |
|-------|---------------|-------------------|---------------------------|----------------------------|----------|
| **gpt-4o** | 128,000 | 16,384 | $2.50 | $10.00 | Complex reasoning, large documents |
| **gpt-4o-mini** | 128,000 | 16,384 | $0.150 | $0.600 | Cost-effective general tasks |
| **gpt-4-turbo** | 128,000 | 4,096 | $10.00 | $30.00 | Advanced reasoning (legacy) |
| **gpt-3.5-turbo** | 16,385 | 4,096 | $0.50 | $1.50 | Simple tasks, fast responses |
| **o1-preview** | 128,000 | 32,768 | $15.00 | $60.00 | Extended reasoning tasks |
| **o1-mini** | 128,000 | 65,536 | $3.00 | $12.00 | STEM reasoning, coding |

*Prices as of January 2026. Check [OpenAI Pricing](https://openai.com/api/pricing/) for updates.*

## Understanding Token Limits

### Context Window
The **context window** is the total number of tokens the model can process in a single request:
```
Total Tokens = Input Tokens + Output Tokens + Function/Tool Tokens
```

### Your Error Breakdown
```
Error: context_length_exceeded
- Model: gpt-4o-mini (128,000 token limit)
- Your usage: 310,978 tokens
  - Messages: 310,670 tokens
  - Functions: 308 tokens
- Overflow: 182,978 tokens over limit
```

## Common Causes of Token Overflow

### 1. SQL Agent Verbose Output
**Problem**: SQL agent includes full table schemas and sample rows for all accessible tables.
```python
# With 122 tables and 3 sample rows each:
# Estimated tokens: ~2,000-5,000 per table
# Total: 244,000 - 610,000 tokens just for schema!
```

**Solutions**:
- Reduce `sample_rows_in_table_info` (currently 3)
- Use `include_tables` to only load relevant tables
- Increase `SQL_AGENT_MAX_ITERATIONS` budget carefully

### 2. Large Query Results
**Problem**: Returning thousands of rows from database.
```sql
-- BAD: Returns 10,000+ rows
SELECT * FROM secure_workorder;

-- GOOD: Limited result set
SELECT * FROM secure_workorder LIMIT 50;
```

**Solutions**:
- Always use `LIMIT` clauses
- Configure `MAX_QUERY_ROWS` environment variable

### 3. Long Conversation History
**Problem**: Each message in the conversation adds to context.
```
Message 1: 500 tokens
Message 2: 800 tokens
Message 3: 1,200 tokens
...
Message 50: 65,000+ tokens accumulated
```

**Solutions**:
- Implement conversation summarization
- Truncate old messages
- Use `MAX_CONVERSATION_TOKENS` limit

## Configuration Options

### Environment Variables

```bash
# Model Selection
OPENAI_MODEL=gpt-4o-mini              # Which model to use
OPENAI_TEMPERATURE=0.1                # Response randomness (0-2)

# Token Limits
MAX_CONTEXT_TOKENS=120000             # Max total tokens (leave buffer below model limit)
MAX_OUTPUT_TOKENS=4000                # Max tokens in model response
MAX_QUERY_ROWS=100                    # Max rows returned from SQL queries

# SQL Agent Configuration
SQL_AGENT_MAX_ITERATIONS=15           # Max reasoning steps
SQL_SAMPLE_ROWS=2                     # Rows per table in schema (reduce for large DBs)
SQL_MAX_TABLES_IN_CONTEXT=20          # Max tables to include in schema

# Conversation Management
MAX_CONVERSATION_MESSAGES=10          # Max messages to keep in history
MAX_CONVERSATION_TOKENS=50000         # Max tokens in conversation history
```

### Token Budget Planning

For `gpt-4o-mini` (128K context):
```
Safe Budget Allocation:
├── System Prompt: ~500 tokens
├── Table Schema: ~60,000 tokens (20 tables × 3,000 avg)
├── Conversation History: ~30,000 tokens (10 messages)
├── Current Query: ~500 tokens
├── Agent Reasoning: ~15,000 tokens (15 iterations × 1,000 avg)
├── Output Buffer: ~4,000 tokens
└── Safety Buffer: ~18,000 tokens (15% reserve)
Total: ~128,000 tokens ✅
```

If you have 122 tables:
```
Problematic Allocation:
├── Table Schema: ~366,000 tokens (122 tables × 3,000 avg) ❌
└── Other: ~50,000 tokens
Total: ~416,000 tokens (3.25x over limit!)
```

## Optimization Strategies

### 1. Reduce Schema Size
```python
# sql_tool.py
self.db = SQLDatabase(
    engine=self.engine,
    ignore_tables=excluded_tables,
    view_support=True,
    sample_rows_in_table_info=1,  # Reduce from 3 to 1
    max_string_length=100,        # Truncate long strings
)
```

### 2. Dynamic Table Loading
Only load tables relevant to the query:
```python
# Instead of loading all 122 tables
# Analyze query first, load only needed tables
relevant_tables = analyze_query_for_tables(user_query)
db = SQLDatabase(engine=engine, include_tables=relevant_tables)
```

### 3. Use Smaller Model for Simple Tasks
```python
# Classification → gpt-4o-mini (cheap, fast)
# SQL Generation → gpt-4o (better at SQL)
# RAG → gpt-4o-mini (sufficient for retrieval)
```

### 4. Implement Streaming Truncation
```python
if token_count > MAX_QUERY_ROWS * 50:  # Estimate 50 tokens/row
    result = result[:MAX_QUERY_ROWS]
    result.append("... (results truncated)")
```

## Cost Optimization

### Current Setup Cost Estimate
```
Scenario: 100 queries/day with gpt-4o-mini
Average tokens per query: 50,000 (input) + 2,000 (output)

Daily cost:
- Input: 100 × 50,000 / 1,000,000 × $0.150 = $0.75
- Output: 100 × 2,000 / 1,000,000 × $0.600 = $0.12
- Total: $0.87/day = $26/month
```

### Cost Comparison
Same workload across models:
- **gpt-4o-mini**: $26/month ✅ Recommended
- **gpt-4o**: $437/month (17x more expensive)
- **gpt-3.5-turbo**: $143/month (slower, smaller context)

### When to Upgrade Models
- **Stick with gpt-4o-mini**: General queries, simple SQL, most RAG tasks
- **Upgrade to gpt-4o**: Complex multi-join SQL, advanced reasoning, accuracy critical
- **Use o1-mini**: Code generation, mathematical problems, logic puzzles

## Monitoring Token Usage

### Add Token Tracking
```python
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = agent.query(question)
    print(f"Tokens used: {cb.total_tokens}")
    print(f"Cost: ${cb.total_cost:.4f}")
```

### Log Token Metrics
```python
logger.info(f"Query tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
logger.warning(f"High token usage: {total_tokens} tokens (threshold: {MAX_CONTEXT_TOKENS})")
```

## Troubleshooting

### Error: `context_length_exceeded`
1. Check current model's limit (gpt-4o-mini = 128K)
2. Reduce `SQL_SAMPLE_ROWS` from 3 to 1
3. Reduce `SQL_MAX_TABLES_IN_CONTEXT` from 122 to 20
4. Increase `SQL_AGENT_MAX_ITERATIONS` limit if needed
5. Add `LIMIT` clauses to all queries
6. Consider upgrading to o1-mini (128K context, better reasoning)

### Error: `rate_limit_exceeded`
```
Tier 1: 500 requests/min, 30,000 tokens/min
Tier 2: 5,000 requests/min, 450,000 tokens/min
```
**Solutions**: Add retry logic, implement request queuing, upgrade tier

### High Costs
1. Switch expensive models to gpt-4o-mini
2. Cache frequent queries
3. Reduce sample rows and context
4. Implement result pagination

## Recommended Configuration

### For Production (Cost-Optimized)
```bash
OPENAI_MODEL=gpt-4o-mini
MAX_CONTEXT_TOKENS=120000
MAX_OUTPUT_TOKENS=4000
SQL_SAMPLE_ROWS=1
SQL_MAX_TABLES_IN_CONTEXT=20
MAX_QUERY_ROWS=100
```

### For Development (Quality-Optimized)
```bash
OPENAI_MODEL=gpt-4o
MAX_CONTEXT_TOKENS=120000
MAX_OUTPUT_TOKENS=8000
SQL_SAMPLE_ROWS=3
SQL_MAX_TABLES_IN_CONTEXT=50
MAX_QUERY_ROWS=500
```

## References
- [OpenAI Models Documentation](https://platform.openai.com/docs/models)
- [Token Counting Guide](https://platform.openai.com/tokenizer)
- [API Limits Documentation](https://platform.openai.com/docs/guides/rate-limits)
- [Pricing Calculator](https://openai.com/api/pricing/)
