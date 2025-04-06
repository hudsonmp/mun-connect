"""
JSON Generator module for background guide processing.

This module provides functions to generate structured JSON outputs from
processed document segments, including topics, committee information,
cited sources, and research maps.
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
import uuid

def generate_json_outputs(
    segments: List[Dict[str, Any]], 
    output_dir: str,
    use_aws_model: bool = True,
    aws_endpoint: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate JSON output files from document segments.
    
    Args:
        segments: List of document segments
        output_dir: Directory to write output files
        use_aws_model: Whether to use AWS hosted model for refinement
        aws_endpoint: AWS endpoint URL for hosted model
        
    Returns:
        Dictionary mapping output types to file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # First, extract topics from segments
    topics = extract_topics(segments)
    
    # Generate various JSON outputs
    json_files = {}
    
    # Generate topic files
    topic_dir = os.path.join(output_dir, "topics")
    os.makedirs(topic_dir, exist_ok=True)
    
    for topic, topic_segments in topics.items():
        filename = f"{slugify(topic)}.json"
        filepath = os.path.join(topic_dir, filename)
        
        topic_data = {
            "topic": topic,
            "segments": topic_segments,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "segment_count": len(topic_segments),
                "word_count": sum(len(segment["text"].split()) for segment in topic_segments)
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(topic_data, f, indent=2)
        
        json_files[f"topic_{topic}"] = filepath
    
    # Generate committee information
    committee_info = extract_committee_info(segments)
    committee_file = os.path.join(output_dir, "committee_info.json")
    
    with open(committee_file, 'w', encoding='utf-8') as f:
        json.dump(committee_info, f, indent=2)
    
    json_files["committee_info"] = committee_file
    
    # Generate cited sources
    sources = extract_cited_sources(segments)
    sources_file = os.path.join(output_dir, "cited_sources.json")
    
    with open(sources_file, 'w', encoding='utf-8') as f:
        json.dump(sources, f, indent=2)
    
    json_files["cited_sources"] = sources_file
    
    # Generate research map
    research_map = create_research_map(segments)
    research_map_file = os.path.join(output_dir, "research_map.json")
    
    with open(research_map_file, 'w', encoding='utf-8') as f:
        json.dump(research_map, f, indent=2)
    
    json_files["research_map"] = research_map_file
    
    # Use AWS model for refinement if requested
    if use_aws_model and aws_endpoint:
        try:
            refined_data = refine_with_aws_model(
                segments, 
                topics, 
                committee_info, 
                sources, 
                research_map,
                aws_endpoint
            )
            
            # Save refined data
            refined_file = os.path.join(output_dir, "refined_data.json")
            with open(refined_file, 'w', encoding='utf-8') as f:
                json.dump(refined_data, f, indent=2)
                
            json_files["refined_data"] = refined_file
        except Exception as e:
            print(f"Error using AWS model for refinement: {e}")
    
    return json_files

def extract_topics(segments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract topics from document segments and group segments by topic.
    
    Args:
        segments: List of document segments
        
    Returns:
        Dictionary mapping topics to relevant segments
    """
    # Simple approach: use main section headings as topics
    topics = {}
    
    for segment in segments:
        section = segment.get("section", "").strip()
        if not section:
            continue
            
        # Skip very short sections or generic sections
        if len(section) < 5 or section.lower() in ["introduction", "conclusion", "summary"]:
            continue
        
        # Use the section as the topic
        topic = section
        
        # Initialize the topic if not already present
        if topic not in topics:
            topics[topic] = []
        
        # Add the segment to the topic
        topics[topic].append(segment)
    
    # If no topics were found, create a generic "Main Topic" entry
    if not topics:
        topics["Main Topic"] = segments
    
    return topics

def extract_committee_info(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract committee information from document segments.
    
    Args:
        segments: List of document segments
        
    Returns:
        Dictionary containing committee information
    """
    committee_info = {
        "name": "",
        "topic": "",
        "rules": [],
        "flow": {},
        "guidelines": [],
        "created_at": datetime.now().isoformat()
    }
    
    # Look for committee information in the first few segments
    intro_segments = segments[:min(5, len(segments))]
    combined_text = " ".join([segment.get("text", "") for segment in intro_segments])
    
    # Extract committee name
    committee_match = re.search(r'(committee|council|commission|assembly)[\s:]+([^\n.]+)', 
                               combined_text, re.IGNORECASE)
    if committee_match:
        committee_info["name"] = committee_match.group(2).strip()
    
    # Extract topic if present
    topic_match = re.search(r'(topic|agenda|issue)[\s:]+([^\n.]+)', 
                           combined_text, re.IGNORECASE)
    if topic_match:
        committee_info["topic"] = topic_match.group(2).strip()
    
    # Extract rules
    rules = []
    for segment in segments:
        text = segment.get("text", "")
        
        # Look for paragraphs that might contain rules
        if re.search(r'(rule|procedure|protocol|guideline)', text, re.IGNORECASE):
            # Extract sentences that might contain rules
            sentences = text.split(". ")
            for sentence in sentences:
                if re.search(r'(must|should|shall|may not|will|required|prohibited)', 
                            sentence, re.IGNORECASE):
                    rules.append(sentence.strip())
    
    committee_info["rules"] = rules[:10]  # Limit to top 10 rules
    
    # Extract debate flow information
    flow_info = {}
    for segment in segments:
        text = segment.get("text", "")
        
        # Look for debate flow information
        if re.search(r'(debate|flow|moderated caucus|unmoderated caucus|voting)', 
                    text, re.IGNORECASE):
            # Look for time mentions
            time_matches = re.findall(r'(\d+)\s*(minute|second|hour)', text, re.IGNORECASE)
            if time_matches:
                flow_info["time_limits"] = [f"{t[0]} {t[1]}s" for t in time_matches]
            
            # Look for speaking time
            speaking_match = re.search(r'speaking time[\s:]+([^\n.]+)', text, re.IGNORECASE)
            if speaking_match:
                flow_info["speaking_time"] = speaking_match.group(1).strip()
            
            # Look for voting procedures
            if re.search(r'voting procedure', text, re.IGNORECASE):
                voting_sentences = [s for s in text.split(". ") 
                                   if "vote" in s.lower() or "majority" in s.lower()]
                if voting_sentences:
                    flow_info["voting"] = voting_sentences
    
    committee_info["flow"] = flow_info
    
    # Extract guidelines
    guidelines = []
    for segment in segments:
        text = segment.get("text", "")
        
        # Look for paragraphs that might contain guidelines
        if re.search(r'(guide|instruct|recommend|suggest)', text, re.IGNORECASE):
            # Extract sentences that might contain guidelines
            sentences = text.split(". ")
            for sentence in sentences:
                if len(sentence.split()) > 5:  # Ignore very short sentences
                    if re.search(r'(delegate|representative|member|participant)', 
                               sentence, re.IGNORECASE):
                        guidelines.append(sentence.strip())
    
    committee_info["guidelines"] = guidelines[:10]  # Limit to top 10 guidelines
    
    return committee_info

def extract_cited_sources(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract cited sources from document segments.
    
    Args:
        segments: List of document segments
        
    Returns:
        Dictionary containing cited sources information
    """
    sources = {
        "citations": [],
        "references": [],
        "created_at": datetime.now().isoformat()
    }
    
    # Patterns to identify citations
    citation_patterns = [
        r'\(([^)]+\d{4}[^)]*)\)',  # Parenthetical citations like (Author, 2020)
        r'(\[\d+\])',  # Numbered citations like [1]
        r'(\d+\s*\.\s*\w+[^.]+\d{4})',  # Numbered references like "1. Author et al. 2020"
    ]
    
    combined_text = " ".join([segment.get("text", "") for segment in segments])
    
    # Extract citations
    all_citations = []
    for pattern in citation_patterns:
        citations = re.findall(pattern, combined_text)
        all_citations.extend(citations)
    
    sources["citations"] = [citation.strip() for citation in all_citations]
    
    # Look for references section
    references = []
    for segment in segments:
        text = segment.get("text", "").lower()
        section = segment.get("section", "").lower()
        
        # Check if this segment looks like a references section
        if "reference" in section or "bibliography" in section or "works cited" in section:
            # Split into individual references
            lines = segment.get("text", "").split("\n")
            current_ref = ""
            
            for line in lines:
                if not line.strip():
                    if current_ref:
                        references.append(current_ref.strip())
                        current_ref = ""
                else:
                    if not current_ref and re.match(r'^\d+\.', line.strip()):
                        # Numbered reference
                        current_ref = line.strip()
                    elif not current_ref and re.match(r'^[A-Z]', line.strip()):
                        # Reference starting with capital letter
                        current_ref = line.strip()
                    else:
                        current_ref += " " + line.strip()
            
            # Add the last reference if there is one
            if current_ref:
                references.append(current_ref.strip())
    
    sources["references"] = references
    
    return sources

def create_research_map(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a structured research map from document segments.
    
    Args:
        segments: List of document segments
        
    Returns:
        Dictionary containing research map information
    """
    research_map = {
        "title": "Background Guide Research Map",
        "sections": [],
        "key_insights": [],
        "created_at": datetime.now().isoformat(),
        "id": str(uuid.uuid4())
    }
    
    # Extract title if available
    if segments and "section" in segments[0]:
        research_map["title"] = f"Research Map: {segments[0]['section']}"
    
    # Group segments by section
    sections = {}
    for segment in segments:
        section = segment.get("section", "Uncategorized")
        
        if section not in sections:
            sections[section] = {
                "title": section,
                "subsections": [],
                "summary": segment.get("summary", ""),
                "level": segment.get("level", 1)
            }
        
        # Add subsection if available
        subsection = segment.get("subsection")
        if subsection:
            sections[section]["subsections"].append({
                "title": subsection,
                "content": segment.get("text", ""),
                "summary": segment.get("summary", ""),
                "level": segment.get("level", 2)
            })
    
    # Convert sections dictionary to list
    research_map["sections"] = list(sections.values())
    
    # Sort sections by level and order of appearance
    research_map["sections"].sort(key=lambda x: (x.get("level", 1), research_map["sections"].index(x)))
    
    # Extract key insights from summaries
    all_summaries = []
    for segment in segments:
        if "summary" in segment and segment["summary"]:
            all_summaries.append(segment["summary"])
    
    # Use simple extraction for key insights
    key_insights = []
    for summary in all_summaries:
        sentences = summary.split(". ")
        for sentence in sentences:
            # Look for sentences that might contain key insights
            lower_sent = sentence.lower()
            if any(kw in lower_sent for kw in ["important", "key", "critical", "significant"]):
                if sentence not in key_insights:
                    key_insights.append(sentence)
    
    # Limit key insights
    research_map["key_insights"] = key_insights[:10]
    
    return research_map

def refine_with_aws_model(
    segments: List[Dict[str, Any]],
    topics: Dict[str, List[Dict[str, Any]]],
    committee_info: Dict[str, Any],
    sources: Dict[str, Any],
    research_map: Dict[str, Any],
    aws_endpoint: str
) -> Dict[str, Any]:
    """
    Refine generated data using an AWS hosted model.
    
    Args:
        segments: Document segments
        topics: Topics extracted from segments
        committee_info: Committee information
        sources: Cited sources
        research_map: Research map
        aws_endpoint: AWS endpoint URL
        
    Returns:
        Refined data from AWS model
    """
    # Prepare the data to send to AWS model
    request_data = {
        "input_data": {
            "segment_count": len(segments),
            "topics": list(topics.keys()),
            "committee_info": committee_info,
            "sources_count": len(sources.get("citations", [])) + len(sources.get("references", [])),
            "research_map_sections": [section["title"] for section in research_map.get("sections", [])]
        }
    }
    
    try:
        # Make the API call to AWS
        response = requests.post(
            aws_endpoint,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error from AWS model: {response.status_code} - {response.text}")
            return {"error": f"AWS model returned status code {response.status_code}"}
    except Exception as e:
        print(f"Error calling AWS model: {e}")
        return {"error": str(e)}

def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.
    
    Args:
        text: Text to convert
        
    Returns:
        Slug version of the text
    """
    # Convert to lowercase
    slug = text.lower()
    
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Limit length
    if len(slug) > 50:
        slug = slug[:50].rstrip('-')
    
    return slug 