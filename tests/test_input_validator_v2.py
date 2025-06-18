"""
Tests for InputValidatorV2

Tests the new input validator that follows the protocol interface.
"""

import pytest
import tempfile
import gzip
from pathlib import Path
from unittest.mock import Mock, patch

from annotation_engine.input_validator_v2 import InputValidatorV2
from annotation_engine.interfaces.validation_interfaces import (
    ValidatedInput,
    ValidatedVCF,
    ValidationResult,
    ValidationStatus,
    SampleType
)


class TestInputValidatorV2:
    """Test the new input validator implementation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.validator = InputValidatorV2()
        
    def create_test_vcf(self, content: str, gzipped: bool = False) -> Path:
        """Create a temporary VCF file for testing"""
        suffix = ".vcf.gz" if gzipped else ".vcf"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            if gzipped:
                f.close()  # Close text file
                with gzip.open(f.name, 'wt') as gz_f:
                    gz_f.write(content)
            else:
                f.write(content)
        
        return Path(f.name)
    
    def test_valid_tumor_only_vcf(self):
        """Test validation of a valid tumor-only VCF"""
        vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100;AF=0.45	GT:AD:DP	0/1:55,45:100
chr17	41234567	.	G	A	45.0	PASS	DP=80;AF=0.35	GT:AD:DP	0/1:52,28:80
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            # Test VCF validation
            validated_vcf = self.validator.validate_vcf(vcf_path, SampleType.TUMOR)
            
            assert validated_vcf.sample_type == SampleType.TUMOR
            assert validated_vcf.variant_count == 2
            assert validated_vcf.has_genotypes is True
            assert validated_vcf.has_allele_frequencies is True
            assert validated_vcf.genome_version == "GRCh38"
            assert validated_vcf.normalized_chromosomes is True
            assert validated_vcf.sample_names == ["TUMOR"]
            
        finally:
            vcf_path.unlink()
    
    def test_missing_required_format_fields(self):
        """Test that missing required FORMAT fields cause errors"""
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT	0/1
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            with pytest.raises(ValueError, match="Missing required FORMAT fields"):
                self.validator.validate_vcf(vcf_path, SampleType.TUMOR)
        finally:
            vcf_path.unlink()
    
    def test_low_depth_warning(self):
        """Test that low depth triggers warnings"""
        vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	15.0	PASS	DP=10	GT:AD:DP	0/1:6,4:10
chr17	41234567	.	G	A	12.0	PASS	DP=8	GT:AD:DP	0/1:5,3:8
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            validated_vcf, errors, warnings = self.validator._validate_vcf_with_errors(
                vcf_path, SampleType.TUMOR
            )
            
            # Should succeed but with warnings
            assert validated_vcf is not None
            assert len(errors) == 0
            assert len(warnings) >= 1
            
            # Check for depth warning
            depth_warnings = [w for w in warnings if "depth" in w.message.lower()]
            assert len(depth_warnings) >= 1
            assert "median depth" in depth_warnings[0].message.lower()
            
        finally:
            vcf_path.unlink()
    
    def test_complete_validation_flow(self):
        """Test complete validation including patient context"""
        vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100;AF=0.45	GT:AD:DP	0/1:55,45:100
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            # Test complete validation
            result = self.validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT001",
                case_id="CASE001",
                oncotree_code="LUAD",
                requested_outputs=["json", "phenopacket"]
            )
            
            assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert result.validated_input is not None
            
            validated_input = result.validated_input
            assert validated_input.analysis_type == "tumor_only"
            assert validated_input.patient.cancer_type == "LUAD"
            assert validated_input.patient.cancer_display_name == "Lung Adenocarcinoma"
            assert "json" in validated_input.requested_outputs
            assert "phenopacket" in validated_input.requested_outputs
            assert validated_input.export_phenopacket is True
            
        finally:
            vcf_path.unlink()
    
    def test_tumor_normal_pairing(self):
        """Test tumor-normal VCF pairing validation"""
        tumor_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        normal_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NORMAL
chr7	140453136	.	A	T	30.0	PASS	DP=80	GT:AD:DP	0/0:80,0:80
"""
        
        tumor_vcf = self.create_test_vcf(tumor_vcf_content)
        normal_vcf = self.create_test_vcf(normal_vcf_content)
        
        try:
            result = self.validator.validate(
                tumor_vcf_path=tumor_vcf,
                normal_vcf_path=normal_vcf,
                patient_uid="PT002",
                case_id="CASE002",
                oncotree_code="SKCM"
            )
            
            assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert result.validated_input.analysis_type == "tumor_normal"
            assert result.validated_input.normal_vcf is not None
            
        finally:
            tumor_vcf.unlink()
            normal_vcf.unlink()
    
    def test_genome_version_mismatch(self):
        """Test that genome version mismatches are caught"""
        tumor_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        normal_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh37
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NORMAL
chr7	140453136	.	A	T	30.0	PASS	DP=80	GT:AD:DP	0/0:80,0:80
"""
        
        tumor_vcf = self.create_test_vcf(tumor_vcf_content)
        normal_vcf = self.create_test_vcf(normal_vcf_content)
        
        try:
            result = self.validator.validate(
                tumor_vcf_path=tumor_vcf,
                normal_vcf_path=normal_vcf,
                patient_uid="PT003",
                case_id="CASE003", 
                oncotree_code="BRCA"
            )
            
            assert result.status == ValidationStatus.INVALID
            assert any("version mismatch" in error.message for error in result.errors)
            
        finally:
            tumor_vcf.unlink()
            normal_vcf.unlink()
    
    def test_invalid_patient_uid(self):
        """Test patient UID validation"""
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            # Test invalid patient UID with special characters
            result = self.validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT@001#",  # Invalid characters
                case_id="CASE001",
                oncotree_code="LUAD"
            )
            
            assert result.status == ValidationStatus.INVALID
            assert any("patient uid format" in error.message.lower() for error in result.errors)
            
        finally:
            vcf_path.unlink()
    
    def test_invalid_oncotree_code(self):
        """Test OncoTree code validation with suggestions"""
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            # Test close match
            result = self.validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT001",
                case_id="CASE001",
                oncotree_code="LUAC"  # Close to LUAD
            )
            
            assert result.status == ValidationStatus.INVALID
            assert any("Did you mean" in error.message for error in result.errors)
            assert any("LUAD" in error.message for error in result.errors)
            
        finally:
            vcf_path.unlink()
    
    def test_tumor_purity_validation(self):
        """Test tumor purity parameter validation"""
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            # Test invalid purity values
            result = self.validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT001",
                case_id="CASE001",
                oncotree_code="LUAD",
                tumor_purity=1.5  # Invalid - > 1.0
            )
            
            assert result.status == ValidationStatus.INVALID
            assert any("tumor purity" in error.message.lower() for error in result.errors)
            
            # Test valid purity
            result = self.validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT001",
                case_id="CASE001",
                oncotree_code="LUAD",
                tumor_purity=0.75
            )
            
            assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert result.validated_input.tumor_purity == 0.75
            
        finally:
            vcf_path.unlink()
    
    def test_gzipped_vcf(self):
        """Test that gzipped VCF files are handled correctly"""
        vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        vcf_path = self.create_test_vcf(vcf_content, gzipped=True)
        
        try:
            validated_vcf = self.validator.validate_vcf(vcf_path, SampleType.TUMOR)
            
            assert validated_vcf.variant_count == 1
            assert validated_vcf.genome_version == "GRCh38"
            
        finally:
            vcf_path.unlink()
    
    def test_chromosome_naming_consistency(self):
        """Test chromosome naming detection and pairing consistency"""
        # Test chr-prefixed format
        chr_vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        # Test non-prefixed format
        no_chr_vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NORMAL
7	140453136	.	A	T	30.0	PASS	DP=80	GT:AD:DP	0/0:80,0:80
"""
        
        chr_vcf = self.create_test_vcf(chr_vcf_content)
        no_chr_vcf = self.create_test_vcf(no_chr_vcf_content)
        
        try:
            # Test mismatch detection
            result = self.validator.validate(
                tumor_vcf_path=chr_vcf,
                normal_vcf_path=no_chr_vcf,
                patient_uid="PT004",
                case_id="CASE004",
                oncotree_code="BRCA"
            )
            
            assert result.status == ValidationStatus.INVALID
            assert any("chromosome naming inconsistent" in error.message.lower() 
                      for error in result.errors)
            
        finally:
            chr_vcf.unlink()
            no_chr_vcf.unlink()


class TestPatientContextValidation:
    """Test patient context validation specifically"""
    
    def setup_method(self):
        self.validator = InputValidatorV2()
    
    def test_valid_patient_context(self):
        """Test valid patient context creation"""
        context = self.validator.validate_patient_context(
            patient_uid="PT001",
            case_id="CASE001",
            oncotree_code="LUAD"
        )
        
        assert context.patient_uid == "PT001"
        assert context.case_id == "CASE001"
        assert context.cancer_type == "LUAD"
        assert context.cancer_display_name == "Lung Adenocarcinoma"
        assert context.primary_site == "Lung"
    
    def test_patient_uid_format_validation(self):
        """Test patient UID format validation"""
        # Valid formats
        valid_uids = ["PT001", "PATIENT-123", "P_001", "ABC123"]
        for uid in valid_uids:
            context = self.validator.validate_patient_context(
                patient_uid=uid,
                case_id="CASE001", 
                oncotree_code="LUAD"
            )
            assert context.patient_uid == uid
        
        # Invalid formats
        invalid_uids = ["", "   ", "PT@001", "PT#001", "-INVALID", "_INVALID"]
        for uid in invalid_uids:
            with pytest.raises(ValueError, match="Patient UID|Invalid patient UID"):
                self.validator.validate_patient_context(
                    patient_uid=uid,
                    case_id="CASE001",
                    oncotree_code="LUAD"
                )
    
    def test_oncotree_fuzzy_matching(self):
        """Test OncoTree code fuzzy matching"""
        # Test edit distance matching
        with pytest.raises(ValueError, match="Did you mean.*LUAD"):
            self.validator.validate_patient_context(
                patient_uid="PT001",
                case_id="CASE001",
                oncotree_code="LUAC"  # One character off from LUAD
            )
        
        # Test prefix matching
        with pytest.raises(ValueError, match="Did you mean.*SKCM"):
            self.validator.validate_patient_context(
                patient_uid="PT001", 
                case_id="CASE001",
                oncotree_code="SKC"  # Prefix of SKCM
            )


if __name__ == "__main__":
    pytest.main([__file__])