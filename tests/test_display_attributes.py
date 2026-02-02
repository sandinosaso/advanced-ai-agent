"""
Tests for display attributes functionality
"""

import json
import pytest
from pathlib import Path
from src.domain.display_attributes import DisplayAttributesManager
from src.domain.ontology.models import DisplayAttributes, ConceptDisplayRules


@pytest.fixture
def test_registry_path(tmp_path):
    """Create a test display attributes registry"""
    registry = {
        "version": 1,
        "description": "Test display attributes registry",
        "tables": {
            "employee": {
                "display_columns": ["id", "firstName", "lastName", "email"],
                "primary_label": ["firstName", "lastName"],
                "description": "Employee display configuration"
            },
            "user": {
                "display_columns": ["id", "firstName", "lastName", "email"],
                "primary_label": ["firstName", "lastName"]
            },
            "workOrderStatus": {
                "display_columns": ["id", "name"],
                "primary_label": ["name"]
            },
            "inspection": {
                "display_columns": ["id", "date", "status"],
                "template_relationship": {
                    "template_table": "inspectionTemplate",
                    "via_tables": ["inspectionTemplateWorkOrder"],
                    "template_columns": ["name"],
                    "description": "Inspection name from template"
                }
            },
            "inspectionTemplate": {
                "display_columns": ["id", "name"],
                "primary_label": ["name"]
            }
        },
        "concepts": {
            "employee": {
                "tables": ["employee"],
                "display_override": {
                    "employee": ["id", "firstName", "lastName"]
                },
                "description": "Employee concept"
            },
            "workorder_status": {
                "tables": ["workOrder", "workOrderStatus"],
                "display_override": {
                    "workOrderStatus": ["id", "name"]
                },
                "required_joins": ["workOrder.workOrderStatusId = workOrderStatus.id"],
                "description": "Workorder status concept"
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
                "description": "Inspection with template"
            }
        }
    }
    
    registry_path = tmp_path / "test_display_attributes.json"
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    return str(registry_path)


class TestDisplayAttributesManager:
    """Tests for DisplayAttributesManager class"""
    
    def test_initialization(self, test_registry_path):
        """Test manager initialization"""
        manager = DisplayAttributesManager(test_registry_path)
        
        assert manager.registry is not None
        assert len(manager.tables_config) == 5
        assert len(manager.concepts_config) == 3
    
    def test_get_display_columns_basic(self, test_registry_path):
        """Test getting display columns for a table"""
        manager = DisplayAttributesManager(test_registry_path)
        
        # Test employee table
        cols = manager.get_display_columns("employee")
        assert "id" in cols
        assert "firstName" in cols
        assert "lastName" in cols
        assert "email" in cols
    
    def test_get_display_columns_with_concept(self, test_registry_path):
        """Test getting display columns with concept override"""
        manager = DisplayAttributesManager(test_registry_path)
        
        # Test employee with concept override
        cols = manager.get_display_columns("employee", concept="employee")
        assert cols == ["id", "firstName", "lastName"]
        
        # Test without concept (should use table default)
        cols = manager.get_display_columns("employee", concept=None)
        assert "email" in cols
    
    def test_get_primary_label(self, test_registry_path):
        """Test getting primary label columns"""
        manager = DisplayAttributesManager(test_registry_path)
        
        labels = manager.get_primary_label("employee")
        assert labels == ["firstName", "lastName"]
        
        labels = manager.get_primary_label("workOrderStatus")
        assert labels == ["name"]
    
    def test_get_template_relationship(self, test_registry_path):
        """Test getting template relationship configuration"""
        manager = DisplayAttributesManager(test_registry_path)
        
        template_rel = manager.get_template_relationship("inspection")
        assert template_rel is not None
        assert template_rel["template_table"] == "inspectionTemplate"
        assert "inspectionTemplateWorkOrder" in template_rel["via_tables"]
        assert "name" in template_rel["template_columns"]
        
        # Table without template relationship
        template_rel = manager.get_template_relationship("employee")
        assert template_rel is None
    
    def test_get_tables_with_template_relationships(self, test_registry_path):
        """Test getting all template relationships for multiple tables"""
        manager = DisplayAttributesManager(test_registry_path)
        
        tables = ["employee", "inspection", "workOrderStatus"]
        template_rels = manager.get_tables_with_template_relationships(tables)
        
        assert "inspection" in template_rels
        assert "employee" not in template_rels
        assert "workOrderStatus" not in template_rels
    
    def test_resolve_concept_display(self, test_registry_path):
        """Test resolving display columns for a concept"""
        manager = DisplayAttributesManager(test_registry_path)
        
        # Test inspection concept
        tables = ["inspection", "inspectionTemplate"]
        display_map = manager.resolve_concept_display("inspection", tables)
        
        assert "inspection" in display_map
        assert "inspectionTemplate" in display_map
        assert display_map["inspection"] == ["id", "date", "status"]
        assert display_map["inspectionTemplate"] == ["name"]
    
    def test_get_concept_required_tables(self, test_registry_path):
        """Test getting required tables for a concept"""
        manager = DisplayAttributesManager(test_registry_path)
        
        tables = manager.get_concept_required_tables("inspection")
        assert "inspection" in tables
        assert "inspectionTemplateWorkOrder" in tables
        assert "inspectionTemplate" in tables
    
    def test_get_concept_required_joins(self, test_registry_path):
        """Test getting required joins for a concept"""
        manager = DisplayAttributesManager(test_registry_path)
        
        joins = manager.get_concept_required_joins("inspection")
        assert len(joins) == 2
        assert any("inspectionTemplateWorkOrder" in join for join in joins)
        assert any("inspectionTemplate" in join for join in joins)
    
    def test_build_display_context(self, test_registry_path):
        """Test building display context for prompts"""
        manager = DisplayAttributesManager(test_registry_path)
        
        tables = ["employee", "workOrderStatus"]
        context = manager.build_display_context(tables)
        
        assert "DISPLAY COLUMN GUIDELINES" in context
        assert "employee" in context
        assert "workOrderStatus" in context
        assert "firstName" in context or "lastName" in context
    
    def test_build_display_context_with_concept(self, test_registry_path):
        """Test building display context with concept"""
        manager = DisplayAttributesManager(test_registry_path)
        
        tables = ["inspection", "inspectionTemplate"]
        context = manager.build_display_context(tables, concept="inspection")
        
        assert "DISPLAY COLUMN GUIDELINES" in context
        assert "Concept: inspection" in context
        assert "Required joins" in context
    
    def test_get_all_required_tables_for_display(self, test_registry_path):
        """Test getting all tables needed for display including templates"""
        manager = DisplayAttributesManager(test_registry_path)
        
        base_tables = ["inspection"]
        all_tables = manager.get_all_required_tables_for_display(base_tables)
        
        assert "inspection" in all_tables
        assert "inspectionTemplate" in all_tables
        assert "inspectionTemplateWorkOrder" in all_tables
    
    def test_get_all_required_tables_with_concept(self, test_registry_path):
        """Test getting all tables with concept requirements"""
        manager = DisplayAttributesManager(test_registry_path)
        
        base_tables = ["workOrder"]
        all_tables = manager.get_all_required_tables_for_display(
            base_tables, 
            concept="workorder_status"
        )
        
        assert "workOrder" in all_tables
        assert "workOrderStatus" in all_tables
    
    def test_has_configuration(self, test_registry_path):
        """Test checking if table has configuration"""
        manager = DisplayAttributesManager(test_registry_path)
        
        assert manager.has_configuration("employee") is True
        assert manager.has_configuration("nonexistent_table") is False
    
    def test_get_concept_names(self, test_registry_path):
        """Test getting all concept names"""
        manager = DisplayAttributesManager(test_registry_path)
        
        concepts = manager.get_concept_names()
        assert "employee" in concepts
        assert "workorder_status" in concepts
        assert "inspection" in concepts
    
    def test_get_table_names(self, test_registry_path):
        """Test getting all table names"""
        manager = DisplayAttributesManager(test_registry_path)
        
        tables = manager.get_table_names()
        assert "employee" in tables
        assert "inspection" in tables
        assert "workOrderStatus" in tables
    
    def test_missing_registry_file(self, tmp_path):
        """Test handling missing registry file"""
        missing_path = tmp_path / "nonexistent.json"
        manager = DisplayAttributesManager(str(missing_path))
        
        # Should initialize with empty configuration
        assert len(manager.tables_config) == 0
        assert len(manager.concepts_config) == 0
    
    def test_get_display_columns_no_config(self, test_registry_path):
        """Test getting display columns for unconfigured table"""
        manager = DisplayAttributesManager(test_registry_path)
        
        # Table not in registry
        cols = manager.get_display_columns("unknown_table")
        assert cols == ["id"]  # Should return just id as fallback
    
    def test_get_display_columns_without_id(self, test_registry_path):
        """Test getting display columns without including id"""
        manager = DisplayAttributesManager(test_registry_path)
        
        cols = manager.get_display_columns("employee", include_id=False)
        assert "id" not in cols
        assert "firstName" in cols
        assert "lastName" in cols


class TestDisplayAttributesModels:
    """Tests for display attributes data models"""
    
    def test_display_attributes_model(self):
        """Test DisplayAttributes dataclass"""
        attrs = DisplayAttributes(
            table="employee",
            display_columns=["id", "firstName", "lastName"],
            primary_label=["firstName", "lastName"],
            description="Employee display config"
        )
        
        assert attrs.table == "employee"
        assert len(attrs.display_columns) == 3
        assert len(attrs.primary_label) == 2
        assert attrs.template_relationship is None
    
    def test_display_attributes_with_template(self):
        """Test DisplayAttributes with template relationship"""
        template_rel = {
            "template_table": "inspectionTemplate",
            "via_tables": ["inspectionTemplateWorkOrder"],
            "template_columns": ["name"]
        }
        
        attrs = DisplayAttributes(
            table="inspection",
            display_columns=["id", "date"],
            primary_label=[],
            template_relationship=template_rel
        )
        
        assert attrs.template_relationship is not None
        assert attrs.template_relationship["template_table"] == "inspectionTemplate"
    
    def test_concept_display_rules_model(self):
        """Test ConceptDisplayRules dataclass"""
        rules = ConceptDisplayRules(
            concept="employee",
            tables=["employee"],
            display_override={"employee": ["id", "firstName", "lastName"]},
            required_joins=[],
            description="Employee concept rules"
        )
        
        assert rules.concept == "employee"
        assert len(rules.tables) == 1
        assert "employee" in rules.display_override
        assert len(rules.required_joins) == 0
    
    def test_concept_display_rules_with_joins(self):
        """Test ConceptDisplayRules with required joins"""
        rules = ConceptDisplayRules(
            concept="workorder_status",
            tables=["workOrder", "workOrderStatus"],
            display_override={
                "workOrderStatus": ["id", "name"]
            },
            required_joins=["workOrder.workOrderStatusId = workOrderStatus.id"]
        )
        
        assert len(rules.tables) == 2
        assert len(rules.required_joins) == 1
        assert "workOrderStatus" in rules.display_override


class TestDisplayAttributesIntegration:
    """Integration tests for display attributes with SQL agent"""
    
    def test_registry_file_exists(self):
        """Test that the actual registry file exists"""
        registry_path = Path("artifacts/display_attributes_registry.json")
        assert registry_path.exists(), "Display attributes registry file should exist"
    
    def test_registry_file_valid_json(self):
        """Test that the registry file is valid JSON"""
        registry_path = Path("artifacts/display_attributes_registry.json")
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        assert "version" in registry
        assert "tables" in registry
        assert "concepts" in registry
    
    def test_registry_has_key_tables(self):
        """Test that registry includes key tables"""
        registry_path = Path("artifacts/display_attributes_registry.json")
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        tables = registry.get("tables", {})
        
        # Check for key tables
        assert "employee" in tables
        assert "user" in tables
        assert "workOrderStatus" in tables
        assert "inspection" in tables
    
    def test_registry_has_key_concepts(self):
        """Test that registry includes key concepts"""
        registry_path = Path("artifacts/display_attributes_registry.json")
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        concepts = registry.get("concepts", {})
        
        # Check for key concepts
        assert "employee" in concepts
        assert "workorder_status" in concepts
        assert "inspection" in concepts
    
    def test_manager_loads_actual_registry(self):
        """Test that manager can load the actual registry"""
        manager = DisplayAttributesManager("artifacts/display_attributes_registry.json")
        
        assert len(manager.tables_config) > 0
        assert len(manager.concepts_config) > 0
        
        # Test specific configurations
        assert manager.has_configuration("employee")
        assert manager.has_configuration("inspection")
    
    def test_template_relationships_configured(self):
        """Test that template relationships are properly configured"""
        manager = DisplayAttributesManager("artifacts/display_attributes_registry.json")
        
        # Check inspection template relationship
        inspection_rel = manager.get_template_relationship("inspection")
        assert inspection_rel is not None
        assert inspection_rel["template_table"] == "inspectionTemplate"
        
        # Check service template relationship
        service_rel = manager.get_template_relationship("service")
        assert service_rel is not None
        assert service_rel["template_table"] == "serviceTemplate"
        
        # Check safety template relationship
        safety_rel = manager.get_template_relationship("safety")
        assert safety_rel is not None
        assert safety_rel["template_table"] == "safetyTemplate"
