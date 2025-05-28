"""
Simple integration test for Azure Speech pronunciation service.
Just tests if the API works with our audio files and reference text.
"""
import pytest
from app.services.pronunciation_service import PronunciationService


class TestAzureSpeech:
    """Simple tests to verify Azure Speech integration works."""

    async def test_pronunciation_analysis_works(self, test_audio_file, skip_if_no_api_keys):
        """Test that Azure Speech can analyze pronunciation."""
        reference_text = "The quick brown fox jumps over the lazy dog."
        
        result = await PronunciationService.analyze_pronunciation(
            test_audio_file, reference_text
        )
        
        # Just verify we get a valid response
        assert "grade" in result
        assert isinstance(result["grade"], (int, float))
        assert 0 <= result["grade"] <= 100
        assert "issues" in result
        print(f"✅ Azure Speech analysis worked. Grade: {result['grade']}")

    async def test_pronunciation_with_session_id_works(self, test_audio_file, skip_if_no_api_keys):
        """Test pronunciation analysis with session ID."""
        reference_text = "Hello world, this is a test."
        session_id = "test_session_123"
        
        result = await PronunciationService.analyze_pronunciation(
            test_audio_file, reference_text, session_id
        )
        
        # Just verify it works with session ID
        assert "grade" in result
        assert isinstance(result["grade"], (int, float))
        print(f"✅ Azure Speech with session ID worked. Grade: {result['grade']}") 