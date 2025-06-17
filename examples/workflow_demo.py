#!/usr/bin/env python3
"""
Demonstration of workflow router functionality
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from annotation_engine.workflow_router import create_workflow_router
from annotation_engine.models import AnalysisType, VariantAnnotation, PopulationFrequency
from annotation_engine.tiering import TieringEngine
import json


def demonstrate_tumor_normal_workflow():
    """Show tumor-normal workflow routing"""
    print("\n=== TUMOR-NORMAL WORKFLOW ===\n")
    
    # Create router for tumor-normal analysis
    router = create_workflow_router(AnalysisType.TUMOR_NORMAL, tumor_type="LUAD")
    
    # Show configuration
    summary = router.get_pathway_summary()
    print(f"Pathway: {summary['pathway_name']}")
    print(f"Tumor Type: {summary['tumor_type']}")
    print(f"VAF Thresholds:")
    for key, value in summary['vaf_thresholds'].items():
        print(f"  - {key}: {value}")
    print(f"\nTop 5 KB Priorities:")
    for i, kb in enumerate(summary['top_5_kb_priorities'], 1):
        print(f"  {i}. {kb}")
    
    # Test variant filtering
    print("\n--- Variant Filtering Examples ---")
    
    # Good somatic variant
    print("\n1. Good somatic variant (VAF: 25% tumor, 1% normal):")
    should_filter = router.should_filter_variant(tumor_vaf=0.25, normal_vaf=0.01)
    print(f"   Filter? {should_filter} ✓ PASS")
    
    # Germline variant
    print("\n2. Likely germline (VAF: 45% tumor, 40% normal):")
    should_filter = router.should_filter_variant(tumor_vaf=0.45, normal_vaf=0.40)
    print(f"   Filter? {should_filter} ✗ FILTERED")
    
    # Low VAF variant
    print("\n3. Low VAF variant (VAF: 3% tumor, 0% normal):")
    should_filter = router.should_filter_variant(tumor_vaf=0.03, normal_vaf=0.0)
    print(f"   Filter? {should_filter} ✗ FILTERED")


def demonstrate_tumor_only_workflow():
    """Show tumor-only workflow routing"""
    print("\n\n=== TUMOR-ONLY WORKFLOW ===\n")
    
    # Create router for tumor-only analysis
    router = create_workflow_router(AnalysisType.TUMOR_ONLY, tumor_type="SKCM")
    
    # Show configuration
    summary = router.get_pathway_summary()
    print(f"Pathway: {summary['pathway_name']}")
    print(f"Tumor Type: {summary['tumor_type']}")
    print(f"VAF Thresholds:")
    for key, value in summary['vaf_thresholds'].items():
        print(f"  - {key}: {value}")
    print(f"\nTop 5 KB Priorities:")
    for i, kb in enumerate(summary['top_5_kb_priorities'], 1):
        print(f"  {i}. {kb}")
    
    # Test variant filtering
    print("\n--- Variant Filtering Examples ---")
    
    # Good somatic variant
    print("\n1. Good somatic variant (VAF: 25%, PopAF: 0.001%):")
    should_filter = router.should_filter_variant(tumor_vaf=0.25, population_af=0.00001)
    print(f"   Filter? {should_filter} ✓ PASS")
    
    # Common variant
    print("\n2. Common variant (VAF: 25%, PopAF: 2%):")
    should_filter = router.should_filter_variant(tumor_vaf=0.25, population_af=0.02)
    print(f"   Filter? {should_filter} ✗ FILTERED")
    
    # Low VAF (stricter for tumor-only)
    print("\n3. Low VAF variant (VAF: 8%):")
    should_filter = router.should_filter_variant(tumor_vaf=0.08, population_af=0.0)
    print(f"   Filter? {should_filter} ✗ FILTERED")
    
    # Hotspot with population frequency
    print("\n4. Hotspot variant (VAF: 15%, PopAF: 0.2%):")
    should_filter = router.should_filter_variant(tumor_vaf=0.15, population_af=0.002, is_hotspot=True)
    print(f"   Filter? {should_filter} ✓ PASS (hotspot exception)")


def demonstrate_evidence_adjustment():
    """Show how evidence scores are adjusted by pathway"""
    print("\n\n=== EVIDENCE WEIGHT ADJUSTMENT ===\n")
    
    # Sample evidence
    evidence_list = [
        {"source_kb": "OncoKB", "score": 10, "description": "FDA-approved therapy"},
        {"source_kb": "gnomAD", "score": 5, "description": "Population frequency 0.1%"},
        {"source_kb": "COSMIC_Hotspot", "score": 8, "description": "Recurrent hotspot"},
        {"source_kb": "REVEL", "score": 6, "description": "Pathogenic prediction"},
    ]
    
    print("Original Evidence Scores:")
    for e in evidence_list:
        print(f"  - {e['source_kb']}: {e['score']} ({e['description']})")
    
    # Tumor-normal adjustment
    print("\n--- Tumor-Normal Pathway Adjustment ---")
    tn_router = create_workflow_router(AnalysisType.TUMOR_NORMAL)
    tn_adjusted = tn_router.adjust_evidence_scores(evidence_list)
    
    for e in tn_adjusted:
        weight = e.get('pathway_weight', 1.0)
        adjusted = e.get('adjusted_score', e['score'])
        print(f"  - {e['source_kb']}: {e['score']} → {adjusted:.1f} (weight: {weight})")
    
    # Tumor-only adjustment
    print("\n--- Tumor-Only Pathway Adjustment ---")
    to_router = create_workflow_router(AnalysisType.TUMOR_ONLY)
    to_adjusted = to_router.adjust_evidence_scores(evidence_list)
    
    for e in to_adjusted:
        weight = e.get('pathway_weight', 1.0)
        adjusted = e.get('adjusted_score', e['score'])
        print(f"  - {e['source_kb']}: {e['score']} → {adjusted:.1f} (weight: {weight})")
    
    print("\nNote: gnomAD weight increases from 0.2 to 0.7 in tumor-only mode!")


def demonstrate_clonality():
    """Show VAF clonality classification"""
    print("\n\n=== CLONALITY CLASSIFICATION ===\n")
    
    router = create_workflow_router(AnalysisType.TUMOR_NORMAL)
    
    test_vafs = [0.10, 0.20, 0.30, 0.40, 0.50]
    
    print("VAF → Clonality:")
    for vaf in test_vafs:
        clonality = router.classify_vaf_clonality(vaf)
        print(f"  {vaf:.0%} → {clonality}")
    
    print(f"\nThresholds:")
    print(f"  - Subclonal: ≤{router.get_vaf_threshold('subclonal_threshold'):.0%}")
    print(f"  - Clonal: ≥{router.get_vaf_threshold('clonal_threshold'):.0%}")


if __name__ == "__main__":
    print("=" * 60)
    print("WORKFLOW ROUTER DEMONSTRATION")
    print("=" * 60)
    
    demonstrate_tumor_normal_workflow()
    demonstrate_tumor_only_workflow()
    demonstrate_evidence_adjustment()
    demonstrate_clonality()
    
    print("\n" + "=" * 60)
    print("✓ Workflow router successfully routes variants through")
    print("  pathway-specific filtering and evidence weighting!")
    print("=" * 60)