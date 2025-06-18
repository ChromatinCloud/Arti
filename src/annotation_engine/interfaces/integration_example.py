"""
Integration Example: Input Validator → Workflow Router

This file demonstrates how Person A and Person B's components interact
through the defined interfaces. This serves as both documentation and
integration test template.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

# These imports define the contract between components
from .validation_interfaces import (
    ValidatedInput, 
    ValidationResult,
    ValidationStatus,
    InputValidatorProtocol
)
from .workflow_interfaces import (
    WorkflowContext,
    WorkflowRouterProtocol,
    AnalysisType
)


def example_integration_flow():
    """
    Example showing how components interact
    
    This is the expected flow that will happen in cli.py
    """
    # Step 1: Person A's Input Validator validates raw input
    validator: InputValidatorProtocol = get_input_validator()  # Person A implements
    
    validation_result: ValidationResult = validator.validate(
        tumor_vcf_path=Path("/path/to/tumor.vcf"),
        patient_uid="PT001",
        case_id="CASE001", 
        oncotree_code="LUAD",
        normal_vcf_path=Path("/path/to/normal.vcf"),  # Optional
        tumor_purity=0.75,  # Optional
        requested_outputs=["json", "phenopacket"]
    )
    
    # Step 2: Check validation results
    if not validation_result.is_valid:
        # Handle validation errors
        for error in validation_result.errors:
            print(f"Validation error: {error.field} - {error.message}")
        return
    
    # Step 3: Get validated input
    validated_input: ValidatedInput = validation_result.validated_input
    
    # Step 4: Person B's Workflow Router determines the workflow
    router: WorkflowRouterProtocol = get_workflow_router()  # Person B implements
    
    workflow_context: WorkflowContext = router.route(validated_input)
    
    # Step 5: Use workflow context for downstream processing
    print(f"Analysis type: {workflow_context.route.analysis_type}")
    print(f"Workflow: {workflow_context.route.workflow_name}")
    print(f"Processing steps: {workflow_context.route.processing_steps}")
    
    # The workflow context now contains everything needed for:
    # - Filtering (filter_config)
    # - Evidence aggregation (aggregator_config, KB priorities)
    # - Tiering (tiering_config)
    # - Output formatting (output_formats)
    
    return workflow_context


def example_cli_integration():
    """
    Example of how cli.py will use these interfaces
    
    This shows the minimal integration needed in the CLI
    """
    from annotation_engine.cli import parse_arguments
    
    # Parse CLI arguments
    args = parse_arguments()
    
    # Initialize components (these will be imported from actual implementations)
    validator = get_input_validator()
    router = get_workflow_router()
    
    # Validate input
    validation_result = validator.validate(
        tumor_vcf_path=args.tumor_vcf or args.input,  # Support legacy --input
        patient_uid=args.patient_uid,
        case_id=args.case_uid,  # Map legacy argument
        oncotree_code=args.oncotree_code or args.cancer_type,
        normal_vcf_path=args.normal_vcf,
        tumor_purity=args.tumor_purity,
        purple_output_dir=args.purple_output,
        requested_outputs=_parse_output_formats(args),
        vrs_normalize=args.vrs_normalize,
        export_phenopacket=args.output_format == "phenopacket",
        export_va=args.export_va
    )
    
    if not validation_result.is_valid:
        _handle_validation_errors(validation_result)
        return 1
    
    # Route to appropriate workflow
    workflow_context = router.route(validation_result.validated_input)
    
    # Pass to existing pipeline with workflow context
    from annotation_engine.main import run_annotation_pipeline
    
    results = run_annotation_pipeline(workflow_context)
    
    return 0


def _parse_output_formats(args) -> list:
    """Helper to parse requested output formats from CLI args"""
    formats = ["json"]  # Always include JSON
    
    if args.output_format:
        formats.append(args.output_format)
    if args.export_phenopacket:
        formats.append("phenopacket")
    if args.export_va:
        formats.append("va")
        
    return list(set(formats))  # Remove duplicates


def _handle_validation_errors(validation_result: ValidationResult):
    """Helper to display validation errors"""
    import sys
    
    print("Input validation failed:", file=sys.stderr)
    for message in validation_result.get_all_messages():
        print(f"  {message}", file=sys.stderr)


# Stub functions for the example (will be replaced with real implementations)
def get_input_validator() -> InputValidatorProtocol:
    """
    Person A will implement:
    from annotation_engine.input_validator import InputValidator
    return InputValidator()
    """
    raise NotImplementedError("Person A implements this")


def get_workflow_router() -> WorkflowRouterProtocol:
    """
    Person B will implement:
    from annotation_engine.workflow_router import WorkflowRouter
    return WorkflowRouter()
    """
    raise NotImplementedError("Person B implements this")


# Example of how existing components will be updated
def example_evidence_aggregator_update():
    """
    Shows how evidence_aggregator.py will be updated to use workflow context
    """
    from annotation_engine.evidence_aggregator import EvidenceAggregator
    
    class WorkflowAwareEvidenceAggregator(EvidenceAggregator):
        """Enhanced aggregator that respects workflow configuration"""
        
        def aggregate_evidence(self, variant, workflow_context: WorkflowContext):
            """Updated method signature to accept workflow context"""
            
            # Get KB priorities from workflow
            kb_priorities = workflow_context.route.configuration.kb_priorities
            
            # Collect evidence respecting workflow configuration
            all_evidence = []
            for kb_config in kb_priorities:
                if not kb_config.enabled:
                    continue
                    
                # Get evidence from this source
                evidence = self._get_evidence_from_source(
                    variant, 
                    kb_config.source
                )
                
                # Apply weight multiplier
                for e in evidence:
                    e.score *= kb_config.weight
                    
                all_evidence.extend(evidence)
            
            return all_evidence


def example_tiering_update():
    """
    Shows how tiering.py will be updated to use workflow context
    """
    from annotation_engine.tiering import TieringEngine
    
    class WorkflowAwareTieringEngine(TieringEngine):
        """Enhanced tiering engine that respects workflow configuration"""
        
        def assign_tier(self, variant, evidence, workflow_context: WorkflowContext):
            """Updated method signature to accept workflow context"""
            
            config = workflow_context.route.configuration
            
            # Apply workflow-specific rules
            if config.require_somatic_evidence:
                # Filter evidence to somatic only
                evidence = [e for e in evidence if self._is_somatic_evidence(e)]
            
            if config.boost_hotspot_variants and variant.is_hotspot:
                # Boost scoring for hotspot variants
                for e in evidence:
                    e.score *= 1.5
            
            # Continue with normal tiering logic
            return super().assign_tier(variant, evidence)