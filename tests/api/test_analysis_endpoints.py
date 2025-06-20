#!/usr/bin/env python3

import pytest
from fastapi.testclient import TestClient

class TestAnalysisEndpoints:
    """Test suite for analysis endpoints (called by webhooks internally)"""
    
    def test_vocabulary_analysis_endpoint(self, test_client, mock_external_services, sample_vocabulary_text):
        """Test vocabulary analysis endpoint"""
        
        print("\n📚 Testing Vocabulary Analysis Endpoint")
        print("=" * 60)
        print(f"Text: '{sample_vocabulary_text}'")
        
        # Note: The endpoint expects just the transcript as a string parameter
        response = test_client.post(
            "/api/v1/vocabulary/analyze",
            params={"transcript": sample_vocabulary_text}
        )
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields from VocabularyFeedback model
        required_fields = ["grade", "vocabulary_suggestions"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 VOCABULARY ANALYSIS RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Grade: {data.get('grade')}")
        print(f"Suggestions Count: {len(data.get('vocabulary_suggestions', {}))}")
        
        # Validate data types
        assert isinstance(data["grade"], (int, float)), "Grade should be numeric"
        assert isinstance(data["vocabulary_suggestions"], dict), "Vocabulary suggestions should be dict"
        assert 0 <= data["grade"] <= 100, "Grade should be between 0 and 100"
        
        print("✅ Vocabulary analysis endpoint working correctly!")
    
    def test_grammar_analysis_endpoint(self, test_client, mock_external_services, sample_grammar_text):
        """Test grammar analysis endpoint"""
        
        print("\n📝 Testing Grammar Analysis Endpoint")
        print("=" * 60)
        print(f"Text: '{sample_grammar_text}'")
        
        request_data = {
            "transcript": sample_grammar_text,
            "question_number": 1
        }
        
        response = test_client.post("/api/v1/grammar/analysis", json=request_data)
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields from GrammarResponse model
        required_fields = ["status", "grammar_corrections", "grade"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 GRAMMAR ANALYSIS RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Status: {data.get('status')}")
        print(f"Grade: {data.get('grade')}")
        print(f"Corrections Count: {len(data.get('grammar_corrections', {}))}")
        
        # Validate data types
        assert isinstance(data["status"], str), "Status should be string"
        assert isinstance(data["grammar_corrections"], dict), "Grammar corrections should be dict"
        assert isinstance(data["grade"], (int, float, type(None))), "Grade should be numeric or None"
        
        if data["grade"] is not None:
            assert 0 <= data["grade"] <= 100, "Grade should be between 0 and 100"
        
        print("✅ Grammar analysis endpoint working correctly!")
    
    def test_fluency_analysis_endpoint(self, test_client, mock_external_services):
        """Test fluency analysis endpoint"""
        
        print("\n💫 Testing Fluency Analysis Endpoint")
        print("=" * 60)
        
        request_data = {
            "reference_text": "This is a test sentence for fluency analysis.",
            "word_details": [
                {
                    "word": "This",
                    "offset": 0.0,
                    "duration": 0.5,
                    "accuracy_score": 90,
                    "error_type": "None"
                },
                {
                    "word": "is",
                    "offset": 0.5,
                    "duration": 0.3,
                    "accuracy_score": 95,
                    "error_type": "None"
                }
            ]
        }
        
        response = test_client.post("/api/v1/fluency/analysis", json=request_data)
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields from SimpleFluencyResponse
        required_fields = ["grade", "issues", "wpm", "filler_word_count", "cohesive_device_band_level", "status"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 FLUENCY ANALYSIS RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Status: {data.get('status')}")
        print(f"Grade: {data.get('grade')}")
        print(f"WPM: {data.get('wpm')}")
        print(f"Filler Words: {data.get('filler_word_count')}")
        print(f"Issues Count: {len(data.get('issues', []))}")
        
        # Validate data types
        assert isinstance(data["grade"], (int, float)), "Grade should be numeric"
        assert isinstance(data["wpm"], (int, float)), "WPM should be numeric"
        assert isinstance(data["filler_word_count"], int), "Filler word count should be integer"
        assert isinstance(data["issues"], list), "Issues should be list"
        assert data["cohesive_device_band_level"] in [0, 1, 3, 5, 7, 9], "Band level should be valid IELTS band"
        
        print("✅ Fluency analysis endpoint working correctly!")
    
    def test_transcription_endpoint(self, test_client, mock_external_services):
        """Test transcription endpoint"""
        
        print("\n🎤 Testing Transcription Endpoint")
        print("=" * 60)
        
        request_data = {
            "audio_url": "https://example.com/test-audio.mp3",
            "question_number": 1
        }
        
        response = test_client.post("/api/v1/transcription/audio_proccessing", json=request_data)
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields from TranscriptionResponse
        required_fields = ["text", "error"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 TRANSCRIPTION RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Text: '{data.get('text', 'N/A')}'")
        print(f"Error: {data.get('error')}")
        
        # Validate data types
        assert isinstance(data["text"], str), "Text should be string"
        
        print("✅ Transcription endpoint working correctly!")
    
    def test_pronunciation_analysis_endpoint(self, test_client, mock_external_services):
        """Test pronunciation analysis endpoint"""
        
        print("\n🗣️ Testing Pronunciation Analysis Endpoint")
        print("=" * 60)
        
        request_data = {
            "audio_file": "/tmp/test-audio.wav",  # Local file path
            "reference_text": "This is a test for pronunciation analysis",
            "question_number": 1
        }
        
        response = test_client.post("/api/v1/pronunciation/analysis", json=request_data)
        
        # Assertions  
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields from PronunciationResponse
        expected_fields = [
            "status", "audio_duration", "transcript", "overall_pronunciation_score",
            "accuracy_score", "fluency_score", "prosody_score", "completeness_score",
            "critical_errors", "filler_words", "word_details", "improvement_suggestion"
        ]
        
        for field in expected_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 PRONUNCIATION ANALYSIS RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Status: {data.get('status')}")
        print(f"Overall Score: {data.get('overall_pronunciation_score')}")
        print(f"Audio Duration: {data.get('audio_duration')}")
        print(f"Word Details Count: {len(data.get('word_details', []))}")
        
        # Validate data types and ranges
        assert isinstance(data["status"], str), "Status should be string"
        assert isinstance(data["overall_pronunciation_score"], (int, float)), "Score should be numeric"
        assert isinstance(data["word_details"], list), "Word details should be list"
        assert 0 <= data["overall_pronunciation_score"] <= 100, "Score should be 0-100"
        
        print("✅ Pronunciation analysis endpoint working correctly!")
    
    def test_analysis_endpoints_error_handling(self, test_client):
        """Test error handling across analysis endpoints"""
        
        print("\n🚨 Testing Analysis Endpoints Error Handling")
        print("=" * 60)
        
        # Test with invalid/missing data
        endpoints_and_data = [
            ("/api/v1/vocabulary/analyze", {"invalid": "data"}),  # Missing transcript
            ("/api/v1/grammar/analysis", {"invalid": "data"}),    # Missing required fields
            ("/api/v1/fluency/analysis", {}),                     # Empty data
            ("/api/v1/transcription/audio_proccessing", {}),      # Empty data
        ]
        
        for endpoint, invalid_data in endpoints_and_data:
            print(f"\nTesting {endpoint} with invalid data...")
            
            if endpoint == "/api/v1/vocabulary/analyze":
                # This endpoint uses query params
                response = test_client.post(endpoint, params=invalid_data)
            else:
                response = test_client.post(endpoint, json=invalid_data)
            
            # Should return validation error
            assert response.status_code in [422, 400, 500], f"Expected error status for {endpoint}"
            
            print(f"✅ {endpoint}: Error handled correctly ({response.status_code})")
    
    def test_analysis_endpoints_response_formats(self, test_client, mock_external_services):
        """Test that all analysis endpoints return properly formatted responses"""
        
        print("\n📋 Testing Analysis Endpoints Response Formats")
        print("=" * 60)
        
        # Test vocabulary
        vocab_response = test_client.post(
            "/api/v1/vocabulary/analyze",
            params={"transcript": "test text"}
        )
        assert vocab_response.status_code == 200
        vocab_data = vocab_response.json()
        assert "grade" in vocab_data and "vocabulary_suggestions" in vocab_data
        
        # Test grammar  
        grammar_response = test_client.post(
            "/api/v1/grammar/analysis",
            json={"transcript": "test text", "question_number": 1}
        )
        assert grammar_response.status_code == 200
        grammar_data = grammar_response.json()
        assert "status" in grammar_data and "grammar_corrections" in grammar_data
        
        print("✅ All analysis endpoints return properly formatted responses!") 