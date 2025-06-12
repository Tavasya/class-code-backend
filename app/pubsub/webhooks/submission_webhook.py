import logging
import asyncio
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.pubsub.webhooks.audio_webhook import AudioWebhook
from app.pubsub.webhooks.transcription_webhook import TranscriptionWebhook
from app.services.database_service import DatabaseService
from datetime import datetime

logger = logging.getLogger(__name__)

class SubmissionWebhook:
    """Webhook handler that processes submissions by starting both audio and transcription in parallel"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_webhook = AudioWebhook()
        self.transcription_webhook = TranscriptionWebhook()
        
    async def handle_student_submission_webhook(self, request: Request) -> Dict[str, str]:
        """Handle student submission webhook from Pub/Sub push - starts both audio and transcription in parallel
        
        Args:
            request: FastAPI Request object containing Pub/Sub push message
            
        Returns:
            Success response
        """
        try:
            # Parse the Pub/Sub message
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            submission_url = message_data.get("submission_url", "unknown")
            audio_urls = message_data.get("audio_urls", [])
            
            # Initialize status logs
            db_service = DatabaseService()
            initial_logs = {
                "submission_started": datetime.now().isoformat(),
                "total_questions": len(audio_urls),
                "questions": {}
            }
            
            # Initialize status for each question
            for q_num in range(1, len(audio_urls) + 1):
                initial_logs["questions"][str(q_num)] = {
                    "pronunciation": "not_started",
                    "fluency": "not_started",
                    "grammar": "not_started",
                    "vocabulary": "not_started",
                    "started_at": datetime.now().isoformat()
                }
            
            # Update the submission with initial status logs
            db_service.update_submission_status_logs(submission_url, initial_logs)
            
            logger.info(f"Starting parallel processing for submission {submission_url} with {len(audio_urls)} audio files")
            
            # Start both audio and transcription processing in parallel
            await asyncio.gather(
                self.audio_webhook.process_submission_for_audio(message_data),
                self.transcription_webhook.process_submission_for_transcription(message_data),
                return_exceptions=True  # Don't fail if one service has issues
            )
            
            logger.info(f"Successfully started parallel processing for submission {submission_url}")
            
            return {
                "status": "success", 
                "message": f"Both audio and transcription processing started for {len(audio_urls)} files"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling submission webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 