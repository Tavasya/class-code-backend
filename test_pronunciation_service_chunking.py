#!/usr/bin/env python3
"""
Test script for pronunciation service with chunking functionality
Tests the integrated chunking and streaming functionality in the main service file.
"""

import asyncio
import os
import sys
import datetime
import json

# Add the app directory to the path so we can import the service
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pronunciation_service import PronunciationService

# Test data
wav_path = "/var/folders/8j/7q9j9_8j78v7py905kp0c3ch0000gn/T/tmp9sxfn969.wav"
session_id = "test_chunking_session"

# Different transcript lengths to test all three methods
test_cases = [
    {
        "name": "Short transcript (standard analysis)",
        "transcript": "I bought a ticket to Costa Rica.",
        "expected_method": "standard"
    },
    {
        "name": "Medium transcript (streaming analysis)",
        "transcript": "I bought a ticket to Costa Rica. Costa Rica is something me and my friends have planning a place of planning to visit. It is a country that is beautiful, exciting and very fun for our group.",
        "expected_method": "streaming"
    },
    {
        "name": "Long transcript (chunking analysis)",
        "transcript": "I bought a ticket to Costa Rica. Costa Rica is something me and my friends have planning a place of planning to visit. It is a country that is beautiful, exciting and very fun for our, for us. We are a group of 20 year olds just entering our senior year of college. I think this is a good celebratory trip to experience a new country and, and grow a better bond between friends. I think it'll be really fun. Our first itinerary is um, uh, La Fortuna, which is a, ah, jungle resort in Costa Rica. I bought it two months ago around um, May. And my next itinerary is after La Fortuna we go to Monteverde, which is labeled as Cloud City. The reason it's called Cloud City is because there's a lot of clouds going through the city. Then after that we go to a beach city. Not sure what the name is, but it's a very beautiful beach city and we will spend a lot of time on the beach, surfing, swimming, hanging out with the locals, stuff like that. After that we go back to San Jose. San Jose is the capital of Costa Rica and is it is the city. Then from San Jose we will fly back to Los Angeles.",
        "expected_method": "chunking"
    }
]

async def test_pronunciation_service():
    """Test the pronunciation service with different transcript lengths"""
    
    results = {
        "test_session": {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
            "test_results": []
        },
        "test_cases": [],
        "summary": {}
    }
    
    def log_result(message, data=None):
        """Helper to log results"""
        entry = {
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        if data:
            entry["data"] = data
        results["test_session"]["test_results"].append(entry)
        print(message)
    
    log_result("🧪 Testing Pronunciation Service with Chunking Integration")
    log_result("=" * 60)
    
    # Check if audio file exists
    file_exists = os.path.exists(wav_path) if wav_path != "d" else False
    log_result(f"📁 Audio file exists: {file_exists}")
    if file_exists:
        file_size = os.path.getsize(wav_path)
        log_result(f"📏 Audio file size: {file_size} bytes")
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases):
        log_result(f"\n🔍 Test {i+1}/{total_tests}: {test_case['name']}")
        log_result(f"📝 Word count: {len(test_case['transcript'].split())} words")
        log_result(f"🎯 Expected method: {test_case['expected_method']}")
        log_result(f"📄 Transcript preview: {test_case['transcript'][:100]}...")
        
        test_result = {
            "test_name": test_case['name'],
            "word_count": len(test_case['transcript'].split()),
            "expected_method": test_case['expected_method'],
            "status": "pending"
        }
        
        if file_exists:
            try:
                # Test the pronunciation analysis
                log_result(f"🎤 Analyzing pronunciation...")
                
                result = await PronunciationService.analyze_pronunciation(
                    wav_path, 
                    test_case['transcript'], 
                    session_id
                )
                
                if result:
                    test_result["status"] = "success"
                    test_result["grade"] = result.get("grade", 0)
                    test_result["accuracy_score"] = result.get("accuracy_score", 0)
                    test_result["fluency_score"] = result.get("fluency_score", 0)
                    test_result["word_count_analyzed"] = len(result.get("word_details", []))
                    test_result["issues_count"] = len(result.get("issues", []))
                    
                    log_result(f"✅ Analysis successful!")
                    log_result(f"📊 Grade: {result.get('grade', 0)}")
                    log_result(f"📊 Accuracy: {result.get('accuracy_score', 0)}")
                    log_result(f"📊 Fluency: {result.get('fluency_score', 0)}")
                    log_result(f"📊 Words analyzed: {len(result.get('word_details', []))}")
                    log_result(f"📊 Issues: {len(result.get('issues', []))}")
                    
                    success_count += 1
                else:
                    test_result["status"] = "failed"
                    test_result["error"] = "No result returned"
                    log_result(f"❌ Analysis failed - no result returned")
                    
            except Exception as e:
                test_result["status"] = "error"
                test_result["error"] = str(e)
                log_result(f"❌ Analysis error: {str(e)}")
        else:
            test_result["status"] = "skipped"
            test_result["reason"] = "Audio file not found"
            log_result(f"⏭️ Test skipped - audio file not found")
        
        results["test_cases"].append(test_result)
    
    # Test helper methods directly
    log_result(f"\n🔧 Testing helper methods...")
    
    try:
        # Test chunking method
        if len(test_cases) > 2:
            long_text = test_cases[2]['transcript']
            log_result(f"📦 Testing text chunking with {len(long_text.split())} words...")
            
            chunks = PronunciationService.chunk_text_into_phrases(long_text)
            log_result(f"✅ Created {len(chunks)} phrase chunks")
            
            for j, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                log_result(f"   Chunk {j+1}: {chunk['word_count']} words - {chunk['phrase'][:50]}...")
    
    except Exception as e:
        log_result(f"❌ Helper method test error: {str(e)}")
    
    # Summary
    results["summary"] = {
        "total_tests": total_tests,
        "successful_tests": success_count,
        "failed_tests": total_tests - success_count,
        "success_rate": (success_count / total_tests * 100) if total_tests > 0 else 0,
        "audio_file_available": file_exists
    }
    
    log_result(f"\n📋 Test Summary:")
    log_result(f"✅ Successful: {success_count}/{total_tests}")
    log_result(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    log_result(f"📈 Success rate: {results['summary']['success_rate']:.1f}%")
    
    # Save results to file
    output_filename = f"pronunciation_chunking_test_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log_result(f"💾 Results saved to {output_filename}")
    except Exception as e:
        log_result(f"❌ Failed to save results: {str(e)}")
    
    return results

if __name__ == "__main__":
    print("🚀 Starting Pronunciation Service Chunking Tests...")
    
    # Check if we're in the right directory
    if not os.path.exists("app/services/pronunciation_service.py"):
        print("❌ Error: Please run this script from the backend directory")
        print("   Current directory:", os.getcwd())
        sys.exit(1)
    
    # Run the async test
    try:
        results = asyncio.run(test_pronunciation_service())
        print(f"\n🎉 Testing complete! Check the results file for detailed output.")
    except KeyboardInterrupt:
        print(f"\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test runner error: {str(e)}")
        sys.exit(1)