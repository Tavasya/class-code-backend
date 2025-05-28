import pytest
import asyncio
from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.services.analysis_coordinator_service import AnalysisCoordinatorService
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage


class TestAnalysisCoordinationChain:
    """Test the critical analysis coordination chain: AudioService + TranscriptionService → AnalysisCoordinator"""

    @pytest.mark.asyncio
    async def test_parallel_services_coordination(self, test_audio_url, submission_url, mock_pubsub_client, analysis_coordinator):
        """Test coordination when audio and transcription services complete in parallel"""
        
        audio_service = AudioService()
        transcription_service = TranscriptionService()
        
        # Step 1: Run audio and transcription services in parallel
        audio_task = audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        transcription_task = transcription_service.process_single_transcription(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        # Execute both services concurrently
        audio_result, transcription_result = await asyncio.gather(audio_task, transcription_task)
        
        # Verify both services completed successfully
        assert "wav_path" in audio_result
        assert "session_id" in audio_result
        assert "text" in transcription_result
        assert transcription_result["error"] is None
        
        # Step 2: Create coordination messages (bypassing pub/sub)
        audio_message = AudioDoneMessage(
            wav_path=audio_result["wav_path"],
            session_id=audio_result["session_id"],
            question_number=1,
            submission_url=submission_url,
            original_audio_url=test_audio_url,
            total_questions=3
        )
        
        transcription_message = TranscriptionDoneMessage(
            text=transcription_result["text"],
            error=transcription_result["error"],
            question_number=1,
            submission_url=submission_url,
            audio_url=test_audio_url,
            total_questions=3
        )
        
        # Step 3: Test coordination logic directly
        await analysis_coordinator.handle_audio_done(audio_message)
        await analysis_coordinator.handle_transcription_done(transcription_message)
        
        # Step 4: Verify coordination triggered analysis-ready message
        # Check that publish_message_by_name was called with correct topic
        mock_pubsub_client.publish_message_by_name.assert_called()
        
        # Verify the published message has correct format
        call_args = mock_pubsub_client.publish_message_by_name.call_args
        topic_name = call_args[0][0]
        message_data = call_args[0][1]
        
        assert topic_name == "QUESTION_ANALYSIS_READY"
        assert message_data["wav_path"] == audio_result["wav_path"]
        assert message_data["transcript"] == transcription_result["text"]
        assert message_data["question_number"] == 1
        assert message_data["submission_url"] == submission_url
        assert message_data["session_id"] == audio_result["session_id"]

    @pytest.mark.asyncio
    async def test_coordination_with_out_of_order_completion(self, test_audio_url, submission_url, mock_pubsub_client, analysis_coordinator):
        """Test coordination when services complete in different orders"""
        
        audio_service = AudioService()
        transcription_service = TranscriptionService()
        
        # Step 1: Process audio and transcription
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        transcription_result = await transcription_service.process_single_transcription(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        # Step 2: Test transcription completing BEFORE audio (reverse order)
        transcription_message = TranscriptionDoneMessage(
            text=transcription_result["text"],
            error=transcription_result["error"],
            question_number=1,
            submission_url=submission_url,
            audio_url=test_audio_url,
            total_questions=3
        )
        
        # Handle transcription first - should not trigger analysis yet
        await analysis_coordinator.handle_transcription_done(transcription_message)
        
        # Verify no message published yet (audio not ready)
        mock_pubsub_client.publish_message_by_name.assert_not_called()
        
        # Step 3: Now handle audio completion
        audio_message = AudioDoneMessage(
            wav_path=audio_result["wav_path"],
            session_id=audio_result["session_id"],
            question_number=1,
            submission_url=submission_url,
            original_audio_url=test_audio_url,
            total_questions=3
        )
        
        await analysis_coordinator.handle_audio_done(audio_message)
        
        # Step 4: Now analysis-ready should be triggered
        mock_pubsub_client.publish_message_by_name.assert_called_once()
        
        call_args = mock_pubsub_client.publish_message_by_name.call_args
        topic_name = call_args[0][0]
        message_data = call_args[0][1]
        
        assert topic_name == "QUESTION_ANALYSIS_READY"
        assert message_data["wav_path"] == audio_result["wav_path"]
        assert message_data["transcript"] == transcription_result["text"]

    @pytest.mark.asyncio
    async def test_coordination_state_management(self, test_audio_url, submission_url, mock_pubsub_client, analysis_coordinator):
        """Test coordination state is properly managed across multiple questions"""
        
        audio_service = AudioService()
        transcription_service = TranscriptionService()
        
        # Step 1: Process multiple questions concurrently
        question_results = {}
        for question_num in [1, 2]:
            audio_result = await audio_service.process_single_audio(
                audio_url=test_audio_url,
                question_number=question_num,
                submission_url=submission_url
            )
            
            transcription_result = await transcription_service.process_single_transcription(
                audio_url=test_audio_url,
                question_number=question_num,
                submission_url=submission_url
            )
            
            question_results[question_num] = {
                "audio": audio_result,
                "transcription": transcription_result
            }
        
        # Step 2: Handle coordination for question 1
        q1_audio_msg = AudioDoneMessage(
            wav_path=question_results[1]["audio"]["wav_path"],
            session_id=question_results[1]["audio"]["session_id"],
            question_number=1,
            submission_url=submission_url,
            original_audio_url=test_audio_url,
            total_questions=2
        )
        
        q1_transcription_msg = TranscriptionDoneMessage(
            text=question_results[1]["transcription"]["text"],
            error=question_results[1]["transcription"]["error"],
            question_number=1,
            submission_url=submission_url,
            audio_url=test_audio_url,
            total_questions=2
        )
        
        await analysis_coordinator.handle_audio_done(q1_audio_msg)
        await analysis_coordinator.handle_transcription_done(q1_transcription_msg)
        
        # Question 1 should trigger analysis-ready
        assert mock_pubsub_client.publish_message_by_name.call_count == 1
        
        # Step 3: Handle only audio for question 2 (incomplete)
        q2_audio_msg = AudioDoneMessage(
            wav_path=question_results[2]["audio"]["wav_path"],
            session_id=question_results[2]["audio"]["session_id"],
            question_number=2,
            submission_url=submission_url,
            original_audio_url=test_audio_url,
            total_questions=2
        )
        
        await analysis_coordinator.handle_audio_done(q2_audio_msg)
        
        # Still only 1 message published (question 2 transcription not complete)
        assert mock_pubsub_client.publish_message_by_name.call_count == 1
        
        # Step 4: Complete question 2 transcription
        q2_transcription_msg = TranscriptionDoneMessage(
            text=question_results[2]["transcription"]["text"],
            error=question_results[2]["transcription"]["error"],
            question_number=2,
            submission_url=submission_url,
            audio_url=test_audio_url,
            total_questions=2
        )
        
        await analysis_coordinator.handle_transcription_done(q2_transcription_msg)
        
        # Now should have 2 published messages (both questions complete)
        assert mock_pubsub_client.publish_message_by_name.call_count == 2

    @pytest.mark.asyncio
    async def test_coordination_error_handling(self, test_audio_url, submission_url, mock_pubsub_client, analysis_coordinator):
        """Test coordination handles service errors gracefully"""
        
        audio_service = AudioService()
        transcription_service = TranscriptionService()
        
        # Step 1: Process audio successfully
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        # Step 2: Simulate transcription error
        transcription_result = {
            "text": "",
            "error": "Transcription service failed",
            "question_number": 1
        }
        
        # Step 3: Create messages with error scenario
        audio_message = AudioDoneMessage(
            wav_path=audio_result["wav_path"],
            session_id=audio_result["session_id"],
            question_number=1,
            submission_url=submission_url,
            original_audio_url=test_audio_url,
            total_questions=1
        )
        
        transcription_message = TranscriptionDoneMessage(
            text=transcription_result["text"],
            error=transcription_result["error"],
            question_number=1,
            submission_url=submission_url,
            audio_url=test_audio_url,
            total_questions=1
        )
        
        # Step 4: Coordination should still work even with transcription error
        await analysis_coordinator.handle_audio_done(audio_message)
        await analysis_coordinator.handle_transcription_done(transcription_message)
        
        # Should still publish analysis-ready message (let analysis services handle errors)
        mock_pubsub_client.publish_message_by_name.assert_called_once()
        
        call_args = mock_pubsub_client.publish_message_by_name.call_args
        topic_name = call_args[0][0]
        message_data = call_args[0][1]
        
        assert topic_name == "QUESTION_ANALYSIS_READY"
        assert message_data["wav_path"] == audio_result["wav_path"]
        assert message_data["transcript"] == ""  # Empty transcript due to error
        assert message_data["session_id"] == audio_result["session_id"]

    @pytest.mark.asyncio
    async def test_coordination_data_flow_integrity(self, test_audio_url, submission_url, mock_pubsub_client, analysis_coordinator):
        """Test that data flows correctly through coordination without corruption"""
        
        audio_service = AudioService()
        transcription_service = TranscriptionService()
        
        # Step 1: Process services with specific test data
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=42,  # Specific test values
            submission_url=submission_url
        )
        
        transcription_result = await transcription_service.process_single_transcription(
            audio_url=test_audio_url,
            question_number=42,
            submission_url=submission_url
        )
        
        original_wav_path = audio_result["wav_path"]
        original_session_id = audio_result["session_id"]
        original_transcript = transcription_result["text"]
        
        # Step 2: Test coordination with specific data
        audio_message = AudioDoneMessage(
            wav_path=original_wav_path,
            session_id=original_session_id,
            question_number=42,
            submission_url=submission_url,
            original_audio_url=test_audio_url,
            total_questions=5
        )
        
        transcription_message = TranscriptionDoneMessage(
            text=original_transcript,
            error=None,
            question_number=42,
            submission_url=submission_url,
            audio_url=test_audio_url,
            total_questions=5
        )
        
        # Step 3: Handle coordination
        await analysis_coordinator.handle_audio_done(audio_message)
        await analysis_coordinator.handle_transcription_done(transcription_message)
        
        # Step 4: Verify data integrity in published message
        mock_pubsub_client.publish_message_by_name.assert_called_once()
        
        call_args = mock_pubsub_client.publish_message_by_name.call_args
        message_data = call_args[0][1]
        
        # Verify all data passed through correctly
        assert message_data["wav_path"] == original_wav_path
        assert message_data["transcript"] == original_transcript
        assert message_data["session_id"] == original_session_id
        assert message_data["question_number"] == 42
        assert message_data["submission_url"] == submission_url
        assert message_data["audio_url"] == test_audio_url
        assert message_data["total_questions"] == 5 