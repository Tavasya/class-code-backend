import pytest
import asyncio
from unittest.mock import patch, Mock
from app.services.pronunciation_service import PronunciationService
from app.services.grammar_service import analyze_grammar
from app.services.lexical_service import analyze_lexical_resources
from app.services.database_service import DatabaseService
from app.core.results_store import results_store


class TestResultsAggregationChain:
    """Test the critical results aggregation chain: All Analysis Services → Final Results Storage"""

    @pytest.mark.asyncio
    async def test_complete_analysis_to_storage_chain(self, test_audio_url, submission_url, test_transcript):
        """Test complete chain from analysis services to final storage"""
        
        # Step 1: Create a test WAV file for pronunciation analysis
        import tempfile
        import os
        from app.services.audio_service import AudioService
        
        audio_service = AudioService()
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        # Step 2: Run all analysis services with the same test data
        pronunciation_task = PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text=test_transcript,
            session_id=session_id
        )
        
        grammar_task = analyze_grammar(test_transcript)
        
        # Convert transcript to sentences for lexical analysis
        sentences = [s.strip() for s in test_transcript.split('.') if s.strip()]
        lexical_task = analyze_lexical_resources(sentences)
        
        # Execute all analysis services concurrently
        pronunciation_result, grammar_result, lexical_result = await asyncio.gather(
            pronunciation_task, grammar_task, lexical_task
        )
        
        # Step 3: Verify all analysis services produced valid results
        assert pronunciation_result is not None
        assert "grade" in pronunciation_result
        assert "issues" in pronunciation_result
        
        assert grammar_result is not None
        assert "grade" in grammar_result
        assert "issues" in grammar_result
        
        assert lexical_result is not None
        assert "grade" in lexical_result
        assert "issues" in lexical_result
        
        # Step 4: Aggregate results (simulating AnalysisWebhook aggregation logic)
        aggregated_results = {
            "submission_url": submission_url,
            "question_number": 1,
            "analysis_results": {
                "pronunciation": pronunciation_result,
                "grammar": grammar_result,
                "lexical": lexical_result,
                "transcript": test_transcript,
                "original_audio_url": test_audio_url
            }
        }
        
        # Step 5: Test storage in ResultsStore (memory cache)
        results_store.store_result(submission_url, aggregated_results)
        
        # Verify memory storage
        stored_results = results_store.get_result(submission_url)
        assert stored_results is not None
        assert stored_results["submission_url"] == submission_url
        assert stored_results["question_number"] == 1
        assert "analysis_results" in stored_results
        
        # Verify all analysis results are preserved
        analysis_data = stored_results["analysis_results"]
        assert "pronunciation" in analysis_data
        assert "grammar" in analysis_data
        assert "lexical" in analysis_data
        assert analysis_data["transcript"] == test_transcript
        
        # Step 6: Test database storage (with mocking)
        with patch('app.services.database_service.DatabaseService.update_submission_results') as mock_db_update:
            mock_db_update.return_value = {"success": True}
            
            database_service = DatabaseService()
            
            # Transform results to database format
            question_results = {
                "1": {
                    "pronunciation": pronunciation_result,
                    "grammar": grammar_result,
                    "lexical": lexical_result,
                    "transcript": test_transcript,
                    "original_audio_url": test_audio_url
                }
            }
            
            recordings = [test_audio_url]
            
            # Store to database
            db_result = await database_service.update_submission_results(
                submission_url=submission_url,
                question_results=question_results,
                recordings=recordings
            )
            
            # Verify database call was made
            mock_db_update.assert_called_once()
            assert db_result["success"] is True
        
        # Cleanup
        results_store.clear_result(submission_url)

    @pytest.mark.asyncio
    async def test_results_format_consistency(self, test_audio_url, submission_url, test_transcript):
        """Test that results format is consistent across all analysis services"""
        
        # Step 1: Setup audio file
        from app.services.audio_service import AudioService
        audio_service = AudioService()
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        # Step 2: Run all analysis services
        pronunciation_result = await PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text=test_transcript,
            session_id=session_id
        )
        
        grammar_result = await analyze_grammar(test_transcript)
        
        sentences = [s.strip() for s in test_transcript.split('.') if s.strip()]
        lexical_result = await analyze_lexical_resources(sentences)
        
        # Step 3: Verify all results follow the standardized format
        analysis_results = [
            ("pronunciation", pronunciation_result),
            ("grammar", grammar_result),
            ("lexical", lexical_result)
        ]
        
        for service_name, result in analysis_results:
            # All results should have grade and issues fields
            assert "grade" in result, f"{service_name} result missing 'grade' field"
            assert "issues" in result, f"{service_name} result missing 'issues' field"
            
            # Grade should be numeric
            assert isinstance(result["grade"], (int, float)), f"{service_name} grade should be numeric"
            assert 0 <= result["grade"] <= 100, f"{service_name} grade should be 0-100"
            
            # Issues should be a list
            assert isinstance(result["issues"], list), f"{service_name} issues should be a list"
            
            # Each issue should have required fields
            for issue in result["issues"]:
                if isinstance(issue, dict):
                    assert "type" in issue, f"{service_name} issue missing 'type' field"
                    assert "message" in issue, f"{service_name} issue missing 'message' field"

    @pytest.mark.asyncio
    async def test_aggregation_with_partial_failures(self, test_audio_url, submission_url, test_transcript):
        """Test results aggregation handles partial service failures gracefully"""
        
        # Step 1: Setup audio file
        from app.services.audio_service import AudioService
        audio_service = AudioService()
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        # Step 2: Run services with some expected to succeed and some to fail
        try:
            pronunciation_result = await PronunciationService.analyze_pronunciation(
                audio_file=wav_path,
                reference_text=test_transcript,
                session_id=session_id
            )
        except Exception as e:
            pronunciation_result = {"grade": 0, "issues": [{"type": "error", "message": str(e)}]}
        
        try:
            grammar_result = await analyze_grammar(test_transcript)
        except Exception as e:
            grammar_result = {"grade": 0, "issues": [{"type": "error", "message": str(e)}]}
        
        try:
            # Intentionally cause lexical analysis to fail with empty input
            lexical_result = await analyze_lexical_resources([])  # Empty sentences
        except Exception as e:
            lexical_result = {"grade": 0, "issues": [{"type": "error", "message": str(e)}]}
        
        # Step 3: Aggregate results even with some failures
        aggregated_results = {
            "submission_url": submission_url,
            "question_number": 1,
            "analysis_results": {
                "pronunciation": pronunciation_result,
                "grammar": grammar_result,
                "lexical": lexical_result,
                "transcript": test_transcript
            }
        }
        
        # Step 4: Verify aggregation works even with partial failures
        results_store.store_result(submission_url, aggregated_results)
        
        stored_results = results_store.get_result(submission_url)
        assert stored_results is not None
        
        # All services should have results (even if they're error results)
        analysis_data = stored_results["analysis_results"]
        assert "pronunciation" in analysis_data
        assert "grammar" in analysis_data
        assert "lexical" in analysis_data
        
        # Each result should have the standardized format
        for service_name in ["pronunciation", "grammar", "lexical"]:
            result = analysis_data[service_name]
            assert "grade" in result
            assert "issues" in result
        
        # Cleanup
        results_store.clear_result(submission_url)

    @pytest.mark.asyncio 
    async def test_multi_question_aggregation(self, test_audio_url, test_transcript):
        """Test aggregation of results across multiple questions"""
        
        submission_url = "multi-question-test-submission"
        
        # Step 1: Process multiple questions
        all_results = {}
        
        for question_num in [1, 2, 3]:
            # Setup audio for each question
            from app.services.audio_service import AudioService
            audio_service = AudioService()
            audio_result = await audio_service.process_single_audio(
                audio_url=test_audio_url,
                question_number=question_num,
                submission_url=f"{submission_url}-q{question_num}"
            )
            
            wav_path = audio_result["wav_path"]
            session_id = audio_result["session_id"]
            
            # Run analysis for each question
            pronunciation_result = await PronunciationService.analyze_pronunciation(
                audio_file=wav_path,
                reference_text=f"{test_transcript} Question {question_num}",
                session_id=session_id
            )
            
            grammar_result = await analyze_grammar(f"{test_transcript} Question {question_num}")
            
            sentences = [f"{test_transcript} Question {question_num}"]
            lexical_result = await analyze_lexical_resources(sentences)
            
            # Store results for this question
            all_results[str(question_num)] = {
                "pronunciation": pronunciation_result,
                "grammar": grammar_result,
                "lexical": lexical_result,
                "transcript": f"{test_transcript} Question {question_num}",
                "original_audio_url": test_audio_url
            }
        
        # Step 2: Aggregate all questions into final submission
        final_results = {
            "submission_url": submission_url,
            "total_questions": 3,
            "completed_questions": list(range(1, 4)),
            "question_results": all_results
        }
        
        # Step 3: Store final aggregated results
        results_store.store_result(submission_url, final_results)
        
        # Step 4: Verify multi-question aggregation
        stored_results = results_store.get_result(submission_url)
        assert stored_results is not None
        assert stored_results["total_questions"] == 3
        assert len(stored_results["question_results"]) == 3
        
        # Verify each question has complete analysis results
        for question_num in ["1", "2", "3"]:
            question_data = stored_results["question_results"][question_num]
            assert "pronunciation" in question_data
            assert "grammar" in question_data
            assert "lexical" in question_data
            assert "transcript" in question_data
            
            # Verify each analysis result has the correct format
            for analysis_type in ["pronunciation", "grammar", "lexical"]:
                result = question_data[analysis_type]
                assert "grade" in result
                assert "issues" in result
        
        # Cleanup
        results_store.clear_result(submission_url)

    @pytest.mark.asyncio
    async def test_storage_consistency_between_cache_and_database(self, test_audio_url, submission_url, test_transcript):
        """Test that memory cache and database storage maintain consistent data"""
        
        # Step 1: Run analysis services
        from app.services.audio_service import AudioService
        audio_service = AudioService()
        audio_result = await audio_service.process_single_audio(
            audio_url=test_audio_url,
            question_number=1,
            submission_url=submission_url
        )
        
        wav_path = audio_result["wav_path"]
        session_id = audio_result["session_id"]
        
        pronunciation_result = await PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text=test_transcript,
            session_id=session_id
        )
        
        grammar_result = await analyze_grammar(test_transcript)
        
        sentences = [s.strip() for s in test_transcript.split('.') if s.strip()]
        lexical_result = await analyze_lexical_resources(sentences)
        
        # Step 2: Store in memory cache
        cache_data = {
            "submission_url": submission_url,
            "question_number": 1,
            "analysis_results": {
                "pronunciation": pronunciation_result,
                "grammar": grammar_result,
                "lexical": lexical_result,
                "transcript": test_transcript
            }
        }
        
        results_store.store_result(submission_url, cache_data)
        
        # Step 3: Prepare database format (simulating the transformation)
        question_results = {
            "1": {
                "pronunciation": pronunciation_result,
                "grammar": grammar_result,
                "lexical": lexical_result,
                "transcript": test_transcript,
                "original_audio_url": test_audio_url
            }
        }
        
        # Step 4: Mock database storage and verify data consistency
        with patch('app.services.database_service.DatabaseService.update_submission_results') as mock_db_update:
            mock_db_update.return_value = {"success": True}
            
            database_service = DatabaseService()
            
            # Store to database
            await database_service.update_submission_results(
                submission_url=submission_url,
                question_results=question_results,
                recordings=[test_audio_url]
            )
            
            # Verify database was called with consistent data
            mock_db_update.assert_called_once()
            call_args = mock_db_update.call_args[1]  # keyword arguments
            
            assert call_args["submission_url"] == submission_url
            assert "1" in call_args["question_results"]
            
            db_question_data = call_args["question_results"]["1"]
            cache_analysis_data = cache_data["analysis_results"]
            
            # Verify key fields are consistent between cache and database
            assert db_question_data["pronunciation"]["grade"] == cache_analysis_data["pronunciation"]["grade"]
            assert db_question_data["grammar"]["grade"] == cache_analysis_data["grammar"]["grade"]
            assert db_question_data["lexical"]["grade"] == cache_analysis_data["lexical"]["grade"]
            assert db_question_data["transcript"] == cache_analysis_data["transcript"]
        
        # Cleanup
        results_store.clear_result(submission_url) 