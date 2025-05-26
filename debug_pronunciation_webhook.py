#!/usr/bin/env python3
"""
Debug script for pronunciation webhook issue
Tests the specific pronunciation done webhook that's causing the list/dict error
"""

import requests
import json
import base64
import time
import sys
import os

# Add the project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration
BASE_URL = "http://127.0.0.1:8000"

def create_pubsub_message(data):
    """Create a simulated Pub/Sub push message format"""
    message_json = json.dumps(data)
    encoded_data = base64.b64encode(message_json.encode('utf-8')).decode('utf-8')
    
    return {
        "message": {
            "data": encoded_data,
            "messageId": f"debug-message-{int(time.time())}",
            "publishTime": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "attributes": {}
        }
    }

def test_pronunciation_webhook_with_dict():
    """Test pronunciation webhook with correct dict format"""
    print("🧪 Testing pronunciation webhook with DICT (expected format)...")
    
    # This is the expected format from pronunciation service
    pronunciation_result_dict = {
        "status": "success",
        "overall_pronunciation_score": 85,
        "accuracy_score": 82,
        "fluency_score": 88,
        "word_details": [
            {"word": "hello", "accuracy_score": 85, "offset": 0.1, "duration": 0.5},
            {"word": "world", "accuracy_score": 90, "offset": 0.6, "duration": 0.4}
        ],
        "critical_errors": [],
        "filler_words": []
    }
    
    message_data = {
        "question_number": 1,
        "submission_url": "debug_test_dict",
        "result": pronunciation_result_dict,
        "transcript": "hello world",
        "total_questions": 1,
        "wav_path": "/tmp/test.wav",
        "audio_url": "test_url",
        "session_id": "test_session"
    }
    
    try:
        pubsub_message = create_pubsub_message(message_data)
        response = requests.post(
            f"{BASE_URL}/api/v1/webhooks/pronunciation-done",
            json=pubsub_message,
            timeout=30
        )
        
        print(f"✅ Dict test response: {response.status_code}")
        if response.status_code == 200:
            print(f"   📝 Success: {response.json()}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Dict test failed: {str(e)}")

def test_pronunciation_webhook_with_list():
    """Test pronunciation webhook with problematic list format"""
    print("\n🧪 Testing pronunciation webhook with LIST (problematic format)...")
    
    # This might be what's actually being sent (causing the error)
    pronunciation_result_list = [
        {"word": "hello", "accuracy_score": 85, "offset": 0.1, "duration": 0.5},
        {"word": "world", "accuracy_score": 90, "offset": 0.6, "duration": 0.4}
    ]
    
    message_data = {
        "question_number": 1,
        "submission_url": "debug_test_list",
        "result": pronunciation_result_list,
        "transcript": "hello world",
        "total_questions": 1,
        "wav_path": "/tmp/test.wav",
        "audio_url": "test_url",
        "session_id": "test_session"
    }
    
    try:
        pubsub_message = create_pubsub_message(message_data)
        response = requests.post(
            f"{BASE_URL}/api/v1/webhooks/pronunciation-done",
            json=pubsub_message,
            timeout=30
        )
        
        print(f"✅ List test response: {response.status_code}")
        if response.status_code == 200:
            print(f"   📝 Success: {response.json()}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ List test failed: {str(e)}")

def test_pronunciation_webhook_with_error():
    """Test pronunciation webhook with error format"""
    print("\n🧪 Testing pronunciation webhook with ERROR format...")
    
    # This is what happens when pronunciation service fails
    pronunciation_result_error = {
        "status": "error",
        "error": "Failed to analyze pronunciation",
        "transcript": "hello world"
    }
    
    message_data = {
        "question_number": 1,
        "submission_url": "debug_test_error",
        "result": pronunciation_result_error,
        "transcript": "hello world",
        "total_questions": 1,
        "wav_path": "/tmp/test.wav",
        "audio_url": "test_url",
        "session_id": "test_session"
    }
    
    try:
        pubsub_message = create_pubsub_message(message_data)
        response = requests.post(
            f"{BASE_URL}/api/v1/webhooks/pronunciation-done",
            json=pubsub_message,
            timeout=30
        )
        
        print(f"✅ Error test response: {response.status_code}")
        if response.status_code == 200:
            print(f"   📝 Success: {response.json()}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error test failed: {str(e)}")

def check_server_health():
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server responded with {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not reachable: {str(e)}")
        return False

def main():
    print("🔧 PRONUNCIATION WEBHOOK DEBUGGER")
    print("=" * 50)
    
    # Check server health first
    if not check_server_health():
        print("\n💡 Make sure your FastAPI server is running:")
        print("   uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    
    print("\n🧪 Running pronunciation webhook tests...")
    
    # Test different scenarios
    test_pronunciation_webhook_with_dict()
    test_pronunciation_webhook_with_list()
    test_pronunciation_webhook_with_error()
    
    print("\n" + "=" * 50)
    print("🎯 Check your server logs to see the DEBUG output!")
    print("   Look for lines starting with 'DEBUG: pronunciation_result'")
    print("=" * 50)

if __name__ == "__main__":
    main() 