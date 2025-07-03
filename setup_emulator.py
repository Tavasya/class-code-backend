#!/usr/bin/env python3
"""
Setup script to create all topics and subscriptions for the Pub/Sub emulator.
Run this after starting the emulator.
"""
import os
from google.cloud import pubsub_v1
from app.pubsub.topics_subs import TOPICS, SUBSCRIPTIONS

# Set emulator host
os.environ['PUBSUB_EMULATOR_HOST'] = '127.0.0.1:8085'

PROJECT_ID = "demo-project"

def create_topics_and_subscriptions():
    """Create all topics and subscriptions in the emulator."""
    
    # Initialize clients
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    
    print("Creating topics...")
    for topic_name, topic_id in TOPICS.items():
        topic_path = publisher.topic_path(PROJECT_ID, topic_id)
        try:
            publisher.create_topic(request={"name": topic_path})
            print(f"✓ Created topic: {topic_id}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"- Topic already exists: {topic_id}")
            else:
                print(f"✗ Failed to create topic {topic_id}: {e}")
    
    print("\nCreating subscriptions...")
    for sub_name, sub_id in SUBSCRIPTIONS.items():
        if sub_name in TOPICS:
            topic_id = TOPICS[sub_name]
            topic_path = publisher.topic_path(PROJECT_ID, topic_id)
            subscription_path = subscriber.subscription_path(PROJECT_ID, sub_id)
            
            try:
                subscriber.create_subscription(
                    request={"name": subscription_path, "topic": topic_path}
                )
                print(f"✓ Created subscription: {sub_id}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"- Subscription already exists: {sub_id}")
                else:
                    print(f"✗ Failed to create subscription {sub_id}: {e}")
    
    print("\nSetup complete!")

if __name__ == "__main__":
    create_topics_and_subscriptions()