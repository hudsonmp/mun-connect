#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MUN-Connect Integration Test

This script tests the integration between the different modules of the MUN-Connect platform,
verifying that they work together correctly after implementing the adapter functions
and standardized interfaces.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any
import logging
import numpy as np

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import shared utilities
from shared import get_logger, set_request_context

# Import modules to test
from background_guide.processor import BackgroundGuideProcessor
from mind_map.mind_map_generator import MindMapGenerator
from user_context.delegate_profile import DelegateProfile

# Set up logger for testing
logger = get_logger("integration_test")
set_request_context("test-request-id", "test-user-id")

class MockSupabaseClient:
    """Mock Supabase client for testing"""
    
    def __init__(self):
        self.data = {}
        self.tables = {}
    
    def table(self, name):
        """Create a mock table"""
        if name not in self.tables:
            self.tables[name] = MockTable(name)
        return self.tables[name]

class MockTable:
    """Mock table for testing"""
    
    def __init__(self, name):
        self.name = name
        self.data = []
        self._filters = []
    
    def select(self, *columns):
        """Mock select operation"""
        self._columns = columns if columns else "*"
        return self
    
    def eq(self, column, value):
        """Mock equality filter"""
        self._filters.append(("eq", column, value))
        return self
    
    def execute(self):
        """Mock execution"""
        # Filter data based on filters
        filtered_data = self.data.copy()
        for filter_type, column, value in self._filters:
            if filter_type == "eq":
                filtered_data = [item for item in filtered_data if item.get(column) == value]
        
        result = MagicMock()
        result.data = filtered_data
        return result
    
    def insert(self, data):
        """Mock insert operation"""
        self._data_to_insert = data
        return self
    
    def update(self, data):
        """Mock update operation"""
        self._data_to_update = data
        return self
    
    def delete(self):
        """Mock delete operation"""
        return self
    
    def execute(self):
        """Mock execution"""
        if hasattr(self, "_data_to_insert"):
            data = self._data_to_insert.copy()
            data["id"] = len(self.data) + 1
            self.data.append(data)
            result = MagicMock()
            result.data = [data]
            delattr(self, "_data_to_insert")
            return result
        
        if hasattr(self, "_data_to_update"):
            # Update existing data based on filters
            for filter_type, column, value in self._filters:
                if filter_type == "eq":
                    for item in self.data:
                        if item.get(column) == value:
                            item.update(self._data_to_update)
            
            # Get updated data
            filtered_data = []
            for filter_type, column, value in self._filters:
                if filter_type == "eq":
                    filtered_data.extend([item for item in self.data if item.get(column) == value])
            
            result = MagicMock()
            result.data = filtered_data
            delattr(self, "_data_to_update")
            return result
        
        # Default execution for select
        filtered_data = self.data.copy()
        for filter_type, column, value in self._filters:
            if filter_type == "eq":
                filtered_data = [item for item in filtered_data if item.get(column) == value]
        
        result = MagicMock()
        result.data = filtered_data
        self._filters = []
        return result

class IntegrationTest(unittest.TestCase):
    """Test integration between MUN-Connect modules"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test directory
        os.makedirs("test_output", exist_ok=True)
        
        # Set up mock Supabase client
        self.mock_supabase = MockSupabaseClient()
        
        # Sample background guide content
        self.sample_bg_content = """
        DISEC: Disarmament and International Security Committee
        
        Topic: Regulation of Autonomous Weapons Systems
        
        Introduction:
        The rapid development of autonomous weapons systems raises significant ethical, legal, and security concerns for the international community. This background guide explores the key issues surrounding these weapons systems and the efforts to regulate them.
        
        Section 1: Definition and Current Technology
        Autonomous weapons systems, often referred to as "killer robots," are weapons that can select and engage targets without human intervention. Current technologies include advanced drones, sentry guns, and missile defense systems with varying degrees of autonomy.
        
        Section 2: Legal Framework
        The existing legal framework governing autonomous weapons includes International Humanitarian Law, the Geneva Conventions, and the Martens Clause. However, there are significant gaps in addressing fully autonomous weapons.
        
        Section 3: Ethical Considerations
        Key ethical issues include accountability, distinction between civilians and combatants, and the dignity of human life. Many argue that life-or-death decisions should not be delegated to machines.
        
        Section 4: Country Positions
        Countries have diverse positions on regulation. The United States supports developing autonomous weapons with appropriate safeguards, while China advocates restrictions. Russia opposes binding limitations, and smaller nations often favor complete bans.
        
        Section 5: Potential Solutions
        Potential approaches include a complete ban on autonomous weapons, regulations requiring meaningful human control, verification mechanisms, and transparency measures for development programs.
        """
        
        # Create temporary files
        with open("test_output/sample_bg.txt", "w") as f:
            f.write(self.sample_bg_content)
    
    def tearDown(self):
        """Clean up after tests"""
        # In a real implementation, we would clean up test files here
        pass
    
    @patch("background_guide.processor.extract_text_from_pdf")
    @patch("background_guide.processor.create_vector_index")
    def test_processor_to_mind_map_integration(self, mock_create_index, mock_extract_text):
        """Test integration between background guide processor and mind map generator"""
        # Set up mocks
        mock_extract_text.return_value = self.sample_bg_content
        mock_create_index.return_value = {"path": "test_output/index", "dimensions": 768, "num_vectors": 5}
        
        # Initialize processor with minimal dependencies
        processor = BackgroundGuideProcessor(
            use_openai_for_summary=False,
            use_aws_model=False,
            output_dir="test_output"
        )
        
        # Process test file
        with patch("background_guide.processor.segment_document") as mock_segment:
            # Mock segmentation to avoid loading models
            mock_segment.return_value = [
                {"section": "Introduction", "text": "The rapid development of autonomous weapons systems...", "id": "1"},
                {"section": "Section 1", "text": "Autonomous weapons systems, often referred to as 'killer robots'...", "id": "2"},
                {"section": "Section 2", "text": "The existing legal framework governing autonomous weapons...", "id": "3"},
                {"section": "Section 3", "text": "Key ethical issues include accountability...", "id": "4"},
                {"section": "Section 4", "text": "Countries have diverse positions on regulation...", "id": "5"}
            ]
            
            with patch("background_guide.processor.summarize_content") as mock_summarize:
                # Mock summarization to avoid API calls
                mock_summarize.side_effect = [
                    "Overview of autonomous weapons regulation debate.", 
                    "Defines autonomous weapons and describes current technology.",
                    "Discusses legal frameworks with gaps.",
                    "Examines ethical issues of machine decisions.",
                    "Outlines country positions on regulation."
                ]
                
                # Process file
                result = processor.process_file("test_output/sample_bg.txt")
                
                # Check that processing was successful
                self.assertIn("segments", result)
                self.assertIn("summaries", result)
                self.assertEqual(len(result["segments"]), 5)
                
                # Get standardized output
                standardized = processor.get_standardized_output()
                
                # Check standardized output format
                self.assertIn("metadata", standardized)
                self.assertIn("segments", standardized)
                self.assertIn("summaries", standardized)
                self.assertEqual(standardized["metadata"]["committee"], "DISEC")
                self.assertEqual(standardized["metadata"]["topic"], "Regulation of Autonomous Weapons Systems")
        
        # Initialize mind map generator with mock
        with patch("mind_map.mind_map_generator.AutoModel") as mock_model:
            with patch("mind_map.mind_map_generator.AutoTokenizer") as mock_tokenizer:
                # Set up mind map generator
                mind_map_gen = MindMapGenerator()
                
                # Mock embedding generation
                mind_map_gen._generate_embedding = MagicMock(return_value=np.zeros(768))
                mind_map_gen._cosine_similarity = MagicMock(return_value=0.8)
                
                # Generate mind map from processor output
                mind_map = mind_map_gen.generate_from_processor_output(standardized)
                
                # Check that mind map was created correctly
                self.assertIn("topics", mind_map)
                self.assertIn("metadata", mind_map)
                self.assertEqual(mind_map["metadata"]["committee"], "DISEC")
                self.assertIn("connections", mind_map)
                self.assertIn("executive_summary", mind_map)
                
                # Test exporting for delegate profile
                export_data = mind_map_gen.export_for_delegate_profile(mind_map, "Sweden")
                
                # Check export data
                self.assertIn("base_structure", export_data)
                self.assertIn("country_positions", export_data)
    
    def test_mind_map_to_delegate_profile_integration(self):
        """Test integration between mind map generator and delegate profile"""
        # Sample mind map data
        sample_mind_map = {
            "metadata": {
                "title": "Background Guide",
                "committee": "DISEC",
                "topic": "Regulation of Autonomous Weapons Systems",
                "created_at": "2023-04-07T10:30:00"
            },
            "base_structure": {
                "topics": [
                    {
                        "title": "Definition and Technology",
                        "description": "Autonomous weapons systems and current technology.",
                        "id": "topic1"
                    },
                    {
                        "title": "Legal Framework",
                        "description": "Legal frameworks governing autonomous weapons.",
                        "id": "topic2"
                    }
                ],
                "connections": [
                    {
                        "source": "topic1",
                        "target": "topic2",
                        "strength": 0.8,
                        "description": "Legal implications of technology"
                    }
                ]
            },
            "country_positions": {
                "topic1": {
                    "position": "Sweden supports clear definitions of autonomous weapons",
                    "stance": "supportive",
                    "key_points": ["Strong definitions needed", "Technology assessment"],
                    "evidence": ["Previous statements", "UN voting record"]
                },
                "topic2": {
                    "position": "Sweden advocates for strong legal framework",
                    "stance": "supportive",
                    "key_points": ["Human control mandatory", "Accountability chains"],
                    "evidence": ["Policy statements", "Coalition membership"]
                }
            },
            "executive_summary": "Sweden maintains strong positions on regulation of autonomous weapons systems."
        }
        
        # Initialize delegate profile with mock Supabase client
        delegate_profile = DelegateProfile("00000000-0000-0000-0000-000000000001", self.mock_supabase)
        
        # Integrate mind map data
        result = delegate_profile.integrate_mind_map_data(sample_mind_map, "Sweden", "DISEC")
        
        # Check that data was integrated correctly
        self.assertEqual(result["operation"], "insert")
        self.assertEqual(len(self.mock_supabase.tables["delegate_analyses"].data), 1)
        
        # Verify profile data
        stored_data = self.mock_supabase.tables["delegate_analyses"].data[0]
        self.assertEqual(stored_data["user_id"], "00000000-0000-0000-0000-000000000001")
        self.assertEqual(stored_data["document_type"], "committee_research")
        self.assertEqual(stored_data["analysis_type"], "mind_map_analysis")
        self.assertEqual(stored_data["content"]["committee"], "DISEC")
        self.assertEqual(stored_data["content"]["country"], "Sweden")
        
        # Generate profile for document generation
        doc_profile = delegate_profile.prepare_for_document_generation()
        
        # Check that profile has all required fields
        self.assertIn("writing_style", doc_profile)
        self.assertIn("persuasion_style", doc_profile)
        self.assertIn("reasoning_approach", doc_profile)
        self.assertIn("tone", doc_profile)
        self.assertIn("content_patterns", doc_profile)

if __name__ == "__main__":
    unittest.main() 