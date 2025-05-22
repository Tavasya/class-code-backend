from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPIError
import json
import logging
from typing import Any, Dict, Callable, Optional
from concurrent.futures import TimeoutError

logger = logging.getLogger(__name__)

class PubSubService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        
    def get_topic_path(self, topic_id: str) -> str:
        """Get the full path for a topic."""
        return self.publisher.topic_path(self.project_id, topic_id)
        
    def get_subscription_path(self, subscription_id: str) -> str:
        """Get the full path for a subscription."""
        return self.subscriber.subscription_path(self.project_id, subscription_id)

    def publish_message(self, topic_id: str, message: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish a message to an existing topic.
        
        Args:
            topic_id: The ID of the topic to publish to
            message: The message data to publish
            attributes: Optional attributes to attach to the message
            
        Returns:
            The published message ID
        """
        topic_path = self.get_topic_path(topic_id)
        
        try:
            message_json = json.dumps(message).encode("utf-8")
            future = self.publisher.publish(
                topic_path, 
                message_json,
                **attributes if attributes else {}
            )
            message_id = future.result()
            logger.info(f"Message published with ID: {message_id}")
            return message_id
        except GoogleAPIError as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise

    def subscribe(self, subscription_id: str, callback: Callable, timeout: Optional[float] = None) -> None:
        """Subscribe to messages from an existing subscription.
        
        Args:
            subscription_id: The ID of the subscription to listen to
            callback: The callback function to process messages
            timeout: Optional timeout in seconds for the subscription
        """
        subscription_path = self.get_subscription_path(subscription_id)
        
        try:
            streaming_pull_future = self.subscriber.subscribe(
                subscription_path, 
                callback=callback
            )
            logger.info(f"Listening for messages on {subscription_path}")
            
            if timeout:
                try:
                    streaming_pull_future.result(timeout=timeout)
                except TimeoutError:
                    streaming_pull_future.cancel()
                    logger.info(f"Subscription timed out after {timeout} seconds")
            else:
                streaming_pull_future.result()
                
        except GoogleAPIError as e:
            logger.error(f"Failed to subscribe: {str(e)}")
            raise

    def pull_messages(self, subscription_id: str, max_messages: int = 1, timeout: float = 5.0) -> list:
        """Pull messages from a subscription synchronously.
        
        Args:
            subscription_id: The ID of the subscription to pull from
            max_messages: Maximum number of messages to pull
            timeout: Timeout in seconds for the pull operation
            
        Returns:
            List of received messages
        """
        subscription_path = self.get_subscription_path(subscription_id)
        
        try:
            response = self.subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": max_messages,
                },
                timeout=timeout
            )
            
            messages = []
            for received_message in response.received_messages:
                try:
                    message_data = json.loads(received_message.message.data.decode("utf-8"))
                    messages.append({
                        "data": message_data,
                        "attributes": received_message.message.attributes,
                        "message_id": received_message.message.message_id
                    })
                    # Acknowledge the message
                    self.subscriber.acknowledge(
                        request={
                            "subscription": subscription_path,
                            "ack_ids": [received_message.ack_id],
                        }
                    )
                except json.JSONDecodeError:
                    logger.error("Failed to decode message data as JSON")
                    continue
                    
            return messages
            
        except GoogleAPIError as e:
            logger.error(f"Failed to pull messages: {str(e)}")
            raise 