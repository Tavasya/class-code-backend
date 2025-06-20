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
        print()
        print("🔧 STANDALONE SERVICE TESTS:")
        print("  python run_tests.py vocabulary    # Test vocabulary service")
        print("  python run_tests.py grammar       # Test grammar service") 
        print("  python run_tests.py transcription # Test transcription service")
        print("  python run_tests.py fluency       # Test fluency service")
        print("  python run_tests.py audio         # Test audio service")
        print("  python run_tests.py pronunciation # Test pronunciation service")
        print()
        print("🌐 API INTEGRATION TESTS:")
        print("  python run_tests.py api-health     # Test health endpoint")
        print("  python run_tests.py api-submission # Test submission endpoint")
        print("  python run_tests.py api-analysis   # Test analysis endpoints")
        print("  python run_tests.py api-all        # Test all API endpoints")
        print()
        print("📦 TEST SUITES:")
        print("  python run_tests.py standalone     # All standalone service tests")
        print("  python run_tests.py api            # All API integration tests")
        print("  python run_tests.py all            # Everything (standalone + API)")
        sys.exit(1)
    
    service = sys.argv[1].lower()
    
    # Standalone service tests
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
    
    # API integration tests
    elif service == "api-health":
        run_pytest_command(["tests/api/test_health_endpoint.py"])
    elif service == "api-submission":
        run_pytest_command(["tests/api/test_submission_endpoint.py"])
    elif service == "api-analysis":
        run_pytest_command(["tests/api/test_analysis_endpoints.py"])
    elif service == "api-all":
        run_pytest_command(["tests/api/"])
    
    # Test suites
    elif service == "standalone":
        run_pytest_command(["tests/standalone/"])
    elif service == "api":
        run_pytest_command(["tests/api/"])
    elif service == "all":
        run_pytest_command(["tests/"])
    else:
        print(f"Unknown test option: {service}")
        print("Run 'python run_tests.py' without arguments to see available options.")
        sys.exit(1)

if __name__ == "__main__":
    main() 