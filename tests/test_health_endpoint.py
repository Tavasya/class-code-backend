import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
import os
from app.main import app

client = TestClient(app)

def test_health_check_success():
    """Test basic health check returns correct response"""
    with patch('app.core.config.supabase', MagicMock()):
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "STAGE BRANCH ISS HEALTHYY"
        assert "timestamp" in data
        assert "environment" in data
        assert data["supabase"] == "connected"

def test_supabase_connected():
    """Test health check when Supabase is connected"""
    with patch('app.core.config.supabase', MagicMock()):
        response = client.get("/api/v1/health/")
        data = response.json()
        
        assert data["supabase"] == "connected"


def test_environment_default():
    """Test default environment when not set"""
    with patch('app.core.config.supabase', MagicMock()):
        with patch.dict(os.environ, {}, clear=True):
            response = client.get("/api/v1/health/")
            data = response.json()
            
            assert data["environment"] == "development"

def test_environment_custom():
    """Test custom environment setting"""
    with patch('app.core.config.supabase', MagicMock()):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            response = client.get("/api/v1/health/")
            data = response.json()
            
            assert data["environment"] == "production" 