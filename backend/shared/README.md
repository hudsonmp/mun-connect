# Standardized AI Integration

This module provides a unified interface for interacting with different AI providers in the MUN Connect platform. It standardizes prompt formats, handles error retries, and provides utilities for validation and structured outputs.

## Components

### AI Interface

The core component is the `AIInterface` class in `ai_interface.py`, which provides a unified way to interact with different AI providers:

```python
from shared.ai_interface import AIInterface

# Create an interface with the default provider (OpenAI)
ai = AIInterface()

# Generate a response
response = ai.generate("What is Model UN?")

# Create with a specific provider and model
ai = AIInterface(provider="anthropic", default_model="claude-3-sonnet-20240229")
```

### AI Providers

The module supports several AI providers out of the box:

- `OpenAIProvider`: Connects to OpenAI's GPT models
- `AnthropicProvider`: Connects to Anthropic's Claude models
- `LocalModelProvider`: Uses local Hugging Face models

### Prompt Templates

Standardized prompt templates are available in `prompt_templates.py`:

```python
from shared.ai_interface import AIInterface
from shared.prompt_templates import SUMMARY_TEMPLATE

ai = AIInterface()
variables = {
    "topic": "Climate Change",
    "text": "Long text to summarize..."
}

summary = ai.generate_with_template(SUMMARY_TEMPLATE, variables)
```

### Validators

The `validators.py` module provides functions to validate AI responses:

```python
from shared.ai_interface import AIInterface
from shared.validators import is_valid_json

ai = AIInterface()
json_response = ai.generate_with_validation(
    "Create a JSON object with name and age fields",
    validator=is_valid_json
)
```

## Usage Examples

### Basic Text Generation

```python
from shared.ai_interface import AIInterface

ai = AIInterface(provider="openai", default_model="gpt-4o-mini")
response = ai.generate(
    "Explain the concept of sovereignty in international relations",
    temperature=0.7,
    max_tokens=500
)
print(response)
```

### Template-Based Generation

```python
from shared.ai_interface import AIInterface
from shared.prompt_templates import POSITION_PAPER_GENERATION_TEMPLATE

ai = AIInterface()
variables = {
    "country": "Sweden",
    "topic": "Nuclear Disarmament",
    "formality_level": "4",
    "persuasive_techniques": "logical reasoning, historical examples",
    "evidence_types": "historical treaties, recent statistics",
    "sentence_complexity": "medium to high",
    "vocabulary_patterns": "formal diplomatic terms",
    "background_info": "Sweden has been a neutral country..."
}

position_paper = ai.generate_with_template(
    POSITION_PAPER_GENERATION_TEMPLATE,
    variables,
    temperature=0.5
)
```

### Generating Structured Output

```python
from shared.ai_interface import AIInterface

ai = AIInterface()
json_data = ai.generate_structured_output(
    "Create a diplomatic profile for the United Kingdom in the Security Council",
    output_format="json"
)
```

### Response Validation

```python
from shared.ai_interface import AIInterface
from shared.validators import has_required_sections

ai = AIInterface()
summary = ai.generate_with_validation(
    "Summarize this text with sections for CONTEXT, ANALYSIS, and RECOMMENDATIONS: ...",
    validator=lambda text: has_required_sections(text, ["CONTEXT", "ANALYSIS", "RECOMMENDATIONS"]),
    max_attempts=3
)
```

## Configuration

API keys can be provided in several ways:

1. Directly to the constructor:
   ```python
   ai = AIInterface(provider="openai", api_key="your-api-key")
   ```

2. Through environment variables:
   - `OPENAI_API_KEY` for OpenAI
   - `ANTHROPIC_API_KEY` for Anthropic
   - `HF_API_KEY` for Hugging Face (local models)

## Error Handling

The interface includes built-in retry logic for transient errors and comprehensive error logging.

## Testing

Unit tests are available in `tests/test_ai_interface.py` and can be run with:

```bash
python -m unittest backend.tests.test_ai_interface
``` 