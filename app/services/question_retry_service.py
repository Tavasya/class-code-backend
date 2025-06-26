import logging
import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RetryStage(Enum):
    """Stages where retries can occur"""
    AUDIO_DOWNLOAD = "audio_download"
    AUDIO_CONVERSION = "audio_conversion"
    TRANSCRIPTION = "transcription"
    ANALYSIS = "analysis"

class RetryReason(Enum):
    """Reasons for retry"""
    FILE_NOT_FOUND = "file_not_found"
    NETWORK_ERROR = "network_error"
    API_TIMEOUT = "api_timeout"
    PROCESSING_ERROR = "processing_error"
    EXTERNAL_API_ERROR = "external_api_error"

@dataclass
class QuestionRetryState:
    """Track retry state for individual questions"""
    question_number: int
    audio_url: str
    submission_url: str
    stage: RetryStage
    reason: RetryReason
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: str = ""
    last_attempt_time: datetime = field(default_factory=datetime.now)
    backoff_seconds: int = 5
    
    def should_retry(self) -> bool:
        """Check if question should be retried"""
        if self.attempt_count >= self.max_attempts:
            return False
        
        # Apply exponential backoff
        time_since_last = datetime.now() - self.last_attempt_time
        required_wait = timedelta(seconds=self.backoff_seconds * (2 ** self.attempt_count))
        
        return time_since_last >= required_wait
    
    def increment_attempt(self, error: str):
        """Increment attempt count and update state"""
        self.attempt_count += 1
        self.last_error = error
        self.last_attempt_time = datetime.now()

class QuestionRetryService:
    """Service for handling individual question retries"""
    
    def __init__(self):
        self.retry_states: Dict[str, QuestionRetryState] = {}
        self.audio_service = None  # Will be injected
        self.transcription_service = None  # Will be injected
        self.pubsub_client = None  # Will be injected
    
    def set_dependencies(self, audio_service, transcription_service, pubsub_client):
        """Inject service dependencies"""
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.pubsub_client = pubsub_client
    
    def _get_retry_key(self, submission_url: str, question_number: int) -> str:
        """Generate unique key for retry tracking"""
        return f"{submission_url}:{question_number}"
    
    def register_question_failure(
        self,
        question_number: int,
        audio_url: str,
        submission_url: str,
        stage: RetryStage,
        reason: RetryReason,
        error: str,
        max_attempts: int = 3
    ):
        """Register a question failure for potential retry"""
        retry_key = self._get_retry_key(submission_url, question_number)
        
        if retry_key in self.retry_states:
            # Update existing retry state
            retry_state = self.retry_states[retry_key]
            retry_state.stage = stage
            retry_state.reason = reason
            retry_state.increment_attempt(error)
        else:
            # Create new retry state
            retry_state = QuestionRetryState(
                question_number=question_number,
                audio_url=audio_url,
                submission_url=submission_url,
                stage=stage,
                reason=reason,
                max_attempts=max_attempts,
                last_error=error
            )
            retry_state.increment_attempt(error)
            self.retry_states[retry_key] = retry_state
        
        logger.info(f"Registered failure for question {question_number} at stage {stage.value}: {error}")
        logger.info(f"Attempt {retry_state.attempt_count}/{retry_state.max_attempts}")
    
    async def retry_failed_questions(self, submission_url: str) -> Dict[str, Any]:
        """Retry all failed questions for a submission that are ready for retry"""
        retry_results = {
            "retried": [],
            "skipped": [],
            "exhausted": [],
            "successful": [],
            "failed": []
        }
        
        # Find questions for this submission that need retry
        questions_to_retry = []
        for retry_key, retry_state in self.retry_states.items():
            if retry_state.submission_url == submission_url:
                if retry_state.should_retry():
                    questions_to_retry.append(retry_state)
                elif retry_state.attempt_count >= retry_state.max_attempts:
                    retry_results["exhausted"].append({
                        "question_number": retry_state.question_number,
                        "last_error": retry_state.last_error,
                        "attempts": retry_state.attempt_count
                    })
                else:
                    retry_results["skipped"].append({
                        "question_number": retry_state.question_number,
                        "reason": "waiting_for_backoff"
                    })
        
        if not questions_to_retry:
            logger.info(f"No questions ready for retry in submission {submission_url}")
            return retry_results
        
        logger.info(f"Retrying {len(questions_to_retry)} questions for submission {submission_url}")
        
        # Process retries with graceful error handling
        retry_tasks = []
        for retry_state in questions_to_retry:
            task = self._retry_single_question(retry_state)
            retry_tasks.append(task)
        
        # Use return_exceptions=True to handle individual failures gracefully
        results = await asyncio.gather(*retry_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            retry_state = questions_to_retry[i]
            retry_results["retried"].append(retry_state.question_number)
            
            if isinstance(result, Exception):
                logger.error(f"Retry failed for question {retry_state.question_number}: {str(result)}")
                retry_results["failed"].append({
                    "question_number": retry_state.question_number,
                    "error": str(result)
                })
                # Update retry state for next retry
                self.register_question_failure(
                    retry_state.question_number,
                    retry_state.audio_url,
                    retry_state.submission_url,
                    retry_state.stage,
                    retry_state.reason,
                    str(result),
                    retry_state.max_attempts
                )
            else:
                logger.info(f"Retry successful for question {retry_state.question_number}")
                retry_results["successful"].append(retry_state.question_number)
                # Remove from retry state
                retry_key = self._get_retry_key(retry_state.submission_url, retry_state.question_number)
                self.retry_states.pop(retry_key, None)
        
        return retry_results
    
    async def _retry_single_question(self, retry_state: QuestionRetryState):
        """Retry a single question based on its failure stage"""
        logger.info(f"Retrying question {retry_state.question_number} at stage {retry_state.stage.value}")
        
        try:
            if retry_state.stage == RetryStage.AUDIO_DOWNLOAD or retry_state.stage == RetryStage.AUDIO_CONVERSION:
                await self._retry_audio_processing(retry_state)
            elif retry_state.stage == RetryStage.TRANSCRIPTION:
                await self._retry_transcription(retry_state)
            elif retry_state.stage == RetryStage.ANALYSIS:
                await self._retry_analysis(retry_state)
            else:
                raise ValueError(f"Unknown retry stage: {retry_state.stage}")
        
        except Exception as e:
            logger.error(f"Retry failed for question {retry_state.question_number}: {str(e)}")
            raise
    
    async def _retry_audio_processing(self, retry_state: QuestionRetryState):
        """Retry audio processing (download + conversion)"""
        try:
            result = await self.audio_service.process_single_audio(
                audio_url=retry_state.audio_url,
                question_number=retry_state.question_number,
                submission_url=retry_state.submission_url
            )
            
            # Publish success message
            message_data = {
                "wav_path": result["wav_path"],
                "session_id": result["session_id"],
                "question_number": retry_state.question_number,
                "submission_url": retry_state.submission_url,
                "original_audio_url": retry_state.audio_url,
                "retry_attempt": True
            }
            
            self.pubsub_client.publish_message_by_name(
                topic_name="AUDIO_CONVERSION_DONE",
                message=message_data
            )
            
            logger.info(f"Successfully retried audio processing for question {retry_state.question_number}")
            
        except Exception as e:
            logger.error(f"Audio retry failed for question {retry_state.question_number}: {str(e)}")
            raise
    
    async def _retry_transcription(self, retry_state: QuestionRetryState):
        """Retry transcription processing"""
        try:
            result = await self.transcription_service.process_single_transcription(
                audio_url=retry_state.audio_url,
                question_number=retry_state.question_number,
                submission_url=retry_state.submission_url
            )
            
            # Publish success message
            message_data = {
                "text": result["text"],
                "error": result["error"],
                "question_number": retry_state.question_number,
                "submission_url": retry_state.submission_url,
                "original_audio_url": retry_state.audio_url,
                "retry_attempt": True
            }
            
            self.pubsub_client.publish_message_by_name(
                topic_name="TRANSCRIPTION_DONE",
                message=message_data
            )
            
            logger.info(f"Successfully retried transcription for question {retry_state.question_number}")
            
        except Exception as e:
            logger.error(f"Transcription retry failed for question {retry_state.question_number}: {str(e)}")
            raise
    
    async def _retry_analysis(self, retry_state: QuestionRetryState):
        """Retry analysis processing - would need analysis coordinator integration"""
        # This would trigger the analysis pipeline again
        # Implementation depends on how analysis is coordinated
        logger.info(f"Analysis retry not yet implemented for question {retry_state.question_number}")
        pass
    
    def get_retry_status(self, submission_url: str) -> Dict[str, Any]:
        """Get retry status for a submission"""
        status = {
            "total_retries": 0,
            "pending_retries": 0,
            "exhausted_retries": 0,
            "questions": []
        }
        
        for retry_key, retry_state in self.retry_states.items():
            if retry_state.submission_url == submission_url:
                status["total_retries"] += 1
                
                if retry_state.should_retry():
                    status["pending_retries"] += 1
                elif retry_state.attempt_count >= retry_state.max_attempts:
                    status["exhausted_retries"] += 1
                
                status["questions"].append({
                    "question_number": retry_state.question_number,
                    "stage": retry_state.stage.value,
                    "reason": retry_state.reason.value,
                    "attempts": retry_state.attempt_count,
                    "max_attempts": retry_state.max_attempts,
                    "can_retry": retry_state.should_retry(),
                    "last_error": retry_state.last_error
                })
        
        return status
    
    def cleanup_old_retries(self, max_age_hours: int = 24):
        """Clean up old retry states"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for retry_key, retry_state in self.retry_states.items():
            if retry_state.last_attempt_time < cutoff_time:
                to_remove.append(retry_key)
        
        for retry_key in to_remove:
            self.retry_states.pop(retry_key, None)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old retry states")

# Global retry service instance
question_retry_service = QuestionRetryService()