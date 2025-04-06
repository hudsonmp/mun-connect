import torch
import numpy as np
from typing import Dict, List, Any, Optional
import os
import json
import re
import datetime
import logging
import boto3
from botocore.exceptions import ClientError
import tempfile

from style_analyzer_core import StyleAnalyzer
from country_position_analyzer import CountryPositionAnalyzer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENV_S3_BUCKET = os.environ.get("DELEGATE_ANALYZER_S3_BUCKET")
ENV_S3_REGION = os.environ.get("DELEGATE_ANALYZER_S3_REGION", "us-east-1")
ENV_MODEL_PATH = os.environ.get("DELEGATE_ANALYZER_MODEL_PATH")
ENV_COUNTRY_DB_PATH = os.environ.get("DELEGATE_ANALYZER_COUNTRY_DB_PATH")
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_STORAGE_MODE = os.environ.get("STORAGE_MODE", "local").lower()  # "local" or "s3"
ENV_USE_CPU_ONLY = os.environ.get("USE_CPU_ONLY", "false").lower() == "true"

# Check if running in Lambda/container environment
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
IS_CONTAINER = os.environ.get("ECS_CONTAINER_METADATA_URI") is not None
IS_AWS_ENV = IS_LAMBDA or IS_CONTAINER

# Maximum retries for AWS operations
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Singleton instance for AWS environments
_instance = None

class DelegateAnalyzer:
    """
    Comprehensive analyzer for Model UN delegates that combines
    style analysis with country position comparison.
    
    This analyzer focuses on evaluating how well delegates stay on policy
    regardless of the specific country they represent.
    """
    
    def __init__(self, country_db_path: Optional[str] = None):
        """
        Initialize delegate analyzer
        
        Args:
            country_db_path: Optional path to country position database
        """
        logger.info("Initializing Delegate Analyzer...")
        
        # Set device configuration
        self.device = "cuda" if torch.cuda.is_available() and not ENV_USE_CPU_ONLY else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Store analyzers as lazy-loaded properties
        self._style_analyzer = None
        self._position_analyzer = None
        
        # Store country_db_path for lazy loading
        self.country_db_path = country_db_path or ENV_COUNTRY_DB_PATH
        
        # S3 handler for AWS environments
        self.s3_handler = None
        if IS_AWS_ENV and ENV_STORAGE_MODE == "s3":
            self._init_s3_handler()
        
        logger.info("Delegate Analyzer initialization complete")
    
    def _init_s3_handler(self):
        """Initialize S3 handler for AWS environments"""
        if not ENV_S3_BUCKET:
            raise ValueError("S3 bucket name must be provided through DELEGATE_ANALYZER_S3_BUCKET environment variable")
        
        logger.info(f"Initializing S3 handler with bucket: {ENV_S3_BUCKET}")
        
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_handler = boto3.client('s3', region_name=ENV_S3_REGION)
                # Verify IAM permissions by checking if we can list the bucket
                self.s3_handler.head_bucket(Bucket=ENV_S3_BUCKET)
                logger.info(f"Successfully connected to S3 bucket: {ENV_S3_BUCKET}")
                return
            except (ClientError, Exception) as e:
                if isinstance(e, ClientError) and e.response['Error']['Code'] == '403':
                    logger.error(f"Permission denied to access S3 bucket: {ENV_S3_BUCKET}")
                    raise
                elif attempt < MAX_RETRIES - 1:
                    logger.warning(f"Failed to initialize S3 client (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    import time
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to initialize S3 client after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    @property
    def style_analyzer(self):
        """Lazy-loaded style analyzer"""
        if self._style_analyzer is None:
            logger.info("Lazy-loading StyleAnalyzer")
            self._style_analyzer = StyleAnalyzer()
        return self._style_analyzer
    
    @property
    def position_analyzer(self):
        """Lazy-loaded position analyzer"""
        if self._position_analyzer is None:
            logger.info("Lazy-loading CountryPositionAnalyzer")
            
            # If in S3 mode and country_db_path is an S3 path
            if self.s3_handler and self.country_db_path and self.country_db_path.startswith("s3://"):
                local_path = self._download_from_s3(self.country_db_path)
                self._position_analyzer = CountryPositionAnalyzer(local_path)
            else:
                self._position_analyzer = CountryPositionAnalyzer(self.country_db_path)
                
        return self._position_analyzer
    
    def _download_from_s3(self, s3_path: str) -> str:
        """Download a file from S3 to local temp directory"""
        if not s3_path.startswith("s3://"):
            return s3_path
            
        # Parse S3 path
        parts = s3_path[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        # Create temp directory if needed
        temp_dir = tempfile.gettempdir()
        local_filename = os.path.join(temp_dir, os.path.basename(key))
        
        logger.info(f"Downloading {s3_path} to {local_filename}")
        
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_handler.download_file(bucket, key, local_filename)
                logger.info(f"Successfully downloaded {s3_path}")
                return local_filename
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error downloading file from S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    import time
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error downloading file from S3 after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def analyze_document(self, text: str, country: str, committee: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a delegate document with focus on country position alignment
        
        Args:
            text: Document text
            country: Country the delegate is representing
            committee: Optional committee context
            
        Returns:
            Dictionary with comprehensive analysis
        """
        logger.info(f"Analyzing document for {country}...")
        
        # Run style analysis
        style_analysis = self.style_analyzer.analyze_style(text, country, committee)
        
        # Run position analysis
        position_analysis = self.position_analyzer.analyze_position_alignment(text, country)
        
        # Integrate analyses
        integrated_analysis = self._integrate_analyses(style_analysis, position_analysis, country, committee)
        
        # Save results to S3 if configured
        if self.s3_handler and ENV_STORAGE_MODE == "s3":
            self._save_analysis_to_s3(integrated_analysis, country, committee)
        
        return integrated_analysis
    
    def _save_analysis_to_s3(self, analysis: Dict[str, Any], country: str, committee: Optional[str] = None) -> str:
        """Save analysis results to S3 and return the key"""
        if not self.s3_handler:
            return None
            
        # Generate a unique key for the analysis
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        country_safe = re.sub(r'[^\w]', '_', country)
        committee_safe = re.sub(r'[^\w]', '_', committee) if committee else "no_committee"
        
        s3_key = f"analyses/{country_safe}/{committee_safe}/{timestamp}.json"
        
        # Convert analysis to JSON
        analysis_json = json.dumps(analysis)
        
        logger.info(f"Saving analysis to S3: {s3_key}")
        
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_handler.put_object(
                    Bucket=ENV_S3_BUCKET,
                    Key=s3_key,
                    Body=analysis_json,
                    ContentType="application/json"
                )
                logger.info(f"Successfully saved analysis to S3: {s3_key}")
                return s3_key
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error saving analysis to S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    import time
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error saving analysis to S3 after {MAX_RETRIES} attempts: {str(e)}")
                    return None
    
    def analyze_multiple_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze multiple delegate documents to identify patterns
        
        Args:
            documents: List of dictionaries with document text, country, and committee
            
        Returns:
            Dictionary with cross-document analysis
        """
        logger.info(f"Analyzing {len(documents)} documents...")
        
        # Analyze each document
        document_analyses = []
        
        for doc in documents:
            text = doc.get("text", "")
            country = doc.get("country", "")
            committee = doc.get("committee", None)
            doc_id = doc.get("id", f"doc_{len(document_analyses)}")
            
            # Check if document is an S3 path and needs to be downloaded
            if text.startswith("s3://") and self.s3_handler:
                try:
                    text = self._get_document_from_s3(text)
                except Exception as e:
                    logger.error(f"Error downloading document from S3: {str(e)}")
                    continue
            
            if text and country:
                try:
                    analysis = self.analyze_document(text, country, committee)
                    document_analyses.append({
                        "id": doc_id,
                        "country": country,
                        "committee": committee,
                        "analysis": analysis
                    })
                except Exception as e:
                    logger.error(f"Error analyzing document {doc_id}: {str(e)}")
        
        # Compare analyses across documents
        comparison = self._compare_analyses(document_analyses)
        
        # Generate delegate profile
        profile = self._generate_delegate_profile(document_analyses, comparison)
        
        # Save multi-document analysis to S3 if configured
        result = {
            "document_analyses": document_analyses,
            "comparison": comparison,
            "delegate_profile": profile,
            "analysis_timestamp": str(datetime.datetime.now())
        }
        
        if self.s3_handler and ENV_STORAGE_MODE == "s3":
            self._save_multi_analysis_to_s3(result)
        
        return result
    
    def _get_document_from_s3(self, s3_path: str) -> str:
        """Get document text from S3"""
        if not s3_path.startswith("s3://"):
            return s3_path
            
        # Parse S3 path
        parts = s3_path[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        logger.info(f"Downloading document from S3: {s3_path}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.s3_handler.get_object(Bucket=bucket, Key=key)
                return response['Body'].read().decode('utf-8')
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error downloading document from S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    import time
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error downloading document from S3 after {MAX_RETRIES} attempts: {str(e)}")
                    raise
    
    def _save_multi_analysis_to_s3(self, analysis: Dict[str, Any]) -> str:
        """Save multi-document analysis results to S3 and return the key"""
        if not self.s3_handler:
            return None
            
        # Generate a unique key for the analysis
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        s3_key = f"analyses/multi/{timestamp}.json"
        
        # Convert analysis to JSON
        analysis_json = json.dumps(analysis)
        
        logger.info(f"Saving multi-document analysis to S3: {s3_key}")
        
        for attempt in range(MAX_RETRIES):
            try:
                self.s3_handler.put_object(
                    Bucket=ENV_S3_BUCKET,
                    Key=s3_key,
                    Body=analysis_json,
                    ContentType="application/json"
                )
                logger.info(f"Successfully saved multi-document analysis to S3: {s3_key}")
                return s3_key
            except ClientError as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Error saving multi-document analysis to S3 (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    import time
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Error saving multi-document analysis to S3 after {MAX_RETRIES} attempts: {str(e)}")
                    return None
    
    def _integrate_analyses(self, style_analysis: Dict[str, Any], position_analysis: Dict[str, Any], 
                           country: str, committee: Optional[str] = None) -> Dict[str, Any]:
        """
        Integrate style and position analyses
        
        Args:
            style_analysis: Results of style analysis
            position_analysis: Results of position analysis
            country: Country being represented
            committee: Optional committee context
            
        Returns:
            Dictionary with integrated analysis
        """
        # Extract key metrics from each analysis
        linguistic_patterns = style_analysis.get("linguisticPatterns", {})
        cognitive_frameworks = style_analysis.get("cognitiveFrameworks", {})
        argumentative_strategies = style_analysis.get("argumentativeStrategies", {})
        
        stance_analysis = position_analysis.get("stance_analysis", {})
        linguistic_alignment = position_analysis.get("linguistic_analysis", {})
        position_deviations = position_analysis.get("position_deviations", [])
        
        # Calculate overall policy alignment score
        style_factors = {
            "vocabulary_appropriateness": linguistic_patterns.get("vocabulary", {}).get("formality", {}).get("score", 0.5) / 10,
            "reasoning_approach": cognitive_frameworks.get("reasoningPatterns", {}).get("dominant_reasoning", "unknown") != "unknown",
            "persuasive_techniques": argumentative_strategies.get("persuasiveTechniques", {}).get("dominant_appeal", "unknown") != "unknown"
        }
        
        style_score = sum(style_factors.values()) / len(style_factors) if style_factors else 0.5
        
        # Get position alignment scores
        position_score = position_analysis.get("overall_alignment", 0.5)
        
        # Calculate integrated alignment score
        integrated_alignment_score = (style_score * 0.4) + (position_score * 0.6)
        
        # Identify key strengths and weaknesses
        strengths = []
        weaknesses = []
        
        # Style strengths/weaknesses
        if style_score > 0.7:
            strengths.append("Strong and appropriate writing style")
        elif style_score < 0.5:
            weaknesses.append("Writing style needs improvement")
        
        # Position strengths/weaknesses
        if position_score > 0.7:
            strengths.append("Excellent alignment with expected country positions")
        elif position_score < 0.5:
            weaknesses.append("Better alignment with country positions needed")
        
        # Add specific strengths/weaknesses
        assessment = position_analysis.get("assessment", {})
        strengths.extend(assessment.get("strengths", [])[:2])  # Limit to top 2
        weaknesses.extend(assessment.get("areas_for_improvement", [])[:2])  # Limit to top 2
        
        # Generate integrated assessment
        integrated_assessment = self._generate_integrated_assessment(
            integrated_alignment_score,
            style_score,
            position_score,
            strengths,
            weaknesses,
            style_analysis,
            position_analysis
        )
        
        return {
            "country": country,
            "committee": committee,
            "style_analysis": {
                "key_metrics": {
                    "vocabulary": linguistic_patterns.get("vocabulary", {}).get("diversity", {}),
                    "sentence_structure": linguistic_patterns.get("sentenceStructure", {}).get("sentence_metrics", {}),
                    "rhetorical_devices": linguistic_patterns.get("stylisticDevices", {}).get("rhetorical_devices", {}).get("counts", {}),
                    "reasoning_patterns": cognitive_frameworks.get("reasoningPatterns", {}).get("reasoning_approaches", {})
                }
            },
            "position_analysis": {
                "key_metrics": {
                    "stance_alignment": stance_analysis.get("overall_stance_alignment", 0.0),
                    "linguistic_alignment": linguistic_alignment.get("language_alignment_score", 0.0),
                    "deviation_count": len(position_deviations)
                },
                "position_deviations": position_deviations[:3]  # Limit to top 3
            },
            "integrated_metrics": {
                "style_score": style_score,
                "position_score": position_score,
                "integrated_alignment_score": integrated_alignment_score,
                "alignment_level": "excellent" if integrated_alignment_score > 0.8 else
                                  "good" if integrated_alignment_score > 0.6 else
                                  "adequate" if integrated_alignment_score > 0.4 else
                                  "needs_improvement"
            },
            "assessment": integrated_assessment,
            "full_style_analysis": style_analysis,
            "full_position_analysis": position_analysis
        }
    
    def _generate_integrated_assessment(self, integrated_score, style_score, position_score, 
                                      strengths, weaknesses, style_analysis, position_analysis):
        """
        Generate integrated assessment of delegate's performance
        
        Args:
            integrated_score: Overall integrated score
            style_score: Style score
            position_score: Position score
            strengths: List of identified strengths
            weaknesses: List of identified weaknesses
            style_analysis: Complete style analysis
            position_analysis: Complete position analysis
            
        Returns:
            Dictionary with integrated assessment
        """
        # Determine overall level
        if integrated_score > 0.8:
            level = "excellent"
            summary = "Excellent representation of country with strong alignment between style and expected positions"
        elif integrated_score > 0.6:
            level = "good"
            summary = "Good representation of country with solid alignment between style and expected positions"
        elif integrated_score > 0.4:
            level = "adequate"
            summary = "Adequate representation of country with some alignment between style and expected positions"
        else:
            level = "needs_improvement"
            summary = "Needs improvement in representing country with better alignment between style and expected positions"
        
        # Get specific recommendations
        position_recommendations = position_analysis.get("assessment", {}).get("specific_recommendations", [])
        
        # Add style recommendations
        style_recommendations = []
        
        if style_score < 0.7:
            linguistic_patterns = style_analysis.get("linguisticPatterns", {})
            vocabulary = linguistic_patterns.get("vocabulary", {})
            
            if vocabulary.get("formality", {}).get("score", 0.5) < 0.6:
                style_recommendations.append("Increase formality level to match diplomatic context")
            
            sentence_structure = linguistic_patterns.get("sentenceStructure", {})
            if sentence_structure.get("sentence_metrics", {}).get("length", {}).get("average", 15) < 10:
                style_recommendations.append("Use more complex sentence structures")
            
            stylistic_devices = linguistic_patterns.get("stylisticDevices", {})
            if stylistic_devices.get("rhetorical_devices", {}).get("counts", {}).get("total", 0) < 5:
                style_recommendations.append("Incorporate more rhetorical devices")
        
        # Combine recommendations
        all_recommendations = position_recommendations + style_recommendations
        
        # Prioritize recommendations (limit to 5)
        prioritized_recommendations = all_recommendations[:5]
        
        return {
            "level": level,
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": prioritized_recommendations
        }
    
    def _compare_analyses(self, document_analyses):
        """
        Compare analyses across multiple documents
        
        Args:
            document_analyses: List of document analysis results
            
        Returns:
            Dictionary with comparison results
        """
        # Group analyses by country
        country_groups = {}
        
        for analysis in document_analyses:
            country = analysis.get("country", "")
            
            if country not in country_groups:
                country_groups[country] = []
            
            country_groups[country].append(analysis)
        
        # Calculate metrics by country
        country_metrics = {}
        
        for country, analyses in country_groups.items():
            # Extract alignment scores
            alignment_scores = [
                a.get("analysis", {}).get("integrated_metrics", {}).get("integrated_alignment_score", 0)
                for a in analyses
            ]
            
            # Calculate average and consistency
            avg_alignment = sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0
            consistency = 1.0 - (max(alignment_scores) - min(alignment_scores)) if len(alignment_scores) > 1 else 1.0
            
            country_metrics[country] = {
                "average_alignment": avg_alignment,
                "consistency": consistency,
                "document_count": len(analyses),
                "alignment_scores": alignment_scores
            }
        
        # Calculate cross-country consistency
        if len(country_metrics) > 1:
            avg_alignments = [metrics["average_alignment"] for country, metrics in country_metrics.items()]
            cross_country_consistency = 1.0 - (max(avg_alignments) - min(avg_alignments))
        else:
            cross_country_consistency = 1.0  # Perfect consistency with only one country
        
        # Calculate strongest and weakest countries
        if country_metrics:
            strongest_country = max(country_metrics.items(), key=lambda x: x[1]["average_alignment"])[0]
            weakest_country = min(country_metrics.items(), key=lambda x: x[1]["average_alignment"])[0]
        else:
            strongest_country = None
            weakest_country = None
        
        # Generate assessment
        consistency_level = "excellent" if cross_country_consistency > 0.8 else \
                          "good" if cross_country_consistency > 0.6 else \
                          "moderate" if cross_country_consistency > 0.4 else \
                          "low"
        
        assessment = f"The delegate shows {consistency_level} consistency across different country representations."
        
        if strongest_country and weakest_country and strongest_country != weakest_country:
            assessment += f" Strongest representation: {strongest_country}. Could improve representation of: {weakest_country}."
        
        return {
            "country_metrics": country_metrics,
            "cross_country_consistency": cross_country_consistency,
            "consistency_level": consistency_level,
            "strongest_country": strongest_country,
            "weakest_country": weakest_country,
            "assessment": assessment
        }
    
    def _generate_delegate_profile(self, document_analyses, comparison):
        """
        Generate comprehensive delegate profile
        
        Args:
            document_analyses: List of document analysis results
            comparison: Results of cross-document comparison
            
        Returns:
            Dictionary with delegate profile
        """
        # Extract key metrics across documents
        style_metrics = []
        position_metrics = []
        
        for doc in document_analyses:
            analysis = doc.get("analysis", {})
            
            # Extract style score
            style_score = analysis.get("integrated_metrics", {}).get("style_score", 0)
            style_metrics.append(style_score)
            
            # Extract position score
            position_score = analysis.get("integrated_metrics", {}).get("position_score", 0)
            position_metrics.append(position_score)
        
        # Calculate average metrics
        avg_style = sum(style_metrics) / len(style_metrics) if style_metrics else 0
        avg_position = sum(position_metrics) / len(position_metrics) if position_metrics else 0
        
        # Calculate consistency
        style_consistency = 1.0 - (max(style_metrics) - min(style_metrics)) if len(style_metrics) > 1 else 1.0
        position_consistency = 1.0 - (max(position_metrics) - min(position_metrics)) if len(position_metrics) > 1 else 1.0
        
        # Extract recurring patterns
        recurring_patterns = self._identify_recurring_patterns(document_analyses)
        
        # Generate characteristic profile
        profile_level = "excellent" if avg_style > 0.8 and avg_position > 0.8 else \
                      "strong" if avg_style > 0.7 and avg_position > 0.7 else \
                      "good" if avg_style > 0.6 and avg_position > 0.6 else \
                      "developing"
        
        # Generate highlights and areas for development
        highlights = []
        development_areas = []
        
        if avg_style > 0.7:
            highlights.append("Strong writing style with effective rhetorical techniques")
        else:
            development_areas.append("Further develop writing style and rhetorical techniques")
        
        if avg_position > 0.7:
            highlights.append("Excellent alignment with expected country positions")
        else:
            development_areas.append("Improve alignment with expected country positions")
        
        if comparison.get("cross_country_consistency", 0) > 0.7 and len(comparison.get("country_metrics", {})) > 1:
            highlights.append("Consistent quality across different country representations")
        elif len(comparison.get("country_metrics", {})) > 1:
            development_areas.append("Develop more consistent approach across different countries")
        
        # Add recurring patterns to highlights
        for pattern in recurring_patterns[:2]:
            highlights.append(pattern)
        
        return {
            "profile_level": profile_level,
            "metrics": {
                "average_style_score": avg_style,
                "average_position_score": avg_position,
                "style_consistency": style_consistency,
                "position_consistency": position_consistency,
                "cross_country_consistency": comparison.get("cross_country_consistency", 1.0)
            },
            "highlights": highlights,
            "areas_for_development": development_areas,
            "recurring_patterns": recurring_patterns,
            "strongest_country": comparison.get("strongest_country", None),
            "profile_summary": f"{profile_level.capitalize()} delegate with {comparison.get('consistency_level', 'good')} consistency across representations"
        }
    
    def _identify_recurring_patterns(self, document_analyses):
        """
        Identify recurring patterns across documents
        
        Args:
            document_analyses: List of document analysis results
            
        Returns:
            List of recurring patterns
        """
        # Count patterns across documents
        reasoning_patterns = {}
        persuasive_approaches = {}
        rhetorical_devices = {}
        
        for doc in document_analyses:
            analysis = doc.get("analysis", {})
            
            # Extract reasoning pattern
            full_style = analysis.get("full_style_analysis", {})
            cognitive = full_style.get("cognitiveFrameworks", {})
            reasoning = cognitive.get("reasoningPatterns", {})
            
            dominant_reasoning = reasoning.get("dominant_reasoning", "unknown")
            if dominant_reasoning != "unknown":
                reasoning_patterns[dominant_reasoning] = reasoning_patterns.get(dominant_reasoning, 0) + 1
            
            # Extract persuasive approach
            argumentative = full_style.get("argumentativeStrategies", {})
            persuasive = argumentative.get("persuasiveTechniques", {})
            
            dominant_appeal = persuasive.get("dominant_appeal", "unknown")
            if dominant_appeal != "unknown":
                persuasive_approaches[dominant_appeal] = persuasive_approaches.get(dominant_appeal, 0) + 1
            
            # Extract rhetorical devices
            linguistic = full_style.get("linguisticPatterns", {})
            stylistic = linguistic.get("stylisticDevices", {})
            rhetorical = stylistic.get("rhetorical_devices", {}).get("counts", {})
            
            for device, count in rhetorical.items():
                if count > 0:
                    rhetorical_devices[device] = rhetorical_devices.get(device, 0) + 1
        
        # Identify most common patterns
        patterns = []
        
        # Add most common reasoning pattern
        if reasoning_patterns:
            most_common = max(reasoning_patterns.items(), key=lambda x: x[1])
            if most_common[1] > len(document_analyses) / 2:  # Used in majority of documents
                reasoning_desc = {
                    "deductive": "Consistently uses deductive reasoning (general principles to specific conclusions)",
                    "inductive": "Regularly employs inductive reasoning (specific examples to general principles)",
                    "analogical": "Often uses analogical reasoning (drawing parallels between situations)",
                    "causal": "Frequently uses causal reasoning (focus on cause-effect relationships)",
                    "conditional": "Typically uses conditional reasoning (if-then structures)"
                }
                patterns.append(reasoning_desc.get(most_common[0], f"Frequently uses {most_common[0]} reasoning"))
        
        # Add most common persuasive approach
        if persuasive_approaches:
            most_common = max(persuasive_approaches.items(), key=lambda x: x[1])
            if most_common[1] > len(document_analyses) / 2:  # Used in majority of documents
                persuasive_desc = {
                    "logos": "Consistently relies on logical appeals and evidence",
                    "ethos": "Regularly employs ethical appeals and credibility building",
                    "pathos": "Often uses emotional appeals to persuade"
                }
                patterns.append(persuasive_desc.get(most_common[0], f"Frequently uses {most_common[0]} appeals"))
        
        # Add most common rhetorical devices
        if rhetorical_devices:
            most_common = sorted(rhetorical_devices.items(), key=lambda x: x[1], reverse=True)[:3]
            device_types = []
            for device, count in most_common:
                if count > len(document_analyses) / 3:  # Used in at least a third of documents
                    device_types.append(device)
            
            if device_types:
                patterns.append(f"Frequently uses {', '.join(device_types)} in arguments")
        
        # Add more patterns based on document analysis
        formality_scores = []
        for doc in document_analyses:
            analysis = doc.get("analysis", {})
            full_style = analysis.get("full_style_analysis", {})
            linguistic = full_style.get("linguisticPatterns", {})
            vocabulary = linguistic.get("vocabulary", {})
            formality = vocabulary.get("formality", {}).get("score", 0.5)
            formality_scores.append(formality)
        
        if formality_scores:
            avg_formality = sum(formality_scores) / len(formality_scores)
            if avg_formality > 0.7:
                patterns.append("Consistently uses formal diplomatic language")
            elif avg_formality < 0.4:
                patterns.append("Tends to use less formal language than typical for diplomatic contexts")
        
        return patterns

# Factory method for creating or getting singleton instance
def get_analyzer_instance(country_db_path: Optional[str] = None) -> DelegateAnalyzer:
    """
    Factory method to get or create a singleton instance of DelegateAnalyzer.
    This helps with reusing the instance across Lambda invocations.
    
    Args:
        country_db_path: Optional path to country position database
        
    Returns:
        Singleton instance of DelegateAnalyzer
    """
    global _instance
    if _instance is None:
        logger.info("Creating new DelegateAnalyzer instance")
        _instance = DelegateAnalyzer(country_db_path)
    return _instance

# Lambda handler function
def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        Lambda response
    """
    logger.info(f"Received Lambda event: {json.dumps(event)}")
    
    try:
        # Initialize analyzer (uses singleton pattern)
        analyzer = get_analyzer_instance(ENV_COUNTRY_DB_PATH)
        
        # Extract request data
        request_type = event.get('requestType', '').lower()
        
        if request_type == 'analyze_document':
            # Get document text - either directly or from S3
            text = event.get('text', '')
            if not text and 's3Path' in event:
                text = analyzer._get_document_from_s3(event['s3Path'])
                
            country = event.get('country', '')
            committee = event.get('committee', None)
            
            if not text or not country:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing required parameters: text and country'})
                }
            
            # Run analysis
            result = analyzer.analyze_document(text, country, committee)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        elif request_type == 'analyze_multiple_documents':
            documents = event.get('documents', [])
            
            if not documents:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing required parameter: documents'})
                }
            
            # Run analysis
            result = analyzer.analyze_multiple_documents(documents)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid request type: {request_type}'})
            }
            
    except Exception as e:
        logger.error(f"Error processing Lambda event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For Docker container or ECS entry point
def container_handler(request_json):
    """
    Container entry point handler
    
    Args:
        request_json: JSON request data
        
    Returns:
        Analysis results
    """
    try:
        # Initialize analyzer (uses singleton pattern)
        analyzer = get_analyzer_instance(ENV_COUNTRY_DB_PATH)
        
        # Extract request data
        request_type = request_json.get('requestType', '').lower()
        
        if request_type == 'analyze_document':
            # Get document text - either directly or from S3
            text = request_json.get('text', '')
            if not text and 's3Path' in request_json:
                text = analyzer._get_document_from_s3(request_json['s3Path'])
                
            country = request_json.get('country', '')
            committee = request_json.get('committee', None)
            
            if not text or not country:
                return {
                    'status': 'error',
                    'error': 'Missing required parameters: text and country'
                }
            
            # Run analysis
            result = analyzer.analyze_document(text, country, committee)
            
            return {
                'status': 'success',
                'result': result
            }
            
        elif request_type == 'analyze_multiple_documents':
            documents = request_json.get('documents', [])
            
            if not documents:
                return {
                    'status': 'error',
                    'error': 'Missing required parameter: documents'
                }
            
            # Run analysis
            result = analyzer.analyze_multiple_documents(documents)
            
            return {
                'status': 'success',
                'result': result
            }
            
        else:
            return {
                'status': 'error',
                'error': f'Invalid request type: {request_type}'
            }
            
    except Exception as e:
        logger.error(f"Error processing container request: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }
