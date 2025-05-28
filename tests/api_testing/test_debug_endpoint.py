import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_file_manager():
    """Mock file_manager for testing"""
    with patch('app.api.v1.endpoints.debug_endpoint.file_manager') as mock:
        yield mock

class TestDebugEndpoint:
    """Test cases for debug endpoint"""

    # ==================== GET ACTIVE FILE SESSIONS ====================
    
    def test_get_active_file_sessions_success(self, mock_file_manager):
        """Test successful retrieval of active file sessions"""
        # Mock active sessions data
        mock_sessions_data = {
            "session-001": {
                "created_at": "2024-01-01T12:00:00Z",
                "files": ["file1.mp3", "file2.wav"],
                "status": "active"
            },
            "session-002": {
                "created_at": "2024-01-01T12:05:00Z", 
                "files": ["file3.mp3"],
                "status": "processing"
            },
            "session-003": {
                "created_at": "2024-01-01T12:10:00Z",
                "files": [],
                "status": "idle"
            }
        }
        
        mock_file_manager.get_active_sessions.return_value = mock_sessions_data
        
        response = client.get("/api/v1/debug/file-sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "active_sessions" in data
        assert "total_active" in data
        assert data["total_active"] == 3
        assert len(data["active_sessions"]) == 3
        
        # Verify session data structure
        assert "session-001" in data["active_sessions"]
        assert "session-002" in data["active_sessions"]
        assert "session-003" in data["active_sessions"]
        
        # Verify session details
        session_001 = data["active_sessions"]["session-001"]
        assert session_001["status"] == "active"
        assert len(session_001["files"]) == 2
        
        # Verify file_manager method was called
        mock_file_manager.get_active_sessions.assert_called_once()

    def test_get_active_file_sessions_empty(self, mock_file_manager):
        """Test retrieval when no active sessions exist"""
        mock_file_manager.get_active_sessions.return_value = {}
        
        response = client.get("/api/v1/debug/file-sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["active_sessions"] == {}
        assert data["total_active"] == 0
        
        # Verify file_manager method was called
        mock_file_manager.get_active_sessions.assert_called_once()

    def test_get_active_file_sessions_error(self, mock_file_manager):
        """Test handling of file manager error"""
        mock_file_manager.get_active_sessions.side_effect = Exception("File manager connection failed")
        
        response = client.get("/api/v1/debug/file-sessions")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error getting file sessions: File manager connection failed" in data["detail"]
        
        # Verify file_manager method was called
        mock_file_manager.get_active_sessions.assert_called_once()

    def test_get_active_file_sessions_large_dataset(self, mock_file_manager):
        """Test handling of large number of active sessions"""
        # Create large dataset
        large_sessions = {}
        for i in range(100):
            large_sessions[f"session-{i:03d}"] = {
                "created_at": f"2024-01-01T{i%24:02d}:00:00Z",
                "files": [f"file{i}.mp3"],
                "status": "active" if i % 2 == 0 else "processing"
            }
        
        mock_file_manager.get_active_sessions.return_value = large_sessions
        
        response = client.get("/api/v1/debug/file-sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_active"] == 100
        assert len(data["active_sessions"]) == 100
        assert "session-000" in data["active_sessions"]
        assert "session-099" in data["active_sessions"]

    # ==================== FORCE CLEANUP SESSION ====================
    
    def test_force_cleanup_session_success(self, mock_file_manager):
        """Test successful session cleanup"""
        # Mock session info and cleanup
        mock_session_info = {
            "session_id": "test-session-123",
            "created_at": "2024-01-01T12:00:00Z",
            "files": ["file1.mp3", "file2.wav"],
            "status": "active"
        }
        
        mock_file_manager.get_session_info.return_value = mock_session_info
        mock_file_manager.force_cleanup_session = AsyncMock()
        
        response = client.post("/api/v1/debug/cleanup-session/test-session-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["message"] == "Forced cleanup of session test-session-123"
        
        # Verify both file_manager methods were called
        mock_file_manager.get_session_info.assert_called_once_with("test-session-123")
        mock_file_manager.force_cleanup_session.assert_called_once_with("test-session-123")

    def test_force_cleanup_session_not_found(self, mock_file_manager):
        """Test cleanup of non-existent session"""
        mock_file_manager.get_session_info.return_value = None
        mock_file_manager.force_cleanup_session = AsyncMock()
        
        response = client.post("/api/v1/debug/cleanup-session/non-existent-session")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Session non-existent-session not found"
        
        # Verify get_session_info was called but force_cleanup_session was not
        mock_file_manager.get_session_info.assert_called_once_with("non-existent-session")
        mock_file_manager.force_cleanup_session.assert_not_called()

    def test_force_cleanup_session_cleanup_failure(self, mock_file_manager):
        """Test cleanup operation failure"""
        # Mock session exists but cleanup fails
        mock_session_info = {
            "session_id": "failing-session",
            "status": "active"
        }
        
        mock_file_manager.get_session_info.return_value = mock_session_info
        mock_file_manager.force_cleanup_session = AsyncMock(side_effect=Exception("Cleanup operation failed"))
        
        response = client.post("/api/v1/debug/cleanup-session/failing-session")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error cleaning up session: Cleanup operation failed" in data["detail"]
        
        # Verify both methods were called
        mock_file_manager.get_session_info.assert_called_once_with("failing-session")
        mock_file_manager.force_cleanup_session.assert_called_once_with("failing-session")

    def test_force_cleanup_session_validation_flow(self, mock_file_manager):
        """Test that cleanup validates session existence before cleanup"""
        mock_session_info = {"session_id": "validation-test", "status": "active"}
        mock_file_manager.get_session_info.return_value = mock_session_info
        mock_file_manager.force_cleanup_session = AsyncMock()
        
        response = client.post("/api/v1/debug/cleanup-session/validation-test")
        
        assert response.status_code == 200
        
        # Verify validation occurs before cleanup
        mock_file_manager.get_session_info.assert_called_once_with("validation-test")
        mock_file_manager.force_cleanup_session.assert_called_once_with("validation-test")

    def test_force_cleanup_session_special_characters(self, mock_file_manager):
        """Test cleanup with special characters in session ID"""
        session_id = "test-session-with-special-chars!@#"
        mock_session_info = {"session_id": session_id, "status": "active"}
        mock_file_manager.get_session_info.return_value = mock_session_info
        mock_file_manager.force_cleanup_session = AsyncMock()
        
        # URL encode the session ID for the request
        import urllib.parse
        encoded_session_id = urllib.parse.quote(session_id, safe='')
        
        response = client.post(f"/api/v1/debug/cleanup-session/{encoded_session_id}")
        
        assert response.status_code == 200
        
        # Verify the decoded session ID was used
        mock_file_manager.get_session_info.assert_called_once_with(session_id)
        mock_file_manager.force_cleanup_session.assert_called_once_with(session_id)

    # ==================== TRIGGER PERIODIC CLEANUP ====================
    
    def test_trigger_periodic_cleanup_success(self, mock_file_manager):
        """Test successful periodic cleanup"""
        mock_file_manager.periodic_cleanup = AsyncMock()
        
        response = client.post("/api/v1/debug/periodic-cleanup")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["message"] == "Periodic cleanup completed"
        
        # Verify periodic_cleanup was called
        mock_file_manager.periodic_cleanup.assert_called_once()

    def test_trigger_periodic_cleanup_failure(self, mock_file_manager):
        """Test periodic cleanup failure"""
        mock_file_manager.periodic_cleanup = AsyncMock(side_effect=Exception("Periodic cleanup failed"))
        
        response = client.post("/api/v1/debug/periodic-cleanup")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error in periodic cleanup: Periodic cleanup failed" in data["detail"]
        
        # Verify periodic_cleanup was called
        mock_file_manager.periodic_cleanup.assert_called_once()

    def test_trigger_periodic_cleanup_performance(self, mock_file_manager):
        """Test periodic cleanup with simulated processing delay"""
        import asyncio
        
        async def slow_cleanup():
            await asyncio.sleep(0.1)  # Simulate processing time
            return None
        
        mock_file_manager.periodic_cleanup = AsyncMock(side_effect=slow_cleanup)
        
        response = client.post("/api/v1/debug/periodic-cleanup")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify cleanup was called
        mock_file_manager.periodic_cleanup.assert_called_once()

    # ==================== FILE MANAGER INTEGRATION ====================
    
    def test_file_manager_service_integration(self, mock_file_manager):
        """Test integration with file manager service across all endpoints"""
        # Setup mocks for all operations
        mock_file_manager.get_active_sessions.return_value = {"session-1": {"status": "active"}}
        mock_file_manager.get_session_info.return_value = {"session_id": "test-session", "status": "active"}
        mock_file_manager.force_cleanup_session = AsyncMock()
        mock_file_manager.periodic_cleanup = AsyncMock()
        
        # Test all endpoints
        client.get("/api/v1/debug/file-sessions")
        client.post("/api/v1/debug/cleanup-session/test-session")
        client.post("/api/v1/debug/periodic-cleanup")
        
        # Verify all methods were called correctly
        mock_file_manager.get_active_sessions.assert_called_once()
        mock_file_manager.get_session_info.assert_called_once_with("test-session")
        mock_file_manager.force_cleanup_session.assert_called_once_with("test-session")
        mock_file_manager.periodic_cleanup.assert_called_once()

    def test_file_manager_service_degradation(self, mock_file_manager):
        """Test handling of intermittent file manager failures"""
        # Mock intermittent failures
        mock_file_manager.get_active_sessions.side_effect = Exception("Service temporarily unavailable")
        mock_file_manager.periodic_cleanup = AsyncMock(side_effect=Exception("Service degraded"))
        
        # Test endpoints during service issues
        response1 = client.get("/api/v1/debug/file-sessions")
        response2 = client.post("/api/v1/debug/periodic-cleanup")
        
        # Verify errors are handled gracefully
        assert response1.status_code == 500
        assert response2.status_code == 500
        assert "Service temporarily unavailable" in response1.json()["detail"]
        assert "Service degraded" in response2.json()["detail"]

    # ==================== SESSION INFORMATION VALIDATION ====================
    
    def test_session_data_format_validation(self, mock_file_manager):
        """Test validation of session data format"""
        # Mock complete session data with all metadata
        mock_complete_sessions = {
            "session-complete": {
                "session_id": "session-complete",
                "created_at": "2024-01-01T12:00:00Z",
                "last_accessed": "2024-01-01T12:30:00Z",
                "files": ["file1.mp3", "file2.wav"],
                "status": "active",
                "metadata": {
                    "user_id": "user123",
                    "upload_count": 2,
                    "total_size": 1024000
                }
            }
        }
        
        mock_file_manager.get_active_sessions.return_value = mock_complete_sessions
        
        response = client.get("/api/v1/debug/file-sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        session_data = data["active_sessions"]["session-complete"]
        
        # Verify all required fields are present
        assert "session_id" in session_data
        assert "created_at" in session_data
        assert "files" in session_data
        assert "status" in session_data
        assert "metadata" in session_data
        
        # Verify data types
        assert isinstance(session_data["files"], list)
        assert isinstance(session_data["metadata"], dict)
        assert session_data["metadata"]["upload_count"] == 2

    def test_session_state_consistency(self, mock_file_manager):
        """Test session state consistency across operations"""
        # Mock session in different states
        mock_sessions = {
            "session-active": {"status": "active", "files": ["file1.mp3"]},
            "session-processing": {"status": "processing", "files": ["file2.wav"]},
            "session-idle": {"status": "idle", "files": []}
        }
        
        mock_file_manager.get_active_sessions.return_value = mock_sessions
        mock_file_manager.get_session_info.return_value = mock_sessions["session-active"]
        mock_file_manager.force_cleanup_session = AsyncMock()
        
        # Query sessions
        response1 = client.get("/api/v1/debug/file-sessions")
        assert response1.status_code == 200
        
        # Cleanup a session
        response2 = client.post("/api/v1/debug/cleanup-session/session-active")
        assert response2.status_code == 200
        
        # Verify state consistency
        sessions_data = response1.json()["active_sessions"]
        assert sessions_data["session-active"]["status"] == "active"
        assert sessions_data["session-processing"]["status"] == "processing"
        assert sessions_data["session-idle"]["status"] == "idle"

    # ==================== ERROR HANDLING AND LOGGING ====================
    
    def test_comprehensive_error_logging(self, mock_file_manager):
        """Test error logging across different scenarios"""
        # Test various error conditions
        error_scenarios = [
            ("get_active_sessions", Exception("Database connection failed")),
            ("periodic_cleanup", Exception("Disk space insufficient")),
        ]
        
        for method_name, exception in error_scenarios:
            # Reset mocks
            mock_file_manager.reset_mock()
            
            if method_name == "get_active_sessions":
                mock_file_manager.get_active_sessions.side_effect = exception
                response = client.get("/api/v1/debug/file-sessions")
            elif method_name == "periodic_cleanup":
                mock_file_manager.periodic_cleanup = AsyncMock(side_effect=exception)
                response = client.post("/api/v1/debug/periodic-cleanup")
            
            # Verify error handling
            assert response.status_code == 500
            assert str(exception) in response.json()["detail"]

    def test_error_response_consistency(self, mock_file_manager):
        """Test consistency of error responses across endpoints"""
        # Mock different error conditions
        mock_file_manager.get_active_sessions.side_effect = Exception("Test error 1")
        mock_file_manager.get_session_info.return_value = None  # For 404 error
        mock_file_manager.periodic_cleanup = AsyncMock(side_effect=Exception("Test error 2"))
        
        # Test all endpoints for error handling
        response1 = client.get("/api/v1/debug/file-sessions")
        response2 = client.post("/api/v1/debug/cleanup-session/non-existent")
        response3 = client.post("/api/v1/debug/periodic-cleanup")
        
        # Verify consistent error response format
        assert response1.status_code == 500
        assert response2.status_code == 404
        assert response3.status_code == 500
        
        # Verify all responses have detail field
        assert "detail" in response1.json()
        assert "detail" in response2.json()
        assert "detail" in response3.json()

    # ==================== PERFORMANCE AND MONITORING ====================
    
    def test_debug_endpoint_performance(self, mock_file_manager):
        """Test performance of debug endpoints"""
        # Mock normal operations
        mock_file_manager.get_active_sessions.return_value = {"session-1": {"status": "active"}}
        mock_file_manager.get_session_info.return_value = {"session_id": "test", "status": "active"}
        mock_file_manager.force_cleanup_session = AsyncMock()
        mock_file_manager.periodic_cleanup = AsyncMock()
        
        # Test all endpoints for performance
        import time
        
        start_time = time.time()
        response1 = client.get("/api/v1/debug/file-sessions")
        response2 = client.post("/api/v1/debug/cleanup-session/test")
        response3 = client.post("/api/v1/debug/periodic-cleanup")
        end_time = time.time()
        
        # Verify all requests completed successfully
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        # Verify reasonable response time (should be very fast with mocks)
        total_time = end_time - start_time
        assert total_time < 1.0  # Should complete within 1 second

    def test_concurrent_debug_operations(self, mock_file_manager):
        """Test concurrent access to debug endpoints"""
        # Mock file manager for concurrent access
        mock_file_manager.get_active_sessions.return_value = {"session-1": {"status": "active"}}
        mock_file_manager.periodic_cleanup = AsyncMock()
        
        # Simulate multiple rapid requests
        responses = []
        for i in range(10):
            if i % 2 == 0:
                response = client.get("/api/v1/debug/file-sessions")
            else:
                response = client.post("/api/v1/debug/periodic-cleanup")
            responses.append(response)
        
        # Verify all requests were successful
        for response in responses:
            assert response.status_code == 200
        
        # Verify methods were called correct number of times
        assert mock_file_manager.get_active_sessions.call_count == 5
        assert mock_file_manager.periodic_cleanup.call_count == 5

    # ==================== INTEGRATION WITH FILE MANAGEMENT ====================
    
    def test_file_lifecycle_monitoring(self, mock_file_manager):
        """Test monitoring of file lifecycle through debug endpoints"""
        # Mock files in various lifecycle stages
        mock_sessions_with_files = {
            "session-uploading": {
                "status": "uploading",
                "files": ["temp_file1.mp3"],
                "lifecycle_stage": "upload_in_progress"
            },
            "session-processing": {
                "status": "processing", 
                "files": ["file2.wav", "file3.mp3"],
                "lifecycle_stage": "analysis_in_progress"
            },
            "session-completed": {
                "status": "completed",
                "files": ["final_file.mp3"],
                "lifecycle_stage": "analysis_complete"
            }
        }
        
        mock_file_manager.get_active_sessions.return_value = mock_sessions_with_files
        
        response = client.get("/api/v1/debug/file-sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify file lifecycle information is tracked
        sessions = data["active_sessions"]
        assert sessions["session-uploading"]["lifecycle_stage"] == "upload_in_progress"
        assert sessions["session-processing"]["lifecycle_stage"] == "analysis_in_progress"
        assert sessions["session-completed"]["lifecycle_stage"] == "analysis_complete"
        
        # Verify file counts per session
        assert len(sessions["session-uploading"]["files"]) == 1
        assert len(sessions["session-processing"]["files"]) == 2
        assert len(sessions["session-completed"]["files"]) == 1

    def test_resource_management_validation(self, mock_file_manager):
        """Test resource management through debug endpoints"""
        # Mock resource tracking data
        mock_sessions_with_resources = {
            "session-heavy": {
                "status": "active",
                "files": ["large_file1.mp3", "large_file2.wav"],
                "resource_usage": {
                    "memory_mb": 512,
                    "disk_space_mb": 1024,
                    "cpu_percent": 25.5
                }
            },
            "session-light": {
                "status": "idle",
                "files": ["small_file.mp3"],
                "resource_usage": {
                    "memory_mb": 64,
                    "disk_space_mb": 128,
                    "cpu_percent": 2.1
                }
            }
        }
        
        mock_file_manager.get_active_sessions.return_value = mock_sessions_with_resources
        mock_file_manager.get_session_info.return_value = mock_sessions_with_resources["session-heavy"]
        mock_file_manager.force_cleanup_session = AsyncMock()
        
        # Monitor resource usage
        response1 = client.get("/api/v1/debug/file-sessions")
        assert response1.status_code == 200
        
        # Test cleanup of resource-heavy session
        response2 = client.post("/api/v1/debug/cleanup-session/session-heavy")
        assert response2.status_code == 200
        
        # Verify resource information is available
        sessions = response1.json()["active_sessions"]
        heavy_session = sessions["session-heavy"]
        light_session = sessions["session-light"]
        
        assert heavy_session["resource_usage"]["memory_mb"] == 512
        assert light_session["resource_usage"]["memory_mb"] == 64
        assert heavy_session["resource_usage"]["cpu_percent"] > light_session["resource_usage"]["cpu_percent"] 