#!/usr/bin/env python3
"""
Simple test runner for standalone service tests
Usage: python run_tests.py [service_name]
"""

import subprocess
import sys
import os

def run_pytest_command(command_args):
    """Run pytest with nice formatting"""
    full_command = ["python", "-m", "pytest"] + command_args + ["-s", "-v"]
    
    print("🚀 Running:", " ".join(full_command))
    print("=" * 80)
    
    try:
        result = subprocess.run(full_command, check=True)
        print("\n✅ Tests completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Available test options:")
        print("  python run_tests.py vocabulary    # Test vocabulary service")
        print("  python run_tests.py grammar       # Test grammar service") 
        print("  python run_tests.py transcription # Test transcription service")
        print("  python run_tests.py fluency       # Test fluency service")
        print("  python run_tests.py audio         # Test audio service")
        print("  python run_tests.py pronunciation # Test pronunciation service")
        print("  python run_tests.py all           # Run all standalone tests")
        sys.exit(1)
    
    service = sys.argv[1].lower()
    
    if service == "vocabulary":
        run_pytest_command(["tests/standalone/test_vocabulary.py"])
    elif service == "grammar":
        run_pytest_command(["tests/standalone/test_grammar.py"])
    elif service == "transcription":
        run_pytest_command(["tests/standalone/test_transcription.py"])
    elif service == "fluency":
        run_pytest_command(["tests/standalone/test_fluency.py"])
    elif service == "audio":
        run_pytest_command(["tests/standalone/test_audio.py"])
    elif service == "pronunciation":
        run_pytest_command(["tests/standalone/test_pronunciation.py"])
    elif service == "all":
        run_pytest_command(["tests/standalone/"])
    else:
        print(f"Unknown service: {service}")
        print("Available options: vocabulary, grammar, transcription, fluency, audio, pronunciation, all")
        sys.exit(1)

if __name__ == "__main__":
    main() 