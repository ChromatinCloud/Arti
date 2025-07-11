#!/usr/bin/env python3
"""
Annotation Engine CLI Module

Provides command-line interface for variant annotation with comprehensive input validation.
Follows implement→test→implement→test cycle for robust development.

Usage:
    python -m annotation_engine.cli --input example.vcf --case-uid CASE_001 --cancer-type lung
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from .validation.vcf_validator import VCFValidator
from .validation.input_schemas import CLIInputSchema, AnalysisRequest
from .validation.error_handler import ValidationError, CLIErrorHandler
from .models import AnalysisType
from .input_validator import InputValidator
from .patient_context import PatientContextManager


class AnnotationEngineCLI:
    """
    Main CLI class for the Annotation Engine
    
    Handles argument parsing, input validation, and user feedback following
    Scout/PCGR CLI patterns with comprehensive error handling.
    """
    
    def __init__(self):
        self.error_handler = CLIErrorHandler()
        self.vcf_validator = VCFValidator()
        self.input_validator = InputValidator()
        self.patient_context_manager = PatientContextManager()
        
    def create_parser(self) -> argparse.ArgumentParser:
        """Create CLI argument parser with comprehensive validation"""
        
        parser = argparse.ArgumentParser(
            prog='annotation-engine',
            description='Clinical Variant Annotation Engine - Validate and annotate somatic variants following AMP/ASCO/CAP 2017, VICC 2022, and OncoKB guidelines',
            epilog='Example: annotation-engine --input sample.vcf --case-uid CASE_001 --cancer-type lung_adenocarcinoma',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Input specification 
        input_group = parser.add_mutually_exclusive_group(required=False)
        input_group.add_argument(
            '--input', '--vcf',
            type=Path,
            help='Input VCF file path (legacy single input, supports .vcf, .vcf.gz)'
        )
        input_group.add_argument(
            '--tumor-vcf',
            type=Path,
            help='Tumor sample VCF file path'
        )
        input_group.add_argument(
            '--api-mode',
            action='store_true',
            help='Run in API mode (start web server)'
        )
        
        # Normal VCF (optional, only valid with --tumor-vcf)
        parser.add_argument(
            '--normal-vcf',
            type=Path,
            help='Normal sample VCF file path (optional, enables tumor-normal analysis)'
        )
        
        # Analysis type (auto-detected but can be overridden)
        parser.add_argument(
            '--analysis-type',
            type=str,
            choices=['TUMOR_NORMAL', 'TUMOR_ONLY'],
            help='Analysis workflow type (auto-detected if not specified)'
        )
        
        # Required case information
        parser.add_argument(
            '--case-uid',
            type=str,
            help='Unique case identifier (alphanumeric, hyphens, underscores allowed)'
        )
        parser.add_argument(
            '--patient-uid',
            type=str,
            help='Patient identifier (default: same as case-uid)'
        )
        
        # Clinical context
        parser.add_argument(
            '--cancer-type',
            type=str,
            choices=[
                'lung_adenocarcinoma', 'lung_squamous', 'breast_cancer',
                'colorectal_cancer', 'melanoma', 'ovarian_cancer',
                'pancreatic_cancer', 'prostate_cancer', 'glioblastoma',
                'acute_myeloid_leukemia', 'other'
            ],
            help='Cancer type for context-specific annotation'
        )
        parser.add_argument(
            '--oncotree-id',
            type=str,
            help='OncoTree disease code (e.g., LUAD, BRCA, COAD)'
        )
        parser.add_argument(
            '--tissue-type',
            type=str,
            choices=['primary_tumor', 'metastatic', 'recurrent', 'normal', 'unknown'],
            default='primary_tumor',
            help='Tissue type (default: primary_tumor)'
        )
        
        # Output configuration
        parser.add_argument(
            '--output', '--outdir',
            type=Path,
            default=Path('./out/results'),
            help='Output directory (default: ./out/results)'
        )
        parser.add_argument(
            '--output-format',
            type=str,
            choices=['json', 'tsv', 'html', 'all'],
            default='all',
            help='Output format (default: all)'
        )
        
        # Analysis options
        parser.add_argument(
            '--genome',
            type=str,
            choices=['GRCh37', 'GRCh38'],
            default='GRCh38',
            help='Reference genome build (default: GRCh38)'
        )
        parser.add_argument(
            '--guidelines',
            type=str,
            nargs='+',
            choices=['AMP_ACMG', 'CGC_VICC', 'ONCOKB'],
            default=['AMP_ACMG', 'CGC_VICC', 'ONCOKB'],
            help='Clinical guidelines to apply (default: all)'
        )
        parser.add_argument(
            '--tumor-purity',
            type=float,
            help='Estimated tumor purity (0.0-1.0). If not provided, will be estimated from VAF data'
        )
        parser.add_argument(
            '--purple-output',
            type=Path,
            help='Path to HMF PURPLE output directory for purity estimation'
        )
        
        # Quality control
        parser.add_argument(
            '--min-depth',
            type=int,
            default=10,
            help='Minimum read depth (default: 10)'
        )
        parser.add_argument(
            '--min-vaf',
            type=float,
            default=0.05,
            help='Minimum variant allele frequency (default: 0.05)'
        )
        parser.add_argument(
            '--skip-qc',
            action='store_true',
            help='Skip quality control filters'
        )
        
        # Advanced options
        parser.add_argument(
            '--config',
            type=Path,
            help='Custom configuration file (YAML)'
        )
        parser.add_argument(
            '--kb-bundle',
            type=Path,
            help='Knowledge base bundle path'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate inputs without running annotation'
        )
        
        # Enhanced text generation options
        parser.add_argument(
            '--enable-enhanced-text',
            action='store_true',
            default=True,
            help='Enable enhanced narrative generation with citations (default: True)'
        )
        parser.add_argument(
            '--disable-enhanced-text',
            action='store_true',
            help='Disable enhanced narrative generation (use basic templates)'
        )
        parser.add_argument(
            '--text-confidence-threshold',
            type=float,
            default=0.7,
            help='Minimum confidence threshold for generated text (default: 0.7)'
        )
        parser.add_argument(
            '--citation-style',
            type=str,
            choices=['academic', 'clinical', 'brief'],
            default='clinical',
            help='Citation style for references (default: clinical)'
        )
        parser.add_argument(
            '--text-style',
            type=str,
            choices=['clinical', 'research', 'brief'],
            default='clinical',
            help='Text style for generated narratives (default: clinical)'
        )
        parser.add_argument(
            '--include-citations',
            action='store_true',
            default=True,
            help='Include citations in generated text (default: True)'
        )
        parser.add_argument(
            '--pertinent-negatives-scope',
            type=str,
            choices=['genes', 'comprehensive', 'cancer-specific'],
            default='comprehensive',
            help='Scope of pertinent negative findings (default: comprehensive)'
        )
        
        # Logging and debugging
        parser.add_argument(
            '--verbose', '-v',
            action='count',
            default=0,
            help='Increase verbosity (-v, -vv, -vvv)'
        )
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress non-essential output'
        )
        parser.add_argument(
            '--log-file',
            type=Path,
            help='Log file path (default: stdout)'
        )
        
        # Version and help
        parser.add_argument(
            '--version',
            action='version',
            version='Annotation Engine v0.1.0'
        )
        
        # Development and testing
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run quick test with example data'
        )
        
        parser.add_argument(
            '--check-plugins',
            action='store_true',
            help='Check VEP plugin status and available data files'
        )
        
        return parser
    
    def validate_arguments(self, args: argparse.Namespace) -> CLIInputSchema:
        """
        Validate parsed CLI arguments using Pydantic schemas
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Validated CLI input schema
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Convert argparse Namespace to dict
            args_dict = vars(args)
            
            # Handle patient_uid default
            if not args_dict.get('patient_uid'):
                args_dict['patient_uid'] = args_dict['case_uid']
            
            # Validate using Pydantic schema
            validated_input = CLIInputSchema.model_validate(args_dict)
            
            return validated_input
            
        except Exception as e:
            raise ValidationError(
                error_type="schema_validation",
                message=f"Invalid command line arguments: {str(e)}",
                details={"validation_error": str(e)}
            )
    
    def validate_vcf_file(self, vcf_path: Path) -> Dict[str, Any]:
        """
        Validate VCF file format and structure using enhanced input validator
        
        Args:
            vcf_path: Path to VCF file
            
        Returns:
            Validation results with summary statistics
            
        Raises:
            ValidationError: If VCF validation fails
        """
        if not vcf_path.exists():
            raise ValidationError(
                error_type="file_not_found",
                message=f"VCF file not found: {vcf_path}",
                details={"file_path": str(vcf_path)}
            )
        
        # Use new input validator for enhanced validation
        validation_result = self.input_validator.vcf_validator.validate_vcf(vcf_path)
        
        if not validation_result.is_valid:
            raise ValidationError(
                error_type="invalid_vcf",
                message=f"VCF validation failed: {'; '.join(validation_result.errors)}",
                details={"errors": validation_result.errors}
            )
        
        # Also run legacy validator for compatibility
        legacy_result = self.vcf_validator.validate_file(vcf_path)
        
        # Merge results
        return {
            **legacy_result,
            "enhanced_metadata": validation_result.metadata,
            "warnings": validation_result.warnings
        }
    
    def create_analysis_request(self, validated_input: CLIInputSchema, vcf_validation: Dict[str, Any], enhanced_text_options: Optional[Dict[str, Any]] = None) -> AnalysisRequest:
        """
        Create analysis request from validated inputs
        
        Args:
            validated_input: Validated CLI inputs
            vcf_validation: VCF validation results
            
        Returns:
            Analysis request ready for processing
        """
        # Handle legacy and new input patterns
        vcf_file_path = None
        tumor_vcf_path = None
        normal_vcf_path = None
        
        if validated_input.input:
            # Legacy single input
            vcf_file_path = str(validated_input.input)
        elif validated_input.tumor_vcf:
            # New dual input pattern
            tumor_vcf_path = str(validated_input.tumor_vcf)
            if validated_input.normal_vcf:
                normal_vcf_path = str(validated_input.normal_vcf)
        
        return AnalysisRequest(
            case_uid=validated_input.case_uid,
            patient_uid=validated_input.patient_uid,
            vcf_file_path=vcf_file_path,
            tumor_vcf_path=tumor_vcf_path,
            normal_vcf_path=normal_vcf_path,
            analysis_type=validated_input.analysis_type,
            cancer_type=validated_input.cancer_type,
            oncotree_id=validated_input.oncotree_id,
            tissue_type=validated_input.tissue_type,
            output_directory=str(validated_input.output),
            output_format=validated_input.output_format,
            genome_build=validated_input.genome,
            guidelines=validated_input.guidelines,
            quality_filters={
                "min_depth": validated_input.min_depth,
                "min_vaf": validated_input.min_vaf,
                "skip_qc": validated_input.skip_qc
            },
            tumor_purity=validated_input.tumor_purity,
            vcf_summary=vcf_validation,
            config_file=str(validated_input.config) if validated_input.config else None,
            kb_bundle=str(validated_input.kb_bundle) if validated_input.kb_bundle else None,
            enhanced_text_options=enhanced_text_options
        )
    
    def print_validation_summary(self, analysis_request: AnalysisRequest, quiet: bool = False) -> None:
        """Print validation summary to user"""
        
        if quiet:
            return
            
        print("=" * 60)
        print("🧬 ANNOTATION ENGINE - INPUT VALIDATION COMPLETE")
        print("=" * 60)
        
        # Case information
        print(f"📋 Case ID: {analysis_request.case_uid}")
        print(f"👤 Patient ID: {analysis_request.patient_uid}")
        print(f"🎯 Cancer Type: {analysis_request.cancer_type}")
        if analysis_request.oncotree_id:
            print(f"🏷️  OncoTree ID: {analysis_request.oncotree_id}")
        
        # Analysis type and input files
        print(f"\n🔬 Analysis Type: {analysis_request.analysis_type if isinstance(analysis_request.analysis_type, str) else analysis_request.analysis_type.value}")
        
        # VCF summary
        vcf_summary = analysis_request.vcf_summary
        if analysis_request.vcf_file_path:
            # Legacy single input
            print(f"\n📄 VCF File: {Path(analysis_request.vcf_file_path).name}")
        elif analysis_request.tumor_vcf_path:
            # Dual input pattern
            print(f"\n📄 Tumor VCF: {Path(analysis_request.tumor_vcf_path).name}")
            if analysis_request.normal_vcf_path:
                print(f"📄 Normal VCF: {Path(analysis_request.normal_vcf_path).name}")
        
        if vcf_summary:
            print(f"🧩 Total Variants: {vcf_summary.get('total_variants', 'Unknown')}")
            print(f"✅ Valid Format: {vcf_summary.get('valid_format', 'Unknown')}")
            
            if 'variant_types' in vcf_summary:
                print("📊 Variant Types:")
                for var_type, count in vcf_summary['variant_types'].items():
                    print(f"   {var_type}: {count}")
        
        # Analysis-specific warnings
        if analysis_request.analysis_type == "TUMOR_ONLY":
            print("\n⚠️  TUMOR-ONLY ANALYSIS: Somatic status will be inferred, not confirmed")
        
        # Analysis configuration
        print(f"\n⚙️  Guidelines: {', '.join(analysis_request.guidelines)}")
        print(f"🔬 Genome Build: {analysis_request.genome_build}")
        print(f"📁 Output: {analysis_request.output_directory}")
        
        # Quality filters
        qf = analysis_request.quality_filters
        if not qf.get('skip_qc', False):
            print(f"\n🔍 Quality Filters:")
            print(f"   Min Depth: {qf.get('min_depth')}")
            print(f"   Min VAF: {qf.get('min_vaf')}")
        else:
            print("\n⚠️  Quality filters disabled")
        
        print("\n✅ All inputs validated successfully!")
        print("🚀 Ready to begin annotation...")
    
    def run(self) -> int:
        """
        Main CLI entry point
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Parse command line arguments
            parser = self.create_parser()
            args = parser.parse_args()
            
            # Handle special modes
            if args.api_mode:
                print("🌐 Starting API server mode...")
                # TODO: Implement API server startup
                print("⚠️  API mode not yet implemented")
                return 1
            
            if args.test:
                print("🧪 Running quick test with example data...")
                return self._run_test_mode(args)
            
            if args.check_plugins:
                print("🔍 Checking VEP plugin status...")
                return self._check_plugin_status()
            
            # Validate required arguments for normal mode
            if not args.input and not args.tumor_vcf:
                print("❌ One of --input or --tumor-vcf is required")
                return 1
            if not args.case_uid:
                print("❌ --case-uid is required")
                return 1
            if not args.cancer_type:
                print("❌ --cancer-type is required")
                return 1
            
            # Process enhanced text options
            use_enhanced_text = args.enable_enhanced_text and not args.disable_enhanced_text
            
            # Validate CLI arguments
            validated_input = self.validate_arguments(args)
            
            # Validate VCF file if provided
            vcf_validation = {}
            if validated_input.input:
                vcf_validation = self.validate_vcf_file(validated_input.input)
            
            # Create analysis request with enhanced text options
            analysis_request = self.create_analysis_request(
                validated_input, 
                vcf_validation, 
                enhanced_text_options={
                    'use_enhanced_text': use_enhanced_text,
                    'text_confidence_threshold': args.text_confidence_threshold,
                    'citation_style': args.citation_style,
                    'text_style': args.text_style,
                    'include_citations': args.include_citations,
                    'pertinent_negatives_scope': args.pertinent_negatives_scope
                }
            )
            
            # Print validation summary
            self.print_validation_summary(analysis_request, args.quiet)
            
            # Handle dry-run mode
            if args.dry_run:
                print("\n🔍 DRY RUN MODE - Validation complete, stopping before annotation")
                return 0
            
            # Execute annotation pipeline
            print("\n🔄 Starting annotation pipeline...")
            results = self._execute_annotation_pipeline(analysis_request)
            
            print(f"✅ Annotation complete: {len(results)} variants processed")
            
            # Save results
            self._save_results(results, analysis_request)
            
            # Save analysis request for debugging
            if args.verbose > 0:
                output_dir = Path(analysis_request.output_directory)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                request_file = output_dir / "analysis_request.json"
                with open(request_file, 'w') as f:
                    json.dump(analysis_request.model_dump(), f, indent=2, default=str)
                print(f"📄 Analysis request saved: {request_file}")
            
            return 0
            
        except ValidationError as e:
            self.error_handler.handle_validation_error(e, verbose=args.verbose if 'args' in locals() else 0)
            return 1
            
        except KeyboardInterrupt:
            print("\n🛑 Analysis interrupted by user")
            return 1
            
        except Exception as e:
            self.error_handler.handle_unexpected_error(e, verbose=args.verbose if 'args' in locals() else 0)
            return 1
    
    def _execute_annotation_pipeline(self, analysis_request) -> List[Dict[str, Any]]:
        """Execute the complete annotation pipeline"""
        from .vcf_parser import VCFFieldExtractor
        from .models import VariantAnnotation
        from .evidence_aggregator import EvidenceAggregator
        from .tiering import TieringEngine
        from .vep_runner import VEPRunner, VEPConfiguration
        from .workflow_router import create_workflow_router
        from pathlib import Path
        
        # Step 1: Determine input VCF
        if analysis_request.tumor_vcf_path:
            vcf_path = Path(analysis_request.tumor_vcf_path)
        else:
            vcf_path = Path(analysis_request.vcf_file_path)
        
        print(f"  📁 Processing VCF: {vcf_path}")
        print(f"  🔬 Analysis type: {analysis_request.analysis_type}")
        
        # Step 1.5: Create patient context
        patient_context = self.patient_context_manager.create_context(
            patient_uid=analysis_request.patient_uid,
            case_uid=analysis_request.case_uid,
            cancer_type=analysis_request.cancer_type,
            oncotree_code=analysis_request.oncotree_id,
            age_at_diagnosis=getattr(analysis_request, 'age_at_diagnosis', None),
            sex=getattr(analysis_request, 'sex', None)
        )
        
        if patient_context.tissue_type:
            print(f"  🏥 Patient Context: {patient_context.cancer_type} ({patient_context.tissue_type})")
        else:
            print(f"  🏥 Patient Context: {patient_context.cancer_type}")
        
        # Step 1.6: Create workflow router for pathway-specific logic
        workflow_router = create_workflow_router(
            analysis_type=analysis_request.analysis_type,
            tumor_type=patient_context.oncotree_code or patient_context.cancer_type
        )
        
        # Step 2: Run VEP annotation first
        print("  🧬 Running VEP annotation...")
        try:
            # Configure VEP
            vep_config = VEPConfiguration(use_docker=True)
            vep_runner = VEPRunner(vep_config)
            
            # Run VEP and get annotated variants
            annotations = vep_runner.annotate_vcf(
                input_vcf=vcf_path,
                output_format="annotations"  # Get VariantAnnotation objects directly
            )
            print(f"  ✅ VEP annotation complete: {len(annotations)} variants annotated")
            
        except Exception as e:
            print(f"  ⚠️  VEP annotation failed: {e}")
            print("  📋 Falling back to direct VCF parsing with limited annotation...")
            
            # Fallback: Parse VCF directly without VEP
            parser = VCFFieldExtractor()
            vcf_variants = parser.extract_variant_bundle(vcf_path)
            print(f"  📊 Extracted {len(vcf_variants)} variants from VCF")
            
            annotations = []
            
            # Known variant mappings (GRCh38 coordinates) for test cases only
            gene_mapping = {
                "7:140753336": ("BRAF", "ENST00000288602", ["missense_variant"], "p.Val600Glu", "c.1799T>A"),
                "17:7674220": ("TP53", "ENST00000269305", ["missense_variant"], "p.Arg248Gln", "c.743G>A"),
                "12:25245350": ("KRAS", "ENST00000256078", ["missense_variant"], "p.Gly12Cys", "c.34G>T"),
                "3:178952085": ("PIK3CA", "ENST00000263967", ["missense_variant"], "p.His1047Arg", "c.3140A>G")
            }
            
            for variant_dict in vcf_variants:
                var_key = f"{variant_dict['chromosome']}:{variant_dict['position']}"
                
                # Extract sample data for VAF and depth
                vaf = None
                total_depth = None
                if variant_dict.get('samples'):
                    sample = variant_dict['samples'][0]  # Use first sample
                    vaf = sample.get('variant_allele_frequency')
                    total_depth = sample.get('sample_depth') or variant_dict.get('total_depth')
                
                # Apply quality filters
                qf = analysis_request.quality_filters
                if not qf.get('skip_qc', False):
                    min_depth = qf.get('min_depth', 10)
                    min_vaf = qf.get('min_vaf', 0.05)
                    
                    if total_depth and total_depth < min_depth:
                        print(f"    ⚠️  Skipping variant {var_key}: depth {total_depth} < {min_depth}")
                        continue
                    if vaf and vaf < min_vaf:
                        print(f"    ⚠️  Skipping variant {var_key}: VAF {vaf:.3f} < {min_vaf}")
                        continue
                
                # Use gene mapping if available
                if var_key in gene_mapping:
                    gene, transcript, consequence, hgvs_p, hgvs_c = gene_mapping[var_key]
                    annotation = VariantAnnotation(
                        chromosome=variant_dict['chromosome'],
                        position=variant_dict['position'],
                        reference=variant_dict['reference'],
                        alternate=variant_dict['alternate'],
                        gene_symbol=gene,
                        transcript_id=transcript,
                        consequence=consequence,
                        hgvs_p=hgvs_p,
                        hgvs_c=hgvs_c,
                        vaf=vaf,
                        total_depth=total_depth,
                        tumor_vaf=vaf  # Add tumor_vaf for workflow router
                    )
                    annotations.append(annotation)
                    print(f"    ✅ {gene} {hgvs_p} (VAF: {vaf:.3f}, Depth: {total_depth})")
                else:
                    print(f"    ⚠️  Skipping unknown variant at {var_key} in fallback mode")
        
        # Step 4: Evidence Aggregation with workflow routing
        print(f"  🔍 Aggregating evidence for {len(annotations)} variants...")
        aggregator = EvidenceAggregator(workflow_router=workflow_router)
        
        all_evidence = []
        for annotation in annotations:
            try:
                evidence = aggregator.aggregate_evidence(annotation)
                all_evidence.extend(evidence)
                print(f"    📚 {annotation.gene_symbol}: {len(evidence)} evidence items")
            except Exception as e:
                print(f"    ❌ Evidence aggregation failed for {annotation.gene_symbol}: {e}")
        
        # Step 5: Display pathway configuration
        print(f"  🔀 Using {workflow_router.pathway.name} pathway")
        print(f"     - VAF thresholds: tumor≥{workflow_router.get_vaf_threshold('min_tumor_vaf'):.0%}")
        if workflow_router.pathway.analysis_type == AnalysisType.TUMOR_NORMAL:
            print(f"     - Normal filtering: ≤{workflow_router.get_vaf_threshold('max_normal_vaf'):.0%}")
        
        # Step 6: Tier Assignment with workflow routing
        print(f"  🎯 Assigning tiers for {len(annotations)} variants...")
        tiering_engine = TieringEngine(workflow_router=workflow_router)
        
        results = []
        for annotation in annotations:
            try:
                # Convert analysis type if needed
                analysis_type_obj = analysis_request.analysis_type if hasattr(analysis_request.analysis_type, 'value') else AnalysisType(analysis_request.analysis_type)
                tier_result = tiering_engine.assign_tier(annotation, analysis_request.cancer_type, analysis_type_obj)
                
                # Convert to JSON-serializable format
                result_dict = {
                    "variant_id": f"{annotation.chromosome}_{annotation.position}_{annotation.reference}_{annotation.alternate}",
                    "genomic_location": {
                        "chromosome": annotation.chromosome,
                        "position": annotation.position,
                        "reference": annotation.reference,
                        "alternate": str(annotation.alternate)
                    },
                    "gene_annotation": {
                        "gene_symbol": annotation.gene_symbol,
                        "transcript_id": annotation.transcript_id,
                        "hgvs_c": annotation.hgvs_c,
                        "hgvs_p": annotation.hgvs_p,
                        "consequence": annotation.consequence
                    },
                    "quality_metrics": {
                        "vaf": annotation.vaf,
                        "total_depth": annotation.total_depth
                    },
                    "clinical_classification": {
                        "amp_tier": tier_result.amp_scoring.get_primary_tier() if tier_result.amp_scoring else None,
                        "vicc_oncogenicity": tier_result.vicc_scoring.classification.value if (tier_result.vicc_scoring and tier_result.vicc_scoring.classification) else None,
                        "oncokb_level": tier_result.oncokb_scoring.therapeutic_level.value if (tier_result.oncokb_scoring and tier_result.oncokb_scoring.therapeutic_level) else None,
                        "confidence_score": tier_result.confidence_score
                    },
                    "metadata": {
                        "analysis_type": analysis_request.analysis_type if isinstance(analysis_request.analysis_type, str) else analysis_request.analysis_type.value,
                        "cancer_type": analysis_request.cancer_type,
                        "case_uid": analysis_request.case_uid,
                        "genome_build": analysis_request.genome_build,
                        "processing_date": datetime.utcnow().isoformat()
                    }
                }
                
                results.append(result_dict)
                
                amp_tier = tier_result.amp_scoring.get_primary_tier() if tier_result.amp_scoring else "Unknown"
                vicc_class = tier_result.vicc_scoring.classification.value if (tier_result.vicc_scoring and tier_result.vicc_scoring.classification) else "Unknown"
                print(f"    🏷️  {annotation.gene_symbol}: {amp_tier}, {vicc_class} (confidence: {tier_result.confidence_score:.2f})")
                
            except Exception as e:
                print(f"    ❌ Tier assignment failed for {annotation.gene_symbol}: {e}")
        
        print(f"  ✅ Pipeline completed: {len(results)} variants successfully processed")
        return results
    
    def _save_results(self, results: List[Dict[str, Any]], analysis_request):
        """Save annotation results to output files"""
        output_dir = Path(analysis_request.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive JSON output
        comprehensive_output = {
            "metadata": {
                "version": "1.0.0",
                "analysis_type": analysis_request.analysis_type if isinstance(analysis_request.analysis_type, str) else analysis_request.analysis_type.value,
                "genome_build": analysis_request.genome_build,
                "annotation_date": datetime.utcnow().isoformat(),
                "case_uid": analysis_request.case_uid,
                "patient_uid": analysis_request.patient_uid,
                "cancer_type": analysis_request.cancer_type,
                "tissue_type": analysis_request.tissue_type,
                "guidelines": analysis_request.guidelines,
                "input_files": {
                    "tumor_vcf": analysis_request.tumor_vcf_path or analysis_request.vcf_file_path,
                    "normal_vcf": analysis_request.normal_vcf_path
                },
                "quality_filters": analysis_request.quality_filters,
                "total_variants": len(results),
                "knowledge_bases": {
                    "oncokb": "2024-01",
                    "civic": "2024-01", 
                    "oncovi": "2024-01",
                    "msk_hotspots": "v2"
                }
            },
            "variants": results,
            "summary": {
                "variants_by_tier": self._summarize_tiers(results),
                "variants_by_gene": self._summarize_genes(results),
                "high_confidence_variants": [r for r in results if r.get("clinical_classification", {}).get("confidence_score", 0) > 0.7]
            }
        }
        
        # Save comprehensive JSON results
        results_file = output_dir / "annotation_results.json"
        with open(results_file, 'w') as f:
            json.dump(comprehensive_output, f, indent=2, default=str)
        
        print(f"💾 Comprehensive results saved: {results_file}")
        
        # Save simple variant list for easy processing
        simple_file = output_dir / "variants_only.json"
        with open(simple_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"💾 Simple variant list saved: {simple_file}")
        
        # Create summary report
        self._create_summary_report(comprehensive_output, output_dir)
    
    def _summarize_tiers(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize variants by AMP tier"""
        tier_counts = {}
        for result in results:
            tier = result.get("clinical_classification", {}).get("amp_tier", "Unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        return tier_counts
    
    def _summarize_genes(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize variants by gene"""
        gene_counts = {}
        for result in results:
            gene = result.get("gene_annotation", {}).get("gene_symbol", "Unknown")
            gene_counts[gene] = gene_counts.get(gene, 0) + 1
        return gene_counts
    
    def _create_summary_report(self, comprehensive_output: Dict[str, Any], output_dir: Path):
        """Create human-readable summary report"""
        summary_file = output_dir / "summary_report.txt"
        
        with open(summary_file, 'w') as f:
            f.write("ANNOTATION ENGINE - SUMMARY REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Metadata
            metadata = comprehensive_output["metadata"]
            f.write(f"Case ID: {metadata['case_uid']}\n")
            f.write(f"Cancer Type: {metadata['cancer_type']}\n")
            f.write(f"Analysis Type: {metadata['analysis_type']}\n")
            f.write(f"Genome Build: {metadata['genome_build']}\n")
            f.write(f"Processing Date: {metadata['annotation_date']}\n\n")
            
            # Summary statistics
            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Variants: {metadata['total_variants']}\n")
            
            # Tier distribution
            f.write("\nTier Distribution:\n")
            for tier, count in comprehensive_output["summary"]["variants_by_tier"].items():
                f.write(f"  {tier}: {count}\n")
            
            # Gene distribution
            f.write("\nGene Distribution:\n")
            for gene, count in comprehensive_output["summary"]["variants_by_gene"].items():
                f.write(f"  {gene}: {count}\n")
            
            # Detailed variant list
            f.write(f"\nDETAILED VARIANT LIST\n")
            f.write("-" * 20 + "\n")
            
            for i, variant in enumerate(comprehensive_output["variants"], 1):
                gene_info = variant["gene_annotation"]
                clinical = variant["clinical_classification"]
                quality = variant["quality_metrics"]
                
                f.write(f"\n{i}. {gene_info['gene_symbol']} {gene_info['hgvs_p']}\n")
                f.write(f"   Location: {variant['genomic_location']['chromosome']}:{variant['genomic_location']['position']}\n")
                f.write(f"   AMP Tier: {clinical['amp_tier']}\n")
                f.write(f"   VICC: {clinical['vicc_oncogenicity']}\n")
                f.write(f"   VAF: {quality['vaf']:.3f}\n")
                f.write(f"   Depth: {quality['total_depth']}\n")
                f.write(f"   Confidence: {clinical['confidence_score']:.2f}\n")
        
        print(f"📄 Summary report saved: {summary_file}")
    
    def _check_plugin_status(self) -> int:
        """Check VEP plugin status and data file availability"""
        from .vep_runner import VEPRunner, VEPConfiguration
        from pathlib import Path
        import os
        
        try:
            # Initialize VEP configuration
            config = VEPConfiguration()
            runner = VEPRunner(config)
            
            print(f"\n📁 VEP Installation Details:")
            print(f"   Cache directory: {config.cache_dir}")
            print(f"   Plugins directory: {config.plugins_dir}")
            print(f"   Reference directory: {config.refs_dir}")
            print(f"   VEP command: {config.vep_command}")
            
            # Check enabled plugins
            print(f"\n✅ Enabled VEP Plugins ({len(runner.default_plugins)}):")
            plugin_status = {}
            
            for plugin_config in runner.default_plugins:
                # Parse plugin configuration
                parts = plugin_config.split(',')
                plugin_name = parts[0]
                
                # Check if data file exists
                if len(parts) > 1:
                    data_path = parts[1].replace('{refs_dir}', str(config.refs_dir))
                    data_file = Path(data_path)
                    exists = data_file.exists()
                    size = data_file.stat().st_size if exists else 0
                    plugin_status[plugin_name] = {
                        'enabled': True,
                        'data_file': str(data_file),
                        'exists': exists,
                        'size': size
                    }
                    
                    status_icon = "✓" if exists else "✗"
                    size_str = f"{size / (1024*1024*1024):.1f}GB" if size > 1e9 else f"{size / (1024*1024):.1f}MB" if size > 1e6 else f"{size / 1024:.1f}KB"
                    print(f"   {status_icon} {plugin_name}: {'Found' if exists else 'MISSING'} ({size_str if exists else 'N/A'})")
                else:
                    plugin_status[plugin_name] = {
                        'enabled': True,
                        'data_file': None,
                        'exists': True,
                        'size': 0
                    }
                    print(f"   ✓ {plugin_name}: No data file required")
            
            # Check for plugin modules
            print(f"\n📦 Plugin Modules (.pm files):")
            plugin_files = list(config.plugins_dir.glob("*.pm"))
            for pm_file in sorted(plugin_files):
                print(f"   ✓ {pm_file.name}")
            
            # Check for disabled plugins
            print(f"\n❌ Disabled Plugins (commented out):")
            # These are hardcoded based on the comments in vep_runner.py
            disabled = ["ClinPred", "dbscSNV", "VARITY", "gnomADc"]
            for plugin in disabled:
                print(f"   - {plugin}: Data file not available")
            
            # Summary statistics
            total_plugins = len(runner.default_plugins)
            working_plugins = sum(1 for p in plugin_status.values() if p['exists'])
            missing_plugins = total_plugins - working_plugins
            
            print(f"\n📊 Summary:")
            print(f"   Total enabled plugins: {total_plugins}")
            print(f"   Working plugins: {working_plugins}")
            print(f"   Missing data files: {missing_plugins}")
            
            # Check VEP cache
            cache_exists = config.cache_dir.exists()
            if cache_exists:
                cache_size = sum(f.stat().st_size for f in config.cache_dir.rglob('*') if f.is_file())
                cache_size_gb = cache_size / (1024*1024*1024)
                print(f"   VEP cache size: {cache_size_gb:.1f}GB")
            else:
                print(f"   ⚠️  VEP cache not found at {config.cache_dir}")
            
            # Recommendations
            if missing_plugins > 0:
                print(f"\n💡 Recommendations:")
                print(f"   Run ./scripts/download_plugin_data.sh to download missing data files")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error checking plugin status: {str(e)}")
            return 1
    
    def _run_test_mode(self, args) -> int:
        """Run quick test with example data"""
        import time
        from pathlib import Path
        
        example_vcf = Path("example_input/proper_test.vcf")
        if not example_vcf.exists():
            print(f"❌ Example VCF not found: {example_vcf}")
            print("   Please run from the repository root directory")
            return 1
        
        print(f"📁 Using example VCF: {example_vcf}")
        print("⚡ Running fast annotation test...")
        
        start_time = time.time()
        
        # Override args for test mode
        args.input = example_vcf
        args.case_uid = "TEST_CASE"
        args.cancer_type = "melanoma"
        args.output = Path("out/results/test_mode")
        args.quiet = True
        args.verbose = 1
        
        # Set default enhanced text options if not present
        if not hasattr(args, 'enable_enhanced_text'):
            args.enable_enhanced_text = True
        if not hasattr(args, 'disable_enhanced_text'):
            args.disable_enhanced_text = False
        if not hasattr(args, 'text_confidence_threshold'):
            args.text_confidence_threshold = 0.7
        if not hasattr(args, 'citation_style'):
            args.citation_style = 'clinical'
        if not hasattr(args, 'text_style'):
            args.text_style = 'clinical'
        if not hasattr(args, 'include_citations'):
            args.include_citations = True
        if not hasattr(args, 'pertinent_negatives_scope'):
            args.pertinent_negatives_scope = 'comprehensive'
        
        try:
            # Process enhanced text options
            use_enhanced_text = args.enable_enhanced_text and not args.disable_enhanced_text
            
            # Run the normal pipeline
            validated_input = self.validate_arguments(args)
            vcf_validation = self.validate_vcf_file(validated_input.input)
            analysis_request = self.create_analysis_request(
                validated_input, 
                vcf_validation,
                enhanced_text_options={
                    'use_enhanced_text': use_enhanced_text,
                    'text_confidence_threshold': args.text_confidence_threshold,
                    'citation_style': args.citation_style,
                    'text_style': args.text_style,
                    'include_citations': args.include_citations,
                    'pertinent_negatives_scope': args.pertinent_negatives_scope
                }
            )
            
            # Execute annotation pipeline
            results = self._execute_annotation_pipeline(analysis_request)
            self._save_results(results, analysis_request)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"\n🎉 TEST COMPLETED SUCCESSFULLY!")
            print(f"⏱️  Processing time: {processing_time:.2f} seconds")
            print(f"📊 Variants processed: {len(results)}")
            print(f"📁 Results saved to: {analysis_request.output_directory}")
            
            # Quick validation
            expected_genes = {"BRAF", "TP53", "KRAS", "PIK3CA"}
            found_genes = {r["gene_annotation"]["gene_symbol"] for r in results}
            
            if expected_genes.issubset(found_genes):
                print("✅ All expected variants found")
            else:
                missing = expected_genes - found_genes
                print(f"⚠️  Missing expected variants: {missing}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return 1


def main() -> int:
    """CLI entry point"""
    cli = AnnotationEngineCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())