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
from app.services.database_service import DatabaseService
from app.models.fluency_model import WordDetail
from app.services.fluency_service import calculate_timing_metrics

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
                original_audio_url=message_data["original_audio_url"],
                session_id=message_data.get("session_id"),
                total_questions=message_data.get("total_questions")
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
                audio_url=message_data["audio_url"],
                total_questions=message_data.get("total_questions")
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
            session_id = message_data.get("session_id")
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for analysis ready question {question_number}, submission {submission_url}")
                # For analysis ready, we don't have existing submission state yet, so we'll use None
                # The downstream handlers will need to handle this case
                logger.warning(f"⚠️ Cannot recover total_questions at analysis ready stage for question {question_number}")
            
            logger.info(f"Starting PHASE 1 analysis for question {question_number} (Grammar, Pronunciation, Lexical)")
            if session_id:
                logger.info(f"Using session {session_id} for file lifecycle management")
            
            # Initialize analysis state
            state = self._get_or_create_analysis_state(submission_url, question_number)
            state["wav_path"] = wav_path
            state["transcript"] = transcript
            state["audio_url"] = audio_url
            state["session_id"] = session_id
            state["total_questions"] = total_questions
            
            # Create tasks for parallel execution (Grammar, Pronunciation, Lexical only)
            tasks = []
            
            # 1. Pronunciation Analysis Task
            async def pronunciation_task():
                try:
                    pronunciation_result = await PronunciationService.analyze_pronunciation(
                        wav_path, 
                        transcript, 
                        session_id=session_id
                    )
                    state["pronunciation_result"] = pronunciation_result
                    state["pronunciation_done"] = True
                    
                    # Publish pronunciation done - this will trigger fluency analysis
                    self.pubsub_client.publish_message_by_name(
                        "PRONUNCIATION_DONE",
                        {
                            "question_number": question_number,
                            "submission_url": submission_url,
                            "wav_path": wav_path,
                            "transcript": transcript,
                            "audio_url": audio_url,
                            "session_id": session_id,
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
                    # lexical_result is already a dict, no need to convert
                    state["lexical_result"] = lexical_result
                    state["lexical_done"] = True
                    
                    # Publish lexical done
                    self.pubsub_client.publish_message_by_name(
                        "LEXICAL_DONE",
                        {
                            "question_number": question_number,
                            "submission_url": submission_url,
                            "total_questions": total_questions,
                            "result": lexical_result
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
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for fluency question {question_number}, submission {submission_url}")
                # Try to infer from existing submission state if available
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    total_questions = 1  # Last resort fallback
            
            logger.info(f"Starting PHASE 2 analysis for question {question_number} (Fluency with pronunciation data)")
            
            # Add debugging to understand the pronunciation_result structure
            logger.info(f"DEBUG: pronunciation_result type: {type(pronunciation_result)}")
            logger.info(f"DEBUG: pronunciation_result content (first 500 chars): {str(pronunciation_result)[:500]}")
            if isinstance(pronunciation_result, list):
                logger.info(f"DEBUG: pronunciation_result is a list with {len(pronunciation_result)} items")
                if pronunciation_result:
                    logger.info(f"DEBUG: First item type: {type(pronunciation_result[0])}")
                    logger.info(f"DEBUG: First item content: {pronunciation_result[0]}")
            elif isinstance(pronunciation_result, dict):
                logger.info(f"DEBUG: pronunciation_result is a dict with keys: {list(pronunciation_result.keys())}")
                if "word_details" in pronunciation_result:
                    logger.info(f"DEBUG: word_details type: {type(pronunciation_result['word_details'])}")
                    logger.info(f"DEBUG: word_details length: {len(pronunciation_result['word_details']) if isinstance(pronunciation_result['word_details'], list) else 'not a list'}")
            
            # Get analysis state
            state = self._get_or_create_analysis_state(submission_url, question_number)
            
            # Run Fluency Analysis with pronunciation word_details
            try:
                # Add defensive handling for both dict and list cases
                if isinstance(pronunciation_result, dict):
                    word_details = pronunciation_result.get("word_details", [])
                elif isinstance(pronunciation_result, list):
                    logger.warning(f"pronunciation_result is unexpectedly a list. Using empty word_details for fluency analysis.")
                    # If it's a list, we might need to extract word_details differently
                    # For now, use empty list to prevent crash
                    word_details = []
                else:
                    logger.warning(f"pronunciation_result has unexpected type {type(pronunciation_result)}. Using empty word_details.")
                    word_details = []
                    
                logger.info(f"DEBUG: Using word_details with {len(word_details)} items for fluency analysis")
                
                # Convert word_details to proper format and calculate timing metrics
                if word_details:
                    # Convert dict word_details to WordDetail objects
                    try:
                        word_detail_objects = []
                        for word_dict in word_details:
                            word_detail = WordDetail(
                                word=word_dict.get("word", ""),
                                offset=word_dict.get("offset", 0.0),
                                duration=word_dict.get("duration", 0.0),
                                accuracy_score=word_dict.get("accuracy_score", 0.0),
                                error_type=word_dict.get("error_type", "None")
                            )
                            word_detail_objects.append(word_detail)
                        
                        # Calculate timing metrics from word details
                        timing_metrics = calculate_timing_metrics(word_detail_objects)
                        logger.info(f"DEBUG: Calculated timing metrics: {timing_metrics}")
                        
                    except Exception as e:
                        logger.error(f"Error converting word_details to WordDetail objects: {str(e)}")
                        timing_metrics = {}
                else:
                    timing_metrics = {}
                
                # Call fluency analysis with proper timing metrics (not raw word_details)
                fluency_result = await get_fluency_coherence_analysis(transcript, timing_metrics)
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
        logger.info(f"🔍 DEBUG: Entering _check_and_publish_completion for question {question_number}, submission {submission_url}")
        
        state = self._get_or_create_analysis_state(submission_url, question_number)
        
        logger.info(f"🔍 DEBUG: Analysis state check - grammar_done: {state['grammar_done']}, pronunciation_done: {state['pronunciation_done']}, lexical_done: {state['lexical_done']}, fluency_done: {state['fluency_done']}")
        
        # Check if all analyses are complete
        if (state["grammar_done"] and state["pronunciation_done"] and 
            state["lexical_done"] and state["fluency_done"]):
            
            logger.info(f"🔍 DEBUG: All analyses complete! Compiling results for question {question_number}")
            
            # Compile all results including the original audio URL
            analysis_results = {
                "pronunciation": state["pronunciation_result"],
                "grammar": state["grammar_result"],
                "lexical": state["lexical_result"],
                "fluency": state["fluency_result"],
                "original_audio_url": state.get("audio_url")  # Include original audio URL
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
            
            logger.info(f"🔍 DEBUG: About to publish ANALYSIS_COMPLETE message for question {question_number}")
            
            self.pubsub_client.publish_message_by_name(
                "ANALYSIS_COMPLETE",
                message_data
            )
            
            logger.info(f"ALL analysis completed for question {question_number} - published to analysis-complete-topic")
            
            # Clean up state
            logger.info(f"🔍 DEBUG: Cleaning up analysis state for question {question_number}")
            self._cleanup_analysis_state(submission_url, question_number)
        else:
            logger.info(f"🔍 DEBUG: Not all analyses complete yet for question {question_number}. Missing: {[name for name, done in [('grammar', state['grammar_done']), ('pronunciation', state['pronunciation_done']), ('lexical', state['lexical_done']), ('fluency', state['fluency_done'])] if not done]}")

    async def handle_fluency_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle fluency analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for fluency question {question_number}, submission {submission_url}")
                # Try to infer from existing submission state if available
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    total_questions = 1  # Last resort fallback
            
            logger.info(f"Fluency analysis acknowledged for question {question_number}")
            
            # Check if all analyses are complete now that fluency is done
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
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
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for grammar question {question_number}, submission {submission_url}")
                # Try to infer from existing submission state if available
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    total_questions = 1  # Last resort fallback
            
            logger.info(f"Grammar analysis acknowledged for question {question_number}")
            
            # Check if all analyses are complete now that grammar is done
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
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
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for lexical question {question_number}, submission {submission_url}")
                # Try to infer from existing submission state if available
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    total_questions = 1  # Last resort fallback
            
            logger.info(f"Lexical analysis acknowledged for question {question_number}")
            
            # Check if all analyses are complete now that lexical is done
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
            return {"status": "success", "message": "Lexical analysis completion acknowledged"}
            
        except Exception as e:
            logger.error(f"Error handling lexical done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_analysis_complete_webhook(self, request: Request) -> Dict[str, str]:
        """Handle analysis completion and check for submission completion"""
        logger.info(f"🔍 DEBUG: Entering handle_analysis_complete_webhook")
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            logger.info(f"🔍 DEBUG: Parsed message data keys: {list(message_data.keys())}")
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            analysis_results = message_data["analysis_results"]
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for question {question_number}, submission {submission_url}")
                # Try to infer from existing submission state if available
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    logger.error(f"❌ Cannot determine total_questions for submission {submission_url}")
                    total_questions = 1  # Last resort fallback
            
            logger.info(f"🔍 DEBUG: Processing question {question_number} for submission {submission_url} with total_questions={total_questions}")
            logger.info(f"Question {question_number} analysis completed for submission {submission_url}")
            
            # Update submission-level state
            submission_state = self._get_or_create_submission_state(submission_url, total_questions)
            logger.info(f"🔍 DEBUG: Current submission state before update: completed={submission_state['completed_questions']}, total={submission_state['total_questions']}")
            
            submission_state["question_results"][question_number] = analysis_results
            submission_state["completed_questions"] += 1
            
            logger.info(f"🔍 DEBUG: Updated submission state: completed={submission_state['completed_questions']}, total={submission_state['total_questions']}")
            logger.info(f"Submission {submission_url}: {submission_state['completed_questions']}/{submission_state['total_questions']} questions complete")
            
            # Check if submission is complete
            if submission_state["completed_questions"] >= submission_state["total_questions"]:
                logger.info(f"🔍 DEBUG: Submission complete! Calling _publish_submission_complete for {submission_url}")
                await self._publish_submission_complete(submission_state)
            else:
                logger.info(f"🔍 DEBUG: Submission not yet complete. Need {submission_state['total_questions'] - submission_state['completed_questions']} more questions for {submission_url}")
                
            return {"status": "success", "message": "Question analysis processed"}
            
        except Exception as e:
            logger.error(f"💥 ERROR in handle_analysis_complete_webhook: {str(e)}")
            logger.error(f"Error handling analysis complete webhook: {str(e)}")
            import traceback
            logger.error(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
            
    async def _publish_submission_complete(self, submission_state: Dict):
        """Publish submission completion with all aggregated results"""
        logger.info(f"🔍 DEBUG: Entering _publish_submission_complete for submission: {submission_state.get('submission_url', 'unknown')}")
        try:
            submission_url = submission_state["submission_url"]
            logger.info(f"🔍 DEBUG: About to compile final results for {submission_url}")
            
            # Compile final submission results
            final_results = {
                "submission_url": submission_url,
                "total_questions": submission_state["total_questions"],
                "completed_questions": submission_state["completed_questions"],
                "question_results": submission_state["question_results"],
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🔍 DEBUG: About to publish SUBMISSION_ANALYSIS_COMPLETE message for {submission_url}")
            # Publish to submission complete topic
            message_id = self.pubsub_client.publish_message_by_name(
                "SUBMISSION_ANALYSIS_COMPLETE",
                final_results
            )
            
            logger.info(f"🎉 Published submission completion for {submission_url} with {submission_state['completed_questions']} questions - Message ID: {message_id}")
            
            # Clean up submission state
            logger.info(f"🔍 DEBUG: Cleaning up submission state for {submission_url}")
            self._cleanup_submission_state(submission_url)
                
        except Exception as e:
            logger.error(f"💥 ERROR in _publish_submission_complete: {str(e)}")
            logger.error(f"Error publishing submission completion: {str(e)}")
            import traceback
            logger.error(f"🔍 DEBUG: Full traceback in _publish_submission_complete: {traceback.format_exc()}")
            raise
            
    async def handle_submission_analysis_complete_webhook(self, request: Request) -> Dict[str, str]:
        """Handle submission analysis completion - all questions done"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            submission_url = message_data["submission_url"]
            completed_questions = message_data["completed_questions"]
            question_results = message_data["question_results"]
            
            logger.info(f"🎉 SUBMISSION COMPLETE: {submission_url} - {completed_questions} questions analyzed")
            logger.info(f"📊 Question results summary for {submission_url}: {list(question_results.keys()) if question_results else 'No results'}")
            
            # Store results for testing/retrieval
            results_store.store_result(submission_url, message_data)
            logger.info(f"💾 Stored results in memory cache for submission: {submission_url}")
            
            # Store final results to database
            logger.info(f"🔄 Beginning Supabase database operations for submission: {submission_url}")
            try:
                db_service = DatabaseService()
                logger.info(f"🏗️ DatabaseService initialized for submission: {submission_url}")
                
                # OPTION 1: Extract original audio URLs from question results instead of searching storage
                logger.info(f"🎵 Extracting original audio URLs from question results for submission: {submission_url}")
                recording_urls = []
                
                for question_num, analysis_results in question_results.items():
                    if isinstance(analysis_results, dict) and "original_audio_url" in analysis_results:
                        original_url = analysis_results["original_audio_url"]
                        if original_url:
                            recording_urls.append(original_url)
                            logger.info(f"🎵 Found original URL for question {question_num}: {original_url}")
                        else:
                            logger.warning(f"⚠️ Question {question_num} has empty original_audio_url")
                    else:
                        logger.warning(f"⚠️ Question {question_num} missing original_audio_url in analysis results")
                
                if recording_urls:
                    logger.info(f"🎵 Successfully extracted {len(recording_urls)} original audio URLs for submission: {submission_url}")
                    # Log first few URLs for verification
                    for i, url in enumerate(recording_urls[:3]):
                        logger.info(f"🎵 Recording {i+1}: {url}")
                else:
                    logger.warning(f"⚠️ No original audio URLs found in question results for submission: {submission_url}")

                # 2. Update the existing submission with analysis results
                logger.info(f"💽 Updating existing submission in Supabase 'submissions' table: {submission_url}")
                submission_db_id = db_service.update_submission_results(
                    submission_url=submission_url,
                    question_results=question_results,
                    recordings=recording_urls
                )
                
                if submission_db_id:
                    logger.info(f"✅ SUCCESS: Updated submission {submission_url} in Supabase database with ID: {submission_db_id}")
                    logger.info(f"📋 Database record updated: table=submissions, id={submission_db_id}, status=graded, recordings_count={len(recording_urls or [])}")
                else:
                    logger.error(f"❌ FAILED: Could not update submission {submission_url} in Supabase database - update_submission_results returned None")
                    logger.error(f"🔍 Check if submission {submission_url} exists in database and has correct permissions")
                    
            except Exception as e:
                logger.error(f"💥 EXCEPTION during Supabase database operation for submission {submission_url}: {str(e)}")
                logger.error(f"🔍 Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"📋 Full traceback for submission {submission_url}: {traceback.format_exc()}")

            logger.info(f"🏁 Completed all operations for submission: {submission_url}")
            
            # TODO: Implement further final submission processing here:
            # - Calculate overall scores/grades
            # - Send notifications to students/teachers
            # - Update student progress tracking
            # - Generate reports/analytics
            
            return {"status": "success", "message": f"Submission analysis complete: {completed_questions} questions processed"}
            
        except Exception as e:
            logger.error(f"💥 CRITICAL ERROR handling submission analysis complete webhook: {str(e)}")
            if 'submission_url' in locals():
                logger.error(f"🆔 Failed submission URL: {submission_url}")
            import traceback
            logger.error(f"📋 Full webhook error traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 