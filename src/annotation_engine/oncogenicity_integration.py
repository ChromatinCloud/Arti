"""
Integration module for CGC/VICC oncogenicity classification with AMP/ASCO/CAP tiering

This module implements the two-layer sequential approach:
1. Layer 1: CGC/VICC oncogenicity classification (biological impact)
2. Layer 2: AMP/ASCO/CAP tier assignment (clinical actionability)

The oncogenicity classification serves as foundational evidence for tier assignment.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

from .cgc_vicc_classifier import (
    CGCVICCClassifier, OncogenicityResult, OncogenicityClassification,
    create_cgc_vicc_evidence
)
from .models import (
    VariantAnnotation, Evidence, TierResult, AMPTierLevel,
    VICCOncogenicity, AnalysisType
)
from .tiering import TieringEngine
from .evidence_aggregator import EvidenceAggregator

logger = logging.getLogger(__name__)


class OncogenicityAwareTieringEngine:
    """
    Enhanced tiering engine that incorporates CGC/VICC oncogenicity classification
    as foundational evidence for AMP/ASCO/CAP tier assignment
    """
    
    def __init__(self, 
                 config=None,
                 kb_path: Path = Path("./.refs")):
        # Initialize CGC/VICC classifier
        self.oncogenicity_classifier = CGCVICCClassifier(kb_path)
        
        # Initialize standard tiering engine
        self.tiering_engine = TieringEngine(config)
        
        # Initialize evidence aggregator
        self.evidence_aggregator = EvidenceAggregator()
        
        logger.info("Initialized oncogenicity-aware tiering engine")
    
    def assign_tier_with_oncogenicity(self,
                                     variant: VariantAnnotation,
                                     cancer_type: str,
                                     analysis_type: AnalysisType) -> TierResult:
        """
        Assign tier using two-layer approach:
        1. Classify oncogenicity using CGC/VICC
        2. Assign clinical tier using AMP/ASCO/CAP with oncogenicity as foundation
        
        Args:
            variant: Annotated variant
            cancer_type: Cancer type context
            analysis_type: Tumor-only or tumor-normal
            
        Returns:
            TierResult with integrated oncogenicity and clinical evidence
        """
        # Layer 1: Oncogenicity classification
        oncogenicity_result = self.oncogenicity_classifier.classify_variant(
            variant, cancer_type
        )
        
        logger.info(f"CGC/VICC classification for {variant.gene_symbol}:{variant.hgvs_p}: "
                   f"{oncogenicity_result.classification}")
        
        # Convert oncogenicity to evidence
        oncogenicity_evidence = create_cgc_vicc_evidence(oncogenicity_result)
        
        # Layer 2: Clinical evidence aggregation
        clinical_evidence = self.evidence_aggregator.aggregate_evidence(
            variant, cancer_type, analysis_type
        )
        
        # Combine evidence with oncogenicity as foundation
        all_evidence = oncogenicity_evidence + clinical_evidence
        
        # Apply tiering rules with oncogenicity consideration
        tier_result = self._assign_tier_with_oncogenicity_rules(
            variant,
            oncogenicity_result,
            all_evidence,
            cancer_type,
            analysis_type
        )
        
        # Add oncogenicity result to tier metadata
        tier_result.metadata["oncogenicity_classification"] = {
            "classification": oncogenicity_result.classification.value,
            "confidence": oncogenicity_result.confidence_score,
            "criteria_met": [c.criterion.value for c in oncogenicity_result.criteria_met],
            "rationale": oncogenicity_result.classification_rationale
        }
        
        return tier_result
    
    def _assign_tier_with_oncogenicity_rules(self,
                                           variant: VariantAnnotation,
                                           oncogenicity: OncogenicityResult,
                                           evidence: List[Evidence],
                                           cancer_type: str,
                                           analysis_type: AnalysisType) -> TierResult:
        """
        Apply tiering rules that consider oncogenicity classification
        """
        # Filter evidence by type
        therapeutic_evidence = [e for e in evidence if "therapeutic" in e.description.lower()]
        diagnostic_evidence = [e for e in evidence if "diagnostic" in e.description.lower()]
        prognostic_evidence = [e for e in evidence if "prognostic" in e.description.lower()]
        
        # Check for FDA-approved therapy
        fda_approved = any(e.code in ["ONCOKB_LEVEL_1", "FDA_APPROVED"] for e in therapeutic_evidence)
        guideline_included = any(e.code in ["ONCOKB_LEVEL_2", "NCCN_GUIDELINE"] for e in therapeutic_evidence)
        clinical_trial = any(e.code in ["ONCOKB_LEVEL_3A", "ONCOKB_LEVEL_3B"] for e in therapeutic_evidence)
        
        # Apply oncogenicity-aware tiering rules
        
        # Tier I: Requires oncogenic classification AND clinical evidence
        if oncogenicity.classification in [OncogenicityClassification.ONCOGENIC,
                                         OncogenicityClassification.LIKELY_ONCOGENIC]:
            if fda_approved:
                return self._create_tier_result(
                    AMPTierLevel.TIER_I_LEVEL_A,
                    evidence,
                    f"FDA-approved therapy available for {oncogenicity.classification.value.lower()} variant"
                )
            
            if guideline_included:
                return self._create_tier_result(
                    AMPTierLevel.TIER_I_LEVEL_B,
                    evidence,
                    f"Included in professional guidelines as {oncogenicity.classification.value.lower()} variant"
                )
        
        # Tier II: Clinical trial evidence with supporting oncogenicity
        if clinical_trial and oncogenicity.classification != OncogenicityClassification.BENIGN:
            if oncogenicity.classification == OncogenicityClassification.LIKELY_ONCOGENIC:
                return self._create_tier_result(
                    AMPTierLevel.TIER_II_LEVEL_C,
                    evidence,
                    "Clinical trial available for likely oncogenic variant"
                )
            elif oncogenicity.classification == OncogenicityClassification.VUS:
                # VUS with clinical trial evidence -> still Tier II but note uncertainty
                return self._create_tier_result(
                    AMPTierLevel.TIER_II_LEVEL_D,
                    evidence,
                    "Clinical trial available but oncogenic significance uncertain"
                )
        
        # Tier III: VUS regardless of other evidence
        if oncogenicity.classification == OncogenicityClassification.VUS:
            return self._create_tier_result(
                AMPTierLevel.TIER_III,
                evidence,
                "Variant of uncertain oncogenic significance"
            )
        
        # Tier IV: Benign/Likely Benign
        if oncogenicity.classification in [OncogenicityClassification.BENIGN,
                                         OncogenicityClassification.LIKELY_BENIGN]:
            return self._create_tier_result(
                AMPTierLevel.TIER_IV,
                evidence,
                f"{oncogenicity.classification.value} variant unlikely to be clinically relevant"
            )
        
        # Default: Tier III for any unclassified scenarios
        return self._create_tier_result(
            AMPTierLevel.TIER_III,
            evidence,
            "Insufficient evidence for definitive classification"
        )
    
    def _create_tier_result(self,
                           tier: AMPTierLevel,
                           evidence: List[Evidence],
                           rationale: str) -> TierResult:
        """Create a TierResult with proper scoring"""
        # Calculate confidence based on evidence
        confidence = self._calculate_tier_confidence(tier, evidence)
        
        # Use standard tiering engine to create proper result
        # but override with our tier assignment
        base_result = self.tiering_engine.assign_tier(evidence, None, None, None)
        
        # Override tier assignment
        base_result.amp_scoring.tier = tier
        base_result.amp_scoring.evidence_counts = self._count_evidence_by_type(evidence)
        base_result.confidence_score = confidence
        
        # Add our rationale
        if not base_result.metadata:
            base_result.metadata = {}
        base_result.metadata["tier_rationale"] = rationale
        
        return base_result
    
    def _calculate_tier_confidence(self, 
                                  tier: AMPTierLevel,
                                  evidence: List[Evidence]) -> float:
        """Calculate confidence score for tier assignment"""
        # Base confidence by tier
        tier_base_confidence = {
            AMPTierLevel.TIER_I_LEVEL_A: 0.95,
            AMPTierLevel.TIER_I_LEVEL_B: 0.90,
            AMPTierLevel.TIER_II_LEVEL_C: 0.80,
            AMPTierLevel.TIER_II_LEVEL_D: 0.70,
            AMPTierLevel.TIER_III: 0.50,
            AMPTierLevel.TIER_IV: 0.60
        }
        
        base_confidence = tier_base_confidence.get(tier, 0.5)
        
        # Adjust based on evidence quantity and quality
        evidence_boost = min(0.1, len(evidence) * 0.01)
        
        # High-quality evidence sources provide additional confidence
        high_quality_sources = ["OncoKB", "FDA", "NCCN", "CGC/VICC"]
        quality_boost = sum(0.02 for e in evidence 
                           if any(src in e.source_kb for src in high_quality_sources))
        
        return min(0.99, base_confidence + evidence_boost + quality_boost)
    
    def _count_evidence_by_type(self, evidence: List[Evidence]) -> Dict[str, int]:
        """Count evidence by category"""
        counts = {
            "therapeutic": 0,
            "diagnostic": 0,
            "prognostic": 0,
            "oncogenic": 0,
            "functional": 0,
            "total": len(evidence)
        }
        
        for e in evidence:
            if "therapeutic" in e.description.lower():
                counts["therapeutic"] += 1
            elif "diagnostic" in e.description.lower():
                counts["diagnostic"] += 1
            elif "prognostic" in e.description.lower():
                counts["prognostic"] += 1
            elif e.guideline == "CGC/VICC 2022":
                counts["oncogenic"] += 1
            else:
                counts["functional"] += 1
        
        return counts


def create_comprehensive_variant_report(variant: VariantAnnotation,
                                      cancer_type: str,
                                      analysis_type: AnalysisType,
                                      kb_path: Optional[Path] = None) -> Dict:
    """
    Create a comprehensive variant report using two-layer classification
    
    Returns complete JSON structure with oncogenicity and clinical tiers
    """
    # Initialize the oncogenicity-aware engine
    engine = OncogenicityAwareTieringEngine(kb_path=kb_path or Path("./.refs"))
    
    # Get tier result with integrated oncogenicity
    tier_result = engine.assign_tier_with_oncogenicity(
        variant, cancer_type, analysis_type
    )
    
    # Build comprehensive report
    report = {
        "variant": {
            "gene": variant.gene_symbol,
            "chromosome": variant.chromosome,
            "position": variant.position,
            "ref": variant.reference,
            "alt": variant.alternate,
            "hgvs_p": variant.hgvs_p,
            "hgvs_c": variant.hgvs_c,
            "consequence": variant.consequence,
            "vaf": variant.vaf
        },
        "clinical_context": {
            "cancer_type": cancer_type,
            "analysis_type": analysis_type.value
        },
        "classification": {
            "clinical_tier": {
                "tier": tier_result.amp_scoring.tier.value if tier_result.amp_scoring else "Unknown",
                "confidence": tier_result.confidence_score,
                "evidence_summary": tier_result.amp_scoring.evidence_counts if tier_result.amp_scoring else {}
            },
            "oncogenicity": tier_result.metadata.get("oncogenicity_classification", {}),
            "other_frameworks": {
                "vicc": tier_result.vicc_scoring.classification.value if tier_result.vicc_scoring else None,
                "oncokb": tier_result.oncokb_scoring.therapeutic_level.value if tier_result.oncokb_scoring else None
            }
        },
        "evidence": {
            "therapeutic": [
                {
                    "source": e.source_kb,
                    "description": e.description,
                    "score": e.score
                } for e in tier_result.evidence_list 
                if "therapeutic" in e.description.lower()
            ],
            "oncogenic": [
                {
                    "criterion": e.code,
                    "description": e.description,
                    "confidence": e.confidence
                } for e in tier_result.evidence_list
                if e.guideline == "CGC/VICC 2022"
            ]
        },
        "interpretation": {
            "summary": tier_result.canned_texts[0].content if tier_result.canned_texts else "",
            "clinical_impact": tier_result.metadata.get("tier_rationale", ""),
            "recommendations": _generate_recommendations(tier_result)
        }
    }
    
    return report


def _generate_recommendations(tier_result: TierResult) -> List[str]:
    """Generate clinical recommendations based on tier assignment"""
    recommendations = []
    
    tier = tier_result.amp_scoring.tier if tier_result.amp_scoring else None
    
    if tier == AMPTierLevel.TIER_I_LEVEL_A:
        recommendations.append("Consider FDA-approved targeted therapy")
        recommendations.append("Confirm variant with orthogonal method if not already done")
    elif tier == AMPTierLevel.TIER_I_LEVEL_B:
        recommendations.append("Review professional guidelines for treatment recommendations")
        recommendations.append("Consider molecular tumor board discussion")
    elif tier in [AMPTierLevel.TIER_II_LEVEL_C, AMPTierLevel.TIER_II_LEVEL_D]:
        recommendations.append("Search for relevant clinical trials")
        recommendations.append("Consider expanded genomic profiling")
    elif tier == AMPTierLevel.TIER_III:
        recommendations.append("Monitor for updates in variant classification")
        recommendations.append("Consider functional studies if available")
    elif tier == AMPTierLevel.TIER_IV:
        recommendations.append("No specific action required for this variant")
        recommendations.append("Focus on other identified variants if present")
    
    return recommendations