import logging
import asyncio
import uuid
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.audio_service import AudioService
from app.services.pronunciation_service import PronunciationService
from app.services.database_service import DatabaseService
from app.core.results_store import ResultsStore

logger = logging.getLogger(__name__)

class PracticeWebhook:
    """Webhook handler for practice pronunciation messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_service = AudioService()
        self.pronunciation_service = PronunciationService()
        self.database_service = DatabaseService()
        self.results_store = ResultsStore()
        
    async def process_practice_pronunciation(self, message_data: Dict[str, Any]) -> None:
        """Process practice pronunciation request and publish result"""
        try:
            # Extract data from message
            audio_url = message_data.get("audio_url")
            transcript = message_data.get("transcript")
            user_id = message_data.get("user_id")
            request_id = message_data.get("request_id")
            webhook_url = message_data.get("webhook_url")  # Where to send the result
            
            if not audio_url or not transcript or not request_id:
                logger.error("Missing required fields in practice pronunciation message")
                raise ValueError("Missing required fields: audio_url, transcript, or request_id")
                
            logger.info(f"🎤 Processing practice pronunciation for request: {request_id}")
            logger.info(f"🔗 Audio URL: {audio_url}")
            logger.info(f"📝 Reference transcript: {transcript[:100]}...")
            
            # Download audio from URL
            temp_audio_file = await self.audio_service.download_audio(audio_url)
            logger.info(f"📁 Downloaded audio to: {temp_audio_file}")
            
            # Convert to WAV if needed
            if not temp_audio_file.endswith('.wav'):
                wav_file = await self.audio_service.convert_webm_to_wav(temp_audio_file)
                # Clean up original file
                try:
                    import os
                    os.unlink(temp_audio_file)
                except:
                    pass
                temp_audio_file = wav_file
                logger.info(f"🎵 Converted to WAV: {temp_audio_file}")
            
            # Generate session ID for pronunciation analysis
            session_id = str(uuid.uuid4())
            
            # Analyze pronunciation
            result = await self.pronunciation_service.analyze_pronunciation(
                temp_audio_file, 
                transcript, 
                session_id=session_id
            )
            
            # Clean up temporary file
            try:
                import os
                os.unlink(temp_audio_file)
                logger.info(f"🧹 Cleaned up temp file: {temp_audio_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_audio_file}: {e}")
            
            # Store result in database/results store
            if result:
                # Store in results store for retrieval
                await self.results_store.store_result(
                    request_id=request_id,
                    result_type="practice_pronunciation",
                    result=result,
                    user_id=user_id
                )
                logger.info(f"📊 Stored practice pronunciation result for request: {request_id}")
            
            # Publish completion message
            completion_message = {
                "request_id": request_id,
                "user_id": user_id,
                "status": "completed" if result else "failed",
                "result": result,
                "webhook_url": webhook_url,
                "processing_time_ms": message_data.get("start_time", 0)  # Calculate if needed
            }
            
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="PRACTICE_PRONUNCIATION_DONE",
                message=completion_message
            )
            logger.info(f"✅ Published practice pronunciation completion - Message ID: {message_id}")
            
        except Exception as e:
            logger.error(f"Error processing practice pronunciation: {str(e)}")
            
            # Publish failure message
            failure_message = {
                "request_id": message_data.get("request_id"),
                "user_id": message_data.get("user_id"),
                "status": "failed",
                "error": str(e),
                "webhook_url": message_data.get("webhook_url")
            }
            
            try:
                message_id = self.pubsub_client.publish_message_by_name(
                    topic_name="PRACTICE_PRONUNCIATION_DONE",
                    message=failure_message
                )
                logger.info(f"❌ Published practice pronunciation failure - Message ID: {message_id}")
            except Exception as pub_error:
                logger.error(f"Failed to publish failure message: {str(pub_error)}")
                
            # Don't re-raise - let the pub/sub system handle retries
            
    async def handle_practice_pronunciation_webhook(self, request: Request) -> Dict[str, str]:
        """Handle practice pronunciation webhook from Pub/Sub push
        
        Args:
            request: FastAPI Request object containing Pub/Sub push message
            
        Returns:
            Success response
        """
        try:
            # Parse the Pub/Sub message
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            await self.process_practice_pronunciation(message_data)
            
            return {"status": "success", "message": "Practice pronunciation processing completed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling practice pronunciation webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 