import logging
from typing import Dict, Optional
from app.pubsub.client import PubSubClient
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class AnalysisCoordinatorService:
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.db_service = DatabaseService()
        # NOTE: We now use database for coordination state instead of in-memory
        # This allows multiple Cloud Run instances to share state

    async def handle_audio_done(self, message: AudioDoneMessage) -> None:
        """Handle audio conversion completion"""
        try:
            total_questions = getattr(message, 'total_questions', None)

            # Convert message to dict for storage
            audio_data = {
                "wav_path": message.wav_path,
                "original_audio_url": message.original_audio_url,
                "question_number": message.question_number,
                "submission_url": message.submission_url,
                "session_id": getattr(message, 'session_id', None)
            }

            # Update coordination state in database
            state = self.db_service.update_coordination_state(
                submission_url=message.submission_url,
                question_number=message.question_number,
                audio_done=True,
                audio_data=audio_data,
                total_questions=total_questions
            )

            if not state:
                logger.error(f"Failed to update coordination state for audio done: {message.submission_url} Q{message.question_number}")
                return

            logger.info(f"📥 Audio done for {message.submission_url} Q{message.question_number}, transcript_done={state.get('transcript_done')}")

            # Check if we can proceed with analysis
            if state.get("transcript_done"):
                await self._publish_analysis_ready(
                    submission_url=message.submission_url,
                    question_number=message.question_number,
                    state=state,
                    total_questions=total_questions
                )

        except Exception as e:
            logger.error(f"Error handling audio done message: {str(e)}")
            raise

    async def handle_transcription_done(self, message: TranscriptionDoneMessage) -> None:
        """Handle transcription completion"""
        try:
            total_questions = getattr(message, 'total_questions', None)

            # Convert message to dict for storage
            transcript_data = {
                "text": message.text,
                "question_number": message.question_number,
                "submission_url": message.submission_url
            }

            # Update coordination state in database
            state = self.db_service.update_coordination_state(
                submission_url=message.submission_url,
                question_number=message.question_number,
                transcript_done=True,
                transcript_data=transcript_data,
                total_questions=total_questions
            )

            if not state:
                logger.error(f"Failed to update coordination state for transcription done: {message.submission_url} Q{message.question_number}")
                return

            logger.info(f"📥 Transcription done for {message.submission_url} Q{message.question_number}, audio_done={state.get('audio_done')}")

            # Check if we can proceed with analysis
            if state.get("audio_done"):
                await self._publish_analysis_ready(
                    submission_url=message.submission_url,
                    question_number=message.question_number,
                    state=state,
                    total_questions=total_questions
                )

        except Exception as e:
            logger.error(f"Error handling transcription done message: {str(e)}")
            raise
            
    async def _publish_analysis_ready(
        self,
        submission_url: str,
        question_number: int,
        state: Dict,
        total_questions: Optional[int] = None
    ) -> None:
        """Publish message when both audio and transcript are ready"""
        try:
            # Get data from stored dicts (not objects, since we store in DB as dicts)
            audio_data = state.get("audio_data", {})
            transcript_data = state.get("transcript_data", {})

            # Get session_id from audio data (if available)
            session_id = audio_data.get('session_id') if isinstance(audio_data, dict) else None

            # Get message data with total_questions and session_id
            message_data = {
                "wav_path": audio_data.get("wav_path") if isinstance(audio_data, dict) else getattr(audio_data, 'wav_path', ''),
                "transcript": transcript_data.get("text") if isinstance(transcript_data, dict) else getattr(transcript_data, 'text', ''),
                "question_number": question_number,
                "submission_url": submission_url,
                "audio_url": audio_data.get("original_audio_url") if isinstance(audio_data, dict) else getattr(audio_data, 'original_audio_url', ''),
                "total_questions": total_questions
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

            logger.info(f"🚀 Published QUESTION_ANALYSIS_READY for {submission_url} Q{question_number} with ID: {message_id}")

            # Clean up coordination state in database
            self.db_service.cleanup_coordination_state(submission_url, question_number)

        except Exception as e:
            logger.error(f"Error publishing analysis ready message: {str(e)}")
            raise