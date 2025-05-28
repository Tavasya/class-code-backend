import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_results_store():
    """Mock results_store for testing"""
    with patch('app.api.v1.endpoints.results_endpoint.results_store') as mock:
        yield mock

class TestResultsEndpoint:
    """Test cases for results endpoint"""

    # ==================== GET SUBMISSION RESULTS (TRANSFORMED) ====================
    
    def test_get_submission_results_success(self, mock_results_store):
        """Test successful retrieval of transformed submission results"""
        # Mock transformed results data
        mock_transformed_data = [
            {
                "question_number": 1,
                "analysis_type": "pronunciation",
                "score": 85.5,
                "feedback": "Good pronunciation overall"
            },
            {
                "question_number": 2,
                "analysis_type": "grammar",
                "score": 78.2,
                "feedback": "Minor grammatical errors detected"
            }
        ]
        
        mock_results_store.get_result_transformed.return_value = mock_transformed_data
        
        response = client.get("/api/v1/results/submission/test-submission-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["question_number"] == 1
        assert data[0]["analysis_type"] == "pronunciation"
        assert data[1]["question_number"] == 2
        assert data[1]["analysis_type"] == "grammar"
        
        # Verify store method was called correctly
        mock_results_store.get_result_transformed.assert_called_once_with("test-submission-123")

    def test_get_submission_results_not_found(self, mock_results_store):
        """Test retrieval of non-existent submission results"""
        mock_results_store.get_result_transformed.return_value = None
        
        response = client.get("/api/v1/results/submission/non-existent-submission")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No results found for submission: non-existent-submission"
        
        # Verify store method was called
        mock_results_store.get_result_transformed.assert_called_once_with("non-existent-submission")

    def test_get_submission_results_complex_data(self, mock_results_store):
        """Test retrieval of complex submission results with multiple analyses"""
        # Mock complex results with multiple question results
        mock_complex_data = [
            {
                "question_number": 1,
                "analysis_type": "pronunciation",
                "score": 85.5,
                "word_details": [
                    {"word": "hello", "accuracy": 90.0},
                    {"word": "world", "accuracy": 80.0}
                ],
                "feedback": "Good pronunciation overall"
            },
            {
                "question_number": 1,
                "analysis_type": "grammar",
                "score": 78.2,
                "errors": [
                    {"type": "subject_verb_agreement", "position": 5}
                ],
                "feedback": "Minor grammatical errors detected"
            },
            {
                "question_number": 2,
                "analysis_type": "fluency",
                "score": 82.1,
                "metrics": {
                    "speaking_rate": 150,
                    "pause_frequency": 0.3
                },
                "feedback": "Good fluency with natural pauses"
            }
        ]
        
        mock_results_store.get_result_transformed.return_value = mock_complex_data
        
        response = client.get("/api/v1/results/submission/complex-submission")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Verify all question results are included
        question_numbers = [item["question_number"] for item in data]
        assert 1 in question_numbers
        assert 2 in question_numbers
        
        # Verify different analysis types are preserved
        analysis_types = [item["analysis_type"] for item in data]
        assert "pronunciation" in analysis_types
        assert "grammar" in analysis_types
        assert "fluency" in analysis_types
        
        # Verify complex data structure is maintained
        pronunciation_result = next(item for item in data if item["analysis_type"] == "pronunciation")
        assert "word_details" in pronunciation_result
        assert len(pronunciation_result["word_details"]) == 2

    def test_get_submission_results_empty_list(self, mock_results_store):
        """Test retrieval when transformed results return empty list"""
        mock_results_store.get_result_transformed.return_value = []
        
        response = client.get("/api/v1/results/submission/empty-submission")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0

    # ==================== GET RAW SUBMISSION RESULTS ====================
    
    def test_get_raw_submission_results_success(self, mock_results_store):
        """Test successful retrieval of raw submission results"""
        # Mock raw results data (debugging format)
        mock_raw_data = {
            "submission_url": "test-submission-123",
            "completed_questions": [1, 2],
            "question_results": {
                "1": {
                    "pronunciation_analysis": {
                        "raw_scores": {"accuracy": 85.5, "fluency": 78.0},
                        "debug_info": {"processing_time": 2.3}
                    },
                    "grammar_analysis": {
                        "raw_errors": [{"type": "tense", "confidence": 0.8}],
                        "debug_info": {"model_version": "v2.1"}
                    }
                }
            },
            "stored_at": "2024-01-01T12:00:00.000Z"
        }
        
        mock_results_store.get_result.return_value = mock_raw_data
        
        response = client.get("/api/v1/results/submission/test-submission-123/raw")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert data["submission_url"] == "test-submission-123"
        assert "question_results" in data
        assert "stored_at" in data
        assert "completed_questions" in data
        
        # Verify raw format is preserved
        assert "raw_scores" in data["question_results"]["1"]["pronunciation_analysis"]
        assert "debug_info" in data["question_results"]["1"]["pronunciation_analysis"]
        
        # Verify store method was called correctly
        mock_results_store.get_result.assert_called_once_with("test-submission-123")

    def test_get_raw_submission_results_not_found(self, mock_results_store):
        """Test retrieval of non-existent raw submission results"""
        mock_results_store.get_result.return_value = None
        
        response = client.get("/api/v1/results/submission/non-existent-submission/raw")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No results found for submission: non-existent-submission"
        
        # Verify store method was called
        mock_results_store.get_result.assert_called_once_with("non-existent-submission")

    def test_get_raw_submission_results_empty_dict(self, mock_results_store):
        """Test retrieval when raw results return empty dict"""
        mock_results_store.get_result.return_value = {}
        
        response = client.get("/api/v1/results/submission/empty-submission/raw")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No results found for submission: empty-submission"

    def test_get_raw_results_format_validation(self, mock_results_store):
        """Test that raw results format is preserved exactly"""
        # Mock raw format with unprocessed data
        mock_raw_data = {
            "unprocessed_field": "raw_value",
            "nested_debug": {
                "internal_state": {"key": "value"},
                "processing_logs": ["log1", "log2"]
            },
            "timestamps": {
                "start": "2024-01-01T12:00:00Z",
                "end": "2024-01-01T12:00:05Z"
            }
        }
        
        mock_results_store.get_result.return_value = mock_raw_data
        
        response = client.get("/api/v1/results/submission/raw-format-test/raw")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify exact structure preservation
        assert data["unprocessed_field"] == "raw_value"
        assert data["nested_debug"]["internal_state"]["key"] == "value"
        assert data["nested_debug"]["processing_logs"] == ["log1", "log2"]
        assert "timestamps" in data

    # ==================== LIST ALL SUBMISSIONS ====================
    
    def test_list_all_submissions_multiple(self, mock_results_store):
        """Test listing multiple submissions"""
        mock_submissions = [
            "submission-001",
            "submission-002", 
            "submission-003",
            "test-submission-123"
        ]
        
        mock_results_store.list_all_submissions.return_value = mock_submissions
        
        response = client.get("/api/v1/results/submissions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "submissions" in data
        assert "count" in data
        assert isinstance(data["submissions"], list)
        assert isinstance(data["count"], int)
        
        assert data["count"] == 4
        assert len(data["submissions"]) == 4
        assert data["count"] == len(data["submissions"])
        
        # Verify all submissions are included
        assert "submission-001" in data["submissions"]
        assert "submission-002" in data["submissions"]
        assert "test-submission-123" in data["submissions"]
        
        # Verify store method was called
        mock_results_store.list_all_submissions.assert_called_once()

    def test_list_all_submissions_empty(self, mock_results_store):
        """Test listing when no submissions exist"""
        mock_results_store.list_all_submissions.return_value = []
        
        response = client.get("/api/v1/results/submissions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["submissions"] == []
        assert data["count"] == 0
        assert len(data["submissions"]) == data["count"]
        
        # Verify store method was called
        mock_results_store.list_all_submissions.assert_called_once()

    def test_list_all_submissions_large_list(self, mock_results_store):
        """Test listing large number of submissions"""
        # Generate large list of submissions
        mock_submissions = [f"submission-{i:04d}" for i in range(100)]
        
        mock_results_store.list_all_submissions.return_value = mock_submissions
        
        response = client.get("/api/v1/results/submissions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 100
        assert len(data["submissions"]) == 100
        assert data["submissions"][0] == "submission-0000"
        assert data["submissions"][-1] == "submission-0099"

    # ==================== CLEAR SUBMISSION RESULTS ====================
    
    def test_clear_submission_results_success(self, mock_results_store):
        """Test successful clearing of submission results"""
        mock_results_store.has_result.return_value = True
        mock_results_store.clear_result.return_value = None
        
        response = client.delete("/api/v1/results/submission/test-submission-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Results cleared for submission: test-submission-123"
        
        # Verify both store methods were called correctly
        mock_results_store.has_result.assert_called_once_with("test-submission-123")
        mock_results_store.clear_result.assert_called_once_with("test-submission-123")

    def test_clear_submission_results_not_found(self, mock_results_store):
        """Test clearing non-existent submission results"""
        mock_results_store.has_result.return_value = False
        
        response = client.delete("/api/v1/results/submission/non-existent-submission")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No results found for submission: non-existent-submission"
        
        # Verify has_result was called but clear_result was not
        mock_results_store.has_result.assert_called_once_with("non-existent-submission")
        mock_results_store.clear_result.assert_not_called()

    def test_clear_results_validation_flow(self, mock_results_store):
        """Test that clearing validates existence before clearing"""
        mock_results_store.has_result.return_value = True
        mock_results_store.clear_result.return_value = None
        
        response = client.delete("/api/v1/results/submission/validation-test")
        
        assert response.status_code == 200
        
        # Verify the validation flow: check existence first, then clear
        assert mock_results_store.has_result.call_count == 1
        assert mock_results_store.clear_result.call_count == 1
        
        # Verify both methods were called with correct parameters
        mock_results_store.has_result.assert_called_with("validation-test")
        mock_results_store.clear_result.assert_called_with("validation-test")

    # ==================== RESULTS STORE INTEGRATION ====================
    
    def test_store_method_integration(self, mock_results_store):
        """Test that all store methods are called correctly"""
        # Setup mocks for different operations
        mock_results_store.get_result_transformed.return_value = [{"test": "data"}]
        mock_results_store.get_result.return_value = {"raw": "data"}
        mock_results_store.list_all_submissions.return_value = ["sub1", "sub2"]
        mock_results_store.has_result.return_value = True
        mock_results_store.clear_result.return_value = None
        
        # Test all endpoints
        client.get("/api/v1/results/submission/test-sub")
        client.get("/api/v1/results/submission/test-sub/raw")
        client.get("/api/v1/results/submissions")
        client.delete("/api/v1/results/submission/test-sub")
        
        # Verify all methods were called with correct parameters
        mock_results_store.get_result_transformed.assert_called_with("test-sub")
        mock_results_store.get_result.assert_called_with("test-sub")
        mock_results_store.list_all_submissions.assert_called_once()
        mock_results_store.has_result.assert_called_with("test-sub")
        mock_results_store.clear_result.assert_called_with("test-sub")

    def test_store_error_handling(self, mock_results_store):
        """Test handling of store exceptions"""
        # Mock store methods to raise exceptions
        mock_results_store.get_result_transformed.side_effect = Exception("Store connection failed")
        
        # The endpoint doesn't have explicit exception handling, so FastAPI will catch it
        # and the exception will propagate during the test
        with pytest.raises(Exception, match="Store connection failed"):
            client.get("/api/v1/results/submission/error-test")

    # ==================== RESPONSE FORMAT VALIDATION ====================
    
    def test_transformed_results_format(self, mock_results_store):
        """Test that transformed results follow correct format"""
        mock_transformed_data = [
            {"field1": "value1", "field2": 123},
            {"field1": "value2", "field2": 456}
        ]
        
        mock_results_store.get_result_transformed.return_value = mock_transformed_data
        
        response = client.get("/api/v1/results/submission/format-test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list)
        
        # Verify each item is a dict
        for item in data:
            assert isinstance(item, dict)
        
        # Verify data integrity
        assert len(data) == 2
        assert data[0]["field1"] == "value1"
        assert data[1]["field2"] == 456

    def test_raw_results_format(self, mock_results_store):
        """Test that raw results follow correct format"""
        mock_raw_data = {
            "submission_id": "test",
            "nested_data": {"key": "value"},
            "array_data": [1, 2, 3]
        }
        
        mock_results_store.get_result.return_value = mock_raw_data
        
        response = client.get("/api/v1/results/submission/format-test/raw")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a dict
        assert isinstance(data, dict)
        
        # Verify structure preservation
        assert data["submission_id"] == "test"
        assert isinstance(data["nested_data"], dict)
        assert isinstance(data["array_data"], list)

    def test_submissions_list_format(self, mock_results_store):
        """Test that submissions list follows correct format"""
        mock_submissions = ["sub1", "sub2", "sub3"]
        mock_results_store.list_all_submissions.return_value = mock_submissions
        
        response = client.get("/api/v1/results/submissions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert "submissions" in data
        assert "count" in data
        
        # Verify field types
        assert isinstance(data["submissions"], list)
        assert isinstance(data["count"], int)
        
        # Verify count calculation
        assert data["count"] == len(data["submissions"])
        assert data["count"] == 3

    # ==================== ERROR HANDLING ====================
    
    def test_invalid_submission_url_format(self, mock_results_store):
        """Test handling of invalid submission URL characters"""
        # URLs with special characters should be handled by FastAPI URL encoding
        mock_results_store.get_result_transformed.return_value = None
        
        # Test with URL-encoded special characters
        response = client.get("/api/v1/results/submission/test%20submission%21")
        
        assert response.status_code == 404
        
        # Verify the store was called with the decoded URL
        mock_results_store.get_result_transformed.assert_called_once_with("test submission!")

    def test_url_encoding_handling(self, mock_results_store):
        """Test that URL encoding is handled correctly"""
        mock_results_store.get_result_transformed.return_value = [{"test": "data"}]
        
        # Test with various encoded characters
        response = client.get("/api/v1/results/submission/test%2Dsubmission%2D123")
        
        assert response.status_code == 200
        
        # Verify the store was called with the decoded URL
        mock_results_store.get_result_transformed.assert_called_once_with("test-submission-123")

    # ==================== PERFORMANCE CONSIDERATIONS ====================
    
    def test_large_results_data(self, mock_results_store):
        """Test handling of large results data"""
        # Create large dataset
        large_data = []
        for i in range(1000):
            large_data.append({
                "question_number": i % 10 + 1,
                "analysis_type": f"analysis_{i % 5}",
                "score": 85.5 + (i % 20),
                "large_field": "x" * 1000  # 1KB per item
            })
        
        mock_results_store.get_result_transformed.return_value = large_data
        
        response = client.get("/api/v1/results/submission/large-data-test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify large data is handled correctly
        assert len(data) == 1000
        assert isinstance(data, list)
        
        # Verify data integrity
        assert data[0]["question_number"] == 1
        assert data[999]["question_number"] == 10

    def test_concurrent_results_access(self, mock_results_store):
        """Test concurrent access to results endpoints"""
        # This is a basic test - real concurrency testing would require threading
        mock_results_store.get_result_transformed.return_value = [{"test": "data"}]
        mock_results_store.list_all_submissions.return_value = ["sub1", "sub2"]
        
        # Simulate multiple rapid requests
        responses = []
        for i in range(10):
            if i % 2 == 0:
                response = client.get(f"/api/v1/results/submission/test-{i}")
            else:
                response = client.get("/api/v1/results/submissions")
            responses.append(response)
        
        # Verify all requests were successful
        for response in responses:
            assert response.status_code == 200
        
        # Verify store methods were called correctly
        assert mock_results_store.get_result_transformed.call_count == 5
        assert mock_results_store.list_all_submissions.call_count == 5 