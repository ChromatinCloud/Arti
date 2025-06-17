"""
Test cases for tier assignment logic including DSC-based tier assignments

Tests the complete tier assignment pipeline including AMP/ASCO/CAP 2017 scoring,
VICC/CGC 2022 oncogenicity classification, and DSC-based tier modulation for
tumor-only analysis.
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import (
    VariantAnnotation, Evidence, TierResult, AMPScoring, VICCScoring,
    OncoKBScoring, AMPTierLevel, VICCOncogenicity, OncoKBLevel,
    AnalysisType, DynamicSomaticConfidence, ActionabilityType,
    ContextSpecificTierAssignment, EvidenceStrength
)
from annotation_engine.tiering import TieringEngine


class TestTierAssignmentEngine:
    """Test tier assignment for different analysis types and evidence scenarios"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.tier_engine = TieringEngine()
        
        # Mock the evidence aggregator to return controlled test data
        self.tier_engine.evidence_aggregator = MagicMock()
        
        # Set workflow router to None to avoid filtering
        self.tier_engine.workflow_router = None
        
    def _setup_evidence_aggregator_mock(self, evidence_list, vicc_scoring=None, oncokb_scoring=None, dsc_scoring=None):
        """Helper to setup evidence aggregator mock with specific return values"""
        self.tier_engine.evidence_aggregator.aggregate_evidence.return_value = evidence_list
        
        # Default VICC scoring
        if vicc_scoring is None:
            vicc_scoring = VICCScoring(
                ovs1_score=0, os1_score=0, os2_score=4, os3_score=4,
                total_score=8, classification=VICCOncogenicity.ONCOGENIC
            )
        self.tier_engine.evidence_aggregator.calculate_vicc_score.return_value = vicc_scoring
        
        # Default OncoKB scoring 
        if oncokb_scoring is None:
            oncokb_scoring = OncoKBScoring(
                oncogenicity="Oncogenic",
                therapeutic_level=OncoKBLevel.LEVEL_1,
                fda_approved_therapy=["dabrafenib", "vemurafenib"]
            )
        self.tier_engine.evidence_aggregator.calculate_oncokb_score.return_value = oncokb_scoring
        
        # Default DSC scoring for tumor-only
        if dsc_scoring is None:
            dsc_scoring = DynamicSomaticConfidence(
                dsc_score=0.95,
                vaf_purity_score=0.9,
                prior_probability_score=0.95,
                modules_available=["vaf_purity", "prior_probability"]
            )
        self.tier_engine.evidence_aggregator.calculate_dsc_score.return_value = dsc_scoring
    
    def test_tumor_normal_tier_assignment(self):
        """Test standard tier assignment for tumor-normal analysis"""
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            consequence=["missense_variant"],
            hgvs_p="p.Val600Glu"
        )
        
        evidence_list = [
            Evidence(
                code="OS2",
                score=4,
                guideline="AMP_2017",
                source_kb="OncoKB",
                description="FDA-approved biomarker for melanoma therapy",
                confidence=1.0
            ),
            Evidence(
                code="OS1",
                score=4,
                guideline="AMP_2017", 
                source_kb="NCCN",
                description="Professional guidelines recommendation for therapy",
                confidence=0.95
            )
        ]
        
        # Setup mock evidence aggregator
        self._setup_evidence_aggregator_mock(evidence_list)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="melanoma",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # Should be Tier IA - highest tier for FDA-approved biomarker
        assert tier_result.amp_scoring.get_primary_tier() == AMPTierLevel.TIER_IA.value
        assert tier_result.analysis_type == AnalysisType.TUMOR_NORMAL
        assert tier_result.dsc_scoring is None  # No DSC for tumor-normal
        assert tier_result.confidence_score > 0.8  # Good confidence
        
        # Check therapeutic tier assignment
        assert tier_result.amp_scoring.therapeutic_tier is not None
        assert tier_result.amp_scoring.therapeutic_tier.tier_level == AMPTierLevel.TIER_IA
        assert tier_result.amp_scoring.therapeutic_tier.evidence_strength == EvidenceStrength.FDA_APPROVED
    
    def test_tumor_only_high_dsc_tier_i(self):
        """Test tumor-only analysis with high DSC allowing Tier I"""
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            vaf=0.45,
            tumor_vaf=0.45,  # Add tumor_vaf for workflow router
            tumor_purity=0.8,
            consequence=["missense_variant"],
            hgvs_p="p.Val600Glu"
        )
        
        evidence_list = [
            Evidence(
                code="OS2",
                score=4,
                guideline="AMP_2017",
                source_kb="OncoKB",
                description="FDA-approved biomarker for targeted therapy",
                confidence=1.0
            ),
            Evidence(
                code="OS1",
                score=4,
                guideline="AMP_2017", 
                source_kb="NCCN",
                description="Professional guidelines recommendation for therapy",
                confidence=0.95
            )
        ]
        
        # Mock high DSC score that will be calculated by the evidence aggregator
        dsc_scoring = DynamicSomaticConfidence(
            dsc_score=0.95,  # High DSC allows Tier I
            vaf_purity_score=0.9,
            prior_probability_score=0.9,
            tumor_purity=0.8,
            variant_vaf=0.45,
            hotspot_evidence=True,
            modules_available=["vaf_purity_consistency", "somatic_germline_prior"]
        )
        
        # Setup mock evidence aggregator to return high DSC
        self._setup_evidence_aggregator_mock(evidence_list, dsc_scoring=dsc_scoring)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="melanoma",
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        # High DSC should allow Tier I assignment
        assert tier_result.amp_scoring.get_primary_tier() == AMPTierLevel.TIER_IA.value
        assert tier_result.analysis_type == AnalysisType.TUMOR_ONLY
        assert tier_result.dsc_scoring.dsc_score == 0.95
        assert tier_result.confidence_score > 0.7  # Good confidence (reduced for tumor-only)
        
        # Should have tumor-only disclaimers
        disclaimer_texts = [ct for ct in tier_result.canned_texts 
                          if "tumor" in ct.content.lower() or ct.text_type.name == "TUMOR_ONLY_DISCLAIMERS"]
        assert len(disclaimer_texts) > 0
    
    def test_tumor_only_moderate_dsc_tier_ii(self):
        """Test tumor-only analysis with moderate DSC limiting to Tier II"""
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            vaf=0.25,
            tumor_vaf=0.25,
            tumor_purity=0.6,
            consequence=["missense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OS2",
                score=4,
                guideline="AMP_2017",
                source_kb="CIViC",
                description="Professional guidelines for therapeutic management",
                confidence=0.8
            )
        ]
        
        # Mock moderate DSC score
        dsc_scoring = DynamicSomaticConfidence(
            dsc_score=0.7,  # Moderate DSC limits to Tier II
            vaf_purity_score=0.6,
            prior_probability_score=0.8,
            tumor_purity=0.6,
            variant_vaf=0.25,
            modules_available=["vaf_purity_consistency", "somatic_germline_prior"]
        )
        
        # Setup mock evidence aggregator to return moderate DSC
        self._setup_evidence_aggregator_mock(evidence_list, dsc_scoring=dsc_scoring)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="lung",
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        # Moderate DSC should limit to Tier II despite strong evidence
        primary_tier = tier_result.amp_scoring.get_primary_tier()
        assert primary_tier in [AMPTierLevel.TIER_IIC.value, AMPTierLevel.TIER_IID.value]
        assert tier_result.dsc_scoring.dsc_score == 0.7
    
    def test_tumor_only_low_dsc_tier_iii(self):
        """Test tumor-only analysis with low DSC assignment to Tier III"""
        variant = VariantAnnotation(
            chromosome="1",
            position=12345678,
            reference="G",
            alternate="A",
            gene_symbol="UNKNOWN_GENE",
            vaf=0.48,  # High VAF suggests germline
            tumor_vaf=0.48,
            tumor_purity=0.9,
            consequence=["synonymous_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OP4",
                score=1,
                guideline="VICC_2022",
                source_kb="gnomAD",
                description="Absent from population databases, potential therapeutic significance",
                confidence=0.6
            ),
            Evidence(
                code="OP1",
                score=2,
                guideline="AMP_2017",
                source_kb="Literature",
                description="Case reports suggest potential therapeutic relevance",
                confidence=0.5
            )
        ]
        
        # Mock low DSC score
        dsc_scoring = DynamicSomaticConfidence(
            dsc_score=0.3,  # Low DSC forces Tier III
            vaf_purity_score=0.2,  # Poor VAF/purity consistency
            prior_probability_score=0.4,
            population_frequency=0.02,
            clinvar_germline=True,
            modules_available=["vaf_purity_consistency", "somatic_germline_prior"]
        )
        
        # Setup mock with low DSC
        vicc_scoring = VICCScoring(
            total_score=1, classification=VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
        )
        oncokb_scoring = OncoKBScoring()
        self._setup_evidence_aggregator_mock(evidence_list, vicc_scoring, oncokb_scoring, dsc_scoring)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="unknown",
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        # Low DSC should force Tier III (VUS)
        assert tier_result.amp_scoring.get_primary_tier() == AMPTierLevel.TIER_III.value
        assert tier_result.dsc_scoring.dsc_score == 0.3
        assert tier_result.confidence_score < 0.5
    
    def test_vicc_oncogenicity_scoring(self):
        """Test VICC/CGC 2022 oncogenicity scoring"""
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            consequence=["missense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OVS1",
                score=8,
                guideline="VICC_2022",
                source_kb="ClinVar",
                description="Null variant in tumor suppressor"
            ),
            Evidence(
                code="OS3",
                score=4,
                guideline="VICC_2022",
                source_kb="COSMIC_Hotspots",
                description="Well-established hotspot"
            ),
            Evidence(
                code="OP1",
                score=1,
                guideline="VICC_2022",
                source_kb="dbNSFP",
                description="Computational evidence"
            )
        ]
        
        # Setup mock for VICC scoring test
        vicc_scoring = VICCScoring(
            ovs1_score=8, os1_score=0, os2_score=4, os3_score=1,
            total_score=13, classification=VICCOncogenicity.ONCOGENIC
        )
        self._setup_evidence_aggregator_mock(evidence_list, vicc_scoring=vicc_scoring)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="melanoma",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # Total VICC score: 8 + 4 + 1 = 13 (>= 7 for Oncogenic)
        assert tier_result.vicc_scoring.total_score >= 7
        assert tier_result.vicc_scoring.classification == VICCOncogenicity.ONCOGENIC
    
    def test_multi_context_tier_assignment(self):
        """Test multi-context tier assignment (therapeutic/diagnostic/prognostic)"""
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C", 
            alternate="T",
            gene_symbol="TP53",
            consequence=["missense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OS2",
                score=4,
                guideline="AMP_2017",
                source_kb="OncoKB",
                description="Therapeutic biomarker",
                confidence=0.9
            ),
            Evidence(
                code="OM1",
                score=2,
                guideline="AMP_2017",
                source_kb="CIViC",
                description="Diagnostic significance",
                confidence=0.8
            ),
            Evidence(
                code="OP2",
                score=1,
                guideline="AMP_2017",
                source_kb="ClinVar",
                description="Prognostic marker",
                confidence=0.7
            )
        ]
        
        # Setup mock for multi-context tier assignment test
        self._setup_evidence_aggregator_mock(evidence_list)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="lung",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # Should have multiple context assignments
        context_tiers = tier_result.amp_scoring.get_context_tiers()
        assert len(context_tiers) >= 1
        
        # Therapeutic should be highest tier
        if tier_result.amp_scoring.therapeutic_tier:
            assert tier_result.amp_scoring.therapeutic_tier.actionability_type == ActionabilityType.THERAPEUTIC
    
    def test_oncokb_integration(self):
        """Test OncoKB evidence integration"""
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T", 
            gene_symbol="BRAF",
            consequence=["missense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="Level_1",
                score=5,
                guideline="OncoKB",
                source_kb="OncoKB",
                description="FDA-approved biomarker for targeted therapy",
                confidence=0.95,
                data={
                    "therapeutic_level": "Level 1",
                    "oncogenicity": "Oncogenic",
                    "drugs": ["dabrafenib", "vemurafenib"],
                    "cancer_types": ["melanoma"]
                }
            )
        ]
        
        # Setup mock for OncoKB integration test
        oncokb_scoring = OncoKBScoring(
            oncogenicity="Oncogenic",
            therapeutic_level=OncoKBLevel.LEVEL_1,
            fda_approved_therapy=["dabrafenib", "vemurafenib"]
        )
        self._setup_evidence_aggregator_mock(evidence_list, oncokb_scoring=oncokb_scoring)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="melanoma",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # OncoKB Level 1 should drive Tier IA
        assert tier_result.amp_scoring.get_primary_tier() == AMPTierLevel.TIER_IA.value
        assert tier_result.oncokb_scoring.therapeutic_level == OncoKBLevel.LEVEL_1
        assert tier_result.oncokb_scoring.oncogenicity == "Oncogenic"
        assert len(tier_result.oncokb_scoring.fda_approved_therapy) > 0


class TestTierAssignmentEdgeCases:
    """Test edge cases and boundary conditions in tier assignment"""
    
    def setup_method(self):
        self.tier_engine = TieringEngine()
        # Mock the evidence aggregator
        self.tier_engine.evidence_aggregator = MagicMock()
    
    def _setup_evidence_aggregator_mock(self, evidence_list, vicc_scoring=None, oncokb_scoring=None):
        """Helper to setup evidence aggregator mock"""
        self.tier_engine.evidence_aggregator.aggregate_evidence.return_value = evidence_list
        
        if vicc_scoring is None:
            vicc_scoring = VICCScoring(total_score=0, classification=VICCOncogenicity.UNCERTAIN_SIGNIFICANCE)
        self.tier_engine.evidence_aggregator.calculate_vicc_score.return_value = vicc_scoring
        
        if oncokb_scoring is None:
            oncokb_scoring = OncoKBScoring()
        self.tier_engine.evidence_aggregator.calculate_oncokb_score.return_value = oncokb_scoring
    
    def test_no_evidence_tier_assignment(self):
        """Test tier assignment with no supporting evidence"""
        variant = VariantAnnotation(
            chromosome="X",
            position=123456,
            reference="C",
            alternate="T",
            gene_symbol="UNKNOWN",
            consequence=["synonymous_variant"]
        )
        
        # Setup mock with no evidence
        self._setup_evidence_aggregator_mock([])
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="unknown",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # No evidence should result in Tier IV (Benign/Likely Benign)
        assert tier_result.amp_scoring.get_primary_tier() == AMPTierLevel.TIER_IV.value
        assert tier_result.confidence_score < 0.5
    
    def test_conflicting_evidence_resolution(self):
        """Test tier assignment with conflicting evidence"""
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            consequence=["missense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OS3",
                score=4,
                guideline="VICC_2022",
                source_kb="COSMIC_Hotspots",
                description="Cancer hotspot with therapeutic implications",
                confidence=0.8
            ),
            Evidence(
                code="SBVS1",
                score=-4,
                guideline="VICC_2022",
                source_kb="gnomAD",
                description="High population frequency",
                confidence=0.9
            )
        ]
        
        # Setup mock for this test - conflicting evidence should result in VUS
        vicc_scoring = VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=0, os3_score=4,
            sbvs1_score=-4,
            total_score=0,  # 4 + (-4) = 0
            classification=VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
        )
        self._setup_evidence_aggregator_mock(evidence_list, vicc_scoring=vicc_scoring)
        
        tier_result = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="lung",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # Conflicting evidence should result in VUS (Tier III)
        assert tier_result.amp_scoring.get_primary_tier() == AMPTierLevel.TIER_III.value
        assert tier_result.vicc_scoring.total_score == 0  # 4 + (-4) = 0
        assert tier_result.vicc_scoring.classification == VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
    
    def test_cancer_type_specific_evidence(self):
        """Test tier assignment with cancer-type-specific evidence"""
        variant = VariantAnnotation(
            chromosome="12",
            position=25398281,
            reference="C",
            alternate="A",
            gene_symbol="KRAS",
            consequence=["missense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OS2",
                score=4,
                guideline="AMP_2017",
                source_kb="OncoKB",
                description="Therapeutic biomarker for lung cancer",
                confidence=0.9,
                data={"cancer_types": ["lung", "colon"]}
            )
        ]
        
        # Setup mock evidence aggregator
        self._setup_evidence_aggregator_mock(evidence_list)
        
        # Test with matching cancer type
        tier_result_match = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="lung",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # Test with non-matching cancer type  
        tier_result_no_match = self.tier_engine.assign_tier(
            variant_annotation=variant,
            cancer_type="breast",
            analysis_type=AnalysisType.TUMOR_NORMAL
        )
        
        # Matching cancer type should have higher confidence
        assert tier_result_match.confidence_score > tier_result_no_match.confidence_score
        assert tier_result_match.amp_scoring.cancer_type_specific is True


if __name__ == "__main__":
    pytest.main([__file__])