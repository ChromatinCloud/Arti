"""
Integration test demonstrating Person A → Person B interface

This test can be run to verify the integration works correctly once
both implementations are complete.
"""

import pytest
from pathlib import Path
from datetime import datetime

from annotation_engine.interfaces import (
    ValidatedInput,
    ValidatedVCF,
    PatientContext,
    ValidationResult,
    ValidationStatus,
    SampleType,
    WorkflowContext,
    AnalysisType,
    EvidenceSource
)


class TestInputValidatorWorkflowRouterIntegration:
    """Test the integration between input validation and workflow routing"""
    
    def test_tumor_only_flow(self):
        """Test complete flow for tumor-only analysis"""
        # Import actual implementations (will fail until implemented)
        from annotation_engine.input_validator import InputValidator
        from annotation_engine.workflow_router import WorkflowRouter
        
        # Initialize components
        validator = InputValidator()
        router = WorkflowRouter()
        
        # Step 1: Validate input
        validation_result = validator.validate(
            tumor_vcf_path=Path("test_data/tumor_only.vcf"),
            patient_uid="PT001",
            case_id="CASE001",
            oncotree_code="LUAD",
            requested_outputs=["json", "phenopacket"]
        )
        
        # Verify validation passed
        assert validation_result.is_valid
        assert validation_result.validated_input is not None
        assert validation_result.validated_input.analysis_type == "tumor_only"
        
        # Step 2: Route to workflow
        workflow_context = router.route(validation_result.validated_input)
        
        # Verify routing
        assert workflow_context.route.analysis_type == AnalysisType.TUMOR_ONLY
        assert workflow_context.route.workflow_name == "tumor_only_LUAD"
        assert "population_filtering" in workflow_context.route.processing_steps
        
        # Verify KB configuration
        kb_priorities = workflow_context.route.configuration.kb_priorities
        assert len(kb_priorities) > 0
        assert any(kb.source == EvidenceSource.ONCOKB for kb in kb_priorities)
        
        # Verify output configuration
        assert "json" in workflow_context.route.output_formats
        assert "phenopacket" in workflow_context.route.output_formats
        
    def test_tumor_normal_flow(self):
        """Test complete flow for tumor-normal analysis"""
        from annotation_engine.input_validator import InputValidator
        from annotation_engine.workflow_router import WorkflowRouter
        
        validator = InputValidator()
        router = WorkflowRouter()
        
        # Step 1: Validate input with normal VCF
        validation_result = validator.validate(
            tumor_vcf_path=Path("test_data/tumor.vcf"),
            normal_vcf_path=Path("test_data/normal.vcf"),
            patient_uid="PT002",
            case_id="CASE002",
            oncotree_code="SKCM",  # Melanoma
            tumor_purity=0.75,
            vrs_normalize=True
        )
        
        # Verify validation
        assert validation_result.is_valid
        assert validation_result.validated_input.analysis_type == "tumor_normal"
        assert validation_result.validated_input.normal_vcf is not None
        assert validation_result.validated_input.tumor_purity == 0.75
        assert validation_result.validated_input.vrs_normalize is True
        
        # Step 2: Route to workflow
        workflow_context = router.route(validation_result.validated_input)
        
        # Verify routing
        assert workflow_context.route.analysis_type == AnalysisType.TUMOR_NORMAL
        assert workflow_context.route.workflow_name == "tumor_normal_SKCM"
        assert "tumor_normal_filtering" in workflow_context.route.processing_steps
        assert "validate_pairing" in workflow_context.route.processing_steps
        
        # Verify tumor-normal specific configuration
        config = workflow_context.route.configuration
        assert config.require_somatic_evidence is True
        assert config.penalize_germline_evidence is False
        assert config.min_tumor_vaf < 0.05  # Lower threshold for T/N
        
    def test_cancer_specific_routing(self):
        """Test that cancer-specific configurations are applied"""
        from annotation_engine.input_validator import InputValidator
        from annotation_engine.workflow_router import WorkflowRouter
        
        validator = InputValidator()
        router = WorkflowRouter()
        
        # Test with melanoma (should have specific config)
        melanoma_input = validator.validate(
            tumor_vcf_path=Path("test_data/melanoma.vcf"),
            patient_uid="PT003",
            case_id="CASE003",
            oncotree_code="SKCM"
        )
        
        melanoma_context = router.route(melanoma_input.validated_input)
        
        # Get OncoKB weight for melanoma
        oncokb_melanoma = next(
            kb for kb in melanoma_context.route.configuration.kb_priorities
            if kb.source == EvidenceSource.ONCOKB
        )
        
        # Test with lung (default config)
        lung_input = validator.validate(
            tumor_vcf_path=Path("test_data/lung.vcf"),
            patient_uid="PT004",
            case_id="CASE004",
            oncotree_code="LUAD"
        )
        
        lung_context = router.route(lung_input.validated_input)
        
        # Get OncoKB weight for lung
        oncokb_lung = next(
            kb for kb in lung_context.route.configuration.kb_priorities
            if kb.source == EvidenceSource.ONCOKB
        )
        
        # Melanoma should have higher OncoKB weight
        assert oncokb_melanoma.weight > oncokb_lung.weight
        
    def test_validation_error_handling(self):
        """Test that validation errors prevent routing"""
        from annotation_engine.input_validator import InputValidator
        from annotation_engine.workflow_router import WorkflowRouter
        
        validator = InputValidator()
        router = WorkflowRouter()
        
        # Invalid OncoTree code
        validation_result = validator.validate(
            tumor_vcf_path=Path("test_data/tumor.vcf"),
            patient_uid="PT005",
            case_id="CASE005",
            oncotree_code="INVALID_CODE"
        )
        
        assert not validation_result.is_valid
        assert validation_result.validated_input is None
        assert len(validation_result.errors) > 0
        assert any("OncoTree" in error.message for error in validation_result.errors)
        
        # Should not be able to route invalid input
        with pytest.raises(AttributeError):
            router.route(validation_result.validated_input)
    
    def test_workflow_context_usage(self):
        """Test that workflow context can be used by downstream components"""
        from annotation_engine.input_validator import InputValidator
        from annotation_engine.workflow_router import WorkflowRouter
        
        validator = InputValidator()
        router = WorkflowRouter()
        
        # Create valid input
        validation_result = validator.validate(
            tumor_vcf_path=Path("test_data/tumor.vcf"),
            patient_uid="PT006",
            case_id="CASE006",
            oncotree_code="BRCA"
        )
        
        workflow_context = router.route(validation_result.validated_input)
        
        # Test context methods
        assert workflow_context.get_kb_weight(EvidenceSource.ONCOKB) > 0
        assert workflow_context.is_kb_enabled(EvidenceSource.ONCOKB) is True
        
        # Test that disabled KBs return 0 weight
        # (Assuming some KB might be disabled in config)
        disabled_weight = workflow_context.get_kb_weight(EvidenceSource.GNOMAD)
        if not workflow_context.is_kb_enabled(EvidenceSource.GNOMAD):
            assert disabled_weight == 0.0
            
        # Test execution tracking
        assert workflow_context.execution_id is not None
        assert workflow_context.start_time is not None
        assert workflow_context.processed_variants == 0  # Not yet processed


# Mock implementations for testing the interface before real implementations exist
class MockInputValidator:
    """Mock implementation for testing interfaces"""
    
    def validate(self, **kwargs) -> ValidationResult:
        # Create mock validated input
        validated_input = ValidatedInput(
            tumor_vcf=ValidatedVCF(
                path=kwargs["tumor_vcf_path"],
                sample_type=SampleType.TUMOR,
                sample_names=["TUMOR"],
                variant_count=100,
                has_genotypes=True,
                has_allele_frequencies=True,
                genome_version="GRCh38",
                normalized_chromosomes=True
            ),
            normal_vcf=None,
            patient=PatientContext(
                patient_uid=kwargs["patient_uid"],
                case_id=kwargs["case_id"],
                cancer_type=kwargs["oncotree_code"],
                cancer_display_name="Test Cancer"
            ),
            analysis_type="tumor_only",
            requested_outputs=kwargs.get("requested_outputs", ["json"]),
            validation_timestamp=datetime.utcnow().isoformat()
        )
        
        return ValidationResult(
            status=ValidationStatus.VALID,
            validated_input=validated_input
        )


class MockWorkflowRouter:
    """Mock implementation for testing interfaces"""
    
    def route(self, validated_input: ValidatedInput) -> WorkflowContext:
        # Create mock workflow context
        from annotation_engine.interfaces.workflow_interfaces import (
            WorkflowRoute,
            WorkflowConfiguration,
            KnowledgeBasePriority
        )
        
        route = WorkflowRoute(
            analysis_type=AnalysisType.TUMOR_ONLY,
            workflow_name="mock_workflow",
            configuration=WorkflowConfiguration(
                kb_priorities=[
                    KnowledgeBasePriority(
                        source=EvidenceSource.ONCOKB,
                        weight=1.0,
                        enabled=True
                    )
                ]
            ),
            processing_steps=["filter", "annotate", "tier"],
            filter_config={},
            aggregator_config={},
            tiering_config={},
            output_formats=validated_input.requested_outputs
        )
        
        return WorkflowContext(
            validated_input=validated_input,
            route=route,
            execution_id="mock-id",
            start_time=datetime.utcnow().isoformat()
        )