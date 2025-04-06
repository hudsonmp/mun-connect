import os
import json
import sys
import logging
from supabase import create_client

# Add the parent directory to the path so we can import the DelegateProfile
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from user_context.delegate_profile import DelegateProfile

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample function to simulate a style analysis result
def generate_sample_style_analysis():
    return {
        "linguisticPatterns": {
            "vocabulary": {
                "diversity": {
                    "unique_words": 520,
                    "total_words": 950,
                    "diversity_ratio": 0.55
                },
                "formality": {
                    "score": 0.78,
                    "assessment": "high"
                }
            },
            "sentenceStructure": {
                "sentence_metrics": {
                    "length": {
                        "average": 22.5,
                        "variance": 45.2
                    },
                    "complexity": {
                        "subordinate_clauses_ratio": 0.35
                    }
                }
            },
            "stylisticDevices": {
                "rhetorical_devices": {
                    "counts": {
                        "total": 12,
                        "metaphor": 3,
                        "parallelism": 5,
                        "rhetoric_question": 4
                    }
                }
            }
        },
        "cognitiveFrameworks": {
            "reasoningPatterns": {
                "reasoning_approaches": {
                    "logical": 0.65,
                    "emotional": 0.25,
                    "ethical": 0.10
                },
                "dominant_reasoning": "logical"
            }
        },
        "argumentativeStrategies": {
            "persuasiveTechniques": {
                "appeals": {
                    "logos": 0.70,
                    "ethos": 0.20,
                    "pathos": 0.10
                },
                "dominant_appeal": "logos"
            }
        }
    }

# Sample function to simulate a sentiment analysis result
def generate_sample_sentiment_analysis():
    return {
        "sentiment": {
            "compound": 0.42,
            "positive": 0.62,
            "neutral": 0.30,
            "negative": 0.08,
            "assessment": "moderately positive"
        },
        "emotion_distribution": {
            "confidence": 0.40,
            "analytical": 0.35,
            "concern": 0.15,
            "uncertainty": 0.10
        }
    }

# Sample function to simulate a comparison analysis result
def generate_sample_comparison_analysis():
    return {
        "similarity_scores": {
            "positive_achievements": 0.82,
            "regional_cooperation": 0.65,
            "economic_focus": 0.45,
            "humanitarian_concern": 0.38,
            "diplomatic_neutral": 0.52,
            "historical_context": 0.33,
            "sovereignty_emphasis": 0.71,
            "legal_framework": 0.59
        },
        "most_similar_approach": "positive_achievements",
        "least_similar_approach": "historical_context"
    }

def main():
    # Initialize Supabase client
    supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Missing Supabase credentials.")
        logger.error("Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables.")
        return
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # ⚠️ IMPORTANT: DEMO CODE ONLY ⚠️
        # In production code, ALWAYS retrieve the user_id from your authentication system
        # For example:
        # user_id = supabase.auth.get_user().user.id
        #
        # NEVER hardcode a user ID in production code as it creates security risks
        # This fixed ID is for demonstration purposes only
        user_id = "00000000-0000-0000-0000-000000000000"  # Using a clearly fake UUID format
        logger.warning("Using a demo user ID. This should never be done in production!")
        
        # Initialize DelegateProfile
        delegate_profile = DelegateProfile(user_id, supabase)
        
        # Store different analyses for different document types
        try:
            # Store style analysis for position paper
            style_result = delegate_profile.store_analysis_result(
                document_type="position_paper",
                json_content=generate_sample_style_analysis(),
                analysis_type="style"
            )
            logger.info(f"Style analysis stored: {style_result['operation']}")
            
            # Store sentiment analysis for position paper
            sentiment_result = delegate_profile.store_analysis_result(
                document_type="position_paper",
                json_content=generate_sample_sentiment_analysis(),
                analysis_type="sentiment"
            )
            logger.info(f"Sentiment analysis stored: {sentiment_result['operation']}")
            
            # Store comparison analysis for position paper
            comparison_result = delegate_profile.store_analysis_result(
                document_type="position_paper",
                json_content=generate_sample_comparison_analysis(),
                analysis_type="comparison"
            )
            logger.info(f"Comparison analysis stored: {comparison_result['operation']}")
            
            # Store style analysis for opening speech
            speech_style_result = delegate_profile.store_analysis_result(
                document_type="opening_speech",
                json_content=generate_sample_style_analysis(),
                analysis_type="style"
            )
            logger.info(f"Opening speech style analysis stored: {speech_style_result['operation']}")
            
            # Retrieve all stored analyses
            all_analyses = delegate_profile.get_all_analysis_results()
            logger.info(f"Retrieved {len(all_analyses)} analyses")
            
            # Generate consolidated profile
            profile = delegate_profile.generate_consolidated_profile()
            
            # Print the consolidated profile in a readable format
            logger.info("\nConsolidated Delegate Profile:")
            print(json.dumps(profile, indent=2))
            
            # Print specific elements from the profile
            logger.info("\nOverall Characteristics:")
            for key, value in profile["overall_characteristics"].items():
                logger.info(f"  {key}: {value}")
            
            logger.info("\nWriting Fingerprint (Signature Patterns):")
            for pattern in profile["writing_fingerprint"]["signature_patterns"]:
                logger.info(f"  - {pattern}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
    
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")

if __name__ == "__main__":
    main() 