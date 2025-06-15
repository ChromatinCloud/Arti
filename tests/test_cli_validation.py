"""
Unit tests for CLI validation module

Tests implement→test→implement→test cycle for robust development
using our example VCF files for realistic testing scenarios.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from annotation_engine.cli import AnnotationEngineCLI
from annotation_engine.validation.input_schemas import CLIInputSchema, AnalysisRequest
from annotation_engine.validation.vcf_validator import VCFValidator
from annotation_engine.validation.error_handler import ValidationError


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.cli = AnnotationEngineCLI()
        self.parser = self.cli.create_parser()
        
        # Path to our example files
        self.example_dir = Path(__file__).parent.parent / "example_input"
        self.synthetic_vcf = self.example_dir / "synthetic_test.vcf"
        self.malformed_vcf = self.example_dir / "malformed_test.vcf"
    
    def test_minimal_valid_arguments(self):
        """Test minimal valid argument set"""
        args = self.parser.parse_args([
            '--input', str(self.synthetic_vcf),
            '--case-uid', 'TEST_CASE_001',
            '--cancer-type', 'lung_adenocarcinoma'
        ])
        
        assert args.input == self.synthetic_vcf
        assert args.case_uid == 'TEST_CASE_001'
        assert args.cancer_type == 'lung_adenocarcinoma'
        assert args.patient_uid is None  # Should default to case_uid
        assert args.output == Path('./results')
    
    def test_comprehensive_arguments(self):
        """Test full argument set"""
        args = self.parser.parse_args([
            '--input', str(self.synthetic_vcf),
            '--case-uid', 'CASE_001',
            '--patient-uid', 'PAT_001',
            '--cancer-type', 'breast_cancer',
            '--oncotree-id', 'BRCA',
            '--tissue-type', 'metastatic',
            '--output', '/tmp/test_output',
            '--output-format', 'json',
            '--genome', 'GRCh38',
            '--guidelines', 'AMP_ACMG', 'CGC_VICC',
            '--min-depth', '20',
            '--min-vaf', '0.1',
            '--verbose', '-v'
        ])
        
        assert args.case_uid == 'CASE_001'
        assert args.patient_uid == 'PAT_001'
        assert args.cancer_type == 'breast_cancer'
        assert args.oncotree_id == 'BRCA'
        assert args.tissue_type == 'metastatic'
        assert args.output == Path('/tmp/test_output')
        assert args.output_format == 'json'
        assert args.genome == 'GRCh38'
        assert args.guidelines == ['AMP_ACMG', 'CGC_VICC']
        assert args.min_depth == 20
        assert args.min_vaf == 0.1
        assert args.verbose == 2
    
    def test_api_mode_argument(self):
        """Test API mode argument"""
        args = self.parser.parse_args([
            '--api-mode',
            '--case-uid', 'API_TEST',
            '--cancer-type', 'other'
        ])
        
        assert args.api_mode is True
        assert args.input is None
    
    def test_missing_required_arguments(self):
        """Test error handling for missing required arguments"""
        with pytest.raises(SystemExit):
            self.parser.parse_args(['--input', str(self.synthetic_vcf)])
        
        with pytest.raises(SystemExit):
            self.parser.parse_args(['--case-uid', 'TEST'])
    
    def test_invalid_cancer_type(self):
        """Test invalid cancer type rejection"""
        with pytest.raises(SystemExit):
            self.parser.parse_args([
                '--input', str(self.synthetic_vcf),
                '--case-uid', 'TEST',
                '--cancer-type', 'invalid_cancer_type'
            ])
    
    def test_invalid_genome_build(self):
        """Test invalid genome build rejection"""
        with pytest.raises(SystemExit):
            self.parser.parse_args([
                '--input', str(self.synthetic_vcf),
                '--case-uid', 'TEST',
                '--cancer-type', 'lung_adenocarcinoma',
                '--genome', 'hg19'  # Should be GRCh37 or GRCh38
            ])


class TestInputSchemaValidation:
    """Test Pydantic schema validation"""
    
    def test_valid_cli_input_schema(self):
        """Test valid CLI input schema validation"""
        test_data = {
            'input': Path('test.vcf'),
            'case_uid': 'CASE_001',
            'patient_uid': 'PAT_001',
            'cancer_type': 'lung_adenocarcinoma',
            'oncotree_id': 'LUAD',
            'tissue_type': 'primary_tumor',
            'output': Path('./results'),
            'output_format': 'all',
            'genome': 'GRCh37',
            'guidelines': ['AMP_ACMG', 'CGC_VICC'],
            'min_depth': 10,
            'min_vaf': 0.05,
            'skip_qc': False,
            'verbose': 1,
            'quiet': False
        }
        
        schema = CLIInputSchema.model_validate(test_data)
        assert schema.case_uid == 'CASE_001'
        assert schema.cancer_type == 'lung_adenocarcinoma'
        assert schema.min_depth == 10
        assert len(schema.guidelines) == 2
    
    def test_invalid_case_uid_format(self):
        """Test invalid case UID format rejection"""
        test_data = {
            'case_uid': 'CASE@001',  # Invalid character
            'cancer_type': 'lung_adenocarcinoma',
            'output': Path('./results'),
            'guidelines': ['AMP_ACMG']
        }
        
        with pytest.raises(ValueError, match="must contain only alphanumeric"):
            CLIInputSchema.model_validate(test_data)
    
    def test_invalid_vcf_extension(self):
        """Test invalid VCF file extension rejection"""
        test_data = {
            'input': Path('test.txt'),  # Invalid extension
            'case_uid': 'CASE_001',
            'cancer_type': 'lung_adenocarcinoma',
            'guidelines': ['AMP_ACMG']
        }
        
        with pytest.raises(ValueError, match="must be .vcf or .vcf.gz"):
            CLIInputSchema.model_validate(test_data)
    
    def test_patient_uid_defaults_to_case_uid(self):
        """Test patient_uid defaulting behavior"""
        cli = AnnotationEngineCLI()
        
        # Simulate args without patient_uid
        args_dict = {
            'input': Path('test.vcf'),
            'case_uid': 'CASE_001',
            'patient_uid': None,
            'cancer_type': 'lung_adenocarcinoma',
            'guidelines': ['AMP_ACMG']
        }
        
        # This mimics the behavior in validate_arguments
        if not args_dict.get('patient_uid'):
            args_dict['patient_uid'] = args_dict['case_uid']
        
        schema = CLIInputSchema.model_validate(args_dict)
        assert schema.patient_uid == 'CASE_001'
    
    def test_quality_filter_validation(self):
        """Test quality filter parameter validation"""
        # Test min_depth bounds
        with pytest.raises(ValueError):
            CLIInputSchema.model_validate({
                'case_uid': 'TEST',
                'cancer_type': 'lung_adenocarcinoma',
                'min_depth': 0  # Too low
            })
        
        with pytest.raises(ValueError):
            CLIInputSchema.model_validate({
                'case_uid': 'TEST',
                'cancer_type': 'lung_adenocarcinoma',
                'min_depth': 1001  # Too high
            })
        
        # Test min_vaf bounds
        with pytest.raises(ValueError):
            CLIInputSchema.model_validate({
                'case_uid': 'TEST',
                'cancer_type': 'lung_adenocarcinoma',
                'min_vaf': -0.1  # Negative
            })
        
        with pytest.raises(ValueError):
            CLIInputSchema.model_validate({
                'case_uid': 'TEST',
                'cancer_type': 'lung_adenocarcinoma',
                'min_vaf': 1.1  # Too high
            })


class TestVCFValidation:
    """Test VCF file validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = VCFValidator()
        self.example_dir = Path(__file__).parent.parent / "example_input"
        self.synthetic_vcf = self.example_dir / "synthetic_test.vcf"
        self.malformed_vcf = self.example_dir / "malformed_test.vcf"
    
    def test_validate_synthetic_vcf(self):
        """Test validation of our synthetic VCF file"""
        if not self.synthetic_vcf.exists():
            pytest.skip(f"Synthetic VCF not found: {self.synthetic_vcf}")
        
        results = self.validator.validate_file(self.synthetic_vcf)
        
        assert results['valid_format'] is True
        assert results['total_variants'] == 4
        assert 'TP53' in str(results)  # Should contain TP53 variants
        assert results['file_path'] == str(self.synthetic_vcf)
        assert results['compressed'] is False
    
    def test_validate_malformed_vcf(self):
        """Test validation of malformed VCF file"""
        if not self.malformed_vcf.exists():
            pytest.skip(f"Malformed VCF not found: {self.malformed_vcf}")
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_file(self.malformed_vcf)
        
        error = exc_info.value
        assert error.error_type == "invalid_vcf_format"
        assert "critical errors" in error.message
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent file"""
        fake_path = Path("nonexistent_file.vcf")
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_file(fake_path)
        
        error = exc_info.value
        assert error.error_type == "file_not_found"
        assert str(fake_path) in error.message
    
    def test_empty_file(self):
        """Test handling of empty file"""
        with tempfile.NamedTemporaryFile(suffix='.vcf', delete=False) as tmp:
            empty_file = Path(tmp.name)
        
        try:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate_file(empty_file)
            
            error = exc_info.value
            assert error.error_type == "empty_file"
        finally:
            empty_file.unlink()
    
    def test_compressed_vcf_handling(self):
        """Test handling of compressed VCF files"""
        # Create a simple compressed VCF for testing
        import gzip
        
        vcf_content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	1000	.	A	T	100	PASS	DP=50
"""
        
        with tempfile.NamedTemporaryFile(suffix='.vcf.gz', delete=False) as tmp:
            compressed_file = Path(tmp.name)
            
        with gzip.open(compressed_file, 'wt') as f:
            f.write(vcf_content)
        
        try:
            results = self.validator.validate_file(compressed_file)
            assert results['valid_format'] is True
            assert results['compressed'] is True
            assert results['total_variants'] == 1
        finally:
            compressed_file.unlink()


class TestAnalysisRequestCreation:
    """Test analysis request creation from validated inputs"""
    
    def test_create_analysis_request(self):
        """Test creating analysis request from validated inputs"""
        cli = AnnotationEngineCLI()
        
        # Create mock validated input
        validated_input = CLIInputSchema.model_validate({
            'input': Path('test.vcf'),
            'case_uid': 'CASE_001',
            'patient_uid': 'PAT_001',
            'cancer_type': 'lung_adenocarcinoma',
            'oncotree_id': 'LUAD',
            'tissue_type': 'primary_tumor',
            'output': Path('./results'),
            'output_format': 'json',
            'genome': 'GRCh37',
            'guidelines': ['AMP_ACMG', 'CGC_VICC'],
            'min_depth': 15,
            'min_vaf': 0.1,
            'skip_qc': False,
            'verbose': 1
        })
        
        # Mock VCF validation results
        vcf_validation = {
            'valid_format': True,
            'total_variants': 10,
            'variant_types': {'SNV': 8, 'indel': 2}
        }
        
        # Create analysis request
        request = cli.create_analysis_request(validated_input, vcf_validation)
        
        assert isinstance(request, AnalysisRequest)
        assert request.case_uid == 'CASE_001'
        assert request.patient_uid == 'PAT_001'
        assert request.cancer_type == 'lung_adenocarcinoma'
        assert request.vcf_file_path == 'test.vcf'
        assert request.quality_filters['min_depth'] == 15
        assert request.quality_filters['min_vaf'] == 0.1
        assert request.vcf_summary == vcf_validation


class TestCLIIntegration:
    """Integration tests for complete CLI workflow"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.cli = AnnotationEngineCLI()
        self.example_dir = Path(__file__).parent.parent / "example_input"
        self.synthetic_vcf = self.example_dir / "synthetic_test.vcf"
    
    @patch('sys.argv')
    def test_dry_run_mode(self, mock_argv):
        """Test dry run mode execution"""
        if not self.synthetic_vcf.exists():
            pytest.skip(f"Synthetic VCF not found: {self.synthetic_vcf}")
        
        # Mock command line arguments
        mock_argv.return_value = [
            'annotation-engine',
            '--input', str(self.synthetic_vcf),
            '--case-uid', 'DRY_RUN_TEST',
            '--cancer-type', 'lung_adenocarcinoma',
            '--dry-run',
            '--quiet'
        ]
        
        # Patch sys.argv for argument parsing
        with patch.object(self.cli.parser, 'parse_args') as mock_parse:
            mock_parse.return_value = MagicMock(
                input=self.synthetic_vcf,
                case_uid='DRY_RUN_TEST',
                patient_uid=None,
                cancer_type='lung_adenocarcinoma',
                tissue_type='primary_tumor',
                output=Path('./results'),
                output_format='all',
                genome='GRCh37',
                guidelines=['AMP_ACMG', 'CGC_VICC', 'ONCOKB'],
                min_depth=10,
                min_vaf=0.05,
                skip_qc=False,
                config=None,
                kb_bundle=None,
                dry_run=True,
                verbose=0,
                quiet=True,
                log_file=None,
                api_mode=False
            )
            
            # Run CLI
            exit_code = self.cli.run()
            assert exit_code == 0
    
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs"""
        with patch.object(self.cli.parser, 'parse_args') as mock_parse:
            mock_parse.return_value = MagicMock(
                input=Path('nonexistent.vcf'),
                case_uid='INVALID_TEST',
                cancer_type='lung_adenocarcinoma',
                patient_uid=None,
                api_mode=False,
                verbose=1
            )
            
            exit_code = self.cli.run()
            assert exit_code == 1  # Should fail with validation error


if __name__ == '__main__':
    pytest.main([__file__, '-v'])