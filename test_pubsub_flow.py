#!/usr/bin/env python3
"""
Quick test script for pub/sub flow
Run this to test your submission pipeline end-to-end
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TEST_SUBMISSION = {
    "audio_urls": [
        "https://zyaobehxpcwxlyljzknw.supabase.co/storage/v1/object/public/audio_recordings/ef09cf11-6a08-4fc9-8f33-9722b4d9dcdc/83/0_1744680795502.webm",
    ],
    "submission_url": f"unique_cdcv46u-{int(time.time())}"
}

def test_submission_flow():
    """Test the complete submission flow"""
    print("🚀 Testing Pub/Sub Flow...")
    print(f"📤 Sending test submission: {TEST_SUBMISSION['submission_url']}")
    print(f"📊 Audio files: {len(TEST_SUBMISSION['audio_urls'])}")
    print("-" * 50)
    
    try:
        # Send submission
        response = requests.post(
            f"{BASE_URL}/api/v1/submission/submit",
            json=TEST_SUBMISSION,
            timeout=30
        )
        
        # Print response
        print(f"✅ Response Status: {response.status_code}")
        print(f"📋 Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("\n🎉 Submission sent successfully!")
            print("💡 Check your server logs to see the pub/sub flow in action")
            print("📊 Expected flow:")
            print("   1. Student submission published")
            print("   2. Audio & transcription processing (parallel)")
            print("   3. Analysis coordination")
            print("   4. Individual analyses (grammar, pronunciation, lexical, fluency)")
            print("   5. Final completion")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server")
        print("💡 Make sure your FastAPI server is running on localhost:8000")
        print("   Run: uvicorn app.main:app --reload")
        
    except requests.exceptions.Timeout:
        print("⏰ Error: Request timed out")
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_health_check():
    """Quick health check"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"⚠️ Server responded with status: {response.status_code}")
            return False
    except:
        print("❌ Server is not responding")
        return False

if __name__ == "__main__":
    print("🧪 Pub/Sub Flow Test Script")
    print("=" * 50)
    
    # Health check first
    if not test_health_check():
        print("\n💡 Start your server first:")
        print("   uvicorn app.main:app --reload")
        sys.exit(1)
    
    print()
    test_submission_flow()
    
    print("\n" + "=" * 50)
    print("📝 Test completed!")
    print("📊 Monitor your server logs for detailed flow execution") 