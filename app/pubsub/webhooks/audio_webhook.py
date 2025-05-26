import logging
import asyncio
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)

class AudioWebhook:
    """Webhook handler for audio conversion messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_service = AudioService()
        
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
            raise
    
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
        
        # Process all questions in parallel
        await asyncio.gather(*tasks)
        logger.info(f"Successfully processed all audio files for submission: {submission_url}")
        
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