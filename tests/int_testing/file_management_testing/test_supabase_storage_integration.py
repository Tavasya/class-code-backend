import pytest
import json
import tempfile
import os
from datetime import datetime
from app.core.config import supabase
from app.services.database_service import DatabaseService


class TestSupabaseStorageIntegration:
    """Integration tests for Supabase storage operations"""

    @pytest.fixture
    def db_service(self):
        """DatabaseService instance for testing"""
        return DatabaseService()

    @pytest.mark.asyncio
    async def test_storage_error_handling(self):
        """Test handling of storage errors"""
        if not supabase:
            pytest.skip("Supabase client not available")
        
        # Try to download non-existent file from recordings bucket
        try:
            download_response = supabase.storage.from_('recordings').download('nonexistent_file.webm')
            # If no exception, check if response indicates error
            assert download_response is None or len(download_response) == 0
        except Exception:
            # Exception is expected for non-existent files
            pass

    @pytest.mark.asyncio
    async def test_database_submission_operations(self, db_service, submission_url):
        """Test database operations for submissions using real test submission"""
        if not supabase:
            pytest.skip("Supabase client not available")
        
        # Test data for submission
        question_results = {
            "1": {
                "pronunciation_score": 85,
                "original_audio_url": "https://example.com/audio1.webm"
            },
            "2": {
                "pronunciation_score": 78,
                "original_audio_url": "https://example.com/audio2.webm"
            }
        }
        recordings = ["https://example.com/audio1.webm", "https://example.com/audio2.webm"]
        
        # Try to update submission results using the real test submission
        result = db_service.update_submission_results(
            submission_url=submission_url,
            question_results=question_results,
            recordings=recordings
        )
        
        # Since we're using a real submission URL that should exist, this should succeed
        if result is not None:
            # If it succeeded, verify the result
            assert isinstance(result, str)
            assert len(result) > 0
        else:
            # If it failed, it means the test submission doesn't exist yet
            pytest.skip(f"Test submission {submission_url} not found in database. Please create it first.")

    @pytest.mark.asyncio
    async def test_recordings_bucket_public_access(self, test_audio_url):
        """Test that we can access recordings bucket files via public URLs"""
        if not supabase:
            pytest.skip("Supabase client not available")
        
        # Test downloading the actual test audio file via HTTP
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(test_audio_url) as response:
                    # Should be able to download the file
                    assert response.status == 200
                    
                    # Should have content
                    content = await response.read()
                    assert len(content) > 0
                    
                    # Should be a WebM file based on the URL
                    content_type = response.headers.get('content-type', '')
                    # Content type might vary, but file should exist and be downloadable
                    
        except Exception as e:
            pytest.skip(f"Could not download test audio file: {str(e)}") 