import pytest
import os
import asyncio
from app.services.audio_service import AudioService
from app.services.file_manager_service import file_manager
from app.services.pronunciation_service import PronunciationService


class TestCoreFileLifecycleChain:
    """Test the critical file lifecycle chain: AudioService → FileManager → PronunciationService"""

    @pytest.mark.asyncio
    async def test_audio_file_pronunciation_lifecycle_chain(self, test_audio_url, submission_url, test_transcript):
        """Test complete file lifecycle: audio processing → file registration → pronunciation analysis → cleanup"""
        
        # Step 1: Audio processing creates file and registers with FileManager
        audio_service = AudioService()
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        # Verify audio processing result
        assert "wav_path" in audio_result
        assert "session_id" in audio_result
        assert "question_number" in audio_result
        assert audio_result["question_number"] == 1
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        # Verify file was created and registered with FileManager
        assert os.path.exists(wav_path)
        assert wav_path.endswith('.wav')
        
        session_info = file_manager.get_session_info(session_id)
        assert session_info is not None
        assert session_info["file_path"] == wav_path
        assert not session_info["cleanup_completed"]
        
        # Step 2: PronunciationService uses the registered file
        pronunciation_result = await PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text=test_transcript,
            session_id=session_id
        )
        
        # Verify pronunciation analysis worked
        assert pronunciation_result is not None
        assert "grade" in pronunciation_result
        assert "issues" in pronunciation_result
        
        # Step 3: Verify file cleanup happened automatically after service completion
        # Wait a bit for async cleanup
        await asyncio.sleep(0.1)
        
        # File should be cleaned up since pronunciation service marked completion
        assert not os.path.exists(wav_path)
        
        # Session should be marked as completed
        session_info = file_manager.get_session_info(session_id)
        assert session_info["cleanup_completed"]

    @pytest.mark.asyncio
    async def test_file_chain_with_service_coordination(self, test_audio_url, submission_url, test_transcript):
        """Test file coordination with multiple services using the same file"""
        
        audio_service = AudioService()
        
        # Step 1: Process audio and register with multiple service dependencies
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        # Verify file exists and is properly registered
        assert os.path.exists(wav_path)
        session_info = file_manager.get_session_info(session_id)
        assert session_info is not None
        
        # Step 2: Manually add another service dependency to test coordination
        # Simulate what would happen if fluency service also needed this file
        await file_manager.register_file_session(
            session_id=session_id,
            file_path=wav_path,
            dependent_services={"pronunciation", "fluency"},  # Two services need the file
            cleanup_timeout_minutes=60
        )
        
        # Step 3: First service (pronunciation) completes
        pronunciation_result = await PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text=test_transcript,
            session_id=session_id
        )
        
        # File should still exist because fluency service hasn't completed
        await asyncio.sleep(0.1)
        assert os.path.exists(wav_path)
        
        # Session should not be marked as cleanup completed yet
        session_info = file_manager.get_session_info(session_id)
        assert not session_info["cleanup_completed"]
        
        # Step 4: Second service (fluency) completes
        all_complete = await file_manager.mark_service_complete(session_id, "fluency")
        assert all_complete  # Should be complete now
        
        # Now file should be cleaned up
        await asyncio.sleep(0.1)
        assert not os.path.exists(wav_path)
        
        # Session should be marked as completed
        session_info = file_manager.get_session_info(session_id)
        assert session_info["cleanup_completed"]

    @pytest.mark.asyncio
    async def test_file_chain_error_handling(self, test_audio_url, submission_url):
        """Test file chain handles errors gracefully while maintaining cleanup"""
        
        audio_service = AudioService()
        
        # Step 1: Process audio successfully
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        # Verify file exists
        assert os.path.exists(wav_path)
        
        # Step 2: Try pronunciation analysis with invalid reference text
        # This should fail but still mark service as complete for cleanup
        pronunciation_result = await PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text="",  # Empty reference text should cause issues
            session_id=session_id
        )
        
        # Even with errors, should get a result structure
        assert pronunciation_result is not None
        assert "grade" in pronunciation_result
        assert "issues" in pronunciation_result
        
        # Step 3: Verify cleanup still happens even when service encounters errors
        await asyncio.sleep(0.1)
        
        # File should be cleaned up because service marked completion even on error
        assert not os.path.exists(wav_path)
        
        # Session should be marked as completed
        session_info = file_manager.get_session_info(session_id)
        assert session_info["cleanup_completed"]

    @pytest.mark.asyncio 
    async def test_concurrent_file_chains(self, test_audio_url):
        """Test multiple file chains running concurrently without interference"""
        
        audio_service = AudioService()
        
        # Step 1: Process multiple audio files concurrently
        tasks = []
        for i in range(3):
            task = audio_service.process_single_audio(
                audio_url=test_audio_url,
                question_number=i + 1,
                submission_url=f"concurrent-chain-submission-{i}"
            )
            tasks.append(task)
        
        # Execute all audio processing concurrently
        audio_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all processing succeeded
        wav_paths = []
        session_ids = []
        
        for i, result in enumerate(audio_results):
            if isinstance(result, Exception):
                pytest.fail(f"Audio processing {i} failed: {result}")
            
            assert "wav_path" in result
            assert "session_id" in result
            
            wav_paths.append(result["wav_path"])
            session_ids.append(result["session_id"])
            
            # Verify each file exists
            assert os.path.exists(result["wav_path"])
        
        # Step 2: Run pronunciation analysis on all files concurrently
        pronunciation_tasks = []
        for i, (wav_path, session_id) in enumerate(zip(wav_paths, session_ids)):
            task = PronunciationService.analyze_pronunciation(
                audio_file=wav_path,
                reference_text=f"Test transcript for file {i}",
                session_id=session_id
            )
            pronunciation_tasks.append(task)
        
        # Execute all pronunciation analysis concurrently
        pronunciation_results = await asyncio.gather(*pronunciation_tasks, return_exceptions=True)
        
        # Verify all analysis succeeded
        for i, result in enumerate(pronunciation_results):
            if isinstance(result, Exception):
                pytest.fail(f"Pronunciation analysis {i} failed: {result}")
            
            assert "grade" in result
            assert "issues" in result
        
        # Step 3: Verify all files were cleaned up properly
        await asyncio.sleep(0.2)  # Wait a bit longer for concurrent cleanup
        
        for wav_path in wav_paths:
            assert not os.path.exists(wav_path)
        
        # Verify all sessions are marked as completed
        for session_id in session_ids:
            session_info = file_manager.get_session_info(session_id)
            assert session_info["cleanup_completed"] 