import pytest
import os
import aiohttp
import asyncio
from app.services.audio_service import AudioService


class TestAudioDownloadIntegration:
    """Integration tests for audio download operations"""

    @pytest.mark.asyncio
    async def test_download_valid_audio_file(self, test_audio_url):
        """Test downloading a valid audio file from Supabase"""
        audio_service = AudioService()
        
        # Download the file
        downloaded_path = await audio_service.download_audio(test_audio_url)
        
        try:
            # Verify file was created
            assert os.path.exists(downloaded_path)
            assert os.path.getsize(downloaded_path) > 0
            
            # Verify file extension
            assert downloaded_path.endswith('.webm')
            
        finally:
            # Cleanup
            if os.path.exists(downloaded_path):
                os.unlink(downloaded_path)

    @pytest.mark.asyncio
    async def test_download_invalid_url(self):
        """Test handling of invalid URLs"""
        audio_service = AudioService()
        invalid_url = "https://invalid-domain.com/nonexistent.webm"
        
        with pytest.raises(Exception) as exc_info:
            await audio_service.download_audio(invalid_url)
        
        assert "Failed to download audio" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_404_url(self):
        """Test handling of 404 URLs"""
        audio_service = AudioService()
        # Using valid domain but non-existent file
        not_found_url = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/nonexistent.webm"
        
        with pytest.raises(Exception) as exc_info:
            await audio_service.download_audio(not_found_url)
        
        assert "Failed to download audio" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_downloads(self, test_audio_url):
        """Test multiple concurrent downloads"""
        audio_service = AudioService()
        
        # Create multiple download tasks
        tasks = [
            audio_service.download_audio(test_audio_url)
            for _ in range(3)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        downloaded_files = []
        try:
            # Verify all downloads succeeded
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Download failed: {result}")
                
                assert os.path.exists(result)
                assert os.path.getsize(result) > 0
                downloaded_files.append(result)
            
        finally:
            # Cleanup all downloaded files
            for file_path in downloaded_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)

    @pytest.mark.asyncio
    async def test_download_file_cleanup_on_error(self):
        """Test that temp files are cleaned up when download fails"""
        audio_service = AudioService()
        
        # Mock a scenario where file creation succeeds but download fails
        import tempfile
        original_get = aiohttp.ClientSession.get
        
        async def mock_failing_get(self, url, **kwargs):
            # Let the temp file be created, then fail the request
            mock_response = aiohttp.ClientResponse(
                method="GET", 
                url=url,
                writer=None,
                continue100=None,
                timer=None,
                request_info=None,
                traces=[],
                loop=asyncio.get_event_loop(),
                session=self
            )
            mock_response.status = 500
            mock_response.reason = "Internal Server Error"
            return mock_response
        
        # Count temp files before
        temp_dir = tempfile.gettempdir()
        temp_files_before = len([f for f in os.listdir(temp_dir) if f.startswith('tmp')])
        
        with pytest.raises(Exception):
            await audio_service.download_audio("https://example.com/test.webm")
        
        # Verify no temp files were left behind
        temp_files_after = len([f for f in os.listdir(temp_dir) if f.startswith('tmp')])
        
        # Should be the same or less (in case other processes cleaned up)
        assert temp_files_after <= temp_files_before 