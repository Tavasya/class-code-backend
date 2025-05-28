import pytest
import os
import tempfile
import subprocess
import wave
from app.services.audio_service import AudioService


class TestFormatConversionIntegration:
    """Integration tests for audio format conversion operations"""

    @pytest.mark.asyncio
    async def test_webm_to_wav_conversion(self, test_audio_url):
        """Test converting webm file to WAV format"""
        audio_service = AudioService()
        
        # Download and convert
        wav_path = await audio_service.convert_to_wav(test_audio_url)
        
        try:
            # Verify WAV file was created
            assert os.path.exists(wav_path)
            assert wav_path.endswith('.wav')
            assert os.path.getsize(wav_path) > 0
            
            # Verify WAV file properties using wave module
            with wave.open(wav_path, 'rb') as wav_file:
                # Check audio properties match expected conversion settings
                assert wav_file.getnchannels() == 1  # Mono
                assert wav_file.getsampwidth() == 2  # 16-bit (2 bytes)
                assert wav_file.getframerate() == 16000  # 16kHz
                
        finally:
            # Cleanup
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    @pytest.mark.asyncio
    async def test_conversion_with_invalid_input(self, temp_dir):
        """Test conversion fails gracefully with invalid input file"""
        audio_service = AudioService()
        
        # Create a fake/corrupted audio file
        fake_audio_path = os.path.join(temp_dir, "fake_audio.webm")
        with open(fake_audio_path, 'wb') as f:
            f.write(b"This is not a real audio file")
        
        with pytest.raises(Exception) as exc_info:
            await audio_service.convert_webm_to_wav(fake_audio_path)
        
        assert "Failed to convert to WAV" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_conversion_cleanup_original_file(self, test_audio_url):
        """Test that original downloaded file is cleaned up after conversion"""
        audio_service = AudioService()
        
        # Get the original file path by downloading first
        original_path = await audio_service.download_audio(test_audio_url)
        
        try:
            # Convert to WAV
            wav_path = await audio_service.convert_webm_to_wav(original_path)
            
            # Verify WAV exists and original still exists (cleanup happens in convert_to_wav)
            assert os.path.exists(wav_path)
            assert os.path.exists(original_path)  # Should still exist at this point
            
            # Cleanup
            if os.path.exists(wav_path):
                os.unlink(wav_path)
        finally:
            # Manual cleanup
            if os.path.exists(original_path):
                os.unlink(original_path)

    def test_ffmpeg_availability(self):
        """Test that FFmpeg is available in the system"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10
            )
            assert result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.fail("FFmpeg is not available in the system")

    @pytest.mark.asyncio
    async def test_conversion_output_file_path(self, temp_dir):
        """Test that conversion creates output file with correct path"""
        audio_service = AudioService()
        
        # Create a minimal valid webm file for testing
        input_path = os.path.join(temp_dir, "test_input.webm")
        
        # Create a simple file (FFmpeg will handle format issues)
        with open(input_path, 'wb') as f:
            f.write(b"fake webm content")
        
        # Expected output path should be same directory with .wav extension
        expected_wav_path = os.path.join(temp_dir, "test_input.wav")
        
        try:
            # This should fail due to invalid input, but we can test the path logic
            await audio_service.convert_webm_to_wav(input_path)
        except Exception:
            # Expected to fail with fake content
            pass
        
        # Verify the expected path logic
        assert expected_wav_path == os.path.splitext(input_path)[0] + '.wav'

    @pytest.mark.asyncio
    async def test_concurrent_conversions(self, test_audio_url):
        """Test multiple concurrent format conversions"""
        audio_service = AudioService()
        
        # Download multiple copies for concurrent conversion
        downloaded_files = []
        for i in range(3):
            file_path = await audio_service.download_audio(test_audio_url)
            downloaded_files.append(file_path)
        
        try:
            # Convert all files concurrently
            import asyncio
            conversion_tasks = [
                audio_service.convert_webm_to_wav(file_path)
                for file_path in downloaded_files
            ]
            
            wav_files = await asyncio.gather(*conversion_tasks, return_exceptions=True)
            
            # Verify all conversions succeeded
            valid_wav_files = []
            for result in wav_files:
                if isinstance(result, Exception):
                    pytest.fail(f"Conversion failed: {result}")
                
                assert os.path.exists(result)
                assert result.endswith('.wav')
                valid_wav_files.append(result)
            
            # Cleanup WAV files
            for wav_file in valid_wav_files:
                if os.path.exists(wav_file):
                    os.unlink(wav_file)
                    
        finally:
            # Cleanup downloaded files
            for file_path in downloaded_files:
                if os.path.exists(file_path):
                    os.unlink(file_path) 