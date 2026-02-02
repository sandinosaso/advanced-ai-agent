# Display Attributes Troubleshooting Guide

## How to Verify It's Working

The Display Attributes system has **three stages** of operation:

### Stage 1: Table Selection ✅ (Working in your logs)
The system automatically includes template tables when needed.

**Evidence from your logs:**
```
2026-02-02 03:06:47 | INFO - Raw LLM output: ["inspection", "inspectionQuestion", "inspectionQuestionAnswer"]
2026-02-02 03:06:47 | INFO - Added template-required table for display: inspectionTemplateWorkOrder
2026-02-02 03:06:47 | INFO - Added template-required table for display: inspectionTemplate
2026-02-02 03:06:47 | INFO - Selected tables: ['inspection', 'inspectionQuestion', 'inspectionQuestionAnswer', 'inspectionTemplateWorkOrder', 'inspectionTemplate']
```

✅ **This is working!** The system detected that `inspection` needs `inspectionTemplate` for display and automatically added both `inspectionTemplateWorkOrder` and `inspectionTemplate`.

### Stage 2: Join Planning ✅ (Working in your logs)
The system includes the template tables in the join plan.

**Evidence from your logs:**
```sql
JOIN inspectionTemplateWorkOrder ON inspectionTemplateWorkOrder.id = inspection.inspectionTemplateWorkOrderId
JOIN inspectionTemplate ON inspectionTemplate.id = inspectionTemplateWorkOrder.inspectionTemplateId
```

✅ **This is working!** The joins to the template tables are being created correctly.

### Stage 3: Column Selection ⚠️ (Needs improvement)
The system should guide the LLM to SELECT human-readable columns.

**Current behavior:**
```sql
SELECT 
    inspection.id AS inspection_id,
    COUNT(inspectionQuestion.id) AS total_questions,
    ...
```

❌ **Missing**: Should also include `inspectionTemplate.name` to show which inspection type.

**Expected behavior:**
```sql
SELECT 
    inspection.id AS inspection_id,
    inspectionTemplate.name AS inspection_name,  -- ← This should be added
    COUNT(inspectionQuestion.id) AS total_questions,
    ...
```

## Why Column Selection Wasn't Working

The display attributes examples were being generated but:
1. They were placed **after** the critical rules in the prompt
2. They weren't **explicit enough** about the SELECT clause
3. For **aggregate queries** (with GROUP BY), the LLM needs stronger guidance

## What Was Fixed

### 1. Enhanced SQL Generator Prompt
Added explicit SELECT clause guidance before the examples:

```
IMPORTANT - SELECT CLAUSE GUIDANCE:
- ALWAYS include human-readable identifiers (name, firstName/lastName, description) in your SELECT
- For inspection queries: include inspectionTemplate.name to show which inspection type
- For employee queries: include firstName and lastName, not just id
- For status queries: include the status name column, not just the ID
- Even in aggregate queries, include identifying columns in SELECT and GROUP BY
```

### 2. Improved Display Columns
Updated inspection display columns to be more useful:
- Before: `["id", "noSignatureReason", "status", "date"]`
- After: `["id", "date", "status", "completedAt"]`

## Testing the Fix

### Test Query 1: Simple List
**Query**: "List inspections"

**Expected SQL**:
```sql
SELECT 
    inspection.id,
    inspection.date,
    inspection.status,
    inspectionTemplate.name AS inspection_name
FROM inspection
JOIN inspectionTemplateWorkOrder ON ...
JOIN inspectionTemplate ON ...
LIMIT 100;
```

### Test Query 2: Aggregate (Your Case)
**Query**: "List inspections and their amount of questions"

**Expected SQL**:
```sql
SELECT 
    inspection.id,
    inspectionTemplate.name AS inspection_name,  -- ← Key addition
    COUNT(inspectionQuestion.id) AS total_questions,
    COUNT(inspectionQuestionAnswer.id) AS answered_questions
FROM inspection
JOIN inspectionTemplateWorkOrder ON ...
JOIN inspectionTemplate ON ...
LEFT JOIN inspectionQuestion ON ...
LEFT JOIN inspectionQuestionAnswer ON ...
GROUP BY inspection.id, inspectionTemplate.name  -- ← Also in GROUP BY
LIMIT 20;
```

### Test Query 3: Employee
**Query**: "Show me employees"

**Expected SQL**:
```sql
SELECT 
    id,
    firstName,
    lastName,
    email
FROM employee
LIMIT 100;
```

## How to Verify After Restart

1. **Restart your API server** to load the updated code:
   ```bash
   # Stop the current server (Ctrl+C)
   # Restart it
   python scripts/run-dev.py
   ```

2. **Try the same query**:
   - "List inspections and their amount of questions"
   
3. **Check the logs** for:
   - ✅ Template tables being added (Stage 1)
   - ✅ Joins being created (Stage 2)
   - ✅ **NEW**: `inspectionTemplate.name` in the SELECT clause (Stage 3)

4. **Check the SQL output** should now include:
   ```sql
   SELECT 
       inspection.id,
       inspectionTemplate.name,  -- ← This should now appear
       COUNT(...) AS total_questions,
       ...
   ```

## Debugging Tips

### Enable Debug Logging
To see the full prompt being sent to the LLM:

1. Check logs for: `[PROMPT] generate_sql prompt:`
2. Look for the section: `IMPORTANT - SELECT CLAUSE GUIDANCE:`
3. Verify it includes: `DISPLAY COLUMN EXAMPLES:`

### Check Display Attributes Manager Initialization
Look for this in startup logs:
```
INFO - Display attributes manager initialized
```

If you see:
```
WARNING - Failed to initialize display attributes
```
Then check the registry file exists at: `artifacts/display_attributes_registry.json`

### Verify Registry Configuration
```bash
cd api-ai-agent
python3 -c "
from src.domain.display_attributes import DisplayAttributesManager
manager = DisplayAttributesManager()
print('Tables configured:', len(manager.tables_config))
print('Concepts configured:', len(manager.concepts_config))
print('Inspection config:', manager.has_configuration('inspection'))
template_rel = manager.get_template_relationship('inspection')
print('Template relationship:', template_rel is not None)
"
```

Expected output:
```
Tables configured: 80
Concepts configured: 8
Inspection config: True
Template relationship: True
```

## Common Issues

### Issue 1: Display attributes not initialized
**Symptom**: No log message about "Display attributes manager initialized"

**Solution**: Check `src/config/settings.py` has:
```python
display_attributes_enabled: bool = True
```

### Issue 2: Template tables not being added
**Symptom**: Logs don't show "Added template-required table for display"

**Solution**: Verify the registry has template_relationship configured for the table.

### Issue 3: Columns still not in SELECT
**Symptom**: Template tables are joined but columns not selected

**Solution**: 
1. Restart the server to load updated prompt
2. Check the LLM is receiving the enhanced prompt with SELECT clause guidance
3. Consider increasing the prominence of display examples in the prompt

## Next Steps

After verifying the fix works:

1. **Monitor queries** to ensure display columns are being selected
2. **Adjust prompts** if certain query patterns still don't work
3. **Extend registry** to cover more tables as needed
4. **Collect feedback** on which columns users find most useful

## Quick Reference

### Files Modified for the Fix
- `src/agents/sql/nodes/sql_generator.py` - Enhanced prompt with explicit SELECT guidance
- `artifacts/display_attributes_registry.json` - Improved inspection display columns

### Key Log Messages to Look For
```
✅ "Display attributes manager initialized"
✅ "Added template-required table for display: inspectionTemplate"
✅ SQL includes: "inspectionTemplate.name"
```
