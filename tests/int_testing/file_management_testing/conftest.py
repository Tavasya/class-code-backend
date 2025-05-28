import pytest
import tempfile
import os
import asyncio
from unittest.mock import AsyncMock
from app.services.file_manager_service import file_manager
from app.services.audio_service import AudioService


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def audio_service():
    """AudioService instance for testing"""
    return AudioService()


@pytest.fixture
def test_audio_url():
    """Test audio URL from Supabase storage - confirmed working WebM file"""
    return "https://drcsbokflpzbhuzsksws.supabase.co/storage/v1/object/public/recordings/recordings/e6b419e8-6ae8-4365-afc5-2a111b8a6479/9c2301fe-fa6c-4860-9c59-faa1483b8f88/e6b419e8-6ae8-4365-afc5-2a111b8a6479_9c2301fe-fa6c-4860-9c59-faa1483b8f88_card-1_1747880119202.webm"


@pytest.fixture
def submission_url():
    """Test submission URL - corresponds to existing database record"""
    return "def91efd-8659-4409-b8ac-b5f3f4906990"


@pytest.fixture
def test_wav_content():
    """Create minimal WAV file content for testing"""
    # Minimal WAV header + some audio data
    wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    return wav_header


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 