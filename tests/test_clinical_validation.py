"""
Legacy Clinical Validation Tests - DEPRECATED

These tests have been replaced by test_clinical_validation_di.py
which uses the new clean dependency injection pattern.

This file is kept for reference but all tests are skipped.
To run the clinical validation tests, use:
    pytest tests/test_clinical_validation_di.py
"""

import pytest

pytestmark = pytest.mark.skip(reason="Replaced by test_clinical_validation_di.py - use dependency injection tests instead")

# Original tests are preserved in test_clinical_validation_legacy.py.bak