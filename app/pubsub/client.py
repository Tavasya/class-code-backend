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
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PubSubClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the PubSub clients."""
        try:
            self._publisher = pubsub_v1.PublisherClient()
            logger.info("PubSub publisher client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PubSub publisher client: {str(e)}")
            raise
    
    @property
    def publisher(self):
        """Get the publisher client instance."""
        return self._publisher

    def get_topic_path(self, topic_id: str) -> str:
        """Get the full path for a topic.
        
        Args:
            topic_id: The ID of the topic
            
        Returns:
            The full topic path
        """
        return self.publisher.topic_path(GOOGLE_CLOUD_PROJECT, topic_id)

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
            logger.info(f"Message published with ID: {message_id} to topic: {topic_path}")
            return message_id
        except GoogleAPIError as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise

    def publish_message_by_name(self, topic_name: str, message: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish a message to a topic by its name in the TOPICS dictionary.
        
        Args:
            topic_name: The name of the topic as defined in TOPICS
            message: The message data to publish
            attributes: Optional attributes to attach to the message
            
        Returns:
            The published message ID
        """
        if topic_name not in TOPICS:
            raise ValueError(f"Unknown topic name: {topic_name}")
        
        return self.publish_message(TOPICS[topic_name], message, attributes)
