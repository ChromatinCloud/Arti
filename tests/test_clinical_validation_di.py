"""
Clinical Validation Tests using Dependency Injection

Migrated from test_clinical_validation.py to use the new clean DI pattern.
Tests various clinical scenarios with proper evidence and tier assignments.
"""

import pytest
from pathlib import Path
import sys

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import (
    AnalysisType, AMPTierLevel, VICCOncogenicity, OncoKBLevel,
    VICCScoring, OncoKBScoring, ActionabilityType, EvidenceStrength
)
from annotation_engine.dependency_injection import create_test_tiering_engine
from annotation_engine.test_mocks import (
    MockEvidenceAggregator, MockWorkflowRouter, MockCannedTextGenerator, MockScoringManager
)
from annotation_engine.test_migration_helpers import (
    create_tier_i_oncogene_evidence, create_tier_iii_vus_evidence, 
    create_tier_iv_benign_evidence, create_tumor_suppressor_evidence,
    create_braf_v600e_variant, create_tp53_truncating_variant
)


class TestClinicalValidationDI:
    """Clinical validation tests using clean dependency injection"""
    
    def setup_method(self):
        """Setup test fixtures with dependency injection"""
        # Create clean mock dependencies
        self.evidence_aggregator = MockEvidenceAggregator()
        self.workflow_router = MockWorkflowRouter(should_include=True)
        self.text_generator = MockCannedTextGenerator()
        self.scoring_manager = MockScoringManager()
        
        # Create test configuration with disabled text generation
        from annotation_engine.models import AnnotationConfig
        test_config = AnnotationConfig(
            kb_base_path=".refs",
            enable_canned_text=False  # Disable text generation for cleaner tests
        )
        
        # Create tiering engine with injected dependencies
        self.tier_engine = create_test_tiering_engine(
            config=test_config,
            evidence_aggregator=self.evidence_aggregator,
            workflow_router=self.workflow_router,
            text_generator=self.text_generator,
            scoring_manager=self.scoring_manager
        )
    
    def test_tier_1_oncogene_hotspot_di(self):
        """Test Tier I assignment for known oncogene hotspot (BRAF V600E) using DI"""
        
        # Setup test data
        variant = create_braf_v600e_variant()
        evidence_list = create_tier_i_oncogene_evidence()
        
        # Configure high therapeutic score for Tier IA
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.95)
        self.scoring_manager.set_default_strength(EvidenceStrength.FDA_APPROVED)
        
        # Configure mocks for Tier I scenario
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=0, os1_score=4, os2_score=4, os3_score=4,
            total_score=12, classification=VICCOncogenicity.ONCOGENIC
        ))
        self.evidence_aggregator.set_oncokb_scoring(OncoKBScoring(
            therapeutic_level=OncoKBLevel.LEVEL_1,
            diagnostic_level=None,
            prognostic_level=None,
            therapeutic_implications="FDA-approved biomarker for vemurafenib therapy",
            oncogenicity_level="Oncogenic"
        ))
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Verify Tier I assignment
        assert result.amp_scoring.therapeutic_tier.tier_level == AMPTierLevel.TIER_IA
        assert result.vicc_scoring.classification == VICCOncogenicity.ONCOGENIC
        assert result.oncokb_scoring.therapeutic_level == OncoKBLevel.LEVEL_1
        assert result.gene_symbol == "BRAF"
        assert result.confidence_score > 0.8
        
        # Verify evidence content
        assert len(result.evidence) == 3
        assert any("OncoKB Level 1" in evidence.description for evidence in result.evidence)
        assert any("hotspot" in evidence.description.lower() for evidence in result.evidence)
    
    def test_tier_3_vus_missense_di(self):
        """Test Tier III VUS assignment for missense variant with uncertain significance"""
        
        # Setup test data with variant in oncogene but unclear significance
        variant = create_braf_v600e_variant()
        variant.hgvs_p = "p.Asp594Gly"  # Different position, less clear significance
        evidence_list = create_tier_iii_vus_evidence()
        
        # Configure moderate scoring for Tier III
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.3)
        self.scoring_manager.set_evidence_score(ActionabilityType.DIAGNOSTIC, 0.2)
        self.scoring_manager.set_default_strength(EvidenceStrength.MULTIPLE_SMALL_STUDIES)
        
        # Configure mocks for VUS scenario
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=0, os3_score=0,
            om1_score=0, om2_score=0, om3_score=0, om4_score=2,
            total_score=2, classification=VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
        ))
        self.evidence_aggregator.set_oncokb_scoring(OncoKBScoring(
            therapeutic_level=None,
            diagnostic_level=None,
            prognostic_level=None,
            therapeutic_implications=None,
            oncogenicity_level="Unknown"
        ))
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Verify Tier III VUS assignment
        assert result.amp_scoring.therapeutic_tier.tier_level == AMPTierLevel.TIER_III
        assert result.vicc_scoring.classification == VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
        assert result.gene_symbol == "BRAF"
        assert 0.3 <= result.confidence_score <= 0.7  # Moderate confidence for VUS
        
        # Verify evidence reflects uncertainty
        assert len(result.evidence) == 2
        assert any("uncertain significance" in evidence.description.lower() for evidence in result.evidence)
    
    def test_tier_4_benign_variant_di(self):
        """Test Tier IV assignment for benign variant with population frequency evidence"""
        
        # Setup test data for common variant
        variant = create_braf_v600e_variant()
        variant.hgvs_p = "p.Glu586Gln"  # Common polymorphism
        evidence_list = create_tier_iv_benign_evidence()
        
        # Configure low scores for benign variant (but not zero to ensure tier assignment)
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.15)
        self.scoring_manager.set_evidence_score(ActionabilityType.DIAGNOSTIC, 0.15)
        self.scoring_manager.set_default_strength(EvidenceStrength.CASE_REPORTS)
        
        # Configure mocks for benign scenario
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=0, os3_score=0,
            total_score=-8, classification=VICCOncogenicity.BENIGN
        ))
        self.evidence_aggregator.set_oncokb_scoring(OncoKBScoring(
            therapeutic_level=None,
            diagnostic_level=None,
            prognostic_level=None,
            therapeutic_implications=None,
            oncogenicity_level="Benign"
        ))
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Verify Tier IV benign assignment
        assert result.amp_scoring.therapeutic_tier.tier_level == AMPTierLevel.TIER_IV
        assert result.vicc_scoring.classification == VICCOncogenicity.BENIGN
        assert result.gene_symbol == "BRAF"
        assert result.confidence_score > 0.7  # Good confidence for benign
        
        # Verify evidence supports benign classification
        assert len(result.evidence) == 2
        assert any("population frequency" in evidence.description.lower() for evidence in result.evidence)
        assert any("benign" in evidence.description.lower() for evidence in result.evidence)
    
    def test_tumor_suppressor_truncating_di(self):
        """Test tier assignment for tumor suppressor truncating variant (TP53)"""
        
        # Setup test data for TP53 truncating variant
        variant = create_tp53_truncating_variant()
        evidence_list = create_tumor_suppressor_evidence()
        
        # Configure very high scores for tumor suppressor LOF
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.9)
        self.scoring_manager.set_evidence_score(ActionabilityType.DIAGNOSTIC, 0.85)
        self.scoring_manager.set_evidence_score(ActionabilityType.PROGNOSTIC, 0.8)
        self.scoring_manager.set_default_strength(EvidenceStrength.FDA_APPROVED)
        
        # Configure mocks for tumor suppressor scenario
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=8, os1_score=0, os2_score=0, os3_score=0,
            total_score=8, classification=VICCOncogenicity.ONCOGENIC
        ))
        self.evidence_aggregator.set_oncokb_scoring(OncoKBScoring(
            therapeutic_level=OncoKBLevel.LEVEL_2A,
            diagnostic_level=OncoKBLevel.LEVEL_1,
            prognostic_level=OncoKBLevel.LEVEL_2A,
            therapeutic_implications="Loss-of-function impacts therapy selection",
            oncogenicity_level="Oncogenic"
        ))
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "li_fraumeni_syndrome", AnalysisType.TUMOR_NORMAL)
        
        # Verify strong tier assignment for tumor suppressor LOF
        assert result.amp_scoring.therapeutic_tier.tier_level in [AMPTierLevel.TIER_IA, AMPTierLevel.TIER_IB]
        assert result.vicc_scoring.classification == VICCOncogenicity.ONCOGENIC
        assert result.gene_symbol == "TP53"
        assert result.confidence_score > 0.8
        
        # Verify multiple actionability contexts
        assert result.amp_scoring.diagnostic_tier is not None
        assert result.amp_scoring.prognostic_tier is not None
        
        # Verify evidence includes tumor suppressor context
        assert len(result.evidence) == 2
        assert any("tumor suppressor" in evidence.description.lower() for evidence in result.evidence)
        assert any("loss-of-function" in evidence.description.lower() for evidence in result.evidence)
    
    def test_context_specific_interpretation_di(self):
        """Test context-specific tier assignments across multiple actionability types"""
        
        # Setup variant with different evidence strengths per context
        variant = create_braf_v600e_variant()
        evidence_list = create_tier_i_oncogene_evidence()
        
        # Configure different scores per context
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.95)  # Strong therapeutic
        self.scoring_manager.set_evidence_score(ActionabilityType.DIAGNOSTIC, 0.6)   # Moderate diagnostic  
        self.scoring_manager.set_evidence_score(ActionabilityType.PROGNOSTIC, 0.2)   # Weak prognostic
        self.scoring_manager.set_default_strength(EvidenceStrength.EXPERT_CONSENSUS)
        
        # Configure mocks
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            total_score=12, classification=VICCOncogenicity.ONCOGENIC
        ))
        self.evidence_aggregator.set_oncokb_scoring(OncoKBScoring(
            therapeutic_level=OncoKBLevel.LEVEL_1,
            diagnostic_level=OncoKBLevel.LEVEL_3A,
            prognostic_level=None,
            oncogenicity_level="Oncogenic"
        ))
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Verify context-specific tier assignments (accept both IA and IB for strong evidence)
        assert result.amp_scoring.therapeutic_tier.tier_level in [AMPTierLevel.TIER_IA, AMPTierLevel.TIER_IB]  # Strong
        assert result.amp_scoring.diagnostic_tier.tier_level in [AMPTierLevel.TIER_IIC, AMPTierLevel.TIER_IID]  # Moderate
        
        # Prognostic may be None or Tier III due to weak evidence
        if result.amp_scoring.prognostic_tier:
            assert result.amp_scoring.prognostic_tier.tier_level in [AMPTierLevel.TIER_III, AMPTierLevel.TIER_IV]
        
        # Verify context-specific confidence
        assert result.amp_scoring.therapeutic_tier.confidence_score > 0.9
        assert result.amp_scoring.diagnostic_tier.confidence_score < 0.8
    
    def test_clean_setup_comparison(self):
        """Demonstrate the clean setup compared to old complex mocking approach"""
        
        # This test shows how simple the new approach is
        variant = create_braf_v600e_variant()
        
        # Single line evidence setup
        self.evidence_aggregator.set_evidence(create_tier_i_oncogene_evidence())
        
        # Simple score configuration
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.95)
        
        # Execute
        result = self.tier_engine.assign_tier(variant, "melanoma")
        
        # Verify (accept both IA and IB for strong evidence)
        assert result.gene_symbol == "BRAF"
        assert result.amp_scoring.therapeutic_tier.tier_level in [AMPTierLevel.TIER_IA, AMPTierLevel.TIER_IB]
        
        # Total lines of setup: ~5 lines vs old approach: ~20+ lines
        # No manual mock attribute manipulation needed!
        # No complex return value chaining!
        # Clear, readable test intent!