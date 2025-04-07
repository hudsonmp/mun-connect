"""
Prompt templates for different MUN-Connect tasks.
These templates should be used with the AIInterface.generate_with_template method.
"""

# Background Guide Processing Templates

SUMMARY_TEMPLATE = """
Given the following section from a Model UN background guide about ${topic}, 
create a concise summary that:
1. Identifies the key issues presented (maximum 3)
2. Extracts relevant historical context
3. Highlights the current international position
4. Notes any specific committee expectations

Format the output as follows:
KEY ISSUES:
- Issue 1
- Issue 2
- Issue 3

HISTORICAL CONTEXT:
[2-3 sentence summary]

CURRENT POSITION:
[2-3 sentence summary]

COMMITTEE EXPECTATIONS:
[1-2 sentence summary]

Section text:
${text}
"""

JSON_GENERATION_TEMPLATE = """
Based on the following background guide section, create a structured JSON object that captures:
1. Main topic and subtopics
2. Key stakeholders and their positions
3. Relevant historical events
4. Current challenges and opportunities
5. Possible solutions or approaches

Use the following JSON structure:
{
  "topic": "Main topic name",
  "subtopics": [
    {"name": "Subtopic 1", "description": "Brief description"},
    {"name": "Subtopic 2", "description": "Brief description"}
  ],
  "stakeholders": [
    {"entity": "Stakeholder 1", "position": "Brief position summary"},
    {"entity": "Stakeholder 2", "position": "Brief position summary"}
  ],
  "historical_context": [
    {"event": "Event 1", "year": "YYYY", "significance": "Brief explanation"},
    {"event": "Event 2", "year": "YYYY", "significance": "Brief explanation"}
  ],
  "current_challenges": [
    {"challenge": "Challenge 1", "description": "Brief description"},
    {"challenge": "Challenge 2", "description": "Brief description"}
  ],
  "possible_approaches": [
    {"approach": "Approach 1", "description": "Brief description"},
    {"approach": "Approach 2", "description": "Brief description"}
  ]
}

Ensure the JSON is valid and properly formatted.

Background guide section:
${text}
"""

# Mind Map Generation Templates

MIND_MAP_GENERATION_TEMPLATE = """
Create a mind map structure based on the following background guide content.
Identify the central topic and branch out to subtopics, ensuring relationships are clear.

Guidelines:
1. The central node should be the main committee topic
2. First-level nodes should be major subtopics
3. Second-level nodes should be specific issues or considerations
4. Include relevant stakeholders, historical context, and potential solutions
5. Indicate connections between different subtopics where relevant

Format the output as a JSON structure with the following format:
{
  "central_topic": {
    "title": "Main Topic",
    "description": "Brief description"
  },
  "main_branches": [
    {
      "id": "branch1",
      "title": "Major Subtopic 1",
      "description": "Brief description",
      "children": [
        {
          "id": "branch1_1",
          "title": "Specific Issue 1.1",
          "description": "Brief description"
        }
      ]
    }
  ],
  "connections": [
    {
      "source": "branch1",
      "target": "branch2",
      "description": "How these topics relate"
    }
  ]
}

Background guide content:
${content}
"""

# Style Analysis Templates

STYLE_ANALYSIS_TEMPLATE = """
Analyze the following MUN position paper for writing style characteristics.
Focus specifically on:
1. Formality level (scale 1-5)
2. Persuasive techniques used
3. Evidence types preferred
4. Sentence complexity metrics
5. Key vocabulary patterns

Format results as a JSON object with the following structure:
{
  "formality_level": 4,
  "persuasive_techniques": ["appeals to authority", "statistical evidence", "moral arguments"],
  "evidence_types": {
    "statistics": 0.4,
    "historical_examples": 0.3,
    "expert_quotes": 0.2,
    "case_studies": 0.1
  },
  "sentence_complexity": {
    "average_length": 24.5,
    "complex_sentence_ratio": 0.6,
    "passive_voice_ratio": 0.25
  },
  "vocabulary_patterns": {
    "formal_terms": ["furthermore", "consequently", "therefore"],
    "technical_terms": ["bilateral agreement", "sovereignty", "jurisdiction"],
    "emotional_terms": ["urgent", "critical", "essential"]
  }
}

Position paper:
${text}
"""

POSITION_PAPER_GENERATION_TEMPLATE = """
Create a Model UN position paper for ${country} on the topic of ${topic}.
The paper should match the following style characteristics:
- Formality level: ${formality_level}/5
- Preferred persuasive techniques: ${persuasive_techniques}
- Evidence types: ${evidence_types}
- Sentence complexity: ${sentence_complexity}
- Key vocabulary patterns: ${vocabulary_patterns}

Use the following structure:
1. Introduction to the country's position
2. Historical context and country's involvement
3. Current policies and initiatives
4. Proposed solutions and approach
5. Conclusion

Background information:
${background_info}
""" 