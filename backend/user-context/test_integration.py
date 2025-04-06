import os
import json
import sys
import uuid
import logging
from pathlib import Path

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger_setup = "Loaded environment variables from .env file"
except ImportError:
    logger_setup = "dotenv package not found, using system environment variables"

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(logger_setup)

# Check for Supabase
try:
    from supabase import create_client
except ImportError:
    logger.error("Supabase package not found. Please install it with: pip install supabase")
    sys.exit(1)

# Import DelegateProfile - using relative import
try:
    from delegate_profile import DelegateProfile, ValidationError, DatabaseError
    logger.info("Successfully imported DelegateProfile from current directory")
except ImportError:
    logger.error("Failed to import DelegateProfile from current directory")
    logger.info("Attempting alternative import method...")
    try:
        # Add the parent directory to the path
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from user_context.delegate_profile import DelegateProfile, ValidationError, DatabaseError
        logger.info("Successfully imported DelegateProfile using sys.path")
    except ImportError:
        logger.error("Could not import DelegateProfile. Please check file paths.")
        sys.exit(1)

# ---- Analysis Sample Functions ----

def generate_sample_style_analysis():
    """Generate a sample style analysis result."""
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

def generate_sample_sentiment_analysis():
    """Generate a sample sentiment analysis result."""
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

def generate_sample_comparison_analysis():
    """Generate a sample comparison analysis result."""
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

# ---- Test Functions ----

def check_environment():
    """Verify environment variables are set correctly."""
    supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Missing Supabase credentials.")
        logger.error("Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables.")
        logger.info("Use the following commands in your terminal:")
        logger.info("export NEXT_PUBLIC_SUPABASE_URL='your-supabase-url'")
        logger.info("export NEXT_PUBLIC_SUPABASE_ANON_KEY='your-supabase-anon-key'")
        return False
    
    logger.info("Environment variables found:")
    logger.info(f"NEXT_PUBLIC_SUPABASE_URL: {supabase_url[:8]}...{supabase_url[-4:]}")
    logger.info(f"NEXT_PUBLIC_SUPABASE_ANON_KEY: {supabase_key[:5]}...{supabase_key[-4:]}")
    return True

def test_supabase_connection():
    """Test connection to Supabase."""
    supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    try:
        logger.info("Testing Supabase connection...")
        supabase = create_client(supabase_url, supabase_key)
        
        # Simple test query
        response = supabase.table('delegate_analyses').select('count', count='exact').execute()
        
        # If we get here, the connection works
        logger.info(f"Supabase connection successful! Found {response.count if hasattr(response, 'count') else 'some'} records in delegate_analyses table.")
        return supabase
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return None

def test_delegate_profile(supabase):
    """Test DelegateProfile functionality."""
    # Generate a test user ID
    test_user_id = str(uuid.uuid4())
    logger.info(f"Testing with temporary user ID: {test_user_id}")
    
    try:
        # Initialize DelegateProfile
        delegate_profile = DelegateProfile(test_user_id, supabase)
        logger.info("DelegateProfile initialized successfully")
        
        # Test storing analyses
        logger.info("Testing store_analysis_result()...")
        
        # Store style analysis
        style_result = delegate_profile.store_analysis_result(
            document_type="position_paper",
            json_content=generate_sample_style_analysis(),
            analysis_type="style"
        )
        logger.info(f"Style analysis stored: {style_result['operation']}")
        
        # Store sentiment analysis
        sentiment_result = delegate_profile.store_analysis_result(
            document_type="position_paper",
            json_content=generate_sample_sentiment_analysis(),
            analysis_type="sentiment"
        )
        logger.info(f"Sentiment analysis stored: {sentiment_result['operation']}")
        
        # Store comparison analysis
        comparison_result = delegate_profile.store_analysis_result(
            document_type="position_paper",
            json_content=generate_sample_comparison_analysis(),
            analysis_type="comparison"
        )
        logger.info(f"Comparison analysis stored: {comparison_result['operation']}")
        
        # Test retrieving analyses
        logger.info("Testing get_all_analysis_results()...")
        all_analyses = delegate_profile.get_all_analysis_results()
        logger.info(f"Retrieved {len(all_analyses)} analyses")
        
        # Test getting analysis by type
        logger.info("Testing get_analysis_by_type()...")
        style_analyses = delegate_profile.get_analysis_by_type("style")
        logger.info(f"Retrieved {len(style_analyses)} style analyses")
        
        # Test getting analysis by document
        logger.info("Testing get_analysis_by_document()...")
        position_paper_analyses = delegate_profile.get_analysis_by_document("position_paper")
        logger.info(f"Retrieved {len(position_paper_analyses)} position paper analyses")
        
        # Test generating consolidated profile
        logger.info("Testing generate_consolidated_profile()...")
        profile = delegate_profile.generate_consolidated_profile()
        
        # Output the profile
        logger.info("\nGenerated Consolidated Delegate Profile:")
        print(json.dumps(profile, indent=2))
        
        if "overall_characteristics" in profile:
            logger.info("\nOverall Characteristics:")
            for key, value in profile["overall_characteristics"].items():
                logger.info(f"  {key}: {value}")
        
        if "writing_fingerprint" in profile and "signature_patterns" in profile["writing_fingerprint"]:
            logger.info("\nWriting Fingerprint (Signature Patterns):")
            for pattern in profile["writing_fingerprint"]["signature_patterns"]:
                logger.info(f"  - {pattern}")
        
        # Clean up - delete the test analyses
        logger.info("\nCleaning up test data...")
        for analysis in all_analyses:
            delete_result = delegate_profile.delete_analysis(analysis['id'])
            logger.info(f"Deleted analysis {analysis['id']}")
        
        return True
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return False
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def main():
    """Main test function to verify integration."""
    logger.info("=== MUN-Connect DelegateProfile Integration Test ===")
    
    # Check environment variables
    if not check_environment():
        return
    
    # Test Supabase connection
    supabase = test_supabase_connection()
    if not supabase:
        return
    
    # Test DelegateProfile
    success = test_delegate_profile(supabase)
    
    if success:
        logger.info("\n✅ Integration test completed successfully!")
        logger.info("The DelegateProfile class and supporting modules are working correctly.")
    else:
        logger.error("\n❌ Integration test failed.")
        logger.error("Please check the errors above and fix the issues.")

if __name__ == "__main__":
    main() 