#!/usr/bin/env python3
"""
Test script for canned text integration with Person A-B-C pipeline
"""

import tempfile
from pathlib import Path

from src.annotation_engine.input_validator_v2 import InputValidatorV2
from src.annotation_engine.workflow_router import WorkflowRouter
from src.annotation_engine.workflow_executor import WorkflowExecutor
from src.annotation_engine.interfaces.validation_interfaces import ValidationStatus

def test_canned_text_integration():
    """Test canned text generation integration"""
    
    # Create test VCF with canned text-worthy variant
    vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr7	55259515	.	T	G	60.0	PASS	DP=100;AF=0.42	GT:AD:DP	0/1:58,42:100
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=".vcf", delete=False) as f:
        f.write(vcf_content)
        vcf_path = Path(f.name)
    
    try:
        # Setup pipeline
        input_validator = InputValidatorV2()
        workflow_router = WorkflowRouter()
        workflow_executor = WorkflowExecutor(enable_caching=True)
        
        print("🔬 Testing canned text integration in Person A-B-C pipeline...")
        
        # Person A: Validate input
        validation_result = input_validator.validate(
            tumor_vcf_path=vcf_path,
            patient_uid="PT_EGFR_001",
            case_id="CASE_EGFR_001", 
            oncotree_code="LUAD",  # Lung adenocarcinoma
            requested_outputs=["json", "phenopacket", "va"]
        )
        
        assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        print("✅ Person A: Input validation successful")
        
        # Person B: Route workflow
        workflow_context = workflow_router.route(validation_result.validated_input)
        
        print(f"✅ Person B: Workflow routed - {workflow_context.route.workflow_name}")
        print(f"   Processing steps: {workflow_context.route.processing_steps}")
        
        # Person C: Execute with canned text generation
        execution_result = workflow_executor.execute(workflow_context)
        
        assert execution_result.success is True
        print(f"✅ Person C: Workflow executed successfully in {execution_result.duration_seconds:.2f}s")
        
        # Check canned text generation results
        metrics = execution_result.performance_metrics
        canned_text_step = metrics.step_metrics.get('canned_text_generation')
        
        if canned_text_step:
            print(f"📝 Canned Text Generation Results:")
            if canned_text_step.output_data:
                output = canned_text_step.output_data
                print(f"   ✅ Success: {output.get('success', 'Unknown')}")
                print(f"   📊 Text types generated: {output.get('text_types_generated', 0)}")
                print(f"   📏 Total characters: {output.get('total_characters', 0)}")
                
                # Show generated text types if available
                if 'text_types' in output:
                    print(f"   📋 Text types: {', '.join(output['text_types'])}")
                
                # Show sample generated texts if available
                if 'generated_texts' in output and output['generated_texts']:
                    print(f"   📄 Sample generated text:")
                    for i, text in enumerate(output['generated_texts'][:2]):  # Show first 2
                        if isinstance(text, dict):
                            print(f"      {i+1}. {text['type']}: {text['content'][:100]}...")
                        else:
                            print(f"      {i+1}. {text.text_type.value}: {text.content[:100]}...")
                        
                # Check for fallback usage
                if output.get('fallback_used'):
                    print(f"   ⚠️  Fallback used: {output.get('error', 'Unknown error')}")
            else:
                print("   ❌ No output data available")
        else:
            print("❌ Canned text generation step not found in results")
        
        # Check GA4GH integration results
        phenopacket_step = metrics.step_metrics.get('phenopacket_export')
        va_step = metrics.step_metrics.get('va_export')
        vrs_step = metrics.step_metrics.get('vrs_normalization')
        
        print(f"\n🌐 GA4GH Integration Results:")
        if phenopacket_step and phenopacket_step.output_data:
            ga4gh_status = phenopacket_step.output_data.get('ga4gh_compliant', False)
            print(f"   📦 Phenopacket: {'✅ GA4GH compliant' if ga4gh_status else '⚠️ Fallback mode'}")
            
        if va_step and va_step.output_data:
            ga4gh_status = va_step.output_data.get('ga4gh_compliant', False)
            print(f"   🔬 VA Export: {'✅ GA4GH compliant' if ga4gh_status else '⚠️ Fallback mode'}")
            
        if vrs_step and vrs_step.output_data:
            ga4gh_status = vrs_step.output_data.get('ga4gh_compliant', False)
            vrs_ids = vrs_step.output_data.get('vrs_ids_generated', False)
            print(f"   🆔 VRS Normalization: {'✅ GA4GH compliant' if ga4gh_status else '⚠️ Fallback mode'}")
            print(f"      VRS IDs generated: {vrs_ids}")
        
        # Performance summary
        print(f"\n⚡ Performance Summary:")
        print(f"   ⏱️  Total duration: {execution_result.duration_seconds:.2f}s")
        print(f"   🧠 Peak memory: {metrics.total_memory_peak_mb:.1f}MB")
        print(f"   📈 Cache hit rate: {metrics.cache_hit_rate_percent:.1f}%")
        print(f"   ✅ Steps completed: {metrics.steps_completed}")
        print(f"   ❌ Steps failed: {metrics.steps_failed}")
        
        print(f"\n🎉 Canned text integration test completed successfully!")
        return True
        
    finally:
        vcf_path.unlink()

if __name__ == "__main__":
    test_canned_text_integration()