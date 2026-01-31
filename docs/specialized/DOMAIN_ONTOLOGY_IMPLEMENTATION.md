# Domain Ontology Layer Implementation

## Overview

Successfully implemented a **Domain Vocabulary Registry** that maps business concepts (like "crane", "action item") to database schema locations. This enables natural language queries to be resolved correctly to SQL constructs.

## What Was Implemented

### 1. Core Domain Ontology Module
**File:** `src/utils/domain_ontology.py`

Key components:
- `DomainOntology` class - Main registry for business vocabulary
- `DomainResolution` dataclass - Represents how terms resolve to schema
- `extract_domain_terms()` - Extract business concepts from questions using LLM
- `resolve_domain_term()` - Map concepts to tables, columns, and filters
- `format_domain_context()` - Format resolutions for prompt injection
- `build_where_clauses()` - Generate SQL WHERE clauses from resolutions

### 2. Domain Registry
**File:** `artifacts/domain_registry.json`

Contains 10 initial business terms:
- **Equipment types:** crane, forklift, hoist, truck, trailer, generator, compressor
- **Inspection concepts:** action_item, unsafe, failed_inspection

Each term includes:
- Primary resolution strategy (highest confidence)
- Secondary resolution strategies (fallback options)
- Table and column mappings
- Match types (semantic, boolean, exact)
- Confidence scores

### 3. Configuration Settings
**File:** `src/utils/config.py`

Added settings:
```python
domain_registry_enabled: bool = True
domain_registry_path: str = "artifacts/domain_registry.json"
domain_extraction_enabled: bool = True
domain_fallback_to_text_search: bool = True
```

### 4. SQL Agent Integration
**File:** `src/agents/sql_graph_agent.py`

**New State Fields:**
```python
domain_terms: List[str]  # Extracted business terms
domain_resolutions: List[Dict[str, Any]]  # Schema mappings
```

**New Workflow Nodes:**
1. `extract_domain_terms` - Extract business concepts from question
2. `resolve_domain_terms` - Map concepts to schema locations

**Modified Nodes:**
- `_select_tables` - Inject domain context, auto-include required tables
- `_plan_joins` - Include domain filter hints in join planning
- `_generate_sql` - Inject WHERE clauses based on domain resolutions

**Updated Workflow:**
```
extract_domain_terms → resolve_domain_terms → select_tables → 
filter_relationships → plan_joins → generate_sql → validate_sql → 
execute → finalize
```

### 5. Test Suite
**Files:** 
- `tests/test_domain_ontology.py` - Unit tests for domain ontology
- `tests/test_domain_validation.py` - Validation test (all checks passed ✓)

## Example Query Flow

**Question:** "Find work orders with crane inspections that have action items"

**Step 1 - Extract Domain Terms:**
```json
["crane", "action_item"]
```

**Step 2 - Resolve Terms:**
```json
{
  "crane": {
    "tables": ["asset", "assetType"],
    "filters": [{"table": "assetType", "column": "name", "operator": "ILIKE", "value": "%crane%"}],
    "confidence": 0.9
  },
  "action_item": {
    "tables": ["inspectionQuestionAnswer"],
    "filters": [{"table": "inspectionQuestionAnswer", "column": "isActionItem", "operator": "=", "value": true}],
    "confidence": 1.0
  }
}
```

**Step 3 - Generate SQL (with domain filters):**
```sql
SELECT wo.id, wo.name, a.name AS asset_name, at.name AS asset_type
FROM workOrder wo
JOIN inspection i ON wo.id = i.workOrderId
JOIN asset a ON i.assetId = a.id
JOIN assetType at ON a.assetTypeId = at.id
JOIN inspectionQuestionAnswer iqa ON i.id = iqa.inspectionId
WHERE at.name ILIKE '%crane%'
  AND iqa.isActionItem = true
LIMIT 50;
```

## Key Features

### 1. Separation of Concerns
Domain knowledge is explicit and queryable, not buried in prompts.

### 2. Scalability
Easy to extend with new business terms without retraining:
- Add new terms to `domain_registry.json`
- No code changes needed
- Supports multiple resolution strategies per term

### 3. Debuggability
Can see exactly how "crane" was resolved to schema in logs.

### 4. Logging & Improvement
- Log every domain term extraction
- Log resolution confidence scores
- Log when terms fail to resolve
- Build vocabulary over time based on user queries

### 5. Confidence Scoring
Multiple resolution strategies with fallbacks:
- Primary (highest confidence)
- Secondary (medium confidence)
- Fallback (lowest confidence)

## Usage

### Enable/Disable Domain Ontology
Set in `.env` file:
```bash
DOMAIN_REGISTRY_ENABLED=true
DOMAIN_EXTRACTION_ENABLED=true
```

### Add New Business Terms
Edit `artifacts/domain_registry.json`:
```json
{
  "your_term": {
    "entity": "your_entity",
    "description": "Your term description",
    "resolution": {
      "primary": {
        "table": "your_table",
        "column": "your_column",
        "match_type": "semantic",
        "confidence": 0.9
      }
    }
  }
}
```

### Query with Domain Terms
```python
from src.agents.sql_graph_agent import SQLGraphAgent

agent = SQLGraphAgent()
result = agent.query("Find work orders with crane inspections that have action items")
print(result)
```

## Testing

### Run Validation Test
```bash
cd api-ai-agent
python tests/test_domain_validation.py
```

### Run Unit Tests
```bash
cd api-ai-agent
pytest tests/test_domain_ontology.py -v
```

### Run End-to-End Test
```bash
cd api-ai-agent
python tests/test_domain_e2e.py
```

## Architecture Benefits

### Before Domain Ontology
- Business terms buried in prompts
- Hard to extend vocabulary
- Difficult to debug term resolution
- No confidence scoring
- Terms must be re-explained in multiple places

### After Domain Ontology
- ✅ Business vocabulary is explicit and centralized
- ✅ Easy to add new terms (just edit JSON)
- ✅ Clear audit trail of term resolution
- ✅ Confidence-based fallback strategies
- ✅ Single source of truth for business concepts
- ✅ Supports multiple resolution strategies per term
- ✅ Automatic WHERE clause injection

## Future Enhancements

### Phase 2 (Expansion)
- Add more business terms based on logged failures
- Implement semantic matching using embeddings for fuzzy matches
- Add support for multi-term concepts ("failed safety inspection")
- Add synonyms support ("unsafe" → "action_item")

### Phase 3 (Advanced)
- Auto-discover domain terms from `dynamicAttribute` keys in database
- Build confidence scoring based on query success rates
- Integrate with RAG for domain term definitions
- Support for context-dependent resolutions
- Support for temporal terms ("last month", "this year")

## Files Created

1. `src/utils/domain_ontology.py` (407 lines)
2. `artifacts/domain_registry.json` (135 lines)
3. `tests/test_domain_ontology.py` (272 lines)
4. `tests/test_domain_e2e.py` (130 lines)
5. `tests/test_domain_validation.py` (249 lines)

## Files Modified

1. `src/agents/sql_graph_agent.py` - Added domain ontology integration
2. `src/utils/config.py` - Added domain configuration settings

## Validation Results

All validation checks passed ✓

```
✓ DomainOntology class found
✓ DomainResolution dataclass found
✓ load_registry method found
✓ extract_domain_terms method found
✓ resolve_domain_term method found
✓ format_domain_context function found
✓ build_where_clauses function found
✓ Valid JSON registry with 10 terms
✓ Required terms 'crane' and 'action_item' present
✓ All configuration settings found
✓ SQL agent integration complete
✓ Test suite created
```

## Next Steps

1. **Install dependencies** (if not already done):
   ```bash
   cd api-ai-agent
   pip install -r requirements.txt
   ```

2. **Configure database** in `.env` file:
   ```bash
   DB_HOST=your_host
   DB_USER=your_user
   DB_PWD=your_password
   DB_NAME=your_database
   ```

3. **Test the implementation**:
   ```bash
   # Run validation
   python tests/test_domain_validation.py
   
   # Try example query (requires database)
   python -c "from src.agents.sql_graph_agent import SQLGraphAgent; agent = SQLGraphAgent(); print(agent.query('Find work orders with crane inspections that have action items'))"
   ```

4. **Monitor logs** to see:
   - Domain term extraction
   - Term resolution to schema
   - Automatic table inclusion
   - WHERE clause injection

5. **Extend vocabulary** by adding terms to `artifacts/domain_registry.json` as needed

## Summary

The domain ontology layer has been successfully implemented and validated. It provides a robust, scalable foundation for mapping business terminology to database schema, enabling more accurate and maintainable natural language to SQL conversion.

The implementation follows the plan exactly and includes all requested components:
- ✅ Domain vocabulary registry
- ✅ Term extraction and resolution
- ✅ SQL agent integration
- ✅ Configuration settings
- ✅ Test suite
- ✅ Documentation

The system is ready for testing with real queries once the database connection is configured.
