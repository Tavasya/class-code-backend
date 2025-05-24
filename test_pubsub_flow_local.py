#!/usr/bin/env python3
"""
Local test script for pub/sub flow (simulates webhooks without Google Cloud)
This bypasses the need for actual Pub/Sub subscriptions by calling webhooks directly
"""

import requests
import json
import time
import sys
import base64

# Configuration
BASE_URL = "http://localhost:8000"
TEST_SUBMISSION = {
    "audio_urls": [
        "https://zyaobehxpcwxlyljzknw.supabase.co/storage/v1/object/public/audio_recordings/ef09cf11-6a08-4fc9-8f33-9722b4d9dcdc/83/0_1744680795502.webm",
    ],
    "submission_url": f"local_test-{int(time.time())}"
}

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

def simulate_webhook_call(endpoint, data, step_name=""):
    """Simulate a webhook call from Pub/Sub"""
    try:
        pubsub_message = create_pubsub_message(data)
        response = requests.post(
            f"{BASE_URL}/api/v1/webhooks/{endpoint}",
            json=pubsub_message,
            timeout=30
        )
        
        success = response.status_code == 200
        icon = "✅" if success else "❌"
        
        print(f"{icon} {step_name} ({endpoint}): {response.status_code}")
        if success:
            resp_data = response.json()
            print(f"   📝 {resp_data.get('message', 'Success')}")
        else:
            print(f"   ❌ Error: {response.text[:100]}")
            
        return success
    except Exception as e:
        print(f"❌ {step_name} failed: {str(e)}")
        return False

def print_analysis_results(results):
    """Pretty print analysis results with detailed feedback"""
    print("\n" + "=" * 80)
    print("📊 DETAILED ANALYSIS RESULTS")
    print("=" * 80)
    
    print(f"🔗 Submission URL: {results['submission_url']}")
    print(f"📝 Questions: {results['completed_questions']}/{results['total_questions']}")
    print(f"⏰ Completed: {results['timestamp']}")
    
    for q_num, q_results in results['question_results'].items():
        print(f"\n" + "━" * 80)
        print(f"📋 QUESTION {q_num} - DETAILED ANALYSIS")
        print("━" * 80)
        
        # Grammar Analysis
        if 'grammar' in q_results:
            grammar = q_results['grammar']
            print(f"\n📝 GRAMMAR ANALYSIS:")
            print("-" * 50)
            if 'error' in grammar:
                print(f"❌ Error: {grammar['error']}")
            else:
                print(f"✅ Overall Score: {grammar.get('overall_score', 'N/A')}")
                print(f"📊 Accuracy: {grammar.get('accuracy', 'N/A')}")
                
                if 'errors' in grammar and grammar['errors']:
                    print(f"\n🔍 Grammar Errors Found ({len(grammar['errors'])}):")
                    for i, error in enumerate(grammar['errors'], 1):
                        print(f"   {i}. {error.get('message', 'No message')}")
                        if error.get('suggestions'):
                            print(f"      💡 Suggestion: {', '.join(error['suggestions'])}")
                        if error.get('context'):
                            print(f"      📝 Context: {error['context']}")
                
                if 'feedback' in grammar:
                    print(f"\n💬 Grammar Feedback:")
                    if isinstance(grammar['feedback'], str):
                        print(f"   {grammar['feedback']}")
                    elif isinstance(grammar['feedback'], list):
                        for feedback in grammar['feedback']:
                            print(f"   • {feedback}")
        
        # Show other analyses (pronunciation, lexical, fluency)
        for analysis_type in ['pronunciation', 'lexical', 'fluency']:
            if analysis_type in q_results:
                analysis = q_results[analysis_type]
                print(f"\n{analysis_type.upper()} ANALYSIS:")
                print("-" * 50)
                if 'error' in analysis:
                    print(f"❌ Error: {analysis['error']}")
                else:
                    # Show key metrics
                    if analysis_type == 'pronunciation':
                        print(f"✅ Overall Score: {analysis.get('overall_score', 'N/A')}")
                        print(f"📊 Accuracy: {analysis.get('accuracy_score', 'N/A')}")
                    elif analysis_type == 'fluency':
                        print(f"✅ Overall Score: {analysis.get('overall_score', 'N/A')}")
                        print(f"⚡ Fluency: {analysis.get('fluency_score', 'N/A')}")
                    elif analysis_type == 'lexical':
                        if isinstance(analysis, list) and len(analysis) > 0:
                            print(f"✅ Categories: {len(analysis)}")
                            for item in analysis[:3]:  # Show first 3 items
                                print(f"   • {item.get('category', 'N/A')}: {item.get('score', 'N/A')}")
                        else:
                            print(f"✅ Data: {str(analysis)[:100]}...")

def simulate_full_flow():
    """Simulate the complete pub/sub flow locally with proper phase handling"""
    print("🚀 Simulating Complete Pub/Sub Flow Locally...")
    print(f"📤 Testing submission: {TEST_SUBMISSION['submission_url']}")
    print("⚠️  Note: Some services may show errors due to missing API keys - this is expected in testing")
    print("-" * 80)
    
    # Step 1: Send initial submission
    print("\n1️⃣ SENDING SUBMISSION")
    print("-" * 40)
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/submission/submit",
            json=TEST_SUBMISSION,
            timeout=30
        )
        print(f"✅ Submission: {response.status_code} - {response.json()}")
        if response.status_code != 200:
            print("❌ Submission failed, stopping test")
            return
    except Exception as e:
        print(f"❌ Submission failed: {str(e)}")
        return
    
    # Step 2: Simulate audio and transcription webhooks
    print("\n2️⃣ PHASE 0: AUDIO & TRANSCRIPTION PROCESSING")
    print("-" * 40)
    submission_data = {
        "audio_urls": TEST_SUBMISSION["audio_urls"],
        "submission_url": TEST_SUBMISSION["submission_url"],
        "total_questions": len(TEST_SUBMISSION["audio_urls"])
    }
    
    # Simulate parallel audio and transcription processing
    audio_success = simulate_webhook_call("student-submission-audio", submission_data, "Audio Processing")
    transcription_success = simulate_webhook_call("student-submission-transcription", submission_data, "Transcription Processing")
    
    if not (audio_success and transcription_success):
        print("❌ Audio/Transcription processing failed, stopping test")
        return
    
    # Wait for audio/transcription to complete
    print("\n⏳ Waiting for audio/transcription processing...")
    time.sleep(5)
    
    # Step 3: Simulate audio/transcription completion coordination
    print("\n3️⃣ PHASE 0: COMPLETION COORDINATION")
    print("-" * 40)
    
    # Audio conversion done
    audio_done_data = {
        "wav_path": "/tmp/test_audio.wav",  # This file doesn't exist but that's ok for testing
        "question_number": 1,
        "submission_url": TEST_SUBMISSION["submission_url"],
        "original_audio_url": TEST_SUBMISSION["audio_urls"][0],
        "total_questions": 1
    }
    simulate_webhook_call("audio-conversion-done", audio_done_data, "Audio Conversion Done")
    
    # Transcription done
    transcription_done_data = {
        "text": "Testing, testing, 1, 2, 3.",  # This matches what we see in logs
        "error": None,
        "question_number": 1,
        "submission_url": TEST_SUBMISSION["submission_url"],
        "audio_url": TEST_SUBMISSION["audio_urls"][0],
        "total_questions": 1
    }
    simulate_webhook_call("transcription-done", transcription_done_data, "Transcription Done")
    
    # Step 4: Wait for analysis coordination and Phase 1
    print("\n4️⃣ PHASE 1: ANALYSIS READY & PARALLEL ANALYSIS")
    print("-" * 40)
    print("⏳ Waiting for analysis coordination...")
    time.sleep(3)
    
    # Question analysis ready should already be triggered by the coordination
    analysis_ready_data = {
        "wav_path": "/tmp/test_audio.wav",
        "transcript": "Testing, testing, 1, 2, 3.",
        "question_number": 1,
        "submission_url": TEST_SUBMISSION["submission_url"],
        "audio_url": TEST_SUBMISSION["audio_urls"][0],
        "total_questions": 1
    }
    simulate_webhook_call("question-analysis-ready", analysis_ready_data, "Question Analysis Ready")
    
    # Wait for Phase 1 analysis to complete
    print("\n⏳ Waiting for Phase 1 analysis (Grammar, Pronunciation, Lexical)...")
    time.sleep(8)
    
    # Step 5: Simulate Phase 2 - Pronunciation Done triggers Fluency
    print("\n5️⃣ PHASE 2: FLUENCY ANALYSIS (triggered by pronunciation)")
    print("-" * 40)
    
    # Simulate pronunciation done to trigger fluency
    pronunciation_done_data = {
        "question_number": 1,
        "submission_url": TEST_SUBMISSION["submission_url"],
        "wav_path": "/tmp/test_audio.wav",
        "transcript": "Testing, testing, 1, 2, 3.",
        "audio_url": TEST_SUBMISSION["audio_urls"][0],
        "total_questions": 1,
        "result": {
            "overall_score": 75,
            "accuracy_score": 80,
            "error": "File open failed - expected in testing",
            "word_details": []  # Empty for testing
        }
    }
    simulate_webhook_call("pronunciation-done", pronunciation_done_data, "Pronunciation Done → Fluency Trigger")
    
    # Wait for fluency analysis
    print("\n⏳ Waiting for fluency analysis...")
    time.sleep(5)
    
    # Step 6: Simulate individual analysis completions
    print("\n6️⃣ PHASE 3: INDIVIDUAL ANALYSIS ACKNOWLEDGMENTS")  
    print("-" * 40)
    
    # Simulate all individual analysis webhooks
    base_result_data = {
        "question_number": 1,
        "submission_url": TEST_SUBMISSION["submission_url"],
        "total_questions": 1,
        "result": {"overall_score": 75, "note": "Test result"}
    }
    
    simulate_webhook_call("grammar-done", base_result_data, "Grammar Done")
    simulate_webhook_call("lexical-done", base_result_data, "Lexical Done") 
    simulate_webhook_call("fluency-done", base_result_data, "Fluency Done")
    
    # Step 7: Final analysis complete
    print("\n7️⃣ PHASE 4: ANALYSIS COMPLETION")
    print("-" * 40)
    
    analysis_complete_data = {
        "question_number": 1,
        "submission_url": TEST_SUBMISSION["submission_url"],
        "total_questions": 1,
        "analysis_results": {
            "pronunciation": {"overall_score": 75, "error": "File access issue (expected)"},
            "grammar": {"overall_score": 70, "error": "API key issue (expected)"},
            "lexical": [{"category": "vocabulary", "score": 80, "feedback": "Good range"}],
            "fluency": {"overall_score": 78, "fluency_score": 75}
        }
    }
    simulate_webhook_call("analysis-complete", analysis_complete_data, "Analysis Complete")
    
    # Step 8: Wait and check for final results
    print("\n8️⃣ CHECKING FINAL RESULTS")
    print("-" * 40)
    print("⏳ Waiting for final submission completion...")
    time.sleep(3)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/results/submission/{TEST_SUBMISSION['submission_url']}",
            timeout=5
        )
        
        if response.status_code == 200:
            print("🎉 SUCCESS! Analysis results found!")
            print_analysis_results(response.json())
        else:
            print(f"⚠️ No results yet: {response.status_code}")
            print("💡 The flow completed but results may not be stored due to service errors")
            print("   This is expected when API keys are missing or files don't exist")
            
    except Exception as e:
        print(f"❌ Error checking results: {str(e)}")

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
    print("🧪 Complete Local Pub/Sub Flow Simulation")
    print("=" * 80)
    print("💡 This simulates the full Google Cloud Pub/Sub flow locally")
    print("⚠️  Service errors (API keys, file access) are expected in testing")
    
    # Health check first
    if not test_health_check():
        print("\n💡 Start your server first:")
        print("   uvicorn app.main:app --reload")
        sys.exit(1)
    
    print()
    simulate_full_flow()
    
    print("\n" + "=" * 80)
    print("📝 Local simulation completed!")
    print("💡 For production: Set up Google Cloud Pub/Sub subscriptions")
    print("💡 For testing: Fix API keys (OpenAI) and file paths for full functionality") 