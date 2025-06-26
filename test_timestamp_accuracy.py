#!/usr/bin/env python3
"""
Test script specifically for timestamp accuracy in chunked pronunciation analysis.
This script validates that word timestamps remain accurate across chunks.
"""

import asyncio
import os
import sys
import datetime
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pronunciation_service import PronunciationService

# Test data
wav_path = "/var/folders/8j/7q9j9_8j78v7py905kp0c3ch0000gn/T/tmp9sxfn969.wav"
session_id = "timestamp_test_session"

# Long transcript that will definitely trigger chunking (>65 words)
long_transcript = """I bought a ticket to Costa Rica. Costa Rica is something me and my friends have planning a place of planning to visit. It is a country that is beautiful, exciting and very fun for our, for us. We are a group of 20 year olds just entering our senior year of college. I think this is a good celebratory trip to experience a new country and, and grow a better bond between friends. I think it'll be really fun. Our first itinerary is um, uh, La Fortuna, which is a, ah, jungle resort in Costa Rica. I bought it two months ago around um, May. And my next itinerary is after La Fortuna we go to Monteverde, which is labeled as Cloud City. The reason it's called Cloud City is because there's a lot of clouds going through the city. Then after that we go to a beach city. Not sure what the name is, but it's a very beautiful beach city and we will spend a lot of time on the beach, surfing, swimming, hanging out with the locals, stuff like that. After that we go back to San Jose."""

async def test_timestamp_accuracy():
    """Test timestamp accuracy in chunked analysis"""
    
    results = {
        "test_session": {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
        },
        "transcript_info": {
            "full_transcript": long_transcript,
            "word_count": len(long_transcript.split()),
            "character_count": len(long_transcript)
        },
        "timestamp_analysis": {},
        "issues_found": []
    }
    
    def log_result(message):
        """Helper to log results"""
        print(message)
    
    log_result("🕐 Testing Timestamp Accuracy in Chunked Analysis")
    log_result("=" * 55)
    
    word_count = len(long_transcript.split())
    log_result(f"📝 Transcript: {word_count} words (should trigger chunking)")
    log_result(f"📁 Audio file exists: {os.path.exists(wav_path) if wav_path != 'd' else False}")
    
    if not os.path.exists(wav_path) or wav_path == "d":
        log_result("⚠️ No audio file available - testing chunking logic only")
        
        # Test chunking logic without audio
        chunks = PronunciationService.chunk_text_into_phrases(long_transcript)
        log_result(f"📦 Text split into {len(chunks)} chunks:")
        
        cumulative_words = 0
        for i, chunk in enumerate(chunks):
            log_result(f"   Chunk {i+1}: {chunk['word_count']} words (words {cumulative_words+1}-{cumulative_words+chunk['word_count']})")
            log_result(f"      Text: {chunk['phrase'][:60]}...")
            cumulative_words += chunk['word_count']
        
        results["chunking_test"] = {
            "total_chunks": len(chunks),
            "chunk_details": chunks
        }
        
        return results
    
    try:
        log_result(f"🎤 Running chunked pronunciation analysis...")
        
        # Run the analysis
        result = await PronunciationService.analyze_pronunciation(
            wav_path, 
            long_transcript, 
            session_id
        )
        
        if result and "word_details" in result:
            word_details = result["word_details"]
            log_result(f"✅ Analysis completed with {len(word_details)} words")
            
            # Analyze timestamp patterns
            timestamp_issues = []
            previous_timestamp = 0
            
            log_result(f"\n🔍 Analyzing timestamps:")
            log_result(f"{'Word':<15} {'Timestamp':<12} {'Duration':<10} {'Chunk':<8} {'Issues':<20}")
            log_result("-" * 70)
            
            for i, word in enumerate(word_details):
                word_text = word.get("word", "")
                offset = word.get("offset", 0)  # This should already be in seconds
                duration = word.get("duration", 0)
                # Note: ChunkInfo metadata removed from production code
                chunk_num = "?"
                
                # Check for timestamp issues
                issues = []
                
                # Check if timestamp goes backwards
                if offset < previous_timestamp:
                    issues.append("BACKWARDS")
                    timestamp_issues.append({
                        "word": word_text,
                        "position": i + 1,
                        "issue": "timestamp_backwards",
                        "current": offset,
                        "previous": previous_timestamp
                    })
                
                # Check for large gaps (>5 seconds between words)
                if i > 0 and (offset - previous_timestamp) > 5.0:
                    issues.append("LARGE_GAP")
                    timestamp_issues.append({
                        "word": word_text,
                        "position": i + 1,
                        "issue": "large_gap",
                        "gap_seconds": offset - previous_timestamp
                    })
                
                # Check for very short durations
                if duration < 0.1 and duration > 0:
                    issues.append("SHORT_DUR")
                
                issues_str = ",".join(issues) if issues else "OK"
                
                log_result(f"{word_text:<15} {offset:<12.2f} {duration:<10.2f} {chunk_num:<8} {issues_str:<20}")
                
                # Show chunk transition details
                if chunk_info and i > 0:
                    prev_chunk = word_details[i-1].get("ChunkInfo", {}).get("chunk_number")
                    if chunk_info.get("chunk_number") != prev_chunk:
                        log_result(f"   ↳ Chunk transition: {prev_chunk} → {chunk_info.get('chunk_number')}")
                        log_result(f"     Chunk start time: {chunk_info.get('chunk_start_time', 0):.2f}s")
                        log_result(f"     Original offset: {chunk_info.get('original_offset', 0):.2f}s")
                
                previous_timestamp = offset
            
            # Summary
            results["timestamp_analysis"] = {
                "total_words": len(word_details),
                "timestamp_issues": len(timestamp_issues),
                "first_word_timestamp": word_details[0].get("offset", 0) if word_details else 0,
                "last_word_timestamp": word_details[-1].get("offset", 0) if word_details else 0,
                "total_audio_span": word_details[-1].get("offset", 0) - word_details[0].get("offset", 0) if len(word_details) > 1 else 0
            }
            
            results["issues_found"] = timestamp_issues
            
            log_result(f"\n📊 Timestamp Analysis Summary:")
            log_result(f"✅ Words processed: {len(word_details)}")
            log_result(f"❌ Timestamp issues found: {len(timestamp_issues)}")
            log_result(f"⏱️ Audio span: {results['timestamp_analysis']['total_audio_span']:.2f} seconds")
            
            if timestamp_issues:
                log_result(f"\n⚠️ Issues detected:")
                for issue in timestamp_issues[:5]:  # Show first 5 issues
                    log_result(f"   • {issue}")
            else:
                log_result(f"🎉 No timestamp issues detected!")
                
        else:
            log_result(f"❌ Analysis failed or returned no word details")
            results["error"] = "No word details in analysis result"
            
    except Exception as e:
        log_result(f"💥 Analysis error: {str(e)}")
        results["error"] = str(e)
    
    # Save detailed results
    output_filename = f"timestamp_accuracy_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log_result(f"💾 Detailed results saved to {output_filename}")
    except Exception as e:
        log_result(f"❌ Failed to save results: {str(e)}")
    
    return results

if __name__ == "__main__":
    print("🚀 Starting Timestamp Accuracy Test...")
    
    # Check if we're in the right directory
    if not os.path.exists("app/services/pronunciation_service.py"):
        print("❌ Error: Please run this script from the backend directory")
        print("   Current directory:", os.getcwd())
        sys.exit(1)
    
    # Run the async test
    try:
        results = asyncio.run(test_timestamp_accuracy())
        
        # Quick summary
        if "timestamp_analysis" in results:
            analysis = results["timestamp_analysis"]
            issues = len(results.get("issues_found", []))
            
            print(f"\n🏁 Test Complete!")
            print(f"Words analyzed: {analysis.get('total_words', 0)}")
            print(f"Timestamp issues: {issues}")
            
            if issues == 0:
                print("✅ Timestamps appear to be working correctly!")
            else:
                print("⚠️ Timestamp issues detected - check the detailed output above")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test runner error: {str(e)}")
        sys.exit(1)