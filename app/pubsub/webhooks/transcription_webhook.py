import logging
import asyncio
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

class TranscriptionWebhook:
    """Webhook handler for transcription messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.transcription_service = TranscriptionService()
        
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
            raise
    
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
        
        # Process all questions in parallel
        await asyncio.gather(*tasks)
        logger.info(f"Successfully processed all transcriptions for submission: {submission_url}")
        
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