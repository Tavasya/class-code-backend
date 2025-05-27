import pytest
import json
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_transcription_service():
    """Mock TranscriptionService for testing"""
    with patch('app.api.v1.endpoints.transcription_endpoint.TranscriptionService') as mock:
        service_instance = MagicMock()
        service_instance.process_single_transcription = AsyncMock()
        mock.return_value = service_instance
        yield service_instance

class TestTranscriptionEndpoint:
    """Test cases for transcription endpoint"""

    def test_direct_transcription_request_success(self, mock_transcription_service):
        """Test successful direct transcription request"""
        # Mock successful transcription result
        mock_transcription_service.process_single_transcription.return_value = {
            "text": "Hello world, this is a test transcription.",
            "error": None,
            "question_number": 1
        }
        
        payload = {
            "audio_url": "https://example.com/speech.mp3",
            "question_number": 1,
            "submission_url": "test-submission-123"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["text"] == "Hello world, this is a test transcription."
        assert data["error"] is None
        assert data["question_number"] == 1
        
        # Verify service was called with correct parameters
        mock_transcription_service.process_single_transcription.assert_called_once_with(
            "https://example.com/speech.mp3", 1, "test-submission-123"
        )

    def test_direct_transcription_without_submission_url(self, mock_transcription_service):
        """Test transcription request without submission URL"""
        mock_transcription_service.process_single_transcription.return_value = {
            "text": "Test transcription without submission URL.",
            "error": None,
            "question_number": 2
        }
        
        payload = {
            "audio_url": "https://example.com/speech.wav",
            "question_number": 2
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["text"] == "Test transcription without submission URL."
        assert data["question_number"] == 2
        
        # Verify service was called with None for submission_url
        mock_transcription_service.process_single_transcription.assert_called_once_with(
            "https://example.com/speech.wav", 2, None
        )

    def test_pubsub_transcription_message_success(self, mock_transcription_service):
        """Test successful Pub/Sub transcription message processing"""
        mock_transcription_service.process_single_transcription.return_value = {
            "text": "Pub/Sub transcription successful.",
            "error": None,
            "question_number": 1
        }
        
        # Create base64 encoded message data
        message_data = {
            "audio_url": "https://example.com/speech.mp3",
            "question_number": 1,
            "submission_url": "test-submission"
        }
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()
        
        payload = {
            "message": {
                "data": encoded_data,
                "messageId": "transcription-msg-123",
                "publishTime": "2024-01-01T00:00:00.000Z"
            }
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["text"] == "Pub/Sub transcription successful."
        assert data["question_number"] == 1
        
        # Verify service was called with decoded parameters
        mock_transcription_service.process_single_transcription.assert_called_once_with(
            "https://example.com/speech.mp3", 1, "test-submission"
        )

    def test_pubsub_invalid_base64_data(self, mock_transcription_service):
        """Test Pub/Sub message with invalid base64 data"""
        payload = {
            "message": {
                "data": "invalid-base64-data!@#$",
                "messageId": "transcription-msg-456"
            }
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 500
        assert "Failed to process audio" in response.json()["detail"]
        
        # Verify service was not called
        mock_transcription_service.process_single_transcription.assert_not_called()

    def test_pubsub_invalid_json_data(self, mock_transcription_service):
        """Test Pub/Sub message with invalid JSON in base64 data"""
        # Encode invalid JSON
        invalid_json = "invalid-json-content"
        encoded_data = base64.b64encode(invalid_json.encode()).decode()
        
        payload = {
            "message": {
                "data": encoded_data,
                "messageId": "transcription-msg-789"
            }
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 500
        assert "Failed to process audio" in response.json()["detail"]
        
        # Verify service was not called
        mock_transcription_service.process_single_transcription.assert_not_called()

    def test_transcription_service_failure(self, mock_transcription_service):
        """Test handling of transcription service failure"""
        # Mock service to raise exception
        mock_transcription_service.process_single_transcription.side_effect = Exception("Transcription failed")
        
        payload = {
            "audio_url": "https://example.com/speech.mp3",
            "question_number": 1,
            "submission_url": "test-submission"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 500
        assert "Failed to process audio: Transcription failed" in response.json()["detail"]

    def test_missing_audio_url(self, mock_transcription_service):
        """Test request missing audio_url parameter"""
        payload = {
            "question_number": 1,
            "submission_url": "test"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 500
        assert "Failed to process audio" in response.json()["detail"]
        
        # Verify service was not called
        mock_transcription_service.process_single_transcription.assert_not_called()

    def test_missing_question_number(self, mock_transcription_service):
        """Test request missing question_number parameter"""
        payload = {
            "audio_url": "https://example.com/speech.mp3",
            "submission_url": "test"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 500
        assert "Failed to process audio" in response.json()["detail"]
        
        # Verify service was not called
        mock_transcription_service.process_single_transcription.assert_not_called()

    def test_different_audio_formats(self, mock_transcription_service):
        """Test transcription with different audio file formats"""
        audio_formats = [
            "https://example.com/speech.mp3",
            "https://example.com/speech.wav", 
            "https://example.com/speech.webm",
            "https://example.com/speech.m4a"
        ]
        
        for i, audio_url in enumerate(audio_formats, 1):
            mock_transcription_service.process_single_transcription.return_value = {
                "text": f"Transcription for format {i}",
                "error": None,
                "question_number": i
            }
            
            payload = {
                "audio_url": audio_url,
                "question_number": i,
                "submission_url": "test-submission"
            }
            
            response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == f"Transcription for format {i}"
            assert data["question_number"] == i

    def test_transcription_with_error_from_service(self, mock_transcription_service):
        """Test transcription when service returns error"""
        mock_transcription_service.process_single_transcription.return_value = {
            "text": "",
            "error": "Audio quality too poor for transcription",
            "question_number": 1
        }
        
        payload = {
            "audio_url": "https://example.com/poor_quality.mp3",
            "question_number": 1,
            "submission_url": "test-submission"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["text"] == ""
        assert data["error"] == "Audio quality too poor for transcription"
        assert data["question_number"] == 1

    def test_response_format_validation(self, mock_transcription_service):
        """Test that response follows TranscriptionResponse schema"""
        mock_transcription_service.process_single_transcription.return_value = {
            "text": "Valid transcription response",
            "error": None,
            "question_number": 5
        }
        
        payload = {
            "audio_url": "https://example.com/speech.mp3",
            "question_number": 5,
            "submission_url": "test-submission"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        assert "text" in data
        assert "error" in data
        assert "question_number" in data
        
        # Verify field types
        assert isinstance(data["text"], str)
        assert data["error"] is None or isinstance(data["error"], str)
        assert data["question_number"] is None or isinstance(data["question_number"], int)

    @patch('app.api.v1.endpoints.transcription_endpoint.logger')
    def test_logging_on_success(self, mock_logger, mock_transcription_service):
        """Test that successful processing is logged appropriately"""
        mock_transcription_service.process_single_transcription.return_value = {
            "text": "Logged transcription",
            "error": None,
            "question_number": 1
        }
        
        payload = {
            "audio_url": "https://example.com/speech.mp3",
            "question_number": 1,
            "submission_url": "test-submission"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 200
        
        # Verify logging was called
        mock_logger.info.assert_called_with("Transcribing audio URL for question 1")

    @patch('app.api.v1.endpoints.transcription_endpoint.logger')
    def test_logging_on_error(self, mock_logger, mock_transcription_service):
        """Test that errors are logged with full context"""
        mock_transcription_service.process_single_transcription.side_effect = Exception("Service error")
        
        payload = {
            "audio_url": "https://example.com/speech.mp3",
            "question_number": 1,
            "submission_url": "test-submission"
        }
        
        response = client.post("/api/v1/transcription/audio_proccessing", json=payload)
        
        assert response.status_code == 500
        
        # Verify error logging was called
        mock_logger.exception.assert_called_once() 