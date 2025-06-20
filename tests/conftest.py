import pytest
import sys
import os

# Add the app directory to Python path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set pytest-asyncio configuration
pytest_plugins = ('pytest_asyncio',)

def pytest_configure(config):
    """Configure pytest settings"""
    # Set asyncio mode to avoid warnings
    config.option.asyncio_mode = "auto" 