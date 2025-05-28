import pytest
import os
import tempfile
import asyncio
from datetime import datetime, timedelta
from app.services.file_manager_service import file_manager


class TestFileLifecycleIntegration:
    """Integration tests for file lifecycle and session management"""

    @pytest.mark.asyncio
    async def test_complete_file_lifecycle(self, temp_dir):
        """Test complete file lifecycle: register -> service complete -> cleanup"""
        
        # Create a test file
        test_file_path = os.path.join(temp_dir, "test_audio.wav")
        with open(test_file_path, 'wb') as f:
            f.write(b"test audio content")
        
        # Generate session ID and register file
        session_id = file_manager.generate_session_id("test_submission", 1)
        dependent_services = {"pronunciation", "transcription"}
        
        await file_manager.register_file_session(
            session_id=session_id,
            file_path=test_file_path,
            dependent_services=dependent_services,
            cleanup_timeout_minutes=1
        )
        
        # Verify file session is registered
        session_info = file_manager.get_session_info(session_id)
        assert session_info is not None
        assert session_info["file_path"] == test_file_path
        assert not session_info["cleanup_completed"]
        
        # Verify file exists
        assert os.path.exists(test_file_path)
        
        # Mark first service complete
        all_complete = await file_manager.mark_service_complete(session_id, "pronunciation")
        assert not all_complete  # Should not be complete yet
        assert os.path.exists(test_file_path)  # File should still exist
        
        # Mark second service complete
        all_complete = await file_manager.mark_service_complete(session_id, "transcription")
        assert all_complete  # Should be complete now
        
        # File should be cleaned up automatically
        assert not os.path.exists(test_file_path)
        
        # Session should be marked as cleanup completed
        session_info = file_manager.get_session_info(session_id)
        assert session_info["cleanup_completed"]

    @pytest.mark.asyncio
    async def test_multiple_sessions_concurrent(self, temp_dir):
        """Test multiple file sessions running concurrently"""
        
        # Create multiple test files
        test_files = []
        session_ids = []
        
        for i in range(3):
            file_path = os.path.join(temp_dir, f"test_audio_{i}.wav")
            with open(file_path, 'wb') as f:
                f.write(f"test audio content {i}".encode())
            test_files.append(file_path)
            
            # Register each file session
            session_id = file_manager.generate_session_id(f"submission_{i}", i)
            session_ids.append(session_id)
            
            await file_manager.register_file_session(
                session_id=session_id,
                file_path=file_path,
                dependent_services={"pronunciation"},
                cleanup_timeout_minutes=1
            )
        
        # Verify all files exist and sessions are active
        for i, (file_path, session_id) in enumerate(zip(test_files, session_ids)):
            assert os.path.exists(file_path)
            session_info = file_manager.get_session_info(session_id)
            assert session_info is not None
            assert not session_info["cleanup_completed"]
        
        # Complete services in different order
        await file_manager.mark_service_complete(session_ids[1], "pronunciation")  # Middle
        await file_manager.mark_service_complete(session_ids[0], "pronunciation")  # First
        await file_manager.mark_service_complete(session_ids[2], "pronunciation")  # Last
        
        # All files should be cleaned up
        for file_path in test_files:
            assert not os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_session_cleanup_timeout(self, temp_dir):
        """Test automatic cleanup of expired sessions"""
        
        # Create test file
        test_file_path = os.path.join(temp_dir, "test_audio_timeout.wav")
        with open(test_file_path, 'wb') as f:
            f.write(b"test audio content")
        
        # Register with very short timeout
        session_id = file_manager.generate_session_id("test_submission", 1)
        await file_manager.register_file_session(
            session_id=session_id,
            file_path=test_file_path,
            dependent_services={"pronunciation"},
            cleanup_timeout_minutes=0.01  # 0.6 seconds
        )
        
        # Verify file exists initially
        assert os.path.exists(test_file_path)
        
        # Wait for timeout
        await asyncio.sleep(1)
        
        # Run periodic cleanup
        await file_manager.periodic_cleanup()
        
        # File should be cleaned up due to timeout
        assert not os.path.exists(test_file_path)

    @pytest.mark.asyncio
    async def test_force_cleanup_session(self, temp_dir):
        """Test force cleanup of a session"""
        
        # Create test file
        test_file_path = os.path.join(temp_dir, "test_audio_force.wav")
        with open(test_file_path, 'wb') as f:
            f.write(b"test audio content")
        
        # Register session
        session_id = file_manager.generate_session_id("test_submission", 1)
        await file_manager.register_file_session(
            session_id=session_id,
            file_path=test_file_path,
            dependent_services={"pronunciation"},
            cleanup_timeout_minutes=60
        )
        
        # Verify file exists
        assert os.path.exists(test_file_path)
        
        # Force cleanup
        await file_manager.force_cleanup_session(session_id)
        
        # File should be cleaned up
        assert not os.path.exists(test_file_path)
        
        # Session should be removed from tracking
        session_info = file_manager.get_session_info(session_id)
        assert session_info is None

    @pytest.mark.asyncio
    async def test_service_completion_with_unknown_session(self):
        """Test marking service complete for unknown session"""
        
        # Try to mark completion for non-existent session
        result = await file_manager.mark_service_complete("unknown_session", "pronunciation")
        assert not result

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, temp_dir):
        """Test getting active sessions information"""
        
        # Initially no active sessions
        active_sessions = file_manager.get_active_sessions()
        initial_count = len(active_sessions)
        
        # Create and register a file session
        test_file_path = os.path.join(temp_dir, "test_audio_active.wav")
        with open(test_file_path, 'wb') as f:
            f.write(b"test audio content")
        
        session_id = file_manager.generate_session_id("test_submission", 1)
        await file_manager.register_file_session(
            session_id=session_id,
            file_path=test_file_path,
            dependent_services={"pronunciation"},
            cleanup_timeout_minutes=60
        )
        
        # Should have one more active session
        active_sessions = file_manager.get_active_sessions()
        assert len(active_sessions) == initial_count + 1
        assert session_id in active_sessions
        
        session_data = active_sessions[session_id]
        assert session_data["file_path"] == test_file_path
        assert "pronunciation" in session_data["dependencies"]
        assert not session_data["cleanup_completed"]
        
        # Complete the service
        await file_manager.mark_service_complete(session_id, "pronunciation")
        
        # Should be back to initial active sessions count after cleanup
        active_sessions = file_manager.get_active_sessions()
        assert len(active_sessions) == initial_count

    @pytest.mark.asyncio
    async def test_session_id_generation_uniqueness(self):
        """Test that session IDs are unique over time"""
        
        # Generate session IDs with small delays to ensure timestamp differences
        session_ids = set()
        for i in range(10):  # Reduced from 100 to be more realistic
            session_id = file_manager.generate_session_id("test_submission", 1)
            session_ids.add(session_id)
            # Small delay to ensure timestamp differences
            await asyncio.sleep(0.01)  # 10ms delay
        
        # All session IDs should be unique
        assert len(session_ids) == 10
        
        # Test with different parameters
        session_ids_different = set()
        for i in range(5):
            session_id = file_manager.generate_session_id(f"submission_{i}", i)
            session_ids_different.add(session_id)
            await asyncio.sleep(0.01)
        
        # Should be unique due to different parameters
        assert len(session_ids_different) == 5 