# app.py
from flask import Flask, request, jsonify, render_template
import torch
from transformers import BertModel, BertTokenizer, BertForSequenceClassification
import numpy as np
import pandas as pd
import json
import os
from collections import defaultdict
import re
from nltk.tokenize import sent_tokenize
import openai
from scipy.special import softmax
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure OpenAI API
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Load BERT model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
bert_model = BertModel.from_pretrained('bert-base-uncased')

# Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
bert_model = bert_model.to(device)
bert_model.eval()  # Set the model to evaluation mode

# Configuration
CONFIG = {
    'elo_k_factor': 30,  # Standard K-factor for ELO rating
    'default_elo': 1400,  # Default ELO rating for new sentences
    'min_comparisons_per_sentence': 5,  # Minimum number of comparisons per sentence
    'max_bert_sequence_length': 512,  # Maximum sequence length for BERT
    'bert_hidden_size': 768,  # Hidden size of BERT outputs
    'linguistic_features': [
        'sentence_length', 'word_length', 'vocab_diversity',
        'formality', 'active_voice', 'complexity'
    ],
    'min_documents_required': 3,  # Minimum number of documents for analysis
}

# ------------------------------------------------------
# DOCUMENT PARSING AND PROCESSING
# ------------------------------------------------------

class DocumentProcessor:
    def __init__(self):
        self.documents = []
        self.sentences = []
        self.metadata = {}
    
    def add_document(self, document_text, document_type, committee, topic, country, year):
        """Add a new document to the processor with metadata"""
        doc_id = len(self.documents)
        
        # Store document with metadata
        document = {
            'id': doc_id,
            'text': document_text,
            'type': document_type,
            'committee': committee,
            'topic': topic, 
            'country': country,
            'year': year,
            'sentences': []
        }
        
        # Extract and store sentences
        sentences = sent_tokenize(document_text)
        for i, sent in enumerate(sentences):
            sent_id = len(self.sentences)
            sentence = {
                'id': sent_id,
                'doc_id': doc_id,
                'position': i,
                'text': sent,
                'elo_rating': CONFIG['default_elo'],
                'comparisons': 0,
                'features': {},
                'section': self._determine_section(i, len(sentences), document_type)
            }
            self.sentences.append(sentence)
            document['sentences'].append(sent_id)
        
        self.documents.append(document)
        self._update_metadata()
        
        return doc_id

    def _determine_section(self, position, total_sentences, doc_type):
        """Determine which section a sentence belongs to based on position"""
        if doc_type == "position_paper":
            # Simple heuristic - divide into introduction, body, conclusion
            if position < total_sentences * 0.2:
                return "introduction"
            elif position > total_sentences * 0.8:
                return "conclusion"
            else:
                return "body"
        elif doc_type == "resolution":
            # Resolutions have preamble and operative clauses
            if position < total_sentences * 0.3:
                return "preamble"
            else:
                return "operative"
        else:
            # Default section determination
            if position < total_sentences * 0.15:
                return "opening"
            elif position > total_sentences * 0.85:
                return "closing"
            else:
                return "main"
    
    def _update_metadata(self):
        """Update metadata based on all documents"""
        committees = set()
        topics = set()
        countries = set()
        years = set()
        
        for doc in self.documents:
            committees.add(doc['committee'])
            topics.add(doc['topic'])
            countries.add(doc['country'])
            years.add(doc['year'])
        
        self.metadata = {
            'committees': list(committees),
            'topics': list(topics),
            'countries': list(countries),
            'years': list(sorted(years)),
            'time_span': f"{min(years)}-{max(years)}" if years else "Unknown",
            'document_count': len(self.documents)
        }
    
    def get_sentences_by_section(self, section):
        """Get all sentences belonging to a specific section"""
        return [s for s in self.sentences if s['section'] == section]
    
    def get_sentences_sample(self, count=10, stratified=True):
        """Get a sample of sentences for comparison, stratified by document and section if requested"""
        if stratified:
            # Get sentences stratified by document and section
            samples = []
            sections = set(s['section'] for s in self.sentences)
            docs = set(s['doc_id'] for s in self.sentences)
            
            # Try to get an equal number from each doc/section combination
            target_per_combo = max(1, count // (len(sections) * len(docs)))
            
            for doc_id in docs:
                for section in sections:
                    candidates = [s for s in self.sentences 
                                 if s['doc_id'] == doc_id and s['section'] == section]
                    if candidates:
                        samples.extend(random.sample(candidates, 
                                                    min(target_per_combo, len(candidates))))
            
            # If we still need more, add random sentences
            if len(samples) < count:
                remaining_sentences = [s for s in self.sentences if s not in samples]
                samples.extend(random.sample(remaining_sentences, 
                                           min(count - len(samples), len(remaining_sentences))))
            
            return samples[:count]
        else:
            # Simple random sample
            return random.sample(self.sentences, min(count, len(self.sentences)))
    
    def get_comparison_pairs(self, count=5):
        """Get pairs of sentences for style preference comparison"""
        pairs = []
        
        # Strategy: pair sentences that need more comparisons
        # but also ensure diversity in sections and documents
        
        # Prioritize sentences with fewer comparisons
        sorted_sentences = sorted(self.sentences, key=lambda s: s['comparisons'])
        
        # Create pairs ensuring diverse docs and sections
        doc_ids = set(doc['id'] for doc in self.documents)
        
        for _ in range(count):
            # Select first sentence that needs more comparisons
            s1 = sorted_sentences[0]
            
            # Find a second sentence from a different document if possible
            candidates = []
            for s2 in self.sentences:
                if s1['id'] != s2['id']:
                    # Give bonus to sentences from different docs and sections
                    score = s2['comparisons']  # Lower is better
                    if s1['doc_id'] != s2['doc_id']:
                        score -= 5  # Bonus for different document
                    if s1['section'] != s2['section']:
                        score -= 2  # Bonus for different section
                    candidates.append((score, s2))
            
            candidates.sort()
            s2 = candidates[0][1] if candidates else random.choice(self.sentences)
            
            pairs.append((s1['id'], s2['id']))
            
            # Update comparison counts for next iteration
            s1['comparisons'] += 1
            s2['comparisons'] += 1
            sorted_sentences = sorted(self.sentences, key=lambda s: s['comparisons'])
        
        return pairs
    
    def get_metadata(self):
        """Get document metadata"""
        return self.metadata

# ------------------------------------------------------
# BERT LINGUISTIC FEATURE EXTRACTION
# ------------------------------------------------------

class BertLinguisticAnalyzer:
    def __init__(self, bert_model, tokenizer, device):
        self.bert_model = bert_model
        self.tokenizer = tokenizer
        self.device = device
        
        # Features we'll extract using BERT
        self.features = {
            'sentence_embedding': self._get_sentence_embedding,
            'sentence_length': self._get_sentence_length,
            'word_length': self._get_avg_word_length,
            'vocab_diversity': self._get_vocab_diversity,
            'formality': self._estimate_formality,
            'active_voice': self._estimate_active_voice,
            'complexity': self._estimate_complexity,
        }
    
    def analyze_sentence(self, sentence_text):
        """Extract all linguistic features from a sentence"""
        features = {}
        
        for feature_name, feature_func in self.features.items():
            features[feature_name] = feature_func(sentence_text)
            
        return features
    
    def _get_sentence_embedding(self, sentence_text):
        """Get BERT embedding for a sentence"""
        inputs = self.tokenizer(sentence_text, return_tensors="pt", 
                                truncation=True, padding=True, 
                                max_length=CONFIG['max_bert_sequence_length'])
        
        inputs = {key: val.to(self.device) for key, val in inputs.items()}
        
        with torch.no_grad():
            outputs = self.bert_model(**inputs)
            # Use [CLS] token embedding as sentence embedding
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
        
        return embedding.tolist()  # Convert to list for JSON serialization
    
    def _get_sentence_length(self, sentence_text):
        """Get sentence length in tokens"""
        return len(self.tokenizer.tokenize(sentence_text))
    
    def _get_avg_word_length(self, sentence_text):
        """Get average word length"""
        words = sentence_text.strip().split()
        if not words:
            return 0
        return sum(len(word) for word in words) / len(words)
    
    def _get_vocab_diversity(self, sentence_text):
        """Calculate vocabulary diversity (unique words / total words)"""
        words = sentence_text.lower().strip().split()
        if not words:
            return 0
        return len(set(words)) / len(words)
    
    def _estimate_formality(self, sentence_text):
        """Estimate formality based on linguistic markers"""
        # This is a simplified approach - could be replaced with a trained classifier
        formal_markers = [
            r'\b(therefore|furthermore|consequently|thus|hence|accordingly)\b',
            r'\b(shall|must|ought|require)\b',
            r'\b(pursuant|aforementioned|hereby|wherein)\b',
            r'\bthe [\w]+ of\b',
            r'\bin accordance with\b',
        ]
        
        informal_markers = [
            r'\b(anyway|basically|actually|so)\b',
            r'\b(like|sort of|kind of)\b',
            r"('ll|'re|'ve|'m|gonna|wanna)\b",
            r'\b(yeah|nope|yep)\b',
            r'!{2,}',
        ]
        
        formal_count = sum(1 for marker in formal_markers 
                          if re.search(marker, sentence_text, re.IGNORECASE))
        informal_count = sum(1 for marker in informal_markers 
                            if re.search(marker, sentence_text, re.IGNORECASE))
        
        # Normalize to 0-1 range
        total = formal_count + informal_count
        if total == 0:
            return 0.5  # Neutral
        return formal_count / total
    
    def _estimate_active_voice(self, sentence_text):
        """Estimate if sentence uses active voice"""
        # This is a heuristic approach
        passive_markers = [
            r'\b(is|are|was|were|be|been|being) \w+ed\b',
            r'\b(has|have|had) been \w+ed\b',
            r'\b(is|are|was|were) being \w+ed\b',
        ]
        
        passive_count = sum(1 for marker in passive_markers 
                           if re.search(marker, sentence_text, re.IGNORECASE))
        
        # Rough estimate - more sophisticated parsing would be better
        return 1.0 if passive_count == 0 else 0.0
    
    def _estimate_complexity(self, sentence_text):
        """Estimate sentence complexity"""
        # Simple heuristic based on sentence length and subordinate clauses
        tokens = self.tokenizer.tokenize(sentence_text)
        length_factor = min(1.0, len(tokens) / 40)  # Normalize to 0-1
        
        # Count subordinate clause markers
        subordinate_markers = [
            r'\b(although|though|while|whereas|because|since|if|unless)\b',
            r'\b(as|that|which|who|whom|whose)\b',
            r',\s*(which|who|where|when)\b',
        ]
        
        clause_count = sum(1 for marker in subordinate_markers 
                          if re.search(marker, sentence_text, re.IGNORECASE))
        clause_factor = min(1.0, clause_count / 3)  # Normalize to 0-1
        
        # Combine factors
        return (length_factor + clause_factor) / 2
    
    def analyze_document(self, document_processor):
        """Analyze all sentences in all documents"""
        for sentence in document_processor.sentences:
            features = self.analyze_sentence(sentence['text'])
            sentence['features'].update(features)
        
        return document_processor
    
    def get_document_level_features(self, document_processor):
        """Extract document-level linguistic features"""
        doc_features = []
        
        for doc in document_processor.documents:
            # Get all sentences for this document
            doc_sentences = [document_processor.sentences[i] for i in doc['sentences']]
            
            # Aggregate sentence-level features
            feature_averages = defaultdict(list)
            for sent in doc_sentences:
                for feature, value in sent['features'].items():
                    # Skip embeddings for aggregation
                    if feature != 'sentence_embedding' and isinstance(value, (int, float)):
                        feature_averages[feature].append(value)
            
            # Calculate document-level statistics
            doc_stats = {
                'doc_id': doc['id'],
                'sentence_count': len(doc_sentences),
                'avg_sentence_length': np.mean(feature_averages['sentence_length']) 
                                      if 'sentence_length' in feature_averages else 0,
                'std_sentence_length': np.std(feature_averages['sentence_length'])
                                      if 'sentence_length' in feature_averages else 0,
                'avg_word_length': np.mean(feature_averages['word_length'])
                                  if 'word_length' in feature_averages else 0,
                'avg_formality': np.mean(feature_averages['formality'])
                                if 'formality' in feature_averages else 0,
                'avg_complexity': np.mean(feature_averages['complexity'])
                                 if 'complexity' in feature_averages else 0,
                'active_voice_ratio': np.mean(feature_averages['active_voice'])
                                    if 'active_voice' in feature_averages else 0,
            }
            
            doc_features.append(doc_stats)
        
        return doc_features

# ------------------------------------------------------
# ELO RATING SYSTEM
# ------------------------------------------------------

class EloStyleRater:
    def __init__(self, k_factor=CONFIG['elo_k_factor']):
        self.k_factor = k_factor
    
    def update_ratings(self, winner_id, loser_id, document_processor):
        """Update ELO ratings after a comparison"""
        # Get current ratings
        winner = next(s for s in document_processor.sentences if s['id'] == winner_id)
        loser = next(s for s in document_processor.sentences if s['id'] == loser_id)
        
        winner_rating = winner['elo_rating']
        loser_rating = loser['elo_rating']
        
        # Calculate expected scores
        expected_winner = 1 / (1 + 10**((loser_rating - winner_rating) / 400))
        expected_loser = 1 / (1 + 10**((winner_rating - loser_rating) / 400))
        
        # Update ratings
        winner['elo_rating'] = winner_rating + self.k_factor * (1 - expected_winner)
        loser['elo_rating'] = loser_rating + self.k_factor * (0 - expected_loser)
        
        # Update comparison counts
        winner['comparisons'] += 1
        loser['comparisons'] += 1
        
        return document_processor
    
    def get_style_rankings(self, document_processor):
        """Get all sentences ranked by ELO rating"""
        # Only include sentences with enough comparisons
        qualified_sentences = [s for s in document_processor.sentences 
                              if s['comparisons'] >= CONFIG['min_comparisons_per_sentence']]
        
        # Sort by ELO rating
        ranked_sentences = sorted(qualified_sentences, 
                                 key=lambda s: s['elo_rating'], reverse=True)
        
        return ranked_sentences
    
    def get_style_insights(self, document_processor):
        """Extract insights from ELO ratings"""
        ranked_sentences = self.get_style_rankings(document_processor)
        
        # Get top and bottom sentences
        top_sentences = ranked_sentences[:min(10, len(ranked_sentences))]
        bottom_sentences = ranked_sentences[-min(10, len(ranked_sentences)):]
        
        # Analyze features of top rated sentences
        top_features = defaultdict(list)
        for sent in top_sentences:
            for feature, value in sent['features'].items():
                if feature != 'sentence_embedding' and isinstance(value, (int, float)):
                    top_features[feature].append(value)
        
        # Calculate average feature values for top sentences
        top_avg_features = {
            feature: np.mean(values) for feature, values in top_features.items()
        }
        
        # Same for bottom sentences
        bottom_features = defaultdict(list)
        for sent in bottom_sentences:
            for feature, value in sent['features'].items():
                if feature != 'sentence_embedding' and isinstance(value, (int, float)):
                    bottom_features[feature].append(value)
        
        bottom_avg_features = {
            feature: np.mean(values) for feature, values in bottom_features.items()
        }
        
        # Generate insights
        insights = []
        
        # Compare top vs bottom for significant differences
        for feature in set(top_avg_features.keys()) & set(bottom_avg_features.keys()):
            top_val = top_avg_features[feature]
            bottom_val = bottom_avg_features[feature]
            
            if abs(top_val - bottom_val) > 0.1:  # Threshold for significance
                if top_val > bottom_val:
                    insights.append({
                        'feature': feature,
                        'insight': f"Higher {feature} correlates with preferred style",
                        'difference': top_val - bottom_val,
                        'top_value': top_val,
                        'bottom_value': bottom_val,
                    })
                else:
                    insights.append({
                        'feature': feature,
                        'insight': f"Lower {feature} correlates with preferred style",
                        'difference': bottom_val - top_val,
                        'top_value': top_val,
                        'bottom_value': bottom_val,
                    })
        
        # Section-specific insights
        section_ratings = defaultdict(list)
        for sent in document_processor.sentences:
            if sent['comparisons'] >= CONFIG['min_comparisons_per_sentence']:
                section_ratings[sent['section']].append(sent['elo_rating'])
        
        section_avg_ratings = {
            section: np.mean(ratings) for section, ratings in section_ratings.items()
            if len(ratings) >= 3  # Minimum number of sentences for reliable average
        }
        
        if section_avg_ratings:
            best_section = max(section_avg_ratings.items(), key=lambda x: x[1])
            worst_section = min(section_avg_ratings.items(), key=lambda x: x[1])
            
            insights.append({
                'feature': 'section_quality',
                'insight': f"Writing in '{best_section[0]}' sections is typically preferred",
                'best_section': best_section[0],
                'best_section_rating': best_section[1],
                'worst_section': worst_section[0],
                'worst_section_rating': worst_section[1],
            })
        
        return {
            'top_sentences': [{'id': s['id'], 'text': s['text'], 'rating': s['elo_rating']} 
                             for s in top_sentences],
            'bottom_sentences': [{'id': s['id'], 'text': s['text'], 'rating': s['elo_rating']} 
                               for s in bottom_sentences],
            'insights': insights
        }

# ------------------------------------------------------
# JSON PROFILE GENERATION
# ------------------------------------------------------

class OpenAIProfileGenerator:
    def __init__(self, api_key):
        openai.api_key = api_key
    
    def generate_profile(self, document_processor, bert_features, elo_insights):
        """Generate a comprehensive profile using OpenAI's API"""
        # Prepare the prompt
        prompt = self._prepare_profile_prompt(document_processor, bert_features, elo_insights)
        
        try:
            # Make API call to OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Adjust based on available models
                messages=[
                    {"role": "system", "content": "You are a seasoned consultant for Model United Nations delegates, analyzing writing and argumentation style."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistent output
                max_tokens=4000,  # Adjust based on requirements
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Extract JSON response
            profile_json = response.choices[0].message.content
            
            # Parse and validate the JSON
            try:
                profile = json.loads(profile_json)
                return profile
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response from OpenAI")
                # Try to extract JSON if wrapped in markdown code blocks
                try:
                    json_match = re.search(r'```json\n(.*?)\n```', profile_json, re.DOTALL)
                    if json_match:
                        profile = json.loads(json_match.group(1))
                        return profile
                except:
                    pass
                
                # Return error structure
                return {
                    "error": "Failed to generate valid JSON profile",
                    "raw_response": profile_json
                }
                
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return {
                "error": f"OpenAI API error: {str(e)}",
                "status": "Failed to generate profile"
            }
    
    def _prepare_profile_prompt(self, document_processor, bert_features, elo_insights):
        """Prepare the prompt for OpenAI's API"""
        # Extract metadata
        metadata = document_processor.get_metadata()
        
        # Create a sample of documents and sentences to include in prompt
        doc_samples = []
        for doc in document_processor.documents[:3]:  # Limit to 3 docs to avoid token limits
            # Include basic metadata and a sample of sentences
            doc_info = {
                'type': doc['type'],
                'committee': doc['committee'],
                'topic': doc['topic'],
                'country': doc['country'],
                'year': doc['year'],
                'sentence_samples': []
            }
            
            # Include samples from each section
            sections = set(document_processor.sentences[i]['section'] for i in doc['sentences'])
            for section in sections:
                section_sentences = [document_processor.sentences[i] for i in doc['sentences'] 
                                    if document_processor.sentences[i]['section'] == section]
                if section_sentences:
                    # Take a sample of sentences from this section
                    sample = random.sample(section_sentences, min(5, len(section_sentences)))
                    doc_info['sentence_samples'].extend([{
                        'text': s['text'],
                        'section': s['section'],
                        'elo_rating': s['elo_rating'] if 'elo_rating' in s else None
                    } for s in sample])
            
            doc_samples.append(doc_info)
        
        # Format BERT features for inclusion
        bert_summary = {
            'document_level_features': bert_features[:3],  # First 3 docs
            'linguistic_highlights': {
                'formality': {
                    'high': [s['text'] for s in document_processor.sentences 
                            if s['features'].get('formality', 0) > 0.8][:3],
                    'low': [s['text'] for s in document_processor.sentences 
                           if s['features'].get('formality', 0) < 0.2][:3]
                },
                'complexity': {
                    'high': [s['text'] for s in document_processor.sentences 
                            if s['features'].get('complexity', 0) > 0.8][:3],
                    'low': [s['text'] for s in document_processor.sentences 
                           if s['features'].get('complexity', 0) < 0.2][:3]
                }
            }
        }
        
        # Assemble the complete prompt
        prompt = f"""
        I need you to analyze the writing and argumentation style of a Model UN delegate based on the following information:

        METADATA:
        Committees: {metadata['committees']}
        Topics: {metadata['topics']}
        Countries represented: {metadata['countries']}
        Time span: {metadata['time_span']}
        Number of documents: {metadata['document_count']}

        DOCUMENT SAMPLES:
        {json.dumps(doc_samples, indent=2)}

        LINGUISTIC ANALYSIS (BERT):
        {json.dumps(bert_summary, indent=2)}

        ELO STYLE PREFERENCES:
        {json.dumps(elo_insights, indent=2)}

        Based on this information, create a comprehensive JSON profile following this structure:

        ```json
        {
          "delegateProfile": {
            "summary": "Executive summary of delegate's style",
            "committees": ["List of committees"],
            "topicAreas": ["Topics addressed"],
            "contextualMetadata": {
              "timespan": "Period covered",
              "countryPositions": ["Countries represented"]
            }
          },
          "linguisticPatterns": {
            "vocabularyProfile": {
              "diversity": 0-10 scale,
              "complexity": 0-10 scale,
              "formalityLevel": 0-10 scale,
              "commonPhrases": ["Frequently used phrases"],
              "distinctiveTerminology": ["Specialized terms frequently used"]
            },
            "sentenceStructure": {
              "averageLength": "Short/Medium/Long with numeric value",
              "preferredStructures": ["Simple", "Complex", "Compound"],
              "paragraphOrganization": "Description of how paragraphs are organized",
              "transitionTechniques": ["How ideas are connected"]
            },
            "stylisticDevices": {
              "rhetoricalDevices": ["Metaphors", "Analogies etc. used"],
              "toneProfile": ["Authoritative", "Conciliatory", "etc."],
              "voicePreference": "Active vs Passive ratio",
              "emphasisTechniques": ["How emphasis is created"]
            }
          },
          "cognitiveFrameworks": {
            "epistemologicalApproach": {
              "evidenceThreshold": "How delegate validates knowledge",
              "sourceCredibility": "How sources are evaluated",
              "empiricalVsTheoretical": 0-10 scale (0:purely empirical, 10:purely theoretical)
            },
            "reasoningModalities": {
              "dominantReasoning": ["Deductive", "Inductive", "Analogical"],
              "counterargumentApproach": "How opposing views are addressed",
              "contingencyPlanning": "How uncertainties are handled"
            },
            "problemFraming": {
              "scopeDefinition": "How problems are bounded",
              "causalAttribution": "Individual vs Systemic approach",
              "stakeholderPrioritization": "Which stakeholders are centered",
              "timeframeOrientation": "Short-term vs Long-term focus"
            }
          },
          "argumentativeStrategies": {
            "evidenceUsage": {
              "preferredEvidence": ["Statistics", "Historical", "Case studies", "etc."],
              "citationPatterns": "How sources are integrated",
              "qualitativeVsQuantitative": 0-10 scale
            },
            "persuasiveTechniques": {
              "emotionalAppeals": ["Types of emotional appeals used"],
              "authorityFraming": "How authority is leveraged",
              "urgencyTactics": "How necessity/urgency is created",
              "ethicalFrameworks": ["Rights-based", "Utilitarian", "etc."]
            },
            "solutionApproaches": {
              "preferredSolutions": ["Bilateral", "Multilateral", "Sanctions", "etc."],
              "scopeOrientation": "Short-term vs Long-term balance",
              "implementationFocus": "What aspects of implementation are emphasized",
              "fundingApproaches": ["How resources are allocated"]
            }
          },
          "uniqueStyleFingerprint": {
            "distinctiveElements": {
              "linguisticQuirks": ["Unusual phrasing or structures"],
              "signaturePhrases": ["Repeated distinctive phrases"],
              "openingTechniques": "How arguments typically begin",
              "closingStrategies": "How arguments typically conclude"
            },
            "implicitPatterns": {
              "underlyingValues": ["Core values evident in argumentation"],
              "assumptionPatterns": ["Unstated assumptions frequently made"],
              "blindSpots": ["Areas consistently overlooked"]
            }
          },
          "applicationGuidance": {
            "replicationStrategies": {
              "argumentFrameworks": ["Templates for argument construction"],
              "adaptationGuidelines": "How to adapt style to new topics",
              "improvementSuggestions": ["Areas where style could be enhanced"]
            },
            "effectivenessMetrics": {
              "strengths": ["Most effective aspects of style"],
              "contextualLimitations": ["When this style might be less effective"],
              "appropriateVenues": ["Where this style would be most persuasive"]
            }
          }
        }
        ```

        Ensure your response is ONLY valid JSON, with no additional text before or after.
        """
        
        return prompt

# ------------------------------------------------------
# INTEGRATED PROFILE SYSTEM
# ------------------------------------------------------

class IntegratedProfileSystem:
    def __init__(self, openai_api_key):
        self.document_processor = DocumentProcessor()
        self.bert_analyzer = BertLinguisticAnalyzer(bert_model, tokenizer, device)
        self.elo_rater = EloStyleRater()
        self.profile_generator = OpenAIProfileGenerator(openai_api_key)
        
    def add_document(self, document_text, document_type, committee, topic, country, year):
        """Add a document to the system"""
        return self.document_processor.add_document(
            document_text, document_type, committee, topic, country, year
        )
        
    def analyze_documents(self):
        """Run BERT analysis on all documents"""
        self.bert_analyzer.analyze_document(self.document_processor)
        bert_features = self.bert_analyzer.get_document_level_features(self.document_processor)
        return bert_features
    
    def get_comparison_pairs(self, count=5):
        """Get sentence pairs for style comparison"""
        return self.document_processor.get_comparison_pairs(count)
    
    def record_comparison(self, winner_id, loser_id):
        """Record the result of a style comparison"""
        self.elo_rater.update_ratings(winner_id, loser_id, self.document_processor)
        
    def generate_profile(self):
        """Generate the complete integrated profile"""
        # Validate sufficient data
        if len(self.document_processor.documents) < CONFIG['min_documents_required']:
            return {
                "error": f"Insufficient documents. Need at least {CONFIG['min_documents_required']}."
            }
        
        # Get BERT features
        bert_features = self.bert_analyzer.get_document_level_features(self.document_processor)
        
        # Get ELO insights
        elo_insights = self.elo_rater.get_style_insights(self.document_processor)
        
        # Generate complete profile
        profile = self.profile_generator.generate_profile(
            self.document_processor, bert_features, elo_insights
        )
        
        return profile
    
    def get_metadata(self):
        """Get document metadata"""
        return self.document_processor.get_metadata()

# ------------------------------------------------------
# FLASK ROUTES
# ------------------------------------------------------

# Initialize the integrated system
profile_system = IntegratedProfileSystem(os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

@app.route('/api/documents', methods=['POST'])
def add_document():
    """API endpoint to add a document"""
    data = request.json
    
    # Validate required fields
    required_fields = ['text', 'type', 'committee', 'topic', 'country', 'year']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({
            'error': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    # Add document to the system
    doc_id = profile_system.add_document(
        data['text'], data['type'], data['committee'], 
        data['topic'], data['country'], data['year']
    )
    
    return jsonify({
        'success': True,
        'doc_id': doc_id,
        'message': 'Document added successfully'
    })

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """API endpoint to get document metadata"""
    return jsonify(profile_system.get_metadata())

@app.route('/api/analyze', methods=['POST'])
def analyze_documents():
    """API endpoint to trigger document analysis"""
    bert_features = profile_system.analyze_documents()
    
    return jsonify({
        'success': True,
        'feature_count': len(bert_features),
        'message': 'Documents analyzed successfully'
    })

@app.route('/api/comparison-pairs', methods=['GET'])
def get_comparison_pairs():
    """API endpoint to get sentence pairs for comparison"""
    count = request.args.get('count', 5, type=int)
    pairs = profile_system.get_comparison_pairs(count)
    
    # Get the actual sentence text
    formatted_pairs = []
    for pair in pairs:
        s1 = next(s for s in profile_system.document_processor.sentences if s['id'] == pair[0])
        s2 = next(s for s in profile_system.document_processor.sentences if s['id'] == pair[1])
        
        formatted_pairs.append({
            'pair_id': f"{pair[0]}-{pair[1]}",
            'sentence1': {
                'id': s1['id'],
                'text': s1['text'],
                'doc_id': s1['doc_id'],
                'section': s1['section']
            },
            'sentence2': {
                'id': s2['id'],
                'text': s2['text'],
                'doc_id': s2['doc_id'],
                'section': s2['section']
            }
        })
    
    return jsonify({
        'pairs': formatted_pairs
    })

@app.route('/api/record-comparison', methods=['POST'])
def record_comparison():
    """API endpoint to record comparison result"""
    data = request.json
    
    # Validate required fields
    if 'winner_id' not in data or 'loser_id' not in data:
        return jsonify({
            'error': 'Missing winner_id or loser_id'
        }), 400
    
    # Record comparison
    profile_system.record_comparison(data['winner_id'], data['loser_id'])
    
    return jsonify({
        'success': True,
        'message': 'Comparison recorded successfully'
    })

@app.route('/api/generate-profile', methods=['POST'])
def generate_profile():
    """API endpoint to generate the complete profile"""
    profile = profile_system.generate_profile()
    
    return jsonify(profile)

if __name__ == '__main__':
    app.run(debug=True)