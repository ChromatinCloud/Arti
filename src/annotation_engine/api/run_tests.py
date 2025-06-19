#!/usr/bin/env python3
"""
Test runner for Annotation Engine API tests
"""

import subprocess
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run the complete test suite"""
    
    print("🧪 Running Annotation Engine API Test Suite...")
    print("=" * 60)
    
    # Set test environment
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    test_commands = [
        # Unit tests
        {
            "name": "Authentication Tests",
            "cmd": ["python", "-m", "pytest", "tests/test_auth.py", "-v"]
        },
        {
            "name": "Variant Processing Tests", 
            "cmd": ["python", "-m", "pytest", "tests/test_variants.py", "-v"]
        },
        {
            "name": "Clinical Case Tests",
            "cmd": ["python", "-m", "pytest", "tests/test_cases.py", "-v"]
        },
        {
            "name": "Job Management Tests",
            "cmd": ["python", "-m", "pytest", "tests/test_jobs.py", "-v"]
        },
        # Integration tests
        {
            "name": "Integration Tests",
            "cmd": ["python", "-m", "pytest", "tests/test_integration.py", "-v"]
        },
        # Full suite with coverage
        {
            "name": "Full Test Suite with Coverage",
            "cmd": ["python", "-m", "pytest", "tests/", "--cov=src/annotation_engine/api", "--cov-report=html", "--cov-report=term"]
        }
    ]
    
    results = {}
    
    for test in test_commands:
        print(f"\n📋 Running {test['name']}...")
        print("-" * 40)
        
        try:
            result = subprocess.run(
                test["cmd"],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            results[test["name"]] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if result.returncode == 0:
                print(f"✅ {test['name']} PASSED")
                print(result.stdout)
            else:
                print(f"❌ {test['name']} FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test['name']} TIMEOUT")
            results[test["name"]] = {"success": False, "error": "timeout"}
            
        except Exception as e:
            print(f"💥 {test['name']} ERROR: {e}")
            results[test["name"]] = {"success": False, "error": str(e)}
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        if result["success"]:
            print(f"✅ {test_name}")
            passed += 1
        else:
            print(f"❌ {test_name}")
            failed += 1
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("💔 Some tests failed. Check output above for details.")
        return False


def run_quick_tests():
    """Run just the essential tests quickly"""
    
    print("⚡ Running Quick Test Suite...")
    
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    cmd = [
        "python", "-m", "pytest", 
        "tests/test_auth.py::TestAuthEndpoints::test_login_success",
        "tests/test_variants.py::TestVariantEndpoints::test_get_variant_details_braf",
        "tests/test_cases.py::TestCaseEndpoints::test_list_cases_success",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Quick tests failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run API tests")
    parser.add_argument("--quick", action="store_true", help="Run quick test suite")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    
    args = parser.parse_args()
    
    if args.install_deps:
        print("📦 Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest-cov"])
    
    if args.quick:
        success = run_quick_tests()
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)