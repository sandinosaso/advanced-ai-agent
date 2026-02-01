"""
Tests for Domain Ontology Layer

Tests the domain vocabulary registry and term resolution logic.
"""

import json
import pytest
from pathlib import Path
from src.domain.ontology import DomainOntology
from src.domain.ontology.formatter import format_domain_context, format_domain_context_for_table_selection, build_where_clauses


@pytest.fixture
def domain_ontology():
    """Create DomainOntology instance for testing"""
    # Use the actual registry file
    return DomainOntology()


@pytest.fixture
def mock_registry(tmp_path):
    """Create a temporary mock registry for testing"""
    registry = {
        "version": 1,
        "terms": {
            "crane": {
                "entity": "asset",
                "resolution": {
                    "primary": {
                        "table": "assetType",
                        "column": "name",
                        "match_type": "semantic",
                        "confidence": 0.9
                    }
                }
            },
            "action_item": {
                "entity": "inspection_finding",
                "resolution": {
                    "primary": {
                        "table": "inspectionQuestionAnswer",
                        "column": "isActionItem",
                        "match_type": "boolean",
                        "value": True,
                        "confidence": 1.0
                    }
                }
            }
        }
    }
    
    registry_path = tmp_path / "test_registry.json"
    with open(registry_path, 'w') as f:
        json.dump(registry, f)
    
    return DomainOntology(str(registry_path))


def test_load_registry(domain_ontology):
    """Test that registry loads successfully"""
    assert domain_ontology.registry is not None
    assert "terms" in domain_ontology.registry
    assert len(domain_ontology.registry["terms"]) > 0


def test_get_all_domain_terms(domain_ontology):
    """Test getting all known domain terms"""
    terms = domain_ontology.get_all_domain_terms()
    assert isinstance(terms, list)
    assert "crane" in terms
    assert "action_item" in terms


def test_resolve_crane_term(mock_registry):
    """Test resolving 'crane' to assetType table"""
    resolution = mock_registry.resolve_domain_term("crane")
    
    assert resolution is not None
    assert resolution.term == "crane"
    assert resolution.entity == "asset"
    assert "assetType" in resolution.tables
    assert len(resolution.filters) > 0
    assert resolution.confidence == 0.9


def test_resolve_action_item_term(mock_registry):
    """Test resolving 'action_item' to boolean filter"""
    resolution = mock_registry.resolve_domain_term("action_item")
    
    assert resolution is not None
    assert resolution.term == "action_item"
    assert resolution.entity == "inspection_finding"
    assert "inspectionQuestionAnswer" in resolution.tables
    assert len(resolution.filters) == 1
    
    # Check filter structure
    filter_obj = resolution.filters[0]
    assert filter_obj["table"] == "inspectionQuestionAnswer"
    assert filter_obj["column"] == "isActionItem"
    assert filter_obj["operator"] == "="
    assert filter_obj["value"] is True
    assert resolution.confidence == 1.0


def test_resolve_unknown_term(mock_registry):
    """Test that unknown terms return None"""
    resolution = mock_registry.resolve_domain_term("unknown_term_xyz")
    assert resolution is None


def test_format_domain_context(mock_registry):
    """Test formatting domain resolutions for prompt injection"""
    # Resolve some terms
    crane_res = mock_registry.resolve_domain_term("crane")
    action_res = mock_registry.resolve_domain_term("action_item")
    
    # Convert to dict format (as used in state)
    resolutions = [
        {
            'term': crane_res.term,
            'entity': crane_res.entity,
            'tables': crane_res.tables,
            'filters': crane_res.filters,
            'confidence': crane_res.confidence,
            'strategy': crane_res.resolution_strategy
        },
        {
            'term': action_res.term,
            'entity': action_res.entity,
            'tables': action_res.tables,
            'filters': action_res.filters,
            'confidence': action_res.confidence,
            'strategy': action_res.resolution_strategy
        }
    ]
    
    context = format_domain_context(resolutions)
    
    assert isinstance(context, str)
    assert "crane" in context.lower()
    assert "action_item" in context.lower() or "action item" in context.lower()
    assert "assetType" in context
    assert "inspectionQuestionAnswer" in context


def test_build_where_clauses_crane(mock_registry):
    """Test building WHERE clauses for crane filter"""
    crane_res = mock_registry.resolve_domain_term("crane")
    
    resolutions = [{
        'term': crane_res.term,
        'entity': crane_res.entity,
        'tables': crane_res.tables,
        'filters': crane_res.filters,
        'confidence': crane_res.confidence,
        'strategy': crane_res.resolution_strategy
    }]
    
    where_clauses = build_where_clauses(resolutions)
    
    assert len(where_clauses) > 0
    # Should contain ILIKE filter for crane
    assert any("ILIKE" in clause and "crane" in clause for clause in where_clauses)


def test_build_where_clauses_action_item(mock_registry):
    """Test building WHERE clauses for action_item filter"""
    action_res = mock_registry.resolve_domain_term("action_item")
    
    resolutions = [{
        'term': action_res.term,
        'entity': action_res.entity,
        'tables': action_res.tables,
        'filters': action_res.filters,
        'confidence': action_res.confidence,
        'strategy': action_res.resolution_strategy
    }]
    
    where_clauses = build_where_clauses(resolutions)
    
    assert len(where_clauses) == 1
    # Should contain boolean filter
    assert "inspectionQuestionAnswer.isActionItem" in where_clauses[0]
    assert "= true" in where_clauses[0]


def test_build_where_clauses_multiple(mock_registry):
    """Test building WHERE clauses for multiple domain terms"""
    crane_res = mock_registry.resolve_domain_term("crane")
    action_res = mock_registry.resolve_domain_term("action_item")
    
    resolutions = [
        {
            'term': crane_res.term,
            'entity': crane_res.entity,
            'tables': crane_res.tables,
            'filters': crane_res.filters,
            'confidence': crane_res.confidence,
            'strategy': crane_res.resolution_strategy
        },
        {
            'term': action_res.term,
            'entity': action_res.entity,
            'tables': action_res.tables,
            'filters': action_res.filters,
            'confidence': action_res.confidence,
            'strategy': action_res.resolution_strategy
        }
    ]
    
    where_clauses = build_where_clauses(resolutions)
    
    # Should have clauses for both filters
    assert len(where_clauses) >= 2
    assert any("crane" in clause.lower() for clause in where_clauses)
    assert any("isActionItem" in clause for clause in where_clauses)


def test_extract_domain_terms_disabled(mock_registry):
    """Test that extraction returns empty list when disabled"""
    # Save original setting
    from src.utils.config import settings
    original = settings.domain_extraction_enabled
    
    try:
        settings.domain_extraction_enabled = False
        terms = mock_registry.extract_domain_terms("Find cranes with action items")
        assert terms == []
    finally:
        settings.domain_extraction_enabled = original


# Integration test would require LLM - skipping for unit tests
@pytest.mark.skip(reason="Requires LLM integration")
def test_extract_domain_terms_integration(domain_ontology):
    """Integration test for domain term extraction (requires LLM)"""
    question = "Find work orders with crane inspections that have action items"
    terms = domain_ontology.extract_domain_terms(question)
    
    assert isinstance(terms, list)
    # Should extract crane and action_item
    assert "crane" in terms or "action_item" in terms


# --- Two-phase extraction: compute_final_registry_terms (Pass 2 deterministic) ---


@pytest.fixture
def registry_with_compound(tmp_path):
    """Registry with atomic terms and a compound term (inspection_questions) for Pass 2 tests."""
    registry = {
        "version": 1,
        "terms": {
            "crane": {
                "entity": "asset",
                "resolution": {
                    "primary": {
                        "table": "assetType",
                        "column": "name",
                        "match_type": "semantic",
                        "confidence": 0.9
                    }
                }
            },
            "action_item": {
                "entity": "inspection_finding",
                "resolution": {
                    "primary": {
                        "table": "inspectionQuestionAnswer",
                        "column": "isActionItem",
                        "match_type": "boolean",
                        "value": True,
                        "confidence": 1.0
                    }
                }
            },
            "inspection_questions": {
                "entity": "inspection_form",
                "requires_explicit_terms": ["question", "questions", "answer", "answers", "form", "checklist"],
                "requires_atomic_signals": ["inspection"],
                "resolution": {
                    "primary": {
                        "tables": ["inspectionQuestion", "inspectionQuestionAnswer"],
                        "confidence": 0.95
                    }
                }
            }
        }
    }
    path = tmp_path / "registry_with_compound.json"
    with open(path, "w") as f:
        json.dump(registry, f)
    return DomainOntology(str(path))


def test_compute_final_registry_terms_negative_gate_excludes_question_terms(registry_with_compound):
    """Negative gate: when question has no explicit question/answer/form/checklist, inspection_questions must not be returned."""
    question = "Find crane inspections for ABC COKE"
    atomic_signals = ["crane", "inspection"]
    result = registry_with_compound.compute_final_registry_terms(question, atomic_signals)
    assert "inspection_questions" not in result
    assert "crane" in result


def test_compute_final_registry_terms_simple_term_in_atomic_signals(registry_with_compound):
    """Simple (atomic-only) term is returned when present in atomic signals."""
    question = "Find cranes"
    atomic_signals = ["crane"]
    result = registry_with_compound.compute_final_registry_terms(question, atomic_signals)
    assert "crane" in result
    assert "inspection_questions" not in result


def test_compute_final_registry_terms_compound_included_when_explicit_and_atomic(registry_with_compound):
    """Compound term is included only when question has explicit word and atomic signals are present."""
    question = "Show me the questions and answers for that inspection"
    atomic_signals = ["inspection", "question"]
    result = registry_with_compound.compute_final_registry_terms(question, atomic_signals)
    assert "inspection_questions" in result


def test_compute_final_registry_terms_compound_excluded_without_explicit_word(registry_with_compound):
    """Compound term is excluded when question does not mention question/answer/form/checklist."""
    question = "Show inspection data"
    atomic_signals = ["inspection"]
    result = registry_with_compound.compute_final_registry_terms(question, atomic_signals)
    assert "inspection_questions" not in result


def test_compute_final_registry_terms_compound_excluded_without_atomic_signal(registry_with_compound):
    """Compound term requiring atomic signal is excluded when that signal is not in atomic_signals."""
    question = "Show me the questions for the form"
    atomic_signals = ["question"]
    result = registry_with_compound.compute_final_registry_terms(question, atomic_signals)
    assert "inspection_questions" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
