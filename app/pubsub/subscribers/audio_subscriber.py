import logging
import asyncio
from typing import Dict, Any, List
from app.pubsub.client import PubSubClient
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)

class AudioSubscriber:
    """Subscriber for handling audio conversion messages"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.audio_service = AudioService()
        
    async def process_single_question(self, audio_url: str, question_number: int, submission_url: str) -> None:
        """Process a single question's audio and publish result"""
        try:
            # Process the audio
            result = await self.audio_service.process_single_audio(
                audio_url=audio_url,
                question_number=question_number,
                submission_url=submission_url
            )
            
            # Publish the result
            message_data = {
                "wav_path": result["wav_path"],
                "question_number": question_number,
                "submission_url": submission_url,
                "original_audio_url": audio_url
            }
            
            message_id = self.pubsub_client.publish_message(
                topic_id="AUDIO_CONVERSION_DONE",
                message=message_data
            )
            logger.info(f"Published audio conversion result for question {question_number} with message ID: {message_id}")
            
        except Exception as e:
            logger.error(f"Error processing audio for question {question_number}: {str(e)}")
            raise
        
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a student submission message and process all audio in parallel
        
        Args:
            message: The message data containing audio URLs and submission details
        """
        try:
            audio_urls = message.get("audio_urls", [])
            submission_url = message.get("submission_url")
            
            if not audio_urls or not submission_url:
                logger.error("Missing required fields in submission message")
                return
                
            # Create tasks for all questions
            tasks = []
            for question_number, audio_url in enumerate(audio_urls, 1):
                task = self.process_single_question(
                    audio_url=audio_url,
                    question_number=question_number,
                    submission_url=submission_url
                )
                tasks.append(task)
            
            # Process all questions in parallel
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error handling audio processing: {str(e)}")
            raise 