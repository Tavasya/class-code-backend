#!/usr/bin/env python3

import pytest
from fastapi.testclient import TestClient

class TestHealthEndpoint:
    """Test suite for health check endpoint"""
    
    def test_health_check_success(self, test_client):
        """Test successful health check"""
        
        print("\n🏥 Testing Health Check Endpoint")
        print("=" * 50)
        
        response = test_client.get("/api/v1/health/")
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dictionary"
        
        # Required fields
        required_fields = ["status", "timestamp", "environment", "supabase"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Display results
        print("📊 HEALTH CHECK RESULTS:")
        print(f"Status Code: {response.status_code}")
        print(f"Status: {data.get('status')}")
        print(f"Environment: {data.get('environment')}")
        print(f"Supabase: {data.get('supabase')}")
        print(f"Timestamp: {data.get('timestamp')}")
        
        # Validate data types
        assert isinstance(data["status"], str), "Status should be string"
        assert isinstance(data["timestamp"], str), "Timestamp should be string"
        assert isinstance(data["environment"], str), "Environment should be string"
        assert isinstance(data["supabase"], str), "Supabase status should be string"
        
        print("✅ Health check endpoint working correctly!")
    
    def test_health_check_response_format(self, test_client):
        """Test that health check response matches expected format"""
        
        response = test_client.get("/api/v1/health/")
        data = response.json()
        
        # Check timestamp format (should be ISO format)
        timestamp = data.get("timestamp")
        assert "T" in timestamp, "Timestamp should be in ISO format"
        assert len(timestamp) > 10, "Timestamp should be detailed"
        
        # Check status values
        status = data.get("status")
        assert len(status) > 0, "Status should not be empty"
        
        # Check environment
        environment = data.get("environment")
        assert environment in ["development", "staging", "production"], f"Unknown environment: {environment}"
        
        print(f"✅ Response format validation passed")
    
    def test_health_check_headers(self, test_client):
        """Test health check response headers"""
        
        response = test_client.get("/api/v1/health/")
        
        # Check content type
        assert "application/json" in response.headers.get("content-type", ""), "Should return JSON"
        
        # Check that response has proper headers
        assert response.headers.get("content-length"), "Should have content-length header"
        
        print("✅ Response headers validation passed") 