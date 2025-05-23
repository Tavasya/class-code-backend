import logging
from typing import Dict, Optional
from app.pubsub.client import PubSubClient
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage, QuestionAnalysisReadyMessage

logger = logging.getLogger(__name__)

class AnalysisCoordinatorService:
    def __init__(self):
        self.pubsub_client = PubSubClient()
        # State map to track progress of each question
        self._state_map: Dict[str, Dict] = {}
        
    def _get_state_key(self, submission_url: str, question_number: int) -> str:
        """Generate a unique key for a question state"""
        return f"{submission_url}:{question_number}"
        
    def _get_or_create_state(self, submission_url: str, question_number: int) -> Dict:
        """Get or create state for a question"""
        key = self._get_state_key(submission_url, question_number)
        if key not in self._state_map:
            self._state_map[key] = {
                "audio_done": False,
                "transcript_done": False,
                "audio_data": None,
                "transcript_data": None
            }
        return self._state_map[key]
        
    def _cleanup_state(self, submission_url: str, question_number: int):
        """Clean up state after processing"""
        key = self._get_state_key(submission_url, question_number)
        if key in self._state_map:
            del self._state_map[key]
            
    async def handle_audio_done(self, message: AudioDoneMessage) -> None:
        """Handle audio conversion completion"""
        try:
            state = self._get_or_create_state(message.submission_url, message.question_number)
            state["audio_done"] = True
            state["audio_data"] = message
            
            # Check if we can proceed with analysis
            if state["transcript_done"]:
                await self._publish_analysis_ready(
                    submission_url=message.submission_url,
                    question_number=message.question_number,
                    state=state
                )
                
        except Exception as e:
            logger.error(f"Error handling audio done message: {str(e)}")
            raise
            
    async def handle_transcription_done(self, message: TranscriptionDoneMessage) -> None:
        """Handle transcription completion"""
        try:
            state = self._get_or_create_state(message.submission_url, message.question_number)
            state["transcript_done"] = True
            state["transcript_data"] = message
            
            # Check if we can proceed with analysis
            if state["audio_done"]:
                await self._publish_analysis_ready(
                    submission_url=message.submission_url,
                    question_number=message.question_number,
                    state=state
                )
                
        except Exception as e:
            logger.error(f"Error handling transcription done message: {str(e)}")
            raise
            
    async def _publish_analysis_ready(
        self,
        submission_url: str,
        question_number: int,
        state: Dict
    ) -> None:
        """Publish message when both audio and transcript are ready"""
        try:
            analysis_message = QuestionAnalysisReadyMessage(
                wav_path=state["audio_data"].wav_path,
                transcript=state["transcript_data"].text,
                question_number=question_number,
                submission_url=submission_url,
                audio_url=state["audio_data"].original_audio_url
            )
            
            # Publish to question analysis ready topic using topic name
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="QUESTION_ANALYSIS_READY",
                message=analysis_message.dict()
            )
            
            logger.info(f"Published analysis ready message for question {question_number} with ID: {message_id}")
            
            # Clean up state
            self._cleanup_state(submission_url, question_number)
            
        except Exception as e:
            logger.error(f"Error publishing analysis ready message: {str(e)}")
            raise 