"""
Unit tests for the AI interface module.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from ..shared.ai_interface import AIInterface, OpenAIProvider, AnthropicProvider
from ..shared.prompt_templates import SUMMARY_TEMPLATE
from ..shared.validators import is_valid_json

class TestAIInterface(unittest.TestCase):
    """Tests for the AIInterface class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Store original environment variables to restore later
        self.original_openai_key = os.environ.get("OPENAI_API_KEY")
        self.original_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        
        # Set test API keys
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Restore original environment variables
        if self.original_openai_key:
            os.environ["OPENAI_API_KEY"] = self.original_openai_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
            
        if self.original_anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = self.original_anthropic_key
        else:
            os.environ.pop("ANTHROPIC_API_KEY", None)
    
    @patch('openai.ChatCompletion.create')
    def test_openai_provider(self, mock_create):
        """Test the OpenAI provider."""
        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response"
        mock_create.return_value = mock_response
        
        # Create a provider and generate a response
        provider = OpenAIProvider()
        response = provider.generate("test prompt", model="gpt-4")
        
        # Check that the response is correct
        self.assertEqual(response, "This is a test response")
        
        # Check that the API was called with the correct arguments
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        self.assertEqual(kwargs["model"], "gpt-4")
        self.assertEqual(kwargs["messages"][0]["content"], "test prompt")
    
    @patch('requests.post')
    def test_anthropic_provider(self, mock_post):
        """Test the Anthropic provider."""
        # Mock the Anthropic API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"completion": "This is a test response"}
        mock_post.return_value = mock_response
        
        # Create a provider and generate a response
        provider = AnthropicProvider()
        response = provider.generate("test prompt", model="claude-3-sonnet-20240229")
        
        # Check that the response is correct
        self.assertEqual(response, "This is a test response")
        
        # Check that the API was called with the correct arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "claude-3-sonnet-20240229")
        self.assertIn("test prompt", kwargs["json"]["prompt"])
    
    @patch('openai.ChatCompletion.create')
    def test_ai_interface_template(self, mock_create):
        """Test template-based generation."""
        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response"
        mock_create.return_value = mock_response
        
        # Create an interface and generate a response
        interface = AIInterface(provider="openai")
        variables = {"topic": "test topic", "text": "test text"}
        response = interface.generate_with_template(SUMMARY_TEMPLATE, variables)
        
        # Check that the response is correct
        self.assertEqual(response, "This is a test response")
        
        # Verify the template was properly filled
        args, kwargs = mock_create.call_args
        self.assertIn("test topic", kwargs["messages"][0]["content"])
        self.assertIn("test text", kwargs["messages"][0]["content"])
    
    @patch('openai.ChatCompletion.create')
    def test_ai_interface_validation(self, mock_create):
        """Test validation-based generation."""
        # Set up a sequence of responses, first invalid then valid
        mock_response1 = MagicMock()
        mock_response1.choices = [MagicMock()]
        mock_response1.choices[0].message.content = "Not valid JSON"
        
        mock_response2 = MagicMock()
        mock_response2.choices = [MagicMock()]
        mock_response2.choices[0].message.content = '{"key": "value"}'
        
        mock_create.side_effect = [mock_response1, mock_response2]
        
        # Create an interface and generate a response with validation
        interface = AIInterface(provider="openai")
        response = interface.generate_with_validation(
            "Create JSON", 
            validator=is_valid_json
        )
        
        # Check that the valid response was returned
        self.assertEqual(response, '{"key": "value"}')
        
        # Verify the API was called twice
        self.assertEqual(mock_create.call_count, 2)
    
    @patch('openai.ChatCompletion.create')
    def test_structured_output(self, mock_create):
        """Test structured output generation."""
        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value", "array": [1, 2, 3]}'
        mock_create.return_value = mock_response
        
        # Create an interface and generate structured output
        interface = AIInterface(provider="openai")
        result = interface.generate_structured_output(
            "Create a JSON object", 
            output_format="json"
        )
        
        # Check that the result is properly parsed
        self.assertIsInstance(result, dict)
        self.assertEqual(result["key"], "value")
        self.assertEqual(result["array"], [1, 2, 3])
        
        # Verify format instructions were added to the prompt
        args, kwargs = mock_create.call_args
        self.assertIn("JSON", kwargs["messages"][0]["content"])

if __name__ == '__main__':
    unittest.main() 