import logging
from typing import Dict
from app.pubsub.client import PubSubClient
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage

logger = logging.getLogger(__name__)

class AnalysisCoordinatorService:
    def __init__(self):
        self.pubsub_client = PubSubClient()
        # State tracking for coordination
        self._coordination_state: Dict[str, Dict] = {}
    
    def _get_state_key(self, submission_url: str, question_number: int) -> str:
        """Generate a unique key for state tracking"""
        return f"coord:{submission_url}:{question_number}"
        
    def _get_or_create_state(self, submission_url: str, question_number: int, total_questions: int = None) -> Dict:
        """Get or create coordination state for a question"""
        key = self._get_state_key(submission_url, question_number)
        if key not in self._coordination_state:
            self._coordination_state[key] = {
                "audio_done": False,
                "transcript_done": False,
                "audio_data": None,
                "transcript_data": None,
                "total_questions": total_questions
            }
        return self._coordination_state[key]
        
    def _cleanup_state(self, submission_url: str, question_number: int):
        """Clean up coordination state after completion"""
        key = self._get_state_key(submission_url, question_number)
        if key in self._coordination_state:
            del self._coordination_state[key]
            
    async def handle_audio_done(self, message: AudioDoneMessage) -> None:
        """Handle audio conversion completion"""
        try:
            total_questions = getattr(message, 'total_questions', None)
            state = self._get_or_create_state(message.submission_url, message.question_number, total_questions)
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
            total_questions = getattr(message, 'total_questions', None)
            state = self._get_or_create_state(message.submission_url, message.question_number, total_questions)
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
            # Get session_id from audio data (if available)
            session_id = getattr(state["audio_data"], 'session_id', None)
            
            # Get message data with total_questions and session_id
            message_data = {
                "wav_path": state["audio_data"].wav_path,
                "transcript": state["transcript_data"].text,
                "question_number": question_number,
                "submission_url": submission_url,
                "audio_url": state["audio_data"].original_audio_url,
                "total_questions": state.get("total_questions", 1)
            }
            
            # Add session_id if available for file lifecycle management
            if session_id:
                message_data["session_id"] = session_id
                logger.info(f"Including session_id {session_id} in analysis ready message")
            
            # Publish to question analysis ready topic using topic name
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="QUESTION_ANALYSIS_READY",
                message=message_data
            )
            
            logger.info(f"Published analysis ready message for question {question_number} with ID: {message_id}")
            
            # Clean up state
            self._cleanup_state(submission_url, question_number)
            
        except Exception as e:
            logger.error(f"Error publishing analysis ready message: {str(e)}")
            raise 