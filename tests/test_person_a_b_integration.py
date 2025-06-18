"""
Integration Test: Person A ↔ Person B Interface

Tests the validated interface between InputValidator (Person A) 
and WorkflowRouter (Person B) using the protocol-based contracts.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from annotation_engine.input_validator_v2 import InputValidatorV2
from annotation_engine.interfaces.validation_interfaces import (
    ValidatedInput,
    ValidationStatus,
    SampleType
)
from annotation_engine.interfaces.workflow_interfaces import (
    WorkflowRouterProtocol,
    WorkflowContext,
    WorkflowRoute,
    WorkflowConfiguration,
    AnalysisType,
    EvidenceSource,
    KnowledgeBasePriority
)


class MockWorkflowRouter:
    """Mock implementation of WorkflowRouter for testing Person A ↔ B interface"""
    
    def route(self, validated_input: ValidatedInput) -> WorkflowContext:
        """Mock workflow routing"""
        # Create workflow configuration
        kb_priorities = [
            KnowledgeBasePriority(source=EvidenceSource.ONCOKB, weight=2.0),
            KnowledgeBasePriority(source=EvidenceSource.CIVIC, weight=1.5),
            KnowledgeBasePriority(source=EvidenceSource.COSMIC, weight=1.0),
        ]
        
        config = WorkflowConfiguration(
            kb_priorities=kb_priorities,
            min_tumor_vaf=0.05,
            min_coverage=20
        )
        
        # Determine route based on analysis type and requested outputs
        if validated_input.analysis_type == "tumor_only":
            if validated_input.export_phenopacket:
                workflow_name = "tumor_only_with_phenopacket"
                processing_steps = ["vep", "evidence_aggregation", "tiering", "phenopacket_export"]
            else:
                workflow_name = "tumor_only_standard"
                processing_steps = ["vep", "evidence_aggregation", "tiering"]
        else:
            workflow_name = "tumor_normal_standard"
            processing_steps = ["vep", "somatic_calling", "evidence_aggregation", "tiering"]
        
        route = WorkflowRoute(
            analysis_type=AnalysisType(validated_input.analysis_type),
            workflow_name=workflow_name,
            configuration=config,
            processing_steps=processing_steps,
            filter_config={"min_depth": 20, "min_vaf": 0.05},
            aggregator_config={"enable_hotspots": True},
            tiering_config={"amp_guidelines": True},
            output_formats=validated_input.requested_outputs or ["json"]
        )
        
        return WorkflowContext(
            validated_input=validated_input,
            route=route,
            execution_id=f"exec_{validated_input.patient.case_id}",
            start_time="2025-01-01T12:00:00Z"
        )
    
    def execute(self, context: WorkflowContext) -> dict:
        """Mock workflow execution"""
        return {
            "execution_id": context.execution_id,
            "status": "completed",
            "outputs": {"json": f"/tmp/output_{context.execution_id}.json"},
            "metrics": {"variants_processed": 42, "duration_seconds": 120}
        }


class TestPersonABIntegration:
    """Test the integration between Person A and Person B components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.input_validator = InputValidatorV2()
        self.workflow_router = MockWorkflowRouter()
    
    def create_test_vcf(self, content: str) -> Path:
        """Create a temporary VCF file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".vcf", delete=False) as f:
            f.write(content)
        return Path(f.name)
    
    def test_tumor_only_integration_flow(self):
        """Test complete Person A → Person B flow for tumor-only analysis"""
        # Create test VCF
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
            # Step 1: Person A validates input
            validation_result = self.input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT001",
                case_id="CASE001",
                oncotree_code="LUAD",
                requested_outputs=["json", "phenopacket"]
            )
            
            # Verify validation succeeded
            assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert validation_result.validated_input is not None
            
            validated_input = validation_result.validated_input
            
            # Verify ValidatedInput has expected structure
            assert validated_input.analysis_type == "tumor_only"
            assert validated_input.patient.cancer_type == "LUAD"
            assert validated_input.patient.cancer_display_name == "Lung Adenocarcinoma"
            assert "json" in validated_input.requested_outputs
            assert "phenopacket" in validated_input.requested_outputs
            assert validated_input.export_phenopacket is True
            
            # Step 2: Person B routes validated input
            workflow_context = self.workflow_router.route(validated_input)
            
            # Verify workflow context
            assert workflow_context.validated_input == validated_input
            assert workflow_context.route.workflow_name == "tumor_only_with_phenopacket"
            assert workflow_context.route.analysis_type == AnalysisType.TUMOR_ONLY
            assert workflow_context.execution_id.startswith("exec_")
            
            # Verify routing configuration
            assert "phenopacket_export" in workflow_context.route.processing_steps
            assert "json" in workflow_context.route.output_formats
            assert "phenopacket" in workflow_context.route.output_formats
            
            # Step 3: Person B executes workflow
            workflow_result = self.workflow_router.execute(workflow_context)
            
            # Verify execution result
            assert workflow_result["status"] == "completed"
            assert "json" in workflow_result["outputs"]
            assert workflow_result["metrics"]["variants_processed"] > 0
            
        finally:
            vcf_path.unlink()
    
    def test_tumor_normal_integration_flow(self):
        """Test complete Person A → Person B flow for tumor-normal analysis"""
        # Create test VCFs
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
            # Step 1: Person A validates input
            validation_result = self.input_validator.validate(
                tumor_vcf_path=tumor_vcf,
                normal_vcf_path=normal_vcf,
                patient_uid="PT002",
                case_id="CASE002",
                oncotree_code="SKCM"
            )
            
            # Verify validation succeeded
            assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert validation_result.validated_input is not None
            
            validated_input = validation_result.validated_input
            
            # Verify ValidatedInput structure for tumor-normal
            assert validated_input.analysis_type == "tumor_normal"
            assert validated_input.normal_vcf is not None
            assert validated_input.patient.cancer_type == "SKCM"
            assert validated_input.patient.cancer_display_name == "Cutaneous Melanoma"
            
            # Step 2: Person B routes validated input
            workflow_context = self.workflow_router.route(validated_input)
            
            # Verify workflow context for tumor-normal
            assert workflow_context.route.workflow_name == "tumor_normal_standard"
            assert workflow_context.route.analysis_type == AnalysisType.TUMOR_NORMAL
            
            # Step 3: Verify that ValidatedInput provides all needed info
            assert validated_input.is_tumor_normal_pair() is True
            all_vcf_paths = validated_input.get_all_vcf_paths()
            assert len(all_vcf_paths) == 2
            assert tumor_vcf in all_vcf_paths
            assert normal_vcf in all_vcf_paths
            
        finally:
            tumor_vcf.unlink()
            normal_vcf.unlink()
    
    def test_validation_error_handling(self):
        """Test that validation errors are properly communicated to Person B"""
        # Create invalid VCF (missing required fields)
        vcf_content = """##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	.	GT	0/1
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            # Step 1: Person A attempts validation
            validation_result = self.input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT003",
                case_id="CASE003",
                oncotree_code="INVALID_CODE"  # Invalid OncoTree code
            )
            
            # Verify validation failed
            assert validation_result.status == ValidationStatus.INVALID
            assert validation_result.validated_input is None
            assert len(validation_result.errors) > 0
            
            # Verify error messages are descriptive
            error_messages = [error.message for error in validation_result.errors]
            assert any("Missing required FORMAT fields" in msg for msg in error_messages)
            assert any("Unknown OncoTree code" in msg for msg in error_messages)
            
            # Person B should not receive a ValidatedInput in this case
            # This prevents downstream processing of invalid data
            
        finally:
            vcf_path.unlink()
    
    def test_interface_contract_compliance(self):
        """Test that the interface contract is strictly followed"""
        # Create minimal valid VCF
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=50	GT:AD:DP	0/1:25,25:50
"""
        
        vcf_path = self.create_test_vcf(vcf_content)
        
        try:
            validation_result = self.input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT004",
                case_id="CASE004",
                oncotree_code="BRCA"
            )
            
            assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            validated_input = validation_result.validated_input
            
            # Verify all required ValidatedInput fields are present
            assert hasattr(validated_input, 'tumor_vcf')
            assert hasattr(validated_input, 'patient')
            assert hasattr(validated_input, 'analysis_type')
            
            # Verify ValidatedVCF has expected attributes
            tumor_vcf = validated_input.tumor_vcf
            assert hasattr(tumor_vcf, 'path')
            assert hasattr(tumor_vcf, 'sample_type')
            assert hasattr(tumor_vcf, 'variant_count')
            assert hasattr(tumor_vcf, 'genome_version')
            
            # Verify PatientContext has expected attributes
            patient = validated_input.patient
            assert hasattr(patient, 'patient_uid')
            assert hasattr(patient, 'case_id')
            assert hasattr(patient, 'cancer_type')
            assert hasattr(patient, 'cancer_display_name')
            
            # Verify interface methods work
            assert isinstance(validated_input.is_tumor_normal_pair(), bool)
            assert isinstance(validated_input.get_all_vcf_paths(), list)
            
        finally:
            vcf_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])