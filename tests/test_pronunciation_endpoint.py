import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_pronunciation_service():
    """Mock PronunciationService.analyze_pronunciation for testing"""
    with patch('app.api.v1.endpoints.pronunciation_endpoint.PronunciationService.analyze_pronunciation') as mock:
        yield mock

class TestPronunciationEndpoint:
    """Test cases for pronunciation assessment endpoint"""

    def test_successful_pronunciation_assessment(self, mock_pronunciation_service):
        """Test successful pronunciation assessment with valid data"""
        # Mock successful analysis result
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 3.5,
            "transcript": "Hello world, this is a test",
            "overall_pronunciation_score": 85.0,
            "accuracy_score": 88.0,
            "fluency_score": 82.0,
            "prosody_score": 80.0,
            "completeness_score": 90.0,
            "critical_errors": [
                {
                    "word": "world",
                    "error_type": "mispronunciation",
                    "expected": "wɜːrld",
                    "actual": "wɔːrld"
                }
            ],
            "filler_words": [
                {
                    "word": "um",
                    "position": 2.1,
                    "confidence": 0.95
                }
            ],
            "word_details": [
                {
                    "word": "hello",
                    "accuracy_score": 95.0,
                    "error_type": "None"
                },
                {
                    "word": "world",
                    "accuracy_score": 75.0,
                    "error_type": "mispronunciation"
                }
            ],
            "improvement_suggestion": "Focus on the pronunciation of 'world' - try to use the correct vowel sound."
        }
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "Hello world, this is a test",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["audio_duration"] == 3.5
        assert data["transcript"] == "Hello world, this is a test"
        assert data["overall_pronunciation_score"] == 85.0
        assert data["accuracy_score"] == 88.0
        assert data["fluency_score"] == 82.0
        assert data["prosody_score"] == 80.0
        assert data["completeness_score"] == 90.0
        assert len(data["critical_errors"]) == 1
        assert len(data["filler_words"]) == 1
        assert len(data["word_details"]) == 2
        assert data["improvement_suggestion"] == "Focus on the pronunciation of 'world' - try to use the correct vowel sound."
        assert data["error"] is None
        assert data["question_number"] == 1
        
        # Verify service was called with correct parameters
        mock_pronunciation_service.assert_called_once_with(
            "https://example.com/audio.mp3",
            "Hello world, this is a test"
        )

    def test_complex_reference_text_analysis(self, mock_pronunciation_service):
        """Test analysis with complex reference text"""
        # Mock complex analysis result
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 8.2,
            "transcript": "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet.",
            "overall_pronunciation_score": 78.0,
            "accuracy_score": 80.0,
            "fluency_score": 75.0,
            "prosody_score": 77.0,
            "completeness_score": 85.0,
            "critical_errors": [
                {
                    "word": "quick",
                    "error_type": "mispronunciation",
                    "expected": "kwɪk",
                    "actual": "kwɪtʃ"
                },
                {
                    "word": "alphabet",
                    "error_type": "omission",
                    "expected": "ˈælfəbɛt",
                    "actual": "ˈælfəbet"
                }
            ],
            "filler_words": [],
            "word_details": [
                {"word": "the", "accuracy_score": 95.0, "error_type": "None"},
                {"word": "quick", "accuracy_score": 65.0, "error_type": "mispronunciation"},
                {"word": "brown", "accuracy_score": 90.0, "error_type": "None"}
            ],
            "improvement_suggestion": "Work on consonant clusters in words like 'quick' and practice stress patterns in longer words like 'alphabet'."
        }
        
        payload = {
            "audio_file": "https://example.com/complex-audio.mp3",
            "reference_text": "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet.",
            "question_number": 2
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert len(data["critical_errors"]) == 2
        assert len(data["filler_words"]) == 0
        assert len(data["word_details"]) == 3
        assert data["question_number"] == 2
        
        # Verify service was called correctly
        mock_pronunciation_service.assert_called_once()

    def test_service_returns_error_status(self, mock_pronunciation_service):
        """Test handling when service returns error status"""
        # Mock service returning error
        mock_pronunciation_service.return_value = {
            "status": "error",
            "error": "Audio file format not supported",
            "transcript": "partial transcript"
        }
        
        payload = {
            "audio_file": "https://example.com/unsupported.xyz",
            "reference_text": "Hello world",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200  # Endpoint handles error gracefully
        data = response.json()
        
        assert data["status"] == "error"
        assert data["error"] == "Audio file format not supported"
        assert data["transcript"] == "partial transcript"
        assert data["overall_pronunciation_score"] == 0
        assert data["accuracy_score"] == 0
        assert data["fluency_score"] == 0
        assert data["prosody_score"] == 0
        assert data["completeness_score"] == 0
        assert data["critical_errors"] == []
        assert data["filler_words"] == []
        assert data["word_details"] == []
        assert data["improvement_suggestion"] == ""
        assert data["question_number"] == 1

    def test_service_throws_exception(self, mock_pronunciation_service):
        """Test handling of service exceptions"""
        # Mock service to raise exception
        mock_pronunciation_service.side_effect = Exception("Processing failed")
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "Hello world",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 500
        assert "Failed to assess pronunciation: Processing failed" in response.json()["detail"]

    def test_missing_required_fields(self, mock_pronunciation_service):
        """Test validation error for missing required fields"""
        payload = {
            "reference_text": "Hello world"
            # Missing audio_file
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 422  # Validation Error
        
        # Verify service was not called
        mock_pronunciation_service.assert_not_called()

    def test_optional_reference_text(self, mock_pronunciation_service):
        """Test request with missing reference_text (should use default None)"""
        # Mock successful analysis
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 2.0,
            "transcript": "Recognized speech without reference",
            "overall_pronunciation_score": 70.0,
            "accuracy_score": 72.0,
            "fluency_score": 68.0,
            "prosody_score": 70.0,
            "completeness_score": 75.0,
            "critical_errors": [],
            "filler_words": [],
            "word_details": [],
            "improvement_suggestion": "Continue practicing for better fluency."
        }
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        
        # Verify service was called with None for reference_text
        mock_pronunciation_service.assert_called_once_with(
            "https://example.com/audio.mp3",
            None
        )

    def test_complete_response_format_validation(self, mock_pronunciation_service):
        """Test that response follows PronunciationResponse schema exactly"""
        # Mock complete service response
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 4.5,
            "transcript": "Complete test transcript",
            "overall_pronunciation_score": 92.0,
            "accuracy_score": 94.0,
            "fluency_score": 90.0,
            "prosody_score": 88.0,
            "completeness_score": 95.0,
            "critical_errors": [
                {
                    "word": "test",
                    "error_type": "stress",
                    "expected": "tɛst",
                    "actual": "tɛst"
                }
            ],
            "filler_words": [
                {
                    "word": "uh",
                    "position": 1.5,
                    "confidence": 0.9
                }
            ],
            "word_details": [
                {
                    "word": "complete",
                    "accuracy_score": 98.0,
                    "error_type": "None"
                }
            ],
            "improvement_suggestion": "Excellent pronunciation overall!"
        }
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "Complete test transcript",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        required_fields = [
            "status", "audio_duration", "transcript", "overall_pronunciation_score",
            "accuracy_score", "fluency_score", "prosody_score", "completeness_score",
            "critical_errors", "filler_words", "word_details", "improvement_suggestion",
            "error", "question_number"
        ]
        
        for field in required_fields:
            assert field in data
        
        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["audio_duration"], (int, float))
        assert isinstance(data["transcript"], str)
        assert isinstance(data["overall_pronunciation_score"], (int, float))
        assert isinstance(data["accuracy_score"], (int, float))
        assert isinstance(data["fluency_score"], (int, float))
        assert isinstance(data["prosody_score"], (int, float))
        assert isinstance(data["completeness_score"], (int, float))
        assert isinstance(data["critical_errors"], list)
        assert isinstance(data["filler_words"], list)
        assert isinstance(data["word_details"], list)
        assert isinstance(data["improvement_suggestion"], str)
        assert data["error"] is None
        assert isinstance(data["question_number"], int)

    def test_different_audio_formats(self, mock_pronunciation_service):
        """Test processing different audio file formats"""
        # Mock successful analysis for different formats
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 3.0,
            "transcript": "Format test",
            "overall_pronunciation_score": 80.0,
            "accuracy_score": 82.0,
            "fluency_score": 78.0,
            "prosody_score": 79.0,
            "completeness_score": 85.0,
            "critical_errors": [],
            "filler_words": [],
            "word_details": [],
            "improvement_suggestion": "Good pronunciation!"
        }
        
        audio_formats = [
            "https://example.com/audio.mp3",
            "https://example.com/audio.wav",
            "https://example.com/audio.webm",
            "https://example.com/audio.m4a"
        ]
        
        for audio_url in audio_formats:
            payload = {
                "audio_file": audio_url,
                "reference_text": "Format test",
                "question_number": 1
            }
            
            response = client.post("/api/v1/pronunciation/analysis", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        
        # Verify service was called for each format
        assert mock_pronunciation_service.call_count == len(audio_formats)

    def test_score_range_validation(self, mock_pronunciation_service):
        """Test that all scores are within valid ranges (0-100)"""
        # Mock service with various score scenarios
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 2.5,
            "transcript": "Score validation test",
            "overall_pronunciation_score": 45.0,
            "accuracy_score": 50.0,
            "fluency_score": 40.0,
            "prosody_score": 42.0,
            "completeness_score": 48.0,
            "critical_errors": [],
            "filler_words": [],
            "word_details": [],
            "improvement_suggestion": "Keep practicing!"
        }
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "Score validation test",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all scores are within 0-100 range
        score_fields = [
            "overall_pronunciation_score", "accuracy_score", "fluency_score",
            "prosody_score", "completeness_score"
        ]
        
        for field in score_fields:
            score = data[field]
            assert 0 <= score <= 100, f"{field} score {score} is not within 0-100 range"

    def test_word_level_analysis(self, mock_pronunciation_service):
        """Test detailed word-level analysis"""
        # Mock detailed word analysis
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 4.0,
            "transcript": "The quick brown fox",
            "overall_pronunciation_score": 75.0,
            "accuracy_score": 78.0,
            "fluency_score": 72.0,
            "prosody_score": 74.0,
            "completeness_score": 80.0,
            "critical_errors": [
                {
                    "word": "quick",
                    "error_type": "mispronunciation",
                    "expected": "kwɪk",
                    "actual": "kwɪtʃ"
                }
            ],
            "filler_words": [],
            "word_details": [
                {"word": "the", "accuracy_score": 95.0, "error_type": "None"},
                {"word": "quick", "accuracy_score": 60.0, "error_type": "mispronunciation"},
                {"word": "brown", "accuracy_score": 85.0, "error_type": "None"},
                {"word": "fox", "accuracy_score": 90.0, "error_type": "None"}
            ],
            "improvement_suggestion": "Focus on the 'qu' sound in 'quick'."
        }
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "The quick brown fox",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify word_details contains all words
        assert len(data["word_details"]) == 4
        
        # Verify each word has required fields
        for word_detail in data["word_details"]:
            assert "word" in word_detail
            assert "accuracy_score" in word_detail
            assert "error_type" in word_detail
        
        # Verify word-level scores are consistent
        word_scores = [detail["accuracy_score"] for detail in data["word_details"]]
        for score in word_scores:
            assert 0 <= score <= 100

    @patch('app.api.v1.endpoints.pronunciation_endpoint.logger')
    def test_request_logging(self, mock_logger, mock_pronunciation_service):
        """Test that requests are logged correctly"""
        # Mock successful analysis
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 3.0,
            "transcript": "Logging test",
            "overall_pronunciation_score": 80.0,
            "accuracy_score": 82.0,
            "fluency_score": 78.0,
            "prosody_score": 79.0,
            "completeness_score": 85.0,
            "critical_errors": [],
            "filler_words": [],
            "word_details": [],
            "improvement_suggestion": "Good work!"
        }
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "Logging test",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        
        # Verify logging calls
        mock_logger.info.assert_called_with(
            f"Processing pronunciation assessment for: {payload['audio_file']}"
        )

    @patch('app.api.v1.endpoints.pronunciation_endpoint.logger')
    def test_error_logging(self, mock_logger, mock_pronunciation_service):
        """Test that errors are logged correctly"""
        # Mock service to raise exception
        mock_pronunciation_service.side_effect = Exception("Test error")
        
        payload = {
            "audio_file": "https://example.com/audio.mp3",
            "reference_text": "Error test",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 500
        
        # Verify error logging
        mock_logger.exception.assert_called_with("Error assessing pronunciation: Test error")

    def test_large_audio_file_processing(self, mock_pronunciation_service):
        """Test processing of large audio file"""
        # Mock analysis for large file
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 120.0,  # 2 minutes
            "transcript": "This is a very long transcript from a large audio file with many sentences and words to test the system's ability to handle extended speech samples.",
            "overall_pronunciation_score": 82.0,
            "accuracy_score": 85.0,
            "fluency_score": 79.0,
            "prosody_score": 80.0,
            "completeness_score": 88.0,
            "critical_errors": [
                {
                    "word": "ability",
                    "error_type": "stress",
                    "expected": "əˈbɪləti",
                    "actual": "ˈæbɪləti"
                }
            ],
            "filler_words": [
                {"word": "um", "position": 15.2, "confidence": 0.9},
                {"word": "uh", "position": 45.8, "confidence": 0.85}
            ],
            "word_details": [
                {"word": "this", "accuracy_score": 95.0, "error_type": "None"},
                {"word": "ability", "accuracy_score": 70.0, "error_type": "stress"}
            ],
            "improvement_suggestion": "Work on word stress patterns in longer words."
        }
        
        payload = {
            "audio_file": "https://example.com/large-audio.mp3",
            "reference_text": "This is a very long transcript from a large audio file with many sentences and words to test the system's ability to handle extended speech samples.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/pronunciation/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["audio_duration"] == 120.0
        assert len(data["critical_errors"]) == 1
        assert len(data["filler_words"]) == 2
        
        # Verify service was called with large transcript
        mock_pronunciation_service.assert_called_once()

    def test_concurrent_pronunciation_requests(self, mock_pronunciation_service):
        """Test multiple concurrent pronunciation assessment requests"""
        # Mock successful analysis
        mock_pronunciation_service.return_value = {
            "status": "success",
            "audio_duration": 3.0,
            "transcript": "Concurrent test",
            "overall_pronunciation_score": 80.0,
            "accuracy_score": 82.0,
            "fluency_score": 78.0,
            "prosody_score": 79.0,
            "completeness_score": 85.0,
            "critical_errors": [],
            "filler_words": [],
            "word_details": [],
            "improvement_suggestion": "Good work!"
        }
        
        payload1 = {
            "audio_file": "https://example.com/audio1.mp3",
            "reference_text": "First concurrent request",
            "question_number": 1
        }
        
        payload2 = {
            "audio_file": "https://example.com/audio2.mp3",
            "reference_text": "Second concurrent request",
            "question_number": 2
        }
        
        # Send concurrent requests
        response1 = client.post("/api/v1/pronunciation/analysis", json=payload1)
        response2 = client.post("/api/v1/pronunciation/analysis", json=payload2)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both requests were processed
        assert mock_pronunciation_service.call_count == 2 