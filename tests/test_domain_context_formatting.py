"""
Test domain context formatting changes.

Verifies:
1. format_domain_context_for_table_selection shows tables only (no filters)
2. format_domain_context shows both tables and filters
3. Structural match types work correctly (no filters)
"""

import unittest
from src.utils.domain_ontology import (
    format_domain_context_for_table_selection,
    format_domain_context,
    DomainOntology
)


class TestDomainContextFormatting(unittest.TestCase):
    """Test domain context formatting changes"""
    
    def test_format_domain_context_for_table_selection(self):
        """Test that table selection format excludes filters"""
        resolutions = [
            {
                'term': 'crane',
                'entity': 'asset',
                'tables': ['asset'],
                'filters': [
                    {
                        'table': 'asset',
                        'column': 'name',
                        'operator': 'LIKE',
                        'value': '%crane%',
                        'case_insensitive': True
                    }
                ],
                'confidence': 0.95,
                'strategy': 'primary'
            }
        ]
        
        result = format_domain_context_for_table_selection(resolutions)
        
        # Should include concept and tables
        self.assertIn("Concept: 'crane'", result)
        self.assertIn("Tables needed: asset", result)
        self.assertIn("Confidence: 0.95", result)
        
        # Should NOT include filter details
        self.assertNotIn("Filters to apply:", result)
        self.assertNotIn("LOWER(asset.name)", result)
        self.assertNotIn("LIKE", result)

    def test_format_domain_context_includes_filters(self):
        """Test that full format includes filters"""
        resolutions = [
            {
                'term': 'crane',
                'entity': 'asset',
                'tables': ['asset'],
                'filters': [
                    {
                        'table': 'asset',
                        'column': 'name',
                        'operator': 'LIKE',
                        'value': '%crane%',
                        'case_insensitive': True
                    }
                ],
                'confidence': 0.95,
                'strategy': 'primary'
            }
        ]
        
        result = format_domain_context(resolutions)
        
        # Should include everything
        self.assertIn("Concept: 'crane'", result)
        self.assertIn("Tables needed: asset", result)
        self.assertIn("Filters to apply:", result)
        self.assertIn("LOWER(asset.name) LIKE '%crane%'", result)
        self.assertIn("Confidence: 0.95", result)

    def test_format_domain_context_structural_match(self):
        """Test that structural matches (no filters) are handled correctly"""
        resolutions = [
            {
                'term': 'inspection_questions',
                'entity': 'inspection_detail',
                'tables': ['inspectionQuestion', 'inspectionQuestionAnswer'],
                'filters': [],  # No filters for structural match
                'confidence': 0.95,
                'strategy': 'primary'
            }
        ]
        
        result = format_domain_context(resolutions)
        
        # Should include concept and tables
        self.assertIn("Concept: 'inspection_questions'", result)
        self.assertIn("Tables needed: inspectionQuestion, inspectionQuestionAnswer", result)
        self.assertIn("Structural grouping (no filters needed)", result)
        self.assertIn("Confidence: 0.95", result)
        
        # Should NOT have "Filters to apply:" section
        self.assertNotIn("Filters to apply:", result)

    def test_domain_registry_has_inspection_questions(self):
        """Test that domain registry includes new inspection_questions term"""
        ontology = DomainOntology()
        
        # Check that the term exists
        terms = ontology.get_all_domain_terms()
        self.assertIn('inspection_questions', terms)
        self.assertIn('safety_questions', terms)
        self.assertIn('service_questions', terms)
        
        # Check that it resolves correctly
        resolution = ontology.resolve_domain_term('inspection_questions')
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.term, 'inspection_questions')
        self.assertEqual(resolution.entity, 'inspection_detail')
        self.assertIn('inspectionQuestion', resolution.tables)
        self.assertIn('inspectionQuestionAnswer', resolution.tables)
        self.assertEqual(len(resolution.filters), 0)  # Structural match has no filters
        self.assertEqual(resolution.confidence, 0.95)

    def test_empty_resolutions(self):
        """Test that empty resolutions return empty strings"""
        self.assertEqual(format_domain_context_for_table_selection([]), "")
        self.assertEqual(format_domain_context([]), "")

    def test_multiple_resolutions(self):
        """Test formatting multiple domain resolutions"""
        resolutions = [
            {
                'term': 'crane',
                'entity': 'asset',
                'tables': ['asset'],
                'filters': [
                    {
                        'table': 'asset',
                        'column': 'name',
                        'operator': 'LIKE',
                        'value': '%crane%',
                        'case_insensitive': True
                    }
                ],
                'confidence': 0.95,
                'strategy': 'primary'
            },
            {
                'term': 'inspection_questions',
                'entity': 'inspection_detail',
                'tables': ['inspectionQuestion', 'inspectionQuestionAnswer'],
                'filters': [],
                'confidence': 0.95,
                'strategy': 'primary'
            }
        ]
        
        # Test table selection format
        result_table = format_domain_context_for_table_selection(resolutions)
        self.assertIn("Concept: 'crane'", result_table)
        self.assertIn("Concept: 'inspection_questions'", result_table)
        self.assertNotIn("Filters to apply:", result_table)
        
        # Test full format
        result_full = format_domain_context(resolutions)
        self.assertIn("Concept: 'crane'", result_full)
        self.assertIn("Concept: 'inspection_questions'", result_full)
        self.assertIn("Filters to apply:", result_full)  # Only for crane
        self.assertIn("Structural grouping", result_full)  # For inspection_questions


if __name__ == '__main__':
    unittest.main()
