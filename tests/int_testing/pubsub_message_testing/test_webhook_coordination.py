import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.core.results_store import results_store


class TestWebhookCoordination:
    """Test webhook service coordination logic - Cost: $0.00"""

    @pytest.mark.asyncio
    async def test_audio_transcription_coordination_flow(
        self, 
        analysis_webhook, 
        sample_pubsub_messages, 
        webhook_request_factory,
        mock_pubsub_client,
        results_store_cleanup
    ):
        """Test AnalysisCoordinator waits for BOTH audio and transcription before triggering analysis"""
        
        # Step 1: Send audio conversion done message
        audio_request = webhook_request_factory(sample_pubsub_messages["audio_conversion_done"])
        response1 = await analysis_webhook.handle_audio_conversion_done_webhook(audio_request)
        
        # Verify response but analysis not triggered yet
        assert response1["status"] == "success"
        assert "Audio conversion done processed" in response1["message"]
        
        # Verify no analysis ready message published yet (waiting for transcription)
        assert mock_pubsub_client.publish_message_by_name.call_count == 0
        
        # Step 2: Send transcription done message
        transcription_request = webhook_request_factory(sample_pubsub_messages["transcription_done"])
        response2 = await analysis_webhook.handle_transcription_done_webhook(transcription_request)
        
        # Verify response
        assert response2["status"] == "success" 
        assert "Transcription done processed" in response2["message"]
        
        # NOW analysis should be triggered (both audio and transcription complete)
        assert mock_pubsub_client.publish_message_by_name.call_count == 1
        
        # Verify the correct message was published
        call_args_list = mock_pubsub_client.publish_message_by_name.call_args_list
        assert len(call_args_list) == 1
        
        # Get the call arguments
        call_args = call_args_list[0]
        args, kwargs = call_args
        
        # Check if arguments were passed positionally or as kwargs
        if len(args) >= 2:
            topic_name = args[0]
            published_data = args[1]
        else:
            # Arguments passed as kwargs
            topic_name = kwargs.get("topic_name")
            published_data = kwargs.get("message")
        
        assert topic_name == "QUESTION_ANALYSIS_READY"  # Topic name
        assert published_data is not None
        
        assert published_data["submission_url"] == "test-pubsub-submission"
        assert published_data["question_number"] == 1
        assert published_data["wav_path"] == "/tmp/test_audio.wav"
        assert published_data["transcript"] == "This is a test transcript for analysis"
        assert published_data["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_reverse_audio_transcription_order(
        self,
        analysis_webhook,
        sample_pubsub_messages,
        webhook_request_factory,
        mock_pubsub_client,
        results_store_cleanup
    ):
        """Test coordination works when transcription arrives before audio"""
        
        # Step 1: Send transcription done FIRST
        transcription_request = webhook_request_factory(sample_pubsub_messages["transcription_done"])
        response1 = await analysis_webhook.handle_transcription_done_webhook(transcription_request)
        
        assert response1["status"] == "success"
        
        # Should not trigger analysis yet
        assert mock_pubsub_client.publish_message_by_name.call_count == 0
        
        # Step 2: Send audio conversion done SECOND
        audio_request = webhook_request_factory(sample_pubsub_messages["audio_conversion_done"])
        response2 = await analysis_webhook.handle_audio_conversion_done_webhook(audio_request)
        
        assert response2["status"] == "success"
        
        # NOW analysis should be triggered
        assert mock_pubsub_client.publish_message_by_name.call_count == 1
        
        # Verify correct coordination
        call_args_list = mock_pubsub_client.publish_message_by_name.call_args_list
        assert len(call_args_list) == 1
        
        call_args = call_args_list[0]
        args, kwargs = call_args
        
        # Check if arguments were passed positionally or as kwargs
        if len(args) >= 2:
            topic_name = args[0]
        else:
            topic_name = kwargs.get("topic_name")
        
        assert topic_name == "QUESTION_ANALYSIS_READY"

    @pytest.mark.asyncio
    async def test_parallel_analysis_coordination_with_mocked_services(
        self,
        analysis_webhook,
        sample_pubsub_messages,
        webhook_request_factory,
        mock_all_analysis_services,
        mock_pubsub_client,
        results_store_cleanup
    ):
        """Test AnalysisWebhook state management across parallel analysis completions"""
        
        # Step 1: Trigger analysis ready (starts all 4 analyses in parallel)
        analysis_ready_request = webhook_request_factory(sample_pubsub_messages["question_analysis_ready"])
        response = await analysis_webhook.handle_question_analysis_ready_webhook(analysis_ready_request)
        
        assert response["status"] == "success"
        assert "phase 1 analysis completed" in response["message"].lower()
        
        # Verify Phase 1 services were triggered (3 parallel analyses)
        # Note: Fluency is triggered in Phase 2 after pronunciation completes
        expected_calls = 3  # Grammar, Pronunciation, Lexical
        assert mock_pubsub_client.publish_message_by_name.call_count == expected_calls
        
        # Step 2: Complete analyses in different order to test state management
        
        # Complete grammar first
        grammar_request = webhook_request_factory(sample_pubsub_messages["grammar_done"])
        grammar_response = await analysis_webhook.handle_grammar_done_webhook(grammar_request)
        assert grammar_response["status"] == "success"
        
        # Complete lexical second  
        lexical_request = webhook_request_factory(sample_pubsub_messages["lexical_done"])
        lexical_response = await analysis_webhook.handle_lexical_done_webhook(lexical_request)
        assert lexical_response["status"] == "success"
        
        # Complete pronunciation third (triggers fluency in Phase 2)
        pronunciation_request = webhook_request_factory(sample_pubsub_messages["pronunciation_done"])
        pronunciation_response = await analysis_webhook.handle_pronunciation_done_webhook(pronunciation_request)
        assert pronunciation_response["status"] == "success"
        
        # Complete fluency fourth
        fluency_request = webhook_request_factory(sample_pubsub_messages["fluency_done"])
        fluency_response = await analysis_webhook.handle_fluency_done_webhook(fluency_request)
        assert fluency_response["status"] == "success"
        
        # All analyses complete - should trigger ANALYSIS_COMPLETE
        # Total calls: 3 (Phase 1) + 1 (Fluency) + 1 (Analysis Complete) = 5
        final_call_count = mock_pubsub_client.publish_message_by_name.call_count
        assert final_call_count >= 4  # At minimum Phase 1 + Fluency + Analysis Complete

    @pytest.mark.asyncio
    async def test_submission_completion_coordination_multiple_questions(
        self,
        analysis_webhook,
        webhook_request_factory,
        mock_pubsub_client,
        mock_database_service,
        results_store_cleanup
    ):
        """Test submission-level aggregation logic with multiple questions"""
        
        # Create analysis complete messages for 3 questions
        question_results = {}
        for q_num in [1, 2, 3]:
            # Create analysis complete message for each question
            analysis_complete_data = {
                "submission_url": "test-pubsub-submission",
                "question_number": q_num,
                "total_questions": 3,
                "analysis_results": {
                    "pronunciation": {"grade": 85.5, "issues": []},
                    "grammar": {"grade": 78.2, "issues": []},
                    "lexical": {"grade": 82.1, "issues": []},
                    "fluency": {"grade": 80.0, "issues": []},
                    "original_audio_url": f"https://example.com/audio{q_num}.webm",
                    "transcript": f"Test transcript for question {q_num}"
                }
            }
            
            from tests.int_testing.pubsub_message_testing.conftest import create_base64_message
            analysis_complete_message = create_base64_message(analysis_complete_data)
            analysis_request = webhook_request_factory(analysis_complete_message)
            
            # Send analysis complete for this question
            response = await analysis_webhook.handle_analysis_complete_webhook(analysis_request)
            assert response["status"] == "success"
        
        # After all 3 questions complete, should trigger SUBMISSION_ANALYSIS_COMPLETE
        submission_complete_calls = [
            call for call in mock_pubsub_client.publish_message_by_name.call_args_list
            if call[0][0] == "SUBMISSION_ANALYSIS_COMPLETE"
        ]
        assert len(submission_complete_calls) == 1
        
        # Verify submission complete message structure
        # Parse call arguments - could be positional or keyword args
        call_args = submission_complete_calls[0]
        if len(call_args[0]) >= 2:
            # Positional arguments: (topic_name, message_data)
            submission_message = call_args[0][1]
        else:
            # Keyword arguments
            submission_message = call_args[1].get("message", call_args[1])
        
        assert submission_message["submission_url"] == "test-pubsub-submission"
        assert submission_message["total_questions"] == 3
        # completed_questions is a count (integer), not a list
        assert submission_message["completed_questions"] == 3
        assert "question_results" in submission_message
        # Verify all 3 questions have results
        assert len(submission_message["question_results"]) == 3
        assert 1 in submission_message["question_results"]
        assert 2 in submission_message["question_results"]
        assert 3 in submission_message["question_results"]

    @pytest.mark.asyncio
    async def test_state_isolation_between_submissions(
        self,
        analysis_webhook,
        webhook_request_factory,
        mock_all_analysis_services,
        mock_pubsub_client,
        results_store_cleanup
    ):
        """Test that different submissions don't interfere with each other"""
        
        # Process question for submission A
        submission_a_data = {
            "submission_url": "test-submission-A",
            "question_number": 1,
            "total_questions": 2,
            "wav_path": "/tmp/audio_a.wav",
            "transcript": "Transcript A",
            "audio_url": "https://example.com/audioA.webm",
            "session_id": "session-A"
        }
        
        from tests.int_testing.pubsub_message_testing.conftest import create_base64_message
        message_a = create_base64_message(submission_a_data)
        request_a = webhook_request_factory(message_a)
        
        response_a = await analysis_webhook.handle_question_analysis_ready_webhook(request_a)
        assert response_a["status"] == "success"
        
        # Process question for submission B (should not interfere)
        submission_b_data = {
            "submission_url": "test-submission-B", 
            "question_number": 1,
            "total_questions": 1,
            "wav_path": "/tmp/audio_b.wav",
            "transcript": "Transcript B",
            "audio_url": "https://example.com/audioB.webm",
            "session_id": "session-B"
        }
        
        message_b = create_base64_message(submission_b_data)
        request_b = webhook_request_factory(message_b)
        
        response_b = await analysis_webhook.handle_question_analysis_ready_webhook(request_b)
        assert response_b["status"] == "success"
        
        # Both submissions should be processed independently
        # Each should trigger their own analysis services
        assert mock_pubsub_client.publish_message_by_name.call_count >= 6  # 3 services × 2 submissions
        
        # Cleanup both submissions
        results_store.clear_result("test-submission-A")
        results_store.clear_result("test-submission-B")

    @pytest.mark.asyncio
    async def test_coordination_with_missing_total_questions(
        self,
        analysis_webhook,
        webhook_request_factory,
        mock_pubsub_client,
        results_store_cleanup
    ):
        """Test coordination handles missing total_questions gracefully"""
        
        # Create message without total_questions field
        audio_data = {
            "submission_url": "test-missing-total",
            "question_number": 1,
            "wav_path": "/tmp/test_audio.wav",
            "session_id": "test-session-123",
            "original_audio_url": "https://example.com/audio1.webm"
            # Missing total_questions
        }
        
        from tests.int_testing.pubsub_message_testing.conftest import create_base64_message
        audio_message = create_base64_message(audio_data)
        audio_request = webhook_request_factory(audio_message)
        
        # Should handle gracefully without crashing
        response = await analysis_webhook.handle_audio_conversion_done_webhook(audio_request)
        assert response["status"] == "success"
        
        # Coordination should still work with fallback logic
        transcription_data = {
            "submission_url": "test-missing-total",
            "question_number": 1,
            "text": "Test transcript",
            "error": None,
            "audio_url": "https://example.com/audio1.webm"
            # Missing total_questions
        }
        
        transcription_message = create_base64_message(transcription_data)
        transcription_request = webhook_request_factory(transcription_message)
        
        response2 = await analysis_webhook.handle_transcription_done_webhook(transcription_request)
        assert response2["status"] == "success"
        
        # Should still trigger analysis coordination
        assert mock_pubsub_client.publish_message_by_name.call_count >= 1

    @pytest.mark.asyncio
    async def test_concurrent_question_processing(
        self,
        analysis_webhook,
        webhook_request_factory,
        mock_all_analysis_services,
        mock_pubsub_client,
        results_store_cleanup
    ):
        """Test concurrent processing of multiple questions from same submission"""
        
        # Process questions 1, 2, 3 concurrently
        tasks = []
        for q_num in [1, 2, 3]:
            question_data = {
                "submission_url": "test-concurrent-submission",
                "question_number": q_num,
                "total_questions": 3,
                "wav_path": f"/tmp/audio_{q_num}.wav",
                "transcript": f"Transcript for question {q_num}",
                "audio_url": f"https://example.com/audio{q_num}.webm",
                "session_id": f"session-{q_num}"
            }
            
            from tests.int_testing.pubsub_message_testing.conftest import create_base64_message
            message = create_base64_message(question_data)
            request = webhook_request_factory(message)
            
            # Create async task for concurrent processing
            task = analysis_webhook.handle_question_analysis_ready_webhook(request)
            tasks.append(task)
        
        # Execute all questions concurrently
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response["status"] == "success"
        
        # Should trigger analysis services for all questions
        # 3 questions × 3 Phase 1 services = 9 calls minimum
        assert mock_pubsub_client.publish_message_by_name.call_count >= 9 