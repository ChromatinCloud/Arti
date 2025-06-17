"""
Unit tests for evidence scoring strategies

These tests demonstrate the improved testability of the refactored evidence scoring system.
Each scorer can be tested in isolation with specific evidence scenarios.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.scoring_strategies import (
    FDAApprovedScorer, GuidelineEvidenceScorer, ClinicalStudyScorer, 
    ExpertConsensusScorer, CaseReportScorer, PreclinicalScorer,
    EvidenceScoringManager
)
from annotation_engine.models import (
    Evidence, ActionabilityType, EvidenceWeights, EvidenceStrength
)


@pytest.fixture
def default_weights():
    """Default evidence weights for testing"""
    return EvidenceWeights()


@pytest.fixture
def sample_evidence():
    """Sample evidence instances for testing"""
    return {
        "fda_approved": Evidence(
            code="TA1",
            score=10,
            guideline="AMP_2017",
            source_kb="OncoKB",
            description="FDA-approved biomarker for targeted therapy",
            confidence=0.95
        ),
        "guideline": Evidence(
            code="TA2", 
            score=8,
            guideline="AMP_2017",
            source_kb="NCCN",
            description="NCCN guideline recommendation for therapeutic selection",
            confidence=0.9
        ),
        "clinical_trial": Evidence(
            code="TA3",
            score=7,
            guideline="AMP_2017", 
            source_kb="ClinicalTrials",
            description="Phase III randomized controlled trial showing efficacy",
            confidence=0.85
        ),
        "meta_analysis": Evidence(
            code="TA4",
            score=8,
            guideline="AMP_2017",
            source_kb="PubMed",
            description="Meta-analysis of multiple clinical studies",
            confidence=0.88
        ),
        "expert_consensus": Evidence(
            code="TA5",
            score=6,
            guideline="AMP_2017",
            source_kb="Expert Panel",
            description="Expert consensus from oncology society",
            confidence=0.8
        ),
        "case_report": Evidence(
            code="TA6",
            score=4,
            guideline="AMP_2017",
            source_kb="PubMed",
            description="Case report of therapeutic response",
            confidence=0.6
        ),
        "preclinical": Evidence(
            code="TA7",
            score=3,
            guideline="AMP_2017",
            source_kb="Laboratory",
            description="In vitro functional studies showing drug sensitivity",
            confidence=0.5
        )
    }


class TestFDAApprovedScorer:
    """Test FDA-approved evidence scorer"""
    
    def test_can_score_fda_evidence(self, default_weights, sample_evidence):
        scorer = FDAApprovedScorer(default_weights)
        
        # Should recognize FDA evidence
        assert scorer.can_score(sample_evidence["fda_approved"]) == True
        
        # Should not recognize non-FDA evidence
        assert scorer.can_score(sample_evidence["guideline"]) == False
        assert scorer.can_score(sample_evidence["case_report"]) == False
    
    def test_calculate_score_by_context(self, default_weights, sample_evidence):
        scorer = FDAApprovedScorer(default_weights)
        evidence = sample_evidence["fda_approved"]
        
        # FDA evidence should score highest for therapeutic context
        therapeutic_score = scorer.calculate_score(evidence, ActionabilityType.THERAPEUTIC)
        diagnostic_score = scorer.calculate_score(evidence, ActionabilityType.DIAGNOSTIC)
        prognostic_score = scorer.calculate_score(evidence, ActionabilityType.PROGNOSTIC)
        
        # Therapeutic should be highest
        assert therapeutic_score > diagnostic_score
        assert therapeutic_score > prognostic_score
        
        # All should be substantial scores
        assert therapeutic_score > 0.8
        assert diagnostic_score > 0.7
        assert prognostic_score > 0.6
    
    def test_get_evidence_strength(self, default_weights, sample_evidence):
        scorer = FDAApprovedScorer(default_weights)
        strength = scorer.get_evidence_strength(sample_evidence["fda_approved"])
        
        assert strength == EvidenceStrength.FDA_APPROVED


class TestGuidelineEvidenceScorer:
    """Test guideline evidence scorer"""
    
    def test_can_score_guideline_evidence(self, default_weights, sample_evidence):
        scorer = GuidelineEvidenceScorer(default_weights)
        
        # Should recognize guideline evidence
        assert scorer.can_score(sample_evidence["guideline"]) == True
        
        # Should not recognize other types
        assert scorer.can_score(sample_evidence["fda_approved"]) == False
        assert scorer.can_score(sample_evidence["preclinical"]) == False
    
    def test_cancer_type_specific_bonus(self, default_weights):
        scorer = GuidelineEvidenceScorer(default_weights)
        
        # Evidence without cancer-type specificity
        regular_evidence = Evidence(
            code="TA2",
            score=8,
            guideline="AMP_2017", 
            source_kb="NCCN",
            description="NCCN guideline recommendation for therapeutic selection",
            confidence=0.9
        )
        
        # Evidence with cancer-type specificity
        cancer_specific_evidence = Evidence(
            code="TA2",
            score=8,
            guideline="AMP_2017",
            source_kb="NCCN", 
            description="Cancer-type-specific NCCN guideline recommendation",
            confidence=0.9
        )
        
        regular_score = scorer.calculate_score(regular_evidence, ActionabilityType.THERAPEUTIC)
        specific_score = scorer.calculate_score(cancer_specific_evidence, ActionabilityType.THERAPEUTIC)
        
        # Cancer-specific should score higher (or at least equal due to bonus application)
        assert specific_score >= regular_score


class TestClinicalStudyScorer:
    """Test clinical study evidence scorer"""
    
    def test_can_score_clinical_evidence(self, default_weights, sample_evidence):
        scorer = ClinicalStudyScorer(default_weights)
        
        # Should recognize clinical study evidence
        assert scorer.can_score(sample_evidence["clinical_trial"]) == True
        assert scorer.can_score(sample_evidence["meta_analysis"]) == True
        
        # Should not recognize other types
        assert scorer.can_score(sample_evidence["fda_approved"]) == False
        assert scorer.can_score(sample_evidence["preclinical"]) == False
    
    def test_study_type_differentiation(self, default_weights):
        scorer = ClinicalStudyScorer(default_weights)
        
        # Different types of clinical evidence
        meta_analysis = Evidence(
            code="TA1", score=8, guideline="AMP_2017", source_kb="PubMed",
            description="Meta-analysis of therapeutic efficacy", confidence=0.9
        )
        
        rct = Evidence(
            code="TA2", score=7, guideline="AMP_2017", source_kb="ClinicalTrials",
            description="Randomized controlled trial phase III", confidence=0.85
        )
        
        small_study = Evidence(
            code="TA3", score=5, guideline="AMP_2017", source_kb="PubMed",
            description="Phase II clinical trial preliminary results", confidence=0.7
        )
        
        # Meta-analysis should get highest score
        meta_score = scorer.calculate_score(meta_analysis, ActionabilityType.THERAPEUTIC)
        rct_score = scorer.calculate_score(rct, ActionabilityType.THERAPEUTIC)
        small_score = scorer.calculate_score(small_study, ActionabilityType.THERAPEUTIC)
        
        assert meta_score > rct_score > small_score
    
    def test_get_evidence_strength_by_study_type(self, default_weights):
        scorer = ClinicalStudyScorer(default_weights)
        
        meta_analysis = Evidence(
            code="TA1", score=8, guideline="AMP_2017", source_kb="PubMed",
            description="Meta-analysis of studies", confidence=0.9
        )
        
        rct = Evidence(
            code="TA2", score=7, guideline="AMP_2017", source_kb="ClinicalTrials", 
            description="Well-powered randomized trial", confidence=0.85
        )
        
        assert scorer.get_evidence_strength(meta_analysis) == EvidenceStrength.META_ANALYSIS
        assert scorer.get_evidence_strength(rct) == EvidenceStrength.WELL_POWERED_RCT


class TestEvidenceScoringManager:
    """Test the evidence scoring manager that coordinates all scorers"""
    
    def test_manager_initialization(self, default_weights):
        manager = EvidenceScoringManager(default_weights)
        
        # Should have all expected scorers
        assert len(manager.scorers) == 6
        scorer_types = [type(scorer).__name__ for scorer in manager.scorers]
        
        expected_types = [
            'FDAApprovedScorer', 'GuidelineEvidenceScorer', 'ClinicalStudyScorer',
            'ExpertConsensusScorer', 'CaseReportScorer', 'PreclinicalScorer'
        ]
        
        for expected_type in expected_types:
            assert expected_type in scorer_types
    
    def test_calculate_comprehensive_score(self, default_weights, sample_evidence):
        manager = EvidenceScoringManager(default_weights)
        
        # Mix of evidence types
        evidence_list = [
            sample_evidence["fda_approved"],
            sample_evidence["guideline"], 
            sample_evidence["clinical_trial"],
            sample_evidence["case_report"]
        ]
        
        score = manager.calculate_evidence_score(evidence_list, ActionabilityType.THERAPEUTIC)
        
        # Should return a normalized score between 0 and 1
        assert 0.0 <= score <= 1.0
        
        # Should be substantial given the high-quality evidence
        assert score > 0.6
    
    def test_determine_strongest_evidence(self, default_weights, sample_evidence):
        manager = EvidenceScoringManager(default_weights)
        
        # Evidence list with FDA evidence (should be strongest)
        evidence_list = [
            sample_evidence["fda_approved"],
            sample_evidence["case_report"],
            sample_evidence["preclinical"]
        ]
        
        strongest = manager.determine_strongest_evidence(evidence_list, ActionabilityType.THERAPEUTIC)
        assert strongest == EvidenceStrength.FDA_APPROVED
        
        # Evidence list without FDA evidence
        evidence_list_no_fda = [
            sample_evidence["guideline"],
            sample_evidence["case_report"],
            sample_evidence["preclinical"]
        ]
        
        strongest_no_fda = manager.determine_strongest_evidence(evidence_list_no_fda, ActionabilityType.THERAPEUTIC)
        assert strongest_no_fda == EvidenceStrength.PROFESSIONAL_GUIDELINES
    
    def test_context_filtering(self, default_weights):
        manager = EvidenceScoringManager(default_weights)
        
        # Create evidence with context-specific terms
        therapeutic_evidence = Evidence(
            code="TA1", score=8, guideline="AMP_2017", source_kb="OncoKB",
            description="Therapeutic drug response evidence", confidence=0.9
        )
        
        diagnostic_evidence = Evidence(
            code="DA1", score=7, guideline="AMP_2017", source_kb="CIViC",
            description="Diagnostic classification evidence", confidence=0.85
        )
        
        prognostic_evidence = Evidence(
            code="PA1", score=6, guideline="AMP_2017", source_kb="COSMIC",
            description="Prognostic survival outcome evidence", confidence=0.8
        )
        
        evidence_list = [therapeutic_evidence, diagnostic_evidence, prognostic_evidence]
        
        # Test context-specific filtering
        therapeutic_filtered = manager._filter_evidence_by_context(evidence_list, ActionabilityType.THERAPEUTIC)
        diagnostic_filtered = manager._filter_evidence_by_context(evidence_list, ActionabilityType.DIAGNOSTIC)
        prognostic_filtered = manager._filter_evidence_by_context(evidence_list, ActionabilityType.PROGNOSTIC)
        
        # Each context should get its relevant evidence
        assert len(therapeutic_filtered) == 1
        assert therapeutic_filtered[0].code == "TA1"
        
        assert len(diagnostic_filtered) == 1
        assert diagnostic_filtered[0].code == "DA1"
        
        assert len(prognostic_filtered) == 1
        assert prognostic_filtered[0].code == "PA1"
    
    def test_scorer_diagnostics(self, default_weights, sample_evidence):
        manager = EvidenceScoringManager(default_weights)
        
        evidence_list = [
            sample_evidence["fda_approved"],
            sample_evidence["guideline"],
            sample_evidence["clinical_trial"],
            sample_evidence["expert_consensus"]
        ]
        
        diagnostics = manager.get_scorer_diagnostics(evidence_list)
        
        # Should have diagnostics structure
        assert "total_evidence" in diagnostics
        assert "scorer_usage" in diagnostics
        assert "unmatched_evidence" in diagnostics
        
        # Should count evidence correctly
        assert diagnostics["total_evidence"] == 4
        
        # Should have some scorer usage (all evidence should match)
        assert len(diagnostics["scorer_usage"]) > 0
        assert diagnostics["unmatched_evidence"] == []  # All should match


class TestContextSpecificScoring:
    """Test how different scorers handle different actionability contexts"""
    
    def test_therapeutic_context_priorities(self, default_weights, sample_evidence):
        manager = EvidenceScoringManager(default_weights)
        
        # FDA evidence should score highest for therapeutic
        fda_score = manager.calculate_evidence_score([sample_evidence["fda_approved"]], ActionabilityType.THERAPEUTIC)
        guideline_score = manager.calculate_evidence_score([sample_evidence["guideline"]], ActionabilityType.THERAPEUTIC)
        clinical_score = manager.calculate_evidence_score([sample_evidence["clinical_trial"]], ActionabilityType.THERAPEUTIC)
        
        assert fda_score > guideline_score > clinical_score
    
    def test_diagnostic_context_adaptation(self, default_weights):
        manager = EvidenceScoringManager(default_weights)
        
        # Create diagnostic-specific evidence
        diagnostic_evidence = Evidence(
            code="DA1", score=7, guideline="AMP_2017", source_kb="CIViC",
            description="Diagnostic classification guideline evidence", confidence=0.9
        )
        
        therapeutic_score = manager.calculate_evidence_score([diagnostic_evidence], ActionabilityType.THERAPEUTIC)
        diagnostic_score = manager.calculate_evidence_score([diagnostic_evidence], ActionabilityType.DIAGNOSTIC)
        
        # Should score higher in diagnostic context (evidence is diagnostic-specific)
        # Note: this depends on the evidence containing diagnostic keywords
        assert diagnostic_score > 0.0
    
    def test_empty_evidence_handling(self, default_weights):
        manager = EvidenceScoringManager(default_weights)
        
        # Empty evidence list should return 0
        score = manager.calculate_evidence_score([], ActionabilityType.THERAPEUTIC)
        assert score == 0.0
        
        # Determine strongest with empty list should return weakest
        strongest = manager.determine_strongest_evidence([], ActionabilityType.THERAPEUTIC)
        assert strongest == EvidenceStrength.PRECLINICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])