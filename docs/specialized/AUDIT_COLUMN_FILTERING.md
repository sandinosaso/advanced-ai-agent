# Audit Column Filtering Fix

## Problem Statement

The SQL agent was generating incorrect join paths by using audit columns (`createdBy`, `updatedBy`) as bridge relationships, resulting in Cartesian products and incorrect query results.

### Example of the Problem

**Incorrect SQL (before fix)**:
```sql
SELECT workOrder.*
FROM workOrder
JOIN user ON workOrder.createdBy = user.id
JOIN inspection ON inspection.createdBy = user.id  -- WRONG! Creates Cartesian product
```

This creates a Cartesian product because:
- Multiple `workOrder` records may have the same `createdBy` user
- Multiple `inspection` records may have the same `createdBy` user  
- The join connects unrelated records that happen to share the same creator

**Correct SQL (after fix)**:
```sql
SELECT workOrder.*
FROM workOrder
JOIN inspectionTemplateWorkOrder ON workOrder.id = inspectionTemplateWorkOrder.workOrderId
JOIN inspection ON inspectionTemplateWorkOrder.id = inspection.inspectionTemplateWorkOrderId
```

## Root Cause

The join graph (`join_graph_merged.json`) includes foreign key relationships for audit columns:
- `workOrder.createdBy → user.id`
- `inspection.createdBy → user.id`
- `workOrder.updatedBy → user.id`
- etc.

While these are valid foreign keys in the database, they are **metadata relationships** for tracking record creation/updates, not **semantic relationships** for data retrieval.

The LLM path planner was treating these as valid join paths, leading to incorrect join logic.

## Solution

Filter out audit column relationships **at the source** when loading the join graph, before they reach any component.

### Implementation

1. **Defined audit columns to exclude** (`sql_graph_agent.py`):
```python
AUDIT_COLUMNS = {'createdBy', 'updatedBy', 'createdAt', 'updatedAt'}
```

2. **Filter relationships when loading the join graph** (`load_join_graph()` function):
```python
def load_join_graph() -> Dict[str, Any]:
    """Filter out audit column relationships at load time."""
    with open(str(JOIN_GRAPH_PATH), "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    # Filter out audit column relationships from join_graph_merged.json
    original_count = len(graph["relationships"])
    graph["relationships"] = [
        r for r in graph["relationships"]
        if r["from_column"] not in AUDIT_COLUMNS
    ]
    filtered_count = original_count - len(graph["relationships"])
    
    logger.info(f"Loaded join graph: {len(graph['tables'])} tables, "
                f"{len(graph['relationships'])} relationships "
                f"(filtered {filtered_count} audit column relationships)")
    
    return graph
```

3. **All components automatically use filtered relationships**:
   - ✅ Path finder (Dijkstra) - initialized with filtered graph
   - ✅ Bridge detection - uses filtered relationships
   - ✅ Direct relationship selection - uses filtered relationships
   - ✅ Suggested paths - computed from filtered graph
   - ✅ LLM prompts - only see non-audit relationships

4. **Removed workarounds**:
   - Reverted `action_item` definition in `domain_registry.json` (removed `tables` array)
   - Simplified bridge detection from two-pass to single-pass

## Benefits

### 1. Correct Join Paths
The path finder (Dijkstra algorithm) now only considers semantic relationships, discovering the correct bridge tables naturally:
- `workOrder → inspectionTemplateWorkOrder → inspection`

### 2. Cleaner Separation of Concerns
- **Domain Registry**: Maps business terms to filter locations only
- **Path Finder**: Discovers semantic table relationships
- **Join Planner**: Plans optimal join sequences

### 3. Prevents Future Issues
Any query that might incorrectly use audit columns is now fixed automatically. No need for per-query workarounds.

### 4. Simpler Code
- Single-pass bridge detection (removed two-pass workaround)
- Domain registry focused on term resolution (removed join path hints)
- One filter at the source prevents issues downstream

## Design Decision: Why Filter vs. Ranking?

### Alternative Considered: Semantic Ranking
We could have kept audit columns but ranked them lower in path finding:
```python
# Assign lower confidence to audit columns
if rel["from_column"] in AUDIT_COLUMNS:
    rel["confidence"] *= 0.1  # Deprioritize
```

### Why We Chose Filtering Instead

1. **Audit columns are never correct for joins**
   - They represent metadata, not data relationships
   - No valid use case for joining tables via `createdBy`

2. **Simpler implementation**
   - Clear binary decision: exclude or include
   - No need to tune ranking weights

3. **Better performance**
   - Fewer relationships for Dijkstra to consider
   - Smaller prompts for LLM

4. **Clearer semantics**
   - Join graph represents "how to connect data"
   - Audit columns represent "who/when modified record"

## Testing

### Test Query
```
"Find me the work orders that have an inspection on a crane where we found action items"
```

### Expected Behavior
1. **Table Selection**:
   - LLM selects: `workOrder`, `asset` (for crane)
   - Domain adds: `inspectionQuestionAnswer` (for action_item)
   - Path finder discovers: `inspection`, `inspectionTemplateWorkOrder` (bridges)

2. **Join Path**:
```
workOrder.id = inspectionTemplateWorkOrder.workOrderId
inspectionTemplateWorkOrder.id = inspection.inspectionTemplateWorkOrderId  
inspection.id = inspectionQuestionAnswer.inspectionId
inspectionTemplateWorkOrder.assetId = asset.id
```

3. **Final SQL**:
```sql
SELECT secure_workorder.*
FROM secure_workorder
JOIN inspectionTemplateWorkOrder ON secure_workorder.id = inspectionTemplateWorkOrder.workOrderId
JOIN inspection ON inspectionTemplateWorkOrder.id = inspection.inspectionTemplateWorkOrderId
JOIN inspectionQuestionAnswer ON inspection.id = inspectionQuestionAnswer.inspectionId
JOIN asset ON inspectionTemplateWorkOrder.assetId = asset.id
WHERE (asset.name LIKE '%crane%' OR asset.manufacturer LIKE '%crane%' OR asset.modelNumber LIKE '%crane%')
  AND inspectionQuestionAnswer.isActionItem = true
LIMIT 100;
```

## Edge Cases

### What if a query legitimately needs to filter by creator?

If a query asks "Find work orders created by user X", the audit columns should be used in the **WHERE clause**, not as JOIN conditions:

```sql
SELECT workOrder.*
FROM workOrder
WHERE workOrder.createdBy = :userId
```

The domain ontology layer or direct WHERE clause generation handles this case, not the join planner.

### What about other metadata columns?

Other common metadata patterns to consider filtering:
- `deletedAt`, `deletedBy` (soft deletes)
- `versionId`, `revisionNumber` (versioning)
- `tenantId` (multi-tenancy, though this might be needed for RLS)

For now, we filter the most common audit columns. Additional patterns can be added to `AUDIT_COLUMNS` as needed.

## Additional Improvements

### 1. Case-Insensitive Matching
Domain term matching now uses `LOWER()` for case-insensitive comparisons:
```sql
-- Before: Case-sensitive (Bulbasaur != bulbasaur)
asset.name LIKE '%Bulbasaur%'

-- After: Case-insensitive (matches all variations)
LOWER(asset.name) LIKE '%bulbasaur%'
```

This ensures terms like "Crane", "crane", "CRANE" all match correctly.

### 2. Dynamic Examples (No Overfitting)
The domain term extraction prompt now generates examples dynamically from the first 3 terms in the registry:

**Before (hardcoded)**:
```
Examples:
- "Find cranes" → ["crane"]
- "Show me action items" → ["action_item"]
```

**After (dynamic)**:
```python
# Generated from registry terms
example_terms = known_terms[:3]
examples = [f'"Find {term}s" → ["{term}"]' for term in example_terms]
```

This prevents overfitting to specific terms and ensures the system works generically for all domain terms, including new ones like "bulbasaur".

### 3. Enhanced Duplicate Join Detection
The `_deduplicate_joins` method now detects both exact duplicates AND same table joined multiple times:

**Problem**:
```sql
JOIN secure_workorder ON secure_workorder.customerId = secure_customer.id
JOIN secure_workorder ON secure_workorder.customerLocationId = secure_customerlocation.id
-- Error: Not unique table/alias 'secure_workorder'
```

**Solution**:
- Track both exact JOIN lines AND table names
- Remove duplicate table joins (keeps first occurrence)
- Log warnings for removed duplicates

### 4. Correction Agent Instructions
Added specific instructions for "Not unique table/alias" errors:
- Identifies when same table is joined multiple times
- Instructs LLM to keep only the most direct path
- Suggests using WHERE clause for multiple conditions instead

## Related Files

- [`api-ai-agent/src/agents/sql_graph_agent.py`](api-ai-agent/src/agents/sql_graph_agent.py) - Main implementation
- [`api-ai-agent/src/utils/domain_ontology.py`](api-ai-agent/src/utils/domain_ontology.py) - Case-insensitive matching and dynamic examples
- [`api-ai-agent/artifacts/domain_registry.json`](api-ai-agent/artifacts/domain_registry.json) - Reverted workarounds
- [`api-ai-agent/src/utils/path_finder.py`](api-ai-agent/src/utils/path_finder.py) - Dijkstra algorithm (benefits from filtered relationships)

## Commit Message

```
fix(sql-agent): filter audit columns from join planning

The LLM was incorrectly using audit columns (createdBy, updatedBy) as
bridge relationships, causing Cartesian products. Now filter these
columns at the source in _filter_relationships, forcing the path finder
to use semantic relationships instead.

- Add AUDIT_COLUMNS constant and filtering logic
- Revert domain registry workarounds (action_item tables array)
- Simplify bridge detection from two-pass to single-pass
- Add documentation in AUDIT_COLUMN_FILTERING.md

Fixes incorrect joins like:
  workOrder → user → inspection (WRONG)
Now generates correct joins:
  workOrder → inspectionTemplateWorkOrder → inspection (CORRECT)
```
