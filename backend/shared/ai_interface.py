"""
Unified AI interface for MUN-Connect platform.
This module provides a standardized way to interact with different AI providers.
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Union, Any, Callable
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProvider:
    """Base class for AI providers"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI provider"""
        self.api_key = api_key or os.environ.get(self._get_api_key_env())
        if not self.api_key:
            logger.warning(f"No API key provided for {self.__class__.__name__}")
    
    def _get_api_key_env(self) -> str:
        """Get the environment variable name for the API key"""
        raise NotImplementedError
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response to the prompt"""
        raise NotImplementedError
    
    def generate_with_structure(self, prompt: str, output_schema: Dict, **kwargs) -> Dict:
        """Generate a structured response according to the schema"""
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI API provider"""
    
    def _get_api_key_env(self) -> str:
        return "OPENAI_API_KEY"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate(self, prompt: str, model: str = "gpt-4", temperature: float = 0.7, 
                max_tokens: int = 1000, **kwargs) -> str:
        """Generate a response using OpenAI API"""
        try:
            import openai
            openai.api_key = self.api_key
            
            logger.info(f"Sending prompt to OpenAI ({model})")
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider"""
    
    def _get_api_key_env(self) -> str:
        return "ANTHROPIC_API_KEY"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate(self, prompt: str, model: str = "claude-3-sonnet-20240229", 
                temperature: float = 0.7, max_tokens: int = 1000, **kwargs) -> str:
        """Generate a response using Anthropic API"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "content-type": "application/json"
            }
            
            data = {
                "model": model,
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "temperature": temperature,
                "max_tokens_to_sample": max_tokens,
                **kwargs
            }
            
            logger.info(f"Sending prompt to Anthropic ({model})")
            response = requests.post(
                "https://api.anthropic.com/v1/complete",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
                
            return response.json().get("completion", "")
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise


class LocalModelProvider(AIProvider):
    """Local model provider using HuggingFace Transformers"""
    
    def _get_api_key_env(self) -> str:
        return "HF_API_KEY"  # Not strictly needed for local models
    
    def __init__(self, model_path: str = "mistralai/Mistral-7B-Instruct-v0.2", 
                 device: str = "cuda", api_key: Optional[str] = None):
        """Initialize the local model provider"""
        super().__init__(api_key)
        self.model_path = model_path
        self.device = device
        self.model = None
        self.tokenizer = None
    
    def _load_model(self):
        """Load the model and tokenizer"""
        if self.model is None or self.tokenizer is None:
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                import torch
                
                logger.info(f"Loading model: {self.model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path, 
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                )
                
                if torch.cuda.is_available() and self.device == "cuda":
                    self.model = self.model.to("cuda")
                    
                logger.info(f"Model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                raise
    
    def generate(self, prompt: str, temperature: float = 0.7, 
                max_tokens: int = 1000, **kwargs) -> str:
        """Generate a response using local model"""
        try:
            import torch
            
            self._load_model()
            
            logger.info(f"Generating response with local model")
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available() and self.device == "cuda":
                inputs = inputs.to("cuda")
            
            generation_config = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": temperature > 0,
                **kwargs
            }
            
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **generation_config)
                
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the prompt from the response
            if response.startswith(prompt):
                response = response[len(prompt):].strip()
                
            return response
        except Exception as e:
            logger.error(f"Local model error: {str(e)}")
            raise


class AIInterface:
    """Unified interface for AI interactions"""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "local": LocalModelProvider,
    }
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None, 
                default_model: Optional[str] = None, **provider_kwargs):
        """Initialize the AI interface"""
        if provider not in self.PROVIDERS:
            raise ValueError(f"Provider {provider} not supported. Available providers: {list(self.PROVIDERS.keys())}")
            
        self.provider_name = provider
        self.provider = self.PROVIDERS[provider](api_key, **provider_kwargs)
        self.default_model = default_model
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response to the prompt"""
        if self.default_model and "model" not in kwargs:
            kwargs["model"] = self.default_model
            
        return self.provider.generate(prompt, **kwargs)
    
    def generate_with_template(self, template: str, variables: Dict[str, Any], **kwargs) -> str:
        """Generate a response using a template"""
        from string import Template
        prompt = Template(template).safe_substitute(variables)
        return self.generate(prompt, **kwargs)
    
    def generate_with_validation(self, prompt: str, validator: Callable[[str], bool], 
                                max_attempts: int = 3, **kwargs) -> str:
        """Generate a response and validate it, retrying if validation fails"""
        for attempt in range(max_attempts):
            response = self.generate(prompt, **kwargs)
            if validator(response):
                return response
            logger.warning(f"Validation failed on attempt {attempt+1}/{max_attempts}, retrying...")
        
        logger.error(f"Failed to generate valid response after {max_attempts} attempts")
        return response  # Return the last response even though validation failed

    def generate_structured_output(self, prompt: str, output_format: str, **kwargs) -> Union[Dict, List]:
        """Generate structured output (JSON or YAML)"""
        format_instruction = f"\nReturn your response as valid {output_format.upper()}."
        full_prompt = prompt + format_instruction
        
        response = self.generate(full_prompt, **kwargs)
        
        # Try to extract and parse the structured output
        try:
            if output_format.lower() == "json":
                # Try to extract JSON from the response if it's wrapped in markdown code blocks
                if "```json" in response.lower():
                    json_content = response.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_content)
                # Otherwise try to parse the whole response
                return json.loads(response)
            elif output_format.lower() == "yaml":
                import yaml
                if "```yaml" in response.lower():
                    yaml_content = response.split("```yaml")[1].split("```")[0].strip()
                    return yaml.safe_load(yaml_content)
                return yaml.safe_load(response)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
        except Exception as e:
            logger.error(f"Failed to parse {output_format} response: {str(e)}")
            logger.debug(f"Response: {response}")
            raise 