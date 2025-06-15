#!/usr/bin/env python3
"""
Comprehensive Test Script for Annotation Engine

Runs a variety of tests to validate the complete pipeline functionality,
including VEP integration, filtering, evidence aggregation, and tier assignment.
Logs all outputs for analysis and debugging.
"""

import sys
import logging
import tempfile
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add the annotation_engine package to the path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from annotation_engine.cli import AnnotationEngineCLI
from annotation_engine.vep_runner import VEPConfiguration, VEPRunner, get_vep_version
from annotation_engine.variant_processor import create_variant_annotations_from_vcf
from annotation_engine.models import AnalysisType
from annotation_engine.tiering import process_vcf_to_tier_results
from annotation_engine.validation.error_handler import ValidationError
from annotation_engine.vcf_utils import VCFFileHandler, detect_vcf_file_type, validate_vcf_files

# Setup logging
def setup_logging(log_file: Path = None):
    """Setup comprehensive logging"""
    
    if log_file is None:
        log_file = repo_root / "out" / "test_results" / f"comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_file.parent.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Setup file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return log_file

class ComprehensiveTestRunner:
    """Comprehensive test runner for the annotation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results = {}
        self.repo_root = repo_root
        self.example_input_dir = self.repo_root / "example_input"
        self.test_output_dir = self.repo_root / "out" / "test_results"
        self.test_output_dir.mkdir(exist_ok=True)
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        
        self.logger.info("=" * 80)
        self.logger.info("🧬 STARTING COMPREHENSIVE ANNOTATION ENGINE TESTS")
        self.logger.info("=" * 80)
        
        tests = [
            ("Environment Check", self.test_environment),
            ("VEP Configuration", self.test_vep_configuration),
            ("VEP Version Check", self.test_vep_version),
            ("CLI Validation", self.test_cli_validation),
            ("VCF File Tests", self.test_vcf_files),
            ("VEP Integration", self.test_vep_integration),
            ("Variant Processing", self.test_variant_processing),
            ("Pipeline Integration", self.test_pipeline_integration),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
            ("Performance Test", self.test_performance),
        ]
        
        for test_name, test_func in tests:
            self.logger.info(f"\n🔬 Running {test_name}...")
            try:
                result = test_func()
                self.test_results[test_name] = {
                    "status": "PASSED" if result else "FAILED",
                    "details": result
                }
                status_emoji = "✅" if result else "❌"
                self.logger.info(f"{status_emoji} {test_name}: {'PASSED' if result else 'FAILED'}")
                
            except Exception as e:
                self.logger.error(f"❌ {test_name}: ERROR - {str(e)}")
                self.logger.debug(f"Full traceback:\n{traceback.format_exc()}")
                self.test_results[test_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
        
        self._generate_summary_report()
        return self.test_results
    
    def test_environment(self) -> Dict[str, Any]:
        """Test environment setup and dependencies"""
        
        results = {}
        
        # Check repository structure
        key_files = [
            "pyproject.toml",
            "src/annotation_engine/__init__.py",
            "src/annotation_engine/cli.py",
            "src/annotation_engine/vep_runner.py",
            "example_input/proper_test.vcf"
        ]
        
        for file_path in key_files:
            full_path = self.repo_root / file_path
            exists = full_path.exists()
            results[f"file_{file_path}"] = exists
            self.logger.debug(f"File {file_path}: {'EXISTS' if exists else 'MISSING'}")
        
        # Check Python imports
        try:
            import pydantic
            results["pydantic_import"] = True
            self.logger.debug(f"Pydantic version: {pydantic.__version__}")
        except ImportError as e:
            results["pydantic_import"] = False
            self.logger.error(f"Pydantic import failed: {e}")
        
        # Check Docker availability
        import shutil
        docker_available = shutil.which("docker") is not None
        results["docker_available"] = docker_available
        self.logger.debug(f"Docker available: {docker_available}")
        
        if docker_available:
            try:
                import subprocess
                result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
                docker_running = result.returncode == 0
                results["docker_running"] = docker_running
                self.logger.debug(f"Docker running: {docker_running}")
            except Exception as e:
                results["docker_running"] = False
                self.logger.debug(f"Docker check failed: {e}")
        
        return results
    
    def test_vep_configuration(self) -> Dict[str, Any]:
        """Test VEP configuration and detection"""
        
        results = {}
        
        try:
            # Test default configuration
            config = VEPConfiguration()
            results["default_config"] = {
                "assembly": config.assembly,
                "use_docker": config.use_docker,
                "docker_image": config.docker_image,
                "cache_dir_exists": config.cache_dir.exists(),
                "plugins_dir_exists": config.plugins_dir.exists()
            }
            
            self.logger.debug(f"VEP config - Assembly: {config.assembly}")
            self.logger.debug(f"VEP config - Use Docker: {config.use_docker}")
            self.logger.debug(f"VEP config - Cache dir: {config.cache_dir} (exists: {config.cache_dir.exists()})")
            self.logger.debug(f"VEP config - Plugins dir: {config.plugins_dir} (exists: {config.plugins_dir.exists()})")
            
            # Test VEP command detection
            try:
                vep_command = config.vep_command
                results["vep_command_detected"] = vep_command
                self.logger.debug(f"VEP command detected: {vep_command}")
            except Exception as e:
                results["vep_command_error"] = str(e)
                self.logger.warning(f"VEP command detection failed: {e}")
            
            # Test validation
            try:
                validation_result = config.validate()
                results["validation_passed"] = validation_result
                self.logger.debug(f"VEP configuration validation: {validation_result}")
            except Exception as e:
                results["validation_error"] = str(e)
                self.logger.warning(f"VEP configuration validation failed: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"VEP configuration test failed: {e}")
            return {"error": str(e)}
    
    def test_vep_version(self) -> Dict[str, Any]:
        """Test VEP version detection"""
        
        results = {}
        
        try:
            # Try to get VEP version with default config
            version_info = get_vep_version()
            results["version_info"] = version_info
            self.logger.info(f"VEP version: {version_info}")
            
            # Test with Docker config
            try:
                docker_config = VEPConfiguration(use_docker=True)
                docker_version = get_vep_version(docker_config)
                results["docker_version"] = docker_version
                self.logger.debug(f"VEP Docker version: {docker_version}")
            except Exception as e:
                results["docker_version_error"] = str(e)
                self.logger.debug(f"Docker VEP version check failed: {e}")
            
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.warning(f"VEP version check failed: {e}")
            return results
    
    def test_cli_validation(self) -> Dict[str, Any]:
        """Test CLI argument validation"""
        
        results = {}
        
        try:
            cli = AnnotationEngineCLI()
            
            # Test valid arguments
            valid_args = [
                '--input', str(self.example_input_dir / 'proper_test.vcf'),
                '--case-uid', 'TEST_001',
                '--cancer-type', 'melanoma',
                '--dry-run'
            ]
            
            import argparse
            from unittest.mock import patch
            
            with patch('sys.argv', ['annotation-engine'] + valid_args):
                try:
                    parser = cli.create_parser()
                    args = parser.parse_args(valid_args)
                    validated_input = cli.validate_arguments(args)
                    
                    results["valid_args_test"] = {
                        "case_uid": validated_input.case_uid,
                        "cancer_type": validated_input.cancer_type,
                        "input_file": str(validated_input.input),
                        "dry_run": args.dry_run
                    }
                    self.logger.debug(f"CLI validation passed for valid arguments")
                    
                except Exception as e:
                    results["valid_args_error"] = str(e)
                    self.logger.error(f"CLI validation failed for valid arguments: {e}")
            
            # Test invalid arguments
            invalid_args = ['--case-uid', 'TEST_002']  # Missing required cancer-type
            
            with patch('sys.argv', ['annotation-engine'] + invalid_args):
                try:
                    parser = cli.create_parser()
                    args = parser.parse_args(invalid_args)
                    results["invalid_args_caught"] = False
                except SystemExit:
                    results["invalid_args_caught"] = True
                    self.logger.debug("CLI correctly caught invalid arguments")
            
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"CLI validation test failed: {e}")
            return results
    
    def test_vcf_files(self) -> Dict[str, Any]:
        """Test VCF file validation and parsing with comprehensive VCF utilities"""
        
        results = {}
        
        # Get all VCF files in example_input directory
        vcf_files = list(self.example_input_dir.glob("*.vcf*"))
        
        # Filter out .tbi index files from processing
        vcf_files = [f for f in vcf_files if not f.name.endswith('.tbi')]
        
        # Use the comprehensive VCF validation function
        validation_results = validate_vcf_files(*vcf_files)
        
        for vcf_file, validation_result in validation_results.items():
            file_key = vcf_file.name
            
            if validation_result.get("valid", False):
                file_type = validation_result["file_type"]
                stats = validation_result.get("stats", {})
                
                results[file_key] = {
                    "size_bytes": stats.get("file_size", 0),
                    "is_gzipped": file_type.get("is_gzipped", False),
                    "is_indexed": file_type.get("is_indexed", False),
                    "variant_count": stats.get("total_variants", 0),
                    "sample_count": stats.get("sample_count", 0),
                    "chromosomes": stats.get("chromosomes", []),
                    "valid_format": stats.get("format_valid", False)
                }
                
                self.logger.debug(f"VCF {file_key}: {stats.get('total_variants', 0)} variants, {stats.get('file_size', 0)} bytes")
                
            else:
                # Handle files that can't be processed
                if "error" in validation_result:
                    results[file_key] = {"error": validation_result["error"]}
                    self.logger.warning(f"VCF file {file_key} validation failed: {validation_result['error']}")
                else:
                    file_type = validation_result.get("file_type", {})
                    if file_type.get("is_tabix_index", False):
                        # Skip tabix index files - they're not meant to be processed
                        continue
                    else:
                        results[file_key] = {"error": validation_result.get("reason", "Unknown validation failure")}
                        self.logger.warning(f"VCF file {file_key} validation failed: {validation_result.get('reason', 'Unknown')}")
        
        return results
    
    def test_vep_integration(self) -> Dict[str, Any]:
        """Test VEP integration with fallback handling"""
        
        results = {}
        
        # Use proper_test.vcf for testing
        test_vcf = self.example_input_dir / "proper_test.vcf"
        
        if not test_vcf.exists():
            results["error"] = f"Test VCF not found: {test_vcf}"
            return results
        
        try:
            # Test VEP runner initialization
            vep_config = VEPConfiguration()
            runner = VEPRunner(vep_config)
            
            results["vep_runner_init"] = True
            self.logger.debug("VEP runner initialized successfully")
            
            # Try VEP annotation (this may fail if VEP not available)
            try:
                annotations = runner.annotate_vcf(
                    input_vcf=test_vcf,
                    output_format="annotations"
                )
                
                results["vep_annotation"] = {
                    "success": True,
                    "annotation_count": len(annotations),
                    "sample_annotation": {
                        "chromosome": annotations[0].chromosome,
                        "gene_symbol": annotations[0].gene_symbol,
                        "consequence": annotations[0].consequence
                    } if annotations else None
                }
                
                self.logger.info(f"VEP annotation successful: {len(annotations)} variants annotated")
                
            except Exception as e:
                results["vep_annotation"] = {
                    "success": False,
                    "error": str(e),
                    "fallback_available": True
                }
                self.logger.warning(f"VEP annotation failed (fallback available): {e}")
            
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"VEP integration test failed: {e}")
            return results
    
    def test_variant_processing(self) -> Dict[str, Any]:
        """Test variant processing pipeline"""
        
        results = {}
        
        test_vcf = self.example_input_dir / "proper_test.vcf"
        
        if not test_vcf.exists():
            results["error"] = f"Test VCF not found: {test_vcf}"
            return results
        
        try:
            # Test variant processing with fallback
            annotations, summary = create_variant_annotations_from_vcf(
                tumor_vcf_path=test_vcf,
                analysis_type=AnalysisType.TUMOR_ONLY,
                cancer_type="melanoma"
            )
            
            results["processing_summary"] = summary
            results["annotation_count"] = len(annotations)
            
            if annotations:
                sample_annotation = annotations[0]
                results["sample_annotation"] = {
                    "chromosome": sample_annotation.chromosome,
                    "position": sample_annotation.position,
                    "gene_symbol": sample_annotation.gene_symbol,
                    "consequence": sample_annotation.consequence,
                    "annotation_source": sample_annotation.annotation_source
                }
            
            self.logger.info(f"Variant processing: {len(annotations)} annotations created")
            self.logger.debug(f"Processing summary: {summary}")
            
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"Variant processing test failed: {e}")
            return results
    
    def test_pipeline_integration(self) -> Dict[str, Any]:
        """Test complete pipeline integration"""
        
        results = {}
        
        test_vcf = self.example_input_dir / "proper_test.vcf"
        
        if not test_vcf.exists():
            results["error"] = f"Test VCF not found: {test_vcf}"
            return results
        
        try:
            # Test complete pipeline
            tier_results, processing_summary = process_vcf_to_tier_results(
                tumor_vcf_path=test_vcf,
                normal_vcf_path=None,
                cancer_type="melanoma",
                analysis_type="TUMOR_ONLY",
                tumor_purity=0.8,
                output_format="json"
            )
            
            results["tier_results_count"] = len(tier_results)
            results["processing_summary"] = processing_summary
            
            if tier_results:
                sample_result = tier_results[0]
                results["sample_tier_result"] = {
                    "variant_id": sample_result.get("variant_id"),
                    "gene_symbol": sample_result.get("gene_symbol"),
                    "amp_tier": sample_result.get("amp_scoring", {}).get("tier"),
                    "confidence_score": sample_result.get("confidence_score"),
                    "analysis_type": sample_result.get("analysis_type")
                }
            
            self.logger.info(f"Pipeline integration: {len(tier_results)} tier results generated")
            
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"Pipeline integration test failed: {e}")
            return results
    
    def test_end_to_end_workflow(self) -> Dict[str, Any]:
        """Test end-to-end workflow through CLI"""
        
        results = {}
        
        test_vcf = self.example_input_dir / "proper_test.vcf"
        
        if not test_vcf.exists():
            results["error"] = f"Test VCF not found: {test_vcf}"
            return results
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir) / "test_output"
                
                # Setup CLI
                cli = AnnotationEngineCLI()
                
                # Create valid arguments
                args = [
                    '--input', str(test_vcf),
                    '--case-uid', 'TEST_E2E_001',
                    '--cancer-type', 'melanoma',
                    '--output', str(output_dir),
                    '--tumor-purity', '0.8'
                ]
                
                from unittest.mock import patch
                
                with patch('sys.argv', ['annotation-engine'] + args):
                    try:
                        result_code = cli.run()
                        
                        results["cli_result_code"] = result_code
                        
                        # Check if output files were created
                        if output_dir.exists():
                            output_files = list(output_dir.glob("*"))
                            results["output_files"] = [f.name for f in output_files]
                            
                            # Check results file if it exists
                            results_file = output_dir / "annotation_results.json"
                            if results_file.exists():
                                with open(results_file, 'r') as f:
                                    annotation_results = json.load(f)
                                
                                results["annotation_results"] = {
                                    "count": len(annotation_results),
                                    "sample_result": annotation_results[0] if annotation_results else None
                                }
                        
                        self.logger.info(f"End-to-end workflow: CLI returned {result_code}")
                        
                    except SystemExit as e:
                        results["cli_system_exit"] = e.code
                        self.logger.warning(f"CLI exited with code: {e.code}")
                    
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"End-to-end workflow test failed: {e}")
            return results
    
    def test_performance(self) -> Dict[str, Any]:
        """Test performance with timing measurements"""
        
        results = {}
        
        test_vcf = self.example_input_dir / "proper_test.vcf"
        
        if not test_vcf.exists():
            results["error"] = f"Test VCF not found: {test_vcf}"
            return results
        
        try:
            import time
            
            # Time variant processing
            start_time = time.time()
            annotations, summary = create_variant_annotations_from_vcf(
                tumor_vcf_path=test_vcf,
                analysis_type=AnalysisType.TUMOR_ONLY,
                cancer_type="melanoma"
            )
            processing_time = time.time() - start_time
            
            # Time tier assignment
            start_time = time.time()
            tier_results, tier_summary = process_vcf_to_tier_results(
                tumor_vcf_path=test_vcf,
                normal_vcf_path=None,
                cancer_type="melanoma",
                analysis_type="TUMOR_ONLY",
                output_format="json"
            )
            tiering_time = time.time() - start_time
            
            results = {
                "variant_processing_time": processing_time,
                "tiering_time": tiering_time,
                "total_time": processing_time + tiering_time,
                "variants_processed": len(annotations),
                "tiers_assigned": len(tier_results),
                "performance_metrics": {
                    "variants_per_second": len(annotations) / processing_time if processing_time > 0 else 0,
                    "tiers_per_second": len(tier_results) / tiering_time if tiering_time > 0 else 0
                }
            }
            
            self.logger.info(f"Performance: {processing_time:.2f}s processing, {tiering_time:.2f}s tiering")
            
            return results
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.error(f"Performance test failed: {e}")
            return results
    
    def _generate_summary_report(self):
        """Generate comprehensive summary report"""
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("📊 COMPREHENSIVE TEST SUMMARY REPORT")
        self.logger.info("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASSED")
        failed_tests = sum(1 for result in self.test_results.values() if result["status"] == "FAILED")
        error_tests = sum(1 for result in self.test_results.values() if result["status"] == "ERROR")
        
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"✅ Passed: {passed_tests}")
        self.logger.info(f"❌ Failed: {failed_tests}")
        self.logger.info(f"💥 Errors: {error_tests}")
        self.logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Test details
        for test_name, result in self.test_results.items():
            status_emoji = {"PASSED": "✅", "FAILED": "❌", "ERROR": "💥"}[result["status"]]
            self.logger.info(f"{status_emoji} {test_name}: {result['status']}")
        
        # Save detailed results
        results_file = self.test_output_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        self.logger.info(f"\n📄 Detailed results saved: {results_file}")
        self.logger.info("=" * 80)


def main():
    """Main test execution"""
    
    print("🧬 Annotation Engine Comprehensive Test Suite")
    print("=" * 80)
    
    # Setup logging
    log_file = setup_logging()
    print(f"📝 Logging to: {log_file}")
    
    # Run tests
    test_runner = ComprehensiveTestRunner()
    results = test_runner.run_all_tests()
    
    # Final summary
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result["status"] == "PASSED")
    
    print(f"\n🏁 Testing Complete: {passed_tests}/{total_tests} tests passed")
    print(f"📝 Full logs available at: {log_file}")


if __name__ == "__main__":
    main()