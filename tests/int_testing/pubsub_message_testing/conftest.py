import pytest
import base64
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
from fastapi import Request
from app.pubsub.webhooks.analysis_webhook import AnalysisWebhook
from app.pubsub.webhooks.submission_webhook import SubmissionWebhook
from app.pubsub.webhooks.audio_webhook import AudioWebhook
from app.pubsub.webhooks.transcription_webhook import TranscriptionWebhook


@pytest.fixture
def mock_all_analysis_services():
    """Mock all expensive analysis services - use in 80% of tests"""
    with patch('app.services.pronunciation_service.PronunciationService') as mock_pronunciation, \
         patch('app.services.grammar_service.analyze_grammar') as mock_grammar, \
         patch('app.services.lexical_service.analyze_lexical_resources') as mock_lexical, \
         patch('app.services.fluency_service.get_fluency_coherence_analysis') as mock_fluency:
        
        # Configure mock returns with standardized format
        mock_pronunciation.return_value.analyze_pronunciation = AsyncMock(return_value={
            "grade": 85.5,
            "issues": [{"type": "pronunciation", "message": "Good pronunciation"}]
        })
        
        mock_grammar.return_value = {
            "grade": 78.2,
            "issues": [{"type": "grammar", "message": "Minor grammatical errors"}]
        }
        
        mock_lexical.return_value = {
            "grade": 82.1,
            "issues": [{"type": "lexical", "message": "Good vocabulary usage"}]
        }
        
        mock_fluency.return_value = {
            "grade": 80.0,
            "issues": [{"type": "fluency", "message": "Natural speaking pace"}]
        }
        
        yield {
            "pronunciation": mock_pronunciation,
            "grammar": mock_grammar,
            "lexical": mock_lexical,
            "fluency": mock_fluency
        }


@pytest.fixture
def mock_pubsub_client():
    """Mock PubSubClient to prevent actual message publishing"""
    # Create a mock instance that we'll inject into webhooks
    mock_instance = Mock()
    mock_instance.publish_message_by_name = Mock(return_value="mock-message-id")
    yield mock_instance


@pytest.fixture
def mock_database_service():
    """Mock database operations for testing"""
    with patch('app.services.database_service.DatabaseService') as mock_db:
        mock_instance = Mock()
        mock_instance.update_submission_results = Mock(return_value="mock-db-id")
        mock_db.return_value = mock_instance
        yield mock_instance


def create_base64_message(message_data: Dict[str, Any]) -> str:
    """Helper function to create base64 encoded message data"""
    json_data = json.dumps(message_data)
    return base64.b64encode(json_data.encode()).decode()


@pytest.fixture
def sample_pubsub_messages():
    """Pre-built Pub/Sub message formats for testing"""
    base_submission_data = {
        "submission_url": "test-pubsub-submission",
        "question_number": 1,
        "total_questions": 3
    }
    
    return {
        "student_submission": create_base64_message({
            "audio_urls": [
                "https://example.com/audio1.webm",
                "https://example.com/audio2.webm",
                "https://example.com/audio3.webm"
            ],
            "submission_url": "test-pubsub-submission",
            "total_questions": 3
        }),
        
        "audio_conversion_done": create_base64_message({
            **base_submission_data,
            "wav_path": "/tmp/test_audio.wav",
            "session_id": "test-session-123",
            "original_audio_url": "https://example.com/audio1.webm"
        }),
        
        "transcription_done": create_base64_message({
            **base_submission_data,
            "text": "This is a test transcript for analysis",
            "error": None,
            "audio_url": "https://example.com/audio1.webm"
        }),
        
        "question_analysis_ready": create_base64_message({
            **base_submission_data,
            "wav_path": "/tmp/test_audio.wav",
            "transcript": "This is a test transcript for analysis",
            "audio_url": "https://example.com/audio1.webm",
            "session_id": "test-session-123"
        }),
        
        "pronunciation_done": create_base64_message({
            **base_submission_data,
            "result": {"grade": 85.5, "issues": []},
            "transcript": "This is a test transcript for analysis"
        }),
        
        "grammar_done": create_base64_message({
            **base_submission_data,
            "result": {"grade": 78.2, "issues": []}
        }),
        
        "lexical_done": create_base64_message({
            **base_submission_data,
            "result": {"grade": 82.1, "issues": []}
        }),
        
        "fluency_done": create_base64_message({
            **base_submission_data,
            "result": {"grade": 80.0, "issues": []}
        }),
        
        "analysis_complete": create_base64_message({
            **base_submission_data,
            "analysis_results": {
                "pronunciation": {"grade": 85.5, "issues": []},
                "grammar": {"grade": 78.2, "issues": []},
                "lexical": {"grade": 82.1, "issues": []},
                "fluency": {"grade": 80.0, "issues": []},
                "original_audio_url": "https://example.com/audio1.webm",
                "transcript": "This is a test transcript for analysis"
            }
        }),
        
        "submission_analysis_complete": create_base64_message({
            "submission_url": "test-pubsub-submission",
            "total_questions": 3,
            "completed_questions": [1, 2, 3],
            "question_results": {
                "1": {
                    "pronunciation": {"grade": 85.5, "issues": []},
                    "grammar": {"grade": 78.2, "issues": []},
                    "lexical": {"grade": 82.1, "issues": []},
                    "fluency": {"grade": 80.0, "issues": []},
                    "original_audio_url": "https://example.com/audio1.webm",
                    "transcript": "This is a test transcript for analysis"
                }
            }
        })
    }


def create_mock_request(message_data: str, attributes: Dict[str, str] = None) -> Mock:
    """Create a mock FastAPI Request with Pub/Sub message format"""
    if attributes is None:
        attributes = {}
    
    request_body = {
        "message": {
            "data": message_data,
            "attributes": attributes,
            "messageId": "mock-message-id-123",
            "publishTime": "2024-01-01T12:00:00.000Z"
        }
    }
    
    mock_request = Mock(spec=Request)
    mock_request.json = AsyncMock(return_value=request_body)
    return mock_request


@pytest.fixture
def webhook_request_factory():
    """Factory to create mock FastAPI Request objects with Pub/Sub message format"""
    return create_mock_request


@pytest.fixture
def analysis_webhook(mock_pubsub_client):
    """Real AnalysisWebhook instance with mocked PubSubClient for testing"""
    webhook = AnalysisWebhook()
    # Replace the real client with our mock
    webhook.pubsub_client = mock_pubsub_client
    webhook.analysis_coordinator.pubsub_client = mock_pubsub_client
    return webhook


@pytest.fixture
def submission_webhook(mock_pubsub_client):
    """Real SubmissionWebhook instance with mocked PubSubClient for testing"""
    webhook = SubmissionWebhook()
    # Replace the real client with our mock
    webhook.pubsub_client = mock_pubsub_client
    return webhook


@pytest.fixture
def audio_webhook(mock_pubsub_client):
    """Real AudioWebhook instance with mocked PubSubClient for testing"""
    webhook = AudioWebhook()
    # Replace the real client with our mock
    webhook.pubsub_client = mock_pubsub_client
    return webhook


@pytest.fixture
def transcription_webhook(mock_pubsub_client):
    """Real TranscriptionWebhook instance with mocked PubSubClient for testing"""
    webhook = TranscriptionWebhook()
    # Replace the real client with our mock
    webhook.pubsub_client = mock_pubsub_client
    return webhook


@pytest.fixture
def test_submission_context():
    """Test submission context for Pub/Sub testing"""
    return {
        "submission_url": "test-pubsub-submission",
        "question_number": 1,
        "total_questions": 3,
        "audio_url": "https://example.com/test-audio.webm"
    }


@pytest.fixture
def results_store_cleanup():
    """Cleanup results store after each test"""
    yield
    # Cleanup any test submissions from results store
    from app.core.results_store import results_store
    test_submissions = [
        "test-pubsub-submission",
        "test-ordering-submission",
        "test-error-submission"
    ]
    for submission in test_submissions:
        results_store.clear_result(submission)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 