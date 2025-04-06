import torch
import torch.nn as nn
import numpy as np
import json
import nltk
import matplotlib.pyplot as plt
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import os
import io
import time
import logging
import tempfile
import boto3
import botocore
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
import sys
import platform
import math
import seaborn as sns

# Configure logging for CloudWatch compatibility
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Environment variables
ENV_S3_BUCKET = os.environ.get("MUN_ANALYSIS_S3_BUCKET")
ENV_S3_REGION = os.environ.get("MUN_ANALYSIS_S3_REGION", "us-east-1")
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_STORAGE_MODE = os.environ.get("STORAGE_MODE", "local").lower()  # "local" or "s3"
ENV_SM_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT")
ENV_USE_SM = os.environ.get("USE_SAGEMAKER", "false").lower() == "true"

# Check if running in Lambda environment
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

# Check for GPU availability
IS_GPU_AVAILABLE = torch.cuda.is_available()
if IS_GPU_AVAILABLE:
    logger.info(f"GPU is available: {torch.cuda.get_device_name(0)}")
else:
    logger.info("GPU is not available, using CPU")

# Maximum retries for AWS operations
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Configure non-interactive matplotlib backend for Lambda
if IS_LAMBDA:
    plt.switch_backend('agg')

# Download NLTK resources - do this outside handler for Lambda optimization
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    logger.info("Downloading NLTK resources...")
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('vader_lexicon', quiet=True)

class S3Handler:
    """Handler for S3 operations"""
    
    def __init__(self, bucket_name: Optional[str] = None, region: str = "us-east-1"):
        """Initialize S3 handler"""
        self.bucket_name = bucket_name or ENV_S3_BUCKET
        self.region = region or ENV_S3_REGION
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided either directly or through MUN_ANALYSIS_S3_BUCKET environment variable")
        
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client with retries"""
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_client = boto3.client('s3', region_name=self.region)
                # Verify IAM permissions by checking if we can list the bucket
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
                return
            except (ClientError, Exception) as e:
                if isinstance(e, ClientError) and e.response['Error']['Code'] == '403':
                    logger.error(f"Permission denied to access S3 bucket: {self.bucket_name}")
                    raise
                elif attempt < MAX_RETRIES - 1:
                    logger.warning(f"Failed to initialize S3 client (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to initialize S3 client after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Download a file from S3 to a local path"""
        for attempt in range(MAX_RETRIES):
            try:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                self.s3_client.download_file(self.bucket_name, s3_key, local_path)
                return True
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error downloading file from S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error downloading file from S3 after {MAX_RETRIES} attempts: {str(e)}")
                    return False
    
    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """Upload a file from a local path to S3"""
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
                return True
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error uploading file to S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error uploading file to S3 after {MAX_RETRIES} attempts: {str(e)}")
                    return False
    
    def upload_bytes(self, data: bytes, s3_key: str, content_type: Optional[str] = None) -> bool:
        """Upload bytes directly to S3"""
        for attempt in range(MAX_RETRIES):
            try:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=data,
                    **extra_args
                )
                return True
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error uploading bytes to S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error uploading bytes to S3 after {MAX_RETRIES} attempts: {str(e)}")
                    return False
    
    def read_file(self, s3_key: str) -> Optional[bytes]:
        """Read a file from S3 as bytes"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                return response['Body'].read()
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error reading file from S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error reading file from S3 after {MAX_RETRIES} attempts: {str(e)}")
                    return None

class SageMakerHandler:
    """Handler for SageMaker operations"""
    
    def __init__(self, endpoint_name: Optional[str] = None, region: str = "us-east-1"):
        """Initialize SageMaker handler"""
        self.endpoint_name = endpoint_name or ENV_SM_ENDPOINT
        self.region = region or ENV_S3_REGION
        
        if not self.endpoint_name:
            raise ValueError("SageMaker endpoint name must be provided either directly or through SAGEMAKER_ENDPOINT environment variable")
        
        self.runtime_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize SageMaker runtime client with retries"""
        for attempt in range(MAX_RETRIES):
            try:
                self.runtime_client = boto3.client('sagemaker-runtime', region_name=self.region)
                logger.info(f"Successfully initialized SageMaker runtime client")
                return
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Failed to initialize SageMaker client (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to initialize SageMaker client after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def invoke_endpoint(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invoke SageMaker endpoint with input data"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.runtime_client.invoke_endpoint(
                    EndpointName=self.endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps(input_data)
                )
                return json.loads(response['Body'].read().decode())
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error invoking SageMaker endpoint (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error invoking SageMaker endpoint after {MAX_RETRIES} attempts: {str(e)}")
                    return None

class MUNDelegateAnalyzer:
    """
    Tool for analyzing MUN delegate position papers and comparing 
    their approach with different generated templates.
    """
    
    def __init__(self, config_file):
        """
        Initialize the analyzer with configuration from a JSON file.
        
        Args:
            config_file (str): Path to configuration file (local path or S3 URI)
        """
        # Load configuration
        self.config = self._load_config(config_file)
        self.use_s3 = ENV_STORAGE_MODE == "s3" and not ENV_TEST_MODE and ENV_S3_BUCKET
        self.s3_handler = None
        
        if self.use_s3:
            try:
                self.s3_handler = S3Handler()
                logger.info("S3 handler initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 handler, falling back to local storage: {str(e)}")
                self.use_s3 = False
        
        # Model initialization strategy based on environment
        self._initialize_model()
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Define approach types
        self.approach_types = [
            "positive_achievements",
            "regional_cooperation",
            "economic_focus",
            "humanitarian_concern",
            "diplomatic_neutral",
            "historical_context",
            "sovereignty_emphasis",
            "legal_framework"
        ]
        
        # Initialize stopwords
        self.stop_words = set(stopwords.words('english'))
        
        # Setup for TF-IDF
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        
        # Initialize results storage
        self.delegate_analysis = None
        self.template_analyses = {}
        self.similarity_scores = {}
        
        # Create a temp directory for local file operations when in Lambda or test mode
        if IS_LAMBDA or ENV_TEST_MODE:
            self.temp_dir = tempfile.TemporaryDirectory()
            self.output_base_dir = self.temp_dir.name
        else:
            self.temp_dir = None
            self.output_base_dir = None
            
        logger.info(f"Analyzer initialized with configuration for topic: {self.config.get('topic', 'Not specified')}")
    
    def _load_config(self, config_file):
        """
        Load configuration from a file, supporting both local and S3 paths.
        
        Args:
            config_file (str): Path to configuration file
            
        Returns:
            dict: Configuration
        """
        try:
            # Check if it's an S3 URI
            if config_file.startswith("s3://") and ENV_S3_BUCKET:
                bucket_name, s3_key = config_file.replace("s3://", "").split("/", 1)
                s3_handler = S3Handler(bucket_name=bucket_name)
                config_data = s3_handler.read_file(s3_key)
                if config_data:
                    return json.loads(config_data.decode('utf-8'))
                else:
                    raise ValueError(f"Failed to load configuration from S3: {config_file}")
            # Otherwise, load from local file
            else:
                with open(config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def _initialize_model(self):
        """Initialize NLP model based on environment (SageMaker, GPU, CPU, or testing)"""
        # Use SageMaker endpoint if configured
        if ENV_USE_SM and ENV_SM_ENDPOINT:
            logger.info(f"Using SageMaker endpoint: {ENV_SM_ENDPOINT}")
            try:
                self.sm_handler = SageMakerHandler()
                self.use_sagemaker = True
                # These are placeholders when using SageMaker
                self.model = None
                self.tokenizer = None
                self.device = None
                return
            except Exception as e:
                logger.warning(f"Failed to initialize SageMaker handler, falling back to local model: {str(e)}")
                self.use_sagemaker = False
        else:
            self.use_sagemaker = False
        
        # For testing environment, use an even smaller model or mock
        if ENV_TEST_MODE:
            logger.info("Using lightweight model for testing environment")
            # Initialize minimal model for testing
            self.device = torch.device("cpu")
            try:
                # Try to use a tiny model for testing
                self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
                self.model = AutoModelForCausalLM.from_pretrained(
                    "distilbert-base-uncased", 
                    return_dict=True
                ).to(self.device)
            except Exception as e:
                logger.warning(f"Failed to load test model, using mock model: {str(e)}")
                # Create a mock model for pure testing purposes
                self.tokenizer = None
                self.model = self._create_mock_model()
        # For Lambda with no GPU
        elif IS_LAMBDA or not IS_GPU_AVAILABLE:
            logger.info("Using CPU-optimized model for Lambda/non-GPU environment")
            self.device = torch.device("cpu")
            self.tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
            # Load in CPU-efficient mode
            self.model = AutoModelForCausalLM.from_pretrained(
                "distilgpt2",
                low_cpu_mem_usage=True,
                return_dict=True
            ).to(self.device)
        # Regular environment with GPU
        else:
            logger.info("Using GPU-accelerated model")
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
            self.model = AutoModelForCausalLM.from_pretrained("distilgpt2").to(self.device)
    
    def _create_mock_model(self):
        """Create a mock model for testing purposes"""
        class MockModel:
            def __init__(self):
                pass
                
            def __call__(self, input_ids):
                # Return a mock logits tensor
                batch_size = input_ids.size(0)
                seq_length = input_ids.size(1)
                vocab_size = 50257  # Standard size for GPT-2
                return type('obj', (object,), {
                    'logits': torch.rand(batch_size, seq_length, vocab_size)
                })
                
            def eval(self):
                return self
                
            def to(self, device):
                return self
        
        return MockModel()
    
    def load_delegate_paper(self, file_path):
        """
        Load delegate's position paper from a file, supporting both local files and S3.
        
        Args:
            file_path (str): Path to the delegate's position paper or S3 URI
            
        Returns:
            str: Content of the position paper
        """
        try:
            # Check if it's an S3 URI
            if file_path.startswith("s3://") and self.use_s3:
                bucket_name, s3_key = file_path.replace("s3://", "").split("/", 1)
                s3_handler = S3Handler(bucket_name=bucket_name)
                paper_data = s3_handler.read_file(s3_key)
                if paper_data:
                    return paper_data.decode('utf-8')
                else:
                    raise ValueError(f"Failed to load paper from S3: {file_path}")
            # Otherwise, load from local file
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
        except Exception as e:
            logger.error(f"Error loading delegate paper: {str(e)}")
            return None
    
    def generate_prompt(self, approach_type):
        """
        Generate a prompt for the LLM to create a position paper with a specific approach.
        
        Args:
            approach_type (str): Type of approach to generate
            
        Returns:
            str: Prompt for the LLM
        """
        country = self.config.get('country', 'a country')
        topic = self.config.get('topic', 'a topic')
        committee = self.config.get('committee', 'a committee')
        
        prompts = {
            "positive_achievements": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Focus heavily on the positive achievements and progress {country} has made related to this topic. Highlight successful policies, initiatives, and improvements.",
            
            "regional_cooperation": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Emphasize regional cooperation and multilateral solutions. Focus on how {country} works with neighboring countries and regional bodies.",
            
            "economic_focus": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Concentrate on economic aspects, financial implications, and economic development related to this topic. Emphasize economic policies and approaches.",
            
            "humanitarian_concern": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Center the paper around humanitarian concerns and human rights. Focus on the welfare of affected populations and humanitarian needs.",
            
            "diplomatic_neutral": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Take a balanced, diplomatic approach that avoids strong positions. Present a neutral stance that acknowledges different perspectives.",
            
            "historical_context": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Emphasize historical context and the evolution of this issue over time. Reference past events and how they shape the current situation.",
            
            "sovereignty_emphasis": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Focus strongly on national sovereignty and the right of nations to determine their own policies. Emphasize respect for borders and non-interference.",
            
            "legal_framework": f"Write a 1-page Model UN position paper for {country} on the topic of {topic} for the {committee}. Center the paper on legal frameworks, treaties, and international law. Reference relevant legal instruments and precedents."
        }
        
        return prompts.get(approach_type, "")
    
    def generate_approach_templates(self):
        """
        Generate multiple approach templates using the configuration.
        
        Returns:
            dict: Dictionary of approach templates
        """
        # In a real implementation, you would use the LLM to generate each approach
        # For this demonstration, we'll simulate the generation
        print("Generating approach templates...")
        
        template_texts = {}
        
        # This is a placeholder for actual generation using a proper API
        for approach_type in self.approach_types:
            prompt = self.generate_prompt(approach_type)
            # In a real implementation, you would call an LLM API here
            # For demonstration, we'll simulate it with a placeholder
            template_text = f"This is a simulated position paper for approach: {approach_type}\n"
            template_text += f"Country: {self.config.get('country', 'a country')}\n"
            template_text += f"Topic: {self.config.get('topic', 'a topic')}\n"
            template_text += f"Committee: {self.config.get('committee', 'a committee')}\n\n"
            template_text += "The actual implementation would generate a full position paper using an LLM API."
            
            template_texts[approach_type] = template_text
            
        return template_texts
    
    def calculate_perplexity(self, text):
        """
        Calculate the perplexity of a text using the language model or SageMaker endpoint.
        Higher perplexity indicates more complex/unpredictable text.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            float: Perplexity score
        """
        # Use SageMaker endpoint if configured
        if self.use_sagemaker:
            try:
                input_data = {"text": text, "task": "perplexity"}
                result = self.sm_handler.invoke_endpoint(input_data)
                if result and "perplexity" in result:
                    return result["perplexity"]
                else:
                    logger.warning("SageMaker endpoint didn't return valid perplexity, using fallback value")
                    return 100.0  # Fallback value
            except Exception as e:
                logger.error(f"Error invoking SageMaker endpoint for perplexity: {str(e)}")
                return 100.0  # Fallback value
        
        # For testing environment with mock model
        if ENV_TEST_MODE and self.tokenizer is None:
            # Return a consistent mock value for testing
            return len(text.split()) / 10
            
        # For local calculation
        try:
            # Tokenize the text
            encodings = self.tokenizer(text, return_tensors="pt").to(self.device)
            
            # Create sequence without the last token for input
            input_ids = encodings.input_ids[:, :-1]
            
            # Create target sequence (shifted by 1)
            target_ids = encodings.input_ids[:, 1:]
            
            # Get model output
            with torch.no_grad():
                outputs = self.model(input_ids)
                logits = outputs.logits
            
            # Calculate loss (cross entropy)
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, logits.size(-1)), target_ids.view(-1))
            
            # Perplexity is exp(loss)
            perplexity = math.exp(loss.item())
            
            return perplexity
        except Exception as e:
            logger.error(f"Error calculating perplexity: {str(e)}")
            return 100.0  # Fallback value in case of error
    
    def calculate_burstiness(self, text):
        """
        Calculate the burstiness of a text (variance in sentence structure).
        Higher burstiness indicates more varied sentence lengths and structures.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            float: Burstiness score
        """
        # Use SageMaker endpoint if configured
        if self.use_sagemaker:
            try:
                input_data = {"text": text, "task": "burstiness"}
                result = self.sm_handler.invoke_endpoint(input_data)
                if result and "burstiness" in result:
                    return result["burstiness"]
                else:
                    logger.warning("SageMaker endpoint didn't return valid burstiness, calculating locally")
            except Exception as e:
                logger.error(f"Error invoking SageMaker endpoint for burstiness: {str(e)}")
                # Continue with local calculation as fallback
        
        try:
            # Tokenize into sentences
            sentences = sent_tokenize(text)
            
            # Calculate sentence lengths
            sentence_lengths = [len(word_tokenize(s)) for s in sentences]
            
            # Calculate burstiness as the coefficient of variation
            # (standard deviation divided by mean)
            if len(sentence_lengths) > 1 and np.mean(sentence_lengths) > 0:
                burstiness = np.std(sentence_lengths) / np.mean(sentence_lengths)
            else:
                burstiness = 0
                
            return burstiness
        except Exception as e:
            logger.error(f"Error calculating burstiness: {str(e)}")
            return 0.0  # Fallback value in case of error
    
    def extract_keywords(self, text, num_keywords=20):
        """
        Extract key terms from the text using TF-IDF.
        
        Args:
            text (str): Text to analyze
            num_keywords (int): Number of keywords to extract
            
        Returns:
            list: Top keywords
        """
        # Use SageMaker endpoint if configured
        if self.use_sagemaker:
            try:
                input_data = {"text": text, "task": "keywords", "num_keywords": num_keywords}
                result = self.sm_handler.invoke_endpoint(input_data)
                if result and "keywords" in result:
                    return result["keywords"]
                else:
                    logger.warning("SageMaker endpoint didn't return valid keywords, calculating locally")
            except Exception as e:
                logger.error(f"Error invoking SageMaker endpoint for keywords: {str(e)}")
                # Continue with local calculation as fallback
        
        try:
            # Tokenize and remove stopwords
            words = word_tokenize(text.lower())
            filtered_words = [w for w in words if w.isalnum() and w not in self.stop_words]
            
            # Calculate frequency distribution
            fdist = FreqDist(filtered_words)
            
            # Get most common words
            return [word for word, freq in fdist.most_common(num_keywords)]
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []  # Return empty list in case of error
    
    def analyze_sentiment(self, text):
        """
        Analyze the sentiment of the text.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            dict: Sentiment scores
        """
        # Use SageMaker endpoint if configured
        if self.use_sagemaker:
            try:
                input_data = {"text": text, "task": "sentiment"}
                result = self.sm_handler.invoke_endpoint(input_data)
                if result and "sentiment" in result:
                    return result["sentiment"]
                else:
                    logger.warning("SageMaker endpoint didn't return valid sentiment, calculating locally")
            except Exception as e:
                logger.error(f"Error invoking SageMaker endpoint for sentiment: {str(e)}")
                # Continue with local calculation as fallback
        
        try:
            return self.sentiment_analyzer.polarity_scores(text)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            # Return neutral sentiment in case of error
            return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    
    def analyze_text(self, text):
        """
        Perform comprehensive analysis of a text.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            dict: Analysis results
        """
        if not text:
            return None
            
        analysis = {
            "perplexity": self.calculate_perplexity(text),
            "burstiness": self.calculate_burstiness(text),
            "keywords": self.extract_keywords(text),
            "sentiment": self.analyze_sentiment(text),
            "text_length": len(text),
            "sentence_count": len(sent_tokenize(text)),
            "word_count": len(word_tokenize(text))
        }
        
        return analysis
    
    def calculate_similarity(self, analysis1, analysis2):
        """
        Calculate similarity between two text analyses.
        
        Args:
            analysis1 (dict): First text analysis
            analysis2 (dict): Second text analysis
            
        Returns:
            float: Similarity score (0-1)
        """
        if not analysis1 or not analysis2:
            return 0
            
        # Compare perplexity (inverse of absolute difference)
        perplexity_diff = abs(analysis1["perplexity"] - analysis2["perplexity"])
        perplexity_sim = 1 / (1 + perplexity_diff)
        
        # Compare burstiness (inverse of absolute difference)
        burstiness_diff = abs(analysis1["burstiness"] - analysis2["burstiness"])
        burstiness_sim = 1 / (1 + burstiness_diff)
        
        # Compare keywords (Jaccard similarity)
        set1 = set(analysis1["keywords"])
        set2 = set(analysis2["keywords"])
        keyword_sim = len(set1.intersection(set2)) / len(set1.union(set2)) if set1 or set2 else 0
        
        # Compare sentiment
        sentiment_diff = abs(analysis1["sentiment"]["compound"] - analysis2["sentiment"]["compound"])
        sentiment_sim = 1 - sentiment_diff  # Higher when sentiment is closer
        
        # Weighted combination
        weights = {
            "perplexity": 0.25,
            "burstiness": 0.25,
            "keywords": 0.3,
            "sentiment": 0.2
        }
        
        similarity = (
            weights["perplexity"] * perplexity_sim +
            weights["burstiness"] * burstiness_sim +
            weights["keywords"] * keyword_sim +
            weights["sentiment"] * sentiment_sim
        )
        
        return similarity
    
    def compare_delegate_to_templates(self, delegate_text, template_texts):
        """
        Compare delegate's paper to each approach template.
        
        Args:
            delegate_text (str): Delegate's position paper
            template_texts (dict): Dictionary of approach templates
            
        Returns:
            dict: Similarity scores for each approach
        """
        # Analyze delegate's paper
        self.delegate_analysis = self.analyze_text(delegate_text)
        
        # Analyze each template
        self.template_analyses = {
            approach: self.analyze_text(text)
            for approach, text in template_texts.items()
        }
        
        # Calculate similarity scores
        self.similarity_scores = {
            approach: self.calculate_similarity(self.delegate_analysis, template_analysis)
            for approach, template_analysis in self.template_analyses.items()
        }
        
        return self.similarity_scores
    
    def visualize_results(self, output_path="results.png"):
        """
        Create visualization of approach fingerprint, saving to local filesystem or S3.
        
        Args:
            output_path (str): Path to save the visualization (local path or S3 prefix)
            
        Returns:
            dict: Dictionary of file paths or S3 URIs
        """
        if not self.similarity_scores:
            logger.warning("No results to visualize yet. Run comparison first.")
            return {}
        
        # Determine if using S3 for output
        use_s3 = self.use_s3 and output_path.startswith("s3://")
        
        # Setup local output paths (temp or final)
        if IS_LAMBDA or ENV_TEST_MODE or use_s3:
            local_dir = self.temp_dir.name if self.temp_dir else tempfile.mkdtemp()
            local_output_path = os.path.join(local_dir, os.path.basename(output_path))
            local_bar_output = local_output_path.replace(".png", "_bar.png")
            local_text_output = local_output_path.replace(".png", ".txt")
        else:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            local_output_path = output_path
            local_bar_output = output_path.replace(".png", "_bar.png")
            local_text_output = output_path.replace(".png", ".txt")
            
        # Prepare data for radar chart
        approaches = list(self.similarity_scores.keys())
        scores = [self.similarity_scores[a] for a in approaches]
        
        # Readable labels for the approaches
        labels = [' '.join(a.split('_')).title() for a in approaches]
        
        try:
            # Create radar chart
            angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
            
            # Close the plot
            angles += angles[:1]
            scores += scores[:1]
            labels += labels[:1]
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
            
            # Draw one axis per variable and add labels
            plt.xticks(angles[:-1], labels[:-1], color='black', size=12)
            
            # Draw ylabels
            ax.set_rlabel_position(0)
            plt.yticks([0.25, 0.5, 0.75], ["0.25", "0.5", "0.75"], color="grey", size=10)
            plt.ylim(0, 1)
            
            # Plot data
            ax.plot(angles, scores, linewidth=2, linestyle='solid')
            
            # Fill area
            ax.fill(angles, scores, alpha=0.25)
            
            # Add title
            plt.title(
                f"MUN Delegate Approach Analysis\nTopic: {self.config.get('topic', 'Not specified')}", 
                size=15, 
                y=1.1
            )
            
            # Save the figure locally
            plt.tight_layout()
            plt.savefig(local_output_path)
            logger.info(f"Radar chart saved to {local_output_path}")
            plt.close(fig)
            
            # Create bar chart for easy comparison
            plt.figure(figsize=(12, 6))
            approaches_sorted = sorted(approaches, key=lambda x: self.similarity_scores[x], reverse=True)
            labels_sorted = [' '.join(a.split('_')).title() for a in approaches_sorted]
            scores_sorted = [self.similarity_scores[a] for a in approaches_sorted]
            
            plt.bar(labels_sorted, scores_sorted, color=sns.color_palette("viridis", len(approaches_sorted)))
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("Similarity Score")
            plt.title("Approach Similarity Ranking")
            plt.tight_layout()
            
            # Save the bar chart locally
            plt.savefig(local_bar_output)
            logger.info(f"Bar chart saved to {local_bar_output}")
            plt.close()
            
            # Generate text report locally
            self.generate_text_report(local_text_output)
            
            # Upload to S3 if needed
            if use_s3:
                output_files = {}
                
                # Parse S3 URI
                s3_uri_prefix = output_path.rsplit('/', 1)[0] if '/' in output_path else output_path
                file_prefix = os.path.basename(s3_uri_prefix)
                bucket_name, s3_key_prefix = s3_uri_prefix.replace("s3://", "").split("/", 1)
                
                # Initialize S3 handler
                s3_handler = S3Handler(bucket_name=bucket_name)
                
                # Upload radar chart
                radar_s3_key = f"{s3_key_prefix}/radar_chart.png"
                if s3_handler.upload_file(local_output_path, radar_s3_key):
                    radar_s3_uri = f"s3://{bucket_name}/{radar_s3_key}"
                    output_files['radar_chart'] = radar_s3_uri
                    logger.info(f"Uploaded radar chart to {radar_s3_uri}")
                
                # Upload bar chart
                bar_s3_key = f"{s3_key_prefix}/bar_chart.png"
                if s3_handler.upload_file(local_bar_output, bar_s3_key):
                    bar_s3_uri = f"s3://{bucket_name}/{bar_s3_key}"
                    output_files['bar_chart'] = bar_s3_uri
                    logger.info(f"Uploaded bar chart to {bar_s3_uri}")
                
                # Upload text report
                text_s3_key = f"{s3_key_prefix}/report.txt"
                if s3_handler.upload_file(local_text_output, text_s3_key):
                    text_s3_uri = f"s3://{bucket_name}/{text_s3_key}"
                    output_files['text_report'] = text_s3_uri
                    logger.info(f"Uploaded text report to {text_s3_uri}")
                
                return output_files
            else:
                return {
                    'radar_chart': local_output_path,
                    'bar_chart': local_bar_output,
                    'text_report': local_text_output
                }
                
        except Exception as e:
            logger.error(f"Error creating visualizations: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
        
    def generate_text_report(self, output_path="results.txt"):
        """
        Generate a text report of the analysis results.
        
        Args:
            output_path (str): Path to save the text report
            
        Returns:
            bool: Success status
        """
        if not self.similarity_scores:
            logger.warning("No results to generate report for. Run comparison first.")
            return False
            
        try:
            with open(output_path, 'w') as f:
                f.write("MUN DELEGATE APPROACH ANALYSIS REPORT\n")
                f.write("=====================================\n\n")
                
                f.write(f"Topic: {self.config.get('topic', 'Not specified')}\n")
                f.write(f"Country: {self.config.get('country', 'Not specified')}\n")
                f.write(f"Committee: {self.config.get('committee', 'Not specified')}\n\n")
                
                f.write("DELEGATE PAPER ANALYSIS\n")
                f.write("----------------------\n")
                f.write(f"Perplexity: {self.delegate_analysis['perplexity']:.2f}\n")
                f.write(f"Burstiness: {self.delegate_analysis['burstiness']:.2f}\n")
                f.write(f"Overall Sentiment: {self.delegate_analysis['sentiment']['compound']:.2f}\n")
                f.write(f"Word Count: {self.delegate_analysis['word_count']}\n")
                f.write(f"Sentence Count: {self.delegate_analysis['sentence_count']}\n")
                f.write("Key Terms: " + ", ".join(self.delegate_analysis['keywords'][:10]) + "\n\n")
                
                f.write("APPROACH SIMILARITY SCORES (Ranked)\n")
                f.write("----------------------------------\n")
                
                # Sort approaches by similarity score
                approaches_sorted = sorted(
                    self.similarity_scores.keys(), 
                    key=lambda x: self.similarity_scores[x], 
                    reverse=True
                )
                
                for i, approach in enumerate(approaches_sorted, 1):
                    score = self.similarity_scores[approach]
                    approach_name = ' '.join(approach.split('_')).title()
                    f.write(f"{i}. {approach_name}: {score:.4f}\n")
                
                f.write("\n")
                f.write("INTERPRETATION\n")
                f.write("-------------\n")
                top_approach = approaches_sorted[0]
                top_approach_name = ' '.join(top_approach.split('_')).title()
                
                f.write(f"The delegate's position paper most closely aligns with a '{top_approach_name}' approach.\n")
                f.write("This suggests the delegate prioritizes the following aspects in their analysis:\n")
                
                approach_characteristics = {
                    "positive_achievements": "Highlighting successful policies and initiatives, focusing on strengths and progress.",
                    "regional_cooperation": "Emphasizing multilateral solutions and coordination with neighboring countries and regional bodies.",
                    "economic_focus": "Concentrating on financial implications, economic development, and market-based approaches.",
                    "humanitarian_concern": "Centering on human rights, welfare of affected populations, and humanitarian needs.",
                    "diplomatic_neutral": "Taking a balanced stance that acknowledges different perspectives without strong positions.",
                    "historical_context": "Referencing past events and how they shape current situations and policies.",
                    "sovereignty_emphasis": "Focusing on national sovereignty, respect for borders, and non-interference principles.",
                    "legal_framework": "Centering on treaties, international law, and legal precedents."
                }
                
                f.write(f"- {approach_characteristics[top_approach]}\n")
                
                # If there's a close second approach
                if len(approaches_sorted) > 1:
                    second_approach = approaches_sorted[1]
                    second_score = self.similarity_scores[second_approach]
                    top_score = self.similarity_scores[top_approach]
                    
                    if top_score - second_score < 0.1:  # If scores are close
                        second_approach_name = ' '.join(second_approach.split('_')).title()
                        f.write(f"\nThe delegate also shows strong alignment with a '{second_approach_name}' approach:\n")
                        f.write(f"- {approach_characteristics[second_approach]}\n")
                
                f.write("\nThis analysis can help understand the delegate's priorities and approach to the topic.\n")
                
            logger.info(f"Text report saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error generating text report: {str(e)}")
            return False
    
    def run_analysis(self, delegate_paper_path, output_dir="results"):
        """
        Run the complete analysis workflow, supporting S3 for AWS environments.
        
        Args:
            delegate_paper_path (str): Path to delegate's paper (local path or S3 URI)
            output_dir (str): Directory to save results (local path or S3 URI)
            
        Returns:
            dict: Analysis results and file paths/URIs
        """
        output_files = {}
        s3_output = False
        
        # Determine if using S3 for output
        if self.use_s3 and output_dir.startswith("s3://"):
            s3_output = True
            # For S3 output, we need a local temp directory for intermediate files
            local_output_dir = os.path.join(self.temp_dir.name if self.temp_dir else tempfile.mkdtemp(), "results")
        else:
            # For local output, ensure the directory exists
            local_output_dir = output_dir
            
        # Create output directory if it doesn't exist
        os.makedirs(local_output_dir, exist_ok=True)
        
        # Load delegate's paper
        logger.info(f"Loading delegate paper from {delegate_paper_path}")
        delegate_text = self.load_delegate_paper(delegate_paper_path)
        if not delegate_text:
            logger.error("Failed to load delegate paper.")
            return None
            
        # Generate approach templates
        logger.info("Generating approach templates")
        template_texts = self.generate_approach_templates()
        
        # Compare delegate's paper to templates
        logger.info("Comparing delegate's paper to approach templates")
        similarity_scores = self.compare_delegate_to_templates(delegate_text, template_texts)
        
        # Generate visualizations
        logger.info("Generating visualizations")
        if s3_output:
            # If using S3, create the full URI for output
            output_path = output_dir
            if not output_path.endswith('/'):
                output_path += '/'
                
            vis_output = self.visualize_results(output_path)
            output_files.update(vis_output)
        else:
            # For local output
            radar_chart_path = os.path.join(local_output_dir, "radar_chart.png")
            vis_output = self.visualize_results(radar_chart_path)
            output_files.update(vis_output)
        
        # Prepare results
        results = {
            "similarity_scores": similarity_scores,
            "delegate_analysis": {
                k: v for k, v in self.delegate_analysis.items() 
                if k not in ['sentiment']
            },  # Exclude sentiment for cleaner JSON
            "output_files": output_files
        }
        
        # Add summary data
        results["sentiment"] = {
            "compound": self.delegate_analysis['sentiment']['compound'],
            "positive": self.delegate_analysis['sentiment']['pos'],
            "negative": self.delegate_analysis['sentiment']['neg'],
            "neutral": self.delegate_analysis['sentiment']['neu']
        }
        
        # Add top approaches
        approaches_sorted = sorted(
            similarity_scores.keys(), 
            key=lambda x: similarity_scores[x], 
            reverse=True
        )
        
        top_approaches = []
        for i, approach in enumerate(approaches_sorted[:3], 1):
            score = similarity_scores[approach]
            approach_name = ' '.join(approach.split('_')).title()
            top_approaches.append({
                "rank": i,
                "approach": approach_name,
                "score": round(score, 4)
            })
        
        results["top_approaches"] = top_approaches
        
        # Save summary results as JSON
        try:
            results_json_path = os.path.join(local_output_dir, "results.json")
            with open(results_json_path, 'w') as f:
                json.dump(results, f, indent=2)
                
            # Upload JSON to S3 if needed
            if s3_output:
                bucket_name, s3_key_prefix = output_dir.replace("s3://", "").split("/", 1)
                s3_handler = S3Handler(bucket_name=bucket_name)
                
                if not s3_key_prefix.endswith('/'):
                    s3_key_prefix += '/'
                    
                results_s3_key = f"{s3_key_prefix}results.json"
                if s3_handler.upload_file(results_json_path, results_s3_key):
                    results_s3_uri = f"s3://{bucket_name}/{results_s3_key}"
                    output_files['results_json'] = results_s3_uri
                    results["output_files"] = output_files
                    logger.info(f"Uploaded results JSON to {results_s3_uri}")
        except Exception as e:
            logger.error(f"Error saving results JSON: {str(e)}")
        
        return results
    
    def cleanup(self):
        """Clean up any temporary resources"""
        if self.temp_dir is not None:
            try:
                self.temp_dir.cleanup()
                logger.info("Cleaned up temporary directory")
            except Exception as e:
                logger.warning(f"Error cleaning up temporary directory: {str(e)}")
        
        # If running in Lambda, try to clean up ML resources
        if IS_LAMBDA and self.model is not None:
            try:
                # Free up memory for Lambda environment
                del self.model
                del self.tokenizer
                import gc
                gc.collect()
                if IS_GPU_AVAILABLE:
                    torch.cuda.empty_cache()
                logger.info("Cleaned up ML resources")
            except Exception as e:
                logger.warning(f"Error cleaning up ML resources: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

# Example usage
if __name__ == "__main__":
    # Check if running in test mode
    if ENV_TEST_MODE:
        logger.info("Running in test mode")
        
        # Sample configuration
        config = {
            "topic": "Climate Change Mitigation",
            "country": "Sweden",
            "committee": "UNEP"
        }
        
        # Create temp directory for test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save config to JSON file
            config_path = os.path.join(temp_dir, "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            
            # Create analyzer
            analyzer = MUNDelegateAnalyzer(config_path)
            
            # Sample delegate paper (for demonstration)
            sample_paper = """
            Sweden is committed to addressing climate change through ambitious mitigation strategies. 
            As a leader in renewable energy, Sweden has already achieved significant emissions reductions
            while maintaining economic growth. Our country aims to become one of the first fossil-free
            welfare states in the world. We have implemented a carbon tax since 1991, which has proven
            effective in reducing emissions while promoting innovation.

            Sweden recognizes the interconnected nature of climate challenges and advocates for a 
            comprehensive approach that includes all nations. We support the Paris Agreement framework
            and believe that developed countries must take the lead in emissions reductions while 
            supporting developing nations. Regional cooperation, particularly within the European Union
            and Nordic countries, has been central to our strategy.

            Sweden proposes strengthening international cooperation through increased climate financing,
            technology transfer, and capacity building. We advocate for a carbon pricing mechanism at the
            global level, similar to our successful national carbon tax. Additionally, we support enhanced
            transparency and accountability measures to ensure all parties meet their commitments under
            the Paris Agreement. Sweden stands ready to share best practices and technological solutions
            that have enabled our progress toward a fossil-free economy.
            """
            
            # Save sample paper to file
            paper_path = os.path.join(temp_dir, "sample_paper.txt")
            with open(paper_path, "w") as f:
                f.write(sample_paper)
            
            # Output directory
            output_dir = os.path.join(temp_dir, "results")
            
            # Run analysis
            results = analyzer.run_analysis(paper_path, output_dir)
            
            # Print summary
            if results:
                logger.info("\nAnalysis Summary:")
                logger.info("----------------")
                for approach in results.get("top_approaches", []):
                    logger.info(f"{approach['rank']}. {approach['approach']}: {approach['score']}")
                
                # Clean up
                analyzer.cleanup()
    else:
        # Standard sample run for demonstration
        # Sample configuration
        config = {
            "topic": "Climate Change Mitigation",
            "country": "Sweden", 
            "committee": "UNEP"
        }
        
        # Save config to JSON file
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        
        # Create analyzer
        analyzer = MUNDelegateAnalyzer("config.json")
        
        # Sample delegate paper (for demonstration)
        sample_paper = """
        Sweden is committed to addressing climate change through ambitious mitigation strategies. 
        As a leader in renewable energy, Sweden has already achieved significant emissions reductions
        while maintaining economic growth. Our country aims to become one of the first fossil-free
        welfare states in the world. We have implemented a carbon tax since 1991, which has proven
        effective in reducing emissions while promoting innovation.

        Sweden recognizes the interconnected nature of climate challenges and advocates for a 
        comprehensive approach that includes all nations. We support the Paris Agreement framework
        and believe that developed countries must take the lead in emissions reductions while 
        supporting developing nations. Regional cooperation, particularly within the European Union
        and Nordic countries, has been central to our strategy.

        Sweden proposes strengthening international cooperation through increased climate financing,
        technology transfer, and capacity building. We advocate for a carbon pricing mechanism at the
        global level, similar to our successful national carbon tax. Additionally, we support enhanced
        transparency and accountability measures to ensure all parties meet their commitments under
        the Paris Agreement. Sweden stands ready to share best practices and technological solutions
        that have enabled our progress toward a fossil-free economy.
        """
        
        # Save sample paper to file
        with open("sample_paper.txt", "w") as f:
            f.write(sample_paper)
        
        # Run analysis
        results = analyzer.run_analysis("sample_paper.txt")
        
        # Print summary
        if results:
            print("\nAnalysis Summary:")
            print("----------------")
            approaches_sorted = sorted(
                results["similarity_scores"].keys(), 
                key=lambda x: results["similarity_scores"][x], 
                reverse=True
            )
            
            for approach in approaches_sorted:
                score = results["similarity_scores"][approach]
                print(f"{approach}: {score:.4f}")
            
            # Clean up
            analyzer.cleanup()
