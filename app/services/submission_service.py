from typing import List
from app.models.submission_model import SubmissionRequest, SubmissionResponse
from app.pubsub.client import PubSubClient
import logging

logger = logging.getLogger(__name__)

class SubmissionService:
    def __init__(self):
        self.pubsub_client = PubSubClient()

    async def process_submission(self, request: SubmissionRequest) -> SubmissionResponse:
        """
        Process the submission by publishing the data to the student-submission-topic
        """
        try:
            # Publish the submission data to the student-submission-topic
            message_data = {
                "audio_urls": request.audio_urls,
                "submission_url": request.submission_url,
                "total_questions": len(request.audio_urls)
            }
            
            # Publish the message using the topic name
            message_id = self.pubsub_client.publish_message_by_name(
                topic_name="STUDENT_SUBMISSION",
                message=message_data
            )
            
            logger.info(f"Published submission to student-submission-topic with message ID: {message_id}")
            
            return SubmissionResponse(
                status="success",
                message="Submission received and published successfully"
            )
        except Exception as e:
            logger.error(f"Error processing submission: {str(e)}")
            return SubmissionResponse(
                status="error", 
                message=f"Failed to process submission: {str(e)}"
            ) 