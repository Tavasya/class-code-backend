#!/usr/bin/env python3
"""
Test script to verify frontend timestamp fields (offset and duration in seconds)
This specifically tests the offset/duration fields that the frontend uses.
"""

import asyncio
import os
import sys
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pronunciation_service import PronunciationService

# Test data that will trigger chunking (>65 words)
long_transcript = """I bought a ticket to Costa Rica. Costa Rica is something me and my friends have planning a place of planning to visit. It is a country that is beautiful, exciting and very fun for our, for us. We are a group of 20 year olds just entering our senior year of college. I think this is a good celebratory trip to experience a new country and grow a better bond between friends. I think it'll be really fun. Our first itinerary is La Fortuna, which is a jungle resort in Costa Rica."""

wav_path = "/var/folders/8j/7q9j9_8j78v7py905kp0c3ch0000gn/T/tmp9sxfn969.wav"
session_id = "frontend_timestamp_test"

async def test_frontend_timestamps():
    """Test that offset and duration fields are accurate for frontend use"""
    
    print("🕐 Testing Frontend Timestamp Fields (offset/duration in seconds)")
    print("=" * 65)
    
    word_count = len(long_transcript.split())
    print(f"📝 Transcript: {word_count} words (should trigger chunking)")
    
    if not os.path.exists(wav_path) or wav_path == "d":
        print("⚠️ No audio file available - cannot test actual timestamps")
        return False
    
    try:
        print(f"🎤 Running pronunciation analysis...")
        
        result = await PronunciationService.analyze_pronunciation(
            wav_path, 
            long_transcript, 
            session_id
        )
        
        if not result or "word_details" not in result:
            print("❌ No word details returned")
            return False
            
        word_details = result["word_details"]
        print(f"✅ Analysis completed with {len(word_details)} words")
        
        # Check frontend timestamp fields
        print(f"\n🔍 Checking Frontend Timestamp Fields:")
        print(f"{'Word':<15} {'Offset(s)':<10} {'Duration(s)':<12} {'Issues':<20}")
        print("-" * 60)
        
        issues = []
        prev_end_time = 0
        
        for i, word in enumerate(word_details[:20]):  # Check first 20 words
            word_text = word.get("word", "")
            offset = word.get("offset", 0)  # This should be in seconds
            duration = word.get("duration", 0)  # This should be in seconds
            
            word_issues = []
            
            # Check if offset goes backwards
            if offset < prev_end_time and i > 0:
                word_issues.append("BACKWARDS")
                issues.append(f"Word {i+1} '{word_text}': offset {offset:.2f}s goes backward from previous end {prev_end_time:.2f}s")
            
            # Check for unrealistic durations
            if duration < 0.05:
                word_issues.append("TOO_SHORT")
            elif duration > 3.0:
                word_issues.append("TOO_LONG")
            
            # Check for large gaps (>2s between words)
            if i > 0 and (offset - prev_end_time) > 2.0:
                word_issues.append("LARGE_GAP")
                issues.append(f"Word {i+1} '{word_text}': large gap of {offset - prev_end_time:.2f}s")
            
            issues_str = ",".join(word_issues) if word_issues else "OK"
            print(f"{word_text:<15} {offset:<10.2f} {duration:<12.2f} {issues_str:<20}")
            
            prev_end_time = offset + duration
        
        # Show chunk transitions if we can detect them
        print(f"\n📊 Timeline Analysis:")
        print(f"First word starts at: {word_details[0].get('offset', 0):.2f}s")
        if len(word_details) > 1:
            last_word = word_details[-1]
            last_end = last_word.get('offset', 0) + last_word.get('duration', 0)
            print(f"Last word ends at: {last_end:.2f}s")
            print(f"Total timeline span: {last_end - word_details[0].get('offset', 0):.2f}s")
        
        # Look for chunk boundaries (where there might be timing jumps)
        chunk_boundaries = []
        for i in range(1, min(len(word_details), 100)):  # Check first 100 words
            current = word_details[i]
            previous = word_details[i-1]
            
            gap = current.get('offset', 0) - (previous.get('offset', 0) + previous.get('duration', 0))
            if gap > 1.0:  # More than 1 second gap might indicate chunk boundary
                chunk_boundaries.append({
                    "word_position": i + 1,
                    "word": current.get('word', ''),
                    "gap_seconds": gap,
                    "previous_word": previous.get('word', ''),
                    "new_start": current.get('offset', 0)
                })
        
        if chunk_boundaries:
            print(f"\n🔄 Possible Chunk Boundaries Detected:")
            for boundary in chunk_boundaries:
                print(f"   After word {boundary['word_position']-1} '{boundary['previous_word']}' → '{boundary['word']}' (gap: {boundary['gap_seconds']:.2f}s, starts at {boundary['new_start']:.2f}s)")
        
        # Summary
        print(f"\n📋 Frontend Timestamp Test Results:")
        print(f"✅ Words analyzed: {len(word_details)}")
        print(f"❌ Timestamp issues: {len(issues)}")
        print(f"🔄 Potential chunk boundaries: {len(chunk_boundaries)}")
        
        if issues:
            print(f"\n⚠️ Issues Found:")
            for issue in issues[:5]:  # Show first 5
                print(f"   • {issue}")
            
            return False
        else:
            print(f"🎉 All frontend timestamps look good!")
            return True
            
    except Exception as e:
        print(f"💥 Test error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Frontend Timestamp Fields...")
    
    if not os.path.exists("app/services/pronunciation_service.py"):
        print("❌ Error: Please run this script from the backend directory")
        sys.exit(1)
    
    try:
        success = asyncio.run(test_frontend_timestamps())
        
        if success:
            print(f"\n✅ Frontend timestamp test PASSED!")
            print(f"The offset and duration fields should work correctly in the frontend.")
        else:
            print(f"\n❌ Frontend timestamp test FAILED!")
            print(f"There are issues with offset/duration accuracy that need to be fixed.")
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted")
    except Exception as e:
        print(f"\n💥 Test runner error: {str(e)}")
        sys.exit(1)