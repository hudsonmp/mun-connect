import json
import pytest
from unittest import mock

@pytest.mark.api
def test_mind_map_endpoint_health(test_client):
    """Test the health endpoint of the mind map API."""
    response = test_client.get('/mind-map/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'

@pytest.mark.api
def test_generate_mind_map(test_client, sample_pdf_file, monkeypatch):
    """Test generating a mind map from a background guide."""
    # Mock the MindMapGenerator
    class MockMindMapGenerator:
        def generate_base_mind_map(self, background_guide_content):
            return {"topics": [{"title": "Test Topic"}]}
        
        def customize_mind_map(self, base_mind_map, country, delegate_profile, api_key=None):
            return {"topics": base_mind_map["topics"], "country": country}
    
    # Apply the mock
    monkeypatch.setattr(
        "backend.mind_map.api.MindMapGenerator", 
        MockMindMapGenerator
    )
    
    # Test the endpoint
    with open(sample_pdf_file, 'rb') as f:
        response = test_client.post(
            '/mind-map/generate',
            data={
                'file': (f, 'test_document.pdf'),
                'country': 'Sweden',
                'committee': 'Test Committee'
            },
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'topics' in data
    assert data['country'] == 'Sweden'

@pytest.mark.api
def test_search_mind_map(test_client, monkeypatch):
    """Test searching within a mind map."""
    # Mock the MindMapIndexer
    class MockMindMapIndexer:
        def search(self, query_embedding, session_id, k=5):
            return [{"title": "Test Result", "relevance": 0.9}]
    
    # Apply the mock
    monkeypatch.setattr(
        "backend.mind_map.api.MindMapIndexer", 
        MockMindMapIndexer
    )
    
    # Mock the embedding model
    def mock_generate_embedding(text):
        return [0.1] * 768  # Return a dummy embedding vector
    
    monkeypatch.setattr(
        "backend.mind_map.api.generate_embedding", 
        mock_generate_embedding
    )
    
    # Test the endpoint
    response = test_client.post(
        '/mind-map/search',
        json={
            'query': 'test query',
            'session_id': 'test-session'
        }
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'results' in data
    assert len(data['results']) > 0
    assert data['results'][0]['title'] == 'Test Result' 