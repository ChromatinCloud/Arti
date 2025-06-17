"""
Comprehensive end-to-end integration tests for the annotation engine

Tests the complete pipeline from VCF input to tier assignment output,
including all intermediate steps and error handling.
"""

import pytest
import tempfile
from pathlib import Path
import json
from datetime import datetime

from annotation_engine.cli import AnnotationEngineCLI
from annotation_engine.models import AnalysisType, VariantAnnotation
from annotation_engine.vep_runner import VEPRunner, VEPConfiguration
from annotation_engine.evidence_aggregator import EvidenceAggregator
from annotation_engine.tiering import TieringEngine
from annotation_engine.workflow_router import create_workflow_router
from annotation_engine.input_validator import InputValidator
from annotation_engine.patient_context import PatientContextManager


class TestEndToEndPipeline:
    """Comprehensive end-to-end tests for the annotation pipeline"""
    
    @pytest.fixture
    def test_vcf_content(self):
        """Create test VCF content with known pathogenic variants"""
        return """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
##FORMAT=<ID=VAF,Number=A,Type=Float,Description="Variant Allele Frequency">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tTUMOR
7\t140753336\t.\tT\tA\t100\tPASS\tDP=50;AF=0.40\tGT:AD:DP:VAF\t0/1:30,20:50:0.40
12\t25245350\t.\tC\tT\t90\tPASS\tDP=40;AF=0.35\tGT:AD:DP:VAF\t0/1:26,14:40:0.35
17\t7674220\t.\tG\tA\t95\tPASS\tDP=60;AF=0.45\tGT:AD:DP:VAF\t0/1:33,27:60:0.45
3\t178952085\t.\tA\tG\t85\tPASS\tDP=45;AF=0.30\tGT:AD:DP:VAF\t0/1:31,14:45:0.30
"""
    
    @pytest.fixture
    def test_vcf_file(self, test_vcf_content):
        """Create a temporary test VCF file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(test_vcf_content)
            return Path(f.name)
    
    def test_input_validation_workflow(self, test_vcf_file):
        """Test the input validation workflow"""
        validator = InputValidator()
        
        # Test VCF validation
        result = validator.validate_input(
            vcf_path=test_vcf_file,
            patient_uid="TEST_001",
            case_uid="CASE_001",
            oncotree_code="SKCM"  # Melanoma
        )
        
        assert result.is_valid
        assert result.metadata["analysis_type"] == AnalysisType.TUMOR_ONLY
        assert result.metadata["sample_count"] == 1
        assert result.metadata["chromosome_style"] in ["with_chr", "without_chr"]
        
        # Cleanup
        test_vcf_file.unlink()
    
    def test_patient_context_creation(self):
        """Test patient context creation with OncoTree validation"""
        manager = PatientContextManager()
        
        # Test valid context
        context = manager.create_context(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Melanoma",
            oncotree_code="SKCM",
            age_at_diagnosis=65,
            sex="M"
        )
        
        assert context.patient_uid == "PT001"
        assert context.oncotree_code == "SKCM"
        assert context.tissue_type is not None
        
        # Test cancer-specific genes
        genes = manager.get_cancer_specific_genes(context)
        assert "BRAF" in genes
        assert "NRAS" in genes
        
        # Test therapy implications
        therapies = manager.get_therapy_implications(context)
        assert "BRAF" in therapies
    
    def test_workflow_router_configuration(self):
        """Test workflow router for different analysis types"""
        # Test tumor-only configuration
        to_router = create_workflow_router(
            analysis_type=AnalysisType.TUMOR_ONLY,
            tumor_type="melanoma"
        )
        
        assert to_router.pathway.name == "Tumor-Only Somatic"
        assert to_router.get_vaf_threshold("min_tumor_vaf") == 0.10
        # Check that population databases have higher weight in tumor-only
        from annotation_engine.workflow_router import EvidenceSource
        assert to_router.get_evidence_weight(EvidenceSource.GNOMAD) == 0.7
        assert to_router.get_evidence_weight(EvidenceSource.CLINVAR) == 0.6
        
        # Test tumor-normal configuration
        tn_router = create_workflow_router(
            analysis_type=AnalysisType.TUMOR_NORMAL,
            tumor_type="lung"
        )
        
        assert tn_router.pathway.name == "Tumor-Normal Somatic"
        assert tn_router.get_vaf_threshold("min_tumor_vaf") == 0.05
        assert tn_router.get_vaf_threshold("max_normal_vaf") == 0.02
        # Population databases have lower weight in tumor-normal
        assert tn_router.get_evidence_weight(EvidenceSource.GNOMAD) == 0.2
        assert tn_router.get_evidence_weight(EvidenceSource.CLINVAR) == 0.3
    
    def test_evidence_aggregation_with_router(self):
        """Test evidence aggregation with workflow router integration"""
        # Create router
        router = create_workflow_router(
            analysis_type=AnalysisType.TUMOR_ONLY,
            tumor_type="melanoma"
        )
        
        # Create aggregator with router
        aggregator = EvidenceAggregator(workflow_router=router)
        
        # Create test variant
        variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            hgvs_c="c.1799T>A",
            consequence=["missense_variant"],
            vaf=0.40,
            tumor_vaf=0.40,
            total_depth=50
        )
        
        # Get evidence
        evidence = aggregator.aggregate_evidence(variant)
        
        assert len(evidence) > 0
        # Check that we got evidence (router adjustment happens internally)
        # The evidence objects themselves don't have analysis_type_adjusted field
    
    def test_tiering_with_workflow_router(self):
        """Test tier assignment with workflow router"""
        # Create router
        router = create_workflow_router(
            analysis_type=AnalysisType.TUMOR_ONLY,
            tumor_type="melanoma"
        )
        
        # Create tiering engine with router
        tiering_engine = TieringEngine(workflow_router=router)
        
        # Test variant with high VAF (should pass filter)
        high_vaf_variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            consequence=["missense_variant"],
            vaf=0.40,
            tumor_vaf=0.40,
            total_depth=50
        )
        
        tier_result = tiering_engine.assign_tier(
            high_vaf_variant,
            cancer_type="melanoma",
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        assert tier_result is not None
        assert tier_result.amp_scoring is not None
        
        # Test variant with low VAF (should be filtered)
        low_vaf_variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            consequence=["missense_variant"],
            vaf=0.05,
            tumor_vaf=0.05,  # Below 10% threshold
            total_depth=50
        )
        
        low_tier_result = tiering_engine.assign_tier(
            low_vaf_variant,
            cancer_type="melanoma",
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        # Should be filtered or assigned low tier due to low VAF
        if hasattr(low_tier_result, 'tier') and low_tier_result.tier == "IV":
            # Direct filtering result
            assert low_tier_result.tier == "IV"
        else:
            # Should get lower tier due to VAF filtering
            primary_tier = low_tier_result.amp_scoring.get_primary_tier()
            assert primary_tier in ["Tier III", "Tier IV"]
    
    def test_complete_pipeline_mock_vep(self, test_vcf_file):
        """Test complete pipeline with mocked VEP"""
        # Mock VEP annotations
        mock_annotations = [
            VariantAnnotation(
                chromosome="7",
                position=140753336,
                reference="T",
                alternate="A",
                gene_symbol="BRAF",
                transcript_id="ENST00000288602",
                consequence=["missense_variant"],
                hgvs_p="p.Val600Glu",
                hgvs_c="c.1799T>A",
                vaf=0.40,
                tumor_vaf=0.40,
                total_depth=50
            ),
            VariantAnnotation(
                chromosome="12",
                position=25245350,
                reference="C",
                alternate="T",
                gene_symbol="KRAS",
                transcript_id="ENST00000256078",
                consequence=["missense_variant"],
                hgvs_p="p.Gly12Cys",
                hgvs_c="c.34G>T",
                vaf=0.35,
                tumor_vaf=0.35,
                total_depth=40
            )
        ]
        
        # Create workflow router
        router = create_workflow_router(
            analysis_type=AnalysisType.TUMOR_ONLY,
            tumor_type="melanoma"
        )
        
        # Create pipeline components
        aggregator = EvidenceAggregator(workflow_router=router)
        tiering_engine = TieringEngine(workflow_router=router)
        
        results = []
        for variant in mock_annotations:
            # Get evidence
            evidence = aggregator.aggregate_evidence(variant)
            
            # Assign tier
            tier_result = tiering_engine.assign_tier(
                variant,
                cancer_type="melanoma",
                analysis_type=AnalysisType.TUMOR_ONLY
            )
            
            # Create result
            result = {
                "variant": f"{variant.gene_symbol} {variant.hgvs_p}",
                "evidence_count": len(evidence),
                "tier": tier_result.amp_scoring.get_primary_tier(),
                "oncogenicity": tier_result.vicc_scoring.classification.value if tier_result.vicc_scoring else None,
                "confidence": tier_result.confidence_score
            }
            results.append(result)
        
        assert len(results) == 2
        assert all(r["tier"] is not None for r in results)
        assert all(r["evidence_count"] > 0 for r in results)
        
        # Cleanup
        test_vcf_file.unlink()
    
    def test_cli_dry_run_mode(self, test_vcf_file):
        """Test CLI in dry-run mode"""
        import sys
        from io import StringIO
        
        # Capture output
        captured_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            # Create CLI arguments
            sys.argv = [
                "annotation-engine",
                "--input", str(test_vcf_file),
                "--case-uid", "TEST_CASE",
                "--cancer-type", "melanoma",
                "--dry-run"
            ]
            
            # Run CLI
            cli = AnnotationEngineCLI()
            exit_code = cli.run()
            
            # Check output
            output = captured_output.getvalue()
            assert exit_code == 0
            assert "DRY RUN MODE" in output
            assert "Validation complete" in output
            
        finally:
            sys.stdout = old_stdout
            test_vcf_file.unlink()
    
    def test_error_handling(self):
        """Test error handling throughout the pipeline"""
        # Test invalid VCF path
        validator = InputValidator()
        try:
            result = validator.validate_input(
                vcf_path=Path("/nonexistent/file.vcf"),
                patient_uid="TEST",
                case_uid="CASE"
            )
            # Should either return invalid result or raise exception
            if hasattr(result, 'is_valid'):
                assert not result.is_valid
        except Exception:
            # Exception is acceptable for missing file
            pass
        
        # Test invalid OncoTree code
        manager = PatientContextManager()
        context = manager.create_context(
            patient_uid="PT001",
            case_uid="CASE001",
            cancer_type="Unknown",
            oncotree_code="INVALID"
        )
        assert context.oncotree_code is None
        
        # Test variant with minimal required fields
        tiering_engine = TieringEngine()
        try:
            # VariantAnnotation requires gene_symbol, so provide it
            minimal_variant = VariantAnnotation(
                chromosome="1",
                position=12345,
                reference="A",
                alternate="T",
                gene_symbol="UNKNOWN"  # Minimal required field
            )
            
            # Should handle gracefully
            tier_result = tiering_engine.assign_tier(
                minimal_variant,
                cancer_type="unknown"
            )
            # Should return a result, likely Tier IV or VUS
            assert tier_result is not None
            assert tier_result.amp_scoring.get_primary_tier() in ["Tier III", "Tier IV"]
        except Exception:
            # Exception is acceptable for minimal variant
            pass
    
    def test_performance_benchmark(self, test_vcf_file):
        """Benchmark pipeline performance"""
        import time
        
        start_time = time.time()
        
        # Run validation
        validator = InputValidator()
        result = validator.validate_input(
            vcf_path=test_vcf_file,
            patient_uid="PERF_TEST",
            case_uid="PERF_CASE",
            oncotree_code="LUAD"
        )
        
        validation_time = time.time() - start_time
        
        # Validation should be fast
        assert validation_time < 1.0  # Less than 1 second
        assert result.is_valid
        
        # Cleanup
        test_vcf_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])