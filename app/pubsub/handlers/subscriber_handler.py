import logging
import asyncio
from typing import Dict, Any
from app.pubsub.client import PubSubClient
from app.pubsub.subscribers.audio_subscriber import AudioSubscriber
from app.pubsub.subscribers.transcription_subscriber import TranscriptionSubscriber

logger = logging.getLogger(__name__)

class SubscriberHandler:
    """Main handler for routing messages to appropriate subscribers"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_subscriber = AudioSubscriber()
        self.transcription_subscriber = TranscriptionSubscriber()
        
    async def handle_submission(self, message: Dict[str, Any]) -> None:
        """Handle a student submission by starting both services in parallel"""
        try:
            # Start both services in parallel
            await asyncio.gather(
                self.audio_subscriber.handle_message(message),
                self.transcription_subscriber.handle_message(message)
            )
        except Exception as e:
            logger.error(f"Error handling submission: {str(e)}")
            raise
        
    async def start_listening(self) -> None:
        """Start listening for messages on all subscriptions"""
        while True:
            try:
                # Pull messages from student submission subscription
                submission_messages = self.pubsub_client.pull_messages("STUDENT_SUBMISSION")
                for message in submission_messages:
                    await self.handle_submission(message["data"])
                
                # Sleep briefly to avoid tight polling
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in subscriber handler: {str(e)}")
                # Sleep longer on error to avoid tight error loops
                await asyncio.sleep(5) 