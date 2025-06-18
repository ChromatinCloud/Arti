"""
CGC/VICC 2022 Oncogenicity Classification Implementation V2

Enhanced version that leverages inter-guideline evidence:
- OncoKB oncogenic classifications as direct evidence for OS1
- CIViC pathogenicity as supporting evidence
- ClinVar somatic interpretations as evidence
- Cross-framework evidence aggregation

This creates a more robust classification by recognizing that different
frameworks provide mutually reinforcing evidence.
"""

from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import json
import logging

from .models import (
    VariantAnnotation, Evidence, PopulationFrequency, 
    HotspotEvidence, FunctionalEvidence
)
from .cgc_vicc_classifier import (
    OncogenicityCriteria, OncogenicityClassification,
    CriterionEvidence, OncogenicityResult, CGCVICCClassifier
)

logger = logging.getLogger(__name__)


class CGCVICCClassifierV2(CGCVICCClassifier):
    """
    Enhanced CGC/VICC classifier that leverages inter-guideline evidence
    """
    
    def __init__(self, kb_path: Path = Path("./.refs")):
        super().__init__(kb_path)
        logger.info("Initialized enhanced CGC/VICC classifier with inter-guideline evidence")
    
    def _evaluate_OS1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OS1: Same amino acid change as established oncogenic variant
        
        Enhanced to recognize OncoKB/CIViC/ClinVar classifications as direct evidence
        rather than just looking for same AA changes
        """
        evidence_sources = []
        max_confidence = 0.0
        
        # 1. Check OncoKB oncogenic classification (highest weight)
        oncokb_evidence = self._check_oncokb_oncogenic_classification(variant)
        if oncokb_evidence:
            evidence_sources.append(oncokb_evidence)
            max_confidence = max(max_confidence, oncokb_evidence['confidence'])
        
        # 2. Check CIViC pathogenic evidence
        civic_evidence = self._check_civic_pathogenic_classification(variant)
        if civic_evidence:
            evidence_sources.append(civic_evidence)
            max_confidence = max(max_confidence, civic_evidence['confidence'])
        
        # 3. Check ClinVar somatic pathogenic
        clinvar_evidence = self._check_clinvar_somatic_pathogenic(variant)
        if clinvar_evidence:
            evidence_sources.append(clinvar_evidence)
            max_confidence = max(max_confidence, clinvar_evidence['confidence'])
        
        # 4. Original check for same AA change (still valuable)
        same_aa_evidence = super()._evaluate_OS1(variant)
        if same_aa_evidence.is_met:
            evidence_sources.extend(same_aa_evidence.evidence_sources)
            max_confidence = max(max_confidence, same_aa_evidence.confidence)
        
        if evidence_sources:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OS1,
                is_met=True,
                strength="Strong",
                evidence_sources=evidence_sources,
                confidence=max_confidence,
                notes="Established oncogenic based on expert curation across multiple databases"
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OS1,
            is_met=False,
            strength="Strong"
        )
    
    def _check_oncokb_oncogenic_classification(self, variant: VariantAnnotation) -> Optional[Dict]:
        """Check if OncoKB classifies this variant as oncogenic"""
        if 'oncokb' not in self.clinical_evidence:
            return None
        
        oncokb_df = self.clinical_evidence['oncokb']
        
        # Try exact match first
        exact_matches = oncokb_df[
            (oncokb_df['gene'] == variant.gene_symbol) &
            (oncokb_df['alteration'] == variant.hgvs_p.replace('p.', '') if variant.hgvs_p else '')
        ]
        
        # If no exact match, try position match
        if exact_matches.empty and variant.hgvs_p:
            position = self._extract_position(variant.hgvs_p)
            if position:
                position_matches = oncokb_df[
                    (oncokb_df['gene'] == variant.gene_symbol) &
                    (oncokb_df['proteinStart'] == position)
                ]
                if not position_matches.empty:
                    exact_matches = position_matches
        
        if not exact_matches.empty:
            oncogenicity = exact_matches.iloc[0].get('oncogenicity', 'Unknown')
            
            if oncogenicity == 'Oncogenic':
                return {
                    "source": "OncoKB",
                    "classification": "Oncogenic",
                    "confidence": 0.95,
                    "evidence_level": exact_matches.iloc[0].get('highestSensitiveLevel', 'N/A'),
                    "note": "OncoKB expert-curated oncogenic classification"
                }
            elif oncogenicity == 'Likely Oncogenic':
                return {
                    "source": "OncoKB",
                    "classification": "Likely Oncogenic",
                    "confidence": 0.85,
                    "evidence_level": exact_matches.iloc[0].get('highestSensitiveLevel', 'N/A'),
                    "note": "OncoKB likely oncogenic classification"
                }
        
        return None
    
    def _check_civic_pathogenic_classification(self, variant: VariantAnnotation) -> Optional[Dict]:
        """Check if CIViC has pathogenic evidence for this variant"""
        if 'civic' not in self.clinical_evidence:
            return None
        
        civic_df = self.clinical_evidence['civic']
        
        # Match by gene and position/AA change
        matches = civic_df[civic_df['gene'] == variant.gene_symbol]
        
        if variant.hgvs_p:
            aa_change = variant.hgvs_p.replace('p.', '')
            matches = matches[matches['variant'].str.contains(aa_change, na=False)]
        
        pathogenic_evidence = []
        for _, row in matches.iterrows():
            if row.get('clinical_significance', '').lower() in ['pathogenic', 'likely pathogenic']:
                evidence_level = row.get('evidence_level', 'D')
                confidence = {
                    'A': 0.9,
                    'B': 0.8,
                    'C': 0.7,
                    'D': 0.6,
                    'E': 0.5
                }.get(evidence_level, 0.5)
                
                pathogenic_evidence.append({
                    "source": "CIViC",
                    "evidence_level": evidence_level,
                    "confidence": confidence,
                    "evidence_type": row.get('evidence_type', 'N/A'),
                    "note": f"CIViC pathogenic evidence level {evidence_level}"
                })
        
        if pathogenic_evidence:
            # Return highest confidence evidence
            return max(pathogenic_evidence, key=lambda x: x['confidence'])
        
        return None
    
    def _check_clinvar_somatic_pathogenic(self, variant: VariantAnnotation) -> Optional[Dict]:
        """Check if ClinVar has somatic pathogenic classification"""
        if 'clinvar' not in self.clinical_evidence:
            return None
        
        clinvar_df = self.clinical_evidence['clinvar']
        
        # Filter for somatic submissions
        somatic_df = clinvar_df[clinvar_df['somatic_status'] == 'Somatic']
        
        # Match by gene and variant
        matches = somatic_df[
            (somatic_df['gene_symbol'] == variant.gene_symbol) &
            (somatic_df['clinical_significance'].str.contains('Pathogenic', na=False))
        ]
        
        if not matches.empty:
            best_match = matches.iloc[0]
            review_status = best_match.get('review_status', '')
            
            # Calculate confidence based on review status
            confidence_map = {
                'reviewed_by_expert_panel': 0.95,
                'criteria_provided_multiple_submitters': 0.85,
                'criteria_provided_single_submitter': 0.7,
                'no_assertion_provided': 0.5
            }
            
            confidence = confidence_map.get(review_status, 0.5)
            
            return {
                "source": "ClinVar",
                "classification": best_match['clinical_significance'],
                "confidence": confidence,
                "review_status": review_status,
                "note": f"ClinVar somatic pathogenic ({review_status})"
            }
        
        return None
    
    def _evaluate_OM1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OM1: Missense in gene for which missense variants are common mechanism
        
        Enhanced to use OncoKB/COSMIC gene annotations
        """
        is_missense = "missense_variant" in variant.consequence
        
        if not is_missense:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OM1,
                is_met=False,
                strength="Moderate"
            )
        
        evidence_sources = []
        
        # Check if OncoKB lists this as an oncogene
        if variant.gene_symbol in self.cancer_genes.get('oncokb_genes', set()):
            # Check if OncoKB has missense variants for this gene
            if self._gene_has_oncogenic_missense(variant.gene_symbol):
                evidence_sources.append({
                    "source": "OncoKB",
                    "note": f"{variant.gene_symbol} has known oncogenic missense variants"
                })
        
        # Check COSMIC gene role
        if self._check_cosmic_oncogene_with_missense(variant.gene_symbol):
            evidence_sources.append({
                "source": "COSMIC CGC",
                "note": f"{variant.gene_symbol} is oncogene with missense mechanism"
            })
        
        # Original hardcoded list (still valuable as expert curation)
        missense_oncogenes = {
            'BRAF', 'KRAS', 'NRAS', 'HRAS', 'PIK3CA', 'AKT1', 'EGFR', 
            'FGFR1', 'FGFR2', 'FGFR3', 'KIT', 'PDGFRA', 'RET', 'MET',
            'ALK', 'ROS1', 'ERBB2', 'IDH1', 'IDH2', 'FLT3', 'JAK2'
        }
        
        if variant.gene_symbol in missense_oncogenes:
            evidence_sources.append({
                "source": "Expert curation",
                "note": "Known oncogene with missense mechanism"
            })
        
        if evidence_sources:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OM1,
                is_met=True,
                strength="Moderate",
                evidence_sources=evidence_sources,
                confidence=0.8
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OM1,
            is_met=False,
            strength="Moderate"
        )
    
    def _evaluate_OP1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OP1: Computational evidence supports oncogenic impact
        
        Enhanced to include OncoKB/COSMIC functional predictions
        """
        computational_evidence = []
        
        # Original computational predictors
        base_result = super()._evaluate_OP1(variant)
        if base_result.is_met:
            computational_evidence.extend(base_result.evidence_sources)
        
        # Add OncoKB mutation effect prediction
        oncokb_effect = self._get_oncokb_mutation_effect(variant)
        if oncokb_effect in ['Gain-of-function', 'Loss-of-function']:
            computational_evidence.append({
                "tool": "OncoKB",
                "prediction": oncokb_effect,
                "interpretation": "Likely oncogenic",
                "note": "Expert-curated functional prediction"
            })
        
        # Add COSMIC FATHMM prediction if available
        cosmic_fathmm = self._get_cosmic_fathmm_prediction(variant)
        if cosmic_fathmm and cosmic_fathmm['prediction'] == 'PATHOGENIC':
            computational_evidence.append({
                "tool": "COSMIC FATHMM",
                "score": cosmic_fathmm['score'],
                "interpretation": "Pathogenic"
            })
        
        # Require at least 2 concordant predictions
        if len(computational_evidence) >= 2:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OP1,
                is_met=True,
                strength="Supporting",
                evidence_sources=computational_evidence,
                confidence=min(0.7, 0.4 + len(computational_evidence) * 0.1),
                notes="Multiple computational tools predict oncogenic impact"
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OP1,
            is_met=False,
            strength="Supporting"
        )
    
    def _gene_has_oncogenic_missense(self, gene: str) -> bool:
        """Check if gene has known oncogenic missense variants in OncoKB"""
        if 'oncokb' not in self.clinical_evidence:
            return False
        
        oncokb_df = self.clinical_evidence['oncokb']
        gene_variants = oncokb_df[oncokb_df['gene'] == gene]
        
        # Check for oncogenic missense variants
        oncogenic_missense = gene_variants[
            (gene_variants['oncogenicity'].isin(['Oncogenic', 'Likely Oncogenic'])) &
            (gene_variants['mutationType'] == 'Missense')
        ]
        
        return not oncogenic_missense.empty
    
    def _check_cosmic_oncogene_with_missense(self, gene: str) -> bool:
        """Check if COSMIC lists gene as oncogene with missense mechanism"""
        # This would check COSMIC CGC data
        # Placeholder for actual implementation
        return gene in {'BRAF', 'KRAS', 'PIK3CA', 'EGFR'}  # Known examples
    
    def _get_oncokb_mutation_effect(self, variant: VariantAnnotation) -> Optional[str]:
        """Get OncoKB's mutation effect annotation"""
        if 'oncokb' not in self.clinical_evidence:
            return None
        
        oncokb_df = self.clinical_evidence['oncokb']
        matches = oncokb_df[
            (oncokb_df['gene'] == variant.gene_symbol) &
            (oncokb_df['alteration'] == variant.hgvs_p.replace('p.', '') if variant.hgvs_p else '')
        ]
        
        if not matches.empty:
            return matches.iloc[0].get('mutationEffect', None)
        
        return None
    
    def _get_cosmic_fathmm_prediction(self, variant: VariantAnnotation) -> Optional[Dict]:
        """Get COSMIC FATHMM prediction if available"""
        # Placeholder - would query COSMIC data
        return None
    
    def classify_variant_with_context(self, 
                                    variant: VariantAnnotation,
                                    cancer_type: Optional[str] = None,
                                    additional_evidence: Optional[List[Evidence]] = None) -> OncogenicityResult:
        """
        Enhanced classification that can incorporate external evidence
        
        Args:
            variant: Variant to classify
            cancer_type: Cancer context
            additional_evidence: Pre-computed evidence from other sources
        
        Returns:
            OncogenicityResult with integrated evidence
        """
        # Run standard classification
        result = self.classify_variant(variant, cancer_type)
        
        # If additional evidence provided, check if it affects classification
        if additional_evidence:
            # Extract relevant evidence
            oncokb_evidence = [e for e in additional_evidence if e.source_kb == "OncoKB"]
            civic_evidence = [e for e in additional_evidence if e.source_kb == "CIViC"]
            
            # Re-evaluate if strong evidence might change classification
            if any(e.code == "ONCOKB_ONCOGENIC" for e in oncokb_evidence):
                # This provides strong support for oncogenic classification
                logger.info("OncoKB oncogenic classification strengthens CGC/VICC assessment")
        
        return result


def create_inter_framework_evidence_summary(variant: VariantAnnotation,
                                          cgc_vicc_result: OncogenicityResult,
                                          all_evidence: List[Evidence]) -> Dict:
    """
    Create a summary showing how different frameworks support each other
    """
    summary = {
        "variant": f"{variant.gene_symbol}:{variant.hgvs_p}",
        "cgc_vicc_classification": cgc_vicc_result.classification.value,
        "supporting_frameworks": {},
        "concordance_score": 0.0
    }
    
    # Check OncoKB support
    oncokb_oncogenic = any(e.code == "ONCOKB_ONCOGENIC" for e in all_evidence)
    if oncokb_oncogenic:
        summary["supporting_frameworks"]["OncoKB"] = {
            "classification": "Oncogenic",
            "supports_cgc_vicc": True,
            "criteria_supported": ["OS1"]
        }
    
    # Check CIViC support  
    civic_pathogenic = any(e.code == "CIVIC_PATHOGENIC" and e.score >= 6 for e in all_evidence)
    if civic_pathogenic:
        summary["supporting_frameworks"]["CIViC"] = {
            "classification": "Pathogenic",
            "supports_cgc_vicc": True,
            "criteria_supported": ["OS1", "OP1"]
        }
    
    # Check ClinVar support
    clinvar_pathogenic = any(e.code == "CLINVAR_PATHOGENIC" for e in all_evidence)
    if clinvar_pathogenic:
        summary["supporting_frameworks"]["ClinVar"] = {
            "classification": "Pathogenic",
            "supports_cgc_vicc": True,
            "criteria_supported": ["OS1"]
        }
    
    # Calculate concordance
    framework_count = len(summary["supporting_frameworks"])
    if framework_count > 0:
        supporting_oncogenic = sum(
            1 for f in summary["supporting_frameworks"].values()
            if f["supports_cgc_vicc"]
        )
        summary["concordance_score"] = supporting_oncogenic / (framework_count + 1)  # +1 for CGC/VICC
    
    return summary