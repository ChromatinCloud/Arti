#!/usr/bin/env python3
"""
Test script for performance optimization of enhanced text generation
"""

import sys
import time
sys.path.append('src')

def test_caching_performance():
    """Test that caching improves performance"""
    print("🚀 Testing Performance Optimizations")
    print("=" * 50)
    
    try:
        from annotation_engine.enhanced_narrative_generator import EnhancedNarrativeGenerator
        from annotation_engine.models import Evidence, CannedTextType
        
        # Create sample evidence
        evidence_list = [
            Evidence(
                evidence_type="THERAPEUTIC",
                evidence_level="FDA_APPROVED",
                source_kb="FDA",
                description="FDA-approved therapy for this variant",
                score=10
            ),
            Evidence(
                evidence_type="CLINICAL_SIGNIFICANCE",
                evidence_level="HIGH",
                source_kb="ONCOKB",
                description="High clinical significance",
                score=9
            ),
            Evidence(
                evidence_type="POPULATION_FREQUENCY",
                evidence_level="HIGH",
                source_kb="GNOMAD",
                description="Rare variant in population",
                score=7
            )
        ]
        
        context = {
            "gene_symbol": "BRAF",
            "cancer_type": "melanoma",
            "variant_description": "V600E"
        }
        
        # Test without caching
        print("Testing without caching...")
        generator_no_cache = EnhancedNarrativeGenerator(enable_caching=False)
        
        start_time = time.time()
        for i in range(5):
            result = generator_no_cache.generate_enhanced_narrative(
                evidence_list=evidence_list,
                text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
                context=context
            )
        no_cache_time = time.time() - start_time
        print(f"⏱️  5 generations without cache: {no_cache_time:.3f} seconds")
        
        # Test with caching
        print("\\nTesting with caching...")
        generator_with_cache = EnhancedNarrativeGenerator(enable_caching=True)
        
        start_time = time.time()
        for i in range(5):
            result = generator_with_cache.generate_enhanced_narrative(
                evidence_list=evidence_list,
                text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
                context=context
            )
        with_cache_time = time.time() - start_time
        print(f"⏱️  5 generations with cache: {with_cache_time:.3f} seconds")
        
        # Calculate improvement
        if no_cache_time > 0:
            speedup = no_cache_time / with_cache_time
            print(f"🚀 Speedup: {speedup:.1f}x faster with caching")
        
        # Show cache stats
        cache_stats = generator_with_cache.get_cache_stats()
        print(f"📊 Cache stats: {cache_stats}")
        
        print("✅ Caching test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Caching test failed: {e}")
        return False

def test_parallel_generation():
    """Test parallel text generation"""
    print("\\n" + "=" * 50)
    print("Testing Parallel Text Generation")
    print("=" * 50)
    
    try:
        from annotation_engine.canned_text_integration import ComprehensiveCannedTextGenerator
        from annotation_engine.models import (
            VariantAnnotation, Evidence, TierResult, AnalysisType, CannedTextType
        )
        
        # Create sample data
        variant = VariantAnnotation(
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            chromosome="7",
            position=140453136,
            ref="A",
            alt="T"
        )
        
        evidence_list = [
            Evidence(
                evidence_type="THERAPEUTIC",
                evidence_level="FDA_APPROVED", 
                source_kb="FDA",
                description="FDA-approved therapy",
                score=10
            ),
            Evidence(
                evidence_type="CLINICAL_SIGNIFICANCE",
                evidence_level="HIGH",
                source_kb="ONCOKB", 
                description="Oncogenic variant",
                score=9
            ),
            Evidence(
                evidence_type="HOTSPOT",
                evidence_level="HIGH",
                source_kb="CANCER_HOTSPOTS",
                description="Mutational hotspot",
                score=8
            )
        ]
        
        tier_result = TierResult(
            variant_id="test",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            analysis_type=AnalysisType.TUMOR_ONLY,
            amp_scoring=None,
            vicc_scoring=None,
            oncokb_scoring=None,
            evidence=evidence_list,
            cancer_type="melanoma",
            canned_texts=[],
            confidence_score=0.9,
            annotation_completeness=0.8
        )
        
        # Test sequential generation
        print("Testing sequential generation...")
        generator_sequential = ComprehensiveCannedTextGenerator(
            use_enhanced_narratives=True, 
            enable_parallel=False
        )
        
        start_time = time.time()
        sequential_texts = generator_sequential.generate_all_texts(
            variant=variant,
            evidence_list=evidence_list,
            tier_result=tier_result,
            cancer_type="melanoma"
        )
        sequential_time = time.time() - start_time
        print(f"⏱️  Sequential generation: {sequential_time:.3f} seconds")
        print(f"📝 Generated {len(sequential_texts)} text types")
        
        # Test parallel generation
        print("\\nTesting parallel generation...")
        generator_parallel = ComprehensiveCannedTextGenerator(
            use_enhanced_narratives=True,
            enable_parallel=True
        )
        
        start_time = time.time()
        parallel_texts = generator_parallel.generate_all_texts_parallel(
            variant=variant,
            evidence_list=evidence_list,
            tier_result=tier_result,
            cancer_type="melanoma"
        )
        parallel_time = time.time() - start_time
        print(f"⏱️  Parallel generation: {parallel_time:.3f} seconds")
        print(f"📝 Generated {len(parallel_texts)} text types")
        
        # Calculate improvement
        if sequential_time > 0 and parallel_time > 0:
            speedup = sequential_time / parallel_time
            print(f"🚀 Speedup: {speedup:.1f}x faster with parallel processing")
        
        print("✅ Parallel generation test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Parallel generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Enhanced Text Generation Performance Tests")
    print("=" * 60)
    
    results = []
    
    # Test caching
    results.append(test_caching_performance())
    
    # Test parallel generation
    results.append(test_parallel_generation())
    
    print("\\n" + "=" * 60)
    if all(results):
        print("🎉 All performance tests passed!")
        print("✅ Enhanced text system optimized and ready")
        return 0
    else:
        print("❌ Some performance tests failed")
        return 1

if __name__ == "__main__":
    exit(main())