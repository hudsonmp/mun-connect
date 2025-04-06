#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Multi-Document Generator for AWS Lambda

This module extends the position paper generator to support multiple document types:
position papers, speeches, and resolutions. It adapts the generation process based
on the document type while maintaining the ability to mimic a delegate's style.
The module is optimized for AWS Lambda execution with S3 storage integration.
"""

import os
import json
import logging
import time
import uuid
import boto3
import botocore
from typing import Dict, List, Any, Optional, Tuple, Literal, Union
from functools import lru_cache

import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    pipeline,
    set_seed
)

# Configure logging for CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define document types
DocumentType = Literal["position_paper", "speech", "resolution"]

# AWS clients
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# AWS S3 utility functions
def read_from_s3(bucket: str, key: str) -> Dict[str, Any]:
    """
    Read JSON data from S3 bucket.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Parsed JSON data
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"S3 error ({error_code}): {error_message} - Bucket: {bucket}, Key: {key}")
        raise

def write_to_s3(data: Dict[str, Any], bucket: str, key: str) -> str:
    """
    Write JSON data to S3 bucket.
    
    Args:
        data: Data to write
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        S3 URI
    """
    try:
        s3_client.put_object(
            Body=json.dumps(data, indent=2, ensure_ascii=False),
            Bucket=bucket,
            Key=key,
            ContentType='application/json'
        )
        return f"s3://{bucket}/{key}"
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"S3 error ({error_code}): {error_message} - Bucket: {bucket}, Key: {key}")
        raise

def check_s3_permissions(bucket: str) -> bool:
    """
    Check if Lambda has the necessary S3 permissions.
    
    Args:
        bucket: S3 bucket name
        
    Returns:
        True if permissions are sufficient, False otherwise
    """
    try:
        # Try to list objects (with a limit of 1) to check read permissions
        s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        
        # Try to put a small test object to check write permissions
        test_key = f"permissions_check_{uuid.uuid4()}.txt"
        s3_client.put_object(
            Body="permissions check",
            Bucket=bucket,
            Key=test_key
        )
        
        # Clean up the test object
        s3_client.delete_object(Bucket=bucket, Key=test_key)
        
        return True
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.warning(f"Insufficient S3 permissions ({error_code}): {error_message} - Bucket: {bucket}")
        return False

class MultiDocumentGenerator:
    """Generate different types of UN documents mimicking a delegate's style, optimized for AWS Lambda"""
    
    # Class-level variables for model caching
    _tokenizer = None
    _model = None
    _generator = None
    
    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
        output_bucket: Optional[str] = None,
        use_gpu: bool = False,
        max_length: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        seed: int = 42,
        load_model: bool = True,
        model_cache_dir: Optional[str] = "/mnt/efs/models" if os.path.exists("/mnt/efs") else None
    ):
        """
        Initialize the document generator for AWS Lambda.
        
        Args:
            model_name: Name of the text generation model
            output_bucket: S3 bucket for saving generated documents
            use_gpu: Whether to use GPU for generation
            max_length: Maximum length of generated text
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            seed: Random seed for reproducibility
            load_model: Whether to load model during initialization
            model_cache_dir: Directory for caching models (e.g., EFS mount)
        """
        self.model_name = model_name
        self.output_bucket = output_bucket
        self.use_gpu = use_gpu
        self.max_length = max_length
        self.temperature = temperature
        self.top_p = top_p
        self.seed = seed
        self.model_cache_dir = model_cache_dir
        
        # Set random seed for reproducibility
        set_seed(seed)
        
        # Check S3 permissions if bucket is provided
        if self.output_bucket:
            if not check_s3_permissions(self.output_bucket):
                logger.warning(f"Insufficient S3 permissions for bucket: {self.output_bucket}")
        
        # Device configuration
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Load model if requested (separate initialization from usage)
        if load_model:
            self.initialize_model()
    
    @classmethod
    def initialize_model(cls, model_name: str = None, device: str = None, model_cache_dir: str = None):
        """
        Initialize the model and tokenizer (can be called separately from constructor).
        This allows for model initialization during container startup rather than during each Lambda invocation.
        
        Args:
            model_name: Name of the text generation model
            device: Device to use ("cuda" or "cpu")
            model_cache_dir: Directory for caching models
        """
        # Skip if already initialized
        if cls._model is not None and cls._tokenizer is not None:
            logger.info("Model already initialized, skipping re-initialization")
            return
        
        if model_name is None:
            model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
        if model_cache_dir and os.path.exists(model_cache_dir):
            os.environ['TRANSFORMERS_CACHE'] = model_cache_dir
            logger.info(f"Using model cache directory: {model_cache_dir}")
        
        try:
            # Load tokenizer
            start_time = time.time()
            logger.info(f"Loading tokenizer for {model_name}...")
            cls._tokenizer = AutoTokenizer.from_pretrained(model_name)
            logger.info(f"Loaded tokenizer in {time.time() - start_time:.2f} seconds")
            
            # Load model for text generation
            start_time = time.time()
            logger.info(f"Loading model {model_name}...")
            cls._model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                low_cpu_mem_usage=True
            )
            logger.info(f"Loaded model in {time.time() - start_time:.2f} seconds")
            
            # Create text generation pipeline
            start_time = time.time()
            logger.info("Creating generation pipeline...")
            cls._generator = pipeline(
                "text-generation",
                model=cls._model,
                tokenizer=cls._tokenizer,
                device=device if device == "cuda" else -1
            )
            logger.info(f"Created pipeline in {time.time() - start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error initializing model: {e}", exc_info=True)
            raise
    
    def get_model_and_tokenizer(self):
        """
        Get the model and tokenizer, initializing if necessary.
        
        Returns:
            Tuple of (model, tokenizer, generator)
        """
        if MultiDocumentGenerator._model is None or MultiDocumentGenerator._tokenizer is None:
            self.initialize_model(
                model_name=self.model_name,
                device=self.device,
                model_cache_dir=self.model_cache_dir
            )
        
        return (
            MultiDocumentGenerator._model,
            MultiDocumentGenerator._tokenizer,
            MultiDocumentGenerator._generator
        )
    
    def generate_document(
        self, 
        delegate_profile: Union[Dict[str, Any], str],
        document_type: DocumentType = "position_paper",
        topic: Optional[str] = None,
        committee: Optional[str] = None,
        country: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        profile_s3_bucket: Optional[str] = None,
        output_s3_bucket: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a document mimicking a delegate's style.
        
        Args:
            delegate_profile: Either the delegate profile dict or an S3 key to the profile
            document_type: Type of document to generate
            topic: Optional override for the document topic
            committee: Optional override for the committee
            country: Optional override for the country
            additional_params: Additional parameters specific to document types
            profile_s3_bucket: S3 bucket containing the delegate profile
            output_s3_bucket: S3 bucket to save the generated document
            
        Returns:
            Tuple of (output path or S3 URI, generated document data)
        """
        start_time = time.time()
        
        # Determine output bucket
        output_bucket = output_s3_bucket or self.output_bucket
        if not output_bucket:
            raise ValueError("No output S3 bucket specified")
        
        # Load delegate profile from S3 if necessary
        if isinstance(delegate_profile, str):
            if not profile_s3_bucket:
                raise ValueError("S3 bucket for delegate profile not specified")
                
            logger.info(f"Loading delegate profile from S3: {profile_s3_bucket}/{delegate_profile}")
            try:
                delegate_profile = read_from_s3(profile_s3_bucket, delegate_profile)
            except Exception as e:
                logger.error(f"Error loading delegate profile: {e}", exc_info=True)
                raise
        
        logger.info(f"Generating {document_type} for {delegate_profile.get('metadata', {}).get('country', 'unknown country')}")
        
        # Extract style information and metadata
        metadata = self._extract_metadata(delegate_profile, topic, committee, country, document_type)
        style_info = self._extract_style_information(delegate_profile)
        
        # Create document-specific parameters
        doc_params = additional_params or {}
        
        # Generate prompt based on document type
        if document_type == "position_paper":
            prompt = self._create_position_paper_prompt(metadata, style_info, doc_params)
        elif document_type == "speech":
            prompt = self._create_speech_prompt(metadata, style_info, doc_params)
        elif document_type == "resolution":
            prompt = self._create_resolution_prompt(metadata, style_info, doc_params)
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        # Generate text
        generated_text = self._generate_text(prompt)
        
        # Process and structure the generated text based on document type
        if document_type == "position_paper":
            document_data = self._structure_position_paper(generated_text, metadata)
        elif document_type == "speech":
            document_data = self._structure_speech(generated_text, metadata)
        elif document_type == "resolution":
            document_data = self._structure_resolution(generated_text, metadata)
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        # Save the generated document to S3
        output_s3_key = self._save_document_to_s3(document_data, output_bucket)
        
        generation_time = time.time() - start_time
        logger.info(f"{document_type.capitalize()} generation completed in {generation_time:.2f} seconds")
        logger.info(f"Document saved to s3://{output_bucket}/{output_s3_key}")
        
        return f"s3://{output_bucket}/{output_s3_key}", document_data
    
    def _extract_metadata(
        self, 
        delegate_profile: Dict[str, Any],
        topic_override: Optional[str],
        committee_override: Optional[str],
        country_override: Optional[str],
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Extract metadata from delegate profile.
        
        Args:
            delegate_profile: Delegate profile data
            topic_override: Optional override for the document topic
            committee_override: Optional override for the committee
            country_override: Optional override for the country
            document_type: Type of document to generate
            
        Returns:
            Dictionary of metadata
        """
        # Extract profile metadata
        profile_metadata = delegate_profile.get("metadata", {})
        
        # Determine metadata values, using overrides if provided
        metadata = {
            "topic": topic_override or profile_metadata.get("topic") or profile_metadata.get("main_topic") or "Climate Change",
            "committee": committee_override or profile_metadata.get("committee") or "General Assembly",
            "country": country_override or profile_metadata.get("country") or "United Nations Member State",
            "document_type": document_type,
            "topics_discussed": profile_metadata.get("topics_discussed") or profile_metadata.get("discussed_topics") or []
        }
        
        return metadata
    
    def _extract_style_information(self, delegate_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract style information from delegate profile.
        
        Args:
            delegate_profile: Delegate profile data
            
        Returns:
            Dictionary of style information
        """
        style_info = {}
        
        # Extract writing style information
        if "writing_style" in delegate_profile:
            writing_style = delegate_profile["writing_style"]
            
            # Readability
            if "readability" in writing_style:
                readability = writing_style["readability"]
                style_info["readability"] = {
                    "flesch_reading_ease": readability.get("flesch_reading_ease", 50),
                    "flesch_kincaid_grade": readability.get("flesch_kincaid_grade", 10)
                }
            
            # Complexity
            if "complexity" in writing_style:
                complexity = writing_style["complexity"]
                style_info["complexity"] = {
                    "avg_sentence_length": complexity.get("avg_sentence_length", 20),
                    "avg_word_length": complexity.get("avg_word_length", 5),
                    "unique_word_ratio": complexity.get("unique_word_ratio", 0.6)
                }
            
            # Style markers
            if "style_markers" in writing_style:
                style_markers = writing_style["style_markers"]
                style_info["style_markers"] = {
                    "passive_voice_ratio": style_markers.get("passive_voice_ratio", 0.2),
                    "question_ratio": style_markers.get("question_ratio", 0.05),
                    "exclamation_ratio": style_markers.get("exclamation_ratio", 0.01)
                }
                
            # POS distribution
            if "pos_distribution" in writing_style:
                style_info["pos_distribution"] = writing_style["pos_distribution"]
                
            # Sentiment
            if "sentiment" in writing_style:
                style_info["sentiment"] = writing_style["sentiment"]
        
        # Extract argumentation information
        if "argumentation" in delegate_profile:
            argumentation = delegate_profile["argumentation"]
            
            style_info["argumentation"] = {
                "component_distribution": argumentation.get("component_distribution", {}),
                "premise_to_claim_ratio": argumentation.get("premise_to_claim_ratio", 2.0),
                "support_to_attack_ratio": argumentation.get("support_to_attack_ratio", 3.0),
                "reasoning_patterns": argumentation.get("reasoning_patterns", {})
            }
        
        return style_info
    
    def _create_position_paper_prompt(
        self, 
        metadata: Dict[str, Any], 
        style_info: Dict[str, Any],
        params: Dict[str, Any]
    ) -> str:
        """
        Create a prompt for generating a position paper.
        
        Args:
            metadata: Document metadata
            style_info: Style information
            params: Additional parameters
            
        Returns:
            Prompt for text generation
        """
        # Create a detailed prompt that describes the paper to generate
        prompt = f"""<s>[INST] You are a skilled writer who specializes in UN position papers. Write a position paper with the following characteristics:

- Country: {metadata['country']}
- Committee: {metadata['committee']}
- Topic: {metadata['topic']}

Your task is to generate a formal UN position paper that authentically represents this country's position on the topic.

Writing Style Guidelines:
"""
        
        # Add readability guidelines
        if "readability" in style_info:
            readability = style_info["readability"]
            prompt += f"- Write at approximately a {readability.get('flesch_kincaid_grade', 10):.1f} grade level\n"
        
        # Add complexity guidelines
        if "complexity" in style_info:
            complexity = style_info["complexity"]
            prompt += f"- Use an average sentence length of about {complexity.get('avg_sentence_length', 20):.1f} words\n"
            prompt += f"- Maintain a vocabulary diversity of about {complexity.get('unique_word_ratio', 0.6):.2f} (ratio of unique words to total words)\n"
        
        # Add style marker guidelines
        if "style_markers" in style_info:
            style_markers = style_info["style_markers"]
            passive_ratio = style_markers.get("passive_voice_ratio", 0.2)
            prompt += f"- Use passive voice in about {passive_ratio * 100:.1f}% of sentences\n"
            
            # High or low use of questions
            if style_markers.get("question_ratio", 0.05) > 0.1:
                prompt += "- Include several rhetorical questions\n"
            else:
                prompt += "- Use minimal rhetorical questions\n"
        
        # Add argumentation guidelines
        if "argumentation" in style_info:
            argumentation = style_info["argumentation"]
            
            # Determine dominant reasoning pattern
            reasoning_patterns = argumentation.get("reasoning_patterns", {})
            if reasoning_patterns:
                # Find the most common reasoning pattern
                dominant_pattern = max(reasoning_patterns.items(), key=lambda x: x[1])[0]
                prompt += f"- Primarily use {dominant_pattern} reasoning in your arguments\n"
            
            # Add guidelines for support vs attack
            support_ratio = argumentation.get("support_to_attack_ratio", 3.0)
            if support_ratio > 2.0:
                prompt += "- Focus more on supporting your position than criticizing others\n"
            else:
                prompt += "- Balance between supporting your position and addressing opposing views\n"
        
        # Add paper structure guidelines
        prompt += """
Paper Structure:
1. Introduction: Briefly introduce the topic and your country's position
2. Background: Provide relevant context about the issue
3. Country Position: Elaborate on your country's stance with specific points
4. Previous Actions: Discuss what your country has done related to this issue
5. Proposed Solutions: Present your country's proposed solutions
6. Conclusion: Summarize your position and call to action

Make the position paper about 1000-1500 words long, divided into clear sections.
Ensure the content is factual, diplomatic, and presented in a formal UN style.
[/INST]</s>"""
        
        return prompt
    
    def _create_speech_prompt(
        self, 
        metadata: Dict[str, Any], 
        style_info: Dict[str, Any],
        params: Dict[str, Any]
    ) -> str:
        """
        Create a prompt for generating a speech.
        
        Args:
            metadata: Document metadata
            style_info: Style information
            params: Additional parameters
            
        Returns:
            Prompt for text generation
        """
        # Extract speech-specific parameters
        speech_length = params.get("speech_length", "5-7 minutes")
        occasion = params.get("occasion", "General Debate")
        is_opening = params.get("is_opening", True)
        
        # Create a detailed prompt that describes the speech to generate
        prompt = f"""<s>[INST] You are a skilled writer who specializes in UN speeches. Write a diplomatic speech with the following characteristics:

- Country: {metadata['country']}
- Committee: {metadata['committee']}
- Topic: {metadata['topic']}
- Occasion: {occasion}
- Length: {speech_length}

Your task is to generate a formal UN speech that would be delivered by the delegate of {metadata['country']} addressing {metadata['topic']}.

Writing Style Guidelines:
"""
        
        # Add readability guidelines
        if "readability" in style_info:
            readability = style_info["readability"]
            prompt += f"- Write at approximately a {readability.get('flesch_kincaid_grade', 10):.1f} grade level\n"
        
        # Add complexity guidelines
        if "complexity" in style_info:
            complexity = style_info["complexity"]
            prompt += f"- Use an average sentence length of about {complexity.get('avg_sentence_length', 20):.1f} words\n"
        
        # Add style marker guidelines
        if "style_markers" in style_info:
            style_markers = style_info["style_markers"]
            
            # Rhetorical questions (speeches often use more)
            question_ratio = style_markers.get("question_ratio", 0.05)
            prompt += f"- Include {'several' if question_ratio > 0.05 else 'a few'} rhetorical questions\n"
            
            # Exclamations (speeches may use more)
            exclamation_ratio = style_markers.get("exclamation_ratio", 0.01)
            prompt += f"- Use {'occasional' if exclamation_ratio > 0.02 else 'minimal'} emphatic statements\n"
        
        # Add argumentation guidelines
        if "argumentation" in style_info:
            argumentation = style_info["argumentation"]
            
            # Determine dominant reasoning pattern
            reasoning_patterns = argumentation.get("reasoning_patterns", {})
            if reasoning_patterns:
                # Find the most common reasoning pattern
                dominant_pattern = max(reasoning_patterns.items(), key=lambda x: x[1])[0]
                prompt += f"- Primarily use {dominant_pattern} reasoning in your arguments\n"
        
        # Add speech-specific guidelines
        prompt += """
Speech Structure:
1. Opening Formalities: Begin with "Thank you Mr./Madam Chair" or appropriate greeting
2. Introduction: Briefly introduce the topic and its importance
3. Country's Perspective: Present your country's view on the issue
4. Key Points: Present 3-5 main points with supporting evidence
5. Call to Action: What your country proposes should be done
6. Conclusion: Summarize and thank the audience

Speech Characteristics:
- Use more direct and engaging language than a written document
- Include appropriate transitions between sections
- Use diplomatic language that is both assertive and respectful
- Address the audience directly at key moments
- Close with a clear, memorable statement

Make the speech sound natural when spoken aloud while maintaining formal diplomatic tone.
[/INST]</s>"""
        
        return prompt
    
    def _create_resolution_prompt(
        self, 
        metadata: Dict[str, Any], 
        style_info: Dict[str, Any],
        params: Dict[str, Any]
    ) -> str:
        """
        Create a prompt for generating a resolution.
        
        Args:
            metadata: Document metadata
            style_info: Style information
            params: Additional parameters
            
        Returns:
            Prompt for text generation
        """
        # Extract resolution-specific parameters
        resolution_type = params.get("resolution_type", "Draft Resolution")
        co_sponsors = params.get("co_sponsors", [])
        resolution_number = params.get("resolution_number", "")
        
        # Format co-sponsors list if available
        co_sponsors_text = ""
        if co_sponsors:
            co_sponsors_text = ", ".join(co_sponsors)
            co_sponsors_text = f"Co-sponsors: {co_sponsors_text}\n"
        
        # Create a detailed prompt that describes the resolution to generate
        prompt = f"""<s>[INST] You are a skilled writer who specializes in UN resolutions. Write a {resolution_type} with the following characteristics:

- Committee: {metadata['committee']}
- Topic: {metadata['topic']}
- Main Submitter: {metadata['country']}
{co_sponsors_text}
Your task is to generate a formal UN resolution that follows the strict formatting and style requirements of United Nations resolutions.

Writing Style Guidelines:
"""
        
        # Add style guidelines relevant to resolutions
        prompt += """- Use formal, precise language
- Maintain objective tone throughout
- Use standard UN resolution terminology
- Follow proper resolution formatting structure
"""
        
        # Add resolution-specific structure
        prompt += f"""
Resolution Structure:
1. Heading: Clearly indicate "{metadata['committee']}" at the top, followed by "{resolution_type}" and resolution number if assigned
2. Preambulatory Clauses: 5-10 clauses that provide context and rationale
3. Operative Clauses: 8-15 specific actions, recommendations, or decisions

Formatting Rules:
- Preambulatory clauses begin with italicized phrases like "Recalling," "Deeply concerned," "Recognizing," etc., and end with commas
- Operative clauses begin with underlined verbs like "Decides," "Requests," "Calls upon," etc., are numbered, and end with semicolons
- The final operative clause ends with a period
- Each clause should be a single sentence, however long and complex

Important Resolution Terminology:
- Preambulatory phrases: Affirming, Alarmed by, Aware of, Bearing in mind, Believing, Cognizant, Concerned, Confident, Contemplating, Convinced, Declaring, Deeply concerned, Deeply conscious, Deeply convinced, Deeply disturbed, Deeply regretting, Desiring, Emphasizing, Expecting, Expressing appreciation, Expressing satisfaction, Fulfilling, Fully alarmed, Fully aware, Fully believing, Further deploring, Further recalling, Guided by, Having adopted, Having considered, Having examined, Having heard, Having received, Having studied, Keeping in mind, Noting with regret, Noting with satisfaction, Noting with deep concern, Noting further, Noting with approval, Observing, Realizing, Reaffirming, Recalling, Recognizing, Referring, Seeking, Taking into account, Taking into consideration, Taking note, Viewing with appreciation, Welcoming

- Operative phrases: Accepts, Affirms, Approves, Authorizes, Calls upon, Condemns, Confirms, Congratulates, Considers, Declares accordingly, Deplores, Designates, Draws attention, Emphasizes, Encourages, Endorses, Expresses its appreciation, Expresses its hope, Further invites, Further proclaims, Further reminds, Further recommends, Further requests, Further resolves, Has resolved, Notes, Proclaims, Reaffirms, Recommends, Regrets, Reminds, Requests, Solemnly affirms, Strongly condemns, Supports, Takes note of, Transmits, Trusts

Generate a complete resolution following these guidelines.
[/INST]</s>"""
        
        return prompt
    
    def _generate_text(self, prompt: str) -> str:
        """
        Generate text using the model.
        
        Args:
            prompt: Generation prompt
            
        Returns:
            Generated text
        """
        logger.info("Generating text...")
        
        try:
            # Get generator, initializing if necessary
            _, _, generator = self.get_model_and_tokenizer()
            
            # Start generation timing
            start_time = time.time()
            
            # Generate text
            response = generator(
                prompt,
                max_length=self.max_length,
                do_sample=True,
                temperature=self.temperature,
                top_p=self.top_p,
                pad_token_id=MultiDocumentGenerator._tokenizer.eos_token_id,
                num_return_sequences=1
            )
            
            generation_time = time.time() - start_time
            
            # Extract generated text
            generated_text = response[0]["generated_text"]
            
            # Remove the prompt from the generated text
            if prompt in generated_text:
                generated_text = generated_text.replace(prompt, "").strip()
            
            # Clean up any model-specific markers
            generated_text = self._clean_generated_text(generated_text)
            
            logger.info(f"Generated {len(generated_text)} characters in {generation_time:.2f} seconds")
            return generated_text
            
        except Exception as e:
            logger.error(f"Error generating text: {e}", exc_info=True)
            # Return error details for debugging
            return f"Error generating document: {str(e)}"
    
    def _clean_generated_text(self, text: str) -> str:
        """
        Clean up generated text.
        
        Args:
            text: Generated text
            
        Returns:
            Cleaned text
        """
        # Remove model-specific markers and formatting artifacts
        text = text.replace("<s>", "").replace("</s>", "")
        text = text.replace("[INST]", "").replace("[/INST]", "")
        
        # Remove any trailing incomplete sentences
        if text.rfind(".") > 0:
            text = text[:text.rfind(".")+1]
        
        return text.strip()
    
    def _structure_position_paper(self, generated_text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure the generated text into a position paper.
        
        Args:
            generated_text: Generated text
            metadata: Document metadata
            
        Returns:
            Structured position paper data
        """
        # Split text into sections based on headers or newlines
        sections = self._extract_sections(generated_text)
        
        # Split sections into paragraphs
        paragraphs = []
        for section in sections:
            section_paragraphs = [p.strip() for p in section["content"].split("\n\n") if p.strip()]
            paragraphs.extend(section_paragraphs)
        
        # Split text into sentences
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        from nltk.tokenize import sent_tokenize
        
        sentences = []
        for paragraph in paragraphs:
            paragraph_sentences = sent_tokenize(paragraph)
            sentences.extend(paragraph_sentences)
        
        # Create paper data structure
        paper_data = {
            "metadata": {
                "document_type": "position_paper",
                "committee": metadata["committee"],
                "country": metadata["country"],
                "main_topic": metadata["topic"],
                "discussed_topics": metadata["topics_discussed"],
                "generated": True,
                "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model_used": self.model_name
            },
            "content": {
                "full_text": generated_text,
                "sections": sections,
                "paragraphs": paragraphs,
                "sentences": sentences
            },
            "generation_info": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_length": self.max_length,
                "seed": self.seed
            }
        }
        
        return paper_data
    
    def _structure_speech(self, generated_text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure the generated text into a speech.
        
        Args:
            generated_text: Generated text
            metadata: Document metadata
            
        Returns:
            Structured speech data
        """
        # For speeches, we need to identify sections like opening, body, conclusion
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        from nltk.tokenize import sent_tokenize
        
        # Split speech into paragraphs
        paragraphs = [p.strip() for p in generated_text.split("\n\n") if p.strip()]
        
        # Identify speech sections
        sections = []
        if paragraphs:
            # First paragraph is typically the opening formalities
            sections.append({
                "title": "Opening Formalities",
                "type": "opening",
                "content": paragraphs[0]
            })
            
            # Middle paragraphs form the body
            body_paragraphs = paragraphs[1:-1] if len(paragraphs) > 2 else []
            if body_paragraphs:
                body_content = "\n\n".join(body_paragraphs)
                sections.append({
                    "title": "Body",
                    "type": "body",
                    "content": body_content
                })
            
            # Last paragraph is typically the conclusion
            if len(paragraphs) > 1:
                sections.append({
                    "title": "Conclusion",
                    "type": "conclusion",
                    "content": paragraphs[-1]
                })
        
        # Split text into sentences
        sentences = []
        for paragraph in paragraphs:
            paragraph_sentences = sent_tokenize(paragraph)
            sentences.extend(paragraph_sentences)
        
        # Create speech data structure
        speech_data = {
            "metadata": {
                "document_type": "speech",
                "committee": metadata["committee"],
                "country": metadata["country"],
                "main_topic": metadata["topic"],
                "discussed_topics": metadata["topics_discussed"],
                "generated": True,
                "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model_used": self.model_name
            },
            "content": {
                "full_text": generated_text,
                "sections": sections,
                "paragraphs": paragraphs,
                "sentences": sentences
            },
            "generation_info": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_length": self.max_length,
                "seed": self.seed
            }
        }
        
        return speech_data
    
    def _structure_resolution(self, generated_text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure the generated text into a resolution.
        
        Args:
            generated_text: Generated text
            metadata: Document metadata
            
        Returns:
            Structured resolution data
        """
        import nltk
        import re
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        from nltk.tokenize import sent_tokenize
        
        # Split resolution into lines
        lines = [line.strip() for line in generated_text.split("\n") if line.strip()]
        
        # Identify resolution components
        heading_lines = []
        preambulatory_clauses = []
        operative_clauses = []
        
        # Process state - 0: heading, 1: preambulatory, 2: operative
        state = 0
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Check for transition from heading to preambulatory clauses
            preambulatory_starters = ["Recalling", "Affirming", "Noting", "Recognizing", "Aware", "Concerned"]
            if state == 0 and any(line.startswith(starter) for starter in preambulatory_starters):
                state = 1
            
            # Check for transition from preambulatory to operative clauses
            operative_starters = ["1.", "Decides", "Recommends", "Requests", "Calls", "Urges"]
            if state == 1 and any(starter in line for starter in operative_starters):
                state = 2
            
            # Process line based on state
            if state == 0:
                heading_lines.append(line)
            elif state == 1:
                preambulatory_clauses.append(line)
            elif state == 2:
                operative_clauses.append(line)
        
        # Extract heading components (committee, topic, etc.)
        heading = "\n".join(heading_lines)
        
        # Create sections for the resolution
        sections = []
        
        # Add heading section
        if heading:
            sections.append({
                "title": "Heading",
                "type": "heading",
                "content": heading
            })
        
        # Add preambulatory section
        if preambulatory_clauses:
            sections.append({
                "title": "Preambulatory Clauses",
                "type": "preambulatory",
                "content": "\n".join(preambulatory_clauses)
            })
        
        # Add operative section
        if operative_clauses:
            sections.append({
                "title": "Operative Clauses",
                "type": "operative",
                "content": "\n".join(operative_clauses)
            })
        
        # Split into paragraphs (each clause is a paragraph)
        paragraphs = preambulatory_clauses + operative_clauses
        
        # Split text into sentences
        sentences = []
        for paragraph in paragraphs:
            paragraph_sentences = sent_tokenize(paragraph)
            sentences.extend(paragraph_sentences)
        
        # Parse clauses into structured format
        structured_clauses = {
            "preambulatory": self._parse_preambulatory_clauses(preambulatory_clauses),
            "operative": self._parse_operative_clauses(operative_clauses)
        }
        
        # Create resolution data structure
        resolution_data = {
            "metadata": {
                "document_type": "resolution",
                "committee": metadata["committee"],
                "country": metadata["country"],  # Main submitter
                "main_topic": metadata["topic"],
                "discussed_topics": metadata["topics_discussed"],
                "generated": True,
                "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model_used": self.model_name
            },
            "content": {
                "full_text": generated_text,
                "heading": heading,
                "sections": sections,
                "paragraphs": paragraphs,
                "sentences": sentences,
                "structured_clauses": structured_clauses
            },
            "generation_info": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_length": self.max_length,
                "seed": self.seed
            }
        }
        
        return resolution_data
    
    def _parse_preambulatory_clauses(self, clauses: List[str]) -> List[Dict[str, str]]:
        """
        Parse preambulatory clauses.
        
        Args:
            clauses: List of preambulatory clause texts
            
        Returns:
            List of parsed preambulatory clauses
        """
        parsed_clauses = []
        preambulatory_phrases = [
            "Affirming", "Alarmed by", "Aware of", "Bearing in mind", "Believing", 
            "Cognizant", "Concerned", "Confident", "Contemplating", "Convinced", 
            "Declaring", "Deeply concerned", "Deeply conscious", "Deeply convinced", 
            "Deeply disturbed", "Deeply regretting", "Desiring", "Emphasizing", 
            "Expecting", "Expressing", "Fulfilling", "Fully aware", "Guided by", 
            "Having adopted", "Having considered", "Having examined", "Having received", 
            "Keeping in mind", "Noting", "Observing", "Realizing", "Reaffirming", 
            "Recalling", "Recognizing", "Referring", "Seeking", "Taking into account", 
            "Taking note", "Viewing", "Welcoming"
        ]
        
        for clause in clauses:
            # Find the phrase that starts the clause
            starter_phrase = ""
            for phrase in preambulatory_phrases:
                if clause.startswith(phrase):
                    starter_phrase = phrase
                    break
            
            # If no standard phrase found, use the first word
            if not starter_phrase and clause:
                starter_phrase = clause.split()[0] if clause.split() else ""
            
            parsed_clauses.append({
                "phrase": starter_phrase,
                "content": clause
            })
        
        return parsed_clauses
    
    def _parse_operative_clauses(self, clauses: List[str]) -> List[Dict[str, Any]]:
        """
        Parse operative clauses.
        
        Args:
            clauses: List of operative clause texts
            
        Returns:
            List of parsed operative clauses
        """
        parsed_clauses = []
        operative_phrases = [
            "Accepts", "Affirms", "Approves", "Authorizes", "Calls upon", "Condemns", 
            "Confirms", "Congratulates", "Considers", "Declares", "Deplores", "Designates", 
            "Draws attention", "Emphasizes", "Encourages", "Endorses", "Expresses", 
            "Further invites", "Further proclaims", "Further reminds", "Further recommends", 
            "Further requests", "Further resolves", "Has resolved", "Notes", "Proclaims", 
            "Reaffirms", "Recommends", "Regrets", "Reminds", "Requests", "Solemnly affirms", 
            "Strongly condemns", "Supports", "Takes note", "Transmits", "Trusts"
        ]
        
        for i, clause in enumerate(clauses):
            # Extract clause number if present
            number = None
            number_match = re.match(r'^(\d+)\.\s+', clause)
            if number_match:
                number = int(number_match.group(1))
                clause = clause[number_match.end():].strip()
            else:
                number = i + 1
            
            # Find the phrase that starts the clause
            starter_phrase = ""
            for phrase in operative_phrases:
                if clause.startswith(phrase):
                    starter_phrase = phrase
                    break
            
            # If no standard phrase found, use the first word
            if not starter_phrase and clause:
                starter_phrase = clause.split()[0] if clause.split() else ""
            
            # Extract sub-clauses (a, b, c, etc.)
            sub_clauses = []
            sub_clause_matches = re.finditer(r'([a-z])\)\s+([^()]+)', clause)
            
            for match in sub_clause_matches:
                sub_letter = match.group(1)
                sub_content = match.group(2).strip()
                sub_clauses.append({
                    "letter": sub_letter,
                    "content": sub_content
                })
            
            parsed_clauses.append({
                "number": number,
                "phrase": starter_phrase,
                "content": clause,
                "sub_clauses": sub_clauses
            })
        
        return parsed_clauses
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract sections from text.
        
        Args:
            text: Generated text
            
        Returns:
            List of sections
        """
        import re
        
        # Common section headers in position papers
        section_patterns = [
            r"(?:^|\n)#+\s*(Introduction|Background|Country\s+Position|Previous\s+Actions|Proposed\s+Solutions|Conclusion).*?(?=\n#+\s*|$)",
            r"(?:^|\n)(Introduction|Background|Country\s+Position|Previous\s+Actions|Proposed\s+Solutions|Conclusion)(?::|\n).*?(?=\n(?:Introduction|Background|Country\s+Position|Previous\s+Actions|Proposed\s+Solutions|Conclusion)(?::|\n)|$)",
            r"(?:^|\n)(?:\d+\.\s*)(Introduction|Background|Country\s+Position|Previous\s+Actions|Proposed\s+Solutions|Conclusion).*?(?=\n\d+\.\s*|$)"
        ]
        
        for pattern in section_patterns:
            # Try to match section headers with this pattern
            matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
            sections = list(matches)
            
            if sections:
                # Extract sections using this successful pattern
                result = []
                for i, match in enumerate(sections):
                    section_text = match.group(0).strip()
                    
                    # Extract section title
                    title_match = re.match(r"(?:#+\s*|\d+\.\s*)?([^\n:]+)(?::|\n)", section_text, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()
                        content = section_text[title_match.end():].strip()
                    else:
                        title = f"Section {i+1}"
                        content = section_text
                    
                    # Add section to result
                    result.append({
                        "title": title,
                        "type": title.lower(),
                        "content": content
                    })
                
                return result
        
        # Fallback: split by double newlines and consider each block a section
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        result = []
        
        for i, paragraph in enumerate(paragraphs):
            # Try to detect section headers
            if i == 0:
                section_type = "introduction"
            elif "conclusion" in paragraph.lower() or i == len(paragraphs) - 1:
                section_type = "conclusion"
            else:
                section_type = "body"
            
            result.append({
                "title": f"Section {i+1}",
                "type": section_type,
                "content": paragraph
            })
        
        return result
    
    def _save_document_to_s3(self, document_data: Dict[str, Any], bucket: str) -> str:
        """
        Save the document data to an S3 bucket.
        
        Args:
            document_data: Document data
            bucket: S3 bucket name
            
        Returns:
            S3 key of the saved document
        """
        # Generate filename based on metadata
        document_type = document_data["metadata"]["document_type"]
        country = document_data["metadata"]["country"].replace(" ", "_")
        committee = document_data["metadata"]["committee"].replace(" ", "_")
        topic = document_data["metadata"]["main_topic"].replace(" ", "_")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        filename = f"{document_type}_{country}_{committee}_{topic}_{timestamp}.json"
        
        # Ensure filename is valid
        import re
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Define S3 key with organized structure
        s3_key = f"documents/{document_type}/{country}/{filename}"
        
        # Save to S3
        try:
            write_to_s3(document_data, bucket, s3_key)
            return s3_key
        except Exception as e:
            logger.error(f"Error saving document to S3: {e}", exc_info=True)
            raise

# Test configuration for smaller models
TEST_CONFIG = {
    "small_model": "distilgpt2",  # Small model for testing
    "test_bucket": "your-test-bucket",
    "max_length": 512,            # Smaller output for faster testing
    "temperature": 0.7,
    "top_p": 0.9
}

# Lambda handler function
def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Response with generation result
    """
    logger.info(f"Received event: {json.dumps(event)}")
    start_time = time.time()
    
    try:
        # Extract parameters from event
        delegate_profile = event.get("delegate_profile")
        document_type = event.get("document_type", "position_paper")
        topic = event.get("topic")
        committee = event.get("committee")
        country = event.get("country")
        additional_params = event.get("additional_params", {})
        
        # Extract S3 buckets
        profile_s3_bucket = event.get("profile_s3_bucket")
        output_s3_bucket = event.get("output_s3_bucket")
        
        # Extract generator configuration
        model_name = event.get("model_name", "mistralai/Mistral-7B-Instruct-v0.2")
        use_gpu = event.get("use_gpu", False)
        max_length = event.get("max_length", 2048)
        temperature = event.get("temperature", 0.7)
        top_p = event.get("top_p", 0.9)
        seed = event.get("seed", 42)
        
        # Check for test mode
        is_test_mode = event.get("test_mode", False)
        if is_test_mode:
            logger.info("Running in test mode with smaller model")
            model_name = TEST_CONFIG["small_model"]
            max_length = TEST_CONFIG["max_length"]
            
        # Check if profile or buckets are missing
        if not delegate_profile:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing delegate profile"})
            }
        
        if isinstance(delegate_profile, str) and not profile_s3_bucket:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing profile S3 bucket"})
            }
        
        if not output_s3_bucket:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing output S3 bucket"})
            }
        
        # Initialize generator
        generator = MultiDocumentGenerator(
            model_name=model_name,
            output_bucket=output_s3_bucket,
            use_gpu=use_gpu,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            seed=seed
        )
        
        # Generate document
        s3_uri, document_data = generator.generate_document(
            delegate_profile=delegate_profile,
            document_type=document_type,
            topic=topic,
            committee=committee,
            country=country,
            additional_params=additional_params,
            profile_s3_bucket=profile_s3_bucket,
            output_s3_bucket=output_s3_bucket
        )
        
        # Return result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "s3_uri": s3_uri,
                "document_type": document_type,
                "country": document_data["metadata"]["country"],
                "topic": document_data["metadata"]["main_topic"],
                "generation_time": time.time() - start_time
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__
            })
        }

# Initialize model when the container starts up, not on every invocation
if os.environ.get("AWS_LAMBDA_INITIALIZATION_TYPE") == "provisioned-concurrency":
    # This block runs only during provisioned concurrency initialization
    logger.info("Initializing model during provisioned concurrency setup")
    
    # Use smaller model for test environments
    if os.environ.get("EXECUTION_ENVIRONMENT") == "test":
        logger.info("Test environment detected, using smaller model")
        model_name = TEST_CONFIG["small_model"]
    else:
        model_name = os.environ.get("MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.2")
    
    # Initialize model
    try:
        MultiDocumentGenerator.initialize_model(
            model_name=model_name,
            model_cache_dir="/mnt/efs/models" if os.path.exists("/mnt/efs") else None
        )
        logger.info("Model successfully pre-initialized")
    except Exception as e:
        logger.error(f"Error pre-initializing model: {e}", exc_info=True)

# Testing fixtures and utilities
class TestFixtures:
    """Test fixtures for document generation"""
    
    @staticmethod
    def get_sample_delegate_profile() -> Dict[str, Any]:
        """
        Get a sample delegate profile for testing.
        
        Returns:
            Sample delegate profile
        """
        return {
            "metadata": {
                "country": "Test Country",
                "committee": "Test Committee",
                "topic": "Test Topic",
                "topics_discussed": ["Climate Change", "Human Rights"]
            },
            "writing_style": {
                "readability": {
                    "flesch_reading_ease": 50,
                    "flesch_kincaid_grade": 10
                },
                "complexity": {
                    "avg_sentence_length": 20,
                    "avg_word_length": 5,
                    "unique_word_ratio": 0.6
                },
                "style_markers": {
                    "passive_voice_ratio": 0.2,
                    "question_ratio": 0.05,
                    "exclamation_ratio": 0.01
                }
            },
            "argumentation": {
                "component_distribution": {
                    "claims": 0.3,
                    "premises": 0.6,
                    "backing": 0.1
                },
                "premise_to_claim_ratio": 2.0,
                "support_to_attack_ratio": 3.0,
                "reasoning_patterns": {
                    "deductive": 0.4,
                    "inductive": 0.3,
                    "abductive": 0.2,
                    "analogical": 0.1
                }
            }
        }
    
    @staticmethod
    def mock_model_pipeline():
        """
        Create a mock model pipeline for testing.
        
        Returns:
            Mock pipeline function
        """
        def mock_generator(prompt, **kwargs):
            """Mock generator that returns dummy text"""
            # Create a dummy response based on document type mentioned in the prompt
            response_text = "This is a mock generated document.\n\n"
            
            if "position paper" in prompt.lower():
                response_text += "Introduction\nThis is a sample position paper for testing purposes.\n\n"
                response_text += "Background\nThis section provides background context.\n\n"
                response_text += "Country Position\nThe country supports sustainable development.\n\n"
                response_text += "Proposed Solutions\n1. Increase funding for research\n2. Promote international cooperation\n\n"
                response_text += "Conclusion\nThank you for your consideration."
            
            elif "speech" in prompt.lower():
                response_text += "Thank you, Madam Chair.\n\n"
                response_text += "It is my honor to address this committee on behalf of my country.\n\n"
                response_text += "We believe in the importance of addressing this critical issue.\n\n"
                response_text += "In conclusion, we call upon all nations to work together."
            
            elif "resolution" in prompt.lower():
                response_text += "DRAFT RESOLUTION\n\n"
                response_text += "The General Assembly,\n\n"
                response_text += "Recalling previous resolutions on this matter,\n\n"
                response_text += "Deeply concerned about the current situation,\n\n"
                response_text += "1. Decides to establish a working group;\n\n"
                response_text += "2. Requests the Secretary-General to report on progress;\n\n"
                response_text += "3. Decides to remain seized of the matter."
            
            return [{"generated_text": response_text}]
        
        return mock_generator

# Modified main function for command line usage
def main():
    """Command line interface for the document generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate UN documents for AWS environments")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Generate document command
    gen_parser = subparsers.add_parser("generate", help="Generate a document")
    gen_parser.add_argument("--profile", help="Path to delegate profile JSON file")
    gen_parser.add_argument("--profile-s3", help="S3 key to delegate profile")
    gen_parser.add_argument("--profile-bucket", help="S3 bucket containing delegate profile")
    gen_parser.add_argument("--type", "-t", choices=["position_paper", "speech", "resolution"], 
                          default="position_paper", help="Type of document to generate")
    gen_parser.add_argument("--topic", help="Topic override")
    gen_parser.add_argument("--committee", help="Committee override")
    gen_parser.add_argument("--country", help="Country override")
    gen_parser.add_argument("--output-bucket", required=True, help="S3 bucket for output")
    gen_parser.add_argument("--model", default="mistralai/Mistral-7B-Instruct-v0.2", help="Model to use")
    gen_parser.add_argument("--gpu", action="store_true", help="Use GPU for generation")
    gen_parser.add_argument("--test-mode", action="store_true", help="Use test configuration with smaller model")
    
    # Test AWS permissions command
    test_parser = subparsers.add_parser("test-aws", help="Test AWS permissions and configuration")
    test_parser.add_argument("--bucket", required=True, help="S3 bucket to test permissions")
    
    # Run test fixtures command
    fixture_parser = subparsers.add_parser("test-fixtures", help="Run using test fixtures (no model loading)")
    fixture_parser.add_argument("--output-bucket", required=True, help="S3 bucket for output")
    fixture_parser.add_argument("--type", "-t", choices=["position_paper", "speech", "resolution"], 
                              default="position_paper", help="Type of document to generate")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        # Create lambda event
        event = {
            "document_type": args.type,
            "topic": args.topic,
            "committee": args.committee,
            "country": args.country,
            "output_s3_bucket": args.output_bucket,
            "model_name": args.model if not args.test_mode else TEST_CONFIG["small_model"],
            "use_gpu": args.gpu,
            "test_mode": args.test_mode
        }
        
        # Add profile information
        if args.profile:
            with open(args.profile, 'r', encoding='utf-8') as f:
                event["delegate_profile"] = json.load(f)
        elif args.profile_s3 and args.profile_bucket:
            event["delegate_profile"] = args.profile_s3
            event["profile_s3_bucket"] = args.profile_bucket
        else:
            print("Error: Either local profile path or S3 profile information is required")
            return
        
        # Call lambda handler
        result = lambda_handler(event, None)
        print(json.dumps(result, indent=2))
    
    elif args.command == "test-aws":
        print(f"Testing AWS permissions for bucket: {args.bucket}")
        if check_s3_permissions(args.bucket):
            print("✅ S3 permissions test passed")
        else:
            print("❌ S3 permissions test failed")
    
    elif args.command == "test-fixtures":
        print(f"Running test with fixtures for {args.type} document")
        
        # Create mock generator with test fixtures
        class MockGenerator(MultiDocumentGenerator):
            def _generate_text(self, prompt: str) -> str:
                """Override to use mock generator"""
                mock_gen = TestFixtures.mock_model_pipeline()
                response = mock_gen(prompt)
                return response[0]["generated_text"]
        
        # Initialize mock generator
        generator = MockGenerator(
            model_name="test_model",
            output_bucket=args.output_bucket,
            load_model=False  # Don't load actual model
        )
        
        # Generate document with sample profile
        sample_profile = TestFixtures.get_sample_delegate_profile()
        s3_uri, _ = generator.generate_document(
            delegate_profile=sample_profile,
            document_type=args.type,
            output_s3_bucket=args.output_bucket
        )
        
        print(f"Test document generated and saved to: {s3_uri}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
