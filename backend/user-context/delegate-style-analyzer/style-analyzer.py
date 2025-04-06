from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModel, pipeline
from bertopic import BERTopic
from keybert import KeyBERT
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.util import ngrams
import numpy as np
import json
import re
import statistics
import datetime
from collections import Counter
import spacy
from textstat import textstat
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import logging
import boto3
from botocore.exceptions import ClientError
import tempfile

# Configure logging for CloudWatch compatibility
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENV_S3_BUCKET = os.environ.get("STYLE_ANALYZER_S3_BUCKET")
ENV_S3_REGION = os.environ.get("STYLE_ANALYZER_S3_REGION", "us-east-1")
ENV_USE_CPU_ONLY = os.environ.get("USE_CPU_ONLY", "false").lower() == "true"
ENV_NLTK_DATA_PATH = os.environ.get("NLTK_DATA_PATH", "/tmp/nltk_data")
ENV_SPACY_MODEL_PATH = os.environ.get("SPACY_MODEL_PATH", "en_core_web_sm")
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"

# Check if running in Lambda/container environment
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
IS_CONTAINER = os.environ.get("ECS_CONTAINER_METADATA_URI") is not None
IS_AWS_ENV = IS_LAMBDA or IS_CONTAINER

# Singleton instance for AWS environments
_style_analyzer_instance = None

# Create Flask app only if not in Lambda environment
app = None
if not IS_LAMBDA:
    app = Flask(__name__)

# Setup S3 client for AWS environments
s3_client = None
if IS_AWS_ENV and ENV_S3_BUCKET:
    try:
        s3_client = boto3.client('s3', region_name=ENV_S3_REGION)
        logger.info(f"Initialized S3 client for region {ENV_S3_REGION}")
    except Exception as e:
        logger.error(f"Error initializing S3 client: {str(e)}")

# Setup NLTK data path
nltk.data.path.append(ENV_NLTK_DATA_PATH)

# Function to download NLTK resources if needed
def download_nltk_resources():
    """Download necessary NLTK resources to the configured path"""
    logger.info(f"Setting up NLTK resources at {ENV_NLTK_DATA_PATH}")
    
    # Create directory if it doesn't exist
    os.makedirs(ENV_NLTK_DATA_PATH, exist_ok=True)
    
    # Download resources if not already present
    resources = ['punkt', 'averaged_perceptron_tagger', 'stopwords']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
            logger.info(f"NLTK resource {resource} already downloaded")
        except LookupError:
            logger.info(f"Downloading NLTK resource: {resource}")
            nltk.download(resource, download_dir=ENV_NLTK_DATA_PATH)

# Function to download spaCy model if needed
def download_spacy_model():
    """Download spaCy model if needed"""
    if ENV_TEST_MODE:
        logger.info("Test mode: Using dummy spaCy model")
        return
    
    try:
        import spacy.util
        if not spacy.util.is_package(ENV_SPACY_MODEL_PATH):
            logger.info(f"Downloading spaCy model: {ENV_SPACY_MODEL_PATH}")
            spacy.cli.download(ENV_SPACY_MODEL_PATH)
            logger.info(f"Successfully downloaded spaCy model: {ENV_SPACY_MODEL_PATH}")
    except Exception as e:
        logger.error(f"Error setting up spaCy model: {str(e)}")

# Class for creating mock models in test environment
class MockModel:
    """Mock implementation for testing purposes"""
    def __init__(self, *args, **kwargs):
        pass
    
    def __call__(self, *args, **kwargs):
        return [{"label": "positive", "score": 0.9}]
    
    def encode(self, *args, **kwargs):
        return np.random.rand(1, 768)
    
    def extract_keywords(self, *args, **kwargs):
        return [("sample_keyword", 0.9), ("test", 0.8), ("example", 0.7)]
    
    def fit_transform(self, *args, **kwargs):
        return [0], np.random.rand(1, 10)
    
    def get_topic(self, *args, **kwargs):
        return [("word1", 0.9), ("word2", 0.8), ("word3", 0.7)]
    
    def get_feature_names_out(self, *args, **kwargs):
        return np.array(["word1", "word2", "word3"])

# Load pre-trained models
class StyleAnalyzer:
    def __init__(self):
        logger.info("Initializing StyleAnalyzer")
        
        # Set device configuration
        self.device = "cuda" if torch.cuda.is_available() and not ENV_USE_CPU_ONLY else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Lazy loading flags
        self._tokenizer_initialized = False
        self._model_initialized = False
        self._keybert_initialized = False
        self._bertopic_initialized = False
        self._nlp_initialized = False
        self._sentiment_analyzer_initialized = False
        
        # Ensure NLTK resources are available
        download_nltk_resources()
        
        # Set up stopwords
        self.stop_words = set(stopwords.words('english'))
        
        # Initialize placeholders
        self.tokenizer = None
        self.model = None
        self.keybert_model = None
        self.bertopic_model = None
        self.nlp = None
        self.sentiment_analyzer = None
        
        logger.info("StyleAnalyzer initialization complete")
    
    def _init_tokenizer(self):
        """Lazy initialization of tokenizer"""
        if not self._tokenizer_initialized:
            logger.info("Initializing DistilBERT tokenizer")
            if ENV_TEST_MODE:
                self.tokenizer = MockModel()
            else:
                self.tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
            self._tokenizer_initialized = True
    
    def _init_model(self):
        """Lazy initialization of model"""
        if not self._model_initialized:
            logger.info("Initializing DistilBERT model")
            if ENV_TEST_MODE:
                self.model = MockModel()
            else:
                self.model = AutoModel.from_pretrained('distilbert-base-uncased')
                if self.device == "cuda":
                    self.model = self.model.to(self.device)
            self._model_initialized = True
    
    def _init_keybert(self):
        """Lazy initialization of KeyBERT"""
        if not self._keybert_initialized:
            logger.info("Initializing KeyBERT")
            if ENV_TEST_MODE:
                self.keybert_model = MockModel()
            else:
                self.keybert_model = KeyBERT()
            self._keybert_initialized = True
    
    def _init_bertopic(self):
        """Lazy initialization of BERTopic"""
        if not self._bertopic_initialized:
            logger.info("Initializing BERTopic")
            if ENV_TEST_MODE:
                self.bertopic_model = MockModel()
            else:
                self.bertopic_model = BERTopic(embedding_model='distilbert-base-uncased')
            self._bertopic_initialized = True
    
    def _init_nlp(self):
        """Lazy initialization of spaCy"""
        if not self._nlp_initialized:
            logger.info("Initializing spaCy")
            if ENV_TEST_MODE:
                # Create a simple mock for spaCy
                from unittest.mock import MagicMock
                self.nlp = MagicMock()
                doc_mock = MagicMock()
                sent_mock = MagicMock()
                token_mock = MagicMock()
                
                # Configure the mocks
                self.nlp.return_value.sents = [sent_mock]
                self.nlp.return_value.ents = []
                sent_mock.text = "This is a test sentence."
                token_mock.is_punct = False
                token_mock.pos_ = "NOUN"
                token_mock.dep_ = "nsubj"
                sent_mock.__iter__.return_value = [token_mock]
            else:
                download_spacy_model()
                self.nlp = spacy.load(ENV_SPACY_MODEL_PATH)
            self._nlp_initialized = True
    
    def _init_sentiment_analyzer(self):
        """Lazy initialization of sentiment analyzer"""
        if not self._sentiment_analyzer_initialized:
            logger.info("Initializing sentiment analyzer")
            if ENV_TEST_MODE:
                self.sentiment_analyzer = MockModel()
            else:
                self.sentiment_analyzer = pipeline('sentiment-analysis', 
                                                 model='distilbert-base-uncased-finetuned-sst-2-english',
                                                 device=0 if self.device == "cuda" else -1)
            self._sentiment_analyzer_initialized = True
    
    def preprocess_text(self, text):
        # Basic text cleaning
        text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
        text = text.strip()
        return text
    
    def extract_metadata(self, text):
        """Extract metadata like committees, topics, time periods and roles"""
        # Ensure NLP is initialized
        self._init_nlp()
        self._init_keybert()
        
        doc = self.nlp(text)
        
        # Extract potential organizations and committees
        committees = []
        for ent in doc.ents:
            if ent.label_ in ["ORG", "GPE"]:
                committees.append(ent.text)
                
        # Extract topics (using KeyBERT)
        topics = [kw[0] for kw in self.keybert_model.extract_keywords(text, keyphrase_ngram_range=(1, 3), 
                                                               stop_words='english', 
                                                               top_n=5)]
        
        # Look for date patterns to determine time period
        date_pattern = r'\b(19|20)\d{2}\b|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b'
        dates = re.findall(date_pattern, text)
        time_period = [d[0] if d[0] else d[1] for d in dates if d[0] or d[1]]
        
        # Try to identify the delegate's role
        role_patterns = [
            r'\b(?:represent(?:ing|s|ed)?|delegat(?:e|ion)|on behalf of)\s+([A-Z][a-zA-Z\s]+)\b',
            r'\b(China|Russia|USA|United States|France|UK|United Kingdom|Germany|Japan|India|Brazil|South Africa|Australia|Canada|Mexico)\b'
        ]
        
        roles = []
        for pattern in role_patterns:
            matches = re.findall(pattern, text)
            roles.extend(matches)
            
        # Remove duplicates
        committees = list(set(committees))
        topics = list(set(topics))
        time_period = list(set(time_period))
        roles = list(set(roles))
        
        return {
            "committees": committees[:5],  # Limit to top 5
            "topics": topics,
            "time_period": time_period,
            "roles": roles
        }
    
    def analyze_vocabulary(self, text):
        """Analyze vocabulary diversity, complexity, jargon, etc."""
        # Tokenize and normalize words
        words = [word.lower() for word in word_tokenize(text) if word.isalnum()]
        
        # Remove stopwords for specialized vocabulary analysis
        content_words = [word for word in words if word not in self.stop_words]
        
        # Calculate vocabulary diversity metrics
        unique_words = set(words)
        vocabulary_diversity = len(unique_words) / len(words) if words else 0
        
        # Type-Token Ratio for content words only
        unique_content_words = set(content_words)
        content_ttr = len(unique_content_words) / len(content_words) if content_words else 0
        
        # Calculate readability scores
        readability = {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "gunning_fog": textstat.gunning_fog(text)
        }
        
        # Find frequent words
        word_freq = FreqDist(words)
        most_common = word_freq.most_common(20)
        
        # Find frequent bigrams and trigrams (potential phrases and expressions)
        bi_grams = list(ngrams(words, 2))
        tri_grams = list(ngrams(words, 3))
        
        bigram_freq = FreqDist(bi_grams)
        trigram_freq = FreqDist(tri_grams)
        
        common_bigrams = [' '.join(bg) for bg, _ in bigram_freq.most_common(15)]
        common_trigrams = [' '.join(tg) for tg, _ in trigram_freq.most_common(10)]
        
        # Identify potentially specialized terminology (longer words less common in general usage)
        long_words = [word for word in content_words if len(word) > 8]
        potential_jargon = list(set(long_words))[:20]  # Limit to 20 unique terms
        
        # Calculate word length metrics
        word_lengths = [len(word) for word in words]
        avg_word_length = sum(word_lengths) / len(word_lengths) if word_lengths else 0
        
        # Use TF-IDF to find distinctive terms
        if text:
            vectorizer = TfidfVectorizer(max_features=20)
            try:
                tfidf_matrix = vectorizer.fit_transform([text])
                feature_names = vectorizer.get_feature_names_out()
                tfidf_scores = tfidf_matrix.toarray()[0]
                distinctive_terms = [{"term": feature_names[i], "score": tfidf_scores[i]} 
                                   for i in tfidf_scores.argsort()[-15:][::-1]]
            except:
                distinctive_terms = []
        else:
            distinctive_terms = []
        
        # Determine formality level
        formality_indicators = {
            "contractions": len(re.findall(r"\b\w+'(?:ve|re|s|d|ll|t|m)\b", text)),
            "first_person": len(re.findall(r"\b(?:I|we|us|our|ours|ourselves|my|mine)\b", text, re.IGNORECASE)),
            "passive_voice": len(re.findall(r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b", text))
        }
        
        # Higher score means more formal
        formality_score = (10 - (formality_indicators["contractions"] / 100) + 
                          (formality_indicators["passive_voice"] / 50) - 
                          (formality_indicators["first_person"] / 100))
        formality_score = max(0, min(10, formality_score))  # Ensure between 0-10
        
        return {
            "diversity": {
                "type_token_ratio": vocabulary_diversity,
                "content_type_token_ratio": content_ttr
            },
            "complexity": readability,
            "frequent_terms": most_common,
            "phrases": {
                "bigrams": common_bigrams,
                "trigrams": common_trigrams
            },
            "specialized_terminology": potential_jargon,
            "distinctive_terms": distinctive_terms,
            "word_length": {
                "average": avg_word_length,
                "distribution": {
                    "min": min(word_lengths) if word_lengths else 0,
                    "max": max(word_lengths) if word_lengths else 0,
                    "median": statistics.median(word_lengths) if word_lengths else 0
                }
            },
            "formality": {
                "score": formality_score,
                "indicators": formality_indicators
            }
        }
    
    def analyze_sentence_structure(self, text):
        """Analyze sentence and paragraph structure"""
        # Parse with spaCy
        doc = self.nlp(text)
        
        # Get sentences
        sentences = list(doc.sents)
        
        # Calculate sentence lengths (in words)
        sentence_lengths = [len([token for token in sent if not token.is_punct]) for sent in sentences]
        
        # Calculate sentence complexity
        sentence_types = []
        for sent in sentences:
            # Count clauses by looking for verbs
            verbs = [token for token in sent if token.pos_ == "VERB"]
            
            if len(verbs) == 0:
                sentence_types.append("fragment")
            elif len(verbs) == 1:
                sentence_types.append("simple")
            elif len(verbs) == 2:
                # Check for subordinating conjunctions
                if any(token.dep_ == "mark" for token in sent):
                    sentence_types.append("complex")
                else:
                    sentence_types.append("compound")
            else:
                sentence_types.append("compound-complex")
        
        # Count sentence types
        sentence_type_counts = Counter(sentence_types)
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        paragraph_lengths = [len(sent_tokenize(p)) for p in paragraphs if p.strip()]
        
        # Identify transition words
        transition_patterns = r'\b(therefore|thus|consequently|furthermore|moreover|however|nevertheless|in addition|for example|for instance|in particular|specifically|in contrast|on the other hand|similarly|likewise|instead|meanwhile|subsequently|finally|in conclusion)\b'
        transitions = re.findall(transition_patterns, text, re.IGNORECASE)
        transition_counts = Counter([t.lower() for t in transitions])
        
        # Analyze punctuation patterns
        punctuation_pattern = r'[,.;:!?()[\]{}"\'-]'
        punctuation = re.findall(punctuation_pattern, text)
        punctuation_counts = Counter(punctuation)
        
        # Calculate distinctive punctuation ratio (punctuation per sentence)
        punct_per_sentence = len(punctuation) / len(sentences) if sentences else 0
        
        return {
            "sentence_metrics": {
                "count": len(sentences),
                "length": {
                    "average": sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0,
                    "min": min(sentence_lengths) if sentence_lengths else 0,
                    "max": max(sentence_lengths) if sentence_lengths else 0,
                    "median": statistics.median(sentence_lengths) if sentence_lengths else 0
                }
            },
            "sentence_types": {
                "counts": dict(sentence_type_counts),
                "distribution": {k: v/len(sentences) for k, v in sentence_type_counts.items()} if sentences else {}
            },
            "paragraph_metrics": {
                "count": len(paragraphs),
                "length": {
                    "average": sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0,
                    "min": min(paragraph_lengths) if paragraph_lengths else 0,
                    "max": max(paragraph_lengths) if paragraph_lengths else 0,
                    "median": statistics.median(paragraph_lengths) if paragraph_lengths else 0
                }
            },
            "transitions": {
                "frequent": dict(transition_counts.most_common(10)),
                "total": len(transitions),
                "density": len(transitions) / len(sentences) if sentences else 0
            },
            "punctuation": {
                "pattern": dict(punctuation_counts.most_common()),
                "per_sentence": punct_per_sentence
            }
        }
    
    def analyze_stylistic_devices(self, text):
        """Analyze rhetorical devices, tone, voice, etc."""
        doc = self.nlp(text)
        
        # Analyze active vs. passive voice
        active_count = 0
        passive_count = 0
        
        for sent in doc.sents:
            if any(token.dep_ == "nsubjpass" for token in sent):
                passive_count += 1
            else:
                active_count += 1
        
        # Identify potential rhetorical devices
        # Simplified detection of some common devices
        metaphors = []
        similes = []
        rhetorical_questions = []
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            
            # Potential similes
            if re.search(r'\b(?:like|as)\b.*\b(?:as|like)\b', sent_text, re.IGNORECASE):
                similes.append(sent_text)
            
            # Potential metaphors (very simplified detection)
            if re.search(r'\bis\b|\bare\b|\bwas\b|\bwere\b', sent_text) and not re.search(r'like|as', sent_text):
                for token in sent:
                    if token.pos_ == "NOUN" and token.head.pos_ == "NOUN" and token.dep_ == "attr":
                        metaphors.append(sent_text)
                        break
            
            # Rhetorical questions
            if sent_text.endswith('?') and any(word in sent_text.lower() for word in ['who', 'what', 'where', 'when', 'why', 'how']):
                if re.search(r'\b(?:consider|imagine|think about)\b', sent_text, re.IGNORECASE):
                    rhetorical_questions.append(sent_text)
        
        # Analyze tone indicators
        tone_patterns = {
            "authoritative": r'\b(?:must|should|need to|certainly|undoubtedly|clearly|evidently)\b',
            "cautionary": r'\b(?:warning|caution|careful|danger|risk|threat|crisis|urgent|emergency)\b',
            "optimistic": r'\b(?:hope|promising|opportunity|potential|progress|improve|success|beneficial)\b',
            "pessimistic": r'\b(?:unfortunately|sadly|regrettably|worryingly|concerning|alarming|failed|impossible)\b',
            "neutral": r'\b(?:appears|seems|suggests|indicates|may|might|could|possibly|approximately)\b',
            "emphatic": r'\b(?:extremely|very|highly|absolutely|completely|entirely|utterly|crucially|vitally)\b'
        }
        
        tone_indicators = {}
        for tone, pattern in tone_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            tone_indicators[tone] = len(matches)
        
        # Find emphasized text
        emphasis_patterns = {
            "italics": r'\*([^*]+)\*',
            "bold": r'\*\*([^*]+)\*\*',
            "underline": r'__([^_]+)__',
            "capitalization": r'\b[A-Z]{2,}\b'
        }
        
        emphasis = {}
        for style, pattern in emphasis_patterns.items():
            matches = re.findall(pattern, text)
            emphasis[style] = len(matches)
        
        # Analyze narrative techniques
        narrative_indicators = {
            "personal_anecdote": len(re.findall(r'\b(?:I saw|I witnessed|I experienced|I observed|I recall|I remember)\b', text, re.IGNORECASE)),
            "historical_reference": len(re.findall(r'\b(?:historically|in the past|previously|former|earlier|ancient|traditional)\b', text, re.IGNORECASE)),
            "hypothetical_scenario": len(re.findall(r'\b(?:imagine|suppose|consider|if|were|would|could|might|hypothetically)\b', text, re.IGNORECASE)),
            "case_study": len(re.findall(r'\b(?:case study|example|instance|illustration|demonstrates|shows)\b', text, re.IGNORECASE))
        }
        
        return {
            "voice": {
                "active": active_count,
                "passive": passive_count,
                "ratio": active_count / (active_count + passive_count) if (active_count + passive_count) > 0 else 0
            },
            "rhetorical_devices": {
                "metaphors": metaphors[:5],  # Limit to 5 examples
                "similes": similes[:5],
                "rhetorical_questions": rhetorical_questions[:5],
                "counts": {
                    "metaphors": len(metaphors),
                    "similes": len(similes),
                    "rhetorical_questions": len(rhetorical_questions)
                }
            },
            "tone_indicators": tone_indicators,
            "emphasis": emphasis,
            "narrative_techniques": narrative_indicators
        }
    
    def analyze_reasoning_patterns(self, text):
        """Analyze reasoning approaches and logical frameworks"""
        # Identify reasoning indicators
        reasoning_patterns = {
            "deductive": r'\b(?:therefore|thus|consequently|it follows that|we can conclude|this proves|inevitably|necessarily)\b',
            "inductive": r'\b(?:typically|generally|usually|often|in most cases|examples show|data suggests|pattern indicates)\b',
            "analogical": r'\b(?:similarly|likewise|in the same way|parallel|comparable to|just as|resembles)\b',
            "causal": r'\b(?:because|due to|as a result of|leads to|causes|effects|impacts|influences|affects)\b',
            "conditional": r'\b(?:if|unless|provided that|as long as|assuming that|in the event that|would|could|should)\b'
        }
        
        reasoning_indicators = {}
        for approach, pattern in reasoning_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            reasoning_indicators[approach] = len(matches)
        
        # Timeframe analysis
        timeframe_patterns = {
            "short_term": r'\b(?:immediate|immediately|urgent|shortly|near-term|soon|emergency|crisis|within days|within weeks|weeks|days|early)\b',
            "medium_term": r'\b(?:eventually|in time|gradually|within months|within years|months|years|middle)\b',
            "long_term": r'\b(?:sustained|sustainable|permanent|long-lasting|durable|long-term|decade|decades|centuries|future generations)\b'
        }
        
        timeframe_indicators = {}
        for timeframe, pattern in timeframe_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            timeframe_indicators[timeframe] = len(matches)
        
        # Counterargument handling
        counterargument_patterns = {
            "acknowledging": r'\b(?:while|although|though|despite|in spite of|it could be argued|some may argue|critics claim|opponents suggest)\b',
            "refuting": r'\b(?:however|nevertheless|nonetheless|yet|still|but|even so|in fact|actually|in reality|on the contrary)\b',
            "conceding": r'\b(?:granted|admittedly|it is true that|certainly|indeed|undoubtedly|undeniably|agreed)\b'
        }
        
        counterargument_indicators = {}
        for approach, pattern in counterargument_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            counterargument_indicators[approach] = len(matches)
        
        # Theoretical vs practical orientation
        theoretical_practical = {
            "theoretical": len(re.findall(r'\b(?:theory|theoretical|framework|concept|principle|paradigm|philosophical|hypothesis|conceptual)\b', text, re.IGNORECASE)),
            "practical": len(re.findall(r'\b(?:practical|pragmatic|implementable|actionable|feasible|workable|concrete|tangible|realistic|viable)\b', text, re.IGNORECASE))
        }
        
        # Logical framework references
        logical_frameworks = {
            "utilitarian": len(re.findall(r'\b(?:utility|greatest good|benefit|cost-benefit|maximize|welfare|wellbeing|happiness|outcome)\b', text, re.IGNORECASE)),
            "rights_based": len(re.findall(r'\b(?:rights|freedoms|liberties|dignity|autonomy|self-determination|sovereignty|entitled|entitled to)\b', text, re.IGNORECASE)),
            "virtue_ethics": len(re.findall(r'\b(?:virtue|character|integrity|excellence|moral|ethical|good|justice|fairness)\b', text, re.IGNORECASE)),
            "pragmatic": len(re.findall(r'\b(?:practical|workable|effective|efficient|results|outcome|success|achievement|impact)\b', text, re.IGNORECASE))
        }
        
        return {
            "reasoning_approaches": reasoning_indicators,
            "timeframe_orientation": timeframe_indicators,
            "counterargument_handling": counterargument_indicators,
            "theoretical_vs_practical": theoretical_practical,
            "logical_frameworks": logical_frameworks,
            "dominant_reasoning": max(reasoning_indicators.items(), key=lambda x: x[1])[0] if reasoning_indicators else "unknown",
            "dominant_timeframe": max(timeframe_indicators.items(), key=lambda x: x[1])[0] if timeframe_indicators else "unknown"
        }
    
    def analyze_evidence_usage(self, text):
        """Analyze evidence types and presentation patterns"""
        # Evidence type patterns
        evidence_patterns = {
            "statistics": r'\b(?:\d+%|\d+\s*percent|statistics show|data indicates|according to data|survey results|research findings|study shows|evidence suggests)\b',
            "historical_precedent": r'\b(?:historically|in the past|precedent|previous|earlier|former|ancient|traditional|history shows)\b',
            "case_study": r'\b(?:case study|example|instance|illustration|case of|demonstrated by|shown in|scenario|situation)\b',
            "expert_opinion": r'\b(?:expert|authority|specialist|according to|stated by|argues that|asserts that|claims that|maintains that)\b',
            "legal_document": r'\b(?:treaty|convention|agreement|resolution|charter|protocol|article|paragraph|clause|provision)\b'
        }
        
        evidence_types = {}
        for type_name, pattern in evidence_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            evidence_types[type_name] = len(matches)
        
        # Citation patterns
        citation_patterns = {
            "formal": r'\(\w+,\s*\d{4}\)|\[\d+\]',
            "name_year": r'\b(?:[A-Z][a-z]+\s+(?:et al\.)?,\s*\d{4})\b',
            "organization": r'\b(?:according to|as stated by|as reported by|cited by)\s+([A-Z][a-zA-Z\s]+)\b'
        }
        
        citation_counts = {}
        citations = []
        
        for style, pattern in citation_patterns.items():
            matches = re.findall(pattern, text)
            citation_counts[style] = len(matches)
            citations.extend(matches)
        
        # Find evidence integration techniques
        integration_patterns = {
            "quote_introduction": r'(?:states|argues|notes|observes|highlights|emphasizes|explains|suggests|points out|concludes|asserts)',
            "data_preface": r'(?:data shows|research indicates|studies demonstrate|evidence suggests|statistics reveal|findings confirm|results show)',
            "example_introduction": r'(?:for example|for instance|to illustrate|as an example|consider the case|such as|namely|specifically)'
        }
        
        integration_techniques = {}
        for technique, pattern in integration_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            integration_techniques[technique] = len(matches)
        
        # Analyze quantitative vs. qualitative balance
        quantitative_indicators = len(re.findall(r'\b(?:\d+%|\d+\s*percent|\d+\s*people|\d+\s*countries|\d+\s*cases|statistics|data|numbers|figures|quantities|amounts|measurements|rates|ratios|proportions)\b', text, re.IGNORECASE))
        
        qualitative_indicators = len(re.findall(r'\b(?:quality|experience|perception|feeling|belief|opinion|view|perspective|qualitative|narrative|descriptive|subjective|impression|interpretation)\b', text, re.IGNORECASE))
        
        total_evidence = sum(evidence_types.values())
        
        return {
            "evidence_types": evidence_types,
            "dominant_evidence": max(evidence_types.items(), key=lambda x: x[1])[0] if evidence_types else "unknown",
            "citation_patterns": citation_counts,
            "citations_found": citations[:10],  # Limit to 10 examples
            "integration_techniques": integration_techniques,
            "quantitative_qualitative_balance": {
                "quantitative_indicators": quantitative_indicators,
                "qualitative_indicators": qualitative_indicators,
                "ratio": quantitative_indicators / qualitative_indicators if qualitative_indicators > 0 else float('inf')
            },
            "evidence_density": total_evidence / len(sent_tokenize(text)) if text else 0
        }
    
    def analyze_persuasive_techniques(self, text):
        """Analyze persuasive techniques and appeals"""
        # Emotional appeal patterns
        emotion_patterns = {
            "fear": r'\b(?:danger|threat|risk|harm|catastrophe|disaster|crisis|emergency|alarming|disturbing|concerning|worrying)\b',
            "hope": r'\b(?:hope|promising|opportunity|potential|progress|improvement|solution|resolve|achieve|success|bright future)\b',
            "empathy": r'\b(?:suffering|pain|distress|hardship|tragedy|victims|affected|vulnerable|human cost|humanitarian|compassion)\b',
            "pride": r'\b(?:achievement|accomplishment|success|pride|honor|dignity|legacy|reputation|respect|standing|status)\b',
            "shame": r'\b(?:failure|embarrassment|disgrace|shame|humiliation|dishonor|disappointment|regret|remorse)\b'
        }
        
        emotional_appeals = {}
        for emotion, pattern in emotion_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            emotional_appeals[emotion] = len(matches)
        
        # Authority appeal patterns
        authority_patterns = {
            "expert": r'\b(?:expert|specialist|authority|professor|doctor|researcher|scientist|scholar)\b',
            "institutional": r'\b(?:United Nations|WHO|World Bank|UNICEF|UNESCO|EU|European Union|International|Agency|IPCC|Council)\b',
            "legal": r'\b(?:law|legal|constitution|statute|treaty|convention|agreement|resolution|charter|protocol)\b',
            "moral": r'\b(?:morally|ethically|right|wrong|good|evil|virtue|vice|ethical|moral|principle|value)\b',
            "historical": r'\b(?:history|historical|tradition|precedent|legacy|heritage|ancestry|roots|origin)\b'
        }
        
        authority_appeals = {}
        for authority, pattern in authority_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            authority_appeals[authority] = len(matches)
        
        # Urgency framing
        urgency_indicators = len(re.findall(r'\b(?:urgent|immediately|quickly|promptly|without delay|as soon as possible|critical|pressing|emergency|crisis|time-sensitive|deadline|rapidly)\b', text, re.IGNORECASE))
        
        # Necessity framing
        necessity_indicators = len(re.findall(r'\b(?:necessary|essential|crucial|vital|critical|imperative|must|required|needed|fundamental)\b', text, re.IGNORECASE))
        
        # Ethical framework references
        ethical_frameworks = {
            "human_rights": len(re.findall(r'\b(?:human rights|fundamental rights|basic rights|dignity|freedom|liberty|equality|justice)\b', text, re.IGNORECASE)),
            "justice": len(re.findall(r'\b(?:justice|fairness|equality|equity|fair|equal|equitable|just|unjust|inequitable)\b', text, re.IGNORECASE)),
            "responsibility": len(re.findall(r'\b(?:responsibility|obligation|duty|accountable|responsible|obligations|duties|commitment)\b', text, re.IGNORECASE)),
            "sustainability": len(re.findall(r'\b(?:sustainable|sustainability|future generations|long-term|environmental|ecological|conservation)\b', text, re.IGNORECASE)),
            "security": len(re.findall(r'\b(?:security|safety|protection|defense|safeguard|protect|defend|secure|safe)\b', text, re.IGNORECASE))
        }
        
        # Calculate appeal balance (logos, ethos, pathos)
        logos_indicators = sum(reasoning_indicators.values()) if 'reasoning_indicators' in locals() else 0
        ethos_indicators = sum(authority_appeals.values())
        pathos_indicators = sum(emotional_appeals.values())
        
        total_appeals = logos_indicators + ethos_indicators + pathos_indicators
        
        appeal_balance = {
            "logos": logos_indicators / total_appeals if total_appeals > 0 else 0,
            "ethos": ethos_indicators / total_appeals if total_appeals > 0 else 0,
            "pathos": pathos_indicators / total_appeals if total_appeals > 0 else 0
        }
        
        return {
            "emotional_appeals": emotional_appeals,
            "authority_appeals": authority_appeals,
            "urgency_framing": urgency_indicators,
            "necessity_framing": necessity_indicators,
            "ethical_frameworks": ethical_frameworks,
            "appeal_balance": appeal_balance,
            "dominant_appeal": max(appeal_balance.items(), key=lambda x: x[1])[0] if appeal_balance else "unknown",
            "dominant_emotion": max(emotional_appeals.items(), key=lambda x: x[1])[0] if emotional_appeals else "unknown",
            "dominant_authority": max(authority_appeals.items(), key=lambda x: x[1])[0] if authority_appeals else "unknown"
        }
    
    def analyze_thematic_patterns(self, text):
        """Analyze recurring topics and policy positions"""
        # Extract topics using BERTopic
        topics = []
        if text:
            try:
                docs = [text]
                topic_model = self.bertopic_model.fit_transform(docs)
                if topic_model[0]:
                    for topic_id in set(topic_model[0]):
                        if topic_id != -1:  # Exclude outlier topic
                            topic_words = [word for word, _ in self.bertopic_model.get_topic(topic_id)]
                            topics.append({"id": topic_id, "keywords": topic_words[:10]})
            except:
                # Fallback to KeyBERT for topic extraction
                keywords = self.keybert_model.extract_keywords(text, keyphrase_ngram_range=(1, 3), 
                                                        stop_words='english', 
                                                        top_n=10)
                topics = [{"id": i, "keywords": [kw[0]]} for i, kw in enumerate(keywords)]
        
        # Policy position indicators
        policy_patterns = {
            "cooperative": r'\b(?:cooperation|collaborate|partnership|ally|allies|joint|together|mutual|collectively|multilateral)\b',
            "confrontational": r'\b(?:confront|oppose|against|resist|challenge|condemn|reject|denounce|sanction)\b',
            "neutral": r'\b(?:neutral|impartial|balanced|even-handed|objective|non-aligned|third-party|mediator)\b',
            "progressive": r'\b(?:reform|progress|change|innovative|novel|pioneering|groundbreaking|transformative)\b',
            "conservative": r'\b(?:preserve|maintain|sustain|continue|traditional|conventional|established|status quo)\b'
        }
        
        policy_indicators = {}
        for position, pattern in policy_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            policy_indicators[position] = len(matches)
        
        # Regional focus
        region_patterns = {
            "global": r'\b(?:global|world|international|worldwide|planet|earth|universal|humanity)\b',
            "regional": r'\b(?:region|regional|neighboring|local|proximity|nearby|surrounding|area)\b',
            "north_america": r'\b(?:United States|America|Canada|Mexico|North America|US|USA)\b',
            "europe": r'\b(?:Europe|European Union|EU|UK|France|Germany|Italy|Spain|Belgium)\b',
            "asia": r'\b(?:Asia|China|Japan|India|Korea|ASEAN|Indonesia|Malaysia|Philippines)\b',
            "middle_east": r'\b(?:Middle East|Gulf|Arab|Saudi Arabia|Iran|Iraq|Syria|Israel|Turkey)\b',
            "africa": r'\b(?:Africa|African Union|South Africa|Nigeria|Egypt|Kenya|Ethiopia|Sudan)\b',
            "latin_america": r'\b(?:Latin America|South America|Brazil|Argentina|Chile|Colombia|Venezuela|Caribbean)\b'
        }
        
        regional_focus = {}
        for region, pattern in region_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            regional_focus[region] = len(matches)
        
        # Ideological markers
        ideology_patterns = {
            "liberal": r'\b(?:liberal|liberty|freedom|individual|rights|market|democracy|democratic|private)\b',
            "socialist": r'\b(?:socialist|equality|equity|collective|public|state-owned|redistribution|communal)\b',
            "nationalist": r'\b(?:national|sovereign|independence|patriot|homeland|domestic|self-determination)\b',
            "globalist": r'\b(?:global|interconnected|integration|multilateral|interdependence|transnational)\b',
            "environmentalist": r'\b(?:environment|sustainable|ecological|green|conservation|preservation|climate)\b',
            "religious": r'\b(?:religious|faith|belief|god|divine|sacred|spiritual|moral|ethical|values)\b'
        }
        
        ideological_markers = {}
        for ideology, pattern in ideology_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            ideological_markers[ideology] = len(matches)
        
        # Position evolution (would need multiple documents to fully analyze)
        position_evolution = "Would require multiple documents with timestamps for analysis"
        
        return {
            "topics": topics,
            "policy_positions": policy_indicators,
            "dominant_position": max(policy_indicators.items(), key=lambda x: x[1])[0] if policy_indicators else "unknown",
            "regional_focus": regional_focus,
            "primary_region": max(regional_focus.items(), key=lambda x: x[1])[0] if regional_focus else "unknown",
            "ideological_markers": ideological_markers,
            "dominant_ideology": max(ideological_markers.items(), key=lambda x: x[1])[0] if ideological_markers else "unknown",
            "position_evolution": position_evolution
        }
    
    def analyze_solution_approaches(self, text):
        """Analyze solution types and approaches"""
        # Solution type patterns
        solution_patterns = {
            "bilateral": r'\b(?:bilateral|between two|mutual|reciprocal|two countries|two nations|two parties|two states)\b',
            "multilateral": r'\b(?:multilateral|international|global|regional|cooperation|collective|jointly|together)\b',
            "sanctions": r'\b(?:sanction|embargo|restriction|ban|blockade|punitive|penalize|isolate)\b',
            "aid": r'\b(?:aid|assistance|support|help|relief|donation|funding|finance|grant|loan)\b',
            "diplomatic": r'\b(?:diplomatic|diplomacy|negotiation|mediation|dialogue|talks|discussion|engagement|summit)\b',
            "military": r'\b(?:military|force|intervention|operation|troops|soldiers|armed|defense|security|war)\b',
            "economic": r'\b(?:economic|trade|investment|financial|fiscal|monetary|market|commerce|business)\b',
            "legal": r'\b(?:legal|law|regulation|legislation|statute|rule|court|judicial|tribunal|judge)\b',
            "educational": r'\b(?:education|training|awareness|curriculum|school|university|learn|teach|instruct)\b',
            "technological": r'\b(?:technology|technical|digital|innovation|solution|system|infrastructure|platform)\b'
        }
        
        solution_types = {}
        for type_name, pattern in solution_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            solution_types[type_name] = len(matches)
        
        # Timeframe patterns
        timeframe_patterns = {
            "short_term": r'\b(?:immediate|immediately|urgent|quickly|promptly|short-term|near-term|soon|emergency)\b',
            "medium_term": r'\b(?:medium-term|intermediate|transitional|interim|temporary|provisional|for now)\b',
            "long_term": r'\b(?:long-term|permanent|lasting|sustainable|durable|persistent|enduring|ongoing|future)\b'
        }
        
        timeframes = {}
        for frame, pattern in timeframe_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            timeframes[frame] = len(matches)
        
        # Idealistic vs. pragmatic patterns
        approach_balance = {
            "idealistic": len(re.findall(r'\b(?:ideal|perfect|ultimate|comprehensive|complete|universal|utopian|principle|vision|aspiration)\b', text, re.IGNORECASE)),
            "pragmatic": len(re.findall(r'\b(?:pragmatic|practical|realistic|feasible|workable|implementable|achievable|doable|attainable|possible)\b', text, re.IGNORECASE))
        }
        
        # Implementation considerations
        implementation_patterns = {
            "funding": r'\b(?:fund|funding|finance|cost|budget|expense|resource|allocation|investment)\b',
            "logistics": r'\b(?:logistics|implementation|operation|mechanism|procedure|process|method|system|execution)\b',
            "monitoring": r'\b(?:monitor|oversight|verification|inspection|supervision|evaluation|assessment|review|control)\b',
            "compliance": r'\b(?:compliance|adherence|conformity|observance|respect|abide|follow|obligation|commitment)\b',
            "stakeholder_engagement": r'\b(?:stakeholder|participant|party|actor|involve|engage|consult|include|participate)\b'
        }
        
        implementation_considerations = {}
        for consideration, pattern in implementation_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            implementation_considerations[consideration] = len(matches)
        
        # UN agencies and funding sources
        agency_patterns = {
            "un_general": r'\b(?:United Nations|UN|General Assembly|Security Council|Secretary-General)\b',
            "undp": r'\b(?:UNDP|Development Programme|development assistance)\b',
            "unicef": r'\b(?:UNICEF|Children\'s Fund|child welfare|children\'s rights)\b',
            "who": r'\b(?:WHO|World Health Organization|health|disease|pandemic)\b',
            "unhcr": r'\b(?:UNHCR|refugee|asylum|displacement|displaced|humanitarian)\b',
            "wfp": r'\b(?:WFP|World Food Programme|food security|hunger|nutrition)\b',
            "worldbank": r'\b(?:World Bank|financing|lending|development fund|investment)\b',
            "imf": r'\b(?:IMF|International Monetary Fund|financial assistance|loan|debt)\b'
        }
        
        un_agencies = {}
        for agency, pattern in agency_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            un_agencies[agency] = len(matches)
        
        # Innovation approach
        innovation_patterns = {
            "adapt_existing": r'\b(?:adapt|modify|adjust|refine|improve|enhance|update|build on|extend)\b',
            "historical_successful": r'\b(?:historical|precedent|previous|past|successful|proven|effective|worked before)\b',
            "traditional": r'\b(?:traditional|conventional|standard|typical|common|usual|normal|regular)\b',
            "novel": r'\b(?:novel|new|innovative|original|creative|unprecedented|unique|groundbreaking|pioneering)\b'
        }
        
        innovation_approach = {}
        for approach, pattern in innovation_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            innovation_approach[approach] = len(matches)
        
        return {
            "solution_types": solution_types,
            "primary_solution_type": max(solution_types.items(), key=lambda x: x[1])[0] if solution_types else "unknown",
            "timeframe": timeframes,
            "primary_timeframe": max(timeframes.items(), key=lambda x: x[1])[0] if timeframes else "unknown",
            "idealistic_vs_pragmatic": approach_balance,
            "dominant_approach": "idealistic" if approach_balance["idealistic"] > approach_balance["pragmatic"] else "pragmatic",
            "implementation_considerations": implementation_considerations,
            "un_agencies_mentioned": un_agencies,
            "innovation_approach": innovation_approach,
            "primary_innovation_approach": max(innovation_approach.items(), key=lambda x: x[1])[0] if innovation_approach else "unknown"
        }
    
    def identify_distinctive_elements(self, text):
        """Identify linguistic quirks and unique stylistic elements"""
        # Unusual phrasing and quirks
        doc = self.nlp(text)
        
        # Look for uncommon n-grams
        sentences = [sent.text for sent in doc.sents]
        words = [token.text.lower() for token in doc if token.is_alpha]
        
        # Get bigrams and trigrams
        bigrams = list(nltk.bigrams(words))
        trigrams = list(nltk.trigrams(words))
        
        # Count frequencies
        bigram_freq = FreqDist(bigrams)
        trigram_freq = FreqDist(trigrams)
        
        # Find rare constructions (hapax legomena - occurring only once)
        rare_bigrams = [' '.join(bg) for bg, count in bigram_freq.items() if count == 1][:10]
        rare_trigrams = [' '.join(tg) for tg, count in trigram_freq.items() if count == 1][:10]
        
        # Identify unusual word combinations (high mutual information)
        unusual_collocations = []
        if len(words) > 50:  # Need enough text for meaningful analysis
            try:
                finder = nltk.collocations.BigramCollocationFinder.from_words(words)
                finder.apply_freq_filter(2)  # Minimum frequency
                unusual_collocations = [' '.join(collocation) for collocation in finder.nbest(nltk.collocations.BigramAssocMeasures().pmi, 10)]
            except:
                unusual_collocations = []
        
        # Look for non-standard formatting
        formatting_patterns = {
            "parenthetical_asides": len(re.findall(r'\([^)]{15,}\)', text)),  # Longer parenthetical comments
            "dashes": len(re.findall(r'\s—\s|\s--\s', text)),
            "ellipses": len(re.findall(r'\.{3,}|…', text)),
            "unusual_punctuation": len(re.findall(r'[;:]{2,}|[!?]{2,}', text)),
            "mid_sentence_linebreaks": len(re.findall(r'[a-z],?\n[a-z]', text, re.IGNORECASE))
        }
        
        # Signature phrases (repeated unusual phrases)
        repeated_phrases = []
        for sent in sentences:
            # Look for phrases that appear multiple times
            matches = re.findall(r'\b(\w+\s+\w+\s+\w+\s+\w+)\b', sent)
            for match in matches:
                if text.lower().count(match.lower()) >= 2 and len(match) > 15:
                    repeated_phrases.append(match)
        
        # Remove duplicates
        repeated_phrases = list(set(repeated_phrases))[:5]
        
        # Analyze openings and closings
        first_sentences = []
        last_sentences = []
        
        # Split by potential paragraph breaks
        paragraphs = re.split(r'\n\s*\n', text)
        
        if paragraphs:
            for para in paragraphs:
                para_sentences = sent_tokenize(para)
                if para_sentences:
                    first_sentences.append(para_sentences[0])
                    if len(para_sentences) > 1:
                        last_sentences.append(para_sentences[-1])
        
        # Analyze opening techniques
        opening_techniques = {
            "question": sum(1 for s in first_sentences if s.endswith('?')),
            "statistic": sum(1 for s in first_sentences if re.search(r'\d+%|\d+ percent|\d+\.\d+', s)),
            "quote": sum(1 for s in first_sentences if re.search(r'".*?"', s)),
            "historical": sum(1 for s in first_sentences if re.search(r'\b(?:history|past|traditional|ancient|previous|earlier|former)\b', s, re.IGNORECASE)),
            "direct_address": sum(1 for s in first_sentences if re.search(r'\b(?:distinguished|honorable|esteemed|respected|ladies and gentlemen|delegates|colleagues)\b', s, re.IGNORECASE))
        }
        
        # Analyze closing techniques
        closing_techniques = {
            "call_to_action": sum(1 for s in last_sentences if re.search(r'\b(?:must|should|need to|urge|call upon|appeal|action)\b', s, re.IGNORECASE)),
            "future_oriented": sum(1 for s in last_sentences if re.search(r'\b(?:future|tomorrow|coming|ahead|next|look forward|vision|horizon)\b', s, re.IGNORECASE)),
            "summary": sum(1 for s in last_sentences if re.search(r'\b(?:conclusion|summary|summarize|sum up|therefore|thus|in conclusion|to conclude)\b', s, re.IGNORECASE)),
            "rhetorical_question": sum(1 for s in last_sentences if s.endswith('?')),
            "quote_ending": sum(1 for s in last_sentences if re.search(r'".*?"', s))
        }
        
        # Non-standard diplomatic elements
        non_standard_elements = {
            "first_person": len(re.findall(r'\b(?:I|my|mine|myself)\b', text, re.IGNORECASE)),
            "colloquialisms": len(re.findall(r'\b(?:pretty much|kind of|sort of|you know|basically|actually|stuff|things)\b', text, re.IGNORECASE)),
            "contractions": len(re.findall(r"\b\w+'(?:ve|re|s|d|ll|t|m)\b", text)),
            "rhetorical_flourish": len(re.findall(r'[!]{2,}|[?]{2,}|\b(?:absolutely|incredibly|extremely|amazingly)\b', text, re.IGNORECASE)),
            "metaphorical_language": len(re.findall(r'\b(?:like a|as a|resembles a|similar to a)\b', text, re.IGNORECASE))
        }
        
        return {
            "linguistic_quirks": {
                "rare_bigrams": rare_bigrams,
                "rare_trigrams": rare_trigrams,
                "unusual_collocations": unusual_collocations
            },
            "formatting_choices": formatting_patterns,
            "signature_phrases": repeated_phrases,
            "opening_techniques": opening_techniques,
            "closing_techniques": closing_techniques,
            "non_standard_elements": non_standard_elements,
            "dominant_non_standard": max(non_standard_elements.items(), key=lambda x: x[1])[0] if non_standard_elements else "none"
        }
    
    def identify_implicit_patterns(self, text):
        """Identify underlying values, assumptions, and biases"""
        # Identify value markers
        value_patterns = {
            "individualism": r'\b(?:individual|personal|private|independence|autonomy|self|liberty|freedom)\b',
            "collectivism": r'\b(?:collective|community|public|common|shared|mutual|together|cooperation|solidarity)\b',
            "hierarchy": r'\b(?:authority|order|structure|leadership|rank|status|position|superiority|subordination)\b',
            "egalitarianism": r'\b(?:equality|equal|equity|fairness|justice|parity|balance|impartiality)\b',
            "traditionalism": r'\b(?:tradition|conventional|historical|heritage|customs|values|preserve|maintain)\b',
            "progressivism": r'\b(?:progress|change|reform|advance|improve|innovate|modernize|transform)\b',
            "security": r'\b(?:security|safety|protection|stability|defense|preserve|guard|shield)\b',
            "openness": r'\b(?:open|transparent|diverse|inclusive|broad|variety|flexible|adaptable)\b'
        }
        
        values = {}
        for value, pattern in value_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            values[value] = len(matches)
        
        # Identify assumption indicators
        assumption_patterns = {
            "causality": r'\b(?:because|due to|as a result|consequently|therefore|thus|hence|since|leads to)\b',
            "inevitability": r'\b(?:inevitably|necessarily|unavoidably|certainly|surely|undoubtedly|must|will)\b',
            "universality": r'\b(?:everyone|everybody|all|universal|globally|worldwide|without exception|in every case)\b',
            "simplification": r'\b(?:simply|merely|just|only|nothing but|straightforward|obvious|clear|plain)\b',
            "dichotomy": r'\b(?:either|or|versus|against|opposing|contrary|opposite|dichotomy|binary)\b'
        }
        
        assumptions = {}
        for assumption, pattern in assumption_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            assumptions[assumption] = len(matches)
        
        # Analyze topic selection bias
        # This is complex and would require multiple documents for comparison
        topic_bias = "Would require multiple documents for comprehensive analysis"
        
        # Identify potential blind spots (what's not mentioned)
        blind_spot_checklist = {
            "environmental_impact": not bool(re.search(r'\b(?:environment|climate|ecological|pollution|sustainable|green)\b', text, re.IGNORECASE)),
            "gender_consideration": not bool(re.search(r'\b(?:gender|women|men|female|male|equality|discrimination)\b', text, re.IGNORECASE)), 
            "economic_inequality": not bool(re.search(r'\b(?:inequality|poverty|wealth gap|economic disparity|distribution)\b', text, re.IGNORECASE)),
            "human_rights": not bool(re.search(r'\b(?:human rights|civil liberties|freedom|oppression|persecution)\b', text, re.IGNORECASE)),
            "historical_context": not bool(re.search(r'\b(?:history|historical|past|precedent|context|background)\b', text, re.IGNORECASE)),
            "implementation_details": not bool(re.search(r'\b(?:implement|operation|execution|procedure|logistics|practical)\b', text, re.IGNORECASE)),
            "alternative_viewpoints": not bool(re.search(r'\b(?:alternative|different perspective|contrary|opposing view|other side)\b', text, re.IGNORECASE))
        }
        
        # Identify intuitive leaps (connections made without explicit explanation)
        intuitive_leaps = []
        doc = self.nlp(text)
        
        for sent in doc.sents:
            # Look for conclusion indicators without clear premises
            if re.search(r'\b(?:therefore|thus|hence|consequently|so)\b', sent.text, re.IGNORECASE):
                # Check if preceding sentences contain premise indicators
                if not re.search(r'\b(?:because|since|as|due to|given that)\b', sent.text, re.IGNORECASE):
                    intuitive_leaps.append(sent.text)
        
        # Identify emotional undertones
        emotional_undertones = {
            "urgency": len(re.findall(r'\b(?:urgent|immediately|quickly|promptly|without delay|as soon as possible|critical|pressing)\b', text, re.IGNORECASE)),
            "concern": len(re.findall(r'\b(?:concern|worry|troubling|problematic|disturbing|alarming|disconcerting)\b', text, re.IGNORECASE)),
            "optimism": len(re.findall(r'\b(?:optimistic|hopeful|promising|positive|encouraging|bright|favorable)\b', text, re.IGNORECASE)),
            "pessimism": len(re.findall(r'\b(?:pessimistic|grim|bleak|negative|discouraging|dark|unfavorable)\b', text, re.IGNORECASE)),
            "confidence": len(re.findall(r'\b(?:confident|certain|sure|definite|convinced|without doubt|assuredly)\b', text, re.IGNORECASE)),
            "uncertainty": len(re.findall(r'\b(?:uncertain|unsure|doubtful|questionable|unclear|ambiguous|vague)\b', text, re.IGNORECASE))
        }
        
        return {
            "value_hierarchy": values,
            "primary_values": sorted(values.items(), key=lambda x: x[1], reverse=True)[:3] if values else [],
            "implicit_assumptions": assumptions,
            "topic_selection_bias": topic_bias,
            "blind_spots": [spot for spot, is_blind in blind_spot_checklist.items() if is_blind],
            "intuitive_leaps": intuitive_leaps[:5],  # Limit to 5 examples
            "emotional_undertones": emotional_undertones,
            "dominant_emotional_tone": max(emotional_undertones.items(), key=lambda x: x[1])[0] if emotional_undertones else "neutral"
        }
        
    def analyze_style_for_quantitative_assessment(self, text):
        """Create numerical metrics for style analysis"""
        
        # Initialize metrics dictionary
        metrics = {}
        
        # Calculate reasoning tendencies (1-10 scale)
        reasoning_patterns = {
            "deductive": r'\b(?:therefore|thus|consequently|it follows that|we can conclude|this proves|inevitably|necessarily)\b',
            "inductive": r'\b(?:typically|generally|usually|often|in most cases|examples show|data suggests|pattern indicates)\b',
            "analogical": r'\b(?:similarly|likewise|in the same way|parallel|comparable to|just as|resembles)\b',
            "causal": r'\b(?:because|due to|as a result of|leads to|causes|effects|impacts|influences|affects)\b',
            "abstract": r'\b(?:concept|theory|principle|framework|model|paradigm|theoretical|abstract|general)\b',
            "concrete": r'\b(?:specific|particular|instance|example|case|concrete|practical|actual|real)\b'
        }
        
        # Calculate raw counts
        reasoning_counts = {}
        for approach, pattern in reasoning_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            reasoning_counts[approach] = len(matches)
        
        # Normalize to 1-10 scale
        total_indicators = sum(reasoning_counts.values()) + 1  # Add 1 to avoid division by zero
        
        for approach, count in reasoning_counts.items():
            # Calculate percentage and scale to 1-10
            percentage = count / total_indicators
            metrics[f"reasoning_{approach}"] = round(1 + percentage * 9, 1)  # Scale from 1-10
        
        # Calculate value metrics (1-10 scale)
        value_patterns = {
            "individualism": r'\b(?:individual|personal|private|independence|autonomy|self|liberty|freedom)\b',
            "collectivism": r'\b(?:collective|community|public|common|shared|mutual|together|cooperation|solidarity)\b',
            "pragmatism": r'\b(?:practical|pragmatic|workable|realistic|feasible|implementable|achievable|doable)\b',
            "idealism": r'\b(?:ideal|utopian|perfect|aspiration|vision|optimum|principle|theoretical|abstract)\b',
            "conservatism": r'\b(?:preserve|maintain|protect|traditional|conventional|established|status quo)\b',
            "progressivism": r'\b(?:progress|change|reform|advance|improve|innovate|modernize|transform)\b'
        }
        
        # Calculate raw counts
        value_counts = {}
        for value, pattern in value_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            value_counts[value] = len(matches)
        
        # Normalize to 1-10 scale
        total_value_indicators = sum(value_counts.values()) + 1  # Add 1 to avoid division by zero
        
        for value, count in value_counts.items():
            percentage = count / total_value_indicators
            metrics[f"value_{value}"] = round(1 + percentage * 9, 1)  # Scale from 1-10
        
        # Calculate cognitive complexity metrics
        sentence_lengths = [len(word_tokenize(s)) for s in sent_tokenize(text)]
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        
        # Linguistic complexity indicators
        subordinate_clauses = len(re.findall(r'\b(?:because|since|although|though|while|whereas|if|unless|until|after|before)\b', text, re.IGNORECASE))
        complex_transitions = len(re.findall(r'\b(?:furthermore|moreover|nevertheless|consequently|subsequently|alternatively|conversely|meanwhile)\b', text, re.IGNORECASE))
        
        # Estimate cognitive complexity score (1-10)
        complexity_score = min(10, 1 + (avg_sentence_length / 10) + (subordinate_clauses / 20) + (complex_transitions / 10))
        metrics["cognitive_complexity"] = round(complexity_score, 1)
        
        # Calculate persuasive mode distributions
        persuasive_patterns = {
            "logos": r'\b(?:logic|reason|evidence|data|statistic|fact|analysis|study|research|logical|rational|proof)\b',
            "ethos": r'\b(?:expert|authority|credible|reputable|trustworthy|reliable|integrity|character|qualification)\b',
            "pathos": r'\b(?:feel|emotion|suffer|pain|hope|fear|concern|worry|care|affect|touch|move|heart)\b'
        }
        
        # Calculate raw counts
        persuasive_counts = {}
        for mode, pattern in persuasive_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            persuasive_counts[mode] = len(matches)
        
        # Calculate probability distributions (sum to 1.0)
        total_persuasive = sum(persuasive_counts.values())
        if total_persuasive > 0:
            for mode, count in persuasive_counts.items():
                metrics[f"persuasive_{mode}_probability"] = round(count / total_persuasive, 2)
        else:
            # Default to equal distribution
            for mode in persuasive_patterns.keys():
                metrics[f"persuasive_{mode}_probability"] = 0.33
        
        # Calculate linguistic style metrics
        style_patterns = {
            "formal": r'\b(?:furthermore|moreover|thus|therefore|consequently|hence|regarding|concerning|pursuant|aforementioned)\b',
            "technical": r'\b(?:methodology|implementation|framework|mechanism|infrastructure|component|parameter|function|variable)\b',
            "diplomatic": r'\b(?:honorable|excellency|esteemed|distinguished|delegation|representative|bilateral|multilateral)\b',
            "academic": r'\b(?:study|research|literature|theory|hypothesis|analysis|methodology|conclusion|findings|scholarly)\b',
            "emotive": r'\b(?:deeply|greatly|strongly|profoundly|gravely|heartily|sincerely|earnestly|passionately)\b'
        }
        
        # Calculate frequency metrics
        for style, pattern in style_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            metrics[f"style_{style}_frequency"] = len(matches) / max(1, len(sent_tokenize(text)))
        
        return metrics
    
    def analyze_style(self, text, country=None, committee=None):
        """Main method to perform comprehensive style analysis"""
        logger.info(f"Analyzing text style{f' for {country}' if country else ''}{f' in {committee}' if committee else ''}")
        
        # Preprocess the text
        processed_text = self.preprocess_text(text)
        
        # Extract metadata
        metadata = self.extract_metadata(processed_text)
        
        # Analyze vocabulary and language
        vocabulary_analysis = self.analyze_vocabulary(processed_text)
        
        # Analyze sentence structure
        sentence_analysis = self.analyze_sentence_structure(processed_text)
        
        # Analyze stylistic devices
        stylistic_analysis = self.analyze_stylistic_devices(processed_text)
        
        # Analyze reasoning patterns
        reasoning_analysis = self.analyze_reasoning_patterns(processed_text)
        
        # Analyze evidence usage
        evidence_analysis = self.analyze_evidence_usage(processed_text)
        
        # Analyze persuasive techniques
        persuasive_analysis = self.analyze_persuasive_techniques(processed_text)
        
        # Analyze thematic patterns
        thematic_analysis = self.analyze_thematic_patterns(processed_text)
        
        # Analyze solution approaches
        solution_analysis = self.analyze_solution_approaches(processed_text)
        
        # Identify distinctive elements
        distinctive_elements = self.identify_distinctive_elements(processed_text)
        
        # Identify implicit patterns
        implicit_patterns = self.identify_implicit_patterns(processed_text)
        
        # Calculate quantitative assessments
        quantitative_metrics = self.analyze_style_for_quantitative_assessment(processed_text)
        
        # Compile all results into structured JSON format
        result = {
            "delegateProfile": {
                "metadata": metadata,
                "country": country,
                "committee": committee,
                "executiveSummary": {
                    "wordCount": len(word_tokenize(processed_text)),
                    "sentenceCount": len(sent_tokenize(processed_text)),
                    "paragraphCount": len(re.split(r'\n\s*\n', processed_text)),
                    "dominantReasoning": reasoning_analysis.get("dominant_reasoning", "unknown"),
                    "dominantPolicyPosition": thematic_analysis.get("dominant_position", "unknown"),
                    "dominantSolutionApproach": solution_analysis.get("primary_solution_type", "unknown"),
                    "primaryValues": implicit_patterns.get("primary_values", [])
                }
            },
            "linguisticPatterns": {
                "vocabulary": vocabulary_analysis,
                "sentenceStructure": sentence_analysis,
                "stylisticDevices": stylistic_analysis,
                "distinctiveElements": distinctive_elements
            },
            "cognitiveFrameworks": {
                "reasoningPatterns": reasoning_analysis,
                "epistemologicalApproach": {
                    "evidenceUsage": evidence_analysis,
                    "authorityAppeals": persuasive_analysis.get("authority_appeals", {})
                },
                "problemFraming": {
                    "issueDefinition": thematic_analysis.get("topics", []),
                    "regionalFocus": thematic_analysis.get("regional_focus", {}),
                    "timeframeOrientation": reasoning_analysis.get("timeframe_orientation", {})
                },
                "solutionDevelopment": solution_analysis
            },
            "argumentativeStrategies": {
                "persuasiveTechniques": persuasive_analysis,
                "evidenceUsage": evidence_analysis,
                "openingClosingTechniques": {
                    "openings": distinctive_elements.get("opening_techniques", {}),
                    "closings": distinctive_elements.get("closing_techniques", {})
                }
            },
            "valueHierarchies": implicit_patterns,
            "quantitativeAssessments": quantitative_metrics
        }
        
        # Add timestamp
        result["analysisTimestamp"] = str(datetime.datetime.now())
        
        # Save to S3 if configured
        if IS_AWS_ENV and ENV_S3_BUCKET and s3_client:
            self._save_analysis_to_s3(result, country, committee)
        
        return result
    
    def _save_analysis_to_s3(self, analysis, country=None, committee=None):
        """Save analysis results to S3"""
        if not s3_client:
            return
        
        try:
            # Generate a unique key
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            country_safe = re.sub(r'[^\w]', '_', country or "unknown")
            committee_safe = re.sub(r'[^\w]', '_', committee or "unknown")
            
            s3_key = f"analyses/{country_safe}/{committee_safe}/{timestamp}.json"
            
            # Convert to JSON
            analysis_json = json.dumps(analysis)
            
            # Upload to S3
            s3_client.put_object(
                Bucket=ENV_S3_BUCKET,
                Key=s3_key,
                Body=analysis_json,
                ContentType="application/json"
            )
            
            logger.info(f"Saved analysis to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Error saving analysis to S3: {str(e)}")

# Factory method for getting the StyleAnalyzer instance
def get_analyzer_instance():
    """Get the StyleAnalyzer singleton instance"""
    global _style_analyzer_instance
    if _style_analyzer_instance is None:
        _style_analyzer_instance = StyleAnalyzer()
    return _style_analyzer_instance

# Define Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler function"""
    logger.info(f"Received Lambda event: {json.dumps(event)}")
    
    try:
        # Get analyzer instance
        analyzer = get_analyzer_instance()
        
        # Check if request is from API Gateway
        if "body" in event:
            try:
                # API Gateway format (body as string)
                payload = json.loads(event["body"])
            except (TypeError, json.JSONDecodeError):
                logger.error("Failed to parse request body as JSON")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid JSON in request body"})
                }
        else:
            # Direct invocation format
            payload = event
        
        # Extract text and metadata
        text = payload.get("text", "")
        country = payload.get("country")
        committee = payload.get("committee")
        
        # Check for S3 path
        if not text and "s3Path" in payload:
            text = _get_text_from_s3(payload["s3Path"])
        
        if not text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required parameter: text"})
            }
        
        # Perform analysis
        result = analyzer.analyze_style(text, country, committee)
        
        # Return results
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def _get_text_from_s3(s3_path):
    """Get text from S3 path"""
    if not s3_client:
        raise ValueError("S3 client not initialized")
    
    if not s3_path.startswith("s3://"):
        raise ValueError(f"Invalid S3 path: {s3_path}")
    
    # Parse S3 path
    path_parts = s3_path[5:].split("/", 1)
    bucket = path_parts[0]
    key = path_parts[1] if len(path_parts) > 1 else ""
    
    try:
        # Get object from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Error retrieving text from S3: {str(e)}")
        raise

# Define container handler
def container_handler(request_json):
    """Handler for container deployment (ECS)"""
    try:
        # Get analyzer instance
        analyzer = get_analyzer_instance()
        
        # Extract parameters
        text = request_json.get("text", "")
        country = request_json.get("country")
        committee = request_json.get("committee")
        
        # Check for S3 path
        if not text and "s3Path" in request_json:
            text = _get_text_from_s3(request_json["s3Path"])
        
        if not text:
            return {
                "status": "error",
                "error": "Missing required parameter: text"
            }
        
        # Perform analysis
        result = analyzer.analyze_style(text, country, committee)
        
        # Return results
        return {
            "status": "success",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Error processing container request: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }

# Define Flask routes if not in Lambda environment
if app:
    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Flask endpoint for analysis"""
        try:
            # Get request data
            request_json = request.get_json()
            
            if not request_json:
                return jsonify({"error": "Missing JSON request body"}), 400
            
            # Use the container handler to process the request
            result = container_handler(request_json)
            
            # Return results
            if result.get("status") == "error":
                return jsonify({"error": result.get("error")}), 400
            
            return jsonify(result.get("result", {}))
        
        except Exception as e:
            logger.error(f"Error processing Flask request: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({"status": "healthy", "timestamp": str(datetime.datetime.now())})

# For local development
if __name__ == "__main__" and app:
    # Use environment variable for port with default 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)