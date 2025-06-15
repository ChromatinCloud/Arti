"""
Basic unit tests for CLI validation
"""

import sys
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.validation.vcf_validator import VCFValidator
from annotation_engine.validation.error_handler import ValidationError


def test_vcf_validator_creation():
    """Test VCFValidator can be created"""
    validator = VCFValidator()
    assert validator is not None
    assert hasattr(validator, 'quality_thresholds')


def test_vcf_validator_with_synthetic_file():
    """Test VCF validation with our synthetic test file"""
    validator = VCFValidator()
    
    # Path to our test VCF
    test_vcf = Path(__file__).parent.parent / "example_input" / "synthetic_test.vcf"
    
    if not test_vcf.exists():
        pytest.skip(f"Test VCF not found: {test_vcf}")
    
    # Should validate successfully
    results = validator.validate_file(test_vcf)
    
    assert results['valid_format'] is True
    assert results['total_variants'] == 4
    assert 'SNV' in results['variant_types']
    assert results['variant_types']['SNV'] == 4


def test_vcf_validator_nonexistent_file():
    """Test VCF validator with nonexistent file"""
    validator = VCFValidator()
    fake_path = Path("nonexistent.vcf")
    
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_file(fake_path)
    
    assert exc_info.value.error_type == "file_not_found"


def test_imports_work():
    """Test that all our modules can be imported"""
    from annotation_engine.validation.input_schemas import CLIInputSchema
    from annotation_engine.validation.error_handler import CLIErrorHandler
    from annotation_engine.cli import AnnotationEngineCLI
    
    # Basic instantiation tests
    cli = AnnotationEngineCLI()
    assert cli is not None
    
    error_handler = CLIErrorHandler()
    assert error_handler is not None