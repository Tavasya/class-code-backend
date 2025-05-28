import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_analyze_grammar():
    """Mock analyze_grammar service function for testing"""
    with patch('app.api.v1.endpoints.grammar_endpoint.analyze_grammar') as mock:
        yield mock

class TestGrammarEndpoint:
    """Test cases for grammar analysis endpoint"""

    def test_successful_grammar_analysis(self, mock_analyze_grammar):
        """Test successful grammar analysis with valid transcript"""
        # Mock successful analysis result
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {
                "sentence_1": {
                    "original_phrase": "was learning",
                    "suggested_correction": "were learning",
                    "explanation": "subject-verb agreement"
                }
            },
            "vocabulary_suggestions": {
                "word_1": {
                    "original_word": "good",
                    "context": "good understanding",
                    "advanced_alternatives": ["excellent", "thorough", "comprehensive"],
                    "level": "B1"
                }
            }
        }
        
        payload = {
            "transcript": "This is a good sentence with proper grammar and vocabulary usage.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "grammar_corrections" in data
        assert "vocabulary_suggestions" in data
        assert data["error"] is None
        
        # Verify service was called with correct transcript
        mock_analyze_grammar.assert_called_once_with(
            "This is a good sentence with proper grammar and vocabulary usage."
        )

    def test_complex_transcript_analysis(self, mock_analyze_grammar):
        """Test analysis of complex transcript with multiple issues"""
        # Mock complex analysis result
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {
                "sentence_1": {
                    "original_phrase": "student was learning",
                    "suggested_correction": "students were learning",
                    "explanation": "subject-verb agreement and plural form"
                },
                "sentence_2": {
                    "original_phrase": "they demonstrate",
                    "suggested_correction": "they demonstrated",
                    "explanation": "verb tense consistency"
                }
            },
            "vocabulary_suggestions": {
                "word_1": {
                    "original_word": "good",
                    "context": "good understanding",
                    "advanced_alternatives": ["excellent", "thorough", "comprehensive"],
                    "level": "B1"
                },
                "word_2": {
                    "original_word": "quickly",
                    "context": "learning quickly",
                    "advanced_alternatives": ["rapidly", "efficiently", "swiftly"],
                    "level": "B2"
                }
            }
        }
        
        payload = {
            "transcript": "The student was learning English language very quickly and they demonstrate good understanding of grammatical rules. However, there is still room for improvement in vocabulary choices and sentence structure.",
            "question_number": 2
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert len(data["grammar_corrections"]) == 2
        assert len(data["vocabulary_suggestions"]) == 2
        
        # Verify service was called correctly
        mock_analyze_grammar.assert_called_once()

    def test_transcript_too_short(self, mock_analyze_grammar):
        """Test validation error for transcript that is too short"""
        payload = {
            "transcript": "Short",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 400
        assert "Transcript is too short for analysis (minimum 10 characters)" in response.json()["detail"]
        
        # Verify service was not called
        mock_analyze_grammar.assert_not_called()

    def test_empty_transcript(self, mock_analyze_grammar):
        """Test validation error for empty transcript"""
        payload = {
            "transcript": "",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 400
        assert "Transcript is too short for analysis" in response.json()["detail"]
        
        # Verify service was not called
        mock_analyze_grammar.assert_not_called()

    def test_whitespace_only_transcript(self, mock_analyze_grammar):
        """Test validation error for whitespace-only transcript"""
        payload = {
            "transcript": "   \n\t   ",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 400
        assert "Transcript is too short for analysis" in response.json()["detail"]
        
        # Verify service was not called
        mock_analyze_grammar.assert_not_called()

    def test_service_returns_grammar_corrections(self, mock_analyze_grammar):
        """Test service returning grammar corrections and vocabulary suggestions"""
        # Mock service response with corrections
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {
                "correction_1": {
                    "original_phrase": "subject-verb disagreement",
                    "suggested_correction": "was -> were",
                    "explanation": "plural subject requires plural verb"
                },
                "correction_2": {
                    "original_phrase": "missing article",
                    "suggested_correction": "add 'the' before 'student'",
                    "explanation": "definite article needed"
                }
            },
            "vocabulary_suggestions": {
                "suggestion_1": {
                    "original_word": "good",
                    "context": "quality",
                    "advanced_alternatives": ["excellent", "outstanding", "remarkable"],
                    "level": "B1"
                }
            }
        }
        
        payload = {
            "transcript": "The students was demonstrating good understanding of the material.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert len(data["grammar_corrections"]) == 2
        assert len(data["vocabulary_suggestions"]) == 1
        assert "correction_1" in data["grammar_corrections"]
        assert "suggestion_1" in data["vocabulary_suggestions"]

    def test_service_throws_exception(self, mock_analyze_grammar):
        """Test handling of service exception"""
        # Mock service to raise exception
        mock_analyze_grammar.side_effect = Exception("Analysis service unavailable")
        
        payload = {
            "transcript": "This is a valid transcript for testing error handling.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 500
        assert "Error analyzing grammar: Analysis service unavailable" in response.json()["detail"]

    def test_complete_grammar_response_format(self, mock_analyze_grammar):
        """Test that response follows GrammarResponse schema exactly"""
        # Mock complete service response
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {
                "correction_1": {
                    "original_phrase": "test phrase",
                    "suggested_correction": "corrected phrase",
                    "explanation": "test explanation"
                }
            },
            "vocabulary_suggestions": {
                "suggestion_1": {
                    "original_word": "test",
                    "context": "test context",
                    "advanced_alternatives": ["examine", "evaluate", "assess"],
                    "level": "B2"
                }
            }
        }
        
        payload = {
            "transcript": "This is a test transcript for response format validation.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        assert "status" in data
        assert "grammar_corrections" in data
        assert "vocabulary_suggestions" in data
        assert "error" in data
        
        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["grammar_corrections"], dict)
        assert isinstance(data["vocabulary_suggestions"], dict)
        assert data["error"] is None

    def test_empty_corrections_response(self, mock_analyze_grammar):
        """Test response when no corrections are needed"""
        # Mock service returning no corrections
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {},
            "vocabulary_suggestions": {}
        }
        
        payload = {
            "transcript": "This is a perfectly written sentence with excellent grammar and vocabulary.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert len(data["grammar_corrections"]) == 0
        assert len(data["vocabulary_suggestions"]) == 0

    @patch('app.api.v1.endpoints.grammar_endpoint.logger')
    def test_request_logging(self, mock_logger, mock_analyze_grammar):
        """Test that requests are logged correctly"""
        # Mock successful analysis
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {
                "test": {
                    "original_phrase": "test phrase",
                    "suggested_correction": "corrected phrase",
                    "explanation": "test explanation"
                }
            },
            "vocabulary_suggestions": {
                "test": {
                    "original_word": "test",
                    "context": "test context",
                    "advanced_alternatives": ["examine", "evaluate"],
                    "level": "B1"
                }
            }
        }
        
        payload = {
            "transcript": "This is a test transcript for logging verification.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        
        # Verify logging calls
        mock_logger.info.assert_any_call(
            f"Received grammar analysis request for transcript of length: {len(payload['transcript'])}"
        )
        mock_logger.info.assert_any_call(
            "Analysis complete: 1 grammar issues, 1 vocabulary suggestions"
        )

    @patch('app.api.v1.endpoints.grammar_endpoint.logger')
    def test_error_logging(self, mock_logger, mock_analyze_grammar):
        """Test that errors are logged correctly"""
        # Mock service to raise exception
        mock_analyze_grammar.side_effect = Exception("Test error")
        
        payload = {
            "transcript": "This is a test transcript for error logging.",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 500
        
        # Verify error logging
        mock_logger.exception.assert_called_once_with("Error in grammar analysis endpoint")

    def test_malformed_request_body(self, mock_analyze_grammar):
        """Test handling of request missing transcript field"""
        payload = {
            "invalid_field": "some text",
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 422  # Validation Error
        
        # Verify service was not called
        mock_analyze_grammar.assert_not_called()

    def test_missing_question_number(self, mock_analyze_grammar):
        """Test request with missing question_number (should use default)"""
        # Mock successful analysis
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {},
            "vocabulary_suggestions": {}
        }
        
        payload = {
            "transcript": "This is a test transcript without question number."
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        
        # Verify service was called
        mock_analyze_grammar.assert_called_once()

    def test_large_transcript_processing(self, mock_analyze_grammar):
        """Test processing of large transcript"""
        # Mock analysis for large transcript
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {
                "large_correction": {
                    "original_phrase": "test phrase",
                    "suggested_correction": "corrected phrase",
                    "explanation": "test explanation"
                }
            },
            "vocabulary_suggestions": {
                "large_suggestion": {
                    "original_word": "test",
                    "context": "test context",
                    "advanced_alternatives": ["examine", "evaluate"],
                    "level": "B1"
                }
            }
        }
        
        # Create large transcript (>1000 characters)
        large_transcript = "This is a test sentence. " * 50  # ~1250 characters
        
        payload = {
            "transcript": large_transcript,
            "question_number": 1
        }
        
        response = client.post("/api/v1/grammar/analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        
        # Verify service was called with large transcript
        mock_analyze_grammar.assert_called_once_with(large_transcript)

    def test_concurrent_analysis_requests(self, mock_analyze_grammar):
        """Test multiple concurrent grammar analysis requests"""
        # Mock successful analysis
        mock_analyze_grammar.return_value = {
            "grammar_corrections": {},
            "vocabulary_suggestions": {}
        }
        
        payload1 = {
            "transcript": "First concurrent request for grammar analysis.",
            "question_number": 1
        }
        
        payload2 = {
            "transcript": "Second concurrent request for grammar analysis.",
            "question_number": 2
        }
        
        # Send concurrent requests
        response1 = client.post("/api/v1/grammar/analysis", json=payload1)
        response2 = client.post("/api/v1/grammar/analysis", json=payload2)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both requests were processed
        assert mock_analyze_grammar.call_count == 2 