"""
Simple fixtures for external API integration tests.
"""
import pytest
import os
import tempfile
import wave
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@pytest.fixture
def test_audio_file():
    """Create a simple test audio file."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        # Generate simple audio
        sample_rate = 16000
        duration = 2
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        with wave.open(temp_file.name, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        yield temp_file.name
        
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass


@pytest.fixture
def skip_if_no_api_keys():
    """Skip test if API keys are not available."""
    required_keys = ["ASSEMBLYAI_API_KEY", "AZURE_SPEECH_KEY", "OPENAI_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        pytest.skip(f"Missing API keys: {missing_keys}")


@pytest.fixture
def test_audio_url():
    """Valid audio URL from your Supabase storage."""
    return "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/e6b419e8-6ae8-4365-afc5-2a111b8a6479/9c2301fe-fa6c-4860-9c59-faa1483b8f88/e6b419e8-6ae8-4365-afc5-2a111b8a6479_9c2301fe-fa6c-4860-9c59-faa1483b8f88_card-1_1747880119202.webm" 