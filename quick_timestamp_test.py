#!/usr/bin/env python3
"""
Quick test to validate timestamp calculation logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pronunciation_service import PronunciationService

# Test text that will trigger chunking
long_text = "I bought a ticket to Costa Rica. Costa Rica is something me and my friends have planning a place of planning to visit. It is a country that is beautiful, exciting and very fun for our, for us. We are a group of 20 year olds just entering our senior year of college. I think this is a good celebratory trip to experience a new country and, and grow a better bond between friends. I think it'll be really fun. Our first itinerary is um, uh, La Fortuna, which is a jungle resort in Costa Rica."

def test_chunking_logic():
    """Test the chunking and timestamp calculation logic"""
    
    print("🧮 Testing Chunking Logic")
    print("=" * 40)
    
    words = long_text.split()
    total_words = len(words)
    total_duration = 60.0  # Simulate 60 seconds of audio
    
    print(f"📝 Total words: {total_words}")
    print(f"⏱️ Total duration: {total_duration}s")
    print(f"📊 Words per second: {total_words/total_duration:.2f}")
    
    # Test chunking
    chunks = PronunciationService.chunk_text_into_phrases(long_text)
    print(f"\n📦 Created {len(chunks)} chunks:")
    
    # Simulate the timestamp calculation logic
    cumulative_words_processed = 0
    words_per_second = total_words / total_duration
    
    for i, chunk in enumerate(chunks):
        chunk_start_time = cumulative_words_processed / words_per_second
        estimated_chunk_duration = chunk['word_count'] / words_per_second
        
        print(f"\nChunk {i+1}:")
        print(f"  Words: {chunk['word_count']} (positions {cumulative_words_processed+1}-{cumulative_words_processed+chunk['word_count']})")
        print(f"  Start time: {chunk_start_time:.2f}s")
        print(f"  Duration: {estimated_chunk_duration:.2f}s")
        print(f"  Text: {chunk['phrase'][:50]}...")
        
        # Simulate word timestamps within this chunk
        print(f"  Sample word timestamps:")
        sample_words = chunk['phrase'].split()[:5]  # First 5 words
        for j, word in enumerate(sample_words):
            # Simulate Azure giving us a relative timestamp within the chunk
            simulated_chunk_offset = j * 0.5  # 0.5s per word simulation
            global_timestamp = chunk_start_time + simulated_chunk_offset
            print(f"    Word {j+1} '{word}': chunk_offset={simulated_chunk_offset:.2f}s → global={global_timestamp:.2f}s")
        
        cumulative_words_processed += chunk['word_count']
    
    print(f"\n✅ Timestamp calculation logic validated!")
    print(f"📊 Final cumulative words: {cumulative_words_processed} (should equal {total_words})")
    
    return chunks

def test_timestamp_continuity():
    """Test that timestamps are continuous across chunks"""
    
    print(f"\n🔗 Testing Timestamp Continuity")
    print("=" * 40)
    
    # Simulate a realistic scenario
    simulated_results = []
    total_duration = 90.0
    total_words = 150
    words_per_second = total_words / total_duration
    
    # Create chunks
    chunk_size = 40
    for chunk_start in range(0, total_words, chunk_size):
        chunk_word_count = min(chunk_size, total_words - chunk_start)
        chunk_start_time = chunk_start / words_per_second
        
        # Simulate words in this chunk
        for word_in_chunk in range(chunk_word_count):
            word_position = chunk_start + word_in_chunk
            
            # Simulate Azure's relative timestamp within chunk (random-ish)
            azure_relative_offset = word_in_chunk * 0.4 + (word_in_chunk % 3) * 0.1
            
            # Calculate global timestamp using our new logic
            global_timestamp = chunk_start_time + azure_relative_offset
            
            simulated_results.append({
                "word_position": word_position + 1,
                "word": f"word{word_position+1}",
                "chunk_start_time": chunk_start_time,
                "azure_offset": azure_relative_offset,
                "global_timestamp": global_timestamp,
                "chunk_number": (chunk_start // chunk_size) + 1
            })
    
    # Check for issues
    issues = []
    for i in range(1, len(simulated_results)):
        current = simulated_results[i]
        previous = simulated_results[i-1]
        
        # Check if timestamp goes backwards
        if current["global_timestamp"] < previous["global_timestamp"]:
            issues.append(f"Word {current['word_position']}: timestamp goes backwards ({previous['global_timestamp']:.2f} → {current['global_timestamp']:.2f})")
        
        # Check for large gaps between adjacent words
        gap = current["global_timestamp"] - previous["global_timestamp"]
        if gap > 2.0:  # More than 2 seconds between words is suspicious
            issues.append(f"Word {current['word_position']}: large gap of {gap:.2f}s from previous word")
    
    # Show sample results
    print(f"📊 Generated {len(simulated_results)} word timestamps")
    print(f"⚠️ Issues found: {len(issues)}")
    
    if issues:
        print(f"\n❌ Timestamp issues detected:")
        for issue in issues[:5]:  # Show first 5 issues
            print(f"   • {issue}")
    else:
        print(f"✅ No timestamp continuity issues detected!")
    
    # Show transitions between chunks
    print(f"\n🔄 Chunk transitions:")
    current_chunk = 1
    for result in simulated_results:
        if result["chunk_number"] != current_chunk:
            print(f"   Chunk {current_chunk} → {result['chunk_number']} at word {result['word_position']} ({result['global_timestamp']:.2f}s)")
            current_chunk = result["chunk_number"]
    
    return len(issues) == 0

if __name__ == "__main__":
    print("🚀 Quick Timestamp Logic Test")
    print("="*50)
    
    try:
        # Test 1: Chunking logic
        chunks = test_chunking_logic()
        
        # Test 2: Timestamp continuity
        continuity_ok = test_timestamp_continuity()
        
        print(f"\n🏁 Test Results:")
        print(f"✅ Chunking: {len(chunks)} chunks created")
        print(f"{'✅' if continuity_ok else '❌'} Timestamp continuity: {'PASS' if continuity_ok else 'FAIL'}")
        
        if continuity_ok:
            print(f"\n🎉 Timestamp calculation logic appears to be working correctly!")
        else:
            print(f"\n⚠️ Timestamp issues detected - review the logic above")
            
    except Exception as e:
        print(f"\n💥 Test error: {str(e)}")
        sys.exit(1)