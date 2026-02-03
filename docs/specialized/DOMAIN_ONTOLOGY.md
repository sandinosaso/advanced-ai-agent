# Domain Ontology

## Overview

The Domain Ontology maps business concepts ("crane", "action item") to database schema locations. It enables natural language queries to resolve correctly to SQL constructs. This document covers the ontology, registry, and template-instance scoping.

---

## 1. Core Components

### Module Structure

- **`src/domain/ontology/`** – Main module
  - `__init__.py` – `DomainOntology` class
  - `extractor.py` – `DomainTermExtractor` (LLM + two-phase)
  - `resolver.py` – `DomainTermResolver` (term → schema)
  - `formatter.py` – `format_domain_context()`, `build_where_clauses()`
  - `models.py` – `DomainResolution`
- **`artifacts/domain_registry.json`** – Business vocabulary

### Configuration

**`src/config/settings.py`**:
```python
domain_registry_path: str = "artifacts/domain_registry.json"
domain_extraction_enabled: bool = True
```

### SQL Agent Integration

**`src/agents/sql/`** – Workflow nodes:
- `nodes/domain.py` – `extract_domain_terms_node`, `resolve_domain_terms_node`
- `nodes/table_selector.py` – Uses domain context for table selection
- `nodes/join_planner.py` – Domain filter hints
- `nodes/sql_generator.py` – Injects WHERE clauses from domain resolutions

**Workflow order:**
```
extract_domain_terms → resolve_domain_terms → select_tables →
filter_relationships → plan_joins → generate_sql → validate_sql →
execute → finalize
```

---

## 2. Two-Phase Extraction

### Pass 1: Atomic Signals (LLM)

Extracts single-concept signals from the question: `["crane", "inspection"]`, `["inspection", "question"]`.

**Negative rule**: If the question does NOT mention "question", "questions", "answer", "form", "checklist" → do NOT return compound terms like `inspection_questions`, `safety_questions`.

### Pass 2: Compound Eligibility (Deterministic)

Uses `compute_final_registry_terms()` to filter:
- Atomic terms: included if in atomic signals
- Compound terms (e.g. `inspection_questions`): require `requires_explicit_terms` and `requires_atomic_signals` from registry

---

## 3. Registry Format

### Basic Term

```json
{
  "crane": {
    "entity": "asset",
    "resolution": {
      "primary": {
        "table": "assetType",
        "column": "name",
        "match_type": "text_search",
        "confidence": 0.9
      }
    }
  }
}
```

### Match Types

- `text_search` / `semantic` – `LIKE '%term%'` (case-insensitive via `LOWER()`)
- `boolean` – `column = true/false`
- `structural` – Table grouping only (no filters)

### Compound Term with Gates

```json
{
  "inspection_questions": {
    "entity": "inspection_form_questions",
    "requires_explicit_terms": ["question", "questions", "answer", "form", "checklist"],
    "requires_atomic_signals": ["inspection"],
    "resolution": {
      "primary": {
        "tables": ["inspection", "inspectionQuestion", "..."],
        "match_type": "structural",
        "confidence": 0.95
      }
    }
  }
}
```

---

## 4. Template-Instance Scoping

### Problem

When querying form-based data (inspections, safety, service), answers from **all executions** using the same template were returned, not just the **specific execution** queried.

**Example**: `inspectionQuestionAnswer` has:
- `inspectionQuestionId` → which question (template)
- `inspectionId` → which inspection execution (instance)

Joining only via `inspectionQuestionId` returns answers from every inspection that used that question.

### Solution: `required_join_constraints`

In `domain_registry.json`:

```json
"inspection_questions_and_answers": {
  "resolution": {
    "primary": {
      "tables": ["inspection", "inspectionQuestion", "inspectionQuestionAnswer", "..."],
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

The SQL agent injects this constraint into prompts and validates it in generated SQL.

### When to Use

- **Dual-parent tables**: A table has two FKs (e.g. `inspectionQuestionAnswer` → question and inspection)
- **Template-instance relationship**: One FK = template structure, one = execution instance
- **Cartesian product risk**: Joining via only one FK creates cross-product

---

## 5. Adding New Terms

Edit `artifacts/domain_registry.json`:

```json
{
  "your_term": {
    "entity": "your_entity",
    "description": "Description for logs",
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

No code changes needed. Run `pytest tests/test_domain_ontology.py` to validate.

---

## 6. Semantic Role System Integration

The domain ontology works together with the **semantic role system** defined in `artifacts/join_graph_manual.json`. While the domain ontology focuses on business terminology mapping, the semantic role system controls table selection and bridge table behavior.

### Semantic Roles Overview

Tables are classified by their business purpose to prevent incorrect bridge table usage:

| Role | Purpose | Bridge Behavior |
|------|---------|-----------------|
| **instance** | Entity executions/records | Normal bridge candidate |
| **template** | Schema/structure definitions | Normal bridge candidate |
| **bridge** | Many-to-many junctions | Used as bridges when needed |
| **content_child** | Child data within context | Normal bridge candidate |
| **satellite** | Auxiliary orthogonal data | **NEVER** used as bridge |
| **assignment** | Membership/assignment tracking | **NEVER** used as bridge |
| **configuration** | Permission/settings | **NEVER** used as bridge |

### Integration Points

#### 1. Table Selection
When domain terms are resolved, the semantic role influences which tables are included:
- **instance/template/bridge** tables: Included when domain term matches
- **satellite** tables: Excluded from bridge discovery
- **assignment/configuration** tables: Only included if explicitly required by domain term

#### 2. Bridge Table Discovery
The semantic role system prevents unnecessary bridges:

```python
# In find_bridge_tables()
if role in ("satellite", "assignment", "configuration"):
    # Exclude from bridge consideration
    return True
```

Example: When querying `workTime` data:
- ✅ Uses direct FK: `workTime.employeeId -> employee.id`
- ❌ Skips `employeeCrew` (role="assignment" - crew membership)
- ❌ Skips `employeeRoleWorkTimeType` (role="configuration" - permissions)

#### 3. Domain Term + Semantic Role

When a domain term like `inspection_questions_and_answers` is detected:

1. **Domain Ontology** provides:
   - Required tables: `inspection`, `inspectionQuestion`, `inspectionQuestionAnswer`
   - Required join constraints: `inspectionQuestionAnswer.inspectionId = inspection.id`
   - Filter hints: Match types, columns to filter

2. **Semantic Role System** filters:
   - ✅ Includes: `inspection` (instance), `inspectionQuestion` (content_child)
   - ❌ Excludes: `inspectionConfiguration` (satellite), `inspectionSignature` (satellite)
   - ✅ Uses bridges: `inspectionTemplateWorkOrder` (bridge) when needed

### Example: Combined Usage

**Query**: "Show me inspection questions and answers for work order #123"

**Domain Ontology Resolution**:
```json
{
  "term": "inspection_questions_and_answers",
  "tables": ["inspection", "inspectionQuestion", "inspectionQuestionAnswer"],
  "required_join_constraints": [
    "inspectionQuestionAnswer.inspectionId = inspection.id"
  ]
}
```

**Semantic Role Filtering**:
```
Selected tables with roles:
- inspection (instance) ✅
- inspectionQuestion (content_child) ✅  
- inspectionQuestionAnswer (content_child) ✅
- inspectionTemplateWorkOrder (bridge) ✅ - needed to connect to workOrder

Excluded from bridges:
- inspectionConfiguration (satellite) ❌
- inspectionCustomerSignature (satellite) ❌
```

**Result**: Clean query with only necessary tables, correctly scoped joins.

### When to Define Each

**Use Domain Ontology** (`domain_registry.json`) when:
- Mapping business terms to database concepts
- Defining required join constraints (template-instance scoping)
- Specifying filter conditions (text_search, boolean, etc.)

**Use Semantic Roles** (`join_graph_manual.json`) when:
- Preventing incorrect bridge table usage
- Marking auxiliary/orthogonal data (satellite)
- Distinguishing assignment/configuration from instance data

Both systems work together to produce accurate, efficient SQL queries.

---

## Related Files

- `src/domain/ontology/` – Core module
- `artifacts/domain_registry.json` – Registry
- `artifacts/join_graph_manual.json` – Semantic role metadata
- `src/agents/sql/nodes/domain.py` – Workflow nodes
- `src/agents/sql/planning/domain_filters.py` – Filter injection
- `src/agents/sql/planning/bridge_tables.py` – Bridge discovery with semantic roles
- `tests/test_domain_ontology.py`, `tests/test_domain_e2e.py`
