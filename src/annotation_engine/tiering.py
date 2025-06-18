"""
Tiering Module for Somatic Variant Annotation

Implements tier assignment following AMP/ASCO/CAP 2017, VICC/CGC 2022, and OncoKB guidelines.
Provides assign_tier(evidence_list) -> TierResult function equivalent to CancerVar's 12 CBP criteria.

Key responsibilities:
1. Implement AMP/ASCO/CAP 2017 therapeutic actionability tiers (I, II, IIe, III, IV)
2. Implement VICC/CGC 2022 oncogenicity scoring with point-based system
3. Integrate OncoKB therapeutic evidence levels
4. Generate canned text for clinical interpretation
5. Provide confidence scoring and completeness metrics
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from pathlib import Path

from .models import (
    Evidence, TierResult, VICCScoring, AMPScoring, OncoKBScoring,
    CannedText, CannedTextType, AMPTierLevel, VICCOncogenicity, OncoKBLevel,
    VariantAnnotation, AnnotationConfig, EvidenceStrength, ActionabilityType,
    ContextSpecificTierAssignment, EvidenceWeights, AnalysisType, DynamicSomaticConfidence
)
from .evidence_aggregator import EvidenceAggregator
from .scoring_strategies import EvidenceScoringManager
from .dependency_injection import (
    EvidenceAggregatorInterface, WorkflowRouterInterface, 
    CannedTextGeneratorInterface, ScoringManagerInterface
)

logger = logging.getLogger(__name__)


class CannedTextGenerator:
    """Generates canned text for clinical interpretation"""
    
    def __init__(self):
        self.confidence_threshold = 0.7
    
    def generate_gene_info_text(self, variant: VariantAnnotation, evidence_list: List[Evidence]) -> Optional[CannedText]:
        """Generate general gene information text"""
        gene = variant.gene_symbol
        
        # Check if gene has sufficient evidence for text generation
        gene_evidence = [e for e in evidence_list if 'gene' in e.description.lower()]
        if not gene_evidence:
            return None
        
        # Build gene description
        content_parts = []
        
        if variant.is_tumor_suppressor:
            content_parts.append(f"{gene} is a tumor suppressor gene.")
        elif variant.is_oncogene:
            content_parts.append(f"{gene} is an oncogene.")
        
        if variant.cancer_gene_census:
            content_parts.append(f"{gene} is included in the COSMIC Cancer Gene Census.")
        
        # Add therapeutic context if available
        therapeutic_evidence = [e for e in evidence_list if e.guideline == "AMP_2017"]
        if therapeutic_evidence:
            content_parts.append(f"Variants in {gene} may have therapeutic implications.")
        
        if not content_parts:
            return None
        
        content = " ".join(content_parts)
        
        return CannedText(
            text_type=CannedTextType.GENERAL_GENE_INFO,
            content=content,
            confidence=0.8,
            evidence_support=[e.code for e in gene_evidence],
            triggered_by=["gene_context"]
        )
    
    def generate_variant_info_text(self, variant: VariantAnnotation, evidence_list: List[Evidence]) -> Optional[CannedText]:
        """Generate general variant information text"""
        
        # Check for hotspot evidence
        hotspot_evidence = [e for e in evidence_list if "hotspot" in e.description.lower()]
        functional_evidence = [e for e in evidence_list if "computational" in e.description.lower()]
        
        content_parts = []
        
        # Add consequence information
        if variant.consequence:
            primary_consequence = variant.consequence[0].replace('_', ' ')
            content_parts.append(f"This variant results in {primary_consequence}.")
        
        # Add hotspot information
        if hotspot_evidence:
            for evidence in hotspot_evidence:
                if evidence.code == "OS3":
                    content_parts.append("This variant occurs at a well-established cancer hotspot.")
                elif evidence.code == "OM3":
                    content_parts.append("This variant occurs at a moderately recurrent cancer hotspot.")
        
        # Add functional prediction information
        if functional_evidence:
            for evidence in functional_evidence:
                if evidence.code == "OP1":
                    content_parts.append("Computational analysis predicts this variant has a damaging effect on protein function.")
                elif evidence.code == "SBP1":
                    content_parts.append("Computational analysis suggests this variant has minimal impact on protein function.")
        
        # Add population frequency context
        pop_freq_evidence = [e for e in evidence_list if "frequency" in e.description.lower()]
        if pop_freq_evidence:
            for evidence in pop_freq_evidence:
                if evidence.code == "SBVS1":
                    content_parts.append("This variant is common in population databases, suggesting it may be a germline polymorphism.")
                elif evidence.code == "OP4":
                    content_parts.append("This variant is very rare in population databases.")
        
        if not content_parts:
            return None
        
        content = " ".join(content_parts)
        
        return CannedText(
            text_type=CannedTextType.GENERAL_VARIANT_INFO,
            content=content,
            confidence=0.8,
            evidence_support=[e.code for e in evidence_list[:3]],  # Top evidence
            triggered_by=["variant_annotation"]
        )
    
    def generate_diagnostic_interpretation_text(self, tier_result: TierResult) -> Optional[CannedText]:
        """Generate variant diagnostic interpretation text"""
        
        content_parts = []
        amp_scoring = tier_result.amp_scoring
        vicc_classification = tier_result.vicc_scoring.classification
        is_tumor_only = tier_result.analysis_type == AnalysisType.TUMOR_ONLY
        dsc_score = tier_result.dsc_scoring.dsc_score if tier_result.dsc_scoring else 1.0
        
        # Get context-specific tiers
        context_tiers = amp_scoring.get_context_tiers()
        primary_tier = amp_scoring.get_primary_tier()
        
        # Multi-context tier interpretation with TO uncertainty language
        if context_tiers:
            if "therapeutic" in context_tiers:
                tier_level = context_tiers["therapeutic"]
                if tier_level == "Tier IA":
                    base_text = "This variant has strong therapeutic significance with FDA-approved or guideline-recommended therapy for this cancer type."
                    if is_tumor_only:
                        if dsc_score > 0.99:
                            base_text = "This **somatic** variant has strong therapeutic significance with FDA-approved or guideline-recommended therapy for this cancer type."
                        elif dsc_score > 0.6:
                            base_text = "This variant, **which is likely somatic**, has strong therapeutic significance with FDA-approved or guideline-recommended therapy for this cancer type."
                        else:
                            base_text = "A variant of **uncertain origin** was detected. If somatic, this variant has strong therapeutic significance with FDA-approved or guideline-recommended therapy for this cancer type."
                    content_parts.append(base_text)
                elif tier_level == "Tier IB":
                    base_text = "This variant has strong therapeutic significance based on expert consensus from well-powered studies."
                    if is_tumor_only:
                        base_text = "This variant, **assuming somatic origin**, has strong therapeutic significance based on expert consensus from well-powered studies."
                    content_parts.append(base_text)
                elif tier_level == "Tier IIC":
                    base_text = "This variant has potential therapeutic significance with emerging evidence or off-label indications."
                    if is_tumor_only:
                        base_text = "This variant has **potential** therapeutic significance with emerging evidence or off-label indications, pending confirmation of somatic origin."
                    content_parts.append(base_text)
                elif tier_level == "Tier IID":
                    base_text = "This variant has limited therapeutic significance based on preclinical studies or case reports."
                    if is_tumor_only:
                        base_text = "This variant **may have** limited therapeutic significance based on preclinical studies or case reports, assuming somatic origin."
                    content_parts.append(base_text)
                elif tier_level == "Tier IIE":
                    base_text = "This variant has investigational significance with emerging clinical trial evidence."
                    if is_tumor_only:
                        base_text = "This variant **potentially has** investigational significance with emerging clinical trial evidence, pending somatic confirmation."
                    content_parts.append(base_text)
            
            if "diagnostic" in context_tiers:
                tier_level = context_tiers["diagnostic"]
                if tier_level in ["Tier IA", "Tier IB"]:
                    base_text = "This variant has diagnostic significance for cancer classification."
                    if is_tumor_only:
                        base_text = "This variant **may have** diagnostic significance for cancer classification, assuming somatic origin."
                    content_parts.append(base_text)
                elif tier_level in ["Tier IIC", "Tier IID", "Tier IIE"]:
                    base_text = "This variant may have diagnostic utility but requires additional validation."
                    if is_tumor_only:
                        base_text = "This variant **potentially has** diagnostic utility but requires additional validation and somatic confirmation."
                    content_parts.append(base_text)
            
            if "prognostic" in context_tiers:
                tier_level = context_tiers["prognostic"]
                if tier_level in ["Tier IA", "Tier IB"]:
                    base_text = "This variant has established prognostic significance."
                    if is_tumor_only:
                        base_text = "This variant **likely has** established prognostic significance, assuming somatic origin."
                    content_parts.append(base_text)
                elif tier_level in ["Tier IIC", "Tier IID", "Tier IIE"]:
                    base_text = "This variant may have prognostic implications but evidence is limited."
                    if is_tumor_only:
                        base_text = "This variant **may have** prognostic implications but evidence is limited and somatic origin unconfirmed."
                    content_parts.append(base_text)
        
        # Fallback to overall tier if no context-specific assignments
        if not content_parts:
            if primary_tier == "Tier IA":
                content_parts.append("This variant has strong clinical significance with high-level evidence.")
            elif primary_tier == "Tier IB":
                content_parts.append("This variant has strong clinical significance based on expert consensus.")
            elif primary_tier in ["Tier IIC", "Tier IID"]:
                content_parts.append("This variant has potential clinical significance but evidence is limited.")
            elif primary_tier == "Tier IIE":
                content_parts.append("This variant has investigational significance with emerging evidence.")
            elif primary_tier == "Tier III":
                content_parts.append("This variant has unknown clinical significance.")
            elif primary_tier == "Tier IV":
                content_parts.append("This variant is likely benign or has no clinical significance.")
        
        # Add oncogenicity assessment
        if vicc_classification == VICCOncogenicity.ONCOGENIC:
            content_parts.append("The variant is classified as oncogenic based on strong evidence.")
        elif vicc_classification == VICCOncogenicity.LIKELY_ONCOGENIC:
            content_parts.append("The variant is classified as likely oncogenic based on moderate evidence.")
        elif vicc_classification == VICCOncogenicity.UNCERTAIN_SIGNIFICANCE:
            content_parts.append("The oncogenic significance of this variant is uncertain.")
        elif vicc_classification == VICCOncogenicity.LIKELY_BENIGN:
            content_parts.append("The variant is likely benign based on available evidence.")
        elif vicc_classification == VICCOncogenicity.BENIGN:
            content_parts.append("The variant is classified as benign.")
        
        # Add therapeutic implications
        therapies = tier_result.get_therapeutic_implications()
        if therapies:
            therapy_text = ", ".join(therapies[:3])  # Limit to first 3
            if len(therapies) > 3:
                therapy_text += f" and {len(therapies) - 3} other(s)"
            
            if is_tumor_only:
                content_parts.append(f"**Potential** therapeutic options include: {therapy_text}, pending confirmation of somatic origin.")
            else:
                content_parts.append(f"Potential therapeutic options include: {therapy_text}.")
        
        content = " ".join(content_parts)
        
        return CannedText(
            text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
            content=content,
            confidence=0.9,
            evidence_support=[e.code for e in tier_result.evidence[:5]],
            triggered_by=[primary_tier, vicc_classification.value]
        )
    
    def generate_biomarker_text(self, tier_result: TierResult) -> Optional[CannedText]:
        """Generate biomarker-specific text"""
        
        # Check for OncoKB Level 1 evidence (FDA-approved biomarkers)
        if tier_result.oncokb_scoring.therapeutic_level == OncoKBLevel.LEVEL_1:
            content = f"This variant in {tier_result.gene_symbol} represents an FDA-approved biomarker for therapeutic decision-making in {tier_result.cancer_type}."
            
            return CannedText(
                text_type=CannedTextType.BIOMARKERS,
                content=content,
                confidence=0.95,
                evidence_support=["FDA_APPROVED"],
                triggered_by=["OncoKB_Level_1"]
            )
        
        # Check for other biomarker evidence
        biomarker_evidence = [e for e in tier_result.evidence if "biomarker" in e.description.lower()]
        if biomarker_evidence:
            content = f"This variant may serve as a biomarker for therapeutic selection in {tier_result.cancer_type}."
            
            return CannedText(
                text_type=CannedTextType.BIOMARKERS,
                content=content,
                confidence=0.8,
                evidence_support=[e.code for e in biomarker_evidence],
                triggered_by=["biomarker_evidence"]
            )
        
        return None
    
    def generate_tumor_only_disclaimers(self, tier_result: TierResult) -> Optional[CannedText]:
        """Generate mandatory disclaimers for tumor-only reports per TN_VERSUS_TO.md"""
        
        if tier_result.analysis_type != AnalysisType.TUMOR_ONLY:
            return None
        
        # Build disclaimer content based on TN_VERSUS_TO.md requirements
        disclaimer_parts = []
        
        # 1. Somatic Status Disclaimer
        disclaimer_parts.append(
            "**Somatic Status:** This analysis was performed on a tumor sample without a matched normal specimen. "
            "Somatic variants were inferred by filtering against population databases and a panel of normals. "
            "The germline or somatic origin of the reported variants has not been confirmed."
        )
        
        # 2. Therapeutic Implications Disclaimer
        disclaimer_parts.append(
            "**Therapeutic Implications:** Therapeutic recommendations based on these findings are predictive "
            "and assume the variants are somatic drivers. The absence of a matched normal sample reduces "
            "confidence in this assumption."
        )
        
        # 3. Incidental/Secondary Findings Disclaimer (check for cancer predisposition genes)
        gene_symbol = tier_result.gene_symbol
        predisposition_genes = {"BRCA1", "BRCA2", "TP53", "MLH1", "MSH2", "MSH6", "PMS2", "APC", "PALB2", "CHEK2", "ATM", "CDKN2A"}
        
        if gene_symbol in predisposition_genes:
            disclaimer_parts.append(
                f"**Incidental/Secondary Findings:** This assay detected a variant in {gene_symbol}, "
                "a cancer predisposition gene. This finding is of uncertain origin (somatic vs. germline) "
                "and should be considered a **potential incidental finding.** Confirmatory germline testing "
                "from a non-tumor specimen (e.g., blood) is required for definitive diagnosis and genetic counseling."
            )
        
        # 4. Biomarker Limitations Disclaimer
        disclaimer_parts.append(
            "**Biomarker Limitations:** Tumor Mutational Burden (TMB) may be overestimated due to the "
            "potential inclusion of unfiltered germline variants. Copy Number Variation (CNV) and "
            "structural variant (SV) analysis is limited and less accurate without a matched normal."
        )
        
        content = "\n\n".join(disclaimer_parts)
        
        return CannedText(
            text_type=CannedTextType.TUMOR_ONLY_DISCLAIMERS,
            content=content,
            confidence=1.0,  # Mandatory disclaimers always generated
            evidence_support=["TUMOR_ONLY_ANALYSIS"],
            triggered_by=["analysis_type_tumor_only"]
        )
    
    def generate_technical_comments(self, tier_result: TierResult) -> Optional[CannedText]:
        """Generate technical comments about the annotation"""
        
        content_parts = []
        
        # Annotation completeness
        if tier_result.annotation_completeness < 0.8:
            content_parts.append("Limited knowledge base coverage for this variant.")
        
        # Confidence assessment
        if tier_result.confidence_score < 0.7:
            content_parts.append("Lower confidence in tier assignment due to limited evidence.")
        
        # Evidence summary
        evidence_summary = tier_result.get_evidence_summary()
        total_evidence = sum(evidence_summary.values())
        if total_evidence > 0:
            content_parts.append(f"Based on {total_evidence} evidence items across {len([k for k, v in evidence_summary.items() if v > 0])} guidelines.")
        
        # Knowledge base versions
        if tier_result.kb_versions:
            kb_list = ", ".join(tier_result.kb_versions.keys())
            content_parts.append(f"Annotation based on: {kb_list}.")
        
        if not content_parts:
            return None
        
        content = " ".join(content_parts)
        
        return CannedText(
            text_type=CannedTextType.TECHNICAL_COMMENTS,
            content=content,
            confidence=0.9,
            evidence_support=[],
            triggered_by=["technical_annotation"]
        )


class TieringEngine:
    """Main tiering engine implementing AMP/ASCO/CAP 2017 and VICC/CGC 2022 guidelines"""
    
    def __init__(self, 
                 config: Optional[AnnotationConfig] = None, 
                 workflow_router: Optional[WorkflowRouterInterface] = None,
                 evidence_aggregator: Optional[EvidenceAggregatorInterface] = None,
                 text_generator: Optional[CannedTextGeneratorInterface] = None,
                 scoring_manager: Optional[ScoringManagerInterface] = None):
        """
        Initialize TieringEngine with optional dependency injection
        
        Args:
            config: Annotation configuration
            workflow_router: Optional workflow router for variant filtering
            evidence_aggregator: Optional evidence aggregator (for testing)
            text_generator: Optional text generator (for testing)
            scoring_manager: Optional scoring manager (for testing)
        """
        self.config = config or AnnotationConfig(kb_base_path=".refs")
        self.workflow_router = workflow_router
        
        # Use injected dependencies or create defaults
        if evidence_aggregator is not None:
            self.evidence_aggregator = evidence_aggregator
        else:
            self.evidence_aggregator = EvidenceAggregator(self.config.kb_base_path, workflow_router)
        
        if text_generator is not None:
            self.text_generator = text_generator
        else:
            # Use comprehensive generator with enhanced narratives by default
            from .canned_text_integration import ComprehensiveCannedTextGenerator
            self.text_generator = ComprehensiveCannedTextGenerator(use_enhanced_narratives=True)
        
        if scoring_manager is not None:
            self.scoring_manager = scoring_manager
        else:
            self.scoring_manager = EvidenceScoringManager(self.config.evidence_weights)
        
    def _calculate_evidence_score(self, evidence_list: List[Evidence], context: ActionabilityType) -> float:
        """Calculate quantitative evidence score for a specific context using strategy pattern"""
        return self.scoring_manager.calculate_evidence_score(evidence_list, context)
    
    def _is_evidence_relevant_to_context(self, evidence: Evidence, context: ActionabilityType) -> bool:
        """Determine if evidence is relevant to a specific actionability context"""
        return self.scoring_manager._is_evidence_relevant_to_context(evidence, context)
    
    def _assign_context_tier(self, evidence_score: float, evidence_strength: EvidenceStrength, 
                           context: ActionabilityType, cancer_type_specific: bool) -> ContextSpecificTierAssignment:
        """Assign tier level for a specific context based on evidence"""
        
        # Determine tier level based on evidence score and strength
        if evidence_score >= self.config.amp_tier_ia_threshold and evidence_strength in [
            EvidenceStrength.FDA_APPROVED, EvidenceStrength.PROFESSIONAL_GUIDELINES
        ]:
            tier_level = AMPTierLevel.TIER_IA
        elif evidence_score >= self.config.amp_tier_ib_threshold and evidence_strength in [
            EvidenceStrength.META_ANALYSIS, EvidenceStrength.WELL_POWERED_RCT, EvidenceStrength.EXPERT_CONSENSUS
        ]:
            tier_level = AMPTierLevel.TIER_IB
        elif evidence_score >= self.config.amp_tier_iic_threshold and evidence_strength in [
            EvidenceStrength.MULTIPLE_SMALL_STUDIES, EvidenceStrength.EXPERT_CONSENSUS
        ]:
            tier_level = AMPTierLevel.TIER_IIC
        elif evidence_score >= self.config.amp_tier_iid_threshold:
            tier_level = AMPTierLevel.TIER_IID
        elif evidence_score > 0.1:  # Some evidence
            tier_level = AMPTierLevel.TIER_III
        else:
            tier_level = AMPTierLevel.TIER_IV
        
        # Calculate confidence
        confidence = min(1.0, evidence_score + (0.1 if cancer_type_specific else 0.0))
        
        return ContextSpecificTierAssignment(
            actionability_type=context,
            tier_level=tier_level,
            evidence_strength=evidence_strength,
            evidence_score=evidence_score,
            confidence_score=confidence,
            fda_approved=(evidence_strength == EvidenceStrength.FDA_APPROVED),
            guideline_included=(evidence_strength == EvidenceStrength.PROFESSIONAL_GUIDELINES),
            expert_consensus=(evidence_strength == EvidenceStrength.EXPERT_CONSENSUS),
            cancer_type_specific=cancer_type_specific
        )
    
    def assign_tier(self, variant_annotation: VariantAnnotation, cancer_type: str, 
                  analysis_type: AnalysisType = AnalysisType.TUMOR_ONLY) -> TierResult:
        """
        Main tier assignment function with comprehensive multi-context AMP/ASCO/CAP 2017 implementation
        
        Args:
            variant_annotation: VEP-annotated variant with evidence
            cancer_type: Cancer type context
            analysis_type: Analysis workflow type (TUMOR_NORMAL vs TUMOR_ONLY)
            
        Returns:
            Complete tier assignment result with context-specific tiers
        """
        logger.info(f"assign_tier called for {variant_annotation.gene_symbol} with cancer_type={cancer_type}")
        
        # Step 0: Apply workflow-specific variant filtering if router available
        if self.workflow_router and hasattr(variant_annotation, 'tumor_vaf'):
            tumor_vaf = variant_annotation.tumor_vaf
            normal_vaf = getattr(variant_annotation, 'normal_vaf', None)
            
            # Get max population frequency from variant
            max_pop_af = 0.0
            if variant_annotation.population_frequencies:
                max_pop_af = max(pf.allele_frequency for pf in variant_annotation.population_frequencies)
            
            # Check if variant is in hotspot
            is_hotspot = bool(variant_annotation.hotspot_evidence)
            
            # Apply workflow filtering
            should_filter = self.workflow_router.should_filter_variant(
                tumor_vaf=tumor_vaf,
                normal_vaf=normal_vaf,
                population_af=max_pop_af,
                is_hotspot=is_hotspot
            )
            
            if should_filter:
                # Return filtered result (Tier IV with explanation)
                # Create minimal AMP scoring for filtered variant
                filtered_amp_scoring = AMPScoring(
                    therapeutic_tier=ContextSpecificTierAssignment(
                        actionability_type=ActionabilityType.THERAPEUTIC,
                        tier_level=AMPTierLevel.TIER_IV,
                        evidence_strength=EvidenceStrength.PRECLINICAL,
                        evidence_score=0.0,
                        confidence_score=0.1
                    ),
                    diagnostic_tier=None,
                    prognostic_tier=None,
                    cancer_type_specific=False,
                    related_cancer_types=[],
                    overall_confidence=0.1,
                    evidence_completeness=0.0
                )
                
                return TierResult(
                    variant_id=f"{variant_annotation.chromosome}:{variant_annotation.position}:{variant_annotation.reference}>{variant_annotation.alternate}",
                    gene_symbol=variant_annotation.gene_symbol or "Unknown",
                    hgvs_p=variant_annotation.hgvs_p,
                    analysis_type=analysis_type,
                    dsc_scoring=None,
                    amp_scoring=filtered_amp_scoring,
                    vicc_scoring=VICCScoring(),
                    oncokb_scoring=OncoKBScoring(),
                    evidence=[],
                    cancer_type=cancer_type,
                    canned_texts=[],
                    confidence_score=0.1,
                    annotation_completeness=0.0,
                    kb_versions=self._get_kb_versions()
                )
        
        # Step 1: Aggregate evidence from all knowledge bases with analysis type
        evidence_list = self.evidence_aggregator.aggregate_evidence(variant_annotation, cancer_type, analysis_type)
        
        # Step 2: Calculate Dynamic Somatic Confidence for tumor-only analysis
        dsc_scoring = None
        if analysis_type == AnalysisType.TUMOR_ONLY:
            tumor_purity = getattr(variant_annotation, 'tumor_purity', None)
            dsc_scoring = self.evidence_aggregator.calculate_dsc_score(variant_annotation, evidence_list, tumor_purity)
        
        # Step 3: Calculate VICC/CGC 2022 oncogenicity scoring (unchanged)
        try:
            vicc_scoring = self.evidence_aggregator.calculate_vicc_score(evidence_list)
            logger.info(f"VICC scoring result: {type(vicc_scoring)} - {vicc_scoring}")
        except Exception as e:
            logger.error(f"Error calculating VICC score: {e}")
            vicc_scoring = VICCScoring()
        
        # Step 4: Calculate OncoKB scoring (unchanged)
        try:
            oncokb_scoring = self.evidence_aggregator.calculate_oncokb_score(evidence_list, variant_annotation.oncokb_evidence)
            logger.info(f"OncoKB scoring result: {type(oncokb_scoring)} - {oncokb_scoring}")
        except Exception as e:
            logger.error(f"Error calculating OncoKB score: {e}")
            oncokb_scoring = OncoKBScoring()
        
        # Step 5: Calculate context-specific AMP tier assignments with DSC modulation
        try:
            amp_scoring = self._calculate_comprehensive_amp_scoring(evidence_list, cancer_type, variant_annotation, analysis_type, dsc_scoring)
            logger.info(f"AMP scoring result: {type(amp_scoring)} - {amp_scoring}")
        except Exception as e:
            logger.error(f"Error calculating AMP score: {e}")
            amp_scoring = AMPScoring(
                therapeutic_tier=None,
                diagnostic_tier=None,
                prognostic_tier=None,
                cancer_type_specific=False,
                related_cancer_types=[],
                overall_confidence=0.0,
                evidence_completeness=0.0
            )
        
        # Step 6: Apply DSC-based tier assignments for tumor-only (replaces old tier capping)
        if analysis_type == AnalysisType.TUMOR_ONLY and dsc_scoring:
            amp_scoring = self._apply_dsc_tier_logic(amp_scoring, dsc_scoring)
        
        # Step 7: Refine AMP tiers based on VICC oncogenicity
        amp_scoring = self._refine_amp_tiers_with_vicc(amp_scoring, vicc_scoring)
        
        # Step 7: Calculate confidence and completeness metrics
        confidence_score = self._calculate_confidence_score(evidence_list, amp_scoring, vicc_scoring, analysis_type)
        completeness_score = self._calculate_completeness_score(variant_annotation, evidence_list)
        
        # Step 8: Generate canned text
        canned_texts = []
        if self.config.enable_canned_text:
            canned_texts = self._generate_all_canned_texts(variant_annotation, evidence_list, amp_scoring, vicc_scoring, oncokb_scoring, cancer_type, analysis_type)
        
        # Step 9: Final safety check to ensure no scoring objects are None
        if amp_scoring is None:
            logger.error("AMP scoring is None, creating default")
            amp_scoring = AMPScoring(
                therapeutic_tier=None,
                diagnostic_tier=None,
                prognostic_tier=None,
                cancer_type_specific=False,
                related_cancer_types=[],
                overall_confidence=0.0,
                evidence_completeness=0.0
            )
        
        if vicc_scoring is None:
            logger.error("VICC scoring is None, creating default")
            vicc_scoring = VICCScoring()
        
        if oncokb_scoring is None:
            logger.error("OncoKB scoring is None, creating default")
            oncokb_scoring = OncoKBScoring()
        
        # Step 10: Create tier result
        logger.info(f"Creating TierResult with amp_scoring={type(amp_scoring)}, vicc_scoring={type(vicc_scoring)}, oncokb_scoring={type(oncokb_scoring)}")
        tier_result = TierResult(
            variant_id=f"{variant_annotation.chromosome}:{variant_annotation.position}:{variant_annotation.reference}>{variant_annotation.alternate}",
            gene_symbol=variant_annotation.gene_symbol,
            hgvs_p=variant_annotation.hgvs_p,
            analysis_type=analysis_type,
            dsc_scoring=dsc_scoring,
            amp_scoring=amp_scoring,
            vicc_scoring=vicc_scoring,
            oncokb_scoring=oncokb_scoring,
            evidence=evidence_list,
            cancer_type=cancer_type,
            canned_texts=canned_texts,
            confidence_score=confidence_score,
            annotation_completeness=completeness_score,
            kb_versions=self._get_kb_versions()
        )
        
        return tier_result
    
    def _calculate_comprehensive_amp_scoring(self, evidence_list: List[Evidence], cancer_type: str, 
                                           variant_annotation: VariantAnnotation, analysis_type: AnalysisType,
                                           dsc_scoring: Optional[DynamicSomaticConfidence] = None) -> AMPScoring:
        """Calculate comprehensive multi-context AMP scoring"""
        
        # Analyze evidence for cancer type specificity
        cancer_type_specific = self._is_evidence_cancer_type_specific(evidence_list, cancer_type)
        related_cancer_types = self._get_related_cancer_types(evidence_list)
        
        # Initialize context-specific tier assignments
        therapeutic_tier = None
        diagnostic_tier = None
        prognostic_tier = None
        
        # Evaluate each actionability context
        for context in [ActionabilityType.THERAPEUTIC, ActionabilityType.DIAGNOSTIC, ActionabilityType.PROGNOSTIC]:
            # Calculate evidence score for this context
            evidence_score = self._calculate_evidence_score(evidence_list, context)
            
            # Skip if no relevant evidence
            if evidence_score < 0.1:
                continue
            
            # Determine strongest evidence type for this context
            evidence_strength = self._determine_strongest_evidence(evidence_list, context)
            
            # Assign tier for this context
            context_tier = self._assign_context_tier(evidence_score, evidence_strength, context, cancer_type_specific)
            
            # Store context-specific assignment
            if context == ActionabilityType.THERAPEUTIC:
                therapeutic_tier = context_tier
            elif context == ActionabilityType.DIAGNOSTIC:
                diagnostic_tier = context_tier
            elif context == ActionabilityType.PROGNOSTIC:
                prognostic_tier = context_tier
        
        # Calculate overall confidence and completeness
        overall_confidence = self._calculate_overall_confidence([therapeutic_tier, diagnostic_tier, prognostic_tier])
        evidence_completeness = self._calculate_evidence_completeness(evidence_list)
        
        return AMPScoring(
            therapeutic_tier=therapeutic_tier,
            diagnostic_tier=diagnostic_tier,
            prognostic_tier=prognostic_tier,
            cancer_type_specific=cancer_type_specific,
            related_cancer_types=related_cancer_types,
            overall_confidence=overall_confidence,
            evidence_completeness=evidence_completeness
        )
    
    def _determine_strongest_evidence(self, evidence_list: List[Evidence], context: ActionabilityType) -> EvidenceStrength:
        """Determine the strongest evidence type for a given context using strategy pattern"""
        return self.scoring_manager.determine_strongest_evidence(evidence_list, context)
    
    def _apply_dsc_tier_logic(self, amp_scoring: AMPScoring, dsc_scoring: DynamicSomaticConfidence) -> AMPScoring:
        """
        Apply DSC-based tier logic per TN_VERSUS_TO.md specification
        
        Tier I requires DSC > 0.9, Tier II requires DSC > 0.6, etc.
        """
        dsc_score = dsc_scoring.dsc_score
        
        logger.info(f"Applying DSC-based tier logic with DSC score: {dsc_score:.3f}")
        
        # Apply DSC requirements to each context-specific tier
        for tier_assignment in [amp_scoring.therapeutic_tier, amp_scoring.diagnostic_tier, amp_scoring.prognostic_tier]:
            if tier_assignment is None:
                continue
            
            current_tier = tier_assignment.tier_level
            new_tier = current_tier
            
            # Apply DSC-based tier requirements per specification
            if current_tier in [AMPTierLevel.TIER_IA, AMPTierLevel.TIER_IB]:
                # Tier I requires DSC > 0.9
                if dsc_score <= 0.9:
                    new_tier = AMPTierLevel.TIER_IIC if dsc_score > 0.6 else AMPTierLevel.TIER_III
                    logger.info(f"DSC-adjusted {current_tier.value} to {new_tier.value} (DSC: {dsc_score:.3f})")
            
            elif current_tier in [AMPTierLevel.TIER_IIC, AMPTierLevel.TIER_IID, AMPTierLevel.TIER_IIE]:
                # Tier II can be assigned for DSC > 0.6
                if dsc_score <= 0.6:
                    new_tier = AMPTierLevel.TIER_III
                    logger.info(f"DSC-adjusted {current_tier.value} to {new_tier.value} (DSC: {dsc_score:.3f})")
            
            # Apply tier adjustment
            if new_tier != current_tier:
                tier_assignment.tier_level = new_tier
                
                # Adjust confidence based on DSC score
                tier_assignment.confidence_score = min(tier_assignment.confidence_score, dsc_score)
                
                # Update evidence summary
                tier_assignment.evidence_summary += f" (DSC-adjusted: {dsc_score:.3f})"
        
        # Update overall confidence based on DSC
        amp_scoring.overall_confidence = min(amp_scoring.overall_confidence, dsc_score + 0.1)
        
        return amp_scoring
    
    def _is_evidence_cancer_type_specific(self, evidence_list: List[Evidence], cancer_type: str) -> bool:
        """Check if evidence is specific to the given cancer type"""
        cancer_specific_evidence = [e for e in evidence_list 
                                  if cancer_type.lower() in e.description.lower() 
                                  or e.data.get("cancer_type_specific", False)]
        return len(cancer_specific_evidence) > 0
    
    def _get_related_cancer_types(self, evidence_list: List[Evidence]) -> List[str]:
        """Extract related cancer types from evidence"""
        cancer_types = set()
        for evidence in evidence_list:
            if "cancer_types" in evidence.data and isinstance(evidence.data["cancer_types"], list):
                cancer_types.update(evidence.data["cancer_types"])
        return list(cancer_types)
    
    def _calculate_overall_confidence(self, tier_assignments: List[Optional[ContextSpecificTierAssignment]]) -> float:
        """Calculate overall confidence across all context-specific tier assignments"""
        valid_assignments = [t for t in tier_assignments if t is not None]
        if not valid_assignments:
            return 0.0
        
        confidence_scores = [t.confidence_score for t in valid_assignments]
        return sum(confidence_scores) / len(confidence_scores)
    
    def _calculate_evidence_completeness(self, evidence_list: List[Evidence]) -> float:
        """Calculate evidence completeness across all contexts"""
        contexts = [ActionabilityType.THERAPEUTIC, ActionabilityType.DIAGNOSTIC, ActionabilityType.PROGNOSTIC]
        context_coverage = 0
        
        for context in contexts:
            relevant_evidence = [e for e in evidence_list if self._is_evidence_relevant_to_context(e, context)]
            if relevant_evidence:
                context_coverage += 1
        
        return context_coverage / len(contexts)
    
    def _refine_amp_tiers_with_vicc(self, amp_scoring: AMPScoring, vicc_scoring: VICCScoring) -> AMPScoring:
        """Refine multi-context AMP tier assignments using VICC oncogenicity assessment"""
        
        # If VICC suggests benign/likely benign, cap all context tiers at IV
        if vicc_scoring.classification in [VICCOncogenicity.BENIGN, VICCOncogenicity.LIKELY_BENIGN]:
            logger.info(f"Adjusting AMP tiers to IV based on VICC benign classification")
            
            # Downgrade each context-specific tier to IV
            if amp_scoring.therapeutic_tier and amp_scoring.therapeutic_tier.tier_level != AMPTierLevel.TIER_IV:
                amp_scoring.therapeutic_tier.tier_level = AMPTierLevel.TIER_IV
                amp_scoring.therapeutic_tier.confidence_score *= 0.8
            
            if amp_scoring.diagnostic_tier and amp_scoring.diagnostic_tier.tier_level != AMPTierLevel.TIER_IV:
                amp_scoring.diagnostic_tier.tier_level = AMPTierLevel.TIER_IV
                amp_scoring.diagnostic_tier.confidence_score *= 0.8
            
            if amp_scoring.prognostic_tier and amp_scoring.prognostic_tier.tier_level != AMPTierLevel.TIER_IV:
                amp_scoring.prognostic_tier.tier_level = AMPTierLevel.TIER_IV
                amp_scoring.prognostic_tier.confidence_score *= 0.8
        
        # If VICC suggests uncertain significance, limit to Tier III or IV
        elif vicc_scoring.classification == VICCOncogenicity.UNCERTAIN_SIGNIFICANCE:
            logger.info(f"Adjusting AMP tiers due to VICC uncertain significance")
            
            # Check each context tier and downgrade if needed
            for tier_assignment in [amp_scoring.therapeutic_tier, amp_scoring.diagnostic_tier, amp_scoring.prognostic_tier]:
                if tier_assignment and tier_assignment.tier_level in [AMPTierLevel.TIER_IA, AMPTierLevel.TIER_IB, AMPTierLevel.TIER_IIC, AMPTierLevel.TIER_IID]:
                    # Strong clinical significance becomes uncertain
                    if tier_assignment.fda_approved or tier_assignment.guideline_included:
                        tier_assignment.tier_level = AMPTierLevel.TIER_III
                    elif tier_assignment.tier_level in [AMPTierLevel.TIER_IIC, AMPTierLevel.TIER_IID]:
                        # Potential significance becomes investigational
                        tier_assignment.tier_level = AMPTierLevel.TIER_IIE
                    else:
                        tier_assignment.tier_level = AMPTierLevel.TIER_IV
                    tier_assignment.confidence_score *= 0.9
        
        # If VICC suggests oncogenic/likely oncogenic, enhance confidence
        elif vicc_scoring.classification in [VICCOncogenicity.ONCOGENIC, VICCOncogenicity.LIKELY_ONCOGENIC]:
            amp_scoring.overall_confidence = min(1.0, amp_scoring.overall_confidence * 1.1)
            
            # Boost confidence for each context tier
            for tier_assignment in [amp_scoring.therapeutic_tier, amp_scoring.diagnostic_tier, amp_scoring.prognostic_tier]:
                if tier_assignment:
                    tier_assignment.confidence_score = min(1.0, tier_assignment.confidence_score * 1.05)
        
        return amp_scoring
    
    def _calculate_confidence_score(self, evidence_list: List[Evidence], amp_scoring: AMPScoring, vicc_scoring: VICCScoring, analysis_type: AnalysisType) -> float:
        """Calculate overall confidence score for tier assignment"""
        
        # Base confidence from evidence strength
        evidence_confidence = 0.0
        if evidence_list:
            confidence_values = [e.confidence for e in evidence_list if e.confidence is not None]
            if confidence_values:
                evidence_confidence = sum(confidence_values) / len(confidence_values)
        
        # Weight by number of evidence items
        evidence_weight = min(1.0, len(evidence_list) / 5.0)  # Normalize to 5 evidence items
        
        # Consistency bonus for agreeing guidelines
        consistency_bonus = 0.0
        primary_tier = amp_scoring.get_primary_tier()
        if primary_tier in ["Tier IA", "Tier IB"] and vicc_scoring.classification in [VICCOncogenicity.ONCOGENIC, VICCOncogenicity.LIKELY_ONCOGENIC]:
            consistency_bonus = 0.1
        elif primary_tier == "Tier IV" and vicc_scoring.classification in [VICCOncogenicity.BENIGN, VICCOncogenicity.LIKELY_BENIGN]:
            consistency_bonus = 0.1
        
        # Apply tumor-only global confidence penalty
        to_penalty = 0.0
        if analysis_type == AnalysisType.TUMOR_ONLY:
            to_penalty = self.config.tumor_only_confidence_penalty  # Default: 0.2
        
        # Combine scores
        final_confidence = (evidence_confidence * 0.6 + 
                          evidence_weight * 0.3 + 
                          amp_scoring.overall_confidence * 0.1 + 
                          consistency_bonus - to_penalty)
        
        return max(0.1, min(1.0, final_confidence))
    
    def _calculate_completeness_score(self, variant_annotation: VariantAnnotation, evidence_list: List[Evidence]) -> float:
        """Calculate annotation completeness score"""
        
        completeness_factors = []
        
        # Population frequency data
        completeness_factors.append(1.0 if variant_annotation.population_frequencies else 0.0)
        
        # Functional predictions
        completeness_factors.append(1.0 if variant_annotation.functional_predictions else 0.0)
        
        # Clinical evidence
        completeness_factors.append(1.0 if (variant_annotation.civic_evidence or variant_annotation.oncokb_evidence) else 0.0)
        
        # Hotspot evidence
        completeness_factors.append(1.0 if variant_annotation.hotspot_evidence else 0.0)
        
        # Gene context
        completeness_factors.append(1.0 if (variant_annotation.is_oncogene or variant_annotation.is_tumor_suppressor) else 0.0)
        
        # Evidence diversity (different guidelines)
        guidelines_represented = set(e.guideline for e in evidence_list)
        completeness_factors.append(len(guidelines_represented) / 3.0)  # 3 main guidelines
        
        return sum(completeness_factors) / len(completeness_factors)
    
    def _generate_all_canned_texts(self, variant: VariantAnnotation, evidence_list: List[Evidence], 
                                 amp_scoring: AMPScoring, vicc_scoring: VICCScoring, 
                                 oncokb_scoring: OncoKBScoring, cancer_type: str, 
                                 analysis_type: AnalysisType) -> List[CannedText]:
        """Generate all applicable canned texts"""
        
        texts = []
        
        # Create temporary tier result for text generation
        temp_tier_result = TierResult(
            variant_id="temp",
            gene_symbol=variant.gene_symbol,
            hgvs_p=variant.hgvs_p,
            analysis_type=analysis_type,
            amp_scoring=amp_scoring,
            vicc_scoring=vicc_scoring,
            oncokb_scoring=oncokb_scoring,
            evidence=evidence_list,
            cancer_type=cancer_type,
            canned_texts=[],
            confidence_score=0.8,
            annotation_completeness=0.8
        )
        
        # Generate each type of text
        gene_info = self.text_generator.generate_gene_info_text(variant, evidence_list)
        if gene_info and gene_info.confidence >= self.config.text_confidence_threshold:
            texts.append(gene_info)
        
        variant_info = self.text_generator.generate_variant_info_text(variant, evidence_list)
        if variant_info and variant_info.confidence >= self.config.text_confidence_threshold:
            texts.append(variant_info)
        
        diagnostic = self.text_generator.generate_diagnostic_interpretation_text(temp_tier_result)
        if diagnostic and diagnostic.confidence >= self.config.text_confidence_threshold:
            texts.append(diagnostic)
        
        biomarker = self.text_generator.generate_biomarker_text(temp_tier_result)
        if biomarker and biomarker.confidence >= self.config.text_confidence_threshold:
            texts.append(biomarker)
        
        technical = self.text_generator.generate_technical_comments(temp_tier_result)
        if technical and technical.confidence >= self.config.text_confidence_threshold:
            texts.append(technical)
        
        # Generate mandatory tumor-only disclaimers
        if analysis_type == AnalysisType.TUMOR_ONLY and self.config.enable_tumor_only_disclaimers:
            disclaimers = self.text_generator.generate_tumor_only_disclaimers(temp_tier_result)
            if disclaimers:
                texts.append(disclaimers)
        
        return texts
    
    def _get_kb_versions(self) -> Dict[str, str]:
        """Get versions of knowledge bases used"""
        # This would be populated from actual KB metadata
        return {
            "OncoKB": "2024-01",
            "CIViC": "2024-01-01",
            "COSMIC": "v98",
            "gnomAD": "v4.0",
            "OncoVI": "1.0"
        }


# Factory function for easy usage
def assign_tier(variant_annotation: VariantAnnotation, cancer_type: str, 
               analysis_type: AnalysisType = AnalysisType.TUMOR_ONLY, 
               config: Optional[AnnotationConfig] = None) -> TierResult:
    """
    Convenience function for tier assignment
    
    Args:
        variant_annotation: VEP-annotated variant
        cancer_type: Cancer type context
        analysis_type: Analysis workflow type
        config: Optional configuration
        
    Returns:
        Complete tier assignment result
    """
    engine = TieringEngine(config)
    return engine.assign_tier(variant_annotation, cancer_type, analysis_type)


def process_vcf_to_tier_results(tumor_vcf_path: Path,
                               analysis_type: AnalysisType,
                               cancer_type: str,
                               normal_vcf_path: Optional[Path] = None,
                               config: Optional[AnnotationConfig] = None,
                               **kwargs) -> Tuple[List[TierResult], Dict[str, Any]]:
    """
    Complete pipeline: VCF → Filtering → Annotation → Tiering
    
    Args:
        tumor_vcf_path: Path to tumor VCF
        analysis_type: Analysis workflow type
        cancer_type: Cancer type context
        normal_vcf_path: Path to normal VCF (for TN analysis)
        config: Optional configuration
        **kwargs: Additional processing parameters
        
    Returns:
        Tuple of (tier_results, processing_summary)
    """
    from .variant_processor import create_variant_annotations_from_vcf
    
    # Step 1: Process VCF to variant annotations
    variant_annotations, processing_summary = create_variant_annotations_from_vcf(
        tumor_vcf_path=tumor_vcf_path,
        analysis_type=analysis_type,
        normal_vcf_path=normal_vcf_path,
        cancer_type=cancer_type,
        **kwargs
    )
    
    # Step 2: Apply tiering to each variant
    engine = TieringEngine(config)
    tier_results = []
    
    for variant_annotation in variant_annotations:
        try:
            tier_result = engine.assign_tier(variant_annotation, cancer_type, analysis_type)
            tier_results.append(tier_result)
        except Exception as e:
            logger.warning(f"Failed to tier variant {variant_annotation.chromosome}:{variant_annotation.position}: {e}")
            continue
    
    # Update processing summary
    processing_summary["tiering"] = {
        "total_tier_results": len(tier_results),
        "tier_distribution": _calculate_tier_distribution(tier_results)
    }
    
    return tier_results, processing_summary


def _calculate_tier_distribution(tier_results: List[TierResult]) -> Dict[str, int]:
    """Calculate distribution of tier assignments"""
    distribution = {}
    
    for tier_result in tier_results:
        primary_tier = tier_result.amp_scoring.get_primary_tier()
        distribution[primary_tier] = distribution.get(primary_tier, 0) + 1
    
    return distribution


# Global engine instance
_default_engine = None

def get_default_engine() -> TieringEngine:
    """Get default tiering engine instance"""
    global _default_engine
    if _default_engine is None:
        _default_engine = TieringEngine()
    return _default_engine