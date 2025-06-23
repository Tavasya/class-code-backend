#!/usr/bin/env python3

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def test_client():
    """Create FastAPI test client"""
    return TestClient(app)

@pytest.fixture(scope="function")
def mock_external_services():
    """Mock all external services to avoid real API calls during tests"""
    
    mocks = {}
    
    # Mock aiohttp sessions for OpenAI API calls
    with patch('aiohttp.ClientSession') as mock_session:
        # Create mock response for OpenAI API
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": '{"corrections": [], "grade": 85}'}}]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Mock session.post to return our mock response
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value = mock_response
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        mocks['aiohttp'] = mock_session
        
        # Mock Pub/Sub Client for submission service
        with patch('app.services.submission_service.PubSubClient') as mock_pubsub:
            mock_instance = MagicMock()
            mock_instance.publish_message_by_name.return_value = "test-message-id"
            mock_pubsub.return_value = mock_instance
            mocks['pubsub'] = mock_pubsub
            
            yield mocks

@pytest.fixture
def sample_submission_data():
    """Sample submission request data"""
    return {
        "audio_urls": [
            "https://example.com/audio1.mp3",
            "https://example.com/audio2.mp3"
        ],
        "submission_url": "https://example.com/submission/test-123"
    }

@pytest.fixture  
def sample_vocabulary_text():
    """Sample text for vocabulary analysis"""
    return "The cat sat on the sophisticated velvet chair"

@pytest.fixture
def sample_grammar_text():
    """Sample text with grammar errors"""
    return "I are going to the store yesterday. Me and him was talking about it."

@pytest.fixture
def pubsub_message_format():
    """Helper to format data as Pub/Sub message"""
    import base64
    import json
    
    def format_message(data):
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
        return {
            "message": {
                "data": encoded_data,
                "messageId": "test-message-id",
                "publishTime": "2023-01-01T00:00:00.000Z"
            }
        }
    return format_message 