# Display Attributes System

## Overview

The Display Attributes system provides a scalable, declarative configuration for instructing the SQL agent which human-readable columns to select by default for each table and concept. This ensures consistent, user-friendly query results without relying solely on prompt engineering.

## Problem Solved

Before this system, the SQL agent had no explicit configuration for:
- **Default display columns** per table (e.g., `employee` → `firstName, lastName` not just `id`)
- **Template-based relationships** where names come from related tables (e.g., `inspection` → `inspectionTemplate.name`)
- **Concept-specific overrides** (e.g., "workorder status" means `workOrderStatus.name`, not `workOrder.workOrderStatusId`)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Natural Language Query                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Display Attributes Registry                     │
│         (artifacts/display_attributes_registry.json)         │
│                                                              │
│  • Table display columns configuration                       │
│  • Template relationship definitions                         │
│  • Concept-specific display rules                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           DisplayAttributesManager                           │
│                                                              │
│  • Load and parse registry                                   │
│  • Resolve display columns per table/concept                 │
│  • Build prompt context                                      │
│  • Handle template relationships                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SQL Agent Workflow Integration                  │
│                                                              │
│  1. Table Selector: Include template tables                 │
│  2. Join Planner: Prioritize display joins                   │
│  3. SQL Generator: Inject display examples                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Generated SQL with Human-Readable Columns            │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Display Attributes Registry

**File**: `artifacts/display_attributes_registry.json`

A JSON configuration file defining:

#### Table Configuration
```json
{
  "tables": {
    "employee": {
      "display_columns": ["id", "firstName", "lastName", "email"],
      "primary_label": ["firstName", "lastName"],
      "description": "Always include firstName and lastName for employees"
    },
    "inspection": {
      "display_columns": ["id", "date", "status"],
      "template_relationship": {
        "template_table": "inspectionTemplate",
        "via_tables": ["inspectionTemplateWorkOrder"],
        "template_columns": ["name"],
        "description": "Inspection name comes from inspectionTemplate.name"
      }
    }
  }
}
```

#### Concept Configuration
```json
{
  "concepts": {
    "employee": {
      "tables": ["employee"],
      "display_override": {
        "employee": ["id", "firstName", "lastName"]
      },
      "description": "When asking about employees, always show firstName and lastName"
    },
    "inspection": {
      "tables": ["inspection", "inspectionTemplateWorkOrder", "inspectionTemplate"],
      "display_override": {
        "inspection": ["id", "date", "status"],
        "inspectionTemplate": ["name"]
      },
      "required_joins": [
        "inspection.inspectionTemplateWorkOrderId = inspectionTemplateWorkOrder.id",
        "inspectionTemplateWorkOrder.inspectionTemplateId = inspectionTemplate.id"
      ],
      "description": "Inspections should include the template name for context"
    }
  }
}
```

### 2. DisplayAttributesManager

**File**: `src/domain/display_attributes/__init__.py`

Core manager class that:
- Loads and parses the display attributes registry
- Resolves display columns for tables and concepts
- Handles template relationships
- Builds prompt context for SQL generation

#### Key Methods

```python
# Get display columns for a table
display_cols = manager.get_display_columns("employee")
# Returns: ["id", "firstName", "lastName", "email"]

# Get display columns with concept override
display_cols = manager.get_display_columns("employee", concept="employee")
# Returns: ["id", "firstName", "lastName"]

# Get template relationship
template_rel = manager.get_template_relationship("inspection")
# Returns: {"template_table": "inspectionTemplate", ...}

# Get all tables needed for display (including templates)
all_tables = manager.get_all_required_tables_for_display(["inspection"])
# Returns: {"inspection", "inspectionTemplateWorkOrder", "inspectionTemplate"}

# Build prompt context
context = manager.build_display_context(["employee", "workOrderStatus"])
# Returns formatted string for prompt injection
```

### 3. Data Models

**File**: `src/domain/ontology/models.py`

```python
@dataclass
class DisplayAttributes:
    """Display attributes configuration for a table"""
    table: str
    display_columns: List[str]
    primary_label: List[str]
    template_relationship: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

@dataclass
class ConceptDisplayRules:
    """Display rules for a business concept"""
    concept: str
    tables: List[str]
    display_override: Dict[str, List[str]]
    required_joins: List[str] = field(default_factory=list)
    description: Optional[str] = None
```

### 4. SQL Agent Integration

#### Table Selector (`src/agents/sql/nodes/table_selector.py`)
- Automatically includes template tables when display attributes require them
- Example: When `inspection` is selected, also includes `inspectionTemplateWorkOrder` and `inspectionTemplate`

#### Join Planner (`src/agents/sql/nodes/join_planner.py`)
- Adds hints about template relationships that need joining
- Prioritizes joins needed for display attributes

#### SQL Generator (`src/agents/sql/nodes/sql_generator.py`)
- Injects display attributes examples into the prompt
- Shows recommended columns per table
- Highlights human-readable identifiers

### 5. Configuration Settings

**File**: `src/config/settings.py`

```python
# Display Attributes Configuration
display_attributes_enabled: bool = True
display_attributes_registry_path: str = "artifacts/display_attributes_registry.json"
display_attributes_always_include_id: bool = True
display_attributes_max_columns: int = 10
```

## Current Coverage

The registry currently includes:

- **80+ tables** with display column configurations
- **8 concepts** with specialized display rules:
  - `employee`: firstName + lastName
  - `user`: firstName + lastName
  - `workorder_status`: workOrderStatus.name
  - `inspection`: inspection data + inspectionTemplate.name
  - `service`: service data + serviceTemplate.name
  - `safety`: safety data + safetyTemplate.name
  - `asset_type`: assetType.name
  - `customer_location`: customer and location names

### Template-Based Entities

Three main template patterns are configured:

1. **Inspection Pattern**
   - `inspection` → `inspectionTemplateWorkOrder` → `inspectionTemplate.name`

2. **Service Pattern**
   - `service` → `serviceTemplateWorkOrder` → `serviceTemplate.name`

3. **Safety Pattern**
   - `safety` → `safetyTemplateWorkOrder` → `safetyTemplate.name`

## Usage Examples

### Example 1: Employee Query

**Query**: "Show me employees"

**Without Display Attributes**:
```sql
SELECT id FROM employee LIMIT 100;
```

**With Display Attributes**:
```sql
SELECT id, firstName, lastName, email FROM employee LIMIT 100;
```

### Example 2: Workorder Status

**Query**: "What's the status of workorder 123?"

**Without Display Attributes**:
```sql
SELECT workOrderStatusId FROM workOrder WHERE id = 123;
-- Result: workOrderStatusId = 5 (not helpful)
```

**With Display Attributes**:
```sql
SELECT 
  workOrder.id,
  workOrder.workOrderNumber,
  workOrderStatus.name
FROM workOrder
JOIN workOrderStatus ON workOrder.workOrderStatusId = workOrderStatus.id
WHERE workOrder.id = 123;
-- Result: name = "In Progress" (human-readable)
```

### Example 3: Inspection with Template

**Query**: "List inspections from last week"

**Without Display Attributes**:
```sql
SELECT id, date FROM inspection 
WHERE date >= DATE_SUB(NOW(), INTERVAL 7 DAY);
-- Result: Just IDs and dates, no descriptive names
```

**With Display Attributes**:
```sql
SELECT 
  inspection.id,
  inspection.date,
  inspection.status,
  inspectionTemplate.name
FROM inspection
JOIN inspectionTemplateWorkOrder 
  ON inspection.inspectionTemplateWorkOrderId = inspectionTemplateWorkOrder.id
JOIN inspectionTemplate 
  ON inspectionTemplateWorkOrder.inspectionTemplateId = inspectionTemplate.id
WHERE inspection.date >= DATE_SUB(NOW(), INTERVAL 7 DAY);
-- Result: Includes template name for context
```

## Adding New Configurations

### Adding a New Table

Edit `artifacts/display_attributes_registry.json`:

```json
{
  "tables": {
    "yourTable": {
      "display_columns": ["id", "name", "description"],
      "primary_label": ["name"],
      "description": "Optional description"
    }
  }
}
```

### Adding a New Concept

```json
{
  "concepts": {
    "your_concept": {
      "tables": ["table1", "table2"],
      "display_override": {
        "table1": ["id", "name"],
        "table2": ["id", "description"]
      },
      "required_joins": [
        "table1.foreignKeyId = table2.id"
      ],
      "description": "Concept description"
    }
  }
}
```

### Adding a Template Relationship

```json
{
  "tables": {
    "yourEntity": {
      "display_columns": ["id", "date", "status"],
      "template_relationship": {
        "template_table": "yourTemplate",
        "via_tables": ["bridgeTable"],
        "template_columns": ["name"],
        "description": "Entity name from template"
      }
    }
  }
}
```

## Testing

Comprehensive tests are available in `tests/test_display_attributes.py`:

```bash
# Run all display attributes tests
pytest tests/test_display_attributes.py -v

# Run specific test class
pytest tests/test_display_attributes.py::TestDisplayAttributesManager -v

# Run integration tests
pytest tests/test_display_attributes.py::TestDisplayAttributesIntegration -v
```

### Test Coverage

- ✅ Manager initialization and configuration loading
- ✅ Display column resolution (basic and with concepts)
- ✅ Primary label extraction
- ✅ Template relationship handling
- ✅ Concept display resolution
- ✅ Required tables and joins
- ✅ Prompt context building
- ✅ Error handling (missing files, unconfigured tables)
- ✅ Integration with actual registry file

## Benefits

### Scalability
- **Declarative configuration**: Add new tables/concepts without code changes
- **Centralized management**: Single source of truth for display rules
- **Easy maintenance**: JSON format, version controlled
- **Automated population**: Registry generated from join graph analysis

### Reliability
- **Explicit rules**: No ambiguity about which columns to select
- **Template handling**: Proper joins for template-based names
- **Concept awareness**: Context-specific column selection
- **Consistent results**: Same query always returns same columns

### Extensibility
- **Concept overrides**: Fine-grained control per business concept
- **Multi-table concepts**: Handle complex relationships
- **Fallback behavior**: Graceful degradation if rules missing
- **Template patterns**: Reusable patterns for similar entities

## Maintenance

### Updating the Registry

The registry should be updated when:
1. **New tables are added** to the database
2. **Column names change** in existing tables
3. **New template relationships** are introduced
4. **Business concepts change** or new concepts emerge

### Regenerating the Registry

To regenerate the registry from the join graph:

```bash
cd api-ai-agent
python3 << 'EOF'
import json

with open('artifacts/join_graph_merged.json', 'r') as f:
    data = json.load(f)
    # ... regeneration logic ...
EOF
```

## Related Documentation

- [Domain Ontology](./specialized/DOMAIN_ONTOLOGY.md) - Business concept to schema mapping
- [SQL Agent Architecture](./ARCHITECTURE.md) - Overall SQL agent design
- [Implementation Guide](./IMPLEMENTATION_GUIDE.md) - Development guidelines

## Future Enhancements

Potential improvements:
1. **Dynamic column selection** based on query context
2. **User preferences** for display columns
3. **Aggregation-aware display** (different columns for aggregated vs detail queries)
4. **Localization support** for column labels
5. **Performance optimization** for large result sets
6. **Auto-detection** of display columns from usage patterns
