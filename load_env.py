#!/usr/bin/env python3
"""
Load environment variables from .env file
"""

import os
from pathlib import Path

def load_env():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("⚠️  No .env file found. Please create one based on .env.example")
        return False
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    return True

if __name__ == '__main__':
    if load_env():
        print("✅ Environment variables loaded from .env")
        
        # Check required keys
        required_keys = ['SUPABASE_URL', 'SUPABASE_KEY', 'OPENAI_API_KEY']
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
        else:
            print("🎉 All required keys present!")
    else:
        print("❌ Failed to load environment variables")