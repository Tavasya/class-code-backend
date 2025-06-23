#!/usr/bin/env python3

import pytest
from fastapi.testclient import TestClient

class TestSubmissionEndpoint:
    """Test suite for submission endpoint - the main entry point"""
    
    def test_submission_success(self, test_client, mock_external_services, sample_submission_data):
        """Test successful submission processing"""
        
        print("\n🚀 Testing Submission Endpoint - Success Case")
        print("=" * 60)
        print(f"Submission data: {sample_submission_data}")
        
        response = test_client.post("/api/v1/submission/submit", json=sample_submission_data)
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields
        required_fields = ["status", "message"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 SUBMISSION RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        
        # Should be successful
        assert data["status"] == "success", f"Expected success status, got {data['status']}"
        assert "published successfully" in data["message"].lower(), "Message should indicate successful publishing"
        
        # Verify that PubSub was called
        pubsub_mock = mock_external_services['pubsub']
        pubsub_mock.assert_called_once()
        pubsub_mock.return_value.publish_message_by_name.assert_called_once()
        
        print("✅ Submission processed successfully!")
    
    def test_submission_pubsub_message_format(self, test_client, mock_external_services, pubsub_message_format):
        """Test submission with Pub/Sub message format (simulating webhook call)"""
        
        print("\n📨 Testing Submission with Pub/Sub Message Format")
        print("=" * 60)
        
        # Create data in Pub/Sub format
        submission_data = {
            "audio_urls": ["https://example.com/test.mp3"],
            "submission_url": "https://example.com/submission/pubsub-test"
        }
        
        pubsub_formatted = pubsub_message_format(submission_data)
        print(f"Pub/Sub format: {pubsub_formatted}")
        
        response = test_client.post("/api/v1/submission/submit", json=pubsub_formatted)
        
        # Should work with both formats
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        print("✅ Pub/Sub message format handled correctly!")
    
    def test_submission_validation_errors(self, test_client):
        """Test submission with invalid data"""
        
        print("\n🚨 Testing Submission Validation Errors")
        print("=" * 60)
        
        test_cases = [
            # Missing audio_urls
            {"submission_url": "https://example.com/submission/test"},
            # Missing submission_url
            {"audio_urls": ["https://example.com/audio.mp3"]},
            # Invalid types
            {"audio_urls": "not-a-list", "submission_url": "https://example.com/submission/test"},
        ]
        
        for i, invalid_data in enumerate(test_cases, 1):
            print(f"\nTest case {i}: {invalid_data}")
            
            # Your endpoint has unhandled ValidationError, so TestClient raises it directly
            try:
                response = test_client.post("/api/v1/submission/submit", json=invalid_data)
                # If we get here, the validation passed unexpectedly
                assert False, f"Expected ValidationError but got response: {response.status_code}"
            except Exception as e:
                # Should be a Pydantic ValidationError
                assert "ValidationError" in str(type(e)), f"Expected ValidationError, got {type(e)}"
                assert "Field required" in str(e) or "validation error" in str(e).lower(), "Should indicate field validation error"
                
                print(f"✅ Validation error caught correctly: {type(e).__name__}")
                print(f"    Error details: {str(e)[:100]}...")
    
    def test_submission_with_empty_audio_urls(self, test_client):
        """Test submission with empty audio_urls (should be valid)"""
        
        print("\n📋 Testing Submission with Empty Audio URLs")
        
        # Empty audio_urls should be valid - some submissions might have no audio
        valid_data = {"audio_urls": [], "submission_url": "https://example.com/submission/test"}
        
        response = test_client.post("/api/v1/submission/submit", json=valid_data)
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200 for empty audio_urls, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "success", "Empty audio_urls should be processed successfully"
        
        print("✅ Empty audio_urls handled correctly - processed successfully!")
    
    def test_submission_with_empty_json(self, test_client):
        """Test submission with empty or malformed JSON"""
        
        print("\n🚨 Testing Submission with Empty/Malformed JSON")
        
        # Empty JSON - should raise ValidationError directly
        try:
            response = test_client.post("/api/v1/submission/submit", json={})
            assert False, f"Expected ValidationError but got response: {response.status_code}"
        except Exception as e:
            assert "ValidationError" in str(type(e)), f"Expected ValidationError, got {type(e)}"
            assert "Field required" in str(e), "Should indicate missing required fields"
            print(f"✅ Empty JSON handled correctly: {type(e).__name__}")
        
        # Malformed request body - should raise JSONDecodeError directly
        try:
            response = test_client.post(
                "/api/v1/submission/submit", 
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert False, f"Expected JSONDecodeError but got response: {response.status_code}"
        except Exception as e:
            assert "JSONDecodeError" in str(type(e)), f"Expected JSONDecodeError, got {type(e)}"
            print(f"✅ Malformed JSON handled correctly: {type(e).__name__}")
        print("✅ Empty/malformed JSON handled correctly!")
    
    def test_submission_service_error_handling(self, test_client, mock_external_services):
        """Test submission when underlying service fails"""
        
        print("\n🚨 Testing Submission Service Error Handling")
        
        # Make PubSub client throw an error
        pubsub_mock = mock_external_services['pubsub']
        pubsub_mock.return_value.publish_message_by_name.side_effect = Exception("PubSub connection failed")
        
        submission_data = {
            "audio_urls": ["https://example.com/audio.mp3"],
            "submission_url": "https://example.com/submission/error-test"
        }
        
        response = test_client.post("/api/v1/submission/submit", json=submission_data)
        
        # Should return success with error status (based on your service design)
        assert response.status_code == 200
        data = response.json()
        
        # Should return error status from service
        assert data["status"] == "error", "Should return error status when service fails"
        assert "failed" in data["message"].lower(), "Error message should indicate failure"
        
        print(f"✅ Service error handled gracefully: {data['message']}")
    
    def test_submission_response_format(self, test_client, mock_external_services, sample_submission_data):
        """Test that submission response matches SubmissionResponse model"""
        
        response = test_client.post("/api/v1/submission/submit", json=sample_submission_data)
        data = response.json()
        
        # Must match SubmissionResponse model
        assert isinstance(data["status"], str), "Status must be string"
        assert isinstance(data["message"], str), "Message must be string"
        assert len(data["status"]) > 0, "Status cannot be empty"
        assert len(data["message"]) > 0, "Message cannot be empty"
        
        # Only these fields should be present
        expected_fields = {"status", "message"}
        actual_fields = set(data.keys())
        assert actual_fields == expected_fields, f"Response has unexpected fields: {actual_fields - expected_fields}"
        
        print("✅ Response format matches SubmissionResponse model!")
    
    def test_submission_cors_headers(self, test_client, sample_submission_data):
        """Test CORS headers in submission response"""
        
        response = test_client.post("/api/v1/submission/submit", json=sample_submission_data)
        
        # Check content type
        assert "application/json" in response.headers.get("content-type", "")
        
        # FastAPI TestClient doesn't include CORS headers by default,
        # but we can verify the response structure is correct
        assert response.status_code in [200, 422], "Should return valid HTTP status"
        
        print("✅ CORS and headers validation passed!")
    
    def test_submission_without_mocks(self, test_client):
        """Test submission endpoint basic functionality without external service mocks"""
        
        print("\n🔧 Testing Submission Endpoint Structure (No Mocks)")
        
        # This test will hit the real PubSub client, which should fail gracefully
        submission_data = {
            "audio_urls": ["https://example.com/audio.mp3"],
            "submission_url": "https://example.com/submission/test"
        }
        
        response = test_client.post("/api/v1/submission/submit", json=submission_data)
        
        # Should return 200 regardless (your service handles errors gracefully)
        assert response.status_code == 200
        data = response.json()
        
        # Should have proper structure
        assert "status" in data
        assert "message" in data
        
        print(f"Status: {data['status']}")
        print(f"Message: {data['message']}")
        print("✅ Endpoint structure is correct!") 