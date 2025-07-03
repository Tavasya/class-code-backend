#!/usr/bin/env python3
"""
Subscriber service that pulls messages from Pub/Sub emulator and calls webhook endpoints.
This simulates exactly how Google Cloud Pub/Sub push subscriptions work in production.
"""
import os
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import SubscriberClient
import aiohttp
from app.pubsub.topics_subs import SUBSCRIPTIONS

# Set emulator host
os.environ['PUBSUB_EMULATOR_HOST'] = '127.0.0.1:8085'

PROJECT_ID = "demo-project"
WEBHOOK_BASE_URL = "http://localhost:8080/api/v1/webhooks"

# Map subscriptions to webhook endpoints
SUBSCRIPTION_TO_ENDPOINT = {
    "student-submission-topic-sub": "/student-submission",
    "audio-conversion-service-sub": "/audio-conversion-done", 
    "transcription-service-sub": "/transcription-done",
    "question-analysis-ready-topic-sub": "/question-analysis-ready",
    "fluency-done-topic-sub": "/fluency-done",
    "grammer-done-topic-sub": "/grammar-done",
    "lexical-done-topic-sub": "/lexical-done",
    "pronoun-done-topic-sub": "/pronunciation-done",
    "analysis-complete-topic-sub": "/analysis-complete",
    "submission-analyis-complete-topic-sub": "/submission-analyis-complete",
    "vocabulary-done-topic-sub": "/vocabulary-done"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubscriberService:
    def __init__(self):
        self.subscriber = SubscriberClient()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.session = None
        self.loop = None
        
    async def start(self):
        """Start all subscribers"""
        logger.info("Starting subscriber service...")
        
        # Store event loop reference
        self.loop = asyncio.get_event_loop()
        
        # Create HTTP session
        self.session = aiohttp.ClientSession()
        
        # Start subscribers for each subscription
        tasks = []
        for sub_name, sub_id in SUBSCRIPTIONS.items():
            if sub_id in SUBSCRIPTION_TO_ENDPOINT:
                task = asyncio.create_task(self._subscribe_to_topic(sub_id))
                tasks.append(task)
        
        # Wait for all subscribers
        await asyncio.gather(*tasks)
    
    async def _subscribe_to_topic(self, subscription_id: str):
        """Subscribe to a specific topic and process messages"""
        subscription_path = self.subscriber.subscription_path(PROJECT_ID, subscription_id)
        endpoint = SUBSCRIPTION_TO_ENDPOINT[subscription_id]
        
        logger.info(f"Starting subscriber for {subscription_id} -> {endpoint}")
        
        def callback(message):
            """Callback for processing messages"""
            try:
                # Decode message
                message_data = json.loads(message.data.decode('utf-8'))
                
                # Create webhook payload (simulating Google Cloud Pub/Sub format)
                import base64
                # Google Cloud Pub/Sub sends data as base64 encoded
                encoded_data = base64.b64encode(message.data).decode('utf-8')
                
                webhook_payload = {
                    "subscription": subscription_path,
                    "message": {
                        "data": encoded_data,
                        "messageId": message.message_id,
                        "publishTime": message.publish_time.isoformat() if message.publish_time else None,
                        "attributes": dict(message.attributes) if message.attributes else {}
                    }
                }
                
                # Schedule webhook call in the main event loop
                asyncio.run_coroutine_threadsafe(
                    self._call_webhook(endpoint, webhook_payload),
                    self.loop
                )
                
                # Acknowledge message
                message.ack()
                
            except Exception as e:
                logger.error(f"Error processing message from {subscription_id}: {e}")
                message.nack()
        
        # Start pull subscription in thread
        def run_subscriber():
            try:
                logger.info(f"Listening on {subscription_path}")
                flow_control = pubsub_v1.types.FlowControl(max_messages=100)
                streaming_pull_future = self.subscriber.subscribe(
                    subscription_path, 
                    callback=callback,
                    flow_control=flow_control
                )
                
                # Keep the subscriber running
                try:
                    streaming_pull_future.result()
                except KeyboardInterrupt:
                    streaming_pull_future.cancel()
                    logger.info(f"Subscriber for {subscription_id} stopped")
                    
            except Exception as e:
                logger.error(f"Error in subscriber for {subscription_id}: {e}")
        
        # Run subscriber in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, run_subscriber)
    
    async def _call_webhook(self, endpoint: str, payload: dict):
        """Call webhook endpoint with message payload"""
        url = f"{WEBHOOK_BASE_URL}{endpoint}"
        
        try:
            async with self.session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully called webhook {endpoint}")
                else:
                    logger.error(f"Webhook {endpoint} returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Error calling webhook {endpoint}: {e}")
    
    async def stop(self):
        """Stop the subscriber service"""
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)

async def main():
    service = SubscriberService()
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Stopping subscriber service...")
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())