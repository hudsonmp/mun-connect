import json
import torch
import numpy as np
import os
from transformers import AutoModel, AutoTokenizer
import requests
import logging
from typing import Dict, List, Any, Optional, Union

# Import unified AI interface
from ..shared.ai_interface import AIInterface

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MindMapGenerator:
    """
    A class to generate and customize mind maps for delegates based on committee background guides.
    This creates a standard mind map structure that can be customized for specific delegates and countries.
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2",
                ai_provider: str = "openai", ai_model: str = "gpt-4o-mini"):
        """
        Initialize the mind map generator with the specified model.
        
        Args:
            model_name: The HuggingFace model to use for embeddings
            ai_provider: The AI provider to use for enrichment (openai, anthropic, local)
            ai_model: The model to use for enrichment
        """
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = AutoModel.from_pretrained(model_name).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Store AI configuration
            self.ai_provider = ai_provider
            self.ai_model = ai_model
            
            logger.info(f"Initialized MindMapGenerator with model {model_name} on {self.device}")
            logger.info(f"Using AI provider: {ai_provider}, model: {ai_model}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def generate_base_mind_map(self, background_guide_content: str) -> Dict[str, Any]:
        """
        Generate the base mind map from a committee's background guide.
        
        Args:
            background_guide_content: The text content of the background guide
            
        Returns:
            A JSON representation of the base mind map
        """
        try:
            # Process the background guide to extract key topics and relationships
            topics = self._extract_topics(background_guide_content)
            
            # Create the base mind map structure
            base_mind_map = {
                "title": "Committee Background Guide",
                "description": "Base mind map generated from committee background guide",
                "created_at": self._get_timestamp(),
                "topics": topics,
                "connections": self._identify_connections(topics)
            }
            
            logger.info(f"Generated base mind map with {len(topics)} topics")
            return base_mind_map
        except Exception as e:
            logger.error(f"Error generating base mind map: {e}")
            raise
    
    def customize_mind_map(self, 
                         base_mind_map: Dict[str, Any], 
                         country: str, 
                         delegate_profile: Dict[str, Any],
                         api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Customize the base mind map with country-specific and delegate-specific information.
        
        Args:
            base_mind_map: The base mind map JSON
            country: The country the delegate is representing
            delegate_profile: The delegate's profile information
            api_key: API key for the AI provider (optional, can use environment variables)
            
        Returns:
            A customized and enriched mind map JSON
        """
        try:
            # Enrich the mind map with country-specific information using the configured AI provider
            enriched_mind_map = self._enrich_with_openai(
                base_mind_map, country, delegate_profile, api_key)
            
            # Create two different output formats - one for backend research and one for frontend visualization
            research_json = self._create_research_json(enriched_mind_map)
            visualization_json = self._create_visualization_json(enriched_mind_map)
            
            logger.info(f"Customized mind map for {country}")
            return {
                "research_json": research_json,
                "visualization_json": visualization_json
            }
        except Exception as e:
            logger.error(f"Error customizing mind map: {e}")
            raise
    
    def index_mind_map(self, research_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Index the mind map content for efficient retrieval during paper generation.
        
        Args:
            research_json: The research-focused JSON from customize_mind_map
            
        Returns:
            An indexed version of the mind map
        """
        try:
            # Create embeddings for each node in the mind map
            indexed_map = research_json.copy()
            indexed_map["node_embeddings"] = {}
            
            # Generate embeddings for each topic and subtopic
            for topic_id, topic in enumerate(indexed_map["topics"]):
                topic_embedding = self._generate_embedding(topic["title"] + ". " + topic["description"])
                indexed_map["node_embeddings"][f"topic_{topic_id}"] = {
                    "embedding": topic_embedding.tolist(),
                    "content": topic["title"] + ". " + topic["description"]
                }
                
                # Process subtopics if they exist
                if "subtopics" in topic:
                    for subtopic_id, subtopic in enumerate(topic["subtopics"]):
                        subtopic_text = subtopic["title"] + ". " + subtopic["description"]
                        subtopic_embedding = self._generate_embedding(subtopic_text)
                        indexed_map["node_embeddings"][f"topic_{topic_id}_subtopic_{subtopic_id}"] = {
                            "embedding": subtopic_embedding.tolist(),
                            "content": subtopic_text
                        }
            
            logger.info(f"Indexed mind map with {len(indexed_map['node_embeddings'])} embeddings")
            return indexed_map
        except Exception as e:
            logger.error(f"Error indexing mind map: {e}")
            raise
    
    def _extract_topics(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract main topics from the background guide text.
        
        Args:
            text: The background guide text
            
        Returns:
            A list of topic objects with titles, descriptions, and subtopics
        """
        # Simple implementation - in production this would use more sophisticated NLP
        # Here we're just doing a basic extraction for demonstration
        
        # Split the text into sections and extract topics
        sections = text.split('\n\n')
        topics = []
        
        current_topic = None
        for section in sections:
            if not section.strip():
                continue
                
            # Very basic heuristic to identify headers as topics
            if len(section.strip()) < 100 and not section.endswith('.'):
                # This might be a header/topic
                current_topic = {
                    "title": section.strip(),
                    "description": "",
                    "subtopics": []
                }
                topics.append(current_topic)
            elif current_topic:
                # If this looks like content and we have a current topic, append to description
                if len(current_topic["description"]) < 200:  # Limit description length
                    current_topic["description"] += section.strip() + " "
                else:
                    # If we already have a description, this might be a subtopic
                    subtopic = {
                        "title": section.split('.')[0].strip(),
                        "description": section.strip()
                    }
                    current_topic["subtopics"].append(subtopic)
        
        return topics
    
    def _identify_connections(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify connections between topics based on semantic similarity.
        
        Args:
            topics: List of topics from the mind map
            
        Returns:
            A list of connection objects showing relationships between topics
        """
        connections = []
        
        # Generate embeddings for each topic
        topic_embeddings = []
        for topic in topics:
            text = topic["title"] + ". " + topic["description"]
            embedding = self._generate_embedding(text)
            topic_embeddings.append(embedding)
        
        # Find connections based on cosine similarity
        for i in range(len(topics)):
            for j in range(i+1, len(topics)):
                similarity = self._cosine_similarity(topic_embeddings[i], topic_embeddings[j])
                
                # If similarity is above threshold, create a connection
                if similarity > 0.7:  # Arbitrary threshold
                    connections.append({
                        "source": i,
                        "target": j,
                        "strength": float(similarity),
                        "description": f"Related concepts: {topics[i]['title']} and {topics[j]['title']}"
                    })
        
        return connections
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a text using the loaded model.
        
        Args:
            text: The text to embed
            
        Returns:
            A numpy array containing the embedding
        """
        # Tokenize and embed the text
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use mean pooling to get a single vector for the entire text
        # Use the last hidden state as the embedding
        embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]
        return embedding
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity as a float
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def _enrich_with_openai(self, 
                           base_mind_map: Dict[str, Any], 
                           country: str, 
                           delegate_profile: Dict[str, Any],
                           api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich the mind map with AI assistance, integrating country-specific context.
        
        Args:
            base_mind_map: The base mind map
            country: The country name
            delegate_profile: Delegate profile information
            api_key: API key for the AI provider (optional, can use environment variables)
            
        Returns:
            Enriched mind map with country-specific details
        """
        from ..shared.prompt_templates import MIND_MAP_GENERATION_TEMPLATE
        
        enriched_map = base_mind_map.copy()
        
        try:
            # Create an AI interface instance
            ai = AIInterface(
                provider=self.ai_provider,
                api_key=api_key,
                default_model=self.ai_model
            )
            
            # Prepare the base mind map for AI
            simplified_base_map = {
                "title": base_mind_map["title"],
                "topics": [{"title": t["title"], "description": t["description"]} for t in base_mind_map["topics"]]
            }
            
            # Create the prompt with instructions
            prompt = f"""
            Please customize this mind map for {country}'s delegation. 
            
            Base mind map:
            {json.dumps(simplified_base_map, indent=2)}
            
            Delegate profile:
            {json.dumps(delegate_profile, indent=2)}
            
            For each topic:
            1. Assign a relevance score (0-10) based on how important this topic is to {country}
            2. Add detailed annotations with quotes, policy notes, and historical context
            3. Add a "highlight" boolean field (true if this node is especially important for {country})
            
            Return only the enriched JSON mind map with these additions.
            """
            
            # Use the AI interface to generate the response
            enriched_content = ai.generate_structured_output(
                prompt,
                output_format="json",
                temperature=0.3,
                max_tokens=3000
            )
            
            # Update the topics with the enriched information
            if enriched_content and "topics" in enriched_content:
                for i, topic in enumerate(enriched_map["topics"]):
                    if i < len(enriched_content["topics"]):
                        enriched_topic = enriched_content["topics"][i]
                        
                        # Add new fields from the AI response
                        topic["relevance_score"] = enriched_topic.get("relevance_score", 5)
                        topic["annotations"] = enriched_topic.get("annotations", [])
                        topic["highlight"] = enriched_topic.get("highlight", False)
                        
                        # If enriched topic includes subtopics, update those too
                        if "subtopics" in enriched_topic and "subtopics" in topic:
                            for j, subtopic in enumerate(topic["subtopics"]):
                                if j < len(enriched_topic["subtopics"]):
                                    enriched_subtopic = enriched_topic["subtopics"][j]
                                    subtopic["relevance_score"] = enriched_subtopic.get("relevance_score", 5)
                                    subtopic["annotations"] = enriched_subtopic.get("annotations", [])
                                    subtopic["highlight"] = enriched_subtopic.get("highlight", False)
                
                logger.info(f"Successfully enriched mind map with AI for {country}")
            else:
                logger.error(f"Error: AI response missing expected 'topics' field")
                # If we couldn't enrich with AI, add placeholder scores
                self._add_placeholder_values(enriched_map)
        
        except Exception as e:
            logger.error(f"Error in AI enrichment: {e}")
            # Add fallback values
            self._add_placeholder_values(enriched_map)
        
        return enriched_map
        
    def _add_placeholder_values(self, mind_map: Dict[str, Any]) -> None:
        """
        Add placeholder values to topics when AI enrichment fails
        
        Args:
            mind_map: The mind map to add placeholder values to
        """
        # Add fallback values to all topics
        for topic in mind_map["topics"]:
            topic["relevance_score"] = 5  # Default score
            topic["annotations"] = []
            topic["highlight"] = False
            
            # Also add to subtopics if they exist
            if "subtopics" in topic:
                for subtopic in topic["subtopics"]:
                    subtopic["relevance_score"] = 5
                    subtopic["annotations"] = []
                    subtopic["highlight"] = False
    
    def _create_research_json(self, enriched_mind_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the detailed research JSON from the enriched mind map.
        This will be used for backend operations and paper generation.
        
        Args:
            enriched_mind_map: The mind map enriched with country context
            
        Returns:
            Research-focused JSON with detailed annotations
        """
        research_json = enriched_mind_map.copy()
        
        # Add metadata and sources field for citations
        research_json["metadata"] = {
            "created_at": self._get_timestamp(),
            "purpose": "research",
            "version": "1.0"
        }
        
        research_json["sources"] = []
        
        # Enhance topics with research-specific data
        for topic in research_json["topics"]:
            # Add fields specific to research needs
            topic["research_notes"] = self._extract_research_notes(topic)
            topic["key_quotes"] = self._extract_key_quotes(topic)
            topic["historical_context"] = self._extract_historical_context(topic)
            
            # Do the same for subtopics
            if "subtopics" in topic:
                for subtopic in topic["subtopics"]:
                    subtopic["research_notes"] = self._extract_research_notes(subtopic)
                    subtopic["key_quotes"] = self._extract_key_quotes(subtopic)
                    subtopic["historical_context"] = self._extract_historical_context(subtopic)
        
        return research_json
    
    def _create_visualization_json(self, enriched_mind_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a simplified JSON for frontend visualization.
        
        Args:
            enriched_mind_map: The mind map enriched with country context
            
        Returns:
            Visualization-focused JSON with styling information
        """
        # Start with a clean slate for visualization
        visualization_json = {
            "title": enriched_mind_map["title"],
            "nodes": [],
            "links": []
        }
        
        # Add central node (the committee/topic)
        visualization_json["nodes"].append({
            "id": "center",
            "label": enriched_mind_map["title"],
            "type": "central",
            "size": 30,
            "color": "#4A90E2"
        })
        
        # Add nodes for each topic
        for i, topic in enumerate(enriched_mind_map["topics"]):
            # Calculate color based on relevance score (green = high, yellow = medium, red = low)
            relevance = topic.get("relevance_score", 5)
            color = self._get_relevance_color(relevance)
            
            # Add the topic node
            node_id = f"topic_{i}"
            visualization_json["nodes"].append({
                "id": node_id,
                "label": topic["title"],
                "type": "topic",
                "relevance": relevance,
                "size": 20 if topic.get("highlight", False) else 15,
                "color": color,
                "highlighted": topic.get("highlight", False),
                "description": topic["description"][:100] + "..." if len(topic["description"]) > 100 else topic["description"]
            })
            
            # Link to central node
            visualization_json["links"].append({
                "source": "center",
                "target": node_id,
                "value": 2
            })
            
            # Add subtopics if they exist
            if "subtopics" in topic:
                for j, subtopic in enumerate(topic["subtopics"]):
                    subtopic_relevance = subtopic.get("relevance_score", relevance)
                    subtopic_color = self._get_relevance_color(subtopic_relevance)
                    
                    # Add the subtopic node
                    subtopic_id = f"topic_{i}_subtopic_{j}"
                    visualization_json["nodes"].append({
                        "id": subtopic_id,
                        "label": subtopic["title"],
                        "type": "subtopic",
                        "relevance": subtopic_relevance,
                        "size": 12 if subtopic.get("highlight", False) else 10,
                        "color": subtopic_color,
                        "highlighted": subtopic.get("highlight", False),
                        "description": subtopic["description"][:80] + "..." if len(subtopic["description"]) > 80 else subtopic["description"]
                    })
                    
                    # Link to parent topic
                    visualization_json["links"].append({
                        "source": node_id,
                        "target": subtopic_id,
                        "value": 1
                    })
        
        # Add connections between related topics
        if "connections" in enriched_mind_map:
            for connection in enriched_mind_map["connections"]:
                source_id = f"topic_{connection['source']}"
                target_id = f"topic_{connection['target']}"
                
                visualization_json["links"].append({
                    "source": source_id,
                    "target": target_id,
                    "value": connection["strength"],
                    "dashed": True
                })
        
        return visualization_json
    
    def _extract_research_notes(self, topic_or_subtopic: Dict[str, Any]) -> List[str]:
        """Extract research notes from topic annotations."""
        notes = []
        for annotation in topic_or_subtopic.get("annotations", []):
            if isinstance(annotation, str):
                notes.append(annotation)
            elif isinstance(annotation, dict) and "text" in annotation:
                notes.append(annotation["text"])
        return notes
    
    def _extract_key_quotes(self, topic_or_subtopic: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract key quotes from topic annotations."""
        quotes = []
        for annotation in topic_or_subtopic.get("annotations", []):
            if isinstance(annotation, dict) and "quote" in annotation:
                quotes.append({
                    "text": annotation["quote"],
                    "source": annotation.get("source", "Unknown")
                })
        return quotes
    
    def _extract_historical_context(self, topic_or_subtopic: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract historical context from topic annotations."""
        history = []
        for annotation in topic_or_subtopic.get("annotations", []):
            if isinstance(annotation, dict) and "historical_context" in annotation:
                history.append({
                    "text": annotation["historical_context"],
                    "year": annotation.get("year", "Unknown")
                })
        return history
    
    def _get_relevance_color(self, relevance: int) -> str:
        """Get a color based on relevance score."""
        if relevance >= 7:
            return "#7FBA00"  # Green for high relevance
        elif relevance >= 4:
            return "#FFBA08"  # Yellow for medium relevance
        else:
            return "#E74C3C"  # Red for low relevance
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp as a string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_from_processor_output(self, processor_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mind map from BackgroundGuideProcessor output
        
        Args:
            processor_output: Standardized processor output
            
        Returns:
            Mind map structure
        """
        try:
            # Extract text content from segments
            content = ""
            if "segments" in processor_output:
                content = "\n\n".join([
                    f"## {segment.get('section', 'Section')}\n{segment.get('text', '')}" 
                    for segment in processor_output.get("segments", [])
                ])
            
            # Generate base mind map
            base_mind_map = self.generate_base_mind_map(content)
            
            # Add metadata from processor
            if "metadata" in processor_output:
                if "metadata" not in base_mind_map:
                    base_mind_map["metadata"] = {}
                
                base_mind_map["metadata"].update(processor_output.get("metadata", {}))
            
            # Add summaries for context
            if "summaries" in processor_output:
                if "summaries" not in base_mind_map:
                    base_mind_map["summaries"] = {}
                
                base_mind_map["summaries"].update(processor_output.get("summaries", {}))
            
            logger.info(f"Generated mind map from processor output with {len(base_mind_map.get('topics', []))} topics")
            return base_mind_map
        except Exception as e:
            logger.error(f"Error generating mind map from processor output: {e}")
            raise
    
    def export_for_delegate_profile(self, mind_map_data: Dict[str, Any], country: str) -> Dict[str, Any]:
        """
        Format mind map data for delegate profile integration
        
        Args:
            mind_map_data: Generated mind map data
            country: Country for position analysis
            
        Returns:
            Formatted data ready for delegate profile
        """
        try:
            logger.info(f"Exporting mind map data for {country} delegate profile")
            
            # Create base structure for export
            export_data = {
                "metadata": mind_map_data.get("metadata", {}),
                "base_structure": {
                    "topics": mind_map_data.get("topics", []),
                    "connections": mind_map_data.get("connections", [])
                }
            }
            
            # Enhance with country-specific position data if needed
            if "country_positions" not in mind_map_data and country:
                country_positions = {}
                
                # Generate positions for each topic based on country
                for i, topic in enumerate(mind_map_data.get("topics", [])):
                    country_positions[f"topic_{i}"] = self._analyze_country_position(
                        topic, country
                    )
                
                export_data["country_positions"] = country_positions
            else:
                export_data["country_positions"] = mind_map_data.get("country_positions", {})
            
            logger.info(f"Exported mind map data with {len(export_data['base_structure']['topics'])} topics")
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting mind map data for delegate profile: {e}")
            raise
    
    def _analyze_country_position(self, topic: Dict[str, Any], country: str) -> Dict[str, Any]:
        """
        Analyze a country's position on a specific topic
        
        Args:
            topic: Topic data
            country: Country name
            
        Returns:
            Position analysis
        """
        # This is a placeholder - in production, this would use more sophisticated analysis
        # It could call an external API or use a specialized model
        
        # Simple random position for demonstration
        stances = ["supportive", "neutral", "opposed"]
        stance = stances[hash(country + topic["title"]) % len(stances)]
        
        return {
            "position": f"{country}'s position on {topic['title']}",
            "stance": stance,
            "key_points": [
                f"Point 1 for {country} on {topic['title']}",
                f"Point 2 for {country} on {topic['title']}"
            ],
            "evidence": [
                f"Evidence from previous {country} statements",
                f"Historical {country} voting patterns"
            ]
        } 