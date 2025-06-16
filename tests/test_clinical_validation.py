"""
Clinical Validation Tests for Annotation Engine

Tests the annotation engine against known clinical variants and benchmark datasets
to ensure accurate tier assignment and evidence scoring.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.evidence_aggregator import EvidenceAggregator
from annotation_engine.tiering import TieringEngine
from annotation_engine.models import (
    VariantAnnotation, AnalysisType, AMPTierLevel, 
    VICCOncogenicity, Evidence, EvidenceStrength
)


class TestClinicalValidation:
    """Test annotation engine against known clinical variants"""
    
    @pytest.fixture
    def aggregator(self):
        """Evidence aggregator fixture"""
        return EvidenceAggregator()
    
    @pytest.fixture
    def tiering_engine(self):
        """Tiering engine fixture"""
        return TieringEngine()
    
    def test_tier_1_oncogene_hotspot(self, aggregator, tiering_engine):
        """Test Tier I assignment for known oncogene hotspot (BRAF V600E)"""
        
        # BRAF V600E - well-established Tier I variant
        variant = VariantAnnotation(
            chromosome="7",
            position=140753336,
            reference="T",
            alternate="A",
            gene_symbol="BRAF",
            hgvs_p="p.Val600Glu",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.9, "prediction": "pathogenic"},
                    "revel": {"score": 0.8},
                    "primateai": {"score": 0.7, "prediction": "pathogenic"}
                },
                "conservation_data": {
                    "gerp": 5.8,  # Highly conserved
                    "loftool": 0.02  # Loss-of-function intolerant
                }
            }
        )
        
        # Mock OncoKB and COSMIC hotspot evidence
        with patch.object(aggregator, '_get_oncokb_variant_evidence') as mock_oncokb, \
             patch.object(aggregator, '_get_hotspot_evidence') as mock_hotspot:
            
            mock_oncokb.return_value = [
                Evidence(
                    code="OP3_ONCOKB_1",
                    description="OncoKB Level 1 - FDA-recognized biomarker",
                    score=4,
                    confidence=1.0,
                    strength=EvidenceStrength.VERY_STRONG,
                    supporting_studies=["Flaherty et al. 2010", "Hauschild et al. 2012"]
                )
            ]
            
            mock_hotspot.return_value = [
                Evidence(
                    code="OP4_HOTSPOT_RECURRENT",
                    description="Recurrent hotspot in 15% of melanomas",
                    score=2,
                    confidence=0.9,
                    strength=EvidenceStrength.STRONG,
                    supporting_studies=["COSMIC Hotspots", "TCGA"]
                )
            ]
            
            # Get all evidence
            evidence_list = aggregator.aggregate_evidence(variant, "melanoma", AnalysisType.TUMOR_ONLY)
            
            # Check for high-quality evidence
            oncokb_evidence = [e for e in evidence_list if e.code == "OP3_ONCOKB_1"]
            hotspot_evidence = [e for e in evidence_list if e.code == "OP4_HOTSPOT_RECURRENT"]
            
            assert len(oncokb_evidence) == 1
            assert len(hotspot_evidence) == 1
            
            # Run tiering
            tier_result = tiering_engine.assign_tier(evidence_list, AnalysisType.TUMOR_ONLY)
            
            # Should be Tier I
            assert tier_result.amp_tier == AMPTierLevel.TIER_I
            assert tier_result.vicc_oncogenicity in [VICCOncogenicity.ONCOGENIC, VICCOncogenicity.LIKELY_ONCOGENIC]
            assert tier_result.confidence >= 0.9
    
    def test_tier_3_vus_missense(self, aggregator, tiering_engine):
        """Test Tier III assignment for VUS missense variant"""
        
        # Missense variant with conflicting evidence
        variant = VariantAnnotation(
            chromosome="17",
            position=43094464,
            reference="G",
            alternate="A",
            gene_symbol="BRCA1",
            hgvs_p="p.Ala1708Thr",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.4, "prediction": "benign"},  # Borderline
                    "revel": {"score": 0.3},  # Benign
                    "primateai": {"score": 0.6, "prediction": "pathogenic"}  # Conflicting
                },
                "conservation_data": {
                    "gerp": 3.2,  # Moderately conserved
                }
            }
        )
        
        # Mock limited evidence
        with patch.object(aggregator, '_get_oncokb_variant_evidence') as mock_oncokb, \
             patch.object(aggregator, '_get_hotspot_evidence') as mock_hotspot:
            
            mock_oncokb.return_value = []  # No OncoKB evidence
            mock_hotspot.return_value = []  # No hotspot evidence
            
            # Get evidence
            evidence_list = aggregator.aggregate_evidence(variant, "breast", AnalysisType.TUMOR_ONLY)
            
            # Run tiering
            tier_result = tiering_engine.assign_tier(evidence_list, AnalysisType.TUMOR_ONLY)
            
            # Should be Tier III (VUS)
            assert tier_result.amp_tier == AMPTierLevel.TIER_III
            assert tier_result.vicc_oncogenicity == VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
            assert tier_result.confidence < 0.7
    
    def test_tier_4_benign_variant(self, aggregator, tiering_engine):
        """Test Tier IV assignment for benign variant"""
        
        # Synonymous variant with benign predictions
        variant = VariantAnnotation(
            chromosome="12",
            position=25245351,
            reference="C",
            alternate="T",
            gene_symbol="KRAS",
            hgvs_p="p.Leu19Leu",  # Synonymous
            consequence=["synonymous_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.1, "prediction": "benign"},
                    "revel": {"score": 0.05},
                },
                "conservation_data": {
                    "gerp": -2.1,  # Not conserved
                }
            }
        )
        
        # Mock no significant evidence
        with patch.object(aggregator, '_get_oncokb_variant_evidence') as mock_oncokb, \
             patch.object(aggregator, '_get_hotspot_evidence') as mock_hotspot:
            
            mock_oncokb.return_value = []
            mock_hotspot.return_value = []
            
            # Get evidence
            evidence_list = aggregator.aggregate_evidence(variant, "lung", AnalysisType.TUMOR_ONLY)
            
            # Run tiering
            tier_result = tiering_engine.assign_tier(evidence_list, AnalysisType.TUMOR_ONLY)
            
            # Should be Tier IV (benign/likely benign)
            assert tier_result.amp_tier == AMPTierLevel.TIER_IV
            assert tier_result.vicc_oncogenicity in [VICCOncogenicity.BENIGN, VICCOncogenicity.LIKELY_BENIGN]
    
    def test_tumor_suppressor_truncating(self, aggregator, tiering_engine):
        """Test proper handling of tumor suppressor truncating variants"""
        
        # TP53 nonsense variant
        variant = VariantAnnotation(
            chromosome="17",
            position=7674220,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            hgvs_p="p.Arg213*",
            consequence=["stop_gained"],
            plugin_data={
                "conservation_data": {
                    "loftool": 0.001  # Extremely loss-of-function intolerant
                }
            }
        )
        
        # Mock tumor suppressor evidence
        with patch.object(aggregator, '_get_oncokb_variant_evidence') as mock_oncokb:
            
            mock_oncokb.return_value = [
                Evidence(
                    code="OP3_ONCOKB_TSG",
                    description="TP53 tumor suppressor gene - truncating variant",
                    score=3,
                    confidence=0.95,
                    strength=EvidenceStrength.STRONG,
                    supporting_studies=["Olivier et al. 2010"]
                )
            ]
            
            # Get evidence
            evidence_list = aggregator.aggregate_evidence(variant, "lung", AnalysisType.TUMOR_ONLY)
            
            # Run tiering
            tier_result = tiering_engine.assign_tier(evidence_list, AnalysisType.TUMOR_ONLY)
            
            # Should be Tier I or II (strong oncogenic)
            assert tier_result.amp_tier in [AMPTierLevel.TIER_I, AMPTierLevel.TIER_II]
            assert tier_result.vicc_oncogenicity in [VICCOncogenicity.ONCOGENIC, VICCOncogenicity.LIKELY_ONCOGENIC]
    
    def test_splicing_variant_assessment(self, aggregator, tiering_engine):
        """Test assessment of splicing variants"""
        
        # Splice site variant
        variant = VariantAnnotation(
            chromosome="2",
            position=29443695,
            reference="G",
            alternate="A",
            gene_symbol="ALK",
            hgvs_c="c.3522+1G>A",
            consequence=["splice_donor_variant"],
            plugin_data={
                "splicing_scores": {
                    "spliceai": {
                        "ds_ag": 0.02,
                        "ds_al": 0.01,
                        "ds_dg": 0.95,  # High donor gain loss
                        "ds_dl": 0.1
                    }
                }
            }
        )
        
        # Mock oncogene evidence
        with patch.object(aggregator, '_get_oncokb_variant_evidence') as mock_oncokb:
            
            mock_oncokb.return_value = [
                Evidence(
                    code="OP3_ONCOKB_2",
                    description="OncoKB Level 2 - Standard care biomarker",
                    score=3,
                    confidence=0.9,
                    strength=EvidenceStrength.STRONG,
                    supporting_studies=["Shaw et al. 2013"]
                )
            ]
            
            # Get evidence
            evidence_list = aggregator.aggregate_evidence(variant, "lung", AnalysisType.TUMOR_ONLY)
            
            # Should have splicing evidence
            splice_evidence = [e for e in evidence_list if "splice" in e.code.lower()]
            assert len(splice_evidence) >= 1
            
            # Run tiering
            tier_result = tiering_engine.assign_tier(evidence_list, AnalysisType.TUMOR_ONLY)
            
            # Strong splicing disruption + oncogene should be significant
            assert tier_result.amp_tier in [AMPTierLevel.TIER_I, AMPTierLevel.TIER_II]
    
    def test_context_specific_interpretation(self, aggregator, tiering_engine):
        """Test cancer type-specific interpretation"""
        
        # PIK3CA H1047R - different significance in different cancer types
        variant = VariantAnnotation(
            chromosome="3",
            position=179234297,
            reference="A",
            alternate="G",
            gene_symbol="PIK3CA",
            hgvs_p="p.His1047Arg",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.8, "prediction": "pathogenic"},
                    "revel": {"score": 0.7}
                }
            }
        )
        
        # Mock context-specific evidence
        with patch.object(aggregator, '_get_oncokb_variant_evidence') as mock_oncokb:
            
            # High significance in breast cancer
            mock_oncokb.return_value = [
                Evidence(
                    code="OP3_ONCOKB_1",
                    description="OncoKB Level 1 in breast cancer",
                    score=4,
                    confidence=1.0,
                    strength=EvidenceStrength.VERY_STRONG,
                    supporting_studies=["Andre et al. 2019"]
                )
            ]
            
            # Test breast cancer context
            evidence_breast = aggregator.aggregate_evidence(variant, "breast", AnalysisType.TUMOR_ONLY)
            tier_breast = tiering_engine.assign_tier(evidence_breast, AnalysisType.TUMOR_ONLY)
            
            # Should be Tier I in breast cancer
            assert tier_breast.amp_tier == AMPTierLevel.TIER_I
            
            # Reset mock for different context
            mock_oncokb.return_value = []
            
            # Test lung cancer context (lower significance)
            evidence_lung = aggregator.aggregate_evidence(variant, "lung", AnalysisType.TUMOR_ONLY)
            tier_lung = tiering_engine.assign_tier(evidence_lung, AnalysisType.TUMOR_ONLY)
            
            # Should be lower tier in lung cancer
            assert tier_lung.amp_tier in [AMPTierLevel.TIER_II, AMPTierLevel.TIER_III]
    
    def test_consensus_predictor_scoring(self, aggregator, tiering_engine):
        """Test consensus scoring from multiple predictors"""
        
        variant = VariantAnnotation(
            chromosome="7",
            position=116771934,
            reference="G",
            alternate="A",
            gene_symbol="EGFR",
            hgvs_p="p.Gly719Ser",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.8},   # pathogenic
                    "revel": {"score": 0.75},          # pathogenic  
                    "primateai": {"score": 0.7},       # pathogenic
                    "varity": {"score": 0.02}          # benign (conflicting)
                }
            }
        )
        
        # Get functional prediction evidence
        evidence_list = aggregator._get_functional_prediction_evidence(variant, AnalysisType.TUMOR_ONLY)
        
        # Should have consensus evidence
        consensus_evidence = [e for e in evidence_list if "consensus" in e.code.lower()]
        assert len(consensus_evidence) >= 1
        
        # Consensus should reflect majority pathogenic prediction
        consensus = consensus_evidence[0]
        assert consensus.score >= 1  # At least moderate evidence
        assert "3/4" in consensus.description or "75%" in consensus.description


if __name__ == "__main__":
    pytest.main([__file__])