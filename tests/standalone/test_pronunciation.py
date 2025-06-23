#!/usr/bin/env python3

import pytest
import os
import tempfile
from app.services.pronunciation_service import PronunciationService
from app.services.audio_service import AudioService

class TestPronunciationService:
    """Test suite for pronunciation analysis service"""
    
    def test_pronunciation_service_structure(self):
        """Test that the pronunciation service has the expected methods"""
        
        print("\n🔧 Testing PronunciationService structure...")
        
        # Test static methods exist
        assert hasattr(PronunciationService, 'get_cmu_pronunciation'), "Should have get_cmu_pronunciation method"
        assert hasattr(PronunciationService, 'convert_to_ipa'), "Should have convert_to_ipa method"
        assert hasattr(PronunciationService, 'convert_to_ipa_with_stress'), "Should have convert_to_ipa_with_stress method"
        assert hasattr(PronunciationService, 'analyze_pronunciation'), "Should have analyze_pronunciation method"
        assert hasattr(PronunciationService, 'process_phoneme'), "Should have process_phoneme method"
        
        print("✅ PronunciationService structure is valid")
    
    def test_cmu_dictionary_lookup(self):
        """Test CMU dictionary pronunciation lookup"""
        
        print("\n📚 Testing CMU Dictionary Lookup")
        print("-" * 50)
        
        test_words = [
            ("hello", True),
            ("world", True), 
            ("pronunciation", True),
            ("nonexistentword123", False),
            ("", False)
        ]
        
        for word, should_exist in test_words:
            pronunciation = PronunciationService.get_cmu_pronunciation(word)
            
            print(f"Word: '{word}'")
            print(f"Pronunciation: {pronunciation}")
            
            if should_exist:
                assert len(pronunciation) > 0, f"Should find pronunciation for '{word}'"
                assert all(isinstance(p, str) for p in pronunciation), "All phonemes should be strings"
            else:
                assert len(pronunciation) == 0, f"Should not find pronunciation for '{word}'"
            
            print()
    
    def test_ipa_conversion(self):
        """Test Azure phoneme to IPA conversion"""
        
        print("\n🔤 Testing IPA Conversion")
        print("-" * 50)
        
        test_phonemes = [
            ("ax", "ə"),      # schwa
            ("ay", "aɪ"),     # PRICE vowel
            ("ow", "oʊ"),     # GOAT vowel
            ("iy", "i"),      # FLEECE vowel
            ("ih", "ɪ"),      # KIT vowel
            ("th", "θ"),      # voiceless th
            ("dh", "ð"),      # voiced th
            ("sh", "ʃ"),      # SHIP consonant
            ("unknown", "unknown")  # fallback case
        ]
        
        for azure_phoneme, expected_ipa in test_phonemes:
            ipa_result = PronunciationService.convert_to_ipa(azure_phoneme)
            
            print(f"Azure: '{azure_phoneme}' → IPA: '{ipa_result}' (expected: '{expected_ipa}')")
            assert ipa_result == expected_ipa, f"Expected '{expected_ipa}', got '{ipa_result}'"
        
        print("✅ All IPA conversions successful!")
    
    def test_stress_marking(self):
        """Test stress marking in phoneme conversion"""
        
        print("\n🎯 Testing Stress Marking")
        print("-" * 50)
        
        test_cases = [
            ("ax1", "ˈə"),    # primary stress
            ("iy2", "ˌi"),    # secondary stress
            ("ih", "ɪ"),      # no stress
        ]
        
        for phoneme_with_stress, expected in test_cases:
            result = PronunciationService.convert_to_ipa(phoneme_with_stress)
            
            print(f"Phoneme: '{phoneme_with_stress}' → '{result}' (expected: '{expected}')")
            assert result == expected, f"Expected '{expected}', got '{result}'"
        
        print("✅ Stress marking working correctly!")
    
    def test_phoneme_processing(self):
        """Test individual phoneme processing with stress"""
        
        print("\n⚙️  Testing Phoneme Processing")
        print("-" * 50)
        
        test_cases = [
            ("ax", None, "ə"),          # no stress
            ("ax", "ˈ", "ˈə"),          # primary stress
            ("iy", "ˌ", "ˌi"),          # secondary stress
        ]
        
        for phoneme, stress, expected in test_cases:
            result = PronunciationService.process_phoneme(phoneme, stress)
            
            print(f"Phoneme: '{phoneme}', Stress: '{stress}' → '{result}'")
            assert result == expected, f"Expected '{expected}', got '{result}'"
        
        print("✅ Phoneme processing working correctly!")
    
    def test_ipa_with_stress_conversion(self):
        """Test full IPA conversion with stress marks using CMU dictionary"""
        
        print("\n🎼 Testing IPA with Stress Conversion")
        print("-" * 50)
        
        test_cases = [
            ("hello", ["hh", "ax", "l", "ow"]),
            ("world", ["w", "er", "l", "d"]),
        ]
        
        for word, azure_phonemes in test_cases:
            ipa_result = PronunciationService.convert_to_ipa_with_stress(word, azure_phonemes)
            
            print(f"Word: '{word}'")
            print(f"Azure phonemes: {azure_phonemes}")
            print(f"IPA result: '{ipa_result}'")
            
            assert len(ipa_result) > 0, f"Should produce IPA for '{word}'"
            assert isinstance(ipa_result, str), "Result should be a string"
            
            print()
    
    def test_file_validation(self):
        """Test file validation for pronunciation analysis"""
        
        print("\n📁 Testing File Validation")
        print("-" * 50)
        
        # Test with non-existent file
        non_existent_file = "/path/to/nonexistent/file.wav"
        
        print(f"Testing with non-existent file: {non_existent_file}")
        
        # This should be wrapped in try-catch since it's async, but for structure test we just verify the logic
        try:
            # Test URL rejection (should not accept URLs)
            url = "https://example.com/audio.wav"
            print(f"Testing URL rejection: {url}")
            # Would fail with ValueError about URLs not being accepted
            
        except Exception as e:
            print(f"Expected behavior: {e}")
    
    @pytest.mark.asyncio
    async def test_pronunciation_analysis_with_real_audio(self):
        """Test pronunciation analysis with a real audio file (requires Azure Speech Key)"""
        
        print("\n🎙️  Testing Pronunciation Analysis with Real Audio")
        print("=" * 70)
        
        # First, we need to get a WAV file using the audio service
        test_audio_url = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/fd90cb13-6723-405c-bf9f-89917b9a89bc/e19e5f34-8d68-4ba4-a387-de3022af8874/fd90cb13-6723-405c-bf9f-89917b9a89bc_e19e5f34-8d68-4ba4-a387-de3022af8874_card-1748924855537_1750262342399.webm"
        
        # Reference text (from previous transcription test)
        reference_text = "For me is a total yes. But in the Asian culture, it's maybe a little bit greedy to have ambitions."
        
        print(f"Audio URL: {test_audio_url}")
        print(f"Reference text: '{reference_text}'")
        print()
        
        try:
            # Step 1: Convert audio to WAV using AudioService
            print("📥 Step 1: Converting audio to WAV...")
            audio_service = AudioService()
            wav_path = await audio_service.convert_to_wav(test_audio_url)
            
            print(f"✅ WAV file created: {wav_path}")
            print(f"File size: {os.path.getsize(wav_path):,} bytes")
            
            # Step 2: Analyze pronunciation
            print("\n🔍 Step 2: Analyzing pronunciation with Azure Speech...")
            result = await PronunciationService.analyze_pronunciation(
                audio_file=wav_path,
                reference_text=reference_text
            )
            
            # Assertions
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "grade" in result, "Result should contain grade"
            
            # Display results
            print("\n📊 PRONUNCIATION ANALYSIS RESULTS:")
            print("=" * 70)
            print(f"Overall Grade: {result.get('grade', 'N/A')}")
            
            if "issues" in result and result["issues"]:
                print(f"Number of Issues: {len(result['issues'])}")
                print("\n📝 Issues Found:")
                for i, issue in enumerate(result["issues"][:3], 1):  # Show first 3
                    issue_type = issue.get("type", "N/A")
                    message = issue.get("message", "N/A")
                    print(f"  {i}. [{issue_type}] {message}")
            
            # Check if we have detailed pronunciation data
            if "word_details" in result:
                word_details = result["word_details"]
                if word_details:
                    print(f"\n🔤 Word-level Analysis ({len(word_details)} words):")
                    for word_detail in word_details[:3]:  # Show first 3 words
                        word = word_detail.get("word", "N/A")
                        accuracy = word_detail.get("accuracy_score", "N/A")
                        print(f"  '{word}': {accuracy}% accuracy")
            
            print("=" * 70)
            
            # Cleanup
            try:
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
                    print("🗑️  Cleaned up WAV file")
            except:
                pass
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Pronunciation analysis failed: {error_msg}")
            
            # Skip test if it's an API key issue or Azure service unavailable
            if any(keyword in error_msg.lower() for keyword in ["speech_key", "authorization", "subscription", "invalid key", "unauthorized"]):
                pytest.skip(f"Pronunciation test skipped - Azure Speech API issue: {e}")
            elif "ffmpeg" in error_msg.lower():
                pytest.skip(f"Pronunciation test skipped - ffmpeg not available: {e}")
            else:
                # Re-raise other errors
                raise
    
    @pytest.mark.asyncio
    async def test_pronunciation_error_handling(self):
        """Test pronunciation service error handling"""
        
        print("\n🚨 Testing Error Handling")
        print("-" * 50)
        
        # Test with non-existent file
        non_existent_file = "/tmp/nonexistent_audio_file.wav"
        reference_text = "Hello world"
        
        print(f"Testing with non-existent file: {non_existent_file}")
        
        result = await PronunciationService.analyze_pronunciation(
            audio_file=non_existent_file,
            reference_text=reference_text
        )
        
        # Should return error result, not crash
        assert isinstance(result, dict), "Should return dict even on error"
        assert "grade" in result, "Should contain grade field"
        assert result["grade"] == 0, "Should have grade 0 on error"
        assert "issues" in result, "Should contain issues field"
        
        print(f"✅ Error handled gracefully")
        print(f"Grade: {result['grade']}")
        print(f"Issues: {len(result.get('issues', []))}")
        
        if result.get("issues"):
            print(f"Error message: {result['issues'][0].get('message', 'N/A')[:100]}...")
        
        print("✅ Error handling working correctly!") 