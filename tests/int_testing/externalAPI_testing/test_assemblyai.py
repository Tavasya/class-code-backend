"""
Simple integration test for AssemblyAI transcription service.
Just tests if the API works with our audio URLs.
"""
import pytest
from app.services.transcription_service import TranscriptionService


class TestAssemblyAI:
    """Simple tests to verify AssemblyAI integration works."""

    async def test_transcribe_audio_url_works(self, test_audio_url, skip_if_no_api_keys):
        """Test that AssemblyAI can transcribe a public audio URL."""
        service = TranscriptionService()
        
        result = await service.transcribe_audio_from_url(test_audio_url)
        
        # Just verify we get a response without errors
        assert result["error"] is None
        assert isinstance(result["text"], str)
        print(f"✅ AssemblyAI transcribed: '{result['text']}'")

    async def test_process_single_transcription_works(self, test_audio_url, skip_if_no_api_keys):
        """Test the main transcription method works."""
        service = TranscriptionService()
        
        result = await service.process_single_transcription(
            audio_url=test_audio_url,
            question_number=1,
            submission_url="test_submission"
        )
        
        # Just verify the method works
        assert result["error"] is None
        assert result["question_number"] == 1
        assert isinstance(result["text"], str)
        print(f"✅ Single transcription worked: '{result['text']}'") 