# Mind Map Generator

This module provides functionality to generate committee-specific mind maps for Model UN delegates. It creates dynamic, customized mind maps based on background guides, country contexts, and delegate profiles.

## Features

- **Base Mind Map Generation**: Extracts topics and relationships from committee background guides.
- **Country-Specific Customization**: Enriches the mind map with country-specific relevance, annotations, and highlights.
- **Indexing for Paper Generation**: Creates searchable indexes for efficient retrieval during position paper generation.
- **Dual Output Formats**: Generates both research-focused JSON (for backend) and visualization-ready JSON (for frontend).

## API Endpoints

### Generate Base Mind Map
- **URL**: `/api/mind-map/generate-base`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "background_guide_content": "Full text of the background guide",
    "session_id": "Optional session ID"
  }
  ```
- **Response**: Base mind map JSON with topics and connections.

### Customize Mind Map
- **URL**: `/api/mind-map/customize`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "session_id": "Session ID from generate-base",
    "country": "Country name",
    "delegate_profile": {},
    "base_mind_map": {}  # Optional if already cached
  }
  ```
- **Response**: Customized mind map with research and visualization JSONs.

### Index Mind Map
- **URL**: `/api/mind-map/index`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "session_id": "Session ID from customize",
    "research_json": {}  # Optional if already cached
  }
  ```
- **Response**: Index information for the mind map.

### Search Mind Map
- **URL**: `/api/mind-map/search`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "session_id": "Session ID from index",
    "query": "The search query",
    "k": 5  # Optional: number of results to return
  }
  ```
- **Response**: Search results with relevant content.

### Generate for Paper
- **URL**: `/api/mind-map/generate-for-paper`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "background_guide_content": "Full text of the background guide",
    "country": "Country name",
    "delegate_profile": {},
    "session_id": "Optional session ID"
  }
  ```
- **Response**: Complete mind map for paper generation (combines all previous steps).

### Get Mind Map
- **URL**: `/api/mind-map/<session_id>`
- **Method**: `GET`
- **Response**: The mind map data for the specified session.

### Delete Mind Map
- **URL**: `/api/mind-map/<session_id>`
- **Method**: `DELETE`
- **Response**: Confirmation of deletion.

## JSON Structure

### Base Mind Map
```json
{
  "title": "Committee Background Guide",
  "description": "Base mind map generated from committee background guide",
  "created_at": "2023-04-06T10:30:00.000Z",
  "topics": [
    {
      "title": "Topic Title",
      "description": "Topic description",
      "subtopics": [
        {
          "title": "Subtopic Title",
          "description": "Subtopic description"
        }
      ]
    }
  ],
  "connections": [
    {
      "source": 0,
      "target": 1,
      "strength": 0.85,
      "description": "Related concepts: Topic A and Topic B"
    }
  ]
}
```

### Research JSON
The research JSON extends the base mind map with:
- Relevance scores for each topic
- Detailed annotations with quotes, policy notes, etc.
- Historical context information
- Research notes for each topic and subtopic
- Metadata and sources for citations

### Visualization JSON
The visualization JSON provides a simplified format for frontend rendering:
```json
{
  "title": "Committee Background Guide",
  "nodes": [
    {
      "id": "center",
      "label": "Committee Background Guide",
      "type": "central",
      "size": 30,
      "color": "#4A90E2"
    },
    {
      "id": "topic_0",
      "label": "Topic Title",
      "type": "topic",
      "relevance": 8,
      "size": 20,
      "color": "#7FBA00",
      "highlighted": true,
      "description": "Topic description"
    }
  ],
  "links": [
    {
      "source": "center",
      "target": "topic_0",
      "value": 2
    }
  ]
}
```

## Testing

To test the mind map functionality, run:

```bash
./run_test.sh
```

This will:
1. Generate a base mind map from the sample background guide
2. Customize it for France
3. Index the mind map
4. Test the search functionality
5. Output results to JSON files

## Requirements

See `requirements.txt` for dependencies. Key requirements:
- Python 3.8+
- Flask
- PyTorch
- Transformers
- FAISS for vector search
- OpenAI API key (for customization) 