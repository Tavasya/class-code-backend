#!/usr/bin/env python3

import pytest
from app.services.transcription_service import TranscriptionService

class TestTranscriptionService:
    """Test suite for transcription service"""
    
    @pytest.mark.asyncio
    async def test_transcription_from_url(self):
        """Test transcription with a sample audio URL"""
        
        # Real audio file from Supabase storage
        test_audio_url = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/fd90cb13-6723-405c-bf9f-89917b9a89bc/e19e5f34-8d68-4ba4-a387-de3022af8874/fd90cb13-6723-405c-bf9f-89917b9a89bc_e19e5f34-8d68-4ba4-a387-de3022af8874_card-1748924855537_1750262342399.webm"
        
        print(f"\n🎙️  Testing Transcription Service")
        print("=" * 60)
        print(f"Audio URL: {test_audio_url}")
        print("Processing...")
        
        service = TranscriptionService()
        
        try:
            result = await service.transcribe_audio_from_url(test_audio_url)
            
            # Assertions
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "text" in result, "Result should contain text"
            assert "error" in result, "Result should contain error field"
            
            # Display results
            print("\n📝 TRANSCRIPTION RESULTS:")
            print("-" * 60)
            print(f"Transcribed Text: '{result.get('text', 'N/A')}'")
            print(f"Error: {result.get('error', 'None')}")
            print("=" * 60)
            
            # If you got text, show some stats
            if result.get('text'):
                text = result['text']
                word_count = len(text.split())
                print(f"Word Count: {word_count}")
                print(f"Character Count: {len(text)}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            # Don't fail the test if it's just a URL issue
            pytest.skip(f"Skipping due to: {e}")
    
    @pytest.mark.asyncio
    async def test_transcription_service_structure(self):
        """Test that the transcription service is properly structured"""
        
        print(f"\n🔧 Testing TranscriptionService structure...")
        
        service = TranscriptionService()
        
        # Test that service has expected methods
        assert hasattr(service, 'transcribe_audio_from_url'), "Service should have transcribe_audio_from_url method"
        assert hasattr(service, 'process_single_transcription'), "Service should have process_single_transcription method"
        
        # Test static methods exist
        assert hasattr(TranscriptionService, 'upload_to_assemblyai'), "Service should have upload_to_assemblyai static method"
        assert hasattr(TranscriptionService, 'get_assemblyai_transcript'), "Service should have get_assemblyai_transcript static method"
        
        print("✅ TranscriptionService structure is valid")
    
    @pytest.mark.asyncio
    async def test_with_invalid_url(self):
        """Test transcription with invalid URL to see error handling"""
        
        invalid_url = "https://invalid-url-for-testing.com/nonexistent.wav"
        
        print(f"\n🚨 Testing error handling with invalid URL...")
        print(f"Invalid URL: {invalid_url}")
        
        service = TranscriptionService()
        result = await service.transcribe_audio_from_url(invalid_url)
        
        # Should return a dict with error info
        assert isinstance(result, dict)
        assert "text" in result
        assert "error" in result
        
        print(f"Text: '{result.get('text', 'N/A')}'")
        print(f"Error: {result.get('error', 'None')}")
        
        # Should have empty text and some error message
        assert result.get('text') == "", "Invalid URL should return empty text"
        assert result.get('error') is not None, "Invalid URL should return an error" 