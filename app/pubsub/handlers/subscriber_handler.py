import logging
import asyncio
from typing import Dict, Any
from app.pubsub.client import PubSubClient
from app.pubsub.webhooks.audio_webhook import AudioWebhook
from app.pubsub.webhooks.transcription_webhook import TranscriptionWebhook

logger = logging.getLogger(__name__)

class SubscriberHandler:
    """Handler for coordinating webhook-based message processing"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_webhook = AudioWebhook()
        self.transcription_webhook = TranscriptionWebhook()
        
    async def handle_submission(self, message: Dict[str, Any]) -> None:
        """Handle a student submission by starting both services in parallel
        
        Args:
            message: The message data containing audio URLs and submission details
        """
        try:
            # Start both services in parallel
            await asyncio.gather(
                self.audio_webhook.process_submission_for_audio(message),
                self.transcription_webhook.process_submission_for_transcription(message)
            )
        except Exception as e:
            logger.error(f"Error handling submission: {str(e)}")
            raise
    
    # Note: The start_listening method has been removed as we now use push-based webhooks
    # instead of polling. The webhook endpoints in webhooks_endpoint.py handle incoming
    # Pub/Sub push messages directly. 