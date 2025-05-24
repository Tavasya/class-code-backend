#!/usr/bin/env python3
"""
Production debugging script for pub/sub flow
This helps diagnose what's wrong with the production setup
"""

import requests
import json
import time
import sys
import base64

# Configuration - Update this to your production URL
PROD_URL = "https://classconnect-staging-107872842385.us-west2.run.app"

def test_endpoint_accessibility():
    """Test if all webhook endpoints are accessible"""
    print("🔍 Testing webhook endpoint accessibility...")
    
    endpoints = [
        "/api/v1/health",
        "/api/v1/webhooks/student-submission-audio",
        "/api/v1/webhooks/student-submission-transcription", 
        "/api/v1/webhooks/audio-conversion-done",
        "/api/v1/webhooks/transcription-done",
        "/api/v1/webhooks/question-analysis-ready",
        "/api/v1/webhooks/grammar-done",
        "/api/v1/webhooks/lexical-done", 
        "/api/v1/webhooks/pronunciation-done",
        "/api/v1/webhooks/fluency-done",
        "/api/v1/webhooks/analysis-complete",
        "/api/v1/results/submissions"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{PROD_URL}{endpoint}", timeout=10)
            status = response.status_code
            results[endpoint] = {
                "status": status,
                "accessible": status in [200, 405, 422],  # 405=Method Not Allowed is OK for POST endpoints
                "response": response.text[:100] if len(response.text) < 100 else response.text[:100] + "..."
            }
            
            icon = "✅" if results[endpoint]["accessible"] else "❌"
            print(f"{icon} {endpoint}: {status}")
            
        except Exception as e:
            results[endpoint] = {
                "status": "ERROR", 
                "accessible": False,
                "error": str(e)
            }
            print(f"❌ {endpoint}: ERROR - {str(e)}")
    
    return results

def test_submission_endpoint():
    """Test the submission endpoint specifically"""
    print("\n📤 Testing submission endpoint...")
    
    test_data = {
        "audio_urls": ["https://example.com/test.mp3"],
        "submission_url": f"debug-test-{int(time.time())}"
    }
    
    try:
        response = requests.post(
            f"{PROD_URL}/api/v1/submission/submit",
            json=test_data,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Submission endpoint working")
            return test_data["submission_url"]
        else:
            print("❌ Submission endpoint failed")
            return None
            
    except Exception as e:
        print(f"❌ Submission test failed: {str(e)}")
        return None

def check_google_cloud_setup():
    """Provide guidance on Google Cloud setup"""
    print("\n☁️ GOOGLE CLOUD PUB/SUB SETUP REQUIRED")
    print("=" * 60)
    print("Your production environment needs these Pub/Sub subscriptions:")
    print()
    
    required_subscriptions = [
        ("student-submission-topic-audio-sub", "student-submission-topic", "/api/v1/webhooks/student-submission-audio"),
        ("student-submission-topic-transcription-sub", "student-submission-topic", "/api/v1/webhooks/student-submission-transcription"),
        ("audio-conversion-service-sub", "audio-conversion-done-topic", "/api/v1/webhooks/audio-conversion-done"),
        ("transcription-service-sub", "transcription-done-topic", "/api/v1/webhooks/transcription-done"),
        ("question-analysis-ready-topic-sub", "question-analysis-ready-topic", "/api/v1/webhooks/question-analysis-ready"),
        ("grammar-done-topic-sub", "grammer-done-topic", "/api/v1/webhooks/grammar-done"),
        ("lexical-done-topic-sub", "lexical-done-topic", "/api/v1/webhooks/lexical-done"),
        ("pronunciation-done-topic-sub", "pronoun-done-topic", "/api/v1/webhooks/pronunciation-done"),
        ("fluency-done-topic-sub", "fluency-done-topic", "/api/v1/webhooks/fluency-done"),
        ("analysis-complete-topic-sub", "analysis-complete-topic", "/api/v1/webhooks/analysis-complete"),
    ]
    
    print("📋 Required gcloud commands:")
    print("-" * 40)
    
    for sub_name, topic_name, endpoint in required_subscriptions:
        full_endpoint = f"{PROD_URL}{endpoint}"
        print(f"gcloud pubsub subscriptions create {sub_name} \\")
        print(f"  --topic={topic_name} \\")
        print(f"  --push-endpoint={full_endpoint}")
        print()

def test_webhook_directly():
    """Test calling a webhook directly to see if it works"""
    print("\n🔧 Testing webhook directly...")
    
    # Create a mock Pub/Sub message
    test_data = {
        "audio_urls": ["https://example.com/test.mp3"],
        "submission_url": f"webhook-test-{int(time.time())}",
        "total_questions": 1
    }
    
    message_json = json.dumps(test_data)
    encoded_data = base64.b64encode(message_json.encode('utf-8')).decode('utf-8')
    
    pubsub_message = {
        "message": {
            "data": encoded_data,
            "messageId": f"test-{int(time.time())}",
            "publishTime": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "attributes": {}
        }
    }
    
    try:
        response = requests.post(
            f"{PROD_URL}/api/v1/webhooks/student-submission-audio",
            json=pubsub_message,
            timeout=30
        )
        
        print(f"Webhook test: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Webhook processing works")
        else:
            print("❌ Webhook processing failed")
            
    except Exception as e:
        print(f"❌ Webhook test failed: {str(e)}")

def check_environment_variables():
    """Check if required environment variables are likely set"""
    print("\n🔧 REQUIRED ENVIRONMENT VARIABLES")
    print("=" * 50)
    print("Make sure these are set in your production environment:")
    print()
    print("✅ GOOGLE_CLOUD_PROJECT=classconnect-455912")
    print("✅ GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json")
    print("✅ BASE_WEBHOOK_URL=" + PROD_URL)
    print("🔄 PUBSUB_WEBHOOK_AUTH_TOKEN=your-secret-token (optional)")

def main():
    print("🔍 PRODUCTION PUB/SUB DIAGNOSTIC")
    print("=" * 60)
    print(f"Testing: {PROD_URL}")
    print()
    
    # Test 1: Endpoint accessibility
    endpoint_results = test_endpoint_accessibility()
    
    # Test 2: Submission endpoint
    submission_url = test_submission_endpoint()
    
    # Test 3: Direct webhook test
    test_webhook_directly()
    
    # Test 4: Check for results (if submission worked)
    if submission_url:
        print(f"\n🔍 Checking for results...")
        time.sleep(2)
        try:
            response = requests.get(f"{PROD_URL}/api/v1/results/submission/{submission_url}")
            if response.status_code == 200:
                print("✅ Results found - pub/sub flow is working!")
            else:
                print("❌ No results found - pub/sub flow not working")
        except Exception as e:
            print(f"❌ Error checking results: {str(e)}")
    
    # Show setup instructions
    check_google_cloud_setup()
    check_environment_variables()
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. Set up Google Cloud Pub/Sub subscriptions (see commands above)")
    print("2. Verify environment variables in production")
    print("3. Test again with this script")
    print("4. Use the local simulation script for immediate testing")

if __name__ == "__main__":
    main() 