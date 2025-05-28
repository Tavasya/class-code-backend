"""
Shared pytest configuration for API and Integration tests.
This file provides common fixtures and setup for CI/CD environments.
"""

import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Generator, Dict, Any

# Test environment detection
IS_CI = os.getenv("CI", "false").lower() == "true"
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"
IS_INTEGRATION_TEST = os.getenv("INTEGRATION_TEST", "false").lower() == "true"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_environment() -> Dict[str, Any]:
    """Provide test environment configuration."""
    return {
        "is_ci": IS_CI,
        "is_testing": IS_TESTING,
        "is_integration_test": IS_INTEGRATION_TEST,
        "environment": os.getenv("ENVIRONMENT", "test"),
    }

@pytest.fixture(scope="function")
def temp_test_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp(prefix="test_")
    temp_path = Path(temp_dir)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch) -> Dict[str, str]:
    """Set up mock environment variables for testing."""
    test_env = {
        "TESTING": "true",
        "ENVIRONMENT": "test",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_supabase_key",
        "OPENAI_API_KEY": "test_openai_key",
        "AZURE_SPEECH_KEY": "test_azure_key",
        "AZURE_SPEECH_REGION": "test_region",
        "ASSEMBLYAI_API_KEY": "test_assembly_key",
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env

@pytest.fixture(scope="function")
def mock_external_apis():
    """Mock external API clients for testing."""
    mocks = {
        "openai_client": Mock(),
        "azure_speech_client": Mock(),
        "assemblyai_client": Mock(),
        "supabase_client": Mock(),
    }
    
    # Configure mock responses
    mocks["openai_client"].chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[Mock(message=Mock(content="Mock OpenAI response"))]
        )
    )
    
    mocks["azure_speech_client"].recognize_once_async = AsyncMock(
        return_value=Mock(text="Mock Azure Speech response")
    )
    
    mocks["assemblyai_client"].transcribe = AsyncMock(
        return_value=Mock(text="Mock AssemblyAI response")
    )
    
    return mocks

@pytest.fixture(scope="function")
def skip_if_no_api_keys():
    """Skip tests that require real API keys if they're not available."""
    required_keys = [
        "OPENAI_API_KEY",
        "AZURE_SPEECH_KEY", 
        "ASSEMBLYAI_API_KEY"
    ]
    
    missing_keys = []
    for key in required_keys:
        value = os.getenv(key)
        if not value or value.startswith("test_"):
            missing_keys.append(key)
    
    if missing_keys and IS_CI:
        pytest.skip(f"Skipping test - missing API keys: {', '.join(missing_keys)}")

@pytest.fixture(scope="function")
def mock_file_operations(temp_test_dir):
    """Mock file operations for testing."""
    def create_test_file(filename: str, content: bytes = b"test content") -> Path:
        file_path = temp_test_dir / filename
        file_path.write_bytes(content)
        return file_path
    
    def create_test_audio_file(filename: str = "test_audio.wav") -> Path:
        # Create a minimal WAV file for testing
        wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
        audio_data = b'\x00\x00' * 1000  # Simple silence
        return create_test_file(filename, wav_header + audio_data)
    
    return {
        "create_test_file": create_test_file,
        "create_test_audio_file": create_test_audio_file,
        "temp_dir": temp_test_dir,
    }

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )
    config.addinivalue_line(
        "markers", "external_api: mark test as requiring external API"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment."""
    # Skip external API tests in CI if no real API keys
    if IS_CI:
        skip_external = pytest.mark.skip(reason="External API tests skipped in CI without real keys")
        for item in items:
            if "external_api" in item.keywords:
                # Check if we have real API keys
                has_real_keys = all(
                    os.getenv(key) and not os.getenv(key).startswith("test_")
                    for key in ["OPENAI_API_KEY", "AZURE_SPEECH_KEY", "ASSEMBLYAI_API_KEY"]
                )
                if not has_real_keys:
                    item.add_marker(skip_external)

# Test session setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """Set up the test session."""
    print(f"\n🧪 Starting test session - Environment: {os.getenv('ENVIRONMENT', 'test')}")
    print(f"📍 CI Environment: {IS_CI}")
    print(f"🔧 Integration Tests: {IS_INTEGRATION_TEST}")
    
    yield
    
    print("\n✅ Test session completed")

# Cleanup fixtures
@pytest.fixture(scope="function", autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts after each test."""
    yield
    
    # Clean up any temporary files or resources
    temp_dirs = [
        "/tmp/test_audio_files",
        "/tmp/test_uploads",
        "/tmp/pytest_temp",
    ]
    
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True) 