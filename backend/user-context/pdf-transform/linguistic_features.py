#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Linguistic Features Extractor

This module extracts detailed linguistic features from text for stylometric analysis.
It helps identify writing style characteristics and patterns of language use.
"""

import re
import logging
import string
import statistics
from collections import Counter
from typing import Dict, List, Set, Tuple, Any, Optional, Union
import os
import time
import json
import tempfile
from functools import lru_cache

import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.util import ngrams
import textstat
import numpy as np

# AWS imports - only import if AWS environment is available
AWS_AVAILABLE = False
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    pass

# Set up environment variables
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_AWS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
ENV_MEMORY_LIMIT = int(os.environ.get("FEATURE_EXTRACTOR_MEMORY_LIMIT", "0"))
ENV_CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_METRICS_NAMESPACE", "PDFTransform")
ENV_S3_BUCKET = os.environ.get("PDF_TRANSFORM_S3_BUCKET")

# Configure logging
logging.basicConfig(
    level=logging.INFO if not ENV_AWS_LAMBDA else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Setup metrics if in AWS environment
metrics = None
if AWS_AVAILABLE and ENV_AWS_LAMBDA:
    try:
        # Initialize CloudWatch client outside of handler for better cold start performance
        cloudwatch = boto3.client('cloudwatch')
        def put_metric(name, value, unit='Count', dimensions=None):
            try:
                if dimensions is None:
                    dimensions = []
                cloudwatch.put_metric_data(
                    Namespace=ENV_CLOUDWATCH_NAMESPACE,
                    MetricData=[{
                        'MetricName': name,
                        'Value': value,
                        'Unit': unit,
                        'Dimensions': dimensions
                    }]
                )
            except Exception as e:
                logger.warning(f"Failed to put CloudWatch metric {name}: {e}")
        
        metrics = {
            'put_metric': put_metric
        }
    except Exception as e:
        logger.warning(f"Failed to initialize CloudWatch metrics: {e}")

# Ensure NLTK resources are available - do this during initialization, not in handler
nltk_resources = ['punkt', 'averaged_perceptron_tagger', 'stopwords']
nltk_dir = os.path.join(tempfile.gettempdir(), 'nltk_data') if ENV_AWS_LAMBDA else None

# Set NLTK data path for Lambda environment
if ENV_AWS_LAMBDA:
    os.environ['NLTK_DATA'] = nltk_dir
    nltk.data.path.insert(0, nltk_dir)

# Download NLTK resources if needed - do this during initialization, not in handler
for resource in nltk_resources:
    try:
        # Check if resource exists
        resource_path = f'tokenizers/{resource}' if resource == 'punkt' else f'corpora/{resource}'
        nltk.data.find(resource_path)
    except LookupError:
        # Download resource
        nltk.download(resource, quiet=True, download_dir=nltk_dir)

from nltk.corpus import stopwords


class LinguisticFeaturesExtractor:
    """Extract linguistic features for stylometric analysis"""
    
    def __init__(self, test_mode: bool = ENV_TEST_MODE, memory_limit: int = ENV_MEMORY_LIMIT):
        """
        Initialize the linguistic features extractor
        
        Args:
            test_mode: Whether to run in test mode with simplified processing
            memory_limit: Memory limit in MB (0 for no limit)
        """
        self.test_mode = test_mode
        self.memory_limit = memory_limit
        self.stopwords = set(stopwords.words('english'))
        self.function_words = self._load_function_words()
        
        # Initialize AWS clients if available
        self.s3_client = None
        if AWS_AVAILABLE and not test_mode:
            try:
                self.s3_client = boto3.client('s3')
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
        
        logger.info(f"Initialized LinguisticFeaturesExtractor (test_mode={test_mode}, memory_limit={memory_limit})")
    
    def extract_features(self, text: str) -> Dict[str, Any]:
        """
        Extract linguistic features from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of linguistic features
        """
        # Track timing for performance monitoring
        start_time = time.time()
        
        # Check if text is empty
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for feature extraction")
            return {}
        
        # Simplified processing for test mode
        if self.test_mode:
            result = self._extract_simplified_features(text)
            logger.info(f"Extracted simplified features in test mode in {time.time() - start_time:.2f}s")
            return result
        
        # Check memory limit
        if self.memory_limit > 0 and len(text) > self.memory_limit * 100:  # Rough estimate: 100 chars per KB
            logger.warning(f"Text too large for memory limit: {len(text)} chars > {self.memory_limit * 100}")
            # Process a subset of the text
            text_sample = text[:self.memory_limit * 100]
            logger.info(f"Processing sample of text: {len(text_sample)} chars")
            text = text_sample
        
        try:
            # Tokenize text
            words = word_tokenize(text.lower())
            
            # Filter non-words
            valid_words = [word for word in words if word.isalpha()]
            
            # Get sentences
            sentences = sent_tokenize(text)
            
            # Calculate word length statistics
            word_lengths = [len(word) for word in valid_words if word]
            
            # Create dictionary to store all features
            features = {}
            
            # Basic text statistics
            features.update(self._extract_basic_statistics(text, valid_words, sentences))
            
            # Lexical features
            features.update(self._extract_lexical_features(valid_words, word_lengths))
            
            # Syntactic features
            features.update(self._extract_syntactic_features(text, sentences))
            
            # POS features
            features.update(self._extract_pos_features(valid_words))
            
            # N-gram features
            features.update(self._extract_ngram_features(valid_words))
            
            # Readability features
            features.update(self._extract_readability_features(text))
            
            # Function word features
            features.update(self._extract_function_word_features(valid_words))
            
            # Punctuation features
            features.update(self._extract_punctuation_features(text))
            
            # Sentiment features
            features.update(self._extract_sentiment_features(text))
            
            # Add processing metadata
            features["processing_metadata"] = {
                "processing_time": time.time() - start_time,
                "text_length": len(text),
                "test_mode": self.test_mode,
                "memory_limited": self.memory_limit > 0,
                "timestamp": time.time()
            }
            
            # Report metrics if available
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('LinguisticFeatureExtractionTime', 
                                          time.time() - start_time, 
                                          'Seconds')
                    metrics['put_metric']('TextLength', len(text), 'Count')
                    metrics['put_metric']('SentenceCount', len(sentences), 'Count')
                    metrics['put_metric']('WordCount', len(valid_words), 'Count')
                except Exception as e:
                    logger.warning(f"Failed to report metrics: {e}")
            
            logger.info(f"Extracted features in {time.time() - start_time:.2f}s")
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            
            # Return basic features in case of error
            return {
                "error": str(e),
                "processing_metadata": {
                    "error": True,
                    "processing_time": time.time() - start_time,
                    "text_length": len(text),
                    "test_mode": self.test_mode
                }
            }
    
    def _extract_simplified_features(self, text: str) -> Dict[str, Any]:
        """
        Extract simplified features for test environment
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of simplified features
        """
        # Get basic counts
        word_count = len(text.split())
        sentence_count = max(1, text.count('.') + text.count('!') + text.count('?'))
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": word_count / sentence_count,
            "char_count": len(text),
            "chars_per_word": len(text) / max(1, word_count),
            "test_mode": True,
            "processing_metadata": {
                "simplified": True,
                "test_mode": True,
                "timestamp": time.time()
            }
        }
    
    def extract_segment_features(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract features for each text segment.
        
        Args:
            segments: List of segment dictionaries
            
        Returns:
            List of segments with features added
        """
        start_time = time.time()
        segments_processed = 0
        errors = 0
        
        for i, segment in enumerate(segments):
            segment_text = segment["text"]
            try:
                segment_features = self.extract_features(segment_text)
                segments[i]["linguistic_features"] = segment_features
                segments_processed += 1
            except Exception as e:
                logger.error(f"Error extracting features for segment {i}: {e}")
                segments[i]["linguistic_features"] = {
                    "error": str(e),
                    "processing_metadata": {
                        "error": True,
                        "test_mode": self.test_mode
                    }
                }
                errors += 1
        
        # Report metrics if available
        if metrics and AWS_AVAILABLE:
            try:
                metrics['put_metric']('SegmentsProcessed', segments_processed, 'Count')
                metrics['put_metric']('SegmentProcessingErrors', errors, 'Count')
                metrics['put_metric']('SegmentProcessingTime', 
                                      time.time() - start_time, 
                                      'Seconds')
            except Exception as e:
                logger.warning(f"Failed to report segment metrics: {e}")
        
        logger.info(f"Processed {segments_processed} segments with {errors} errors in {time.time() - start_time:.2f}s")
        return segments
    
    def extract_features_from_s3(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Extract features from text stored in S3
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Dictionary of linguistic features
        """
        if not AWS_AVAILABLE or not self.s3_client:
            raise ImportError("boto3 is required for S3 operations")
        
        try:
            # Get object from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            text = response['Body'].read().decode('utf-8')
            
            # Extract features
            features = self.extract_features(text)
            
            # Add S3 metadata
            features["s3_metadata"] = {
                "bucket": bucket,
                "key": key,
                "size": response['ContentLength'],
                "last_modified": response['LastModified'].isoformat()
            }
            
            return features
            
        except ClientError as e:
            logger.error(f"Error getting object {key} from bucket {bucket}: {e}")
            raise
    
    def save_features_to_s3(self, features: Dict[str, Any], bucket: str, key: str) -> str:
        """
        Save features to S3
        
        Args:
            features: Features dictionary
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            S3 URI of saved object
        """
        if not AWS_AVAILABLE or not self.s3_client:
            raise ImportError("boto3 is required for S3 operations")
        
        try:
            # Convert features to JSON
            features_json = json.dumps(features, default=str)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=features_json,
                ContentType='application/json'
            )
            
            logger.info(f"Saved features to s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"
            
        except ClientError as e:
            logger.error(f"Error saving features to s3://{bucket}/{key}: {e}")
            raise
    
    def _extract_basic_statistics(self, text: str, words: List[str], sentences: List[str]) -> Dict[str, Any]:
        """
        Extract basic text statistics.
        
        Args:
            text: Full text
            words: List of words
            sentences: List of sentences
            
        Returns:
            Dictionary of basic statistics
        """
        # Calculate basic counts
        char_count = len(text)
        word_count = len(words)
        sentence_count = len(sentences)
        unique_words = set(words)
        
        # Avoid division by zero
        if word_count == 0:
            return {
                "char_count": char_count,
                "word_count": word_count,
                "sentence_count": sentence_count,
                "unique_word_count": len(unique_words),
                "chars_per_word": 0,
                "words_per_sentence": 0
            }
        
        # Calculate ratios
        chars_per_word = sum(len(word) for word in words) / word_count
        
        if sentence_count == 0:
            words_per_sentence = 0
        else:
            words_per_sentence = word_count / sentence_count
        
        return {
            "char_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "unique_word_count": len(unique_words),
            "chars_per_word": chars_per_word,
            "words_per_sentence": words_per_sentence
        }
    
    def _extract_lexical_features(self, words: List[str], word_lengths: List[int]) -> Dict[str, Any]:
        """
        Extract lexical features.
        
        Args:
            words: List of words
            word_lengths: List of word lengths
            
        Returns:
            Dictionary of lexical features
        """
        # Calculate type-token ratio
        if not words:
            return {
                "type_token_ratio": 0,
                "hapax_legomena_ratio": 0,
                "avg_word_length": 0,
                "std_word_length": 0,
                "word_length_distribution": {},
                "vocabulary_richness": 0
            }
        
        unique_words = set(words)
        type_token_ratio = len(unique_words) / len(words)
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Count hapax legomena (words that appear only once)
        hapax_legomena = sum(1 for word, count in word_counts.items() if count == 1)
        hapax_legomena_ratio = hapax_legomena / len(words)
        
        # Word length statistics
        avg_word_length = sum(word_lengths) / len(word_lengths) if word_lengths else 0
        
        if len(word_lengths) > 1:
            std_word_length = statistics.stdev(word_lengths)
        else:
            std_word_length = 0
        
        # Word length distribution
        word_length_distribution = Counter(word_lengths)
        word_length_distribution = {str(length): count for length, count in word_length_distribution.items()}
        
        # Vocabulary richness (Yule's K)
        vocabulary_richness = self._calculate_yules_k(words)
        
        return {
            "type_token_ratio": type_token_ratio,
            "hapax_legomena_ratio": hapax_legomena_ratio,
            "avg_word_length": avg_word_length,
            "std_word_length": std_word_length,
            "word_length_distribution": word_length_distribution,
            "vocabulary_richness": vocabulary_richness
        }
    
    def _extract_syntactic_features(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """
        Extract syntactic features.
        
        Args:
            text: Full text
            sentences: List of sentences
            
        Returns:
            Dictionary of syntactic features
        """
        # Extract sentence length statistics
        sentence_lengths = [len(word_tokenize(s)) for s in sentences]
        
        if not sentence_lengths:
            return {
                "avg_sentence_length": 0,
                "std_sentence_length": 0,
                "short_sentence_ratio": 0,
                "medium_sentence_ratio": 0,
                "long_sentence_ratio": 0,
                "sentence_length_distribution": {},
                "passive_voice_ratio": 0,
                "question_ratio": 0,
                "exclamation_ratio": 0
            }
        
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
        
        if len(sentence_lengths) > 1:
            std_sentence_length = statistics.stdev(sentence_lengths)
        else:
            std_sentence_length = 0
        
        # Sentence length distribution
        short_sentences = sum(1 for length in sentence_lengths if length < 10)
        medium_sentences = sum(1 for length in sentence_lengths if 10 <= length <= 25)
        long_sentences = sum(1 for length in sentence_lengths if length > 25)
        
        short_sentence_ratio = short_sentences / len(sentence_lengths)
        medium_sentence_ratio = medium_sentences / len(sentence_lengths)
        long_sentence_ratio = long_sentences / len(sentence_lengths)
        
        sentence_length_distribution = Counter(sentence_lengths)
        sentence_length_distribution = {str(length): count for length, count in sentence_length_distribution.items()}
        
        # Passive voice detection
        passive_count = 0
        for sentence in sentences:
            tokens = word_tokenize(sentence.lower())
            tagged = pos_tag(tokens)
            
            # Look for passive voice patterns
            for i in range(len(tagged) - 2):
                # Basic passive pattern: be verb + past participle
                if (tagged[i][1] in ['VBZ', 'VBP', 'VBD', 'VBN', 'VB'] and 
                    tagged[i][0] in ['is', 'are', 'was', 'were', 'be', 'been', 'being'] and 
                    tagged[i+1][1] == 'VBN'):
                    passive_count += 1
                    break
        
        passive_voice_ratio = passive_count / len(sentences)
        
        # Question and exclamation detection
        question_count = sum(1 for s in sentences if s.strip().endswith('?'))
        exclamation_count = sum(1 for s in sentences if s.strip().endswith('!'))
        
        question_ratio = question_count / len(sentences)
        exclamation_ratio = exclamation_count / len(sentences)
        
        return {
            "avg_sentence_length": avg_sentence_length,
            "std_sentence_length": std_sentence_length,
            "short_sentence_ratio": short_sentence_ratio,
            "medium_sentence_ratio": medium_sentence_ratio,
            "long_sentence_ratio": long_sentence_ratio,
            "sentence_length_distribution": sentence_length_distribution,
            "passive_voice_ratio": passive_voice_ratio,
            "question_ratio": question_ratio,
            "exclamation_ratio": exclamation_ratio
        }
    
    def _extract_pos_features(self, words: List[str]) -> Dict[str, Any]:
        """
        Extract part-of-speech features.
        
        Args:
            words: List of words
            
        Returns:
            Dictionary of POS features
        """
        if not words:
            return {"pos_ratios": {}}
        
        # Get POS tags
        tagged_words = pos_tag(words)
        
        # Count POS tags
        pos_counts = Counter(tag for word, tag in tagged_words)
        
        # Calculate POS ratios
        total_words = len(words)
        pos_ratios = {tag: count / total_words for tag, count in pos_counts.items()}
        
        # Group similar POS tags
        grouped_pos = {
            "noun_ratio": sum(pos_ratios.get(tag, 0) for tag in ['NN', 'NNS', 'NNP', 'NNPS']),
            "verb_ratio": sum(pos_ratios.get(tag, 0) for tag in ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']),
            "adjective_ratio": sum(pos_ratios.get(tag, 0) for tag in ['JJ', 'JJR', 'JJS']),
            "adverb_ratio": sum(pos_ratios.get(tag, 0) for tag in ['RB', 'RBR', 'RBS']),
            "pronoun_ratio": sum(pos_ratios.get(tag, 0) for tag in ['PRP', 'PRP$', 'WP', 'WP$']),
            "preposition_ratio": sum(pos_ratios.get(tag, 0) for tag in ['IN']),
            "conjunction_ratio": sum(pos_ratios.get(tag, 0) for tag in ['CC', 'IN']),
            "determiner_ratio": sum(pos_ratios.get(tag, 0) for tag in ['DT', 'PDT', 'WDT']),
            "interjection_ratio": sum(pos_ratios.get(tag, 0) for tag in ['UH'])
        }
        
        return {
            "pos_ratios": pos_ratios,
            "grouped_pos": grouped_pos
        }
    
    def _extract_ngram_features(self, words: List[str]) -> Dict[str, Any]:
        """
        Extract n-gram features.
        
        Args:
            words: List of words
            
        Returns:
            Dictionary of n-gram features
        """
        if len(words) < 2:
            return {
                "top_bigrams": {},
                "top_trigrams": {}
            }
        
        # Generate n-grams
        bigrams_list = list(ngrams(words, 2))
        trigrams_list = list(ngrams(words, 3)) if len(words) >= 3 else []
        
        # Count n-grams
        bigram_counts = Counter(bigrams_list)
        trigram_counts = Counter(trigrams_list)
        
        # Get top n-grams
        top_bigrams = {' '.join(gram): count for gram, count in bigram_counts.most_common(20)}
        top_trigrams = {' '.join(gram): count for gram, count in trigram_counts.most_common(20)}
        
        return {
            "top_bigrams": top_bigrams,
            "top_trigrams": top_trigrams
        }
    
    def _extract_readability_features(self, text: str) -> Dict[str, Any]:
        """
        Extract readability features.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of readability features
        """
        try:
            # Calculate readability scores
            flesch_reading_ease = textstat.flesch_reading_ease(text)
            flesch_kincaid_grade = textstat.flesch_kincaid_grade(text)
            smog_index = textstat.smog_index(text)
            coleman_liau_index = textstat.coleman_liau_index(text)
            automated_readability_index = textstat.automated_readability_index(text)
            dale_chall_readability_score = textstat.dale_chall_readability_score(text)
            difficult_words = textstat.difficult_words(text)
            linsear_write_formula = textstat.linsear_write_formula(text)
            gunning_fog = textstat.gunning_fog(text)
            text_standard = textstat.text_standard(text, float_output=True)
            
            return {
                "flesch_reading_ease": flesch_reading_ease,
                "flesch_kincaid_grade": flesch_kincaid_grade,
                "smog_index": smog_index,
                "coleman_liau_index": coleman_liau_index,
                "automated_readability_index": automated_readability_index,
                "dale_chall_readability_score": dale_chall_readability_score,
                "difficult_words": difficult_words,
                "linsear_write_formula": linsear_write_formula,
                "gunning_fog": gunning_fog,
                "text_standard": text_standard
            }
        except Exception as e:
            logger.warning(f"Error calculating readability features: {e}")
            return {}
    
    def _extract_function_word_features(self, words: List[str]) -> Dict[str, Any]:
        """
        Extract function word features.
        
        Args:
            words: List of words
            
        Returns:
            Dictionary of function word features
        """
        if not words:
            return {
                "function_word_ratio": 0,
                "stopword_ratio": 0,
                "function_word_categories": {}
            }
        
        # Count function words and stopwords
        function_word_count = sum(1 for word in words if word in self.function_words)
        stopword_count = sum(1 for word in words if word in self.stopwords)
        
        # Calculate ratios
        total_words = len(words)
        function_word_ratio = function_word_count / total_words
        stopword_ratio = stopword_count / total_words
        
        # Count function words by category
        function_word_categories = {
            "articles": sum(1 for word in words if word in ['a', 'an', 'the']) / total_words,
            "prepositions": sum(1 for word in words if word in self._get_function_words_by_category('prepositions')) / total_words,
            "conjunctions": sum(1 for word in words if word in self._get_function_words_by_category('conjunctions')) / total_words,
            "pronouns": sum(1 for word in words if word in self._get_function_words_by_category('pronouns')) / total_words,
            "auxiliary_verbs": sum(1 for word in words if word in self._get_function_words_by_category('auxiliary_verbs')) / total_words,
            "modals": sum(1 for word in words if word in self._get_function_words_by_category('modals')) / total_words,
            "quantifiers": sum(1 for word in words if word in self._get_function_words_by_category('quantifiers')) / total_words
        }
        
        return {
            "function_word_ratio": function_word_ratio,
            "stopword_ratio": stopword_ratio,
            "function_word_categories": function_word_categories
        }
    
    def _extract_punctuation_features(self, text: str) -> Dict[str, Any]:
        """
        Extract punctuation features.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of punctuation features
        """
        # Count punctuation marks
        punctuation_counts = {p: text.count(p) for p in string.punctuation}
        
        # Calculate total punctuation
        total_punctuation = sum(punctuation_counts.values())
        
        # Calculate total character count
        total_chars = len(text)
        
        if total_chars == 0:
            return {
                "punctuation_ratio": 0,
                "punctuation_counts": punctuation_counts
            }
        
        # Calculate punctuation ratio
        punctuation_ratio = total_punctuation / total_chars
        
        # Group some punctuation marks
        grouped_punctuation = {
            "comma_ratio": punctuation_counts.get(',', 0) / total_chars,
            "period_ratio": punctuation_counts.get('.', 0) / total_chars,
            "semicolon_ratio": punctuation_counts.get(';', 0) / total_chars,
            "colon_ratio": punctuation_counts.get(':', 0) / total_chars,
            "question_mark_ratio": punctuation_counts.get('?', 0) / total_chars,
            "exclamation_mark_ratio": punctuation_counts.get('!', 0) / total_chars,
            "quotation_mark_ratio": (punctuation_counts.get('"', 0) + punctuation_counts.get("'", 0)) / total_chars,
            "bracket_ratio": (punctuation_counts.get('(', 0) + punctuation_counts.get(')', 0) + 
                              punctuation_counts.get('[', 0) + punctuation_counts.get(']', 0) + 
                              punctuation_counts.get('{', 0) + punctuation_counts.get('}', 0)) / total_chars
        }
        
        return {
            "punctuation_ratio": punctuation_ratio,
            "punctuation_counts": punctuation_counts,
            "grouped_punctuation": grouped_punctuation
        }
    
    def _extract_sentiment_features(self, text: str) -> Dict[str, Any]:
        """
        Extract sentiment features using lexicon-based approach.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of sentiment features
        """
        # Define sentiment lexicons
        positive_words = set([
            'good', 'great', 'excellent', 'positive', 'outstanding', 'exceptional', 'remarkable',
            'wonderful', 'fantastic', 'terrific', 'tremendous', 'impressive', 'marvelous',
            'superb', 'brilliant', 'awesome', 'fabulous', 'extraordinary', 'incredible',
            'amazing', 'perfect', 'supreme', 'beautiful', 'delightful', 'favorable',
            'beneficial', 'superior', 'valuable', 'fortunate', 'pleasant', 'satisfying',
            'successful', 'effective', 'efficient', 'adequate', 'decent', 'fine',
            'satisfactory', 'acceptable', 'admirable', 'commendable'
        ])
        
        negative_words = set([
            'bad', 'poor', 'terrible', 'negative', 'awful', 'horrible', 'dreadful',
            'abysmal', 'appalling', 'atrocious', 'inadequate', 'inferior', 'mediocre',
            'substandard', 'unacceptable', 'disappointing', 'unsatisfactory', 'disastrous',
            'catastrophic', 'tragic', 'unfortunate', 'unfavorable', 'detrimental', 'adverse',
            'harmful', 'damaging', 'deficient', 'defective', 'faulty', 'useless', 'worthless',
            'insufficient', 'problematic', 'troublesome', 'difficult', 'challenging', 'severe',
            'serious', 'critical', 'dire', 'grave', 'harsh', 'grim'
        ])
        
        # Tokenize text and convert to lowercase
        words = word_tokenize(text.lower())
        
        # Count positive and negative words
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        total_sentiment_words = positive_count + negative_count
        
        # Avoid division by zero
        if total_sentiment_words == 0:
            return {
                "positive_word_ratio": 0,
                "negative_word_ratio": 0,
                "sentiment_polarity": 0
            }
        
        # Calculate sentiment measures
        positive_ratio = positive_count / total_sentiment_words if total_sentiment_words > 0 else 0
        negative_ratio = negative_count / total_sentiment_words if total_sentiment_words > 0 else 0
        
        # Calculate sentiment polarity (-1 to 1)
        sentiment_polarity = (positive_count - negative_count) / total_sentiment_words if total_sentiment_words > 0 else 0
        
        return {
            "positive_word_ratio": positive_ratio,
            "negative_word_ratio": negative_ratio,
            "sentiment_polarity": sentiment_polarity
        }
    
    def _calculate_yules_k(self, words: List[str]) -> float:
        """
        Calculate Yule's K measure of vocabulary richness.
        
        Args:
            words: List of words
            
        Returns:
            Yule's K measure
        """
        if not words:
            return 0
        
        word_counts = Counter(words)
        frequency_spectrum = Counter(word_counts.values())
        
        # Calculate M (total number of word occurrences)
        M = sum(word_counts.values())
        
        if M <= 1:
            return 0
        
        # Calculate Yule's K
        sum_fi2 = sum(freq_count * (freq ** 2) for freq, freq_count in frequency_spectrum.items())
        K = 10000 * (sum_fi2 - M) / (M ** 2)
        
        return K
    
    def _load_function_words(self) -> Set[str]:
        """
        Load common function words.
        
        Returns:
            Set of function words
        """
        # Define function words by category
        function_words = set()
        
        # Articles
        function_words.update(['a', 'an', 'the'])
        
        # Prepositions
        function_words.update([
            'about', 'above', 'across', 'after', 'against', 'along', 'among', 'around',
            'at', 'before', 'behind', 'below', 'beneath', 'beside', 'between', 'beyond',
            'by', 'despite', 'down', 'during', 'except', 'for', 'from', 'in', 'inside',
            'into', 'like', 'near', 'of', 'off', 'on', 'onto', 'out', 'outside', 'over',
            'past', 'since', 'through', 'throughout', 'to', 'toward', 'under', 'underneath',
            'until', 'up', 'upon', 'with', 'within', 'without'
        ])
        
        # Conjunctions
        function_words.update([
            'and', 'but', 'or', 'nor', 'so', 'yet', 'for', 'because', 'if', 'although',
            'since', 'unless', 'while', 'whereas', 'whether', 'though', 'even though',
            'even if', 'as', 'as if', 'as though', 'that', 'when', 'whenever', 'where',
            'wherever', 'after', 'before', 'once', 'until', 'till', 'so that'
        ])
        
        # Pronouns
        function_words.update([
            'i', 'me', 'my', 'mine', 'myself', 'you', 'your', 'yours', 'yourself',
            'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it',
            'its', 'itself', 'we', 'us', 'our', 'ours', 'ourselves', 'they', 'them',
            'their', 'theirs', 'themselves', 'this', 'that', 'these', 'those', 'who',
            'whom', 'whose', 'which', 'what', 'whatever', 'whoever', 'whomever',
            'whichever', 'where', 'when', 'how', 'why'
        ])
        
        # Auxiliary verbs
        function_words.update([
            'am', 'is', 'are', 'was', 'were', 'be', 'being', 'been', 'have', 'has',
            'had', 'having', 'do', 'does', 'did', 'doing', 'get', 'gets', 'got', 'gotten'
        ])
        
        # Modal verbs
        function_words.update([
            'can', 'could', 'may', 'might', 'must', 'shall', 'should', 'will', 'would',
            'ought', 'need', 'dare'
        ])
        
        # Quantifiers
        function_words.update([
            'all', 'any', 'both', 'each', 'every', 'few', 'many', 'much', 'most', 'some',
            'several', 'little', 'enough', 'more', 'less', 'no', 'none', 'one', 'two',
            'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'
        ])
        
        return function_words
    
    def _get_function_words_by_category(self, category: str) -> Set[str]:
        """
        Get function words for a specific category.
        
        Args:
            category: Function word category
            
        Returns:
            Set of function words for the category
        """
        if category == 'prepositions':
            return {
                'about', 'above', 'across', 'after', 'against', 'along', 'among', 'around',
                'at', 'before', 'behind', 'below', 'beneath', 'beside', 'between', 'beyond',
                'by', 'despite', 'down', 'during', 'except', 'for', 'from', 'in', 'inside',
                'into', 'like', 'near', 'of', 'off', 'on', 'onto', 'out', 'outside', 'over',
                'past', 'since', 'through', 'throughout', 'to', 'toward', 'under', 'underneath',
                'until', 'up', 'upon', 'with', 'within', 'without'
            }
        elif category == 'conjunctions':
            return {
                'and', 'but', 'or', 'nor', 'so', 'yet', 'for', 'because', 'if', 'although',
                'since', 'unless', 'while', 'whereas', 'whether', 'though', 'even though',
                'even if', 'as', 'as if', 'as though', 'that', 'when', 'whenever', 'where',
                'wherever', 'after', 'before', 'once', 'until', 'till', 'so that'
            }
        elif category == 'pronouns':
            return {
                'i', 'me', 'my', 'mine', 'myself', 'you', 'your', 'yours', 'yourself',
                'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it',
                'its', 'itself', 'we', 'us', 'our', 'ours', 'ourselves', 'they', 'them',
                'their', 'theirs', 'themselves', 'this', 'that', 'these', 'those', 'who',
                'whom', 'whose', 'which', 'what', 'whatever', 'whoever', 'whomever',
                'whichever', 'where', 'when', 'how', 'why'
            }
        elif category == 'auxiliary_verbs':
            return {
                'am', 'is', 'are', 'was', 'were', 'be', 'being', 'been', 'have', 'has',
                'had', 'having', 'do', 'does', 'did', 'doing', 'get', 'gets', 'got', 'gotten'
            }
        elif category == 'modals':
            return {
                'can', 'could', 'may', 'might', 'must', 'shall', 'should', 'will', 'would',
                'ought', 'need', 'dare'
            }
        elif category == 'quantifiers':
            return {
                'all', 'any', 'both', 'each', 'every', 'few', 'many', 'much', 'most', 'some',
                'several', 'little', 'enough', 'more', 'less', 'no', 'none', 'one', 'two',
                'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'
            }
        else:
            return set()


# Testing function if run directly
if __name__ == "__main__":
    import json
    import sys
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Extract linguistic features from text')
    parser.add_argument('input', help='Input file path or S3 URI (s3://bucket/key)')
    parser.add_argument('--output', help='Output file path or S3 URI (s3://bucket/key)')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with simplified processing')
    parser.add_argument('--memory-limit', type=int, default=0, help='Memory limit in MB (0 for no limit)')
    parser.add_argument('--aws', action='store_true', help='Force AWS mode for S3 operations')
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = LinguisticFeaturesExtractor(test_mode=args.test_mode, memory_limit=args.memory_limit)
    
    try:
        # Check if input is an S3 URI
        if args.input.startswith('s3://') and (AWS_AVAILABLE or args.aws):
            # Parse S3 URI
            s3_path = args.input[5:]  # Remove "s3://"
            bucket, key = s3_path.split('/', 1)
            
            print(f"Extracting features from S3: s3://{bucket}/{key}")
            features = extractor.extract_features_from_s3(bucket, key)
            
            # Determine output path
            if args.output:
                if args.output.startswith('s3://'):
                    # Parse S3 output URI
                    output_s3_path = args.output[5:]  # Remove "s3://"
                    output_bucket, output_key = output_s3_path.split('/', 1)
                    
                    # Save to S3
                    s3_uri = extractor.save_features_to_s3(features, output_bucket, output_key)
                    print(f"Saved features to {s3_uri}")
                else:
                    # Save to local file
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(features, f, indent=2, ensure_ascii=False)
                    print(f"Saved features to {args.output}")
            else:
                # Default output path
                output_key = key.rsplit('.', 1)[0] + '_features.json'
                s3_uri = extractor.save_features_to_s3(features, bucket, output_key)
                print(f"Saved features to {s3_uri}")
                
                # Print some key features
                print("\nKey Linguistic Features:")
                if "type_token_ratio" in features:
                    print(f"  Lexical Diversity (Type-Token Ratio): {features['type_token_ratio']:.4f}")
                if "flesch_reading_ease" in features:
                    print(f"  Flesch Reading Ease: {features['flesch_reading_ease']:.2f}")
                if "avg_sentence_length" in features:
                    print(f"  Average Sentence Length: {features['avg_sentence_length']:.2f} words")
        
        # Check if input is a JSON file
        elif args.input.endswith('.json'):
            with open(args.input, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            # Extract features for full text
            print(f"Extracting features from JSON document: {args.input}")
            document_data["linguistic_features"] = extractor.extract_features(
                document_data["content"]["full_text"]
            )
            
            # Extract features for segments if available
            if "segments" in document_data.get("bert_friendly", {}):
                print(f"Processing {len(document_data['bert_friendly']['segments'])} segments")
                document_data["bert_friendly"]["segments"] = extractor.extract_segment_features(
                    document_data["bert_friendly"]["segments"]
                )
            
            # Save updated document data
            output_path = args.output if args.output else args.input
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully extracted linguistic features and updated {output_path}")
        
        # Input is a plain text file
        else:
            with open(args.input, 'r', encoding='utf-8') as f:
                text = f.read()
            
            print(f"Extracting features from text file: {args.input}")
            features = extractor.extract_features(text)
            
            # Save features to JSON
            output_path = args.output if args.output else args.input + "_features.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(features, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully extracted linguistic features and saved to {output_path}")
            
            # Print some key features
            print("\nKey Linguistic Features:")
            if "type_token_ratio" in features:
                print(f"  Lexical Diversity (Type-Token Ratio): {features['type_token_ratio']:.4f}")
            if "flesch_reading_ease" in features:
                print(f"  Flesch Reading Ease: {features['flesch_reading_ease']:.2f}")
            if "avg_sentence_length" in features:
                print(f"  Average Sentence Length: {features['avg_sentence_length']:.2f} words")
            if "grouped_pos" in features and "noun_ratio" in features["grouped_pos"]:
                print(f"  Noun Ratio: {features['grouped_pos']['noun_ratio']:.4f}")
                print(f"  Verb Ratio: {features['grouped_pos']['verb_ratio']:.4f}")
            if "sentiment_polarity" in features:
                print(f"  Sentiment Polarity: {features['sentiment_polarity']:.4f}")
    
    except Exception as e:
        print(f"Error extracting linguistic features: {e}")
        sys.exit(1)

# AWS Lambda handler
def lambda_handler(event, context):
    """
    AWS Lambda handler for linguistic feature extraction
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    # Configure logging for Lambda
    if ENV_AWS_LAMBDA:
        logger.setLevel(logging.INFO)
    
    # Log event details (excluding large payloads)
    logger.info(f"Processing Lambda event: {json.dumps({k: v for k, v in event.items() if k != 'text'})}")
    
    start_time = time.time()
    
    try:
        # Initialize extractor
        test_mode = event.get('test_mode', ENV_TEST_MODE)
        memory_limit = int(event.get('memory_limit', ENV_MEMORY_LIMIT))
        extractor = LinguisticFeaturesExtractor(test_mode=test_mode, memory_limit=memory_limit)
        
        # Extract features based on input type
        if 'text' in event:
            # Direct text input
            features = extractor.extract_features(event['text'])
            response_body = features
            
        elif 's3_bucket' in event and 's3_key' in event:
            # S3 input
            features = extractor.extract_features_from_s3(event['s3_bucket'], event['s3_key'])
            
            # Save to S3 if output path specified
            if 'output_s3_key' in event:
                s3_uri = extractor.save_features_to_s3(
                    features, 
                    event.get('output_s3_bucket', event['s3_bucket']),
                    event['output_s3_key']
                )
                response_body = {
                    'features': features,
                    'output_uri': s3_uri
                }
            else:
                response_body = features
                
        elif 'document_data' in event:
            # JSON document data
            document_data = event['document_data']
            
            # Extract features for full text
            document_data["linguistic_features"] = extractor.extract_features(
                document_data["content"]["full_text"]
            )
            
            # Extract features for segments if available
            if "segments" in document_data.get("bert_friendly", {}):
                document_data["bert_friendly"]["segments"] = extractor.extract_segment_features(
                    document_data["bert_friendly"]["segments"]
                )
            
            response_body = document_data
        
        else:
            # Invalid input
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid input. Must provide text, S3 path, or document_data.'
                })
            }
        
        # Add processing metadata
        processing_time = time.time() - start_time
        if "processing_metadata" not in response_body:
            response_body["processing_metadata"] = {}
        
        response_body["processing_metadata"].update({
            'lambda_processing_time': processing_time,
            'aws_request_id': context.aws_request_id if context else None,
            'timestamp': time.time()
        })
        
        # Report metrics
        if metrics:
            try:
                metrics['put_metric']('LambdaProcessingTime', processing_time, 'Seconds')
                metrics['put_metric']('LambdaInvocations', 1, 'Count')
            except Exception as e:
                logger.warning(f"Failed to report Lambda metrics: {e}")
        
        # Return success
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, default=str)
        }
    
    except Exception as e:
        # Log error
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        
        # Report error metric
        if metrics:
            try:
                metrics['put_metric']('LambdaErrors', 1, 'Count')
            except Exception:
                pass
        
        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'processing_metadata': {
                    'error': True,
                    'lambda_processing_time': time.time() - start_time,
                    'aws_request_id': context.aws_request_id if context else None,
                    'timestamp': time.time()
                }
            })
        }
