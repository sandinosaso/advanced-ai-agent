# Template-Instance Scoping Constraints

## Problem Statement

When querying form-based data (inspections, safety, service) that includes questions and answers, a common SQL error occurs: answers from **all executions** that use the same template are returned, not just answers from the **specific execution instance** being queried.

### Example: Inspection Questions

**Incorrect SQL** (missing constraint):
```sql
SELECT 
    inspection.id,
    inspectionQuestion.content AS question,
    inspectionQuestionAnswer.content AS answer
FROM inspection
JOIN inspectionTemplateWorkOrder ON inspection.inspectionTemplateWorkOrderId = inspectionTemplateWorkOrder.id
JOIN inspectionTemplate ON inspectionTemplateWorkOrder.inspectionTemplateId = inspectionTemplate.id
JOIN inspectionSection ON inspectionTemplate.id = inspectionSection.inspectionTemplateId
JOIN inspectionQuestionGroup ON inspectionSection.id = inspectionQuestionGroup.inspectionSectionId
JOIN inspectionQuestion ON inspectionQuestionGroup.id = inspectionQuestion.inspectionQuestionGroupId
JOIN inspectionQuestionAnswer ON inspectionQuestion.id = inspectionQuestionAnswer.inspectionQuestionId
WHERE inspection.id = '82E9F8EA-7A8F-4715-97EF-FBBEF289E77C'
LIMIT 100;
```

**Result**: Returns the same question multiple times with answers from different inspections that used the same template.

**Why this happens**:
- The join `inspectionQuestionAnswer ON inspectionQuestion.id = inspectionQuestionAnswer.inspectionQuestionId` connects the question to **all answers ever given for that question** across every inspection.
- We're missing the constraint that binds answers to the specific inspection instance.

---

## Root Cause

This is a **template-instance pattern**:

- **Templates** define structure (questions, sections, groups)
- **Instances** define state (specific inspection execution, answers)

The database has two relationships for `inspectionQuestionAnswer`:
1. `inspectionQuestionAnswer.inspectionQuestionId → inspectionQuestion.id` (which question)
2. `inspectionQuestionAnswer.inspectionId → inspection.id` (which inspection execution)

Both must be enforced when joining to ensure answers are scoped to the correct instance.

---

## Solution

Add **required_join_constraints** to the domain registry for terms that query template-instance data.

### Correct SQL

```sql
JOIN inspectionQuestionAnswer 
  ON inspectionQuestion.id = inspectionQuestionAnswer.inspectionQuestionId
 AND inspectionQuestionAnswer.inspectionId = inspection.id
```

Or equivalently (for INNER JOIN):

```sql
JOIN inspectionQuestionAnswer 
  ON inspectionQuestion.id = inspectionQuestionAnswer.inspectionQuestionId
WHERE 
    inspection.id = '82E9F8EA-7A8F-4715-97EF-FBBEF289E77C'
    AND inspectionQuestionAnswer.inspectionId = inspection.id
```

---

## Implementation

### 1. Registry Schema

In `domain_registry.json`, add `required_join_constraints` under `resolution.primary` (or term-level):

```json
"inspection_questions_and_answers": {
  "entity": "inspection_form_questions_and_answers",
  "description": "...",
  "resolution": {
    "primary": {
      "tables": [...],
      "required_join_constraints": [
        {
          "table": "inspectionQuestionAnswer",
          "conditions": [
            "inspectionQuestionAnswer.inspectionId = inspection.id"
          ],
          "note": "Answers must be scoped to the same inspection instance"
        }
      ]
    }
  }
}
```

**Fields**:
- `table`: The table whose join needs the additional constraint
- `conditions`: List of SQL condition strings (e.g. `"tableA.colX = tableB.colY"`)
- `note` (optional): Human-readable explanation

### 2. Agent Integration

The SQL agent reads `required_join_constraints` from the registry and:

1. **Prompt injection** (`_build_domain_join_constraint_instructions`): Tells the LLM to include the constraint when joining that table.
2. **Safety net** (`_inject_domain_join_constraints`): Adds the constraint to the WHERE clause if the LLM didn't include it.

Both layers ensure the constraint is enforced.

---

## Patterns Where This Applies

### Inspection Forms
- **Term**: `inspection_questions_and_answers`
- **Constraint**: `inspectionQuestionAnswer.inspectionId = inspection.id`
- **Why**: Answers are scoped to a specific inspection execution

### Safety Forms
- **Term**: `safety_questions`
- **Constraint**: `safetyQuestionAnswer.safetyId = safety.id`
- **Why**: Answers are scoped to a specific safety execution

### Service Forms
- **Term**: `service_questions`
- **Constraint**: `serviceQuestionAnswer.serviceId = service.id`
- **Why**: Answers are scoped to a specific service execution

---

## When to Use This Pattern

Use `required_join_constraints` when:

1. **Dual-parent tables**: A table has two foreign keys (e.g. `inspectionQuestionAnswer` has `inspectionQuestionId` and `inspectionId`)
2. **Template-instance relationship**: One FK points to template structure, one points to execution instance
3. **Cartesian product risk**: Joining via only one FK creates a cross-product across all instances

### Detection Heuristic

If you see:
- Same question/item repeated multiple times in results
- Answers from different executions mixed together
- Query returns more rows than expected

Check if the answer table has both:
- FK to the question/item (template structure)
- FK to the execution instance (state)

If both exist and both parent tables are in the query, add a `required_join_constraints` entry.

---

## Architecture Notes

### Why Not Encode in the Join Graph?

The join graph reflects **schema relationships** (foreign keys). Both relationships are valid:
- `inspectionQuestionAnswer → inspectionQuestion` (valid FK)
- `inspectionQuestionAnswer → inspection` (valid FK)

The constraint that "both must be used together" is a **domain rule**, not a schema rule. It belongs in the domain registry, not the join graph.

### Why Not Automatic Detection?

We could detect dual-parent tables automatically and always enforce both joins. However:
- **False positives**: Not all dual-parent tables need both joins (e.g. audit columns like `createdBy` pointing to `user`)
- **Debuggability**: Explicit registry entries make the constraint visible and documented
- **Flexibility**: Some queries might intentionally want all answers for a question across all inspections

Explicit per-term constraints are safer and more maintainable.

---

## Example Flow

**User query**: "Show me the questions and answers for inspection 82E9F8EA"

**Step 1**: Domain extraction identifies `inspection_questions_and_answers`

**Step 2**: Resolution reads `required_join_constraints` from registry

**Step 3**: SQL generation prompt includes:
```
REQUIRED JOIN CONSTRAINTS (template-instance scoping):
When joining these tables, you MUST include these conditions:
  - inspectionQuestionAnswer: inspectionQuestionAnswer.inspectionId = inspection.id  # Answers must be scoped to the same inspection instance
```

**Step 4**: LLM generates SQL with the constraint in ON or WHERE clause

**Step 5**: Safety net (`_inject_domain_join_constraints`) verifies constraint is present; adds to WHERE if missing

**Result**: SQL returns only answers for the specific inspection, not all answers for those questions.

---

## Comparison with Domain Filters

| Feature | Domain Filters | Join Constraints |
|---------|---------------|------------------|
| **Purpose** | Business logic (e.g. isActionItem = true) | Template-instance scoping (e.g. answer.inspectionId = inspection.id) |
| **Registry key** | `filters` | `required_join_constraints` |
| **Applied to** | WHERE clause | ON or WHERE clause |
| **Example** | "Find action items" → isActionItem = true | "Questions for this inspection" → answer.inspectionId = inspection.id |

Both are declarative, registry-driven, and have prompt + injection layers.

---

## Testing

Test that:
1. Registry parsing: `inspection_questions_and_answers` resolution includes `join_constraints`
2. Prompt includes constraint text when domain term is active
3. Injection adds constraint to WHERE when missing
4. End-to-end: query for "questions for inspection X" returns only answers for that inspection

---

## Future Enhancements

### 1. Automatic Detection (Optional)

Detect dual-parent tables automatically:
```python
if table has two FKs and both parent tables are in selected_tables:
    add constraint for both FKs
```

Pros: No registry entries needed  
Cons: False positives, less debuggable

### 2. Pattern Library (Optional)

Define reusable patterns:
```json
"patterns": {
  "template_instance": {
    "description": "Bind answers to execution instance",
    "applies_to": ["inspection", "safety", "service"],
    "constraint_template": "{answer_table}.{instance_fk} = {instance_table}.id"
  }
}
```

Then reference patterns in term definitions instead of repeating constraints.

---

## Related Documentation

- [Domain Ontology Implementation](DOMAIN_ONTOLOGY_IMPLEMENTATION.md) - How domain terms are extracted and resolved
- [Audit Column Filtering](AUDIT_COLUMN_FILTERING.md) - Similar pattern for filtering metadata relationships
- [Architecture](../ARCHITECTURE.md) - Overall system architecture
