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
                "submission_url": request.submission_url
            }
            
            # Get the topic path using the topic name
            topic_path = self.pubsub_client.get_topic_path_by_name("STUDENT_SUBMISSION")
            
            # Publish the message
            message_id = self.pubsub_client.publish_message(
                topic_id=topic_path,
                message=message_data
            )
            
            logger.info(f"Published submission to topic with message ID: {message_id}")
            
            return SubmissionResponse(
                status="success",
                message="Submission received and published successfully"
            )
        except Exception as e:
            logger.error(f"Error processing submission: {str(e)}")
            return SubmissionResponse(
                status="error",
                message=f"Error processing submission: {str(e)}"
            ) 