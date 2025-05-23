import logging
import asyncio
from typing import Dict, Any
from datetime import datetime
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.analysis_coordinator_service import AnalysisCoordinatorService
from app.services.fluency_service import get_fluency_coherence_analysis
from app.services.grammar_service import analyze_grammar
from app.services.lexical_service import analyze_lexical_resources
from app.services.pronunciation_service import PronunciationService
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage, QuestionAnalysisReadyMessage
from app.core.results_store import results_store

logger = logging.getLogger(__name__)

class AnalysisWebhook:
    """Webhook handler for analysis-related messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.analysis_coordinator = AnalysisCoordinatorService()
        # State tracking for analysis coordination
        self._analysis_state: Dict[str, Dict] = {}
        # NEW: Submission-level aggregation state
        self._submission_state: Dict[str, Dict] = {}
        
    def _get_analysis_state_key(self, submission_url: str, question_number: int) -> str:
        """Generate a unique key for analysis state tracking"""
        return f"analysis:{submission_url}:{question_number}"
        
    def _get_or_create_analysis_state(self, submission_url: str, question_number: int) -> Dict:
        """Get or create analysis state for a question"""
        key = self._get_analysis_state_key(submission_url, question_number)
        if key not in self._analysis_state:
            self._analysis_state[key] = {
                "grammar_done": False,
                "pronunciation_done": False,
                "lexical_done": False,
                "fluency_done": False,
                "wav_path": None,
                "transcript": None,
                "audio_url": None,
                "pronunciation_result": None,
                "grammar_result": None,
                "lexical_result": None,
                "fluency_result": None
            }
        return self._analysis_state[key]
        
    def _cleanup_analysis_state(self, submission_url: str, question_number: int):
        """Clean up analysis state after completion"""
        key = self._get_analysis_state_key(submission_url, question_number)
        if key in self._analysis_state:
            del self._analysis_state[key]
            
    def _get_submission_state_key(self, submission_url: str) -> str:
        """Generate key for submission-level tracking"""
        return f"submission:{submission_url}"
        
    def _get_or_create_submission_state(self, submission_url: str, total_questions: int) -> Dict:
        """Get or create submission state"""
        key = self._get_submission_state_key(submission_url)
        if key not in self._submission_state:
            self._submission_state[key] = {
                "total_questions": total_questions,
                "completed_questions": 0,
                "question_results": {},
                "submission_url": submission_url
            }
        return self._submission_state[key]
        
    def _cleanup_submission_state(self, submission_url: str):
        """Clean up submission state after completion"""
        key = self._get_submission_state_key(submission_url)
        if key in self._submission_state:
            del self._submission_state[key]

    async def handle_audio_conversion_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle audio conversion completed webhook from Pub/Sub push"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            # Create AudioDoneMessage
            audio_message = AudioDoneMessage(
                wav_path=message_data["wav_path"],
                question_number=message_data["question_number"],
                submission_url=message_data["submission_url"],
                original_audio_url=message_data["original_audio_url"]
            )
            
            # Handle in coordinator
            await self.analysis_coordinator.handle_audio_done(audio_message)
            
            logger.info(f"Successfully handled audio conversion done for question {audio_message.question_number}")
            return {"status": "success", "message": "Audio conversion done processed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling audio conversion done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def handle_transcription_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle transcription completed webhook from Pub/Sub push"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            # Create TranscriptionDoneMessage
            transcription_message = TranscriptionDoneMessage(
                text=message_data["text"],
                error=message_data.get("error"),
                question_number=message_data["question_number"],
                submission_url=message_data["submission_url"],
                audio_url=message_data["audio_url"]
            )
            
            # Handle in coordinator
            await self.analysis_coordinator.handle_transcription_done(transcription_message)
            
            logger.info(f"Successfully handled transcription done for question {transcription_message.question_number}")
            return {"status": "success", "message": "Transcription done processed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling transcription done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def handle_question_analysis_ready_webhook(self, request: Request) -> Dict[str, str]:
        """Handle question ready for analysis webhook from Pub/Sub push
        
        PHASE 1: Run Grammar, Pronunciation, and Lexical in PARALLEL
        (Fluency will be triggered separately when pronunciation completes)
        """
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            wav_path = message_data["wav_path"]
            transcript = message_data["transcript"]
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            audio_url = message_data["audio_url"]
            total_questions = message_data.get("total_questions", 1)
            
            logger.info(f"Starting PHASE 1 analysis for question {question_number} (Grammar, Pronunciation, Lexical)")
            
            # Initialize analysis state
            state = self._get_or_create_analysis_state(submission_url, question_number)
            state["wav_path"] = wav_path
            state["transcript"] = transcript
            state["audio_url"] = audio_url
            state["total_questions"] = total_questions
            
            # Create tasks for parallel execution (Grammar, Pronunciation, Lexical only)
            tasks = []
            
            # 1. Pronunciation Analysis Task
            async def pronunciation_task():
                try:
                    pronunciation_result = await PronunciationService.analyze_pronunciation(wav_path, transcript)
                    state["pronunciation_result"] = pronunciation_result
                    state["pronunciation_done"] = True
                    
                    # Publish pronunciation done - this will trigger fluency analysis
                    self.pubsub_client.publish_message_by_name(
                        "PRONOUN_DONE",
                        {
                            "question_number": question_number,
                            "submission_url": submission_url,
                            "wav_path": wav_path,
                            "transcript": transcript,
                            "audio_url": audio_url,
                            "total_questions": total_questions,
                            "result": pronunciation_result
                        }
                    )
                    logger.info(f"Pronunciation analysis completed for question {question_number}")
                except Exception as e:
                    logger.error(f"Pronunciation analysis failed for question {question_number}: {str(e)}")
                    state["pronunciation_result"] = {"error": str(e)}
                    state["pronunciation_done"] = True
            
            # 2. Grammar Analysis Task
            async def grammar_task():
                try:
                    grammar_result = await analyze_grammar(transcript)
                    state["grammar_result"] = grammar_result
                    state["grammar_done"] = True
                    
                    # Publish grammar done
                    self.pubsub_client.publish_message_by_name(
                        "GRAMMER_DONE",
                        {
                            "question_number": question_number,
                            "submission_url": submission_url,
                            "total_questions": total_questions,
                            "result": grammar_result
                        }
                    )
                    logger.info(f"Grammar analysis completed for question {question_number}")
                except Exception as e:
                    logger.error(f"Grammar analysis failed for question {question_number}: {str(e)}")
                    state["grammar_result"] = {"error": str(e)}
                    state["grammar_done"] = True
            
            # 3. Lexical Analysis Task
            async def lexical_task():
                try:
                    sentences = [s.strip() for s in transcript.split('.') if s.strip()]
                    lexical_result = await analyze_lexical_resources(sentences)
                    state["lexical_result"] = lexical_result
                    state["lexical_done"] = True
                    
                    # Publish lexical done
                    self.pubsub_client.publish_message_by_name(
                        "LEXICAL_DONE",
                        {
                            "question_number": question_number,
                            "submission_url": submission_url,
                            "total_questions": total_questions,
                            "result": [feedback.dict() for feedback in lexical_result]
                        }
                    )
                    logger.info(f"Lexical analysis completed for question {question_number}")
                except Exception as e:
                    logger.error(f"Lexical analysis failed for question {question_number}: {str(e)}")
                    state["lexical_result"] = {"error": str(e)}
                    state["lexical_done"] = True
            
            # Add tasks to list
            tasks.extend([pronunciation_task(), grammar_task(), lexical_task()])
            
            # Run all Phase 1 tasks in parallel
            await asyncio.gather(*tasks)
            
            logger.info(f"PHASE 1 analysis completed for question {question_number}")
            return {"status": "success", "message": "Phase 1 analysis completed (Grammar, Pronunciation, Lexical)"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling question analysis ready webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_pronunciation_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle pronunciation completion and trigger Fluency analysis (PHASE 2)"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            pronunciation_result = message_data["result"]
            transcript = message_data["transcript"]
            total_questions = message_data.get("total_questions", 1)
            
            logger.info(f"Starting PHASE 2 analysis for question {question_number} (Fluency with pronunciation data)")
            
            # Get analysis state
            state = self._get_or_create_analysis_state(submission_url, question_number)
            
            # Run Fluency Analysis with pronunciation word_details
            try:
                word_details = pronunciation_result.get("word_details", [])
                fluency_result = await get_fluency_coherence_analysis(transcript, word_details)
                state["fluency_result"] = fluency_result
                state["fluency_done"] = True
                
                # Publish fluency done
                self.pubsub_client.publish_message_by_name(
                    "FLUENCY_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "total_questions": total_questions,
                        "result": fluency_result
                    }
                )
                logger.info(f"Fluency analysis completed for question {question_number}")
                
            except Exception as e:
                logger.error(f"Fluency analysis failed for question {question_number}: {str(e)}")
                state["fluency_result"] = {"error": str(e)}
                state["fluency_done"] = True
            
            # Check if all analyses are complete
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
            return {"status": "success", "message": "Phase 2 analysis completed (Fluency)"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling pronunciation done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def _check_and_publish_completion(self, submission_url: str, question_number: int, total_questions: int = None):
        """Check if all analyses are complete and publish final results"""
        state = self._get_or_create_analysis_state(submission_url, question_number)
        
        # Check if all analyses are complete
        if (state["grammar_done"] and state["pronunciation_done"] and 
            state["lexical_done"] and state["fluency_done"]):
            
            # Compile all results
            analysis_results = {
                "pronunciation": state["pronunciation_result"],
                "grammar": state["grammar_result"],
                "lexical": state["lexical_result"],
                "fluency": state["fluency_result"]
            }
            
            # Publish analysis complete with total_questions
            message_data = {
                "question_number": question_number,
                "submission_url": submission_url,
                "analysis_results": analysis_results
            }
            
            # Add total_questions if available
            if total_questions is not None:
                message_data["total_questions"] = total_questions
            
            self.pubsub_client.publish_message_by_name(
                "ANALYSIS_COMPLETE",
                message_data
            )
            
            logger.info(f"ALL analysis completed for question {question_number} - published to analysis-complete-topic")
            
            # Clean up state
            self._cleanup_analysis_state(submission_url, question_number)

    async def handle_fluency_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle fluency analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            logger.info(f"Fluency analysis acknowledged for question {question_number}")
            return {"status": "success", "message": "Fluency analysis completion acknowledged"}
            
        except Exception as e:
            logger.error(f"Error handling fluency done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_grammar_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle grammar analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            logger.info(f"Grammar analysis acknowledged for question {question_number}")
            return {"status": "success", "message": "Grammar analysis completion acknowledged"}
            
        except Exception as e:
            logger.error(f"Error handling grammar done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_lexical_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle lexical analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            logger.info(f"Lexical analysis acknowledged for question {question_number}")
            return {"status": "success", "message": "Lexical analysis completion acknowledged"}
            
        except Exception as e:
            logger.error(f"Error handling lexical done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_analysis_complete_webhook(self, request: Request) -> Dict[str, str]:
        """Handle analysis completion and check for submission completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            analysis_results = message_data["analysis_results"]
            total_questions = message_data.get("total_questions", 1)
            
            logger.info(f"Question {question_number} analysis completed for submission {submission_url}")
            
            # Update submission-level state
            submission_state = self._get_or_create_submission_state(submission_url, total_questions)
            submission_state["question_results"][question_number] = analysis_results
            submission_state["completed_questions"] += 1
            
            logger.info(f"Submission {submission_url}: {submission_state['completed_questions']}/{submission_state['total_questions']} questions complete")
            
            # Check if submission is complete
            if submission_state["completed_questions"] >= submission_state["total_questions"]:
                await self._publish_submission_complete(submission_state)
                
            return {"status": "success", "message": "Question analysis processed"}
            
        except Exception as e:
            logger.error(f"Error handling analysis complete webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
            
    async def _publish_submission_complete(self, submission_state: Dict):
        """Publish submission completion with all aggregated results"""
        try:
            submission_url = submission_state["submission_url"]
            
            # Compile final submission results
            final_results = {
                "submission_url": submission_url,
                "total_questions": submission_state["total_questions"],
                "completed_questions": submission_state["completed_questions"],
                "question_results": submission_state["question_results"],
                "timestamp": datetime.now().isoformat()
            }
            
            # Publish to submission complete topic
            message_id = self.pubsub_client.publish_message_by_name(
                "SUBMISSION_ANALYSIS_COMPLETE",
                final_results
            )
            
            logger.info(f"🎉 Published submission completion for {submission_url} with {submission_state['completed_questions']} questions - Message ID: {message_id}")
            
            # Clean up submission state
            self._cleanup_submission_state(submission_url)
                
        except Exception as e:
            logger.error(f"Error publishing submission completion: {str(e)}")
            raise
            
    async def handle_submission_analysis_complete_webhook(self, request: Request) -> Dict[str, str]:
        """Handle submission analysis completion - all questions done"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            submission_url = message_data["submission_url"]
            total_questions = message_data["total_questions"]
            completed_questions = message_data["completed_questions"]
            question_results = message_data["question_results"]
            
            logger.info(f"🎉 SUBMISSION COMPLETE: {submission_url} - {completed_questions} questions analyzed")
            
            # Store results for testing/retrieval
            results_store.store_result(submission_url, message_data)
            
            # TODO: Implement final submission processing here:
            # - Calculate overall scores/grades
            # - Store final results to database  
            # - Send notifications to students/teachers
            # - Update student progress tracking
            # - Generate reports/analytics
            
            return {"status": "success", "message": f"Submission analysis complete: {completed_questions} questions processed"}
            
        except Exception as e:
            logger.error(f"Error handling submission analysis complete webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 