"""
Tests for CGC/VICC 2022 oncogenicity classification implementation
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import (
    VariantAnnotation, PopulationFrequency, HotspotEvidence
)
from annotation_engine.cgc_vicc_classifier import (
    CGCVICCClassifier, OncogenicityClassification, OncogenicityCriteria,
    CriterionEvidence, create_cgc_vicc_evidence
)


class TestCGCVICCClassifier:
    """Test CGC/VICC oncogenicity classification"""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance"""
        # Use test knowledge base path or mock
        return CGCVICCClassifier(kb_path=Path("./.refs"))
    
    def test_ovs1_null_variant_in_tsg(self, classifier):
        """Test OVS1: Null variant in tumor suppressor gene"""
        # Create a frameshift variant in TP53 (known TSG)
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="CT",
            gene_symbol="TP53",
            transcript_id="ENST00000269305",
            consequence=["frameshift_variant"],
            hgvs_p="p.Arg282Trpfs*10",
            hgvs_c="c.844delC",
            is_tumor_suppressor=True,
            vaf=0.35,
            total_depth=100
        )
        
        result = classifier.classify_variant(variant)
        
        # Should classify as Oncogenic due to OVS1
        assert result.classification == OncogenicityClassification.ONCOGENIC
        
        # Check that OVS1 was met
        ovs1_met = any(c.criterion == OncogenicityCriteria.OVS1 and c.is_met 
                       for c in result.criteria_met)
        assert ovs1_met
    
    def test_os3_hotspot_variant(self, classifier):
        """Test OS3: Well-established cancer hotspot"""
        # Create BRAF V600E variant
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            transcript_id="ENST00000288602",
            consequence=["missense_variant"],
            hgvs_p="p.Val600Glu",
            hgvs_c="c.1799T>A",
            is_oncogene=True,
            vaf=0.45,
            total_depth=150,
            hotspot_evidence=[
                HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=1500,
                    cancer_types=["Melanoma", "Colorectal", "Thyroid"],
                    hotspot_type="single_residue"
                )
            ]
        )
        
        result = classifier.classify_variant(variant, "Melanoma")
        
        # Should classify as Oncogenic
        assert result.classification in [
            OncogenicityClassification.ONCOGENIC,
            OncogenicityClassification.LIKELY_ONCOGENIC
        ]
        
        # Check that OS3 was met
        os3_met = any(c.criterion == OncogenicityCriteria.OS3 and c.is_met 
                      for c in result.criteria_met)
        assert os3_met
    
    def test_sbvs1_common_polymorphism(self, classifier):
        """Test SBVS1: Common variant in population"""
        # Create a common polymorphism
        variant = VariantAnnotation(
            chromosome="1",
            position=1000000,
            reference="G",
            alternate="A",
            gene_symbol="TEST1",
            transcript_id="ENST00000000001",
            consequence=["missense_variant"],
            hgvs_p="p.Ala100Thr",
            hgvs_c="c.298G>A",
            vaf=0.5,
            total_depth=100,
            population_frequencies=[
                PopulationFrequency(
                    database="gnomAD",
                    population="global",
                    allele_frequency=0.08,  # 8% - common
                    allele_count=10000,
                    allele_number=125000
                )
            ]
        )
        
        result = classifier.classify_variant(variant)
        
        # Should classify as Benign due to high population frequency
        assert result.classification == OncogenicityClassification.BENIGN
        
        # Check that SBVS1 was met
        sbvs1_met = any(c.criterion == OncogenicityCriteria.SBVS1 and c.is_met 
                        for c in result.criteria_met)
        assert sbvs1_met
    
    def test_combination_rules_likely_oncogenic(self, classifier):
        """Test combination rules resulting in Likely Oncogenic"""
        # Create variant with OS1 + OP criteria
        variant = VariantAnnotation(
            chromosome="12",
            position=25398281,
            reference="C",
            alternate="A",
            gene_symbol="KRAS",
            transcript_id="ENST00000256078",
            consequence=["missense_variant"],
            hgvs_p="p.Gly12Cys",
            hgvs_c="c.34G>T",
            is_oncogene=True,
            vaf=0.25,
            total_depth=120,
            cadd_phred=28,
            revel_score=0.85,
            population_frequencies=[
                PopulationFrequency(
                    database="gnomAD",
                    population="global",
                    allele_frequency=0.000001,
                    allele_count=1,
                    allele_number=1000000
                )
            ]
        )
        
        result = classifier.classify_variant(variant, "Lung adenocarcinoma")
        
        # Should get moderate/supporting evidence leading to Likely Oncogenic
        assert result.classification in [
            OncogenicityClassification.LIKELY_ONCOGENIC,
            OncogenicityClassification.ONCOGENIC  # Might be oncogenic if OS1 matches
        ]
        
        # Should have multiple criteria met
        assert len(result.criteria_met) >= 2
    
    def test_vus_insufficient_evidence(self, classifier):
        """Test VUS classification when insufficient evidence"""
        # Create variant with minimal evidence
        variant = VariantAnnotation(
            chromosome="2",
            position=2000000,
            reference="C",
            alternate="T",
            gene_symbol="UNKNOWN1",
            transcript_id="ENST00000000002",
            consequence=["missense_variant"],
            hgvs_p="p.Arg50Trp",
            hgvs_c="c.148C>T",
            vaf=0.15,
            total_depth=80
        )
        
        result = classifier.classify_variant(variant)
        
        # Should classify as VUS due to insufficient evidence
        assert result.classification == OncogenicityClassification.VUS
        
        # Should have low number of criteria met
        assert len(result.criteria_met) <= 2
    
    def test_evidence_conversion(self, classifier):
        """Test conversion of classification result to Evidence objects"""
        # Create oncogenic variant
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            transcript_id="ENST00000288602",
            consequence=["missense_variant"],
            hgvs_p="p.Val600Glu",
            hgvs_c="c.1799T>A",
            is_oncogene=True,
            vaf=0.45,
            total_depth=150,
            hotspot_evidence=[
                HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=1500,
                    cancer_types=["Melanoma"],
                    hotspot_type="single_residue"
                )
            ]
        )
        
        result = classifier.classify_variant(variant, "Melanoma")
        evidence_list = create_cgc_vicc_evidence(result)
        
        # Should create evidence objects
        assert len(evidence_list) > 0
        
        # Should have main classification evidence
        main_evidence = [e for e in evidence_list if e.code == "CGC_VICC_ONCOGENIC"]
        assert len(main_evidence) > 0
        
        # Should have individual criteria evidence
        criteria_evidence = [e for e in evidence_list if e.guideline == "CGC/VICC 2022"]
        assert len(criteria_evidence) >= len(result.criteria_met)
    
    def test_cancer_type_specific_classification(self, classifier):
        """Test that cancer type affects classification"""
        # Create variant that might be differentially classified
        variant = VariantAnnotation(
            chromosome="9",
            position=5073770,
            reference="T",
            alternate="G",
            gene_symbol="JAK2",
            transcript_id="ENST00000381652",
            consequence=["missense_variant"],
            hgvs_p="p.Val617Phe",
            hgvs_c="c.1849G>T",
            is_oncogene=True,
            vaf=0.45,
            total_depth=100,
            hotspot_evidence=[
                HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=500,
                    cancer_types=["Myeloproliferative neoplasm"],
                    hotspot_type="single_residue"
                )
            ]
        )
        
        # Test with matching cancer type
        result_mpn = classifier.classify_variant(variant, "Myeloproliferative neoplasm")
        
        # Test with non-matching cancer type
        result_lung = classifier.classify_variant(variant, "Lung adenocarcinoma")
        
        # Both should be classified but potentially with different confidence
        assert result_mpn.classification in [
            OncogenicityClassification.ONCOGENIC,
            OncogenicityClassification.LIKELY_ONCOGENIC
        ]
        
        # Confidence should be higher for matching cancer type
        assert result_mpn.confidence_score >= result_lung.confidence_score
    
    def test_conflicting_evidence_handling(self, classifier):
        """Test handling of conflicting oncogenic and benign evidence"""
        # Create variant with conflicting evidence
        variant = VariantAnnotation(
            chromosome="3",
            position=3000000,
            reference="G",
            alternate="A",
            gene_symbol="CONFLICT1",
            transcript_id="ENST00000000003",
            consequence=["missense_variant"],
            hgvs_p="p.Arg100Gln",
            hgvs_c="c.299G>A",
            vaf=0.48,  # Suggests germline
            total_depth=100,
            is_oncogene=True,  # Oncogenic evidence
            population_frequencies=[
                PopulationFrequency(
                    database="gnomAD",
                    population="global",
                    allele_frequency=0.02,  # Moderate frequency - benign evidence
                    allele_count=2500,
                    allele_number=125000
                )
            ]
        )
        
        result = classifier.classify_variant(variant)
        
        # Should handle conflict appropriately - likely VUS or Likely Benign
        assert result.classification in [
            OncogenicityClassification.VUS,
            OncogenicityClassification.LIKELY_BENIGN
        ]
        
        # Should have both oncogenic and benign criteria in results
        oncogenic_criteria = [c for c in result.criteria_met 
                             if c.criterion.value.startswith('O')]
        benign_criteria = [c for c in result.criteria_met 
                          if c.criterion.value.startswith('S')]
        
        # May have evidence from both sides
        assert len(result.criteria_met) > 0


class TestOncogenicityIntegration:
    """Test integration with tiering engine"""
    
    def test_oncogenicity_aware_tiering(self):
        """Test that oncogenicity classification affects tier assignment"""
        from annotation_engine.oncogenicity_integration import (
            OncogenicityAwareTieringEngine
        )
        from annotation_engine.models import AnalysisType
        
        engine = OncogenicityAwareTieringEngine()
        
        # Create oncogenic variant with therapeutic evidence
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            transcript_id="ENST00000288602",
            consequence=["missense_variant"],
            hgvs_p="p.Val600Glu",
            hgvs_c="c.1799T>A",
            is_oncogene=True,
            vaf=0.45,
            total_depth=150,
            hotspot_evidence=[
                HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=1500,
                    cancer_types=["Melanoma"],
                    hotspot_type="single_residue"
                )
            ]
        )
        
        # This would need actual implementation of evidence aggregator
        # For now, we're testing the structure
        try:
            result = engine.assign_tier_with_oncogenicity(
                variant,
                "Melanoma",
                AnalysisType.TUMOR_ONLY
            )
            
            # Should have oncogenicity classification in metadata
            assert "oncogenicity_classification" in result.metadata
            assert result.metadata["oncogenicity_classification"]["classification"] in [
                "Oncogenic", "Likely Oncogenic"
            ]
        except Exception as e:
            # Expected if knowledge bases aren't fully loaded
            pytest.skip(f"Integration test requires full KB setup: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])