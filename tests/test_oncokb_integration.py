"""
Test OncoKB Enhanced Integration

Tests for the comprehensive OncoKB variant-drug-cancer association matching
and evidence generation implemented in Phase 1.
"""

import pytest
from pathlib import Path
import sys

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.evidence_aggregator import EvidenceAggregator
from annotation_engine.models import VariantAnnotation, Evidence, OncoKBScoring, OncoKBLevel
from annotation_engine.tiering import TieringEngine


class TestOncoKBEnhancedIntegration:
    """Test the enhanced OncoKB integration with biomarker associations"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.aggregator = EvidenceAggregator()
        self.tiering_engine = TieringEngine()
    
    def test_oncokb_variant_matching_exact(self):
        """Test exact HGVS variant matching for OncoKB"""
        # Create BRAF V600E variant
        variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            hgvs_c="c.1799T>A",
            consequence=["missense_variant"]
        )
        
        # Get OncoKB evidence
        evidence_list = self.aggregator.aggregate_evidence(variant, cancer_type="melanoma")
        oncokb_evidence = [e for e in evidence_list if e.source_kb == "OncoKB"]
        
        # Should find BRAF V600E Level 1 evidence
        assert len(oncokb_evidence) > 0
        
        # Check for Level 1 evidence
        level_1_evidence = [e for e in oncokb_evidence if e.code == "ONCOKB_LEVEL_1"]
        assert len(level_1_evidence) > 0
        
        # Verify evidence details
        evidence = level_1_evidence[0]
        assert "FDA-approved therapy" in evidence.description
        assert evidence.confidence == 0.95
        assert evidence.data["oncokb_level"] == "LEVEL_1"
        assert "BRAF" in evidence.description
        assert "V600E" in evidence.description or "Val600Glu" in evidence.description
    
    def test_oncokb_variant_matching_short_form(self):
        """Test short form variant matching (V600E style)"""
        # Create KRAS G12C variant
        variant = VariantAnnotation(
            chromosome="12",
            position=25245350,
            reference="C",
            alternate="T", 
            gene_symbol="KRAS",
            hgvs_p="p.Gly12Cys",
            hgvs_c="c.34G>T",
            consequence=["missense_variant"]
        )
        
        # Get OncoKB evidence
        evidence_list = self.aggregator.aggregate_evidence(variant, cancer_type="lung_adenocarcinoma")
        oncokb_evidence = [e for e in evidence_list if e.source_kb == "OncoKB"]
        
        # Should find KRAS G12C evidence
        assert len(oncokb_evidence) > 0
        
        # Check evidence levels
        evidence_codes = [e.code for e in oncokb_evidence]
        assert any(code in ["ONCOKB_LEVEL_1", "ONCOKB_LEVEL_2", "ONCOKB_LEVEL_3", "ONCOKB_LEVEL_4"] 
                  for code in evidence_codes)
    
    def test_oncokb_gene_level_matching(self):
        """Test gene-level mutation matching"""
        # Create PIK3CA variant
        variant = VariantAnnotation(
            chromosome="3",
            position=178952085,
            reference="A",
            alternate="G",
            gene_symbol="PIK3CA",
            hgvs_p="p.His1047Arg",
            hgvs_c="c.3140A>G",
            consequence=["missense_variant"]
        )
        
        # Get OncoKB evidence  
        evidence_list = self.aggregator.aggregate_evidence(variant, cancer_type="breast_cancer")
        oncokb_evidence = [e for e in evidence_list if e.source_kb == "OncoKB"]
        
        # Should find evidence (exact or gene-level)
        assert len(oncokb_evidence) > 0
    
    def test_oncokb_scoring_calculation(self):
        """Test OncoKB scoring calculation from evidence"""
        # Create variant with OncoKB evidence
        variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            consequence=["missense_variant"]
        )
        
        # Get evidence and calculate OncoKB score
        evidence_list = self.aggregator.aggregate_evidence(variant, cancer_type="melanoma")
        oncokb_scoring = self.aggregator.calculate_oncokb_score(evidence_list)
        
        # Verify OncoKB scoring
        assert oncokb_scoring.therapeutic_level == OncoKBLevel.LEVEL_1
        assert len(oncokb_scoring.fda_approved_therapy) > 0
        assert oncokb_scoring.cancer_type_specific == True
        assert oncokb_scoring.oncogenicity == "Oncogenic"
    
    def test_oncokb_tier_influence(self):
        """Test that OncoKB Level 1 influences tier assignment"""
        # Create BRAF V600E variant
        variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            consequence=["missense_variant"]
        )
        
        # Get tier assignment
        tier_result = self.tiering_engine.assign_tier(variant, cancer_type="melanoma")
        
        # Verify OncoKB influenced the tier
        assert tier_result.oncokb_scoring.therapeutic_level == OncoKBLevel.LEVEL_1
        
        # Should get better tier due to OncoKB Level 1
        # (Exact tier depends on other evidence, but should be Tier I, II, or III)
        primary_tier = tier_result.amp_scoring.get_primary_tier()
        assert primary_tier in ["Tier I", "Tier II", "Tier III"]
        
        # Confidence should be higher with OncoKB evidence
        assert tier_result.confidence_score > 0.5
    
    def test_oncokb_cancer_type_matching(self):
        """Test cancer type specific matching"""
        variant = VariantAnnotation(
            chromosome="7", 
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            consequence=["missense_variant"]
        )
        
        # Test melanoma (should match)
        evidence_melanoma = self.aggregator.aggregate_evidence(variant, cancer_type="melanoma")
        oncokb_melanoma = [e for e in evidence_melanoma if e.source_kb == "OncoKB" and e.code == "ONCOKB_LEVEL_1"]
        assert len(oncokb_melanoma) > 0
        
        # Test different cancer type 
        evidence_other = self.aggregator.aggregate_evidence(variant, cancer_type="lung_adenocarcinoma")
        oncokb_other = [e for e in evidence_other if e.source_kb == "OncoKB"]
        # May still find evidence but possibly different levels or "all tumors" matches
        # Just verify it doesn't crash and returns valid evidence
        assert isinstance(oncokb_other, list)
    
    def test_hgvs_simplification(self):
        """Test HGVS simplification methods"""
        # Test various HGVS formats
        assert self.aggregator._simplify_hgvs("p.Val600Glu") == "Val600Glu"
        assert self.aggregator._simplify_hgvs("ENSP00000288602:p.Val600Glu") == "Val600Glu"
        assert self.aggregator._simplify_hgvs("NP_004324.2:p.Val600Glu") == "Val600Glu"
        
        # Test short form conversion
        assert self.aggregator._hgvs_to_short_form("p.Val600Glu") == "V600E"
        assert self.aggregator._hgvs_to_short_form("p.Gly12Cys") == "G12C"
        assert self.aggregator._hgvs_to_short_form("p.His1047Arg") == "H1047R"
    
    def test_oncokb_evidence_levels_loaded(self):
        """Test that OncoKB evidence levels are loaded"""
        from annotation_engine.evidence_aggregator import _KB_CACHE
        
        # Ensure KBs are loaded
        self.aggregator.loader.load_all_kbs()
        
        # Check evidence levels loaded
        oncokb_levels = _KB_CACHE.get('oncokb_evidence_levels', {})
        assert len(oncokb_levels) > 0
        
        # Verify key levels exist
        assert 'LEVEL_1' in oncokb_levels
        assert 'LEVEL_2' in oncokb_levels
        assert 'LEVEL_3A' in oncokb_levels
        assert 'LEVEL_4' in oncokb_levels
        
        # Check level categorization
        level_1 = oncokb_levels.get('LEVEL_1', {})
        assert level_1.get('therapeutic_significance') == 'high_therapeutic'
    
    def test_oncokb_biomarker_associations_loaded(self):
        """Test that biomarker associations are loaded"""
        from annotation_engine.evidence_aggregator import _KB_CACHE
        
        # Ensure KBs are loaded
        self.aggregator.loader.load_all_kbs()
        
        # Check variants loaded
        oncokb_variants = _KB_CACHE.get('oncokb_variants', {})
        assert len(oncokb_variants) > 0
        
        # Check for known variants
        # Should have BRAF V600E in some form
        braf_variants = [k for k in oncokb_variants.keys() if k.startswith("BRAF:")]
        assert len(braf_variants) > 0
        
        # Check variant structure
        first_variant_key = list(oncokb_variants.keys())[0]
        first_variant = oncokb_variants[first_variant_key]
        assert 'gene' in first_variant
        assert 'alteration' in first_variant
        assert 'evidence_items' in first_variant
    
    def test_no_oncokb_evidence_graceful(self):
        """Test that variants without OncoKB evidence are handled gracefully"""
        # Create a variant unlikely to have OncoKB evidence
        variant = VariantAnnotation(
            chromosome="1",
            position=12345,
            reference="A",
            alternate="T",
            gene_symbol="UNKNOWN_GENE",
            hgvs_p="p.Ala123Val",
            consequence=["missense_variant"]
        )
        
        # Should not crash, just return empty OncoKB evidence
        evidence_list = self.aggregator.aggregate_evidence(variant)
        oncokb_evidence = [e for e in evidence_list if e.source_kb == "OncoKB"]
        assert len(oncokb_evidence) == 0
        
        # OncoKB scoring should handle no evidence
        oncokb_scoring = self.aggregator.calculate_oncokb_score(evidence_list)
        assert oncokb_scoring.therapeutic_level is None
        assert len(oncokb_scoring.fda_approved_therapy) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])