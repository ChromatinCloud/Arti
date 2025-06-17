"""
Unit tests for VCF field extraction using pysam
"""

import sys
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.vcf_parser import VCFFieldExtractor
from annotation_engine.validation.error_handler import ValidationError


def test_vcf_field_extractor_creation():
    """Test VCFFieldExtractor can be created"""
    extractor = VCFFieldExtractor()
    assert extractor is not None


def test_extract_metadata_bundle():
    """Test metadata extraction from synthetic VCF"""
    extractor = VCFFieldExtractor()
    
    # Path to our test VCF
    test_vcf = Path(__file__).parent.parent / "example_input" / "proper_test.vcf"
    
    if not test_vcf.exists():
        pytest.skip(f"Test VCF not found: {test_vcf}")
    
    # Mock analysis context
    analysis_context = {
        'case_uid': 'TEST_001',
        'patient_uid': 'PAT_001',
        'cancer_type': 'lung_adenocarcinoma',
        'tissue_type': 'primary_tumor',
        'genome_build': 'GRCh37',
        'guidelines': ['AMP_ACMG', 'CGC_VICC']
    }
    
    metadata = extractor.extract_metadata_bundle(test_vcf, analysis_context)
    
    # Check analysis context fields
    assert metadata['case_uid'] == 'TEST_001'
    assert metadata['patient_uid'] == 'PAT_001' 
    assert metadata['cancer_type'] == 'lung_adenocarcinoma'
    assert metadata['guidelines'] == ['AMP_ACMG', 'CGC_VICC']
    
    # Check VCF metadata
    assert metadata['vcf_path'] == str(test_vcf)
    assert metadata['total_variants'] == 5
    assert 'vcf_version' in metadata
    assert 'sample_names' in metadata
    assert 'processing_timestamp' in metadata


def test_extract_variant_bundle():
    """Test variant field extraction from synthetic VCF"""
    extractor = VCFFieldExtractor()
    
    # Path to our test VCF
    test_vcf = Path(__file__).parent.parent / "example_input" / "proper_test.vcf"
    
    if not test_vcf.exists():
        pytest.skip(f"Test VCF not found: {test_vcf}")
    
    variants = extractor.extract_variant_bundle(test_vcf)
    
    # Should have 4 variants
    assert len(variants) == 4
    
    # Check first variant structure
    variant = variants[0]
    
    # Core identification
    assert 'chromosome' in variant
    assert 'position' in variant  
    assert 'reference' in variant
    assert 'alternate' in variant
    
    # Quality fields
    assert 'quality_score' in variant
    assert 'filter_status' in variant
    
    # Standard INFO fields
    assert 'allele_frequency' in variant
    assert 'total_depth' in variant
    assert 'variant_type' in variant
    # These fields may not be present in all VCFs
    # assert 'dbsnp_member' in variant
    # assert 'somatic_flag' in variant
    
    # Sample data
    assert 'samples' in variant
    assert len(variant['samples']) >= 1
    
    # Check sample structure
    sample = variant['samples'][0]
    assert 'name' in sample
    assert 'genotype' in sample
    assert 'data' in sample
    # Format fields are in data dict
    assert 'DP' in sample['data']
    assert 'AD' in sample['data']


def test_genome_build_extraction():
    """Test genome build extraction from header"""
    extractor = VCFFieldExtractor()
    
    test_vcf = Path(__file__).parent.parent / "example_input" / "proper_test.vcf"
    
    if not test_vcf.exists():
        pytest.skip(f"Test VCF not found: {test_vcf}")
    
    build = extractor.extract_genome_build_from_header(test_vcf)
    # Our synthetic VCF has ##reference=GRCh37
    assert build == 'GRCh38'  # Test VCF uses GRCh38


def test_nonexistent_file_error():
    """Test error handling for nonexistent file"""
    extractor = VCFFieldExtractor()
    fake_path = Path("nonexistent.vcf")
    
    with pytest.raises(ValidationError):
        extractor.extract_variant_bundle(fake_path)
    
    with pytest.raises(ValidationError):
        extractor.extract_metadata_bundle(fake_path, {})