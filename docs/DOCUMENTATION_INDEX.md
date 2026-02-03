# Documentation Index - Semantic Role System

## 📚 Complete Documentation Suite

All documentation has been updated to explain the semantic role system comprehensively.

---

## Quick Reference Guides

## Architecture Documentation

### 🏗️ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
**Updated section**: "Semantic Role System" (under "Join Graph Pipeline")  
**Contains**:
- Complete role reference table (7 roles)
- Bridge table discovery logic
- Three-layer defense strategy
- Real-world examples (workTime query)
- When to use each role
- Implementation file locations

**Best for**: System-level understanding

---

## Specialized Documentation

### 🎯 [docs/specialized/SEMANTIC_ROLE_SYSTEM.md](docs/specialized/SEMANTIC_ROLE_SYSTEM.md) ⭐ NEW
**Complete reference guide**  
**Contains**:

#### Section 1-2: Overview & Role Details
- All 7 roles with detailed descriptions
- When to use each role
- Bridge behavior for each role
- Real-world examples for each

#### Section 3: Bridge Discovery Logic
- Three-layer defense algorithm
- Code examples with explanations
- Discovery algorithm flowchart

#### Section 4: Metadata Format
- JSON schema and examples
- Field descriptions
- Advanced configurations

#### Section 5: Real-World Examples
- workTime query (before/after)
- Inspection with signatures
- Crew membership query
- Generated SQL examples

#### Section 6: Adding New Roles
- Step-by-step guide
- Decision tree for role selection
- Testing recommendations

#### Section 7: Monitoring & Debugging
- Log messages to watch
- Debugging checklist
- Common issues

#### Section 8-10: Integration & Files
- Benefits comparison
- Integration with other systems
- File locations

**Best for**: Complete reference, adding new roles, debugging

---

### 🔗 [docs/specialized/DOMAIN_ONTOLOGY.md](docs/specialized/DOMAIN_ONTOLOGY.md)
**New section**: "Semantic Role System Integration"  
**Contains**:
- How semantic roles integrate with domain ontology
- Role reference table
- Integration points (table selection, bridge discovery)
- Combined usage examples
- When to use domain ontology vs semantic roles

**Best for**: Understanding system interactions

---

### 📐 [docs/specialized/SCOPED_JOINS_IMPLEMENTATION.md](docs/specialized/SCOPED_JOINS_IMPLEMENTATION.md)
**Related**: Template-instance scoping  
**Contains**:
- How scoped joins work
- Relationship to semantic roles
- content_child role usage

**Best for**: Understanding template-instance relationships

---

## Documentation Map

```
Architecture
└── docs/ARCHITECTURE.md                ← System architecture
    └── Semantic Role System section    ← Role overview

Specialized Guides
└── docs/specialized/
    ├── SEMANTIC_ROLE_SYSTEM.md ⭐      ← Complete reference
    ├── DOMAIN_ONTOLOGY.md              ← Domain integration
    └── SCOPED_JOINS_IMPLEMENTATION.md  ← Related: Scoping

Implementation Files
└── artifacts/join_graph_manual.json    ← Metadata definitions
```

---

## Role Quick Reference

| Role | Never Bridge? | Use When |
|------|---------------|----------|
| instance | No | Actual records/executions |
| template | No | Structure definitions |
| bridge | No | Legitimate many-to-many junctions |
| content_child | No | Child data in parent context |
| **satellite** | **YES** ❌ | Auxiliary orthogonal data |
| **assignment** | **YES** ❌ | Membership tracking |
| **configuration** | **YES** ❌ | Permissions/settings |

---

## Common Scenarios

### "I need to add a new table to metadata"
→ Read: `docs/specialized/SEMANTIC_ROLE_SYSTEM.md` Section 6 (Adding New Roles)

### "I want to understand why a bridge was excluded"
→ Read: `docs/specialized/SEMANTIC_ROLE_SYSTEM.md` Section 7 (Monitoring & Debugging)

### "I need to debug a query that's using wrong tables"
→ Read: `docs/specialized/SEMANTIC_ROLE_SYSTEM.md` Section 7 (Debugging Checklist)

### "I want to understand the system architecture"
→ Read: `docs/ARCHITECTURE.md` Semantic Role System section

### "I need to understand domain ontology integration"
→ Read: `docs/specialized/DOMAIN_ONTOLOGY.md` Section 6

### "I need to verify the fix works"
→ Read: `BRIDGE_TABLE_FIX_QUICKSTART.md`

---

## File Locations

### Code Files
- `src/agents/sql/planning/bridge_tables.py` - Bridge discovery logic
- `src/agents/sql/nodes/join_planner.py` - Join planning with roles
- `src/agents/sql/nodes/sql_generator.py` - SQL generation with roles
- `src/utils/path_finder.py` - Path finding with role filtering

### Metadata Files
- `artifacts/join_graph_manual.json` - Semantic role definitions
- `artifacts/domain_registry.json` - Domain term mappings

### Documentation Files
- All listed above in this index
