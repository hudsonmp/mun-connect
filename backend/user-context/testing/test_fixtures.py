"""
Test fixtures for DelegateAnalyzer.

This module provides mock data and test fixtures for testing DelegateAnalyzer
in various environments including AWS.
"""

import os
import json
import tempfile
from typing import Dict, Any, List, Optional

# Mock country database path for testing
TEST_COUNTRY_DB_PATH = os.path.join(tempfile.gettempdir(), "test_country_db.json")

# Mock test documents
TEST_DOCUMENTS = [
    {
        "id": "test_doc_1",
        "country": "United States",
        "committee": "Security Council",
        "text": """
        The United States strongly condemns the recent actions by rogue nations that threaten international peace and security.
        We believe in a rules-based international order where all nations must be held accountable for their actions.
        Our delegation proposes increased sanctions and monitoring mechanisms to ensure compliance with UN resolutions.
        We are committed to working with our allies to maintain security and stability across regions of concern.
        """
    },
    {
        "id": "test_doc_2",
        "country": "China",
        "committee": "Security Council",
        "text": """
        China emphasizes the importance of non-interference in sovereign affairs of member states.
        We believe diplomatic solutions must be prioritized over punitive measures that may escalate tensions.
        Our delegation calls for a balanced approach that respects the development paths chosen by individual nations.
        China remains committed to peaceful resolution of conflicts through dialogue and mutual respect.
        """
    },
    {
        "id": "test_doc_3",
        "country": "United States",
        "committee": "Human Rights Council",
        "text": """
        The United States reaffirms its commitment to protecting human rights worldwide.
        We urge all nations to uphold the Universal Declaration of Human Rights and ensure freedoms of speech, assembly, and religion.
        Our delegation proposes strengthening mechanisms for monitoring and reporting human rights violations.
        We stand ready to work with partner nations to advance human dignity and fundamental freedoms.
        """
    }
]

# Mock analysis results for faster testing
MOCK_STYLE_ANALYSIS = {
    "linguisticPatterns": {
        "vocabulary": {
            "diversity": {
                "unique_words": 45,
                "total_words": 78,
                "diversity_score": 0.58
            },
            "formality": {
                "score": 0.75,
                "formal_markers": ["strongly", "international", "delegation"],
                "informal_markers": []
            }
        },
        "sentenceStructure": {
            "sentence_metrics": {
                "count": 4,
                "length": {
                    "average": 19.5,
                    "min": 15,
                    "max": 25
                },
                "complexity_score": 0.68
            }
        },
        "stylisticDevices": {
            "rhetorical_devices": {
                "counts": {
                    "parallelism": 2,
                    "repetition": 1,
                    "total": 3
                }
            }
        }
    },
    "cognitiveFrameworks": {
        "reasoningPatterns": {
            "dominant_reasoning": "deductive",
            "reasoning_approaches": {
                "deductive": 0.65,
                "inductive": 0.25,
                "analogical": 0.1
            }
        }
    },
    "argumentativeStrategies": {
        "persuasiveTechniques": {
            "dominant_appeal": "logos",
            "appeal_scores": {
                "logos": 0.7,
                "ethos": 0.25,
                "pathos": 0.05
            }
        }
    }
}

MOCK_POSITION_ANALYSIS = {
    "overall_alignment": 0.78,
    "stance_analysis": {
        "overall_stance_alignment": 0.81
    },
    "linguistic_analysis": {
        "language_alignment_score": 0.75
    },
    "position_deviations": [
        "Slight deviation on economic sanctions approach",
        "Minor inconsistency on multilateral engagement"
    ],
    "assessment": {
        "strengths": [
            "Strong alignment with expected security positions",
            "Consistent use of diplomatic language"
        ],
        "areas_for_improvement": [
            "Could better emphasize bilateral relationships",
            "Consider more specific regional policy points"
        ],
        "specific_recommendations": [
            "Include more specific references to key allies",
            "Strengthen language on non-proliferation commitments"
        ]
    }
}

def create_test_country_db():
    """Create a test country database file"""
    data = {
        "United States": {
            "general_positions": [
                "Promotes democracy and human rights globally",
                "Advocates for free markets and international trade",
                "Emphasizes national sovereignty and security interests",
                "Supports strong military alliances like NATO"
            ],
            "security_council": [
                "Maintains strong stance against nuclear proliferation",
                "Advocates for interventions in humanitarian crises",
                "Supports sanctions against non-compliant regimes",
                "Emphasizes counterterrorism cooperation"
            ],
            "human_rights_council": [
                "Promotes individual liberties and freedoms",
                "Advocates for religious freedom worldwide",
                "Critical of human rights violations in authoritarian states",
                "Supports NGOs and civil society organizations"
            ]
        },
        "China": {
            "general_positions": [
                "Emphasizes non-interference in internal affairs",
                "Promotes economic development as a human right",
                "Advocates for multipolarity in global governance",
                "Focuses on South-South cooperation"
            ],
            "security_council": [
                "Opposes military interventions without host country consent",
                "Emphasizes diplomatic solutions to conflicts",
                "Cautious approach to sanctions and punitive measures",
                "Promotes developmental approach to security issues"
            ],
            "human_rights_council": [
                "Emphasizes economic and social rights",
                "Promotes right to development as fundamental",
                "Advocates cultural relativity in human rights",
                "Opposes 'politicization' of human rights issues"
            ]
        }
    }
    
    with open(TEST_COUNTRY_DB_PATH, 'w') as f:
        json.dump(data, f)
    
    return TEST_COUNTRY_DB_PATH

def get_mock_lambda_event(request_type="analyze_document", doc_index=0):
    """Get a mock Lambda event for testing"""
    if request_type == "analyze_document":
        return {
            "requestType": "analyze_document",
            "text": TEST_DOCUMENTS[doc_index]["text"],
            "country": TEST_DOCUMENTS[doc_index]["country"],
            "committee": TEST_DOCUMENTS[doc_index]["committee"]
        }
    elif request_type == "analyze_multiple_documents":
        return {
            "requestType": "analyze_multiple_documents",
            "documents": TEST_DOCUMENTS
        }
    else:
        return {
            "requestType": request_type
        }

def get_mock_s3_event(request_type="analyze_document", doc_index=0):
    """Get a mock Lambda event using S3 paths for testing"""
    if request_type == "analyze_document":
        return {
            "requestType": "analyze_document",
            "s3Path": f"s3://test-bucket/documents/{TEST_DOCUMENTS[doc_index]['id']}.txt",
            "country": TEST_DOCUMENTS[doc_index]["country"],
            "committee": TEST_DOCUMENTS[doc_index]["committee"]
        }
    elif request_type == "analyze_multiple_documents":
        return {
            "requestType": "analyze_multiple_documents",
            "documents": [
                {
                    "id": doc["id"],
                    "country": doc["country"],
                    "committee": doc["committee"],
                    "text": f"s3://test-bucket/documents/{doc['id']}.txt"
                }
                for doc in TEST_DOCUMENTS
            ]
        }
    else:
        return {
            "requestType": request_type
        }

class MockAnalyzer:
    """Mock analyzer class for testing with CPU-only variants"""
    
    def __init__(self):
        """Initialize mock analyzer"""
        pass
    
    def analyze_style(self, text, country, committee=None):
        """Return mock style analysis"""
        return MOCK_STYLE_ANALYSIS
    
    def analyze_position_alignment(self, text, country):
        """Return mock position analysis"""
        return MOCK_POSITION_ANALYSIS 