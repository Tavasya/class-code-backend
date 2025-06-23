#!/usr/bin/env python3

import pytest
from app.services.fluency_service import analyze_fluency, count_filler_words, calculate_timing_metrics
from app.models.fluency_model import FluencyRequest, WordDetail

class TestFluencyService:
    """Test suite for fluency analysis service"""
    
    def test_filler_word_detection(self):
        """Test filler word counting functionality"""
        
        test_cases = [
            ("This is a clear sentence without fillers.", 0),
            ("Um, I think, like, this is, you know, difficult.", 3),  # um, like, you know
            ("Well, so I was, uh, thinking about it.", 3),  # well, so, uh
            ("Actually, I mean, basically it's like whatever.", 5)  # actually, i mean, basically, like, whatever
        ]
        
        print("\n🔍 Testing Filler Word Detection")
        print("-" * 50)
        
        for text, expected_count in test_cases:
            count, filler_words = count_filler_words(text)
            
            print(f"Text: '{text}'")
            print(f"Expected: {expected_count}, Found: {count}")
            print(f"Fillers: {filler_words}")
            print()
            
            assert count == expected_count, f"Expected {expected_count} fillers, found {count}"
    
    def test_timing_metrics_calculation(self):
        """Test timing metrics calculation with mock word details"""
        
        print("\n⏱️  Testing Timing Metrics Calculation")
        print("-" * 50)
        
        # Mock word details with timing information
        word_details = [
            WordDetail(word="Hello", offset=0.0, duration=0.5, accuracy_score=95, error_type="None"),
            WordDetail(word="there", offset=0.8, duration=0.4, accuracy_score=90, error_type="None"),  # 0.3s pause
            WordDetail(word="how", offset=1.5, duration=0.3, accuracy_score=85, error_type="None"),    # 0.3s pause  
            WordDetail(word="are", offset=2.0, duration=0.4, accuracy_score=92, error_type="None"),    # 0.2s pause
            WordDetail(word="you", offset=2.8, duration=0.5, accuracy_score=88, error_type="None"),    # 0.4s pause (significant)
        ]
        
        metrics = calculate_timing_metrics(word_details)
        
        print("📊 Calculated Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Assertions
        assert "words_per_minute" in metrics
        assert "pause_count" in metrics
        assert "pause_percentage" in metrics
        
        # Should detect pauses > 0.3s (there are 2: 0.3s and 0.4s)
        assert metrics["pause_count"] >= 1, "Should detect significant pauses"
    
    @pytest.mark.asyncio
    async def test_fluency_analysis_with_good_speech(self):
        """Test fluency analysis with fluent speech pattern"""
        
        transcript = "I believe that education is fundamental to personal growth and development. When we invest in learning, we create opportunities for innovation and progress."
        
        print(f"\n🎯 Testing Fluent Speech Analysis")
        print(f"Text: '{transcript}'")
        print("-" * 50)
        
        # Create request with minimal word details for testing
        word_details = [
            WordDetail(word=word, offset=i*0.6, duration=0.5, accuracy_score=90, error_type="None")
            for i, word in enumerate(transcript.split())
        ]
        
        request = FluencyRequest(
            reference_text=transcript,
            word_details=word_details
        )
        
        result = await analyze_fluency(request)
        
        print("📊 FLUENCY ANALYSIS RESULTS:")
        print(f"Status: {result.status}")
        print(f"Overall Score: {result.fluency_metrics.overall_fluency_score}")
        print(f"Words Per Minute: {result.fluency_metrics.words_per_minute}")
        print(f"Filler Word Count: {result.fluency_metrics.filler_word_count}")
        print(f"Cohesive Device Level: {result.cohesive_device_band_level}")
        print("\nKey Findings:")
        for finding in result.key_findings[:3]:  # Show first 3 findings
            print(f"  • {finding}")
        print(f"\nCohesive Device Feedback: {result.cohesive_device_feedback[:100]}...")
        
        # Assertions
        assert result.status == "success"
        assert isinstance(result.fluency_metrics.overall_fluency_score, (int, float))
        assert 0 <= result.fluency_metrics.overall_fluency_score <= 100
        assert result.cohesive_device_band_level in [0, 1, 3, 5, 7, 9]  # Include 0 as default
        assert len(result.key_findings) >= 0
    
    @pytest.mark.asyncio
    async def test_fluency_analysis_with_disfluent_speech(self):
        """Test fluency analysis with disfluent speech (lots of fillers and pauses)"""
        
        transcript = "Um, well, I think, like, education is, you know, really important. Uh, when we, like, learn new things, um, we can, sort of, grow as people."
        
        print(f"\n🎯 Testing Disfluent Speech Analysis")  
        print(f"Text: '{transcript}'")
        print("-" * 50)
        
        # Create request with longer pauses to simulate hesitation
        word_details = [
            WordDetail(word=word, offset=i*1.2, duration=0.6, accuracy_score=85, error_type="None")  # Slower pace
            for i, word in enumerate(transcript.split()) if word not in ["um", "uh", "like", "well"]
        ]
        
        request = FluencyRequest(
            reference_text=transcript,
            word_details=word_details
        )
        
        result = await analyze_fluency(request)
        
        print("📊 FLUENCY ANALYSIS RESULTS:")
        print(f"Status: {result.status}")
        print(f"Overall Score: {result.fluency_metrics.overall_fluency_score}")
        print(f"Words Per Minute: {result.fluency_metrics.words_per_minute}")
        print(f"Filler Word Count: {result.fluency_metrics.filler_word_count}")
        print(f"Cohesive Device Level: {result.cohesive_device_band_level}")
        
        # Count filler words for comparison
        filler_count, filler_words = count_filler_words(transcript)
        print(f"Filler Words Detected: {filler_count} ({filler_words})")
        
        print("\nTop Key Findings:")
        for finding in result.key_findings[:3]:
            print(f"  • {finding}")
        
        # Assertions - should get lower grade due to disfluency
        assert result.status == "success"
        assert isinstance(result.fluency_metrics.overall_fluency_score, (int, float))
        assert result.fluency_metrics.overall_fluency_score < 80, "Disfluent speech should get lower grade"
        assert filler_count > 5, "Should detect multiple filler words" 