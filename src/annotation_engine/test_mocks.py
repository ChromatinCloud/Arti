"""
Clean mock implementations for testing the annotation engine

Provides simple, predictable mock objects that implement the dependency interfaces
without complex setup requirements.
"""

from typing import List, Optional, Dict, Any
from .models import (
    Evidence, VariantAnnotation, VICCScoring, OncoKBScoring, 
    DynamicSomaticConfidence, AnalysisType, CannedText,
    VICCOncogenicity, OncoKBLevel, ActionabilityType
)
from .dependency_injection import (
    EvidenceAggregatorInterface, WorkflowRouterInterface,
    CannedTextGeneratorInterface, ScoringManagerInterface
)


class MockEvidenceAggregator:
    """Mock evidence aggregator with predictable behavior"""
    
    def __init__(self):
        self.evidence_list = []
        self.vicc_scoring = VICCScoring(
            ovs1_score=0, os1_score=0, os2_score=4, os3_score=4,
            total_score=8, classification=VICCOncogenicity.ONCOGENIC
        )
        self.oncokb_scoring = OncoKBScoring(
            therapeutic_level=OncoKBLevel.LEVEL_3A,
            diagnostic_level=None,
            prognostic_level=None,
            therapeutic_implications="Actionable therapeutic biomarker",
            oncogenicity_level="Oncogenic"
        )
        self.dsc_scoring = None
    
    def set_evidence(self, evidence_list: List[Evidence]) -> None:
        """Set the evidence list to return"""
        self.evidence_list = evidence_list
    
    def set_vicc_scoring(self, vicc_scoring: VICCScoring) -> None:
        """Set the VICC scoring to return"""
        self.vicc_scoring = vicc_scoring
    
    def set_oncokb_scoring(self, oncokb_scoring: OncoKBScoring) -> None:
        """Set the OncoKB scoring to return"""
        self.oncokb_scoring = oncokb_scoring
    
    def set_dsc_scoring(self, dsc_scoring: Optional[DynamicSomaticConfidence]) -> None:
        """Set the DSC scoring to return"""
        self.dsc_scoring = dsc_scoring
    
    def aggregate_evidence(self, variant_annotation: VariantAnnotation, 
                         cancer_type: str, analysis_type: AnalysisType) -> List[Evidence]:
        """Return the configured evidence list"""
        return self.evidence_list
    
    def calculate_vicc_score(self, evidence_list: List[Evidence]) -> VICCScoring:
        """Return the configured VICC scoring"""
        return self.vicc_scoring
    
    def calculate_oncokb_score(self, evidence_list: List[Evidence], 
                             oncokb_evidence: Optional[Dict[str, Any]] = None) -> OncoKBScoring:
        """Return the configured OncoKB scoring"""
        return self.oncokb_scoring
    
    def calculate_dsc_score(self, variant_annotation: VariantAnnotation, 
                          evidence_list: List[Evidence], 
                          tumor_purity: Optional[float] = None) -> Optional[DynamicSomaticConfidence]:
        """Return the configured DSC scoring"""
        return self.dsc_scoring


class MockWorkflowRouter:
    """Mock workflow router with predictable behavior"""
    
    def __init__(self, should_include: bool = True, should_filter: bool = False):
        self.should_include = should_include
        self.should_filter = should_filter
    
    def set_should_include(self, should_include: bool) -> None:
        """Set whether variants should be included"""
        self.should_include = should_include
    
    def set_should_filter(self, should_filter: bool) -> None:
        """Set whether variants should be filtered"""
        self.should_filter = should_filter
    
    def should_include_variant(self, variant_annotation: VariantAnnotation, 
                             analysis_type: AnalysisType) -> bool:
        """Return the configured inclusion decision"""
        return self.should_include
    
    def should_filter_variant(self, tumor_vaf: float, normal_vaf: Optional[float] = None,
                            population_af: float = 0.0, is_hotspot: bool = False) -> bool:
        """Return the configured filtering decision"""
        return self.should_filter


class MockCannedTextGenerator:
    """Mock canned text generator with predictable behavior"""
    
    def __init__(self):
        self.texts = []
    
    def set_texts(self, texts: List[CannedText]) -> None:
        """Set the texts to return"""
        self.texts = texts
    
    def generate_gene_info_text(self, variant: VariantAnnotation, 
                              evidence_list: List[Evidence]) -> Optional[CannedText]:
        """Return first configured text or None"""
        return self.texts[0] if self.texts else None
    
    def generate_variant_info_text(self, variant: VariantAnnotation, 
                                 evidence_list: List[Evidence]) -> Optional[CannedText]:
        """Return second configured text or None"""
        return self.texts[1] if len(self.texts) > 1 else None


class MockScoringManager:
    """Mock scoring manager with predictable behavior"""
    
    def __init__(self):
        self.evidence_scores = {}
        self.default_score = 0.5
        self.default_strength = None
    
    def set_evidence_score(self, context: ActionabilityType, score: float) -> None:
        """Set score for a specific context"""
        self.evidence_scores[context] = score
    
    def set_default_score(self, score: float) -> None:
        """Set default score for all contexts"""
        self.default_score = score
    
    def set_default_strength(self, strength) -> None:
        """Set default evidence strength to return"""
        self.default_strength = strength
    
    def calculate_evidence_score(self, evidence_list: List[Evidence], 
                               context: ActionabilityType) -> float:
        """Return configured score for context or default"""
        return self.evidence_scores.get(context, self.default_score)
    
    def determine_strongest_evidence(self, evidence_list: List[Evidence], 
                                   context: ActionabilityType):
        """Return configured evidence strength or default"""
        if self.default_strength:
            return self.default_strength
        
        # Import here to avoid circular imports
        from .models import EvidenceStrength
        
        # Simple heuristic based on evidence descriptions
        for evidence in evidence_list:
            if self._is_evidence_relevant_to_context(evidence, context):
                if "FDA-approved" in evidence.description:
                    return EvidenceStrength.FDA_APPROVED
                elif "therapeutic" in evidence.description:
                    return EvidenceStrength.EXPERT_CONSENSUS
                elif "hotspot" in evidence.description:
                    return EvidenceStrength.MULTIPLE_SMALL_STUDIES
        
        return EvidenceStrength.CASE_REPORTS
    
    def _is_evidence_relevant_to_context(self, evidence: Evidence, context: ActionabilityType) -> bool:
        """Simple relevance check based on evidence description"""
        context_keywords = {
            ActionabilityType.THERAPEUTIC: ["therapeutic", "therapy", "treatment", "drug"],
            ActionabilityType.DIAGNOSTIC: ["diagnostic", "diagnosis", "biomarker"],
            ActionabilityType.PROGNOSTIC: ["prognostic", "prognosis", "survival", "outcome"]
        }
        
        keywords = context_keywords.get(context, [])
        return any(keyword in evidence.description.lower() for keyword in keywords)


def create_tier_i_evidence() -> List[Evidence]:
    """Create evidence list that should result in Tier I assignment"""
    return [
        Evidence(
            code="TA1",
            score=8,
            guideline="AMP_2017",
            source_kb="OncoKB",
            description="FDA-approved therapeutic biomarker with clinical evidence",
            data={
                "strength": 0.95,
                "direction": "Supports",
                "cancer_types": ["melanoma"],
                "therapeutic_context": True
            },
            confidence=0.95
        ),
        Evidence(
            code="OS3",
            score=4,
            guideline="VICC_2022",
            source_kb="CIViC",
            description="Well-established cancer hotspot with therapeutic implications",
            data={
                "strength": 0.9,
                "direction": "Supports",
                "cancer_types": ["melanoma"]
            },
            confidence=0.9
        )
    ]


def create_tier_iii_evidence() -> List[Evidence]:
    """Create evidence list that should result in Tier III assignment"""
    return [
        Evidence(
            code="BA1",
            score=-8,
            guideline="AMP_2017",
            source_kb="ClinVar",
            description="Stand-alone benign evidence",
            data={
                "strength": 0.8,
                "direction": "Benign",
                "cancer_types": []
            },
            confidence=0.8
        ),
        Evidence(
            code="BP1",
            score=-2,
            guideline="AMP_2017",
            source_kb="ClinVar",
            description="Supporting benign evidence",
            data={
                "strength": 0.3,
                "direction": "Benign",
                "cancer_types": []
            },
            confidence=0.3
        )
    ]


def create_test_variant_annotation() -> VariantAnnotation:
    """Create a test variant annotation"""
    return VariantAnnotation(
        chromosome="7",
        position=140753336,
        reference="T",
        alternate="A",
        gene_symbol="BRAF",
        hgvs_c="c.1799T>A",
        hgvs_p="p.Val600Glu",
        consequence=["missense_variant"],
        is_oncogene=True,
        is_tumor_suppressor=False,
        cancer_gene_census=True,
        tumor_vaf=0.45,
        normal_vaf=None,
        population_frequencies=[]
    )