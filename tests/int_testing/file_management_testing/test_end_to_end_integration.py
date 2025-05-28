import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.audio_service import AudioService
from app.services.file_manager_service import file_manager
from app.services.pronunciation_service import PronunciationService


class TestEndToEndFileManagementIntegration:
    """End-to-end integration tests for complete file management workflow"""

    @pytest.mark.asyncio
    async def test_complete_audio_processing_workflow(self, test_audio_url, submission_url):
        """Test complete workflow: download -> convert -> register -> service use -> cleanup"""
        audio_service = AudioService()
        
        # Step 1: Process audio (download + convert + register)
        result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        # Verify processing result
        assert "wav_path" in result
        assert "session_id" in result
        assert "question_number" in result
        assert result["question_number"] == 1
        
        wav_path = result["wav_path"]
        session_id = result["session_id"]
        
        # Verify file was created and registered
        assert os.path.exists(wav_path)
        assert wav_path.endswith('.wav')
        
        session_info = file_manager.get_session_info(session_id)
        assert session_info is not None
        assert session_info["file_path"] == wav_path
        assert not session_info["cleanup_completed"]
        
        # Step 2: Simulate pronunciation service completing
        # Mark pronunciation service as complete for this session
        all_complete = await file_manager.mark_service_complete(session_id, "pronunciation")
        assert all_complete  # Should be complete since only pronunciation service is registered
        
        # Step 3: Verify file cleanup happened automatically
        # Wait a bit for async cleanup
        await asyncio.sleep(0.1)
        
        # File should be cleaned up
        assert not os.path.exists(wav_path)
        
        # Session should be marked as completed
        session_info = file_manager.get_session_info(session_id)
        assert session_info["cleanup_completed"]

    @pytest.mark.asyncio
    async def test_multiple_concurrent_audio_processing(self, test_audio_url):
        """Test processing multiple audio files concurrently"""
        audio_service = AudioService()
        
        # Process multiple audio files concurrently
        tasks = []
        for i in range(3):
            task = audio_service.process_single_audio(
                audio_url=test_audio_url,
                question_number=i + 1,
                submission_url=f"concurrent_submission_{i}"
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all processing succeeded
        wav_paths = []
        session_ids = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Audio processing {i} failed: {result}")
            
            assert "wav_path" in result
            assert "session_id" in result
            assert result["question_number"] == i + 1
            
            wav_paths.append(result["wav_path"])
            session_ids.append(result["session_id"])
            
            # Verify file exists
            assert os.path.exists(result["wav_path"])
        
        # Mark all services complete to trigger cleanup
        for session_id in session_ids:
            await file_manager.mark_service_complete(session_id, "pronunciation")
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Verify all files were cleaned up
        for wav_path in wav_paths:
            assert not os.path.exists(wav_path)

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, submission_url):
        """Test error handling throughout the workflow"""
        audio_service = AudioService()
        
        # Test with invalid URL
        invalid_url = "https://invalid-domain-that-does-not-exist.com/audio.webm"
        
        with pytest.raises(Exception) as exc_info:
            await audio_service.process_single_audio(
                audio_url=invalid_url,
                question_number=1,
                submission_url=submission_url
            )
        
        assert "Failed to download audio" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_failure_cleanup_behavior(self, test_audio_url, submission_url):
        """Test that files are cleaned up even when services fail"""
        audio_service = AudioService()
        
        # Process audio file
        result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = result["wav_path"]
        session_id = result["session_id"]
        
        # Verify file exists
        assert os.path.exists(wav_path)
        
        # Mark service complete (simulates service finishing, even on error)
        await file_manager.mark_service_complete(session_id, "pronunciation")
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # File should be cleaned up
        assert not os.path.exists(wav_path)

    @pytest.mark.asyncio
    async def test_session_timeout_behavior(self, test_audio_url, submission_url):
        """Test behavior when sessions timeout"""
        audio_service = AudioService()
        
        # Process audio file
        result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = result["wav_path"]
        session_id = result["session_id"]
        
        # Verify file exists
        assert os.path.exists(wav_path)
        
        # Force session to expire by manipulating the timeout
        session_info = file_manager.get_session_info(session_id)
        if session_info:
            # Set timeout to past time
            from datetime import datetime, timedelta
            session_info["cleanup_timeout"] = datetime.now() - timedelta(minutes=1)
        
        # Run periodic cleanup
        await file_manager.periodic_cleanup()
        
        # File should be cleaned up due to timeout
        assert not os.path.exists(wav_path)

    @pytest.mark.asyncio
    async def test_file_system_integration(self, test_audio_url, submission_url):
        """Test file system operations throughout the workflow"""
        audio_service = AudioService()
        
        # Count temp files before processing
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_files_before = len([f for f in os.listdir(temp_dir) if f.startswith('tmp')])
        
        # Process audio
        result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = result["wav_path"]
        session_id = result["session_id"]
        
        # Verify file properties
        assert os.path.exists(wav_path)
        assert os.path.getsize(wav_path) > 0
        assert os.access(wav_path, os.R_OK)  # File is readable
        
        # Complete the service to trigger cleanup
        await file_manager.mark_service_complete(session_id, "pronunciation")
        
        # Wait for cleanup
        await asyncio.sleep(0.1)
        
        # Check temp files after processing
        temp_files_after = len([f for f in os.listdir(temp_dir) if f.startswith('tmp')])
        
        # Should not have accumulated temp files
        assert temp_files_after <= temp_files_before + 1  # Allow for some temp file variance 