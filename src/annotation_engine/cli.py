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


class AnnotationEngineCLI:
    """
    Main CLI class for the Annotation Engine
    
    Handles argument parsing, input validation, and user feedback following
    Scout/PCGR CLI patterns with comprehensive error handling.
    """
    
    def __init__(self):
        self.error_handler = CLIErrorHandler()
        self.vcf_validator = VCFValidator()
        
    def create_parser(self) -> argparse.ArgumentParser:
        """Create CLI argument parser with comprehensive validation"""
        
        parser = argparse.ArgumentParser(
            prog='annotation-engine',
            description='Clinical Variant Annotation Engine - Validate and annotate somatic variants following AMP ACMG 2017, CGC/VICC 2022, and OncoKB guidelines',
            epilog='Example: annotation-engine --input sample.vcf --case-uid CASE_001 --cancer-type lung_adenocarcinoma',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Input specification (mutually exclusive)
        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument(
            '--input', '--vcf',
            type=Path,
            help='Input VCF file path (supports .vcf, .vcf.gz)'
        )
        input_group.add_argument(
            '--api-mode',
            action='store_true',
            help='Run in API mode (start web server)'
        )
        
        # Required case information
        parser.add_argument(
            '--case-uid',
            type=str,
            required=True,
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
            required=True,
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
            default=Path('./results'),
            help='Output directory (default: ./results)'
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
            default='GRCh37',
            help='Reference genome build (default: GRCh37)'
        )
        parser.add_argument(
            '--guidelines',
            type=str,
            nargs='+',
            choices=['AMP_ACMG', 'CGC_VICC', 'ONCOKB'],
            default=['AMP_ACMG', 'CGC_VICC', 'ONCOKB'],
            help='Clinical guidelines to apply (default: all)'
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
        Validate VCF file format and structure
        
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
        
        return self.vcf_validator.validate_file(vcf_path)
    
    def create_analysis_request(self, validated_input: CLIInputSchema, vcf_validation: Dict[str, Any]) -> AnalysisRequest:
        """
        Create analysis request from validated inputs
        
        Args:
            validated_input: Validated CLI inputs
            vcf_validation: VCF validation results
            
        Returns:
            Analysis request ready for processing
        """
        return AnalysisRequest(
            case_uid=validated_input.case_uid,
            patient_uid=validated_input.patient_uid,
            vcf_file_path=str(validated_input.input) if validated_input.input else None,
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
            vcf_summary=vcf_validation,
            config_file=str(validated_input.config) if validated_input.config else None,
            kb_bundle=str(validated_input.kb_bundle) if validated_input.kb_bundle else None
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
        
        # VCF summary
        if analysis_request.vcf_file_path:
            vcf_summary = analysis_request.vcf_summary
            print(f"\n📄 VCF File: {Path(analysis_request.vcf_file_path).name}")
            print(f"🧩 Total Variants: {vcf_summary.get('total_variants', 'Unknown')}")
            print(f"✅ Valid Format: {vcf_summary.get('valid_format', 'Unknown')}")
            
            if 'variant_types' in vcf_summary:
                print("📊 Variant Types:")
                for var_type, count in vcf_summary['variant_types'].items():
                    print(f"   {var_type}: {count}")
        
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
            
            # Handle API mode separately
            if args.api_mode:
                print("🌐 Starting API server mode...")
                # TODO: Implement API server startup
                print("⚠️  API mode not yet implemented")
                return 1
            
            # Validate CLI arguments
            validated_input = self.validate_arguments(args)
            
            # Validate VCF file if provided
            vcf_validation = {}
            if validated_input.input:
                vcf_validation = self.validate_vcf_file(validated_input.input)
            
            # Create analysis request
            analysis_request = self.create_analysis_request(validated_input, vcf_validation)
            
            # Print validation summary
            self.print_validation_summary(analysis_request, args.quiet)
            
            # Handle dry-run mode
            if args.dry_run:
                print("\n🔍 DRY RUN MODE - Validation complete, stopping before annotation")
                return 0
            
            # TODO: Pass to annotation pipeline
            print("\n🔄 Annotation pipeline not yet implemented")
            print("📝 Analysis request created successfully")
            
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


def main() -> int:
    """CLI entry point"""
    cli = AnnotationEngineCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())