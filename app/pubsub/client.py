from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPIError
import json
import logging
from typing import Any, Dict, Optional
from app.pubsub.core.config import GOOGLE_CLOUD_PROJECT
from app.pubsub.topics_subs import TOPICS, SUBSCRIPTIONS

logger = logging.getLogger(__name__)

class PubSubClient:
    """Singleton class for managing PubSub client instances."""
    
    _instance = None
    _publisher = None
    _subscriber = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PubSubClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the PubSub clients."""
        try:
            self._publisher = pubsub_v1.PublisherClient()
            self._subscriber = pubsub_v1.SubscriberClient()
            logger.info("PubSub clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PubSub clients: {str(e)}")
            raise
    
    @property
    def publisher(self):
        """Get the publisher client instance."""
        return self._publisher
    
    @property
    def subscriber(self):
        """Get the subscriber client instance."""
        return self._subscriber

    def get_topic_path(self, topic_id: str) -> str:
        """Get the full path for a topic.
        
        Args:
            topic_id: The ID of the topic
            
        Returns:
            The full topic path
        """
        return self.publisher.topic_path(GOOGLE_CLOUD_PROJECT, topic_id)
        
    def get_subscription_path(self, subscription_id: str) -> str:
        """Get the full path for a subscription.
        
        Args:
            subscription_id: The ID of the subscription
            
        Returns:
            The full subscription path
        """
        return self.subscriber.subscription_path(GOOGLE_CLOUD_PROJECT, subscription_id)

    def get_topic_path_by_name(self, topic_name: str) -> str:
        """Get the full path for a topic by its name in the TOPICS dictionary.
        
        Args:
            topic_name: The name of the topic as defined in TOPICS
            
        Returns:
            The full topic path
        """
        if topic_name not in TOPICS:
            raise ValueError(f"Unknown topic name: {topic_name}")
        return self.get_topic_path(TOPICS[topic_name])

    def get_subscription_path_by_name(self, subscription_name: str) -> str:
        """Get the full path for a subscription by its name in the SUBSCRIPTIONS dictionary.
        
        Args:
            subscription_name: The name of the subscription as defined in SUBSCRIPTIONS
            
        Returns:
            The full subscription path
        """
        if subscription_name not in SUBSCRIPTIONS:
            raise ValueError(f"Unknown subscription name: {subscription_name}")
        return self.get_subscription_path(SUBSCRIPTIONS[subscription_name])
    
    def publish_message(self, topic_id: str, message: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish a message to a topic.
        
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
    
    def pull_messages(self, subscription_id: str) -> list:
        """Pull messages from a subscription synchronously.
        
        Args:
            subscription_id: The ID of the subscription to pull from
            
        Returns:
            List of received messages
        """
        subscription_path = self.get_subscription_path(subscription_id)
        
        try:
            response = self.subscriber.pull(
                request={
                    "subscription": subscription_path,
                }
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
