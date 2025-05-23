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
        
        # Pronunciation Analysis  
        if 'pronunciation' in q_results:
            pronunciation = q_results['pronunciation']
            print(f"\n🗣️ PRONUNCIATION ANALYSIS:")
            print("-" * 50)
            if 'error' in pronunciation:
                print(f"❌ Error: {pronunciation['error']}")
            else:
                print(f"✅ Overall Score: {pronunciation.get('overall_score', 'N/A')}")
                print(f"📊 Accuracy Score: {pronunciation.get('accuracy_score', 'N/A')}")
                print(f"🎯 Fluency Score: {pronunciation.get('fluency_score', 'N/A')}")
                print(f"⚡ Speaking Rate: {pronunciation.get('speaking_rate', 'N/A')}")
                
                if 'word_details' in pronunciation and pronunciation['word_details']:
                    print(f"\n🔤 Word-by-Word Analysis:")
                    for word in pronunciation['word_details'][:10]:  # Show first 10 words
                        word_text = word.get('word', 'Unknown')
                        accuracy = word.get('accuracy_score', 'N/A')
                        error_type = word.get('error_type', 'None')
                        print(f"   '{word_text}': {accuracy} ({error_type})")
                    if len(pronunciation['word_details']) > 10:
                        print(f"   ... and {len(pronunciation['word_details']) - 10} more words")
                
                if 'feedback' in pronunciation:
                    print(f"\n💬 Pronunciation Feedback:")
                    if isinstance(pronunciation['feedback'], str):
                        print(f"   {pronunciation['feedback']}")
                    elif isinstance(pronunciation['feedback'], list):
                        for feedback in pronunciation['feedback']:
                            print(f"   • {feedback}")
        
        # Lexical Analysis
        if 'lexical' in q_results:
            lexical = q_results['lexical']
            print(f"\n📚 LEXICAL ANALYSIS:")
            print("-" * 50)
            if 'error' in lexical:
                print(f"❌ Error: {lexical['error']}")
            else:
                if isinstance(lexical, list):
                    # Handle list of feedback items
                    print(f"📋 Lexical Feedback Items ({len(lexical)}):")
                    for i, item in enumerate(lexical, 1):
                        print(f"\n   {i}. Category: {item.get('category', 'N/A')}")
                        print(f"      Score: {item.get('score', 'N/A')}")
                        print(f"      Feedback: {item.get('feedback', 'N/A')}")
                        if item.get('suggestions'):
                            print(f"      💡 Suggestions: {', '.join(item['suggestions'])}")
                else:
                    # Handle dictionary format
                    print(f"✅ Overall Score: {lexical.get('overall_score', 'N/A')}")
                    print(f"🔤 Lexical Diversity: {lexical.get('lexical_diversity', 'N/A')}")
                    print(f"📊 Vocabulary Range: {lexical.get('vocabulary_range', 'N/A')}")
                    
                    if 'feedback' in lexical:
                        print(f"\n💬 Lexical Feedback:")
                        if isinstance(lexical['feedback'], str):
                            print(f"   {lexical['feedback']}")
                        elif isinstance(lexical['feedback'], list):
                            for feedback in lexical['feedback']:
                                print(f"   • {feedback}")
        
        # Fluency Analysis
        if 'fluency' in q_results:
            fluency = q_results['fluency']
            print(f"\n🌊 FLUENCY ANALYSIS:")
            print("-" * 50)
            if 'error' in fluency:
                print(f"❌ Error: {fluency['error']}")
            else:
                print(f"✅ Overall Score: {fluency.get('overall_score', 'N/A')}")
                print(f"⚡ Fluency Score: {fluency.get('fluency_score', 'N/A')}")
                print(f"🔗 Coherence Score: {fluency.get('coherence_score', 'N/A')}")
                print(f"⏱️ Speaking Rate: {fluency.get('speaking_rate', 'N/A')} WPM")
                print(f"⏸️ Pause Analysis: {fluency.get('pause_analysis', 'N/A')}")
                
                if 'feedback' in fluency:
                    print(f"\n💬 Fluency Feedback:")
                    if isinstance(fluency['feedback'], str):
                        print(f"   {fluency['feedback']}")
                    elif isinstance(fluency['feedback'], list):
                        for feedback in fluency['feedback']:
                            print(f"   • {feedback}")
                
                if 'detailed_analysis' in fluency:
                    print(f"\n🔍 Detailed Fluency Analysis:")
                    for key, value in fluency['detailed_analysis'].items():
                        print(f"   {key.title()}: {value}")

def wait_for_results(submission_url, timeout=120):
    """Wait for analysis results to be available"""
    print(f"\n⏳ Waiting for analysis results (timeout: {timeout}s)...")
    
    start_time = time.time()
    dots = 0
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/results/submission/{submission_url}",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # Still processing, keep waiting
                time.sleep(2)
                dots = (dots + 1) % 4
                print(f"\r⏳ Processing{'.' * dots}{'  ' * (3-dots)}", end='', flush=True)
            else:
                print(f"\n⚠️ Unexpected response: {response.status_code}")
                time.sleep(2)
                
        except requests.exceptions.RequestException:
            time.sleep(2)
            dots = (dots + 1) % 4
            print(f"\r⏳ Processing{'.' * dots}{'  ' * (3-dots)}", end='', flush=True)
    
    print(f"\n⏰ Timeout reached ({timeout}s)")
    return None

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
            
            # Wait for results
            results = wait_for_results(TEST_SUBMISSION['submission_url'])
            
            if results:
                print_analysis_results(results)
            else:
                print("\n❌ No results received within timeout period")
                print("💡 Check your server logs for processing status")
                
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
    print("💡 Use /api/v1/results/submissions to see all results") 