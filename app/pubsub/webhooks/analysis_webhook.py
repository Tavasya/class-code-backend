import logging
import asyncio
import json
import os
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
from app.services.vocabulary_service import analyze_vocabulary
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage, QuestionAnalysisReadyMessage
from app.core.results_store import results_store
from app.services.database_service import DatabaseService
from app.models.fluency_model import WordDetail
from app.services.fluency_service import calculate_timing_metrics
from app.utils.text_processing import count_actual_words, get_sentence_count

logger = logging.getLogger(__name__)

class AnalysisWebhook:
    """Webhook handler for analysis-related messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.analysis_coordinator = AnalysisCoordinatorService()
        self.database_service = DatabaseService()
        # State tracking for analysis coordination
        self._analysis_state: Dict[str, Dict] = {}
        # NEW: Submission-level aggregation state
        self._submission_state: Dict[str, Dict] = {}
        # NEW: Improvement tracking state
        self._improvement_state: Dict[str, Dict] = {}
        # FIX: Add locks for thread-safe submission state updates
        self._submission_locks: Dict[str, asyncio.Lock] = {}
        # Question tracking file
        self.tracking_file = "/tmp/question_tracking.json"
        self._init_tracking_file()
        # Initialize vocabulary debug log
        try:
            from app.services.vocabulary_service import init_vocab_log
            init_vocab_log()
        except Exception:
            pass
        
    def _init_tracking_file(self):
        """Initialize the tracking file"""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump({"sessions": {}, "start_time": datetime.now().isoformat()}, f, indent=2)
        except Exception as e:
            print(f"Failed to initialize tracking file: {e}")
    
    def _track_question(self, submission_url: str, question_number: int, event: str, data: Dict = None):
        """Track question events to separate file"""
        try:
            # Read current data
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'r') as f:
                    tracking_data = json.load(f)
            else:
                tracking_data = {"sessions": {}}
            
            # Initialize submission if not exists
            if submission_url not in tracking_data["sessions"]:
                tracking_data["sessions"][submission_url] = {"questions": {}}
            
            # Initialize question if not exists
            q_key = str(question_number)
            if q_key not in tracking_data["sessions"][submission_url]["questions"]:
                tracking_data["sessions"][submission_url]["questions"][q_key] = {"events": []}
            
            # Add event
            event_data = {
                "timestamp": datetime.now().isoformat(),
                "event": event,
                "data": data or {}
            }
            tracking_data["sessions"][submission_url]["questions"][q_key]["events"].append(event_data)
            
            # Write back
            with open(self.tracking_file, 'w') as f:
                json.dump(tracking_data, f, indent=2)
                
        except Exception as e:
            print(f"Failed to track question {question_number}: {e}")
    
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
                "vocabulary_done": False,
                "wav_path": None,
                "transcript": None,
                "audio_url": None,
                "pronunciation_result": None,
                "grammar_result": None,
                "lexical_result": None,
                "fluency_result": None,
                "vocabulary_result": None
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
        
    def _get_submission_lock(self, submission_url: str) -> asyncio.Lock:
        """Get or create a lock for thread-safe submission state updates"""
        if submission_url not in self._submission_locks:
            self._submission_locks[submission_url] = asyncio.Lock()
        return self._submission_locks[submission_url]
        
    def _cleanup_submission_state(self, submission_url: str):
        """Clean up submission state after completion"""
        key = self._get_submission_state_key(submission_url)
        if key in self._submission_state:
            del self._submission_state[key]
        # FIX: Also clean up the lock
        if submission_url in self._submission_locks:
            del self._submission_locks[submission_url]

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
        
        PHASE 1: Run Grammar, Pronunciation, Lexical, and Vocabulary in PARALLEL
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
            
            logger.info(f"🚀 STARTING PHASE 1 analysis for question {question_number} (Grammar, Pronunciation, Lexical, Vocabulary)")
            logger.info(f"🔍 QUESTION {question_number} ANALYSIS_READY RECEIVED - Submission: {submission_url}")
            
            # Track analysis ready
            self._track_question(submission_url, question_number, "ANALYSIS_READY", {
                "wav_path": wav_path,
                "transcript_length": len(transcript) if transcript else 0,
                "total_questions": total_questions
            })
            
            if session_id:
                logger.info(f"Using session {session_id} for file lifecycle management")
            
            # Initialize analysis state
            state = self._get_or_create_analysis_state(submission_url, question_number)
            
            # FIX: Check if question is fully completed to prevent duplicates
            all_completed = all([
                state.get("pronunciation_done", False),
                state.get("grammar_done", False),
                state.get("lexical_done", False),
                state.get("fluency_done", False),
                state.get("vocabulary_done", False)
            ])
            if all_completed:
                logger.warning(f"⚠️ Question {question_number} already fully completed, skipping duplicate processing")
                return {"status": "success", "message": "Question already completed"}
            
            # Check if this is a partial retry - log the current state
            partial_states = {
                "pronunciation": state.get("pronunciation_done", False),
                "grammar": state.get("grammar_done", False), 
                "lexical": state.get("lexical_done", False),
                "fluency": state.get("fluency_done", False),
                "vocabulary": state.get("vocabulary_done", False)
            }
            logger.info(f"🔍 Question {question_number} current analysis states: {partial_states}")
            
            # Track processing start
            self._track_question(submission_url, question_number, "PROCESSING_START", partial_states)
            
            state["wav_path"] = wav_path
            state["transcript"] = transcript
            state["audio_url"] = audio_url
            state["session_id"] = session_id
            state["total_questions"] = total_questions
            
            # Generate clean transcript for grammar and vocabulary analysis
            from app.services.transcript_cleaning_service import clean_transcript
            clean_text = clean_transcript(transcript) if transcript else ""
            state["clean_transcript"] = clean_text
            logger.info(f"🧹 Generated clean transcript for question {question_number}: {len(transcript or '')} -> {len(clean_text)} chars")
            
            # FIX: Set status to in_progress BEFORE starting analyses (not after)
            db_service = DatabaseService()
            analysis_types = ["pronunciation", "grammar", "lexical", "vocabulary"]
            for analysis_type in analysis_types:
                await db_service.update_status_logs(submission_url, question_number, analysis_type, "in_progress")
            logger.info(f"✅ Set all analysis statuses to 'in_progress' for question {question_number}")
            
            # Add detailed tracking for debugging
            logger.info(f"🔍 QUESTION {question_number} PROCESSING START - Submission: {submission_url}")
            logger.info(f"🔍 Audio URL: {audio_url}")
            logger.info(f"🔍 WAV Path: {wav_path}")
            logger.info(f"🔍 Transcript length: {len(transcript) if transcript else 0} chars")
            logger.info(f"🔍 Total questions: {total_questions}")
            logger.info(f"🔍 Session ID: {session_id}")
            
            # Create tasks for parallel execution
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
                    # Use clean transcript for more accurate grammar analysis
                    grammar_result = await analyze_grammar(clean_text, submission_url, question_number)
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
                            "result": lexical_result
                        }
                    )
                    logger.info(f"Lexical analysis completed for question {question_number}")
                except Exception as e:
                    logger.error(f"Lexical analysis failed for question {question_number}: {str(e)}")
                    state["lexical_result"] = {"error": str(e)}
                    state["lexical_done"] = True

            # 4. Vocabulary Analysis Task
            async def vocabulary_task():
                try:
                    logger.info(f"🔍 VOCAB TASK: Starting vocabulary analysis for question {question_number}")
                    # Use clean transcript for more accurate vocabulary analysis
                    vocabulary_result = await analyze_vocabulary(clean_text, question_number)
                    state["vocabulary_result"] = vocabulary_result
                    state["vocabulary_done"] = True
                    
                    # Publish vocabulary done
                    self.pubsub_client.publish_message_by_name(
                        "VOCABULARY_DONE",
                        {
                            "question_number": question_number,
                            "submission_url": submission_url,
                            "total_questions": total_questions,
                            "result": vocabulary_result
                        }
                    )
                    logger.info(f"✅ VOCAB TASK: Vocabulary analysis completed for question {question_number}")
                    # Track vocabulary task completion
                    self._track_question(submission_url, question_number, "VOCAB_TASK_COMPLETED", {
                        "grade": vocabulary_result.get("grade", "N/A")
                    })
                except Exception as e:
                    logger.error(f"💥 VOCAB TASK: Vocabulary analysis failed for question {question_number}: {str(e)}")
                    # Track vocabulary task failure
                    self._track_question(submission_url, question_number, "VOCAB_TASK_FAILED", {
                        "error": str(e)[:100]
                    })
                    # Still mark as done with error result to prevent hanging
                    state["vocabulary_result"] = {"error": str(e), "grade": 25}
                    state["vocabulary_done"] = True
                    
                    # Still publish vocabulary done with error result
                    try:
                        self.pubsub_client.publish_message_by_name(
                            "VOCABULARY_DONE",
                            {
                                "question_number": question_number,
                                "submission_url": submission_url,
                                "total_questions": total_questions,
                                "result": {"error": str(e), "grade": 25}
                            }
                        )
                    except Exception as pub_error:
                        logger.error(f"💥 VOCAB TASK: Failed to publish vocabulary done message: {str(pub_error)}")
            
            # Add all tasks to parallel execution
            tasks.extend([
                pronunciation_task(),
                grammar_task(),
                lexical_task(),
                vocabulary_task()
            ])
            
            # Run all Phase 1 tasks in parallel with proper error handling
            try:
                await asyncio.gather(*tasks)
                logger.info(f"🎉 PHASE 1 analysis completed for question {question_number}")
                logger.info(f"🔍 QUESTION {question_number} PARALLEL TASKS COMPLETED - Submission: {submission_url}")
                
                # Track parallel completion
                self._track_question(submission_url, question_number, "PARALLEL_COMPLETED")
                
                # FIX: Check completion immediately after parallel processing to prevent hanging
                # This ensures questions complete even if individual webhooks have issues
                await self._check_and_publish_completion(submission_url, question_number, total_questions)
                
                return {"status": "success", "message": "Phase 1 analysis completed (Grammar, Pronunciation, Lexical, Vocabulary)"}
            except Exception as parallel_error:
                logger.error(f"💥 Error during parallel analysis for question {question_number}: {str(parallel_error)}")
                # FIX: Mark all analyses as failed on exception to prevent hanging
                for analysis_type in analysis_types:
                    try:
                        await db_service.update_status_logs(submission_url, question_number, analysis_type, "failed")
                    except Exception as status_error:
                        logger.error(f"Failed to update status to failed for {analysis_type}: {str(status_error)}")
                raise parallel_error
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling question analysis ready webhook: {str(e)}")
            # FIX: Ensure cleanup on any exception
            try:
                db_service = DatabaseService()
                analysis_types = ["pronunciation", "grammar", "lexical", "vocabulary"]
                for analysis_type in analysis_types:
                    await db_service.update_status_logs(submission_url, question_number, analysis_type, "failed")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup statuses on exception: {str(cleanup_error)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_pronunciation_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle pronunciation completion and trigger Fluency analysis (PHASE 2)"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            # FIX: Remove redundant status update (now done in analysis_ready)
            db_service = DatabaseService()
            
            pronunciation_result = message_data["result"]
            transcript = message_data["transcript"]
            total_questions = message_data.get("total_questions")
            
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for fluency question {question_number}, submission {submission_url}")
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    total_questions = 1
            
            logger.info(f"Starting PHASE 2 analysis for question {question_number} (Fluency - WPM calculation)")
            
            state = self._get_or_create_analysis_state(submission_url, question_number)
            
            try:
                wpm_calculated = 0.0
                timing_metrics_for_ai = {}
                audio_duration_from_pron_result = None

                if isinstance(pronunciation_result, dict):
                    audio_duration_from_pron_result = pronunciation_result.get("audio_duration")
                    logger.info(f"DEBUG: Extracted audio_duration from pronunciation_result: {audio_duration_from_pron_result}")
                else:
                    logger.warning(f"DEBUG: pronunciation_result is not a dict (type: {type(pronunciation_result)}), cannot get audio_duration.")

                if transcript and audio_duration_from_pron_result and isinstance(audio_duration_from_pron_result, (int, float)) and audio_duration_from_pron_result > 0:
                    logger.info("🎯 Starting WPM calculation process...")
                    
                    # Count actual words using the utility function
                    word_count = count_actual_words(transcript)
                    logger.info(f"📝 Found {word_count} actual words in transcript")
                    
                    # Get sentence count for natural pause adjustment
                    sentence_count = get_sentence_count(transcript)
                    logger.info(f"📋 Detected {sentence_count} sentences")
                    
                    # Natural speech timing adjustments (in seconds)
                    PAUSE_BETWEEN_SENTENCES = 1.5  # Increased for more natural speech rhythm
                    PAUSE_FOR_COMMA = 0.7  # Increased for clearer pauses
                    PAUSE_FOR_THOUGHT = 1.0  # Increased for natural thought process
                    BASE_WORD_DURATION = 0.35  # Average duration per word for clear speech (slowed down)
                    
                    # Count commas for additional pauses
                    comma_count = transcript.count(',')
                    logger.info(f"✂️ Found {comma_count} commas for natural pauses")
                    
                    # Calculate thought pauses - more frequent for natural speech
                    thought_pauses = word_count // 10  # Increased frequency (was 12)
                    logger.info(f"🤔 Calculated {thought_pauses} natural thought pauses (1 per 10 words)")
                    
                    # Calculate minimum speaking time based on word count
                    base_speaking_time = word_count * BASE_WORD_DURATION
                    logger.info(f"⌛ Base speaking time: {base_speaking_time:.1f}s (without pauses)")
                    
                    # Calculate pause durations
                    sentence_pause_time = sentence_count * PAUSE_BETWEEN_SENTENCES
                    comma_pause_time = comma_count * PAUSE_FOR_COMMA
                    thought_pause_time = thought_pauses * PAUSE_FOR_THOUGHT
                    
                    total_pause_duration = sentence_pause_time + comma_pause_time + thought_pause_time
                    
                
                    # Calculate pause impact factor with more emphasis on longer texts
                    # New formula that scales better with text length
                    pause_impact_factor = min(0.95, max(0.75, 1.0 - (word_count / 300)))
                    logger.info(f"📉 Calculated pause impact factor: {pause_impact_factor:.2f} (adjusts for text length)")
                    
                    adjusted_pause_duration = total_pause_duration * pause_impact_factor
                    logger.info(f"⚖️ Adjusted pause duration: {adjusted_pause_duration:.1f}s (after impact factor)")
                    
                    # Calculate minimum required duration based on word count and pauses
                    # Increased the pause factor to 0.8 (was 0.7) for more natural speech
                    min_required_duration = base_speaking_time + (adjusted_pause_duration * 0.8)
                    logger.info(f"📏 Minimum required duration: {min_required_duration:.1f}s (base + essential pauses)")
                    
                    # Use the larger of calculated minimum or 80% of original (was 75%)
                    min_duration = max(min_required_duration, audio_duration_from_pron_result * 0.8)
                    logger.info(f"📐 Final minimum duration: {min_duration:.1f}s")
                    
                    # Calculate adjusted duration
                    adjusted_duration = max(min_duration, audio_duration_from_pron_result - adjusted_pause_duration)
                    
                    if adjusted_duration == min_duration:
                        logger.info(f"⚠️ Using minimum allowed duration: {adjusted_duration:.1f}s")
                    else:
                        logger.info(f"✅ Using calculated adjusted duration: {adjusted_duration:.1f}s")
                    
                    if word_count > 0:
                        # Calculate WPM using adjusted duration
                        wpm_calculated = round((word_count / adjusted_duration) * 60, 1)
                        # Add a sanity check cap for extremely high WPM values
                        wpm_calculated = min(wpm_calculated, 300)  # Cap at 300 WPM which is very fast but possible
                     
                    else:
                        logger.warning("⚠️ Transcript word count is 0. WPM will be 0.")
                else:
                    logger.warning(
                        f"DEBUG: WPM calculation skipped or failed. Transcript available: {bool(transcript)}, "
                        f"Audio duration valid: {audio_duration_from_pron_result if audio_duration_from_pron_result is not None else 'N/A'} (must be > 0). WPM will be 0."
                    )
                
                timing_metrics_for_ai['words_per_minute'] = wpm_calculated
                
                # Call original fluency analysis for grade and issues, providing the calculated WPM
                ai_fluency_analysis_result = await get_fluency_coherence_analysis(transcript, timing_metrics_for_ai)
                
                final_fluency_output = {
                    "grade": ai_fluency_analysis_result.get("grade", 0),
                    "issues": ai_fluency_analysis_result.get("issues", []),
                    "wpm": wpm_calculated,
                    "filler_word_count": ai_fluency_analysis_result.get("filler_word_count", 0),
                    "cohesive_device_band_level": ai_fluency_analysis_result.get("cohesive_device_band_level", 0),
                    "cohesive_device_feedback": ai_fluency_analysis_result.get("cohesive_device_feedback", "Cohesive device analysis not available.")
                }
                
                state["fluency_result"] = final_fluency_output
                state["fluency_done"] = True
                
                self.pubsub_client.publish_message_by_name(
                    "FLUENCY_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "total_questions": total_questions,
                        "result": final_fluency_output
                    }
                )
                logger.info(f"Fluency analysis completed for question {question_number}. WPM: {wpm_calculated}")
                
            except Exception as e:
                logger.error(f"Fluency analysis failed for question {question_number}: {str(e)}")
                state["fluency_result"] = {"error": str(e)}
                state["fluency_done"] = True
            
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
            # Update status to completed
            await db_service.update_status_logs(submission_url, question_number, "pronunciation", "completed")
            
            return {"status": "success", "message": "Pronunciation analysis completion acknowledged"}
            
        except Exception as e:
            # Update status to failed if there's an error
            await db_service.update_status_logs(submission_url, question_number, "pronunciation", "failed")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_fluency_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle fluency analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            # FIX: Remove redundant status update (now done in analysis_ready)
            db_service = DatabaseService()
            
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
            
            # Update status to completed
            await db_service.update_status_logs(submission_url, question_number, "fluency", "completed")
            
            return {"status": "success", "message": "Fluency analysis completion acknowledged"}
            
        except Exception as e:
            # Update status to failed if there's an error
            await db_service.update_status_logs(submission_url, question_number, "fluency", "failed")
            logger.error(f"Error handling fluency done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_grammar_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle grammar analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            # FIX: Remove redundant status update (now done in analysis_ready)
            db_service = DatabaseService()
            
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
            
            # FIX: Update database status FIRST, then internal state
            await db_service.update_status_logs(submission_url, question_number, "grammar", "completed")
            
            # FIX: Update grammar state to mark as done (this was missing!)
            state = self._get_or_create_analysis_state(submission_url, question_number)
            grammar_result = message_data.get("result", {})
            state["grammar_result"] = grammar_result
            state["grammar_done"] = True
            logger.info(f"✅ Marked grammar as done for question {question_number}")
            
            # Check if all analyses are complete now that grammar is done
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
            return {"status": "success", "message": "Grammar analysis completion acknowledged"}
            
        except Exception as e:
            # Update status to failed if there's an error
            await db_service.update_status_logs(submission_url, question_number, "grammar", "failed")
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
            
            # FIX: Add missing database status update for lexical!
            db_service = DatabaseService()
            await db_service.update_status_logs(submission_url, question_number, "lexical", "completed")
            
            # FIX: Update lexical state to mark as done (this was missing!)
            state = self._get_or_create_analysis_state(submission_url, question_number)
            lexical_result = message_data.get("result", {})
            state["lexical_result"] = lexical_result
            state["lexical_done"] = True
            logger.info(f"✅ Marked lexical as done for question {question_number}")
            
            # Check if all analyses are complete now that lexical is done
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
            return {"status": "success", "message": "Lexical analysis completion acknowledged"}
            
        except Exception as e:
            # Update status to failed if there's an error
            try:
                db_service = DatabaseService()
                await db_service.update_status_logs(submission_url, question_number, "lexical", "failed")
            except Exception as status_error:
                logger.error(f"Failed to update lexical status to failed: {str(status_error)}")
            logger.error(f"Error handling lexical done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def handle_vocabulary_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle vocabulary analysis completion"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            
            # FIX: Remove redundant status update (now done in analysis_ready)
            db_service = DatabaseService()
            
            total_questions = message_data.get("total_questions")
            
            # Defensive logic for missing total_questions
            if total_questions is None:
                logger.warning(f"⚠️ total_questions is None for vocabulary question {question_number}, submission {submission_url}")
                # Try to infer from existing submission state if available
                existing_state_key = self._get_submission_state_key(submission_url)
                if existing_state_key in self._submission_state:
                    total_questions = self._submission_state[existing_state_key]["total_questions"]
                    logger.info(f"🔧 Recovered total_questions={total_questions} from existing submission state")
                else:
                    total_questions = 1  # Last resort fallback
            
            logger.info(f"Vocabulary analysis acknowledged for question {question_number}")
            
            # Track vocabulary webhook call
            self._track_question(submission_url, question_number, "VOCAB_WEBHOOK_CALLED")
            
            # FIX: Update database status FIRST, then internal state
            await db_service.update_status_logs(submission_url, question_number, "vocabulary", "completed")
            
            # FIX: Update vocabulary state to mark as done (this was missing!)
            state = self._get_or_create_analysis_state(submission_url, question_number)
            vocabulary_result = message_data.get("result", {})
            state["vocabulary_result"] = vocabulary_result
            state["vocabulary_done"] = True
            logger.info(f"✅ Marked vocabulary as done for question {question_number}")
            
            # Track vocabulary state update
            self._track_question(submission_url, question_number, "VOCAB_STATE_UPDATED")
            
            # Check if all analyses are complete now that vocabulary is done
            await self._check_and_publish_completion(submission_url, question_number, total_questions)
            
            return {"status": "success", "message": "Vocabulary analysis completion acknowledged"}
            
        except Exception as e:
            # Update status to failed if there's an error
            await db_service.update_status_logs(submission_url, question_number, "vocabulary", "failed")
            logger.error(f"Error handling vocabulary done webhook: {str(e)}")
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
            
            # FIX: Use lock for thread-safe submission state updates
            async with self._get_submission_lock(submission_url):
                # Update submission-level state
                submission_state = self._get_or_create_submission_state(submission_url, total_questions)
                logger.info(f"🔍 DEBUG: Current submission state before update: completed={submission_state['completed_questions']}, total={submission_state['total_questions']}")
                
                # FIX: Ensure question_number is stored as string for consistency
                question_key = str(question_number)
                
                # FIX: Check for duplicate question processing
                if question_key in submission_state["question_results"]:
                    logger.warning(f"⚠️ Question {question_key} already processed! Skipping duplicate.")
                    self._track_question(submission_url, question_number, "DUPLICATE_SKIPPED")
                    return {"status": "success", "message": f"Question {question_key} already processed"}
                
                submission_state["question_results"][question_key] = analysis_results
                logger.info(f"🔍 DEBUG: Stored results for question key '{question_key}' (type: {type(question_key)})")
                submission_state["completed_questions"] += 1
                
                # Track completion
                self._track_question(submission_url, question_number, "QUESTION_COMPLETED", {
                    "completed_count": submission_state["completed_questions"],
                    "total_questions": submission_state["total_questions"]
                })
                
                logger.info(f"🔍 DEBUG: Updated submission state: completed={submission_state['completed_questions']}, total={submission_state['total_questions']}")
                logger.info(f"🔍 DEBUG: Current question keys in results: {list(submission_state['question_results'].keys())}")
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
            #d
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
            logger.info(f"🔍 DEBUG: Final question_results keys: {list(question_results.keys())}")
            logger.info(f"🔍 DEBUG: Expected questions 1-10, got: {sorted(question_results.keys())}")
           
            # Initialize lists for per-section scores
            pronunciation_scores_list = []
            fluency_scores_list = []
            grammar_scores_list = []
            lexical_scores_list = []

            # Initialize average scores
            avg_pronunciation_score = 0
            avg_fluency_score = 0
            avg_grammar_score = 0
            avg_lexical_score = 0

            if question_results:
                for q_num, q_data in question_results.items():
                    if q_data and isinstance(q_data, dict):
                        # Helper to safely extract grade
                        def get_grade(analysis_type, data):
                            analysis = data.get(analysis_type)
                            if analysis and isinstance(analysis, dict):
                                grade = analysis.get("grade")
                                if isinstance(grade, (int, float)):
                                    return grade
                                else:
                                    logger.warning(f"{analysis_type.capitalize()} grade for Q{q_num} is not a number ('{grade}'), skipping for this question's {analysis_type} score.")
                            else:
                                logger.warning(f"No {analysis_type} analysis data or invalid format for Q{q_num}, skipping {analysis_type} score.")
                            return None

                        pron_grade = get_grade("pronunciation", q_data)
                        flu_grade = get_grade("fluency", q_data)
                        gram_grade = get_grade("grammar", q_data)
                        lex_grade = get_grade("lexical", q_data)

                        if pron_grade is not None:
                            pronunciation_scores_list.append(pron_grade)
                        if flu_grade is not None:
                            fluency_scores_list.append(flu_grade)
                        if gram_grade is not None:
                            grammar_scores_list.append(gram_grade)
                        if lex_grade is not None:
                            lexical_scores_list.append(lex_grade)
                    else:
                        logger.warning(f"No data or invalid data format for question {q_num}, skipping score calculation for this question.")

                # Calculate averages if lists are not empty
                if pronunciation_scores_list:
                    avg_pronunciation_score = round(sum(pronunciation_scores_list) / len(pronunciation_scores_list))
                    logger.info(f"Average Pronunciation Score for {submission_url}: {avg_pronunciation_score}")
                else:
                    logger.warning(f"No valid pronunciation scores to average for {submission_url}.")
                
                if fluency_scores_list:
                    avg_fluency_score = round(sum(fluency_scores_list) / len(fluency_scores_list))
                    logger.info(f"Average Fluency Score for {submission_url}: {avg_fluency_score}")
                else:
                    logger.warning(f"No valid fluency scores to average for {submission_url}.")

                if grammar_scores_list:
                    avg_grammar_score = round(sum(grammar_scores_list) / len(grammar_scores_list))
                    logger.info(f"Average Grammar Score for {submission_url}: {avg_grammar_score}")
                else:
                    logger.warning(f"No valid grammar scores to average for {submission_url}.")

                if lexical_scores_list:
                    avg_lexical_score = round(sum(lexical_scores_list) / len(lexical_scores_list))
                    logger.info(f"Average Lexical Score for {submission_url}: {avg_lexical_score}")
                else:
                    logger.warning(f"No valid lexical scores to average for {submission_url}.")
            else:
                logger.warning(f"No question_results found for {submission_url}, all average scores will be 0.")
            
            # Create a dictionary for the overall_assignment_score JSON field
            overall_assignment_score_json = {
                "avg_pronunciation_score": avg_pronunciation_score,
                "avg_fluency_score": avg_fluency_score,
                "avg_grammar_score": avg_grammar_score,
                "avg_lexical_score": avg_lexical_score
            }
            logger.info(f"Compiled section averages for {submission_url}: {overall_assignment_score_json}")

            # --- BEGIN: IELTS Score Calculation ---
            ielts_score = None
            try:
                from app.services.ielts_scoring_service import IELTSScoringService
                
                # Get assignment questions for IELTS scoring
                db_service = DatabaseService()
                submission_row = db_service.get_submission_by_url(submission_url)
                questions = []
                
                if submission_row and 'assignment_id' in submission_row:
                    assignment_row = db_service.get_assignment_by_id(submission_row['assignment_id'])
                    if assignment_row and 'questions' in assignment_row:
                        import json
                        questions = json.loads(assignment_row['questions'])
                        logger.info(f"📊 Retrieved {len(questions)} questions for IELTS scoring")
                    else:
                        logger.warning(f"Could not fetch assignment or questions for assignment_id: {submission_row.get('assignment_id')}")
                else:
                    logger.warning(f"Could not fetch submission or assignment_id for submission_url: {submission_url}")
                
                if questions:
                    # Initialize IELTS scoring service
                    ielts_service = IELTSScoringService()
                    
                    # Calculate IELTS score
                    ielts_score = ielts_service.calculate_ielts_score(question_results, questions)
                    
                    # Add IELTS score to overall assignment score
                    overall_assignment_score_json.update({
                        "ielts_overall_band": ielts_score.overall,
                        "ielts_fluency_and_coherence": ielts_score.fluency_and_coherence,
                        "ielts_lexical_resource": ielts_score.lexical_resource,
                        "ielts_grammatical_range_and_accuracy": ielts_score.grammatical_range_and_accuracy,
                        "ielts_pronunciation": ielts_score.pronunciation
                    })
                    
                    logger.info(f"🎯 IELTS scores calculated for {submission_url}:")
                    logger.info(f"  Overall Band: {ielts_score.overall}")
                    logger.info(f"  Fluency & Coherence: {ielts_score.fluency_and_coherence}")
                    logger.info(f"  Lexical Resource: {ielts_score.lexical_resource}")
                    logger.info(f"  Grammatical Range & Accuracy: {ielts_score.grammatical_range_and_accuracy}")
                    logger.info(f"  Pronunciation: {ielts_score.pronunciation}")
                else:
                    logger.warning(f"⚠️ No questions found for IELTS scoring for submission: {submission_url}")
                    
            except Exception as e:
                logger.error(f"💥 Error calculating IELTS score for {submission_url}: {str(e)}")
                import traceback
                logger.error(f"📋 IELTS scoring error traceback: {traceback.format_exc()}")
                # Continue with submission processing even if IELTS scoring fails
            # --- END: IELTS Score Calculation ---

            # NOTE: Paragraph restructuring is now handled concurrently per question
            # in _process_question_improvement() method when each question completes analysis

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

                # --- BEGIN: Duration/TimeLimit Feedback Calculation ---
                duration_feedback = []
                try:
                    db_service = DatabaseService()
                    submission_row = db_service.get_submission_by_url(submission_url)
                    if submission_row and 'assignment_id' in submission_row:
                        assignment_row = db_service.get_assignment_by_id(submission_row['assignment_id'])
                        if assignment_row and 'questions' in assignment_row:
                            import json
                            questions = json.loads(assignment_row['questions'])
                            logger.info(f"📊 Processing duration feedback for {len(questions)} questions")
                            for idx, question in enumerate(questions):
                                q_num = str(idx + 1)
                                time_limit_sec = int(question.get('timeLimit', 0)) * 60
                                # Get actual duration from pronunciation analysis
                                actual_duration = 0
                                q_data = question_results.get(q_num)
                                if q_data and isinstance(q_data, dict):
                                    pron = q_data.get('pronunciation')
                                    if pron and isinstance(pron, dict):
                                        actual_duration = pron.get('audio_duration', 0)
                                        logger.info(f"📊 Question {q_num}: Found audio_duration={actual_duration}s, time_limit={time_limit_sec}s")
                                    else:
                                        logger.warning(f"⚠️ Question {q_num}: No pronunciation data found")
                                else:
                                    logger.warning(f"⚠️ Question {q_num}: No question data found")
                                ratio = (actual_duration / time_limit_sec) * 100 if time_limit_sec > 0 else 0
                                if ratio < 50:
                                    feedback = "Did not speak that much."
                                elif ratio <= 100:
                                    feedback = "User spoke longer."
                                else:
                                    feedback = "User exceeded the time limit."
                                duration_feedback.append({
                                    'question_number': q_num,
                                    'feedback': feedback,
                                    'ratio': ratio,
                                    'actual_duration': actual_duration,
                                    'time_limit_sec': time_limit_sec
                                })
                                logger.info(f"📊 Question {q_num} duration feedback: {feedback} (ratio={ratio:.1f}%)")
                        else:
                            logger.warning(f"Could not fetch assignment or questions for assignment_id: {submission_row.get('assignment_id')}")
                    else:
                        logger.warning(f"Could not fetch submission or assignment_id for submission_url: {submission_url}")
                except Exception as e:
                    logger.error(f"Error calculating duration/timeLimit feedback: {str(e)}")
                    import traceback
                    logger.error(f"📋 Full traceback for duration feedback calculation: {traceback.format_exc()}")
                # --- END: Duration/TimeLimit Feedback Calculation ---

                # Log duration feedback before database update
                if duration_feedback:
                    logger.info(f"📊 Duration feedback summary: {len(duration_feedback)} questions processed")
                    for fb in duration_feedback:
                        logger.info(f"  Q{fb['question_number']}: {fb['feedback']} ({fb['ratio']:.1f}%)")
                else:
                    logger.warning("⚠️ No duration feedback to send to database")

                # 2. Update the existing submission with analysis results
                logger.info(f"💽 Updating existing submission in Supabase 'submissions' table: {submission_url}")
                submission_db_id = db_service.update_submission_results(
                    submission_url=submission_url,
                    question_results=question_results,
                    recordings=recording_urls,
                    overall_assignment_score=overall_assignment_score_json,
                    duration_feedback=duration_feedback
                )
                
                if submission_db_id:
                    logger.info(f"✅ SUCCESS: Updated submission {submission_url} in Supabase database with ID: {submission_db_id}")
                    logger.info(f"📋 Database record updated: table=submissions, id={submission_db_id}, status=graded, recordings_count={len(recording_urls or [])}")
                else:
                    error_msg = f"Failed to update submission {submission_url} in Supabase database"
                    logger.error(f"❌ {error_msg} - update_submission_results returned None")
                    logger.error(f"🔍 Check if submission {submission_url} exists in database and has correct permissions")
                    
                    # Rollback status logs for all analyses to failed
                    logger.warning(f"🔄 Rolling back status logs to 'failed' due to result storage failure")
                    analysis_types = ["pronunciation", "fluency", "grammar", "vocabulary"]
                    for question_num in question_results.keys():
                        for analysis_type in analysis_types:
                            try:
                                await db_service.update_status_logs(submission_url, int(question_num), analysis_type, "failed")
                                logger.info(f"🔄 Rolled back Q{question_num} {analysis_type} status to 'failed'")
                            except Exception as rollback_error:
                                logger.error(f"❌ Failed to rollback Q{question_num} {analysis_type} status: {rollback_error}")
                    
                    raise HTTPException(status_code=500, detail=error_msg)
                    
            except Exception as e:
                error_msg = f"Exception during Supabase database operation for submission {submission_url}: {str(e)}"
                logger.error(f"💥 {error_msg}")
                logger.error(f"🔍 Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"📋 Full traceback for submission {submission_url}: {traceback.format_exc()}")
                
                # Rollback status logs for all analyses to failed on exception
                logger.warning(f"🔄 Rolling back status logs to 'failed' due to database exception")
                analysis_types = ["pronunciation", "fluency", "grammar", "vocabulary"]
                try:
                    for question_num in question_results.keys():
                        for analysis_type in analysis_types:
                            try:
                                await db_service.update_status_logs(submission_url, int(question_num), analysis_type, "failed")
                                logger.info(f"🔄 Rolled back Q{question_num} {analysis_type} status to 'failed'")
                            except Exception as rollback_error:
                                logger.error(f"❌ Failed to rollback Q{question_num} {analysis_type} status: {rollback_error}")
                except Exception as rollback_exception:
                    logger.error(f"❌ Critical error during status rollback: {rollback_exception}")
                
                raise HTTPException(status_code=500, detail=error_msg)

            logger.info(f"🏁 Completed all operations for submission: {submission_url}")
            
            # Add duration_feedback to message_data for storage and API
            message_data['duration_feedback'] = duration_feedback

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

    async def _process_question_improvement(self, submission_url: str, question_number: int, analysis_results: Dict[str, Any]):
        """Process paragraph improvement for a single question concurrently"""
        try:
            logger.info(f"🔄 Starting concurrent paragraph improvement for question {question_number}")
            
            from app.services.paragraph_restructuring_service import restructure_paragraph
            
            # Extract transcript from analysis results
            transcript = ""
            
            # Try to get transcript from top level first
            if "transcript" in analysis_results:
                transcript = analysis_results["transcript"] or ""
            # Fallback to pronunciation results
            elif "pronunciation" in analysis_results and isinstance(analysis_results["pronunciation"], dict):
                transcript = analysis_results["pronunciation"].get("transcript", "")
            
            if transcript and transcript.strip():
                logger.info(f"📝 Processing paragraph restructuring for question {question_number}")
                
                # Restructure paragraph using all analysis results for band detection
                restructuring_result = await restructure_paragraph(
                    transcript=transcript,
                    analysis_results=analysis_results
                )
                
                # Add restructuring result to question results
                analysis_results["paragraph_restructuring"] = {
                    "original_band": restructuring_result.original_band,
                    "target_band": restructuring_result.target_band,
                    "improved_transcript": restructuring_result.improved_transcript
                }
                
                logger.info(f"✅ Paragraph restructuring completed for question {question_number}: {restructuring_result.original_band} → {restructuring_result.target_band}")
                
                # Update improvement completion tracking
                improvement_key = f"improvement:{submission_url}:{question_number}"
                self._improvement_state[improvement_key] = {
                    "completed": True,
                    "result": restructuring_result
                }
                
            else:
                logger.warning(f"⚠️ No transcript found for question {question_number}, skipping paragraph restructuring")
                
        except Exception as e:
            logger.error(f"💥 Error in concurrent paragraph restructuring for question {question_number}: {str(e)}")
            import traceback
            logger.error(f"📋 Improvement error traceback: {traceback.format_exc()}")
            # Don't fail the whole process if one improvement fails

    async def _check_and_publish_completion(self, submission_url: str, question_number: int, total_questions: int):
        """Check if all analyses are complete and publish completion if they are."""
        try:
            state = self._get_or_create_analysis_state(submission_url, question_number)
            
            # Check if all analyses are complete
            pron_done = state.get("pronunciation_done", False)
            gram_done = state.get("grammar_done", False)
            lex_done = state.get("lexical_done", False)
            flu_done = state.get("fluency_done", False)
            vocab_done = state.get("vocabulary_done", False)
            
            # FIX: Add detailed completion tracking
            logger.info(f"🔍 COMPLETION CHECK Q{question_number}: pron={pron_done}, gram={gram_done}, lex={lex_done}, flu={flu_done}, vocab={vocab_done}")
            
            # Track completion check
            self._track_question(submission_url, question_number, "COMPLETION_CHECK", {
                "pronunciation": pron_done,
                "grammar": gram_done,
                "lexical": lex_done,
                "fluency": flu_done,
                "vocabulary": vocab_done
            })
            
            all_done = all([pron_done, gram_done, lex_done, flu_done, vocab_done])
            
            if all_done:
                logger.info(f"🎉 All analyses complete for question {question_number}")
                logger.info(f"🔍 QUESTION {question_number} READY FOR COMPLETION - Submission: {submission_url}")
                self._track_question(submission_url, question_number, "ALL_ANALYSES_COMPLETE")
                
                # Compile all results INCLUDING the missing fields
                analysis_results = {
                    "pronunciation": state.get("pronunciation_result"),
                    "grammar": state.get("grammar_result"),
                    "lexical": state.get("lexical_result"),
                    "fluency": state.get("fluency_result"),
                    "vocabulary": state.get("vocabulary_result"),
                    "original_audio_url": state.get("audio_url"),
                    "transcript": state.get("transcript"),
                    "clean_transcript": state.get("clean_transcript")
                }
                
                # Process paragraph improvement synchronously to ensure it's included in results
                await self._process_question_improvement(submission_url, question_number, analysis_results)
                
                # Publish analysis complete message with paragraph restructuring included
                self.pubsub_client.publish_message_by_name(
                    "ANALYSIS_COMPLETE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "total_questions": total_questions,
                        "analysis_results": analysis_results
                    }
                )
                
                # Clean up state
                self._cleanup_analysis_state(submission_url, question_number)
                
        except Exception as e:
            logger.error(f"Error checking completion for question {question_number}: {str(e)}")
            raise 