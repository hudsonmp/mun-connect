import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DelegateProfileError(Exception):
    """Base exception class for DelegateProfile errors."""
    pass

class DatabaseError(DelegateProfileError):
    """Exception raised for database operation errors."""
    pass

class ValidationError(DelegateProfileError):
    """Exception raised for validation errors."""
    pass

class DelegateProfile:
    """
    DelegateProfile handles storage, retrieval, and consolidation of various
    writing style analyses for a Model UN delegate.
    
    This class serves as the interface between individual analysis modules
    and the Supabase database, creating a comprehensive delegate writing profile
    that can be used for AI-generated papers matching the delegate's style.
    """
    
    def __init__(self, user_id: Union[str, uuid.UUID], supabase_client):
        """
        Initialize a delegate profile manager.
        
        Args:
            user_id: The unique identifier for the delegate/user (UUID or string representation)
            supabase_client: Initialized Supabase client for database operations
        """
        # Ensure user_id is properly formatted as string representation of UUID
        try:
            # Convert to string if it's a UUID object
            if isinstance(user_id, uuid.UUID):
                self.user_id = str(user_id)
            else:
                # Validate string is a valid UUID by attempting conversion
                self.user_id = str(uuid.UUID(user_id))
        except ValueError:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            raise ValidationError("user_id must be a valid UUID format")
            
        self.supabase = supabase_client
        logger.info(f"DelegateProfile initialized for user_id: {self.user_id}")
    
    def store_analysis_result(self, document_type: str, json_content: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """
        Store an individual analysis result in the database.
        
        Args:
            document_type: Type of document analyzed (e.g., 'position_paper', 'opening_speech')
            json_content: The analysis result as a JSON-serializable dictionary
            analysis_type: Type of analysis performed (e.g., 'sentiment', 'style', 'comparison')
        
        Returns:
            Dictionary with operation result information
        """
        # Validate inputs
        if not document_type or not analysis_type:
            logger.error(f"Missing required parameters: document_type={document_type}, analysis_type={analysis_type}")
            raise ValidationError("document_type and analysis_type must be provided")
        
        if not isinstance(json_content, dict):
            logger.error(f"Invalid json_content type: {type(json_content)}")
            raise ValidationError("json_content must be a dictionary")
        
        # Prepare data for upsert - let database handle timestamps
        analysis_data = {
            "user_id": self.user_id,
            "document_type": document_type,
            "analysis_type": analysis_type,
            "content": json_content
            # Let the database handle timestamps with DEFAULT now()
        }
        
        try:
            # Check if entry already exists
            response = self.supabase.table('delegate_analyses') \
                .select('id') \
                .eq('user_id', self.user_id) \
                .eq('document_type', document_type) \
                .eq('analysis_type', analysis_type) \
                .execute()
            
            # Log operation details
            logger.info(f"Storing analysis: user_id={self.user_id}, document_type={document_type}, analysis_type={analysis_type}")
            
            if response.data and len(response.data) > 0:
                # Update existing record
                result = self.supabase.table('delegate_analyses') \
                    .update(analysis_data) \
                    .eq('id', response.data[0]['id']) \
                    .execute()
                logger.info(f"Updated existing analysis for document_type={document_type}, analysis_type={analysis_type}")
                return {"operation": "update", "result": result.data}
            else:
                # Insert new record
                result = self.supabase.table('delegate_analyses') \
                    .insert(analysis_data) \
                    .execute()
                logger.info(f"Inserted new analysis for document_type={document_type}, analysis_type={analysis_type}")
                return {"operation": "insert", "result": result.data}
        
        except Exception as e:
            error_msg = f"Database error while storing analysis: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e
    
    def get_all_analysis_results(self) -> List[Dict[str, Any]]:
        """
        Retrieve all analysis results for the user from the database.
        
        Returns:
            List of dictionaries containing all stored analyses
        """
        try:
            logger.info(f"Retrieving all analysis results for user_id: {self.user_id}")
            response = self.supabase.table('delegate_analyses') \
                .select('*') \
                .eq('user_id', self.user_id) \
                .order('created_at', desc=True) \
                .execute()
            
            logger.info(f"Retrieved {len(response.data) if response.data else 0} analysis results")
            return response.data if response.data else []
        
        except Exception as e:
            error_msg = f"Error retrieving analysis results: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e
    
    def get_analysis_by_type(self, analysis_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve all analysis results of a specific type.
        
        Args:
            analysis_type: Type of analysis to retrieve
            
        Returns:
            List of dictionaries containing analyses of the specified type
        """
        try:
            logger.info(f"Retrieving {analysis_type} analyses for user_id: {self.user_id}")
            response = self.supabase.table('delegate_analyses') \
                .select('*') \
                .eq('user_id', self.user_id) \
                .eq('analysis_type', analysis_type) \
                .order('created_at', desc=True) \
                .execute()
            
            logger.info(f"Retrieved {len(response.data) if response.data else 0} {analysis_type} analyses")
            return response.data if response.data else []
        
        except Exception as e:
            error_msg = f"Error retrieving {analysis_type} analysis results: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e
    
    def get_analysis_by_document(self, document_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve all analysis results for a specific document type.
        
        Args:
            document_type: Type of document to retrieve analyses for
            
        Returns:
            List of dictionaries containing analyses for the specified document type
        """
        try:
            logger.info(f"Retrieving analyses for document_type={document_type}, user_id={self.user_id}")
            response = self.supabase.table('delegate_analyses') \
                .select('*') \
                .eq('user_id', self.user_id) \
                .eq('document_type', document_type) \
                .order('created_at', desc=True) \
                .execute()
            
            logger.info(f"Retrieved {len(response.data) if response.data else 0} analyses for {document_type}")
            return response.data if response.data else []
        
        except Exception as e:
            error_msg = f"Error retrieving analyses for {document_type}: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e
    
    def delete_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """
        Delete a specific analysis by ID.
        
        Args:
            analysis_id: ID of the analysis to delete
            
        Returns:
            Dictionary with operation result information
        """
        try:
            logger.info(f"Deleting analysis id={analysis_id} for user_id={self.user_id}")
            result = self.supabase.table('delegate_analyses') \
                .delete() \
                .eq('id', analysis_id) \
                .eq('user_id', self.user_id) \
                .execute()
            
            logger.info(f"Deleted analysis id={analysis_id}")
            return {"operation": "delete", "result": result.data}
        
        except Exception as e:
            error_msg = f"Error deleting analysis {analysis_id}: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e
    
    def generate_consolidated_profile(self) -> Dict[str, Any]:
        """
        Generate a consolidated profile combining all analysis results.
        
        This method aggregates all stored analyses into a comprehensive
        writing style profile that can be used for AI generation tasks.
        
        Returns:
            A consolidated delegate profile as a structured dictionary
        """
        try:
            # Get all analyses
            logger.info(f"Generating consolidated profile for user_id={self.user_id}")
            all_analyses = self.get_all_analysis_results()
            
            if not all_analyses:
                logger.info(f"No analysis data found for user_id={self.user_id}")
                return {
                    "user_id": self.user_id,
                    "has_data": False,
                    "message": "No analysis data found for this user",
                    "created_at": datetime.now().isoformat()
                }
            
            # Initialize profile structure
            profile = {
                "user_id": self.user_id,
                "has_data": True,
                "document_types": {},
                "style_summary": {
                    "linguistic_patterns": {},
                    "cognitive_frameworks": {},
                    "argumentative_strategies": {},
                    "sentiment_profile": {}
                },
                "created_at": datetime.now().isoformat()
            }
            
            # Process and integrate each analysis
            for analysis in all_analyses:
                doc_type = analysis.get("document_type")
                analysis_type = analysis.get("analysis_type")
                content = analysis.get("content", {})
                
                # Initialize document type in profile if not exists
                if doc_type not in profile["document_types"]:
                    profile["document_types"][doc_type] = {
                        "analyses": []
                    }
                
                # Add this analysis to the document type
                profile["document_types"][doc_type]["analyses"].append({
                    "type": analysis_type,
                    "id": analysis.get("id"),
                    "created_at": analysis.get("created_at"),
                    "updated_at": analysis.get("updated_at")
                })
                
                # Integrate analysis content based on analysis type
                self._integrate_analysis_content(profile, analysis_type, content, doc_type)
            
            # Calculate aggregated metrics
            self._calculate_aggregate_metrics(profile)
            
            logger.info(f"Successfully generated consolidated profile for user_id={self.user_id}")
            return profile
            
        except Exception as e:
            error_msg = f"Error generating consolidated profile: {e}"
            logger.error(error_msg)
            raise DelegateProfileError(error_msg) from e
    
    def _integrate_analysis_content(self, profile: Dict[str, Any], analysis_type: str, 
                                   content: Dict[str, Any], doc_type: str):
        """
        Integrate specific analysis content into the consolidated profile.
        
        Args:
            profile: The profile being constructed
            analysis_type: Type of analysis being integrated
            content: The analysis content to integrate
            doc_type: The document type this analysis is for
        """
        # Handle different analysis types differently
        if analysis_type == "style":
            # Extract style elements
            linguistic = content.get("linguisticPatterns", {})
            cognitive = content.get("cognitiveFrameworks", {})
            argumentative = content.get("argumentativeStrategies", {})
            
            # Add to document type specific profile
            if "style_profile" not in profile["document_types"][doc_type]:
                profile["document_types"][doc_type]["style_profile"] = {}
            
            profile["document_types"][doc_type]["style_profile"] = {
                "linguistic_patterns": linguistic,
                "cognitive_frameworks": cognitive,
                "argumentative_strategies": argumentative
            }
            
            # Contribute to overall style summary
            self._merge_dict(profile["style_summary"]["linguistic_patterns"], linguistic)
            self._merge_dict(profile["style_summary"]["cognitive_frameworks"], cognitive)
            self._merge_dict(profile["style_summary"]["argumentative_strategies"], argumentative)
        
        elif analysis_type == "sentiment":
            # Extract sentiment data
            sentiment = content.get("sentiment", {})
            
            # Add to document type specific profile
            if "sentiment_profile" not in profile["document_types"][doc_type]:
                profile["document_types"][doc_type]["sentiment_profile"] = {}
            
            profile["document_types"][doc_type]["sentiment_profile"] = sentiment
            
            # Contribute to overall sentiment summary
            self._merge_dict(profile["style_summary"]["sentiment_profile"], sentiment)
        
        elif analysis_type == "comparison":
            # Store comparison data specifically for this document type
            if "comparison_profile" not in profile["document_types"][doc_type]:
                profile["document_types"][doc_type]["comparison_profile"] = {}
            
            profile["document_types"][doc_type]["comparison_profile"] = content
            
            # Add a comparison_findings section to the overall profile if not exists
            if "comparison_findings" not in profile:
                profile["comparison_findings"] = {}
            
            # Extract relevant comparison metrics
            approach_scores = content.get("similarity_scores", {})
            if approach_scores:
                # Store document's approach profiles
                profile["comparison_findings"][doc_type] = approach_scores
        
        # Generic handler for other analysis types
        else:
            if analysis_type not in profile["document_types"][doc_type]:
                profile["document_types"][doc_type][analysis_type] = {}
            
            profile["document_types"][doc_type][analysis_type] = content
    
    def _calculate_aggregate_metrics(self, profile: Dict[str, Any]):
        """
        Calculate aggregate metrics across all analyses.
        
        Args:
            profile: The profile being constructed
        """
        # Add overall writing style characteristics
        profile["overall_characteristics"] = {
            "formality_level": self._calculate_formality(profile),
            "complexity_level": self._calculate_complexity(profile),
            "persuasion_style": self._determine_persuasion_style(profile),
            "reasoning_approach": self._determine_reasoning_approach(profile),
            "dominant_sentiment": self._determine_dominant_sentiment(profile)
        }
        
        # Calculate writing fingerprint - a compact representation of style
        profile["writing_fingerprint"] = self._generate_writing_fingerprint(profile)
    
    def _calculate_formality(self, profile: Dict[str, Any]) -> str:
        """Calculate overall formality level based on linguistic patterns."""
        # Simplified implementation - would be more sophisticated in production
        linguistic = profile["style_summary"]["linguistic_patterns"]
        
        # Default to medium if no data
        if not linguistic:
            return "medium"
        
        vocabulary = linguistic.get("vocabulary", {})
        formality = vocabulary.get("formality", {})
        
        score = formality.get("score", 0.5)
        
        if score > 0.7:
            return "high"
        elif score > 0.4:
            return "medium"
        else:
            return "low"
    
    def _calculate_complexity(self, profile: Dict[str, Any]) -> str:
        """Calculate overall complexity level based on sentence structure."""
        # Simplified implementation - would be more sophisticated in production
        linguistic = profile["style_summary"]["linguistic_patterns"]
        
        if not linguistic:
            return "medium"
        
        sentence_structure = linguistic.get("sentenceStructure", {})
        metrics = sentence_structure.get("sentence_metrics", {})
        
        avg_length = metrics.get("length", {}).get("average", 15)
        
        if avg_length > 20:
            return "high"
        elif avg_length > 12:
            return "medium"
        else:
            return "low"
    
    def _determine_persuasion_style(self, profile: Dict[str, Any]) -> str:
        """Determine dominant persuasion style from argumentative strategies."""
        argumentative = profile["style_summary"]["argumentative_strategies"]
        
        if not argumentative:
            return "balanced"
        
        techniques = argumentative.get("persuasiveTechniques", {})
        dominant = techniques.get("dominant_appeal", "balanced")
        
        return dominant
    
    def _determine_reasoning_approach(self, profile: Dict[str, Any]) -> str:
        """Determine dominant reasoning approach from cognitive frameworks."""
        cognitive = profile["style_summary"]["cognitive_frameworks"]
        
        if not cognitive:
            return "balanced"
        
        reasoning = cognitive.get("reasoningPatterns", {})
        dominant = reasoning.get("dominant_reasoning", "balanced")
        
        return dominant
    
    def _determine_dominant_sentiment(self, profile: Dict[str, Any]) -> str:
        """Determine dominant sentiment from sentiment analysis."""
        sentiment = profile["style_summary"]["sentiment_profile"]
        
        if not sentiment:
            return "neutral"
        
        compound = sentiment.get("compound", 0)
        
        if compound > 0.25:
            return "positive"
        elif compound < -0.25:
            return "negative"
        else:
            return "neutral"
    
    def _generate_writing_fingerprint(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a compact representation of the delegate's writing style.
        
        This is a simplified version - a production system would use more 
        sophisticated methods like embedding vectors.
        """
        characteristics = profile["overall_characteristics"]
        
        fingerprint = {
            "style_vector": {
                "formality": self._formality_to_numeric(characteristics["formality_level"]),
                "complexity": self._complexity_to_numeric(characteristics["complexity_level"]),
                "logical_reasoning": 1 if characteristics["reasoning_approach"] == "logical" else 0.5,
                "emotional_appeal": 1 if characteristics["persuasion_style"] == "emotional" else 0.5,
                "sentiment_polarity": self._sentiment_to_numeric(characteristics["dominant_sentiment"])
            },
            "signature_patterns": [
                f"{characteristics['formality_level']} formality",
                f"{characteristics['complexity_level']} complexity",
                f"{characteristics['reasoning_approach']} reasoning",
                f"{characteristics['persuasion_style']} persuasion",
                f"{characteristics['dominant_sentiment']} sentiment"
            ]
        }
        
        return fingerprint
    
    def _formality_to_numeric(self, formality: str) -> float:
        """Convert formality level to numeric value."""
        mapping = {"low": 0.0, "medium": 0.5, "high": 1.0}
        return mapping.get(formality, 0.5)
    
    def _complexity_to_numeric(self, complexity: str) -> float:
        """Convert complexity level to numeric value."""
        mapping = {"low": 0.0, "medium": 0.5, "high": 1.0}
        return mapping.get(complexity, 0.5)
    
    def _sentiment_to_numeric(self, sentiment: str) -> float:
        """Convert sentiment to numeric value."""
        mapping = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}
        return mapping.get(sentiment, 0.0)
    
    def _merge_dict(self, target: Dict[str, Any], source: Dict[str, Any]):
        """
        Merge source dictionary into target dictionary.
        
        This is a simplified implementation that may need customization 
        depending on the exact structure of the analysis results.
        """
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], dict) and isinstance(value, dict):
                    self._merge_dict(target[key], value)
                elif isinstance(target[key], list) and isinstance(value, list):
                    target[key].extend(value)
                else:
                    # For simple values, overwrite with the latest
                    target[key] = value
            else:
                # Key doesn't exist in target, so add it
                target[key] = value 