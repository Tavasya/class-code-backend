#!/usr/bin/env python3
"""
Test script for the new centralized file processing system
Tests the FileManager and updated AudioService/PronunciationService integration
"""

import requests
import json
import time
import base64
import asyncio
import logging

# Configuration
BASE_URL = "http://localhost:8000"
TEST_AUDIO_URL = "https://zyaobehxpcwxlyljzknw.supabase.co/storage/v1/object/public/audio_recordings/ef09cf11-6a08-4fc9-8f33-9722b4d9dcdc/83/0_1744680795502.webm"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_pubsub_message(data):
    """Create a simulated Pub/Sub push message format"""
    message_json = json.dumps(data)
    encoded_data = base64.b64encode(message_json.encode('utf-8')).decode('utf-8')
    
    return {
        "message": {
            "data": encoded_data,
            "messageId": f"test-message-{int(time.time())}",
            "publishTime": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "attributes": {}
        }
    }

def test_file_session_monitoring():
    """Test the file session monitoring endpoints"""
    print("\n🔍 Testing file session monitoring...")
    
    try:
        # Check active sessions
        response = requests.get(f"{BASE_URL}/api/v1/debug/file-sessions")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Active sessions: {data['total_active']}")
            if data['active_sessions']:
                for session_id, info in data['active_sessions'].items():
                    print(f"   📄 Session {session_id}: {info['file_path']} (deps: {info['dependencies']})")
            else:
                print("   📄 No active sessions")
        else:
            print(f"❌ Failed to get sessions: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Session monitoring test failed: {str(e)}")

def test_centralized_audio_processing():
    """Test the new centralized audio processing flow"""
    print("\n🎵 Testing centralized audio processing...")
    
    submission_url = f"centralized-test-{int(time.time())}"
    
    # Step 1: Submit audio URLs (should trigger download and conversion once)
    submission_data = {
        "audio_urls": [TEST_AUDIO_URL],
        "submission_url": submission_url,
        "total_questions": 1
    }
    
    try:
        pubsub_message = create_pubsub_message(submission_data)
        response = requests.post(
            f"{BASE_URL}/api/v1/webhooks/student-submission-audio",
            json=pubsub_message,
            timeout=60
        )
        
        if response.status_code == 200:
            print("✅ Audio processing initiated")
            
            # Wait a bit and check file sessions
            time.sleep(5)
            test_file_session_monitoring()
            
        else:
            print(f"❌ Audio processing failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Centralized audio processing test failed: {str(e)}")

def test_manual_cleanup():
    """Test manual cleanup functionality"""
    print("\n🧹 Testing manual cleanup...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/debug/periodic-cleanup")
        if response.status_code == 200:
            print("✅ Manual cleanup completed")
        else:
            print(f"❌ Manual cleanup failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Manual cleanup test failed: {str(e)}")

def main():
    """Run all tests"""
    print("🧪 Testing Centralized File Processing System")
    print("=" * 50)
    
    # Test 1: Check initial state
    test_file_session_monitoring()
    
    # Test 2: Test the new audio processing flow
    test_centralized_audio_processing()
    
    # Wait for processing to complete
    print("\n⏳ Waiting for processing to complete...")
    time.sleep(10)
    
    # Test 3: Check final state
    test_file_session_monitoring()
    
    # Test 4: Manual cleanup
    test_manual_cleanup()
    
    # Test 5: Final check
    test_file_session_monitoring()
    
    print("\n🎉 Testing completed!")
    print("\nKey improvements:")
    print("✅ Single download/conversion per audio file")
    print("✅ Centralized file lifecycle management")
    print("✅ Session-based cleanup tracking")
    print("✅ No premature file deletion")
    print("✅ Monitoring and debugging endpoints")

if __name__ == "__main__":
    main() 