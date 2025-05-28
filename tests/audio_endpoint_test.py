import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import base64
import json
from app.main import app
from app.services.audio_service import AudioService
import logging
import os

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create test client
client = TestClient(app)

# Test data
VALID_AUDIO_URL = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/e6b419e8-6ae8-4365-afc5-2a111b8a6479/9c2301fe-fa6c-4860-9c59-faa1483b8f88/e6b419e8-6ae8-4365-afc5-2a111b8a6479_9c2301fe-fa6c-4860-9c59-faa1483b8f88_card-1_1747880119202.webm"
VALID_QUESTION_NUMBER = 1
VALID_SUBMISSION_URL = "test-submission-123"
VALID_WAV_PATH = "/../lib/mock-test1.wav"

@pytest.fixture(autouse=True)
def setup_test():
    """Setup and teardown for each test"""
    # Setup
    logger.info("Setting up test")
    yield
    # Teardown
    logger.info("Tearing down test")

@pytest.fixture
def mock_audio_service():
    """Mock the AudioService for testing"""
    with patch('app.api.v1.endpoints.audio_endpoint.AudioService') as mock:
        yield mock

def test_valid_audio_conversion_request(mock_audio_service):
    """Test direct audio conversion request with valid data"""
    # Setup mock
    mock_service = Mock(spec=AudioService)
    mock_service.process_single_audio.return_value = {
        "wav_path": VALID_WAV_PATH,
        "question_number": VALID_QUESTION_NUMBER
    }
    mock_audio_service.return_value = mock_service

    # Test request
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "audio_url": VALID_AUDIO_URL,
            "question_number": VALID_QUESTION_NUMBER,
            "submission_url": VALID_SUBMISSION_URL
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 200
    assert "wav_path" in response.json()
    assert response.json()["wav_path"] == VALID_WAV_PATH
    assert response.json()["question_number"] == VALID_QUESTION_NUMBER
    mock_service.process_single_audio.assert_called_once_with(
        VALID_AUDIO_URL,
        VALID_QUESTION_NUMBER,
        VALID_SUBMISSION_URL
    )

def test_audio_conversion_without_submission_url(mock_audio_service):
    """Test audio conversion without submission URL"""
    # Setup mock
    mock_service = Mock(spec=AudioService)
    mock_service.process_single_audio.return_value = {
        "wav_path": VALID_WAV_PATH,
        "question_number": VALID_QUESTION_NUMBER
    }
    mock_audio_service.return_value = mock_service

    # Test request
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "audio_url": VALID_AUDIO_URL,
            "question_number": VALID_QUESTION_NUMBER
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 200
    assert "wav_path" in response.json()
    assert response.json()["wav_path"] == VALID_WAV_PATH
    assert response.json()["question_number"] == VALID_QUESTION_NUMBER
    mock_service.process_single_audio.assert_called_once_with(
        VALID_AUDIO_URL,
        VALID_QUESTION_NUMBER,
        None
    )

def test_valid_pubsub_message(mock_audio_service):
    """Test processing of valid Pub/Sub message"""
    # Setup mock
    mock_service = Mock(spec=AudioService)
    mock_service.process_single_audio.return_value = {
        "wav_path": VALID_WAV_PATH,
        "question_number": VALID_QUESTION_NUMBER
    }
    mock_audio_service.return_value = mock_service

    # Create Pub/Sub message
    message_data = {
        "audio_url": VALID_AUDIO_URL,
        "question_number": VALID_QUESTION_NUMBER,
        "submission_url": VALID_SUBMISSION_URL
    }
    encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

    # Test request
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "message": {
                "data": encoded_data,
                "messageId": "test-message-123",
                "publishTime": "2024-01-01T00:00:00.000Z"
            }
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 200
    assert "wav_path" in response.json()
    assert response.json()["wav_path"] == VALID_WAV_PATH
    assert response.json()["question_number"] == VALID_QUESTION_NUMBER
    mock_service.process_single_audio.assert_called_once_with(
        VALID_AUDIO_URL,
        VALID_QUESTION_NUMBER,
        VALID_SUBMISSION_URL
    )

def test_invalid_base64_pubsub_message(mock_audio_service):
    """Test handling of invalid base64 in Pub/Sub message"""
    # Test request with invalid base64
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "message": {
                "data": "invalid-base64-data!@#$",
                "messageId": "test-message-456"
            }
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 500
    assert "Invalid base64-encoded string" in response.json()["detail"]

def test_invalid_json_pubsub_message(mock_audio_service):
    """Test handling of invalid JSON in Pub/Sub message"""
    # Create invalid JSON data
    invalid_json = "invalid-json-content"
    encoded_data = base64.b64encode(invalid_json.encode()).decode()

    # Test request
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "message": {
                "data": encoded_data,
                "messageId": "test-message-789"
            }
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 500
    assert "Expecting value" in response.json()["detail"]

def test_audio_service_processing_failure(mock_audio_service):
    """Test handling of audio service processing failure"""
    # Setup mock to raise exception
    mock_service = Mock(spec=AudioService)
    mock_service.process_single_audio.side_effect = Exception("Audio conversion failed")
    mock_audio_service.return_value = mock_service

    # Test request
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "audio_url": VALID_AUDIO_URL,
            "question_number": VALID_QUESTION_NUMBER
        }
    )

    # Assertions
    assert response.status_code == 500
    assert "Audio conversion failed" in response.json()["detail"]

def test_missing_audio_url(mock_audio_service):
    """Test handling of missing audio URL"""
    # Test request without audio_url
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "question_number": VALID_QUESTION_NUMBER,
            "submission_url": VALID_SUBMISSION_URL
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 500
    assert "audio_url" in response.json()["detail"]

def test_missing_question_number(mock_audio_service):
    """Test handling of missing question number"""
    # Test request without question_number
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "audio_url": VALID_AUDIO_URL,
            "submission_url": VALID_SUBMISSION_URL
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 500
    assert "question_number" in response.json()["detail"]

def test_different_audio_formats(mock_audio_service):
    """Test processing of different audio file formats with mocked service"""
    # Setup mock
    mock_service = Mock(spec=AudioService)
    mock_service.process_single_audio.return_value = {
        "wav_path": VALID_WAV_PATH,
        "question_number": VALID_QUESTION_NUMBER
    }
    mock_audio_service.return_value = mock_service

    # Test different audio formats
    formats = [".mp3", ".wav", ".webm", ".m4a"]
    for format in formats:
        # Use a URL pattern that matches the actual application
        audio_url = f"https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/test-user-id/test-submission-id/test-user-id_test-submission-id_card-1_1747880119202{format}"
        
        response = client.post(
            "/api/v1/audio/audio_proccessing",
            json={
                "audio_url": audio_url,
                "question_number": VALID_QUESTION_NUMBER
            }
        )

        # Debug logging
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response body: {response.json()}")

        # Assertions
        assert response.status_code == 200
        assert "wav_path" in response.json()
        assert response.json()["wav_path"] == VALID_WAV_PATH
        assert response.json()["question_number"] == VALID_QUESTION_NUMBER
        mock_service.process_single_audio.assert_called_with(
            audio_url,
            VALID_QUESTION_NUMBER,
            None
        )

def test_invalid_audio_url(mock_audio_service):
    """Test handling of invalid audio URL"""
    # Setup mock to handle invalid URL
    mock_service = Mock(spec=AudioService)
    mock_service.process_single_audio.side_effect = Exception("Invalid audio URL")
    mock_audio_service.return_value = mock_service

    # Test request with invalid URL
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "audio_url": "not-a-valid-url",
            "question_number": VALID_QUESTION_NUMBER
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 500
    assert "Invalid audio URL" in response.json()["detail"]

def test_real_audio_conversion():
    """Test actual audio conversion with real service"""
    # Use a real audio URL from our storage
    real_audio_url = VALID_AUDIO_URL  # This is a real .webm file in our storage
    
    response = client.post(
        "/api/v1/audio/audio_proccessing",
        json={
            "audio_url": real_audio_url,
            "question_number": VALID_QUESTION_NUMBER,
            "submission_url": VALID_SUBMISSION_URL  # Required for session_id generation
        }
    )

    # Debug logging
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    # Assertions
    assert response.status_code == 200
    assert "wav_path" in response.json()
    assert response.json()["question_number"] == VALID_QUESTION_NUMBER
    
    # Verify the WAV file was actually created
    wav_path = response.json()["wav_path"]
    assert os.path.exists(wav_path), f"WAV file was not created at {wav_path}"
    
    # Note: We don't need to clean up the file as FileManagerService will handle it
    # The file will be automatically cleaned up after 30 minutes or when all services complete
