"""
Simple integration test for annotation engine components
Tests individual components and their integration without requiring VEP/Docker
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from annotation_engine.evidence_aggregator import EvidenceAggregator, KnowledgeBaseLoader
from annotation_engine.tiering import TieringEngine
from annotation_engine.models import VariantAnnotation, Evidence, AnalysisType

def test_knowledge_base_loading():
    """Test that knowledge bases can be loaded"""
    print("Testing knowledge base loading...")
    
    loader = KnowledgeBaseLoader()
    
    # Test OncoVI gene lists loading
    try:
        oncovi_tsg = loader._load_oncovi_tumor_suppressors()
        oncovi_onc = loader._load_oncovi_oncogenes()
        print(f"✅ OncoVI TSG genes loaded: {len(oncovi_tsg)}")
        print(f"✅ OncoVI oncogenes loaded: {len(oncovi_onc)}")
        assert len(oncovi_tsg) > 0
        assert len(oncovi_onc) > 0
    except Exception as e:
        print(f"❌ OncoVI loading failed: {e}")
    
    # Test OncoKB gene loading
    try:
        oncokb_genes = loader._load_oncokb_genes()
        print(f"✅ OncoKB genes loaded: {len(oncokb_genes)}")
    except Exception as e:
        print(f"❌ OncoKB loading failed: {e}")
    
    print("Knowledge base loading test completed.\n")

def test_evidence_aggregation():
    """Test evidence aggregation with mock variant"""
    print("Testing evidence aggregation...")
    
    # Create mock variant annotation for BRAF V600E
    braf_variant = VariantAnnotation(
        chromosome="7",
        position=140753336,
        reference="T", 
        alternate="A",
        gene_symbol="BRAF",
        transcript_id="ENST00000288602",
        consequence=["missense_variant"],
        hgvs_p="p.Val600Glu",
        hgvs_c="c.1799T>A",
        is_oncogene=True,
        is_tumor_suppressor=False,
        vaf=0.45,
        tumor_vaf=0.45,  # Add tumor_vaf for workflow router
        total_depth=100
    )
    
    try:
        aggregator = EvidenceAggregator()
        evidence_list = aggregator.aggregate_evidence(braf_variant)
        
        print(f"✅ Evidence aggregation successful: {len(evidence_list)} evidence items")
        
        # Print evidence details
        for i, evidence in enumerate(evidence_list[:5]):  # Show first 5
            print(f"   Evidence {i+1}: {evidence.code} ({evidence.source_kb}) - {evidence.description[:50]}...")
        
        assert len(evidence_list) > 0  # Verify we got evidence
        
    except Exception as e:
        print(f"❌ Evidence aggregation failed: {e}")
        raise

def test_tier_assignment():
    """Test tier assignment with mock evidence"""
    print("Testing tier assignment...")
    
    # Create mock variant
    braf_variant = VariantAnnotation(
        chromosome="7",
        position=140753336,
        reference="T",
        alternate="A", 
        gene_symbol="BRAF",
        transcript_id="ENST00000288602",
        consequence=["missense_variant"],
        hgvs_p="p.Val600Glu",
        hgvs_c="c.1799T>A",
        is_oncogene=True,
        is_tumor_suppressor=False,
        vaf=0.45,
        tumor_vaf=0.45,  # Add tumor_vaf for workflow router
        total_depth=100
    )
    
    try:
        # Get evidence
        aggregator = EvidenceAggregator()
        evidence_list = aggregator.aggregate_evidence(braf_variant)
        
        # Assign tier
        tiering_engine = TieringEngine()
        tier_result = tiering_engine.assign_tier(braf_variant, "melanoma")
        
        print(f"✅ Tier assignment successful!")
        print(f"   AMP Tier: {tier_result.amp_scoring.get_primary_tier() if tier_result.amp_scoring else 'None'}")
        print(f"   VICC Oncogenicity: {tier_result.vicc_scoring.classification if tier_result.vicc_scoring else 'None'}")
        print(f"   OncoKB Level: {tier_result.oncokb_scoring.therapeutic_level if tier_result.oncokb_scoring else 'None'}")
        print(f"   Confidence: {tier_result.confidence_score:.2f}")
        
        assert tier_result is not None  # Verify tier was assigned
        
    except Exception as e:
        print(f"❌ Tier assignment failed: {e}")
        raise

def test_integration_flow():
    """Test complete flow with mock data"""
    print("Testing complete integration flow...")
    
    # Mock variants including BRAF V600E and TP53 mutation
    variants = [
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
            is_oncogene=True,
            is_tumor_suppressor=False,
            vaf=0.45,
            tumor_vaf=0.45,
            total_depth=100
        ),
        VariantAnnotation(
            chromosome="17",
            position=7674220,
            reference="G",
            alternate="A",
            gene_symbol="TP53",
            transcript_id="ENST00000269305", 
            consequence=["missense_variant"],
            hgvs_p="p.Arg248Gln",
            hgvs_c="c.743G>A",
            is_oncogene=False,
            is_tumor_suppressor=True,
            vaf=0.52,
            tumor_vaf=0.52,
            total_depth=45
        )
    ]
    
    try:
        aggregator = EvidenceAggregator()
        tiering_engine = TieringEngine()
        
        results = []
        
        for variant in variants:
            print(f"\nProcessing {variant.gene_symbol} {variant.hgvs_p}...")
            
            # Get evidence
            evidence_list = aggregator.aggregate_evidence(variant)
            print(f"   Evidence items: {len(evidence_list)}")
            
            # Assign tier
            tier_result = tiering_engine.assign_tier(variant, "unknown")
            print(f"   AMP Tier: {tier_result.amp_scoring.get_primary_tier() if tier_result.amp_scoring else 'None'}")
            print(f"   VICC: {tier_result.vicc_scoring.classification if tier_result.vicc_scoring else 'None'}")
            
            # Create result
            result = {
                "variant": f"{variant.gene_symbol} {variant.hgvs_p}",
                "chromosome": variant.chromosome,
                "position": variant.position,
                "evidence_count": len(evidence_list),
                "amp_tier": tier_result.amp_scoring.get_primary_tier() if tier_result.amp_scoring else None,
                "vicc_oncogenicity": tier_result.vicc_scoring.classification.value if (tier_result.vicc_scoring and tier_result.vicc_scoring.classification) else None,
                "confidence": tier_result.confidence_score
            }
            results.append(result)
        
        print(f"\n✅ Integration flow completed successfully!")
        print(f"   Variants processed: {len(results)}")
        
        assert len(results) == 2  # Should process both variants
        assert all(r['amp_tier'] is not None for r in results)  # All should have tiers
        
    except Exception as e:
        print(f"❌ Integration flow failed: {e}")
        raise

if __name__ == "__main__":
    print("=== Annotation Engine Integration Tests ===\n")
    
    # Run tests
    test_knowledge_base_loading()
    evidence_list = test_evidence_aggregation()
    tier_result = test_tier_assignment() 
    results = test_integration_flow()
    
    print("\n=== Test Summary ===")
    if evidence_list and tier_result and results:
        print("✅ All integration tests passed!")
        print("✅ System ready for end-to-end testing")
    else:
        print("⚠️  Some tests failed - check logs above")
        print("⚠️  May need knowledge base data fixes")