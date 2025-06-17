"""
Test input validation and patient context modules
"""

import pytest
from pathlib import Path
import tempfile
import gzip

from annotation_engine.input_validator import (
    InputValidator, VCFValidator, SampleDetector, 
    ChromosomeStandardizer, ValidationResult
)
from annotation_engine.patient_context import (
    PatientContextManager, OncoTreeValidator, 
    PatientContext, TissueType
)
from annotation_engine.models import AnalysisType


class TestVCFValidator:
    """Test VCF validation"""
    
    def create_test_vcf(self, content: str, gzipped: bool = False) -> Path:
        """Create a temporary test VCF file"""
        suffix = ".vcf.gz" if gzipped else ".vcf"
        with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as f:
            if gzipped:
                with gzip.open(f, 'wt') as gz:
                    gz.write(content)
            else:
                f.write(content.encode())
            return Path(f.name)
    
    def test_valid_vcf(self):
        """Test validation of a valid VCF"""
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	tumor_sample
chr1	12345	.	A	T	100	PASS	DP=50;AF=0.4	GT:AD	0/1:30,20
chr2	67890	.	G	C	200	PASS	DP=100;AF=0.3	GT:AD	0/1:70,30
"""
        vcf_path = self.create_test_vcf(vcf_content)
        
        validator = VCFValidator()
        result = validator.validate_vcf(vcf_path)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.metadata["sample_count"] == 1
        assert result.metadata["samples"] == ["tumor_sample"]
        assert result.metadata["chromosome_style"] == "with_chr"
        assert "DP" in result.metadata["info_fields"]
        assert "AF" in result.metadata["info_fields"]
        
        vcf_path.unlink()
    
    def test_missing_headers(self):
        """Test VCF with missing required headers"""
        vcf_content = """#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	12345	.	A	T	100	PASS	DP=50
"""
        vcf_path = self.create_test_vcf(vcf_content)
        
        validator = VCFValidator()
        result = validator.validate_vcf(vcf_path)
        
        assert not result.is_valid
        assert any("fileformat" in e for e in result.errors)
        
        vcf_path.unlink()
    
    def test_gzipped_vcf(self):
        """Test gzipped VCF validation"""
        vcf_content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	12345	.	A	T	100	PASS	DP=50
"""
        vcf_path = self.create_test_vcf(vcf_content, gzipped=True)
        
        validator = VCFValidator()
        result = validator.validate_vcf(vcf_path)
        
        assert result.is_valid
        
        vcf_path.unlink()


class TestSampleDetector:
    """Test sample type detection"""
    
    def test_single_sample(self):
        """Test single sample detection"""
        detector = SampleDetector()
        
        analysis_type, sample_map = detector.detect_sample_type(["sample1"])
        
        assert analysis_type == AnalysisType.TUMOR_ONLY
        assert sample_map == {"tumor": "sample1"}
    
    def test_tumor_normal_pair(self):
        """Test tumor-normal pair detection"""
        detector = SampleDetector()
        
        # Test various naming patterns
        test_cases = [
            (["sample_T", "sample_N"], {"tumor": "sample_T", "normal": "sample_N"}),
            (["patient1_tumor", "patient1_normal"], {"tumor": "patient1_tumor", "normal": "patient1_normal"}),
            (["TCGA-01-tumor", "TCGA-01-normal"], {"tumor": "TCGA-01-tumor", "normal": "TCGA-01-normal"}),
            (["sample.T", "sample.N"], {"tumor": "sample.T", "normal": "sample.N"}),
            (["T1", "N1"], {"tumor": "T1", "normal": "N1"}),
        ]
        
        for samples, expected_map in test_cases:
            analysis_type, sample_map = detector.detect_sample_type(samples)
            assert analysis_type == AnalysisType.TUMOR_NORMAL
            assert sample_map == expected_map
    
    def test_ambiguous_samples(self):
        """Test ambiguous sample names"""
        detector = SampleDetector()
        
        # Two samples without clear tumor/normal pattern
        analysis_type, sample_map = detector.detect_sample_type(["sample1", "sample2"])
        
        assert analysis_type == AnalysisType.TUMOR_ONLY
        assert sample_map == {"tumor": "sample1"}


class TestChromosomeStandardizer:
    """Test chromosome name standardization"""
    
    def test_standardize_to_chr(self):
        """Test standardization to chr prefix"""
        standardizer = ChromosomeStandardizer()
        
        assert standardizer.standardize_chromosome("1", "with_chr") == "chr1"
        assert standardizer.standardize_chromosome("chr1", "with_chr") == "chr1"
        assert standardizer.standardize_chromosome("X", "with_chr") == "chrX"
        assert standardizer.standardize_chromosome("chrM", "with_chr") == "chrM"
    
    def test_standardize_without_chr(self):
        """Test standardization without chr prefix"""
        standardizer = ChromosomeStandardizer()
        
        assert standardizer.standardize_chromosome("chr1", "without_chr") == "1"
        assert standardizer.standardize_chromosome("1", "without_chr") == "1"
        assert standardizer.standardize_chromosome("chrX", "without_chr") == "X"
        assert standardizer.standardize_chromosome("M", "without_chr") == "M"


class TestOncoTreeValidator:
    """Test OncoTree validation"""
    
    def test_validate_known_codes(self):
        """Test validation of known OncoTree codes"""
        validator = OncoTreeValidator()
        
        # Test valid codes
        valid_codes = ["LUAD", "BRCA", "SKCM", "GBM", "AML"]
        for code in valid_codes:
            is_valid, info = validator.validate_code(code)
            assert is_valid
            assert info["code"] == code
            assert info["tissue"] is not None
    
    def test_validate_aliases(self):
        """Test alias resolution"""
        validator = OncoTreeValidator()
        
        # Test aliases
        is_valid, info = validator.validate_code("MELANOMA")
        assert is_valid
        assert info["code"] == "SKCM"
        
        is_valid, info = validator.validate_code("LUNG_ADENO")
        assert is_valid
        assert info["code"] == "LUAD"
    
    def test_tissue_type_mapping(self):
        """Test tissue type extraction"""
        validator = OncoTreeValidator()
        
        assert validator.get_tissue_type("LUAD") == TissueType.LUNG
        assert validator.get_tissue_type("SKCM") == TissueType.SKIN
        assert validator.get_tissue_type("BRCA") == TissueType.BREAST
        assert validator.get_tissue_type("GBM") == TissueType.BRAIN
    
    def test_parent_hierarchy(self):
        """Test parent code hierarchy"""
        validator = OncoTreeValidator()
        
        # LUAD -> NSCLC -> LUNG
        parents = validator.get_parent_codes("LUAD")
        assert "NSCLC" in parents
        assert "LUNG" in parents
        
        # SKCM -> MEL -> SKIN
        parents = validator.get_parent_codes("SKCM")
        assert "MEL" in parents
        assert "SKIN" in parents
    
    def test_related_codes(self):
        """Test related code finding"""
        validator = OncoTreeValidator()
        
        # Get all lung-related codes
        related = validator.get_related_codes("LUAD")
        assert "LUAD" in related
        assert "LUSC" in related  # Sibling
        assert "NSCLC" in related  # Parent
        assert "LUNG" in related  # Grandparent


class TestPatientContextManager:
    """Test patient context management"""
    
    def test_create_basic_context(self):
        """Test basic context creation"""
        manager = PatientContextManager()
        
        context = manager.create_context(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Lung Adenocarcinoma",
            oncotree_code="LUAD"
        )
        
        assert context.patient_uid == "PT001"
        assert context.case_uid == "CASE001"
        assert context.cancer_type == "Lung Adenocarcinoma"
        assert context.oncotree_code == "LUAD"
        assert context.tissue_type == TissueType.LUNG
    
    def test_invalid_oncotree_code(self):
        """Test handling of invalid OncoTree code"""
        manager = PatientContextManager()
        
        context = manager.create_context(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Unknown Cancer",
            oncotree_code="INVALID"
        )
        
        assert context.oncotree_code is None  # Invalid code rejected
        assert context.tissue_type is None
        assert context.cancer_type == "Unknown Cancer"  # Keeps original
    
    def test_cancer_specific_genes(self):
        """Test cancer-specific gene lists"""
        manager = PatientContextManager()
        
        # Lung cancer context
        lung_context = manager.create_context(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Lung",
            oncotree_code="LUAD"
        )
        
        lung_genes = manager.get_cancer_specific_genes(lung_context)
        assert "EGFR" in lung_genes
        assert "ALK" in lung_genes
        assert "KRAS" in lung_genes
        
        # Melanoma context
        mel_context = manager.create_context(
            patient_uid="PT002",
            case_uid="CASE002",
            cancer_type="Melanoma",
            oncotree_code="SKCM"
        )
        
        mel_genes = manager.get_cancer_specific_genes(mel_context)
        assert "BRAF" in mel_genes
        assert "NRAS" in mel_genes
        assert "KIT" in mel_genes
    
    def test_therapy_implications(self):
        """Test therapy mapping"""
        manager = PatientContextManager()
        
        context = manager.create_context(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Lung",
            oncotree_code="LUAD"
        )
        
        therapies = manager.get_therapy_implications(context)
        
        assert "EGFR" in therapies
        assert "Osimertinib" in therapies["EGFR"]
        assert "ALK" in therapies
        assert "Alectinib" in therapies["ALK"]
    
    def test_context_validation(self):
        """Test context validation"""
        manager = PatientContextManager()
        
        # Valid context
        valid_context = PatientContext(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Lung Cancer",
            oncotree_code="LUAD",
            age_at_diagnosis=65,
            sex="M"
        )
        
        is_valid, issues = manager.validate_context(valid_context)
        assert is_valid
        assert len(issues) == 0
        
        # Invalid context
        invalid_context = PatientContext(
            patient_uid="",
            case_uid="CASE001",
            cancer_type="Cancer",
            oncotree_code="INVALID",
            age_at_diagnosis=200,
            sex="Unknown"
        )
        
        is_valid, issues = manager.validate_context(invalid_context)
        assert not is_valid
        assert len(issues) > 0
        assert any("patient UID" in issue for issue in issues)
        assert any("OncoTree" in issue for issue in issues)
        assert any("age" in issue for issue in issues)


class TestInputValidator:
    """Test main input validator"""
    
    def test_integrated_validation(self):
        """Test integrated validation workflow"""
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE_T	SAMPLE_N
chr1	12345	.	A	T	100	PASS	DP=50;AF=0.4	GT	0/1	0/0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(vcf_content)
            vcf_path = Path(f.name)
        
        validator = InputValidator()
        result = validator.validate_input(
            vcf_path=vcf_path,
            patient_uid="PT001",
            case_uid="CASE001",
            oncotree_code="LUAD"
        )
        
        assert result.is_valid
        assert result.metadata["analysis_type"] == AnalysisType.TUMOR_NORMAL
        assert result.metadata["sample_mapping"] == {"tumor": "SAMPLE_T", "normal": "SAMPLE_N"}
        # Allow warnings about optional fields
        assert all("recommended" in w for w in result.warnings)
        
        vcf_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])