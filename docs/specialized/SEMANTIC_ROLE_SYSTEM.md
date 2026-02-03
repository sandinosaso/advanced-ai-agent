# Semantic Role System

## Overview

The **Semantic Role System** classifies database tables by their business purpose to prevent incorrect bridge table usage and ensure accurate SQL query generation. This system works alongside the Domain Ontology to produce clean, efficient queries.

**Location**: `artifacts/join_graph_manual.json` (table_metadata section)

---

## 1. Table Roles

### Complete Role Reference

| Role | Purpose | Bridge Behavior | When to Use |
|------|---------|-----------------|-------------|
| **instance** | Primary entity executions/records | Normal bridge candidate | Tables representing actual records, executions, or transactions |
| **template** | Structure/schema definitions | Normal bridge candidate | Tables defining structure, templates, or schemas |
| **bridge** | Legitimate many-to-many junctions | Used as bridges when needed | True junction tables connecting two entities |
| **content_child** | Child data within parent context | Normal bridge candidate | Detail records that belong to a parent context |
| **satellite** | Orthogonal auxiliary data | **NEVER** used as bridge | Signatures, attachments, configurations that don't affect query logic |
| **assignment** | Membership/assignment tracking | **NEVER** used as bridge | Tables tracking who is assigned to what |
| **configuration** | Permission/settings | **NEVER** used as bridge | Tables defining permissions, rules, or configuration |

---

## 2. Role Details & Examples

### instance
**Purpose**: Tables representing actual executions, records, or transactions

**Characteristics**:
- Primary business entities
- Have instance-specific data (dates, statuses, values)
- Often have FKs to templates or parent entities

**Examples**:
```
✅ inspection - An inspection execution/instance
✅ safety - A safety check execution
✅ service - A service execution
✅ workTime - A time entry record
✅ workOrder - A work order instance
```

**Bridge Behavior**: Normal candidate - can be used as a bridge if it connects two selected tables

### template
**Purpose**: Tables defining structure, schema, or templates

**Characteristics**:
- Define reusable structures
- Referenced by instance tables
- Contain field definitions, not instance data

**Examples**:
```
✅ inspectionTemplate - Template defining inspection structure
✅ safetyTemplate - Template defining safety check structure
✅ serviceTemplate - Template defining service structure
```

**Bridge Behavior**: Normal candidate - can be used as a bridge if needed

### bridge
**Purpose**: Legitimate many-to-many junction tables

**Characteristics**:
- Connect two entities in a many-to-many relationship
- Usually have two foreign keys
- Minimal additional data (maybe order, timestamps)
- Actually NEEDED for certain queries

**Examples**:
```
✅ inspectionTemplateWorkOrder - Links inspection instances to work orders
✅ safetyTemplateWorkOrder - Links safety instances to work orders
✅ serviceTemplateWorkOrder - Links service instances to work orders
```

**Bridge Behavior**: Used as bridge when connecting both entities

**When included**:
```sql
-- Query needs both inspection AND work order data
SELECT ... 
FROM inspection
JOIN inspectionTemplateWorkOrder ON ...  -- ✅ NEEDED as bridge
JOIN workOrder ON ...
```

### content_child
**Purpose**: Child data that belongs within a parent context

**Characteristics**:
- Detail records for a parent entity
- Often have dual-parent relationships (template + instance)
- Contain granular data within broader context

**Examples**:
```
✅ inspectionQuestion - Questions in inspection templates
✅ inspectionQuestionAnswer - Answers in inspection instances
✅ safetyQuestion - Questions in safety templates
✅ serviceQuestion - Questions in service templates
```

**Bridge Behavior**: Normal candidate, but often needs scoped joins (template-instance)

### satellite
**Purpose**: Orthogonal auxiliary data that doesn't affect core query logic

**Characteristics**:
- Attached to entities but functionally independent
- Optional, supplementary data
- Rarely queried in normal business questions
- Should NOT become a bridge table

**Examples**:
```
✅ inspectionCustomerSignature - Signature for inspection (orthogonal)
✅ inspectionCrewSignature - Signature for inspection (orthogonal)
✅ inspectionConfiguration - Config settings (orthogonal)
✅ inspectionQAAttachment - Attachments (orthogonal)
✅ safetySignature - Signature for safety (orthogonal)
```

**Bridge Behavior**: **NEVER** used as bridge - filtered out during bridge discovery

**Why excluded**:
- Signatures don't help connect inspections to other entities
- Configurations don't define relationships
- Attachments are auxiliary, not structural

### assignment
**Purpose**: Tables tracking membership, assignments, or "who belongs to what"

**Characteristics**:
- Define membership relationships
- Track assignments over time
- Separate from instance data (e.g., crew membership ≠ time entry)
- Should NOT be used to bridge instance queries

**Examples**:
```
✅ employeeCrew - Which employees are assigned to which crews
   - Tracks crew membership
   - NOT the same as "who logged time"
   - workTime has direct FK to employee
```

**Bridge Behavior**: **NEVER** used as bridge - filtered out during bridge discovery

**Problem it solves**:
```
Query: "Show me employee work time for Oct 6-12"

❌ WRONG (before fix):
SELECT ...
FROM employee
JOIN employeeCrew ON employeeCrew.employeeId = employee.id  -- UNNECESSARY!
JOIN workTime ON workTime.employeeId = employee.id

✅ CORRECT (after fix):
SELECT ...
FROM employee
JOIN workTime ON workTime.employeeId = employee.id  -- Direct FK
```

**Why wrong?**:
- `employeeCrew` tracks crew membership (who is on which crew)
- `workTime.employeeId` directly references employee (who logged time)
- Using employeeCrew as a bridge creates unnecessary complexity
- Can cause Cartesian products or wrong results

### configuration
**Purpose**: Tables defining permissions, allowed values, rules, or settings

**Characteristics**:
- Define what is allowed/configured
- Reference rules, not instance data
- Often "Role" or "Type" in name
- Separate from actual usage/execution

**Examples**:
```
✅ employeeRoleWorkTimeType - Which work time types are allowed per role
   - Defines permissions (what types are allowed)
   - NOT the same as "what types were used"
   - workTime has direct FK to workTimeType
```

**Bridge Behavior**: **NEVER** used as bridge - filtered out during bridge discovery

**Problem it solves**:
```
Query: "Show me work time by type for Oct 6-12"

❌ WRONG (before fix):
SELECT ...
FROM workTime
JOIN employeeRoleWorkTimeType ON ... -- UNNECESSARY!
JOIN workTimeType ON ...

✅ CORRECT (after fix):
SELECT ...
FROM workTime
JOIN workTimeType ON workTime.workTimeTypeId = workTimeType.id  -- Direct FK
```

**Why wrong?**:
- `employeeRoleWorkTimeType` defines allowed types per role (configuration)
- `workTime.workTimeTypeId` directly references the type used (instance data)
- Using employeeRoleWorkTimeType as a bridge adds configuration data to instance query
- Only needed when querying "what types are allowed for this role?"

---

## 3. Bridge Table Discovery Logic

### Three-Layer Defense

The system uses three layers to prevent incorrect bridge usage:

#### Layer 1: Role-Based Filtering
```python
def should_exclude_table(table_name: str) -> bool:
    metadata = table_metadata.get(table_name, {})
    role = metadata.get("role")
    
    # Exclude satellite, assignment, and configuration
    if role in ("satellite", "assignment", "configuration"):
        logger.debug(f"Excluding {role} table '{table_name}'")
        return True
    
    return False
```

**Result**: satellite, assignment, and configuration tables are filtered out before connectivity analysis

#### Layer 2: Metadata Exclusions
```json
{
  "employeeCrew": {
    "role": "assignment",
    "exclude_as_bridge_for": ["workTime", "employee"],
    "note": "Only for crew membership queries"
  }
}
```

**Result**: Even if a table passes role check, it can be explicitly excluded for specific table pairs

#### Layer 3: Direct Path Detection
```python
# Check if direct paths already exist
if all_have_direct_path:
    logger.info("Skipping bridge - direct paths exist")
    continue
```

**Result**: If selected tables already have direct foreign keys between them, don't add a bridge

### Discovery Algorithm

```python
def find_bridge_tables(selected_tables, relationships, table_metadata):
    # 1. Build direct connection map
    for rel in relationships:
        if both tables in selected_tables:
            direct_connections[table1].add(table2)
    
    # 2. Find potential bridges (tables connecting 2+ selected tables)
    for potential_bridge in relationships:
        if connects 2+ selected tables:
            # Layer 1: Check role
            if role in ("satellite", "assignment", "configuration"):
                skip
            
            # Layer 2: Check metadata exclusions
            if table in exclude_as_bridge_for:
                skip
            
            # Layer 3: Check direct paths
            if all connected tables have direct paths:
                skip
            
            # Only add if no exclusions and no direct path
            add_to_bridges
    
    return bridges
```

---

## 4. Metadata Format

### Basic Entry
```json
{
  "tableName": {
    "role": "instance",
    "category": "execution",
    "description": "Human-readable description"
  }
}
```

### Advanced Entry with Exclusions
```json
{
  "employeeCrew": {
    "role": "assignment",
    "category": "crew_membership",
    "description": "Employee-to-crew assignments - tracks which employees are assigned to which crews, not time tracking data",
    "exclude_as_bridge_for": ["workTime", "employee"],
    "note": "Only needed when querying crew membership or assignments, not for time entries"
  }
}
```

### Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `role` | Yes | string | One of: instance, template, bridge, content_child, satellite, assignment, configuration |
| `category` | No | string | Sub-category for logging/organization |
| `description` | Yes | string | Human-readable explanation of table's purpose |
| `exclude_as_bridge_for` | No | array | Tables this should NOT bridge between |
| `note` | No | string | Additional context for developers |

---

## 5. Real-World Examples

### Example 1: workTime Query (Fixed by Semantic Roles)

**Query**: "Show me employees who worked between Oct 6-12 with daily hours"

**Before Semantic Roles**:
```
Selected tables: employee, workTime, workTimeType
Bridge discovery finds:
  - employeeCrew (connects employee + workTime) ❌
  - employeeRoleWorkTimeType (connects workTime + workTimeType) ❌

Result: 5 tables, complex query, potential errors
```

**After Semantic Roles**:
```
Selected tables: employee, workTime, workTimeType
Bridge discovery:
  - employeeCrew: role="assignment" → EXCLUDED ✅
  - employeeRoleWorkTimeType: role="configuration" → EXCLUDED ✅
  - Direct paths exist: workTime.employeeId -> employee.id ✅

Result: 3 tables, clean query using direct FKs
```

**Generated SQL**:
```sql
SELECT 
    employee.id,
    employee.firstName,
    employee.lastName,
    SUM(CASE WHEN DATE(workTime.startTime) = '2025-10-06' THEN workTime.hours ELSE 0 END) AS hours_oct_06,
    ...
    SUM(workTime.hours) AS total_hours
FROM employee
JOIN workTime ON workTime.employeeId = employee.id  -- Direct FK ✅
WHERE DATE(workTime.startTime) BETWEEN '2025-10-06' AND '2025-10-12'
GROUP BY employee.id, employee.firstName, employee.lastName
```

### Example 2: Inspection with Signatures (Satellite Exclusion)

**Query**: "Show me inspections for work order #123"

**Bridge Discovery**:
```
Selected tables: inspection, workOrder
Potential bridges:
  - inspectionTemplateWorkOrder: role="bridge" → INCLUDED ✅ (needed!)
  - inspectionCustomerSignature: role="satellite" → EXCLUDED ✅
  - inspectionCrewSignature: role="satellite" → EXCLUDED ✅
  - inspectionConfiguration: role="satellite" → EXCLUDED ✅

Result: Only necessary bridge (inspectionTemplateWorkOrder) is used
```

### Example 3: Crew Membership Query (Assignment Included)

**Query**: "Show me which employees are assigned to crew 'Alpha'"

**Tables Needed**:
```
employee, employeeCrew, crew
```

**Bridge Discovery**:
```
employeeCrew connects employee + crew
Role="assignment" BUT:
  - Query is ABOUT assignments (not a side effect)
  - exclude_as_bridge_for=["workTime", "employee"]
  - Not in exclusion list for this query
  
Result: employeeCrew IS included ✅ (correct - query needs it!)
```

**Key Insight**: Roles don't universally exclude tables - they prevent MISUSE as bridges. If the query is ABOUT assignments, assignment tables are needed.

---

## 6. Adding New Roles

### Step-by-Step

1. **Identify the table's business purpose**
   - Is it instance data or configuration?
   - Does it track assignments/membership?
   - Is it auxiliary/orthogonal?

2. **Choose the appropriate role**
   - instance: Actual records/executions
   - assignment: Membership tracking
   - configuration: Permission/settings
   - satellite: Auxiliary orthogonal data

3. **Add to join_graph_manual.json**
```json
{
  "table_metadata": {
    "yourTable": {
      "role": "assignment",
      "category": "your_category",
      "description": "Clear description of purpose",
      "exclude_as_bridge_for": ["table1", "table2"],
      "note": "When to use/not use"
    }
  }
}
```

4. **Test the behavior**
   - Run queries that previously included this table as a bridge
   - Verify it's now excluded (check logs)
   - Test queries that DO need this table (ensure still works)

### Decision Tree

```
Is this table instance/execution data?
├─ Yes → role="instance"
└─ No
   ├─ Does it define structure/templates?
   │  └─ Yes → role="template"
   └─ No
      ├─ Is it a many-to-many junction?
      │  └─ Yes → role="bridge"
      └─ No
         ├─ Is it auxiliary/orthogonal?
         │  └─ Yes → role="satellite"
         └─ No
            ├─ Does it track membership/assignments?
            │  └─ Yes → role="assignment"
            └─ No
               └─ Is it configuration/permissions?
                  └─ Yes → role="configuration"
```

---

## 7. Monitoring & Debugging

### Log Messages to Watch

**Role-based exclusion**:
```
INFO - Excluding configuration table 'employeeRoleWorkTimeType' from bridge discovery
INFO - Excluding satellite table 'inspectionConfiguration' from bridge discovery
```

**Metadata-based exclusion**:
```
DEBUG - Skipping bridge table 'employeeCrew' - explicitly excluded for table 'employee' in metadata
```

**Direct path detection**:
```
INFO - Skipping bridge table 'employeeCrew' - direct paths already exist between connected tables: ['employee', 'workTime']
```

**Bridge addition**:
```
INFO - Found bridge table 'inspectionTemplateWorkOrder' (role: bridge) connecting 2 selected tables: ['inspection', 'workOrder']
```

### Debugging Checklist

If a query isn't working as expected:

1. **Check the logs** - Which bridges were added/excluded?
2. **Verify roles** - Is the table metadata correct?
3. **Check direct paths** - Do direct FKs exist?
4. **Review exclude_as_bridge_for** - Is the exclusion too broad?
5. **Query purpose** - Does the query actually need this table?

---

## 8. Benefits

### Before Semantic Roles
- ❌ Unnecessary bridge tables added
- ❌ Complex queries (5+ tables when 3 needed)
- ❌ Cartesian products from incorrect bridges
- ❌ Mixing instance data with configuration data
- ❌ Hard to debug which tables are needed

### After Semantic Roles
- ✅ Only necessary tables included
- ✅ Simpler queries (3-4 tables average)
- ✅ Direct foreign keys preferred
- ✅ Clear semantic separation
- ✅ Metadata-driven, no code changes needed

---

## 9. Integration with Other Systems

### Domain Ontology
- Domain terms define WHAT to query
- Semantic roles define HOW to connect tables

### Path Finder
- Path finder finds shortest paths
- Semantic roles filter which paths are valid

### Display Attributes
- Display attributes define what to show
- Semantic roles ensure correct joins for display data

---

## 10. File Locations

| File | Purpose |
|------|---------|
| `artifacts/join_graph_manual.json` | Semantic role metadata definitions |
| `src/agents/sql/planning/bridge_tables.py` | Bridge discovery with role filtering |
| `src/agents/sql/nodes/join_planner.py` | Join planning with role awareness |
| `src/utils/path_finder.py` | Path finding with role filtering |
| `docs/ARCHITECTURE.md` | System architecture with semantic roles section |
| `docs/specialized/DOMAIN_ONTOLOGY.md` | Integration with domain ontology |

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [DOMAIN_ONTOLOGY.md](DOMAIN_ONTOLOGY.md) - Domain term resolution system
- [SCOPED_JOINS_IMPLEMENTATION.md](SCOPED_JOINS_IMPLEMENTATION.md) - Template-instance scoping
