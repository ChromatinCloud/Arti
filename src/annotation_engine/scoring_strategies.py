"""
Evidence Scoring Strategies for Variant Annotation

Implements the Strategy Pattern to decouple evidence scoring logic from the tiering engine.
Each scorer focuses on a specific evidence type or scoring approach, making the system
more testable, maintainable, and extensible.

Key Benefits:
1. Separation of Concerns: Each scorer handles one specific evidence type
2. Testability: Individual scorers can be unit tested in isolation
3. Extensibility: New scoring strategies can be added without modifying core logic
4. Configurability: Scorers can be configured independently
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import Evidence, ActionabilityType, EvidenceWeights, EvidenceStrength


class EvidenceScorer(ABC):
    """Abstract base class for evidence scoring strategies"""
    
    def __init__(self, weights: EvidenceWeights):
        self.weights = weights
    
    @abstractmethod
    def can_score(self, evidence: Evidence) -> bool:
        """Determine if this scorer can handle the given evidence"""
        pass
    
    @abstractmethod
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        """Calculate the weighted score for this evidence in the given context"""
        pass
    
    @abstractmethod
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        """Determine the strength level of this evidence"""
        pass


class FDAApprovedScorer(EvidenceScorer):
    """Scores FDA-approved biomarker evidence (highest weight)"""
    
    def can_score(self, evidence: Evidence) -> bool:
        return ("FDA" in evidence.description or 
                evidence.source_kb == "FDA" or
                "fda-approved" in evidence.description.lower())
    
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        base_score = self.weights.fda_approved
        
        # FDA evidence is relevant to all contexts but strongest for therapeutic
        context_modifier = 1.0
        if context == ActionabilityType.THERAPEUTIC:
            context_modifier = 1.0
        elif context == ActionabilityType.DIAGNOSTIC:
            context_modifier = 0.9
        elif context == ActionabilityType.PROGNOSTIC:
            context_modifier = 0.8
        
        # Apply confidence weighting
        confidence = evidence.confidence or 0.9  # FDA evidence defaults to high confidence
        
        return base_score * context_modifier * confidence
    
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        return EvidenceStrength.FDA_APPROVED


class GuidelineEvidenceScorer(EvidenceScorer):
    """Scores professional guideline evidence"""
    
    def can_score(self, evidence: Evidence) -> bool:
        description_lower = evidence.description.lower()
        return any(term in description_lower for term in [
            "guideline", "professional", "society", "nccn", "esmo", "asco"
        ])
    
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        base_score = self.weights.professional_guidelines
        
        # Guidelines are strongest for therapeutic and diagnostic contexts
        context_modifier = 1.0
        if context == ActionabilityType.THERAPEUTIC:
            context_modifier = 1.0
        elif context == ActionabilityType.DIAGNOSTIC:
            context_modifier = 0.95
        elif context == ActionabilityType.PROGNOSTIC:
            context_modifier = 0.85
        
        # Apply cancer-type-specific bonus
        if self._is_cancer_type_specific(evidence):
            base_score += self.weights.cancer_type_specific_bonus
        
        confidence = evidence.confidence or 0.85
        return base_score * context_modifier * confidence
    
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        return EvidenceStrength.PROFESSIONAL_GUIDELINES
    
    def _is_cancer_type_specific(self, evidence: Evidence) -> bool:
        return ("cancer-type-specific" in evidence.description or 
                evidence.data.get("cancer_type_specific", False))


class ClinicalStudyScorer(EvidenceScorer):
    """Scores clinical study evidence (RCTs, meta-analyses, etc.)"""
    
    def can_score(self, evidence: Evidence) -> bool:
        description_lower = evidence.description.lower()
        return any(term in description_lower for term in [
            "meta-analysis", "systematic review", "rct", "randomized", 
            "clinical trial", "well-powered", "phase"
        ])
    
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        # Determine study type and base score
        description_lower = evidence.description.lower()
        
        if any(term in description_lower for term in ["meta-analysis", "systematic review"]):
            base_score = self.weights.meta_analysis
            strength = EvidenceStrength.META_ANALYSIS
        elif any(term in description_lower for term in ["rct", "randomized", "well-powered"]):
            base_score = self.weights.well_powered_rct
            strength = EvidenceStrength.WELL_POWERED_RCT
        else:
            # Generic clinical trial
            base_score = self.weights.multiple_small_studies
            strength = EvidenceStrength.MULTIPLE_SMALL_STUDIES
        
        # Clinical studies are most relevant for therapeutic context
        context_modifier = 1.0
        if context == ActionabilityType.THERAPEUTIC:
            context_modifier = 1.0
        elif context == ActionabilityType.PROGNOSTIC:
            context_modifier = 0.9
        elif context == ActionabilityType.DIAGNOSTIC:
            context_modifier = 0.8
        
        # Apply clinical trial bonus
        if "clinical trial" in description_lower:
            base_score += self.weights.clinical_trial_bonus
        
        # Apply cancer-type-specific bonus
        if self._is_cancer_type_specific(evidence):
            base_score += self.weights.cancer_type_specific_bonus
        
        confidence = evidence.confidence or 0.8
        return base_score * context_modifier * confidence
    
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        description_lower = evidence.description.lower()
        
        if any(term in description_lower for term in ["meta-analysis", "systematic review"]):
            return EvidenceStrength.META_ANALYSIS
        elif any(term in description_lower for term in ["rct", "randomized", "well-powered"]):
            return EvidenceStrength.WELL_POWERED_RCT
        else:
            return EvidenceStrength.MULTIPLE_SMALL_STUDIES
    
    def _is_cancer_type_specific(self, evidence: Evidence) -> bool:
        return ("cancer-type-specific" in evidence.description or 
                evidence.data.get("cancer_type_specific", False))


class ExpertConsensusScorer(EvidenceScorer):
    """Scores expert consensus evidence"""
    
    def can_score(self, evidence: Evidence) -> bool:
        description_lower = evidence.description.lower()
        return any(term in description_lower for term in [
            "expert consensus", "consensus", "expert panel", "expert opinion"
        ])
    
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        base_score = self.weights.expert_consensus
        
        # Expert consensus is valuable across all contexts
        context_modifier = 1.0
        
        # Apply cancer-type-specific bonus
        if self._is_cancer_type_specific(evidence):
            base_score += self.weights.cancer_type_specific_bonus
        
        confidence = evidence.confidence or 0.75
        return base_score * context_modifier * confidence
    
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        return EvidenceStrength.EXPERT_CONSENSUS
    
    def _is_cancer_type_specific(self, evidence: Evidence) -> bool:
        return ("cancer-type-specific" in evidence.description or 
                evidence.data.get("cancer_type_specific", False))


class CaseReportScorer(EvidenceScorer):
    """Scores case report and small study evidence"""
    
    def can_score(self, evidence: Evidence) -> bool:
        description_lower = evidence.description.lower()
        return any(term in description_lower for term in [
            "case report", "case series", "case study", "small study",
            "multiple studies", "published studies"
        ])
    
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        description_lower = evidence.description.lower()
        
        # Determine evidence type and base score
        if any(term in description_lower for term in ["multiple studies", "published studies"]):
            base_score = self.weights.multiple_small_studies
        else:
            base_score = self.weights.case_reports
        
        # Case reports are less reliable for diagnostic context
        context_modifier = 1.0
        if context == ActionabilityType.THERAPEUTIC:
            context_modifier = 1.0
        elif context == ActionabilityType.PROGNOSTIC:
            context_modifier = 0.9
        elif context == ActionabilityType.DIAGNOSTIC:
            context_modifier = 0.7
        
        # Apply off-label penalty if relevant
        if "off-label" in description_lower:
            base_score -= self.weights.off_label_penalty
        
        confidence = evidence.confidence or 0.6
        return max(0.0, base_score * context_modifier * confidence)
    
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        description_lower = evidence.description.lower()
        
        if any(term in description_lower for term in ["multiple studies", "published studies"]):
            return EvidenceStrength.MULTIPLE_SMALL_STUDIES
        else:
            return EvidenceStrength.CASE_REPORTS


class PreclinicalScorer(EvidenceScorer):
    """Scores preclinical and computational evidence"""
    
    def can_score(self, evidence: Evidence) -> bool:
        description_lower = evidence.description.lower()
        return any(term in description_lower for term in [
            "preclinical", "in vitro", "in vivo", "computational", 
            "functional", "molecular", "biochemical"
        ])
    
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float:
        base_score = self.weights.preclinical
        
        # Preclinical evidence is weakest for therapeutic, stronger for diagnostic/prognostic
        context_modifier = 1.0
        if context == ActionabilityType.DIAGNOSTIC:
            context_modifier = 1.1  # Functional evidence can support classification
        elif context == ActionabilityType.PROGNOSTIC:
            context_modifier = 1.0
        elif context == ActionabilityType.THERAPEUTIC:
            context_modifier = 0.8  # Less direct therapeutic relevance
        
        confidence = evidence.confidence or 0.5
        return base_score * context_modifier * confidence
    
    def get_evidence_strength(self, evidence: Evidence) -> EvidenceStrength:
        return EvidenceStrength.PRECLINICAL


class EvidenceScoringManager:
    """Manages multiple evidence scoring strategies using the Strategy Pattern"""
    
    def __init__(self, weights: EvidenceWeights):
        self.weights = weights
        self.scorers = [
            FDAApprovedScorer(weights),
            GuidelineEvidenceScorer(weights),
            ClinicalStudyScorer(weights),
            ExpertConsensusScorer(weights),
            CaseReportScorer(weights),
            PreclinicalScorer(weights)
        ]
    
    def calculate_evidence_score(self, evidence_list: List[Evidence], context: ActionabilityType) -> float:
        """Calculate comprehensive evidence score for a specific context"""
        context_evidence = self._filter_evidence_by_context(evidence_list, context)
        
        if not context_evidence:
            return 0.0
        
        total_score = 0.0
        max_possible = 0.0
        
        for evidence in context_evidence:
            # Find the appropriate scorer for this evidence
            scorer = self._find_scorer_for_evidence(evidence)
            
            if scorer:
                score = scorer.calculate_score(evidence, context)
                total_score += score
                max_possible += self.weights.fda_approved  # Maximum possible weight
            else:
                # Fallback to preclinical weight for unmatched evidence
                confidence = evidence.confidence or 0.5
                total_score += self.weights.preclinical * confidence
                max_possible += self.weights.fda_approved
        
        # Normalize to 0-1 scale
        return min(1.0, total_score / max(max_possible, 1.0)) if max_possible > 0 else 0.0
    
    def determine_strongest_evidence(self, evidence_list: List[Evidence], context: ActionabilityType) -> EvidenceStrength:
        """Determine the strongest evidence type for a given context"""
        context_evidence = self._filter_evidence_by_context(evidence_list, context)
        
        if not context_evidence:
            return EvidenceStrength.PRECLINICAL
        
        # Find the strongest evidence type among relevant evidence
        strongest = EvidenceStrength.PRECLINICAL
        strength_hierarchy = [
            EvidenceStrength.FDA_APPROVED,
            EvidenceStrength.PROFESSIONAL_GUIDELINES,
            EvidenceStrength.META_ANALYSIS,
            EvidenceStrength.WELL_POWERED_RCT,
            EvidenceStrength.EXPERT_CONSENSUS,
            EvidenceStrength.MULTIPLE_SMALL_STUDIES,
            EvidenceStrength.CASE_REPORTS,
            EvidenceStrength.PRECLINICAL
        ]
        
        for evidence in context_evidence:
            scorer = self._find_scorer_for_evidence(evidence)
            if scorer:
                evidence_strength = scorer.get_evidence_strength(evidence)
                for strength in strength_hierarchy:
                    if evidence_strength == strength:
                        if strength_hierarchy.index(strength) < strength_hierarchy.index(strongest):
                            strongest = strength
                        break
        
        return strongest
    
    def _filter_evidence_by_context(self, evidence_list: List[Evidence], context: ActionabilityType) -> List[Evidence]:
        """Filter evidence relevant to a specific actionability context"""
        relevant_evidence = []
        
        for evidence in evidence_list:
            if self._is_evidence_relevant_to_context(evidence, context):
                relevant_evidence.append(evidence)
        
        return relevant_evidence
    
    def _is_evidence_relevant_to_context(self, evidence: Evidence, context: ActionabilityType) -> bool:
        """Determine if evidence is relevant to a specific actionability context"""
        description = evidence.description.lower()
        
        if context == ActionabilityType.THERAPEUTIC:
            return any(term in description for term in [
                "therapy", "therapeutic", "treatment", "drug", "response", "resistance"
            ])
        elif context == ActionabilityType.DIAGNOSTIC:
            return any(term in description for term in [
                "diagnostic", "diagnosis", "classification", "subtype"
            ])
        elif context == ActionabilityType.PROGNOSTIC:
            return any(term in description for term in [
                "prognosis", "prognostic", "outcome", "survival", "recurrence"
            ])
        
        # Default: therapeutic evidence (most common)
        return context == ActionabilityType.THERAPEUTIC
    
    def _find_scorer_for_evidence(self, evidence: Evidence) -> Optional[EvidenceScorer]:
        """Find the most appropriate scorer for the given evidence"""
        for scorer in self.scorers:
            if scorer.can_score(evidence):
                return scorer
        return None
    
    def get_scorer_diagnostics(self, evidence_list: List[Evidence]) -> Dict[str, Any]:
        """Generate diagnostics about which scorers are being used"""
        diagnostics = {
            "total_evidence": len(evidence_list),
            "scorer_usage": {},
            "unmatched_evidence": []
        }
        
        for evidence in evidence_list:
            scorer = self._find_scorer_for_evidence(evidence)
            if scorer:
                scorer_name = scorer.__class__.__name__
                diagnostics["scorer_usage"][scorer_name] = diagnostics["scorer_usage"].get(scorer_name, 0) + 1
            else:
                diagnostics["unmatched_evidence"].append({
                    "code": evidence.code,
                    "description": evidence.description[:100] + "..." if len(evidence.description) > 100 else evidence.description
                })
        
        return diagnostics