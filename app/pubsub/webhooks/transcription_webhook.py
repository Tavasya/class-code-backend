import logging
import asyncio
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.transcription_service import TranscriptionService
from app.services.question_retry_service import question_retry_service, RetryStage, RetryReason

logger = logging.getLogger(__name__)

class TranscriptionWebhook:
    """Webhook handler for transcription messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.transcription_service = TranscriptionService()
        # Update retry service dependencies
        question_retry_service.set_dependencies(
            audio_service=question_retry_service.audio_service,  # Keep existing
            transcription_service=self.transcription_service,
            pubsub_client=self.pubsub_client
        )
        
    async def process_single_question(self, audio_url: str, question_number: int, submission_url: str, total_questions: int = None) -> None:
        """Process a single question's transcription and publish result"""
        try:
            # Process the transcription
            result = await self.transcription_service.process_single_transcription(
                audio_url=audio_url,
                question_number=question_number,
                submission_url=submission_url
            )
            
            # Publish the result
            message_data = {
                "text": result["text"],
                "error": result["error"],
                "question_number": question_number,
                "submission_url": submission_url,
                "audio_url": audio_url
            }
            
            # Add total_questions if available
            if total_questions is not None:
                message_data["total_questions"] = total_questions
            
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="TRANSCRIPTION_DONE",
                message=message_data
            )
            logger.info(f"Published transcription result for question {question_number} with message ID: {message_id}")
            
        except Exception as e:
            logger.error(f"Error processing transcription for question {question_number}: {str(e)}")
            
            # Register failure for retry
            retry_reason = RetryReason.EXTERNAL_API_ERROR
            
            # Determine retry reason based on error
            error_str = str(e).lower()
            if "timeout" in error_str:
                retry_reason = RetryReason.API_TIMEOUT
            elif "network" in error_str or "connection" in error_str:
                retry_reason = RetryReason.NETWORK_ERROR
            elif "not found" in error_str or "404" in error_str:
                retry_reason = RetryReason.FILE_NOT_FOUND
            elif "assemblyai" in error_str or "api" in error_str:
                retry_reason = RetryReason.EXTERNAL_API_ERROR
            else:
                retry_reason = RetryReason.PROCESSING_ERROR
            
            question_retry_service.register_question_failure(
                question_number=question_number,
                audio_url=audio_url,
                submission_url=submission_url,
                stage=RetryStage.TRANSCRIPTION,
                reason=retry_reason,
                error=str(e)
            )
            
            # Don't re-raise - let other questions continue
            logger.warning(f"Transcription processing failed for question {question_number}, registered for retry")
    
    async def process_submission_for_transcription(self, message_data: Dict[str, Any]) -> None:
        """Process submission for transcription - used by coordinator"""
        audio_urls = message_data.get("audio_urls", [])
        submission_url = message_data.get("submission_url")
        total_questions = message_data.get("total_questions")
        
        if not audio_urls or not submission_url:
            logger.error("Missing required fields in submission message")
            raise ValueError("Missing required fields: audio_urls or submission_url")
            
        logger.info(f"Processing transcription for {len(audio_urls)} audio files for submission: {submission_url}")
        
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
                logger.error(f"Transcription processing failed for question {question_number}: {str(result)}")
            else:
                successful_count += 1
        
        logger.info(f"Transcription processing completed for submission {submission_url}: {successful_count} successful, {failed_count} failed")
        
        # If some questions failed, attempt immediate retry for quick failures
        if failed_count > 0:
            logger.info(f"Attempting immediate retry for failed questions in submission {submission_url}")
            retry_results = await question_retry_service.retry_failed_questions(submission_url)
            logger.info(f"Retry results: {retry_results}")
        
    async def handle_student_submission_webhook(self, request: Request) -> Dict[str, str]:
        """Handle student submission webhook from Pub/Sub push for transcription
        
        Args:
            request: FastAPI Request object containing Pub/Sub push message
            
        Returns:
            Success response
        """
        try:
            # Parse the Pub/Sub message
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            await self.process_submission_for_transcription(message_data)
            
            return {"status": "success", "message": "Transcription processing completed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling transcription processing webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 