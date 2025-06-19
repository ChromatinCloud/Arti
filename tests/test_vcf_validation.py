"""
Unit tests for VCF validation and metadata validation
"""

import pytest
import tempfile
import gzip
from pathlib import Path
from src.annotation_engine.api.validators.vcf_validator import (
    VCFValidator, MetadataValidator, AnalysisMode, VCFValidationError
)


class TestVCFValidator:
    """Test VCF validation logic"""
    
    @pytest.fixture
    def validator(self):
        return VCFValidator()
    
    @pytest.fixture
    def single_sample_vcf(self):
        """Create a temporary single-sample VCF"""
        content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=249250621>
##contig=<ID=chr7,length=159138663>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR_SAMPLE
chr7	140453136	.	A	T	100	PASS	DP=100	GT:DP:AD	0/1:100:50,50
chr1	12345	.	G	A	80	PASS	DP=80	GT:DP:AD	0/1:80:40,40
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.fixture
    def multi_sample_vcf(self):
        """Create a temporary multi-sample VCF"""
        content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=249250621>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=SOMATIC,Number=0,Type=Flag,Description="Somatic mutation">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR	NORMAL
chr7	140453136	.	A	T	100	PASS	DP=100;SOMATIC	GT:DP:AD	0/1:100:50,50	0/0:100:100,0
chr1	12345	.	G	A	80	PASS	DP=80;SOMATIC	GT:DP:AD	0/1:80:40,40	0/0:80:80,0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.fixture
    def multi_sample_vcf_complex_names(self):
        """Create VCF with complex sample names"""
        content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	Patient123_T	Patient123_N
chr7	140453136	.	A	T	100	PASS	DP=100	GT:DP:AD	0/1:100:50,50	0/0:100:100,0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_tumor_only_single_sample_valid(self, validator, single_sample_vcf):
        """Test valid tumor-only with single sample"""
        result = validator.validate_vcf_for_mode(
            [single_sample_vcf],
            AnalysisMode.TUMOR_ONLY
        )
        
        assert result['valid'] is True
        assert result['mode'] == 'tumor_only'
        assert result['samples']['tumor'] == 'TUMOR_SAMPLE'
        assert result['variant_count'] == 2
    
    def test_tumor_only_multi_sample_invalid(self, validator, multi_sample_vcf):
        """Test tumor-only mode rejects multi-sample VCF"""
        with pytest.raises(VCFValidationError) as exc_info:
            validator.validate_vcf_for_mode(
                [multi_sample_vcf],
                AnalysisMode.TUMOR_ONLY
            )
        
        assert "Tumor-only mode requires single-sample VCF" in str(exc_info.value)
        assert "found 2 samples" in str(exc_info.value)
    
    def test_tumor_normal_multi_sample_valid(self, validator, multi_sample_vcf):
        """Test valid tumor-normal with multi-sample VCF"""
        result = validator.validate_vcf_for_mode(
            [multi_sample_vcf],
            AnalysisMode.TUMOR_NORMAL
        )
        
        assert result['valid'] is True
        assert result['mode'] == 'tumor_normal'
        assert result['samples']['tumor'] == 'TUMOR'
        assert result['samples']['normal'] == 'NORMAL'
        assert result['multi_sample'] is True
    
    def test_tumor_normal_separate_files_valid(self, validator, single_sample_vcf):
        """Test tumor-normal with separate VCF files"""
        # Create a second VCF for normal
        normal_content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NORMAL_SAMPLE
chr7	140453136	.	A	T	10	LowQual	DP=100	GT:DP:AD	0/0:100:95,5
chr1	99999	.	C	T	50	PASS	DP=60	GT:DP:AD	0/1:60:30,30
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(normal_content)
            normal_vcf = f.name
        
        result = validator.validate_vcf_for_mode(
            [single_sample_vcf, normal_vcf],
            AnalysisMode.TUMOR_NORMAL
        )
        
        assert result['valid'] is True
        assert result['mode'] == 'tumor_normal'
        assert result['samples']['tumor'] == 'TUMOR_SAMPLE'
        assert result['samples']['normal'] == 'NORMAL_SAMPLE'
        assert result['separate_files'] is True
        assert result['variant_counts']['overlap'] == 1  # chr7:140453136
    
    def test_sample_name_identification(self, validator, multi_sample_vcf_complex_names):
        """Test sample name identification with metadata"""
        # Without metadata - should use heuristics
        result = validator.validate_vcf_for_mode(
            [multi_sample_vcf_complex_names],
            AnalysisMode.TUMOR_NORMAL
        )
        assert result['samples']['tumor'] == 'Patient123_T'
        assert result['samples']['normal'] == 'Patient123_N'
        
        # With metadata - should use provided names
        result = validator.validate_vcf_for_mode(
            [multi_sample_vcf_complex_names],
            AnalysisMode.TUMOR_NORMAL,
            metadata={
                'tumor_sample': 'Patient123_T',
                'normal_sample': 'Patient123_N'
            }
        )
        assert result['samples']['tumor'] == 'Patient123_T'
        assert result['samples']['normal'] == 'Patient123_N'
    
    def test_missing_vcf_file(self, validator):
        """Test handling of missing VCF file"""
        with pytest.raises(VCFValidationError) as exc_info:
            validator.validate_vcf_for_mode(
                ['/non/existent/file.vcf'],
                AnalysisMode.TUMOR_ONLY
            )
        assert "VCF file not found" in str(exc_info.value)
    
    def test_invalid_vcf_format(self, validator):
        """Test handling of invalid VCF format"""
        # Create invalid VCF without fileformat header
        content = """#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	12345	.	G	A	80	PASS	DP=80	GT:DP:AD	0/1:80:40,40
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            invalid_vcf = f.name
        
        with pytest.raises(VCFValidationError) as exc_info:
            validator.validate_vcf_for_mode(
                [invalid_vcf],
                AnalysisMode.TUMOR_ONLY
            )
        assert "Invalid VCF format" in str(exc_info.value)
    
    def test_gzipped_vcf(self, validator):
        """Test handling of gzipped VCF files"""
        content = b"""##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE1
chr1	12345	.	G	A	80	PASS	DP=80	GT	0/1
"""
        with tempfile.NamedTemporaryFile(suffix='.vcf.gz', delete=False) as f:
            with gzip.open(f.name, 'wb') as gz:
                gz.write(content)
            
            result = validator.validate_vcf_for_mode(
                [f.name],
                AnalysisMode.TUMOR_ONLY
            )
            assert result['valid'] is True


class TestMetadataValidator:
    """Test metadata validation"""
    
    def test_valid_metadata_minimal(self):
        """Test minimal valid metadata"""
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'SKCM'
        }
        result = MetadataValidator.validate(metadata)
        assert result['valid'] is True
        assert result['has_oncotree_code'] is True
        assert result['has_tumor_purity'] is False
    
    def test_valid_metadata_complete(self):
        """Test complete valid metadata"""
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'LUAD',
            'patient_uid': 'PT_001',
            'tumor_purity': 0.75,
            'specimen_type': 'FFPE',
            'tumor_sample': 'Patient1_T',
            'normal_sample': 'Patient1_N'
        }
        result = MetadataValidator.validate(metadata)
        assert result['valid'] is True
        assert len(result['warnings']) == 0
    
    def test_missing_required_field(self):
        """Test missing required field"""
        metadata = {
            'cancer_type': 'SKCM'
            # Missing case_id
        }
        with pytest.raises(VCFValidationError) as exc_info:
            MetadataValidator.validate(metadata)
        assert "Missing required field: case_id" in str(exc_info.value)
    
    def test_invalid_tumor_purity(self):
        """Test invalid tumor purity value"""
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'SKCM',
            'tumor_purity': 1.5  # Invalid: > 1.0
        }
        with pytest.raises(VCFValidationError) as exc_info:
            MetadataValidator.validate(metadata)
        assert "Invalid value for tumor_purity" in str(exc_info.value)
    
    def test_invalid_oncotree_code_warning(self):
        """Test warning for potentially invalid OncoTree code"""
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'invalid123'  # Contains numbers
        }
        result = MetadataValidator.validate(metadata)
        assert result['valid'] is True
        assert len(result['warnings']) == 1
        assert "OncoTree code" in result['warnings'][0]
    
    def test_ffpe_without_tumor_purity_warning(self):
        """Test warning for FFPE without tumor purity"""
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'SKCM',
            'specimen_type': 'FFPE'
            # No tumor_purity
        }
        result = MetadataValidator.validate(metadata)
        assert result['valid'] is True
        assert any('Tumor purity is recommended' in w for w in result['warnings'])
    
    def test_non_standard_specimen_type_warning(self):
        """Test warning for non-standard specimen type"""
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'SKCM',
            'specimen_type': 'CustomType'
        }
        result = MetadataValidator.validate(metadata)
        assert result['valid'] is True
        assert any('not in standard list' in w for w in result['warnings'])


@pytest.mark.integration
class TestVCFValidationIntegration:
    """Integration tests for VCF validation in API context"""
    
    def test_full_validation_workflow_tumor_only(self):
        """Test complete validation workflow for tumor-only"""
        # Create test VCF
        vcf_content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TumorSample
chr7	140453136	.	A	T	100	PASS	DP=100	GT:DP:AD	0/1:100:50,50
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(vcf_content)
            vcf_path = f.name
        
        # Validate
        validator = VCFValidator()
        metadata = {
            'case_id': 'CASE_001',
            'cancer_type': 'SKCM',
            'tumor_purity': 0.8,
            'specimen_type': 'FFPE'
        }
        
        # Validate metadata
        metadata_result = MetadataValidator.validate(metadata)
        assert metadata_result['valid'] is True
        
        # Validate VCF
        vcf_result = validator.validate_vcf_for_mode(
            [vcf_path],
            AnalysisMode.TUMOR_ONLY,
            metadata
        )
        assert vcf_result['valid'] is True
        assert vcf_result['samples']['tumor'] == 'TumorSample'
    
    def test_full_validation_workflow_tumor_normal_multisample(self):
        """Test complete validation workflow for tumor-normal multi-sample"""
        # Create test VCF
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=SOMATIC,Number=0,Type=Flag,Description="Somatic mutation">
##INFO=<ID=TUMOR_AF,Number=1,Type=Float,Description="Tumor allele frequency">
##INFO=<ID=NORMAL_AF,Number=1,Type=Float,Description="Normal allele frequency">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	Tumor_P1	Normal_P1	Extra_Sample
chr7	140453136	.	A	T	100	PASS	SOMATIC;TUMOR_AF=0.5;NORMAL_AF=0.0	GT:DP:AD	0/1:100:50,50	0/0:100:100,0	0/0:50:50,0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(vcf_content)
            vcf_path = f.name
        
        # Validate with sample name hints
        validator = VCFValidator()
        metadata = {
            'case_id': 'CASE_002',
            'cancer_type': 'LUAD',
            'tumor_sample': 'Tumor_P1',
            'normal_sample': 'Normal_P1'
        }
        
        result = validator.validate_vcf_for_mode(
            [vcf_path],
            AnalysisMode.TUMOR_NORMAL,
            metadata
        )
        
        assert result['valid'] is True
        assert result['samples']['tumor'] == 'Tumor_P1'
        assert result['samples']['normal'] == 'Normal_P1'
        assert len(result['samples']['all']) == 3  # Including extra sample