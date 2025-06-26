import logging
import asyncio
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.audio_service import AudioService
from app.services.question_retry_service import question_retry_service, RetryStage, RetryReason

logger = logging.getLogger(__name__)

class AudioWebhook:
    """Webhook handler for audio conversion messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_service = AudioService()
        # Set up retry service dependencies
        question_retry_service.set_dependencies(
            audio_service=self.audio_service,
            transcription_service=None,  # Will be set by transcription webhook
            pubsub_client=self.pubsub_client
        )
        
    async def process_single_question(self, audio_url: str, question_number: int, submission_url: str, total_questions: int = None) -> None:
        """Process a single question's audio and publish result"""
        try:
            # Process the audio
            result = await self.audio_service.process_single_audio(
                audio_url=audio_url,
                question_number=question_number,
                submission_url=submission_url
            )
            
            # Publish the result with session_id
            message_data = {
                "wav_path": result["wav_path"],
                "session_id": result["session_id"],  # Include session ID for file lifecycle management
                "question_number": question_number,
                "submission_url": submission_url,
                "original_audio_url": audio_url
            }
            
            # Add total_questions if available
            if total_questions is not None:
                message_data["total_questions"] = total_questions
            
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="AUDIO_CONVERSION_DONE",
                message=message_data
            )
            logger.info(f"Published audio conversion result for question {question_number} with session {result['session_id']} - Message ID: {message_id}")
            
        except Exception as e:
            logger.error(f"Error processing audio for question {question_number}: {str(e)}")
            
            # Register failure for retry
            retry_stage = RetryStage.AUDIO_DOWNLOAD
            retry_reason = RetryReason.FILE_NOT_FOUND
            
            # Determine retry stage and reason based on error
            error_str = str(e).lower()
            if "download" in error_str or "failed to download" in error_str:
                retry_stage = RetryStage.AUDIO_DOWNLOAD
                retry_reason = RetryReason.NETWORK_ERROR
            elif "convert" in error_str or "ffmpeg" in error_str:
                retry_stage = RetryStage.AUDIO_CONVERSION
                retry_reason = RetryReason.PROCESSING_ERROR
            elif "timeout" in error_str:
                retry_reason = RetryReason.API_TIMEOUT
            elif "not found" in error_str or "404" in error_str:
                retry_reason = RetryReason.FILE_NOT_FOUND
            else:
                retry_reason = RetryReason.PROCESSING_ERROR
            
            question_retry_service.register_question_failure(
                question_number=question_number,
                audio_url=audio_url,
                submission_url=submission_url,
                stage=retry_stage,
                reason=retry_reason,
                error=str(e)
            )
            
            # Don't re-raise - let other questions continue
            logger.warning(f"Audio processing failed for question {question_number}, registered for retry")
    
    async def process_submission_for_audio(self, message_data: Dict[str, Any]) -> None:
        """Process submission for audio - used by coordinator"""
        audio_urls = message_data.get("audio_urls", [])
        submission_url = message_data.get("submission_url")
        total_questions = message_data.get("total_questions")
        
        if not audio_urls or not submission_url:
            logger.error("Missing required fields in submission message")
            raise ValueError("Missing required fields: audio_urls or submission_url")
            
        logger.info(f"Processing {len(audio_urls)} audio files for submission: {submission_url}")
        
        # Create tasks for all questions
        tasks = []
        for question_number, audio_url in enumerate(audio_urls, 1):
            task = self.process_single_question(
                audio_url=audio_url,
                question_number=question_number,
                submission_url=submission_url,
                total_questions=total_questions
            )
            tasks.append(task)
        
        # Process all questions in parallel with graceful error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        successful_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            question_number = i + 1
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"Audio processing failed for question {question_number}: {str(result)}")
            else:
                successful_count += 1
        
        logger.info(f"Audio processing completed for submission {submission_url}: {successful_count} successful, {failed_count} failed")
        
        # If some questions failed, attempt immediate retry for quick failures
        if failed_count > 0:
            logger.info(f"Attempting immediate retry for failed questions in submission {submission_url}")
            retry_results = await question_retry_service.retry_failed_questions(submission_url)
            logger.info(f"Retry results: {retry_results}")
        
    async def handle_student_submission_webhook(self, request: Request) -> Dict[str, str]:
        """Handle student submission webhook from Pub/Sub push
        
        Args:
            request: FastAPI Request object containing Pub/Sub push message
            
        Returns:
            Success response
        """
        try:
            # Parse the Pub/Sub message
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            await self.process_submission_for_audio(message_data)
            
            return {"status": "success", "message": "Audio processing completed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling audio processing webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 