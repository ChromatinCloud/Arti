"""
Integration Test: Person A → Person B → Person C Complete Pipeline

Tests the complete workflow from input validation through execution with
caching, performance monitoring, and parallel processing.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

from annotation_engine.input_validator_v2 import InputValidatorV2
from annotation_engine.workflow_router import WorkflowRouter
from annotation_engine.workflow_executor import WorkflowExecutor, SimpleProgressCallback
from annotation_engine.interfaces.validation_interfaces import ValidationStatus
from annotation_engine.interfaces.execution_interfaces import ExecutionStatus, CacheStatus


class TestPersonABCIntegration:
    """Test the complete Person A → Person B → Person C pipeline"""
    
    def setup_method(self):
        """Setup test environment"""
        self.input_validator = InputValidatorV2()
        self.workflow_router = WorkflowRouter()
        self.workflow_executor = WorkflowExecutor(enable_caching=True, max_parallel_workers=2)
        
    def create_test_vcf(self, content: str) -> Path:
        """Create a temporary VCF file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".vcf", delete=False) as f:
            f.write(content)
        return Path(f.name)
    
    def test_complete_tumor_only_pipeline(self):
        """Test complete A → B → C pipeline for tumor-only analysis"""
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
chr1	12345678	.	C	G	50.0	PASS	DP=90;AF=0.40	GT:AD:DP	0/1:54,36:90
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
            
            # Verify Person A output
            assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert validation_result.validated_input is not None
            
            validated_input = validation_result.validated_input
            assert validated_input.analysis_type == "tumor_only"
            assert validated_input.tumor_vcf.variant_count == 3
            assert validated_input.export_phenopacket is True
            
            # Step 2: Person B routes workflow
            workflow_context = self.workflow_router.route(validated_input)
            
            # Verify Person B output
            assert workflow_context.route.workflow_name == "tumor_only_with_phenopacket"
            assert workflow_context.route.analysis_type.value == "tumor_only"
            assert "vep" in workflow_context.route.processing_steps
            assert "evidence_aggregation" in workflow_context.route.processing_steps
            assert "tiering" in workflow_context.route.processing_steps
            assert "phenopacket_export" in workflow_context.route.processing_steps
            
            # Step 3: Person C executes workflow
            execution_result = self.workflow_executor.execute(workflow_context)
            
            # Verify Person C output
            assert execution_result.success is True
            assert execution_result.status == ExecutionStatus.COMPLETED
            assert execution_result.annotation_results is not None
            assert execution_result.performance_metrics is not None
            
            # Check performance metrics
            metrics = execution_result.performance_metrics
            assert metrics.steps_completed > 0
            assert metrics.steps_failed == 0
            assert metrics.variants_processed == 3
            assert metrics.success_rate_percent == 100.0
            
            # Check output files
            assert "json" in execution_result.output_files
            assert "phenopacket" in execution_result.output_files
            
            # Check execution time is reasonable
            assert execution_result.duration_seconds < 10.0  # Should be fast for mock execution
            
            print(f"✅ Complete pipeline executed in {execution_result.duration_seconds:.2f}s")
            print(f"✅ Processed {metrics.variants_processed} variants")
            print(f"✅ Cache hit rate: {metrics.cache_hit_rate_percent:.1f}%")
            
        finally:
            vcf_path.unlink()
    
    def test_tumor_normal_pipeline_with_caching(self):
        """Test tumor-normal pipeline with caching optimization"""
        # Create tumor VCF
        tumor_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
chr17	41234567	.	G	A	45.0	PASS	DP=80	GT:AD:DP	0/1:52,28:80
"""
        
        # Create normal VCF
        normal_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NORMAL
chr7	140453136	.	A	T	30.0	PASS	DP=80	GT:AD:DP	0/0:80,0:80
chr17	41234567	.	G	A	25.0	PASS	DP=70	GT:AD:DP	0/0:70,0:70
"""
        
        tumor_vcf = self.create_test_vcf(tumor_vcf_content)
        normal_vcf = self.create_test_vcf(normal_vcf_content)
        
        try:
            # Person A validation
            validation_result = self.input_validator.validate(
                tumor_vcf_path=tumor_vcf,
                normal_vcf_path=normal_vcf,
                patient_uid="PT002",
                case_id="CASE002",
                oncotree_code="SKCM"
            )
            
            assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            validated_input = validation_result.validated_input
            assert validated_input.analysis_type == "tumor_normal"
            assert validated_input.normal_vcf is not None
            
            # Person B routing
            workflow_context = self.workflow_router.route(validated_input)
            assert workflow_context.route.workflow_name == "tumor_normal_standard"
            assert "somatic_calling" in workflow_context.route.processing_steps
            
            # Person C execution - first run (cache misses)
            execution_result_1 = self.workflow_executor.execute(workflow_context)
            assert execution_result_1.success is True
            
            # Check that most steps were cache misses on first run
            cache_misses_1 = sum(1 for step in execution_result_1.performance_metrics.step_metrics.values()
                               if step.cache_status == CacheStatus.MISS)
            assert cache_misses_1 > 0
            
            # Person C execution - second run (should have cache hits)
            execution_result_2 = self.workflow_executor.execute(workflow_context)
            assert execution_result_2.success is True
            
            # Check that some steps were cache hits on second run
            cache_hits_2 = sum(1 for step in execution_result_2.performance_metrics.step_metrics.values()
                             if step.cache_status == CacheStatus.HIT)
            assert cache_hits_2 > 0
            
            # Second run should be faster due to caching
            assert execution_result_2.duration_seconds <= execution_result_1.duration_seconds
            
            print(f"✅ First run: {execution_result_1.duration_seconds:.2f}s")
            print(f"✅ Second run: {execution_result_2.duration_seconds:.2f}s (with caching)")
            print(f"✅ Cache hits in second run: {cache_hits_2}")
            
        finally:
            tumor_vcf.unlink()
            normal_vcf.unlink()
    
    def test_performance_monitoring(self):
        """Test performance monitoring capabilities"""
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
            # Complete pipeline
            validation_result = self.input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT003",
                case_id="CASE003",
                oncotree_code="BRCA"
            )
            
            workflow_context = self.workflow_router.route(validation_result.validated_input)
            execution_result = self.workflow_executor.execute(workflow_context)
            
            # Verify performance metrics are collected
            metrics = execution_result.performance_metrics
            
            # Check step-level metrics
            assert len(metrics.step_metrics) > 0
            for step_name, step_result in metrics.step_metrics.items():
                assert step_result.step_name == step_name
                assert step_result.duration_seconds is not None
                assert step_result.duration_seconds >= 0
                assert step_result.memory_peak_mb is not None
                assert step_result.memory_peak_mb > 0
            
            # Check overall metrics
            assert metrics.total_duration_seconds > 0
            assert metrics.total_memory_peak_mb > 0
            assert metrics.variants_processed == 1
            
            # Check cache statistics
            cache_stats = self.workflow_executor.get_cache_stats()
            assert "hits" in cache_stats
            assert "misses" in cache_stats
            assert "hit_rate_percent" in cache_stats
            
            print(f"✅ Performance metrics collected for {len(metrics.step_metrics)} steps")
            print(f"✅ Peak memory usage: {metrics.total_memory_peak_mb:.2f} MB")
            print(f"✅ Cache statistics: {cache_stats}")
            
        finally:
            vcf_path.unlink()
    
    def test_error_handling_and_recovery(self):
        """Test error handling throughout the pipeline"""
        # Create invalid VCF (missing required fields)
        invalid_vcf_content = """##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	.	GT	0/1
"""
        
        vcf_path = self.create_test_vcf(invalid_vcf_content)
        
        try:
            # Person A should catch validation errors
            validation_result = self.input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT004",
                case_id="CASE004",
                oncotree_code="INVALID_CODE"
            )
            
            # Should fail validation
            assert validation_result.status == ValidationStatus.INVALID
            assert validation_result.validated_input is None
            assert len(validation_result.errors) > 0
            
            # Error messages should be descriptive
            error_messages = [error.message for error in validation_result.errors]
            assert any("Missing required FORMAT fields" in msg for msg in error_messages)
            assert any("Unknown OncoTree code" in msg for msg in error_messages)
            
            print("✅ Person A correctly handled validation errors")
            print(f"✅ Caught {len(validation_result.errors)} validation errors")
            
        finally:
            vcf_path.unlink()
    
    def test_parallel_processing_capabilities(self):
        """Test parallel processing capabilities"""
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
            # Setup pipeline
            validation_result = self.input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT005",
                case_id="CASE005",
                oncotree_code="LUAD",
                requested_outputs=["json", "phenopacket", "va"]
            )
            
            workflow_context = self.workflow_router.route(validation_result.validated_input)
            
            # Test parallel task execution
            def mock_task(task_id):
                time.sleep(0.1)  # Simulate work
                return f"task_{task_id}_result"
            
            tasks = [lambda i=i: mock_task(i) for i in range(5)]
            
            start_time = time.time()
            results = self.workflow_executor.execute_parallel(tasks, max_workers=3)
            parallel_duration = time.time() - start_time
            
            # Verify parallel execution worked
            assert len(results) == 5
            assert all("task_" in str(result) for result in results if result)
            
            # Should be faster than sequential (5 * 0.1 = 0.5s sequential vs ~0.2s parallel)
            assert parallel_duration < 0.4
            
            # Test step parallelization capability
            parallelizable_steps = ["evidence_aggregation", "canned_text_generation", "phenopacket_export"]
            for step in parallelizable_steps:
                assert self.workflow_executor.can_parallelize(step)
            
            print(f"✅ Parallel execution of 5 tasks completed in {parallel_duration:.2f}s")
            print(f"✅ {len(parallelizable_steps)} steps support parallelization")
            
        finally:
            vcf_path.unlink()
    
    def test_cache_invalidation_and_management(self):
        """Test cache management capabilities"""
        # Test cache operations
        cache = self.workflow_executor.cache
        
        # Test basic cache operations
        cache.set("test_key", {"data": "test_value"}, ttl_seconds=60)
        cached_value = cache.get("test_key")
        assert cached_value == {"data": "test_value"}
        
        # Test cache invalidation
        cache.invalidate("test_key")
        assert cache.get("test_key") is None
        
        # Test cache clearing
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        
        # Test pattern-based clearing
        cache.set("vep_key1", "vep_data1")
        cache.set("tiering_key1", "tiering_data1")
        cache.clear("vep")
        assert cache.get("vep_key1") is None
        assert cache.get("tiering_key1") == "tiering_data1"
        
        print("✅ Cache management operations working correctly")


class TestProgressReporting:
    """Test progress reporting capabilities"""
    
    def test_progress_callback_integration(self):
        """Test progress callback during execution"""
        
        class TestProgressCallback:
            def __init__(self):
                self.step_starts = []
                self.step_completions = []
                self.execution_complete = False
            
            def on_step_start(self, step_name: str, step_index: int, total_steps: int):
                self.step_starts.append((step_name, step_index, total_steps))
            
            def on_step_progress(self, step_name: str, progress_percent: float, message: str = ""):
                pass  # Not testing detailed progress here
            
            def on_step_complete(self, step_name: str, step_result):
                self.step_completions.append((step_name, step_result.success))
            
            def on_execution_complete(self, execution_result):
                self.execution_complete = True
        
        # Setup
        input_validator = InputValidatorV2()
        workflow_router = WorkflowRouter()
        workflow_executor = WorkflowExecutor()
        progress_callback = TestProgressCallback()
        
        # Create test VCF
        vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	140453136	.	A	T	60.0	PASS	DP=100	GT:AD:DP	0/1:55,45:100
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".vcf", delete=False) as f:
            f.write(vcf_content)
            vcf_path = Path(f.name)
        
        try:
            # Execute pipeline with progress callback
            validation_result = input_validator.validate(
                tumor_vcf_path=vcf_path,
                patient_uid="PT006",
                case_id="CASE006",
                oncotree_code="LUAD"
            )
            
            workflow_context = workflow_router.route(validation_result.validated_input)
            execution_result = workflow_executor.execute(workflow_context, progress_callback)
            
            # Verify progress callbacks were called
            assert len(progress_callback.step_starts) > 0
            assert len(progress_callback.step_completions) > 0
            assert progress_callback.execution_complete is True
            
            # Verify callback data makes sense
            for step_name, step_index, total_steps in progress_callback.step_starts:
                assert isinstance(step_name, str)
                assert isinstance(step_index, int)
                assert isinstance(total_steps, int)
                assert step_index < total_steps
            
            for step_name, success in progress_callback.step_completions:
                assert isinstance(step_name, str)
                assert isinstance(success, bool)
            
            print(f"✅ Progress callback tracked {len(progress_callback.step_starts)} step starts")
            print(f"✅ Progress callback tracked {len(progress_callback.step_completions)} step completions")
            
        finally:
            vcf_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])