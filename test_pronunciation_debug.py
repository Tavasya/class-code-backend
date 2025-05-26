import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from app.pubsub.webhooks.analysis_webhook import AnalysisWebhook
import json
import base64

@pytest.fixture
def analysis_webhook():
    """Create an AnalysisWebhook instance for testing"""
    return AnalysisWebhook()

def create_mock_request(message_data):
    """Create a mock FastAPI request with PubSub message format"""
    # Encode the message data as PubSub would
    message_json = json.dumps(message_data)
    encoded_data = base64.b64encode(message_json.encode('utf-8')).decode('utf-8')
    
    pubsub_message = {
        "message": {
            "data": encoded_data,
            "messageId": "test-123",
            "publishTime": "2024-01-01T00:00:00.000Z"
        }
    }
    
    # Create mock request
    request = MagicMock(spec=Request)
    request.json = AsyncMock(return_value=pubsub_message)
    return request

@pytest.mark.asyncio
async def test_pronunciation_webhook_with_dict(analysis_webhook):
    """Test pronunciation webhook with correct dict format"""
    # Expected dict format
    pronunciation_result = {
        "status": "success",
        "word_details": [
            {"word": "hello", "accuracy_score": 85},
            {"word": "world", "accuracy_score": 90}
        ]
    }
    
    message_data = {
        "question_number": 1,
        "submission_url": "test_dict",
        "result": pronunciation_result,
        "transcript": "hello world",
        "total_questions": 1
    }
    
    request = create_mock_request(message_data)
    
    # Mock the fluency analysis function
    with pytest.mock.patch('app.pubsub.webhooks.analysis_webhook.get_fluency_coherence_analysis') as mock_fluency:
        mock_fluency.return_value = {"fluency_score": 85}
        
        result = await analysis_webhook.handle_pronunciation_done_webhook(request)
        
        # Should succeed
        assert result["status"] == "success"
        # Should call fluency analysis with word_details
        mock_fluency.assert_called_once()
        args, kwargs = mock_fluency.call_args
        assert len(args[1]) == 2  # word_details should have 2 items

@pytest.mark.asyncio
async def test_pronunciation_webhook_with_list(analysis_webhook):
    """Test pronunciation webhook with problematic list format"""
    # Problematic list format (this is what's causing the error)
    pronunciation_result = [
        {"word": "hello", "accuracy_score": 85},
        {"word": "world", "accuracy_score": 90}
    ]
    
    message_data = {
        "question_number": 1,
        "submission_url": "test_list",
        "result": pronunciation_result,
        "transcript": "hello world",
        "total_questions": 1
    }
    
    request = create_mock_request(message_data)
    
    # Mock the fluency analysis function
    with pytest.mock.patch('app.pubsub.webhooks.analysis_webhook.get_fluency_coherence_analysis') as mock_fluency:
        mock_fluency.return_value = {"fluency_score": 85}
        
        result = await analysis_webhook.handle_pronunciation_done_webhook(request)
        
        # Should still succeed with our defensive fix
        assert result["status"] == "success"
        # Should call fluency analysis with empty word_details (defensive behavior)
        mock_fluency.assert_called_once()
        args, kwargs = mock_fluency.call_args
        assert len(args[1]) == 0  # word_details should be empty due to defensive handling

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 