import logging
import uuid
from typing import Dict, Any, Optional
from app.pubsub.client import PubSubClient
from app.pubsub.topics_subs import TOPICS

logger = logging.getLogger(__name__)

class PracticeWebhookService:
    """Service for managing webhook sessions during practice pronunciation flow"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        logger.info("PracticeWebhookService initialized")
    
    def start_practice_webhook_session(self, session_id: str, transcript: str) -> Optional[str]:
        """
        Start a practice webhook session for pronunciation analysis
        
        Args:
            session_id: Practice session ID  
            transcript: The transcript text for context
            
        Returns:
            Webhook session ID if successful, None if failed
        """
        try:
            # Generate unique webhook session ID
            webhook_session_id = str(uuid.uuid4())
            
            logger.info(f"🎯 Starting practice webhook session for practice session: {session_id}")
            logger.info(f"📝 Webhook session ID: {webhook_session_id}")
            
            # Prepare message for practice pronunciation request topic
            practice_webhook_message = {
                "action": "start_practice_session",
                "practice_session_id": session_id,
                "webhook_session_id": webhook_session_id,
                "transcript": transcript,
                "callback_url": f"/api/v1/webhooks/practice-pronunciation-done",
                "analysis_type": "practice_session",
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish to practice pronunciation request topic
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="PRACTICE_PRONUNCIATION_REQUEST",
                message=practice_webhook_message,
                attributes={
                    "action": "start_practice_session",
                    "practice_session_id": session_id,
                    "webhook_session_id": webhook_session_id
                }
            )
            
            logger.info(f"✅ Practice webhook session started successfully")
            logger.info(f"📨 Published message ID: {message_id}")
            logger.info(f"🎯 Webhook session ID: {webhook_session_id}")
            
            return webhook_session_id
            
        except Exception as e:
            logger.error(f"❌ Error starting practice webhook session for {session_id}: {str(e)}")
            return None
    
    def stop_practice_webhook_session(self, session_id: str, webhook_session_id: str) -> bool:
        """
        Stop a webhook session for practice pronunciation analysis
        
        Args:
            session_id: Practice session ID
            webhook_session_id: Webhook session ID to stop
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🛑 Stopping practice webhook session for practice session: {session_id}")
            logger.info(f"📝 Webhook session ID: {webhook_session_id}")
            
            # Prepare message for stopping practice webhook session
            stop_webhook_message = {
                "action": "stop_practice_session",
                "practice_session_id": session_id,
                "webhook_session_id": webhook_session_id,
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish to practice pronunciation request topic
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="PRACTICE_PRONUNCIATION_REQUEST",
                message=stop_webhook_message,
                attributes={
                    "action": "stop_practice_session",
                    "practice_session_id": session_id,
                    "webhook_session_id": webhook_session_id
                }
            )
            
            logger.info(f"✅ Practice webhook session stopped successfully")
            logger.info(f"📨 Published stop message ID: {message_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping practice webhook session {webhook_session_id}: {str(e)}")
            return False
    
    def submit_sentence_for_analysis(self, 
                                   session_id: str, 
                                   webhook_session_id: str,
                                   sentence_index: int,
                                   sentence_text: str, 
                                   audio_url: str) -> bool:
        """
        Submit a sentence recording for pronunciation analysis
        
        Args:
            session_id: Practice session ID
            webhook_session_id: Active webhook session ID
            sentence_index: Index of the sentence being practiced
            sentence_text: Expected sentence text
            audio_url: URL to the recorded audio
            
        Returns:
            True if submitted successfully, False otherwise
        """
        try:
            logger.info(f"🎤 Submitting sentence for analysis - Session: {session_id}")
            logger.info(f"📝 Sentence {sentence_index}: {sentence_text}")
            logger.info(f"🔊 Audio URL: {audio_url}")
            
            # Prepare message for sentence analysis
            sentence_analysis_message = {
                "action": "analyze_sentence",
                "practice_session_id": session_id,
                "webhook_session_id": webhook_session_id,
                "analysis_type": "sentence",
                "sentence_index": sentence_index,
                "expected_text": sentence_text,
                "audio_url": audio_url,
                "callback_url": f"/api/v1/webhooks/practice-pronunciation-done",
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish to practice pronunciation request topic
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="PRACTICE_PRONUNCIATION_REQUEST",
                message=sentence_analysis_message,
                attributes={
                    "action": "analyze_sentence",
                    "practice_session_id": session_id,
                    "webhook_session_id": webhook_session_id,
                    "analysis_type": "sentence"
                }
            )
            
            logger.info(f"✅ Sentence submitted for analysis successfully")
            logger.info(f"📨 Published message ID: {message_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error submitting sentence for analysis: {str(e)}")
            return False
    
    def submit_word_for_analysis(self, 
                               session_id: str, 
                               webhook_session_id: str,
                               word: str,
                               sentence_context: str,
                               audio_url: str) -> bool:
        """
        Submit a word recording for pronunciation analysis
        
        Args:
            session_id: Practice session ID
            webhook_session_id: Active webhook session ID
            word: Word being practiced
            sentence_context: Full sentence context for the word
            audio_url: URL to the recorded audio
            
        Returns:
            True if submitted successfully, False otherwise
        """
        try:
            logger.info(f"🎤 Submitting word for analysis - Session: {session_id}")
            logger.info(f"📝 Word: {word}")
            logger.info(f"📄 Context: {sentence_context}")
            logger.info(f"🔊 Audio URL: {audio_url}")
            
            # Prepare message for word analysis
            word_analysis_message = {
                "action": "analyze_word",
                "practice_session_id": session_id,
                "webhook_session_id": webhook_session_id,
                "analysis_type": "word",
                "expected_text": word,
                "word_context": sentence_context,
                "audio_url": audio_url,
                "callback_url": f"/api/v1/webhooks/practice-pronunciation-done",
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish to practice pronunciation request topic
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="PRACTICE_PRONUNCIATION_REQUEST",
                message=word_analysis_message,
                attributes={
                    "action": "analyze_word",
                    "practice_session_id": session_id,
                    "webhook_session_id": webhook_session_id,
                    "analysis_type": "word"
                }
            )
            
            logger.info(f"✅ Word submitted for analysis successfully")
            logger.info(f"📨 Published message ID: {message_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error submitting word for analysis: {str(e)}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_webhook_session_status(self, webhook_session_id: str) -> Dict[str, Any]:
        """
        Get status information for a webhook session
        
        Args:
            webhook_session_id: Webhook session ID
            
        Returns:
            Status information dictionary
        """
        # This would typically query the webhook service status
        # For now, return basic information
        return {
            "webhook_session_id": webhook_session_id,
            "status": "active",
            "created_at": self._get_current_timestamp()
        }