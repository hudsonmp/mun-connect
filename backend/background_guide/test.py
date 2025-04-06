#!/usr/bin/env python3
"""
Integration test for the background guide processor.

This script tests the basic functionality of the background guide processor
with a sample text document.
"""

import os
import sys
import tempfile
from pathlib import Path

from processor import BackgroundGuideProcessor

def create_sample_text():
    """Create a sample text file for testing."""
    text = """
BACKGROUND GUIDE: UNITED NATIONS SECURITY COUNCIL

INTRODUCTION

The United Nations Security Council (UNSC) is one of the six principal organs of the United Nations and is charged with ensuring international peace and security. It is the only UN body with the authority to issue binding resolutions to member states. The Security Council also has the power to establish peacekeeping operations, enact international sanctions, and authorize military action.

COMMITTEE STRUCTURE

The Security Council consists of fifteen members, of which five are permanent members with veto power: China, France, Russia, the United Kingdom, and the United States. The remaining ten members are elected by the General Assembly for two-year terms. Decisions on substantive matters require nine votes, including the concurring votes of all permanent members.

TOPIC A: ADDRESSING THE CONFLICT IN EASTERN EUROPE

Historical Context

The conflict in Eastern Europe has deep historical roots dating back to the collapse of the Soviet Union in 1991. The region has seen numerous territorial disputes, separatist movements, and ethnic tensions since then. The current situation has escalated since 2014, with increased military activity and violations of internationally recognized borders.

Current Situation

As of 2023, the conflict continues to pose a significant threat to international peace and security. Several key developments include:

1. Ongoing military operations in contested regions
2. Humanitarian crisis affecting over 3 million civilians
3. Allegations of human rights violations by all parties
4. Disruption of global energy supplies and food security

The Security Council has held numerous emergency sessions on this issue but has been unable to reach consensus due to the divergent positions of permanent members.

International Response

The international community has responded in various ways:

a) Economic sanctions imposed by Western nations
b) Humanitarian aid coordinated by UN agencies
c) Diplomatic negotiations through the Minsk Process
d) Observer missions by the OSCE

TOPIC B: CLIMATE SECURITY

Background

Climate change has increasingly been recognized as a threat multiplier for international security. Rising temperatures, changing precipitation patterns, and more frequent extreme weather events exacerbate existing political and social tensions, particularly in fragile states and regions already facing governance challenges.

In 2007, the Security Council held its first debate on the implications of climate change for security. Since then, the Council has addressed climate-related security risks in various country-specific and regional contexts.

Key Security Implications

Climate change poses several distinct challenges to international security:

- Resource scarcity leading to competition and conflict
- Migration and displacement due to environmental degradation
- Increased vulnerability of critical infrastructure
- Threats to territorial integrity of small island developing states

Security Council's Role

The Council has several tools at its disposal to address climate security challenges:

1. Early warning and risk assessment
2. Preventive diplomacy and mediation
3. Peacekeeping operations with environmental mandates
4. Coordination with other UN bodies

DEBATE PROCEDURES

The Security Council follows specific procedures that differ somewhat from other UN committees:

- Each member state has one vote
- Permanent members possess veto power on substantive matters
- Procedural matters require nine affirmative votes
- Speaking time is typically limited to 5 minutes per delegation

Delegates are expected to thoroughly research their country's position on each topic and be prepared to engage in intensive negotiation. Draft resolutions should address both immediate crisis management and long-term solutions.

REFERENCES

1. United Nations Charter, Chapter V: The Security Council
2. Security Council Report, "Climate Change: A Root Cause of Security Threats" (2021)
3. International Crisis Group, "Eastern Europe Conflict Briefing" (2023)
4. IPCC Sixth Assessment Report (2022)
5. UN Secretary-General's Report on Climate Security (2020)
    """
    
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix='.txt')
    with os.fdopen(fd, 'w') as f:
        f.write(text)
    
    return path

def test_processor():
    """Test the basic functionality of the background guide processor."""
    print("Creating sample text document...")
    file_path = create_sample_text()
    
    try:
        print("Initializing processor...")
        processor = BackgroundGuideProcessor(
            use_openai_for_summary=False,  # Use local models for test
            use_aws_model=False,
            output_dir="test_output"
        )
        
        print("Processing document...")
        results = processor.process_file(file_path)
        
        # Basic assertions
        assert len(results.get('segments', [])) > 0, "No segments found"
        assert len(results.get('json_files', {})) > 0, "No JSON files generated"
        
        # Test query
        query = "climate change security implications"
        print(f"Testing query: '{query}'")
        context = processor.retrieve_context_for_query(query)
        
        assert len(context) > 0, "No context retrieved for query"
        
        print("\nTest successful!")
        print(f"Processed {len(results.get('segments', []))} segments")
        print(f"Generated {len(results.get('json_files', {}))} JSON files")
        print(f"Retrieved {len(context)} context segments for query")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up
        os.remove(file_path)
    
    return 0

if __name__ == "__main__":
    sys.exit(test_processor()) 