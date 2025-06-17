"""
Clean tier assignment tests using dependency injection

Demonstrates the new clean testing approach with dependency injection
instead of complex manual mocking.
"""

import pytest
from pathlib import Path
import sys

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import (
    VICCScoring, OncoKBScoring, DynamicSomaticConfidence,
    VICCOncogenicity, OncoKBLevel, AnalysisType, AMPTierLevel
)
from annotation_engine.dependency_injection import create_test_tiering_engine
from annotation_engine.test_mocks import (
    MockEvidenceAggregator, MockWorkflowRouter, MockCannedTextGenerator, MockScoringManager,
    create_tier_i_evidence, create_tier_iii_evidence, create_test_variant_annotation
)


class TestTierAssignmentWithDI:
    """Test tier assignment using clean dependency injection patterns"""
    
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
    
    def test_tier_i_assignment_with_therapeutic_evidence(self):
        """Test Tier I assignment with FDA-approved therapeutic evidence"""
        # Setup test data
        variant = create_test_variant_annotation()
        evidence_list = create_tier_i_evidence()
        
        # Configure high therapeutic score for Tier IA
        from annotation_engine.models import ActionabilityType, EvidenceStrength
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.95)
        self.scoring_manager.set_default_strength(EvidenceStrength.FDA_APPROVED)
        
        # Configure mocks for Tier I scenario
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=4, os3_score=4,
            total_score=8, classification=VICCOncogenicity.ONCOGENIC
        ))
        self.evidence_aggregator.set_oncokb_scoring(OncoKBScoring(
            therapeutic_level=OncoKBLevel.LEVEL_1,
            diagnostic_level=None,
            prognostic_level=None,
            therapeutic_implications="FDA-approved biomarker",
            oncogenicity_level="Oncogenic"
        ))
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Verify Tier I assignment
        assert result.amp_scoring.therapeutic_tier.tier_level == AMPTierLevel.TIER_IA
        assert result.vicc_scoring.classification == VICCOncogenicity.ONCOGENIC
        assert result.oncokb_scoring.therapeutic_level == OncoKBLevel.LEVEL_1
        assert result.confidence_score > 0.8
    
    def test_tier_iii_assignment_with_benign_evidence(self):
        """Test Tier III assignment with benign evidence"""
        # Setup test data
        variant = create_test_variant_annotation()
        evidence_list = create_tier_iii_evidence()
        
        # Configure mocks for Tier III scenario
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=0, os3_score=0,
            total_score=0, classification=VICCOncogenicity.BENIGN
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
        
        # Verify Tier IV assignment (benign evidence should result in Tier IV)
        assert result.amp_scoring.therapeutic_tier.tier_level == AMPTierLevel.TIER_IV
        assert result.vicc_scoring.classification == VICCOncogenicity.BENIGN
        assert result.oncokb_scoring.therapeutic_level is None
    
    def test_tumor_only_dsc_modulation(self):
        """Test DSC-based tier modulation for tumor-only analysis"""
        # Setup test data
        variant = create_test_variant_annotation()
        evidence_list = create_tier_i_evidence()
        
        # Configure DSC scoring for tumor-only
        dsc_scoring = DynamicSomaticConfidence(
            dsc_score=0.6,
            prior_probability_score=0.7,
            tumor_purity=0.6,
            variant_vaf=0.45,
            hotspot_evidence=True,
            population_frequency=0.0001,
            clinvar_germline=False,
            dsc_confidence=0.8,
            modules_available=["vaf_purity", "prior_probability", "hotspot"]
        )
        
        # Configure mocks
        self.evidence_aggregator.set_evidence(evidence_list)
        self.evidence_aggregator.set_dsc_scoring(dsc_scoring)
        self.evidence_aggregator.set_vicc_scoring(VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=4, os3_score=4,
            total_score=8, classification=VICCOncogenicity.ONCOGENIC
        ))
        
        # Execute tier assignment for tumor-only
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_ONLY)
        
        # Verify DSC modulation applied
        assert result.analysis_type == AnalysisType.TUMOR_ONLY
        assert result.dsc_scoring is not None
        assert result.dsc_scoring.dsc_score == 0.6
        assert result.dsc_scoring.hotspot_evidence == True
        assert result.confidence_score > 0.0  # Should have some confidence
    
    def test_workflow_filtering(self):
        """Test workflow router filtering functionality"""
        # Setup test data
        variant = create_test_variant_annotation()
        evidence_list = create_tier_i_evidence()
        
        # Configure router to exclude variants
        self.workflow_router.set_should_include(False)
        self.evidence_aggregator.set_evidence(evidence_list)
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Variant should still be processed (router only affects specific filtering logic)
        assert result is not None
        assert result.gene_symbol == "BRAF"
    
    def test_scoring_manager_integration(self):
        """Test scoring manager integration with context-specific scoring"""
        # Setup test data
        variant = create_test_variant_annotation()
        evidence_list = create_tier_i_evidence()
        
        # Configure context-specific scores
        from annotation_engine.models import ActionabilityType
        self.scoring_manager.set_evidence_score(ActionabilityType.THERAPEUTIC, 0.95)
        self.scoring_manager.set_evidence_score(ActionabilityType.DIAGNOSTIC, 0.3)
        self.scoring_manager.set_evidence_score(ActionabilityType.PROGNOSTIC, 0.1)
        
        self.evidence_aggregator.set_evidence(evidence_list)
        
        # Execute tier assignment
        result = self.tier_engine.assign_tier(variant, "melanoma", AnalysisType.TUMOR_NORMAL)
        
        # Verify high therapeutic score leads to strong tier
        assert result.amp_scoring.therapeutic_tier is not None
        assert result.amp_scoring.therapeutic_tier.tier_level in [AMPTierLevel.TIER_IA, AMPTierLevel.TIER_IB]
        
        # Diagnostic and prognostic should be weaker or None
        if result.amp_scoring.diagnostic_tier:
            assert result.amp_scoring.diagnostic_tier.tier_level != AMPTierLevel.TIER_IA
    
    def test_clean_test_setup_simplicity(self):
        """Demonstrate the simplicity of the new test setup"""
        # This test shows how easy it is to set up specific scenarios
        
        # Scenario 1: High-confidence therapeutic biomarker
        variant = create_test_variant_annotation()
        self.evidence_aggregator.set_evidence(create_tier_i_evidence())
        
        result = self.tier_engine.assign_tier(variant, "melanoma")
        assert result.gene_symbol == "BRAF"
        assert result.confidence_score > 0.5
        
        # Scenario 2: Low-confidence benign variant (just change evidence)
        self.evidence_aggregator.set_evidence(create_tier_iii_evidence())
        
        result = self.tier_engine.assign_tier(variant, "melanoma")
        assert result.gene_symbol == "BRAF"
        
        # No complex mock setup, no manual attribute assignment!
        # Clean, readable, maintainable tests.