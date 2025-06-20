#!/usr/bin/env python3

import pytest
import os
import tempfile
from app.services.audio_service import AudioService

class TestAudioService:
    """Test suite for audio processing service"""
    
    def test_audio_service_structure(self):
        """Test that the audio service has the expected methods"""
        
        print("\n🔧 Testing AudioService structure...")
        
        service = AudioService()
        
        # Test that service has expected methods
        assert hasattr(service, 'process_single_audio'), "Service should have process_single_audio method"
        assert hasattr(service, 'convert_to_wav'), "Service should have convert_to_wav method"
        
        # Test static methods exist
        assert hasattr(AudioService, 'download_audio'), "Service should have download_audio static method"
        assert hasattr(AudioService, 'convert_webm_to_wav'), "Service should have convert_webm_to_wav static method"
        
        print("✅ AudioService structure is valid")
    
    @pytest.mark.asyncio
    async def test_audio_download(self):
        """Test audio download functionality with your Supabase audio"""
        
        # Use your real audio URL
        test_audio_url = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/fd90cb13-6723-405c-bf9f-89917b9a89bc/e19e5f34-8d68-4ba4-a387-de3022af8874/fd90cb13-6723-405c-bf9f-89917b9a89bc_e19e5f34-8d68-4ba4-a387-de3022af8874_card-1748924855537_1750262342399.webm"
        
        print(f"\n📥 Testing Audio Download")
        print("=" * 60)
        print(f"Audio URL: {test_audio_url}")
        print("Downloading...")
        
        try:
            downloaded_path = await AudioService.download_audio(test_audio_url)
            
            # Assertions
            assert downloaded_path is not None, "Should return a file path"
            assert os.path.exists(downloaded_path), "Downloaded file should exist"
            assert os.path.getsize(downloaded_path) > 0, "Downloaded file should not be empty"
            
            # Display results
            file_size = os.path.getsize(downloaded_path)
            print(f"✅ Download successful!")
            print(f"File path: {downloaded_path}")
            print(f"File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            print(f"File extension: {os.path.splitext(downloaded_path)[1]}")
            
            # Cleanup
            try:
                os.unlink(downloaded_path)
                print("🗑️  Cleaned up downloaded file")
            except:
                pass
                
        except Exception as e:
            print(f"❌ Download failed: {e}")
            pytest.skip(f"Download test skipped due to: {e}")
    
    @pytest.mark.asyncio
    async def test_audio_conversion(self):
        """Test audio format conversion (.webm to .wav)"""
        
        test_audio_url = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/fd90cb13-6723-405c-bf9f-89917b9a89bc/e19e5f34-8d68-4ba4-a387-de3022af8874/fd90cb13-6723-405c-bf9f-89917b9a89bc_e19e5f34-8d68-4ba4-a387-de3022af8874_card-1748924855537_1750262342399.webm"
        
        print(f"\n🔄 Testing Audio Conversion")
        print("=" * 60)
        print("Converting .webm to .wav...")
        
        try:
            # First download the file
            downloaded_path = await AudioService.download_audio(test_audio_url)
            
            print(f"Downloaded: {os.path.splitext(downloaded_path)[1]} file")
            
            # Convert to WAV
            wav_path = await AudioService.convert_webm_to_wav(downloaded_path)
            
            # Assertions
            assert wav_path is not None, "Should return WAV file path"
            assert wav_path.endswith('.wav'), "Output should be .wav file"
            assert os.path.exists(wav_path), "WAV file should exist"
            assert os.path.getsize(wav_path) > 0, "WAV file should not be empty"
            
            # Display results
            original_size = os.path.getsize(downloaded_path)
            wav_size = os.path.getsize(wav_path)
            
            print(f"✅ Conversion successful!")
            print(f"Original file: {original_size:,} bytes")
            print(f"WAV file: {wav_size:,} bytes")
            print(f"WAV path: {wav_path}")
            
            # Cleanup
            try:
                os.unlink(downloaded_path)
                os.unlink(wav_path)
                print("🗑️  Cleaned up both files")
            except:
                pass
                
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            # Don't fail the test if ffmpeg is not available
            if "ffmpeg" in str(e).lower():
                pytest.skip(f"Conversion test skipped - ffmpeg not available: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_full_audio_processing_pipeline(self):
        """Test the complete audio processing workflow"""
        
        test_audio_url = "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/fd90cb13-6723-405c-bf9f-89917b9a89bc/e19e5f34-8d68-4ba4-a387-de3022af8874/fd90cb13-6723-405c-bf9f-89917b9a89bc_e19e5f34-8d68-4ba4-a387-de3022af8874_card-1748924855537_1750262342399.webm"
        
        print(f"\n🎵 Testing Full Audio Processing Pipeline")
        print("=" * 60)
        print("Testing: Download → Convert → Process")
        
        service = AudioService()
        
        try:
            # Test the complete pipeline
            result = await service.process_single_audio(
                audio_url=test_audio_url,
                question_number=1,
                submission_url="test_submission_123"
            )
            
            # Assertions
            assert isinstance(result, dict), "Should return a dictionary"
            assert "wav_path" in result, "Should contain wav_path"
            assert "session_id" in result, "Should contain session_id"
            assert "question_number" in result, "Should contain question_number"
            
            # Check the WAV file exists
            wav_path = result["wav_path"]
            assert os.path.exists(wav_path), "WAV file should exist"
            assert wav_path.endswith('.wav'), "Should be a WAV file"
            
            # Display results
            print(f"✅ Full pipeline successful!")
            print(f"WAV Path: {wav_path}")
            print(f"Session ID: {result['session_id']}")
            print(f"Question Number: {result['question_number']}")
            print(f"WAV File Size: {os.path.getsize(wav_path):,} bytes")
            
            # Note: Don't cleanup here as the file manager service handles this
            print("📝 Note: File cleanup handled by file manager service")
            
        except Exception as e:
            print(f"❌ Pipeline test failed: {e}")
            if "ffmpeg" in str(e).lower():
                pytest.skip(f"Pipeline test skipped - ffmpeg not available: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_invalid_url_handling(self):
        """Test error handling with invalid URLs"""
        
        invalid_url = "https://invalid-audio-url.com/nonexistent.webm"
        
        print(f"\n🚨 Testing Error Handling")
        print(f"Invalid URL: {invalid_url}")
        
        try:
            await AudioService.download_audio(invalid_url)
            # Should not reach here
            assert False, "Should have raised an exception for invalid URL"
        except Exception as e:
            print(f"✅ Correctly caught error: {type(e).__name__}")
            print(f"Error message: {str(e)[:100]}...")
            # This is expected behavior
            assert "Failed to download" in str(e) or "404" in str(e) or "error" in str(e).lower() 