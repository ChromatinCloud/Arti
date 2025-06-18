"""
Comprehensive Canned Text Generation System

Implements all 8 types of clinical interpretation text:
1. General Gene Info - boilerplate overview of the gene
2. Gene Dx Interpretation - gene-level meaning for patient's specific diagnosis
3. General Variant Info - technical description of the variant itself
4. Variant Dx Interpretation - variant-specific clinical meaning for diagnosis
5. Incidental/Secondary Findings - ACMG-SF-style reportables unrelated to primary dx
6. Chromosomal Alteration Interpretation - CNVs/fusions/large SVs
7. Pertinent Negatives - explicit "no clinically significant variants found in..." statements
8. Biomarkers - TMB, MSI, expression; we bucket values vs. thresholds
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging
import re

from .models import (
    CannedText, CannedTextType, Evidence, VariantAnnotation,
    TierResult, AMPScoring, VICCScoring, OncoKBScoring
)
from .ga4gh.clinical_context import ClinicalContextExtractor, ClinicalContext

logger = logging.getLogger(__name__)


@dataclass
class TextTemplate:
    """Template for generating canned text"""
    template: str
    required_fields: List[str]
    optional_fields: List[str] = None
    confidence_factors: Dict[str, float] = None
    
    def __post_init__(self):
        if self.optional_fields is None:
            self.optional_fields = []
        if self.confidence_factors is None:
            self.confidence_factors = {}


class CannedTextGenerator:
    """
    Comprehensive canned text generator implementing all 8 types
    with template system and GA4GH clinical context integration
    """
    
    def __init__(self):
        self.clinical_context_extractor = ClinicalContextExtractor()
        self.templates = self._initialize_templates()
        
    def _initialize_templates(self) -> Dict[CannedTextType, List[TextTemplate]]:
        """Initialize text templates for each type"""
        return {
            CannedTextType.GENERAL_GENE_INFO: [
                TextTemplate(
                    template=(
                        "{gene_symbol} ({gene_name}) encodes {protein_function}. "
                        "This gene is located on chromosome {chromosome} and has been "
                        "associated with {associated_conditions}. {domain_info}"
                    ),
                    required_fields=["gene_symbol", "gene_name", "chromosome"],
                    optional_fields=["protein_function", "associated_conditions", "domain_info"],
                    confidence_factors={"protein_function": 0.2, "domain_info": 0.1}
                ),
                TextTemplate(
                    template=(
                        "{gene_symbol} is classified as {gene_role} and plays a critical "
                        "role in {pathway}. {cancer_relevance}"
                    ),
                    required_fields=["gene_symbol", "gene_role"],
                    optional_fields=["pathway", "cancer_relevance"],
                    confidence_factors={"pathway": 0.15, "cancer_relevance": 0.25}
                )
            ],
            
            CannedTextType.GENE_DX_INTERPRETATION: [
                TextTemplate(
                    template=(
                        "In the context of {cancer_type}, {gene_symbol} functions as {gene_role_in_cancer}. "
                        "{therapeutic_relevance} {prognostic_significance}"
                    ),
                    required_fields=["cancer_type", "gene_symbol", "gene_role_in_cancer"],
                    optional_fields=["therapeutic_relevance", "prognostic_significance"],
                    confidence_factors={"therapeutic_relevance": 0.3, "prognostic_significance": 0.2}
                ),
                TextTemplate(
                    template=(
                        "Alterations in {gene_symbol} are {frequency} in {cancer_type} and "
                        "are associated with {clinical_outcome}. {actionability}"
                    ),
                    required_fields=["gene_symbol", "cancer_type"],
                    optional_fields=["frequency", "clinical_outcome", "actionability"],
                    confidence_factors={"frequency": 0.1, "clinical_outcome": 0.2, "actionability": 0.3}
                )
            ],
            
            CannedTextType.GENERAL_VARIANT_INFO: [
                TextTemplate(
                    template=(
                        "The variant {variant_notation} results in {molecular_consequence} "
                        "at position {position}. This variant has a population frequency of "
                        "{pop_frequency} and {computational_prediction}."
                    ),
                    required_fields=["variant_notation", "molecular_consequence"],
                    optional_fields=["position", "pop_frequency", "computational_prediction"],
                    confidence_factors={"pop_frequency": 0.15, "computational_prediction": 0.2}
                ),
                TextTemplate(
                    template=(
                        "{variant_notation} is a {variant_type} that affects {affected_domain}. "
                        "{conservation_info} {hotspot_info}"
                    ),
                    required_fields=["variant_notation", "variant_type"],
                    optional_fields=["affected_domain", "conservation_info", "hotspot_info"],
                    confidence_factors={"affected_domain": 0.2, "hotspot_info": 0.25}
                )
            ],
            
            CannedTextType.VARIANT_DX_INTERPRETATION: [
                TextTemplate(
                    template=(
                        "This {gene_symbol} {variant_notation} variant is classified as {clinical_significance} "
                        "for {cancer_type} based on {evidence_basis}. {therapeutic_implications} "
                        "{resistance_info}"
                    ),
                    required_fields=["gene_symbol", "variant_notation", "clinical_significance", "cancer_type"],
                    optional_fields=["evidence_basis", "therapeutic_implications", "resistance_info"],
                    confidence_factors={"evidence_basis": 0.2, "therapeutic_implications": 0.3}
                ),
                TextTemplate(
                    template=(
                        "In {cancer_type}, this variant {actionability_statement}. "
                        "{clinical_trials_info} {prognosis_info}"
                    ),
                    required_fields=["cancer_type", "actionability_statement"],
                    optional_fields=["clinical_trials_info", "prognosis_info"],
                    confidence_factors={"clinical_trials_info": 0.2, "prognosis_info": 0.15}
                )
            ],
            
            CannedTextType.INCIDENTAL_SECONDARY_FINDINGS: [
                TextTemplate(
                    template=(
                        "The {gene_symbol} {variant_notation} variant is classified as {germline_classification} "
                        "and is associated with {hereditary_condition}. This finding is unrelated to the "
                        "patient's {primary_indication} but may have implications for {clinical_management}."
                    ),
                    required_fields=["gene_symbol", "variant_notation", "germline_classification", "hereditary_condition"],
                    optional_fields=["primary_indication", "clinical_management"],
                    confidence_factors={"clinical_management": 0.3}
                ),
                TextTemplate(
                    template=(
                        "ACMG Secondary Finding: {gene_symbol} is an actionable gene associated with "
                        "{condition_category}. {penetrance_info} {screening_recommendations}"
                    ),
                    required_fields=["gene_symbol", "condition_category"],
                    optional_fields=["penetrance_info", "screening_recommendations"],
                    confidence_factors={"penetrance_info": 0.2, "screening_recommendations": 0.25}
                )
            ],
            
            CannedTextType.CHROMOSOMAL_ALTERATION_INTERPRETATION: [
                TextTemplate(
                    template=(
                        "The {alteration_type} involving {genes_affected} spans {size} and "
                        "{functional_impact}. {known_syndrome} {clinical_relevance}"
                    ),
                    required_fields=["alteration_type", "genes_affected"],
                    optional_fields=["size", "functional_impact", "known_syndrome", "clinical_relevance"],
                    confidence_factors={"functional_impact": 0.2, "clinical_relevance": 0.3}
                ),
                TextTemplate(
                    template=(
                        "This {alteration_type} results in {gene_dosage_effect} of {key_genes}. "
                        "{therapeutic_vulnerability} {prognostic_impact}"
                    ),
                    required_fields=["alteration_type", "gene_dosage_effect"],
                    optional_fields=["key_genes", "therapeutic_vulnerability", "prognostic_impact"],
                    confidence_factors={"therapeutic_vulnerability": 0.25, "prognostic_impact": 0.2}
                )
            ],
            
            CannedTextType.PERTINENT_NEGATIVES: [
                TextTemplate(
                    template=(
                        "No clinically significant variants were identified in the following "
                        "{gene_category}: {gene_list}. This includes genes associated with "
                        "{clinical_context} in {cancer_type}."
                    ),
                    required_fields=["gene_category", "gene_list", "cancer_type"],
                    optional_fields=["clinical_context"],
                    confidence_factors={"clinical_context": 0.15}
                ),
                TextTemplate(
                    template=(
                        "Analysis of {pathway_name} pathway genes ({gene_count} genes) revealed "
                        "no actionable alterations. {coverage_statement}"
                    ),
                    required_fields=["pathway_name", "gene_count"],
                    optional_fields=["coverage_statement"],
                    confidence_factors={"coverage_statement": 0.2}
                )
            ],
            
            CannedTextType.BIOMARKERS: [
                TextTemplate(
                    template=(
                        "Tumor Mutational Burden (TMB): {tmb_value} mutations/Mb ({tmb_category}). "
                        "This is {tmb_interpretation} the threshold for {therapy_indication}. "
                        "{clinical_context}"
                    ),
                    required_fields=["tmb_value", "tmb_category"],
                    optional_fields=["tmb_interpretation", "therapy_indication", "clinical_context"],
                    confidence_factors={"therapy_indication": 0.3, "clinical_context": 0.2}
                ),
                TextTemplate(
                    template=(
                        "Microsatellite Status: {msi_status}. {msi_interpretation} "
                        "{immunotherapy_implications}"
                    ),
                    required_fields=["msi_status"],
                    optional_fields=["msi_interpretation", "immunotherapy_implications"],
                    confidence_factors={"immunotherapy_implications": 0.35}
                ),
                TextTemplate(
                    template=(
                        "{biomarker_name}: {biomarker_value} ({biomarker_category}). "
                        "{clinical_interpretation} {therapy_associations}"
                    ),
                    required_fields=["biomarker_name", "biomarker_value", "biomarker_category"],
                    optional_fields=["clinical_interpretation", "therapy_associations"],
                    confidence_factors={"clinical_interpretation": 0.25, "therapy_associations": 0.3}
                )
            ]
        }
    
    def generate_all_canned_texts(self,
                                variant: VariantAnnotation,
                                evidence_list: List[Evidence],
                                tier_result: TierResult,
                                cancer_type: str,
                                kb_data: Optional[Dict[str, Any]] = None) -> List[CannedText]:
        """
        Generate all applicable canned texts for a variant
        
        Args:
            variant: Variant annotation with gene and variant info
            evidence_list: All evidence supporting the variant
            tier_result: Tier assignment results
            cancer_type: Cancer type context
            kb_data: Additional knowledge base data
            
        Returns:
            List of generated canned texts
        """
        texts = []
        
        # Extract clinical contexts from evidence
        clinical_contexts = self._extract_clinical_contexts(evidence_list, variant, cancer_type)
        
        # Generate each type of text
        generators = [
            (CannedTextType.GENERAL_GENE_INFO, self._generate_general_gene_info),
            (CannedTextType.GENE_DX_INTERPRETATION, self._generate_gene_dx_interpretation),
            (CannedTextType.GENERAL_VARIANT_INFO, self._generate_general_variant_info),
            (CannedTextType.VARIANT_DX_INTERPRETATION, self._generate_variant_dx_interpretation),
            (CannedTextType.INCIDENTAL_SECONDARY_FINDINGS, self._generate_incidental_findings),
            (CannedTextType.CHROMOSOMAL_ALTERATION_INTERPRETATION, self._generate_chromosomal_interpretation),
            (CannedTextType.PERTINENT_NEGATIVES, self._generate_pertinent_negatives),
            (CannedTextType.BIOMARKERS, self._generate_biomarker_text)
        ]
        
        for text_type, generator in generators:
            try:
                generated_text = generator(
                    variant, evidence_list, tier_result, 
                    cancer_type, clinical_contexts, kb_data
                )
                if generated_text and generated_text.confidence > 0.5:
                    texts.append(generated_text)
            except Exception as e:
                logger.warning(f"Failed to generate {text_type}: {e}")
                
        return texts
    
    def _extract_clinical_contexts(self,
                                 evidence_list: List[Evidence],
                                 variant: VariantAnnotation,
                                 cancer_type: str) -> List[ClinicalContext]:
        """Extract clinical contexts from all evidence"""
        contexts = []
        for evidence in evidence_list:
            try:
                context = self.clinical_context_extractor.extract_clinical_context(
                    evidence, variant, cancer_type
                )
                contexts.append(context)
            except Exception as e:
                logger.debug(f"Could not extract context from evidence: {e}")
        return contexts
    
    def _generate_general_gene_info(self,
                                  variant: VariantAnnotation,
                                  evidence_list: List[Evidence],
                                  tier_result: TierResult,
                                  cancer_type: str,
                                  clinical_contexts: List[ClinicalContext],
                                  kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate General Gene Info text (Type 1)"""
        
        # Collect data from evidence and KB
        data = self._collect_gene_info_data(variant, evidence_list, kb_data)
        
        # Select best template
        template = self._select_best_template(
            CannedTextType.GENERAL_GENE_INFO,
            data
        )
        
        if not template:
            return None
            
        # Fill template
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        # Extract supporting evidence
        evidence_codes = self._extract_evidence_codes(evidence_list, ["gene_function", "gene_role"])
        
        return CannedText(
            text_type=CannedTextType.GENERAL_GENE_INFO,
            content=text,
            confidence=confidence,
            evidence_support=evidence_codes,
            triggered_by=[f"Gene: {variant.gene_symbol}"]
        )
    
    def _generate_gene_dx_interpretation(self,
                                       variant: VariantAnnotation,
                                       evidence_list: List[Evidence],
                                       tier_result: TierResult,
                                       cancer_type: str,
                                       clinical_contexts: List[ClinicalContext],
                                       kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate Gene Dx Interpretation text (Type 2)"""
        
        # Collect diagnosis-specific gene data
        data = self._collect_gene_dx_data(variant, evidence_list, cancer_type, kb_data)
        
        # Select template based on available data
        template = self._select_best_template(
            CannedTextType.GENE_DX_INTERPRETATION,
            data
        )
        
        if not template:
            return None
            
        # Fill template
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        # Boost confidence if we have cancer-specific evidence
        if any(ctx.primary_condition == cancer_type for ctx in clinical_contexts):
            confidence *= 1.2
            
        evidence_codes = self._extract_evidence_codes(
            evidence_list, 
            ["cancer_gene", "therapeutic", "prognostic"]
        )
        
        return CannedText(
            text_type=CannedTextType.GENE_DX_INTERPRETATION,
            content=text,
            confidence=min(confidence, 1.0),
            evidence_support=evidence_codes,
            triggered_by=[f"Gene: {variant.gene_symbol}", f"Cancer: {cancer_type}"]
        )
    
    def _generate_general_variant_info(self,
                                     variant: VariantAnnotation,
                                     evidence_list: List[Evidence],
                                     tier_result: TierResult,
                                     cancer_type: str,
                                     clinical_contexts: List[ClinicalContext],
                                     kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate General Variant Info text (Type 3)"""
        
        # Collect variant-specific data
        data = self._collect_variant_info_data(variant, evidence_list, kb_data)
        
        template = self._select_best_template(
            CannedTextType.GENERAL_VARIANT_INFO,
            data
        )
        
        if not template:
            return None
            
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        evidence_codes = self._extract_evidence_codes(
            evidence_list,
            ["variant_effect", "population_frequency", "computational"]
        )
        
        return CannedText(
            text_type=CannedTextType.GENERAL_VARIANT_INFO,
            content=text,
            confidence=confidence,
            evidence_support=evidence_codes,
            triggered_by=[f"Variant: {variant.hgvs_c or variant.hgvs_p or 'Unknown'}"]
        )
    
    def _generate_variant_dx_interpretation(self,
                                          variant: VariantAnnotation,
                                          evidence_list: List[Evidence],
                                          tier_result: TierResult,
                                          cancer_type: str,
                                          clinical_contexts: List[ClinicalContext],
                                          kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate Variant Dx Interpretation text (Type 4)"""
        
        # Collect clinical interpretation data
        data = self._collect_variant_dx_data(
            variant, evidence_list, tier_result, cancer_type, clinical_contexts, kb_data
        )
        
        template = self._select_best_template(
            CannedTextType.VARIANT_DX_INTERPRETATION,
            data
        )
        
        if not template:
            return None
            
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        # Adjust confidence based on tier
        tier_confidence_boost = {
            "IA": 1.5, "IB": 1.4, "IIC": 1.2, "IID": 1.1, "III": 1.0, "IV": 0.8
        }
        if tier_result.amp_scoring:
            confidence *= tier_confidence_boost.get(tier_result.amp_scoring.tier, 1.0)
            
        evidence_codes = self._extract_evidence_codes(
            evidence_list,
            ["therapeutic", "diagnostic", "prognostic", "clinical_significance"]
        )
        
        return CannedText(
            text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
            content=text,
            confidence=min(confidence, 1.0),
            evidence_support=evidence_codes,
            triggered_by=[
                f"Variant: {variant.hgvs_p or variant.hgvs_c}",
                f"Tier: {tier_result.amp_scoring.tier if tier_result.amp_scoring else 'Unknown'}"
            ]
        )
    
    def _generate_incidental_findings(self,
                                    variant: VariantAnnotation,
                                    evidence_list: List[Evidence],
                                    tier_result: TierResult,
                                    cancer_type: str,
                                    clinical_contexts: List[ClinicalContext],
                                    kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate Incidental/Secondary Findings text (Type 5)"""
        
        # Check if this is an ACMG secondary finding
        if not self._is_acmg_secondary_finding(variant, evidence_list, kb_data):
            return None
            
        data = self._collect_incidental_findings_data(variant, evidence_list, cancer_type, kb_data)
        
        template = self._select_best_template(
            CannedTextType.INCIDENTAL_SECONDARY_FINDINGS,
            data
        )
        
        if not template:
            return None
            
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        evidence_codes = self._extract_evidence_codes(
            evidence_list,
            ["germline_pathogenic", "hereditary", "acmg_sf"]
        )
        
        return CannedText(
            text_type=CannedTextType.INCIDENTAL_SECONDARY_FINDINGS,
            content=text,
            confidence=confidence,
            evidence_support=evidence_codes,
            triggered_by=["ACMG Secondary Finding", f"Gene: {variant.gene_symbol}"]
        )
    
    def _generate_chromosomal_interpretation(self,
                                           variant: VariantAnnotation,
                                           evidence_list: List[Evidence],
                                           tier_result: TierResult,
                                           cancer_type: str,
                                           clinical_contexts: List[ClinicalContext],
                                           kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate Chromosomal Alteration Interpretation text (Type 6)"""
        
        # Check if this is a chromosomal alteration
        if not self._is_chromosomal_alteration(variant):
            return None
            
        data = self._collect_chromosomal_data(variant, evidence_list, kb_data)
        
        template = self._select_best_template(
            CannedTextType.CHROMOSOMAL_ALTERATION_INTERPRETATION,
            data
        )
        
        if not template:
            return None
            
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        evidence_codes = self._extract_evidence_codes(
            evidence_list,
            ["structural_variant", "copy_number", "fusion"]
        )
        
        return CannedText(
            text_type=CannedTextType.CHROMOSOMAL_ALTERATION_INTERPRETATION,
            content=text,
            confidence=confidence,
            evidence_support=evidence_codes,
            triggered_by=[f"Alteration: {variant.variant_type}", f"Genes: {variant.gene_symbol}"]
        )
    
    def _generate_pertinent_negatives(self,
                                    variant: VariantAnnotation,
                                    evidence_list: List[Evidence],
                                    tier_result: TierResult,
                                    cancer_type: str,
                                    clinical_contexts: List[ClinicalContext],
                                    kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate Pertinent Negatives text (Type 7)"""
        
        # This is typically generated at the report level, not variant level
        # For now, return None unless we have specific negative findings data
        
        if not kb_data or "negative_findings" not in kb_data:
            return None
            
        data = self._collect_pertinent_negatives_data(cancer_type, kb_data)
        
        template = self._select_best_template(
            CannedTextType.PERTINENT_NEGATIVES,
            data
        )
        
        if not template:
            return None
            
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        return CannedText(
            text_type=CannedTextType.PERTINENT_NEGATIVES,
            content=text,
            confidence=confidence,
            evidence_support=["coverage_analysis", "gene_panel"],
            triggered_by=[f"Cancer type: {cancer_type}", "Negative findings"]
        )
    
    def _generate_biomarker_text(self,
                                variant: VariantAnnotation,
                                evidence_list: List[Evidence],
                                tier_result: TierResult,
                                cancer_type: str,
                                clinical_contexts: List[ClinicalContext],
                                kb_data: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate Biomarkers text (Type 8)"""
        
        # Check for biomarker data
        if not kb_data or not any(k in kb_data for k in ["tmb", "msi", "expression", "biomarkers"]):
            return None
            
        data = self._collect_biomarker_data(cancer_type, kb_data)
        
        # Select appropriate biomarker template
        if "tmb" in data:
            templates = [t for t in self.templates[CannedTextType.BIOMARKERS] if "TMB" in t.template]
        elif "msi_status" in data:
            templates = [t for t in self.templates[CannedTextType.BIOMARKERS] if "Microsatellite" in t.template]
        else:
            templates = [t for t in self.templates[CannedTextType.BIOMARKERS] if "biomarker_name" in t.required_fields]
            
        if not templates:
            return None
            
        template = templates[0]  # Use first matching template
        
        text, confidence = self._fill_template(template, data)
        
        if not text:
            return None
            
        evidence_codes = ["biomarker_assessment", f"{list(data.keys())[0]}_analysis"]
        
        return CannedText(
            text_type=CannedTextType.BIOMARKERS,
            content=text,
            confidence=confidence,
            evidence_support=evidence_codes,
            triggered_by=[f"Biomarker: {list(data.keys())[0]}", f"Cancer: {cancer_type}"]
        )
    
    # Helper methods
    
    def _select_best_template(self,
                            text_type: CannedTextType,
                            data: Dict[str, Any]) -> Optional[TextTemplate]:
        """Select the best template based on available data"""
        templates = self.templates.get(text_type, [])
        
        best_template = None
        best_score = 0
        
        for template in templates:
            # Check if all required fields are available
            if not all(field in data for field in template.required_fields):
                continue
                
            # Calculate score based on available optional fields
            score = len(template.required_fields)  # Base score
            for field in template.optional_fields:
                if field in data:
                    score += template.confidence_factors.get(field, 0.1)
                    
            if score > best_score:
                best_score = score
                best_template = template
                
        return best_template
    
    def _fill_template(self,
                     template: TextTemplate,
                     data: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """Fill template with data and calculate confidence"""
        try:
            # Start with base confidence
            confidence = 0.6
            
            # Prepare fill data
            fill_data = {}
            
            # Add required fields
            for field in template.required_fields:
                if field not in data:
                    return None, 0.0
                fill_data[field] = data[field]
                
            # Add optional fields
            for field in template.optional_fields:
                if field in data:
                    fill_data[field] = data[field]
                    confidence += template.confidence_factors.get(field, 0.1)
                else:
                    fill_data[field] = ""  # Empty string for missing optional fields
                    
            # Fill template
            text = template.template.format(**fill_data)
            
            # Clean up text (remove double spaces, empty sentences)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\.\s*\.', '.', text)
            text = text.strip()
            
            return text, min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Template filling error: {e}")
            return None, 0.0
    
    def _collect_gene_info_data(self,
                              variant: VariantAnnotation,
                              evidence_list: List[Evidence],
                              kb_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect data for general gene info"""
        data = {
            "gene_symbol": variant.gene_symbol,
            "chromosome": variant.chromosome
        }
        
        # Extract from evidence
        for evidence in evidence_list:
            if evidence.source_kb == "NCBI_GENE" and "gene_name" in evidence.metadata:
                data["gene_name"] = evidence.metadata["gene_name"]
            if evidence.source_kb == "UNIPROT" and "protein_function" in evidence.metadata:
                data["protein_function"] = evidence.metadata["protein_function"]
            if evidence.source_kb == "COSMIC_CGC" and "gene_role" in evidence.metadata:
                data["gene_role"] = evidence.metadata["gene_role"]
                
        # Extract from KB data
        if kb_data:
            if "gene_info" in kb_data:
                data.update(kb_data["gene_info"])
            if "pfam_domains" in kb_data:
                data["domain_info"] = f"Contains {len(kb_data['pfam_domains'])} functional domains"
                
        # Set defaults
        data.setdefault("gene_name", data["gene_symbol"])
        data.setdefault("associated_conditions", "various cancers")
        
        return data
    
    def _collect_gene_dx_data(self,
                            variant: VariantAnnotation,
                            evidence_list: List[Evidence],
                            cancer_type: str,
                            kb_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect diagnosis-specific gene data"""
        data = {
            "gene_symbol": variant.gene_symbol,
            "cancer_type": cancer_type
        }
        
        # Determine gene role in this cancer
        gene_roles = []
        therapeutic_relevance = []
        
        for evidence in evidence_list:
            if evidence.metadata:
                if "gene_role" in evidence.metadata:
                    gene_roles.append(evidence.metadata["gene_role"])
                if evidence.evidence_type == "THERAPEUTIC":
                    therapeutic_relevance.append(evidence.description)
                    
        if gene_roles:
            # Pick most specific role
            if "oncogene" in " ".join(gene_roles).lower():
                data["gene_role_in_cancer"] = "an oncogene"
            elif "tumor suppressor" in " ".join(gene_roles).lower():
                data["gene_role_in_cancer"] = "a tumor suppressor"
            else:
                data["gene_role_in_cancer"] = "a cancer-associated gene"
        else:
            data["gene_role_in_cancer"] = "a gene of interest"
            
        if therapeutic_relevance:
            data["therapeutic_relevance"] = f"Alterations may predict response to targeted therapies."
            
        # Add frequency data if available
        if kb_data and "cancer_frequency" in kb_data:
            freq = kb_data["cancer_frequency"].get(cancer_type, 0)
            if freq > 0.1:
                data["frequency"] = "commonly altered"
            elif freq > 0.01:
                data["frequency"] = "occasionally altered"
            else:
                data["frequency"] = "rarely altered"
                
        return data
    
    def _collect_variant_info_data(self,
                                 variant: VariantAnnotation,
                                 evidence_list: List[Evidence],
                                 kb_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect variant-specific technical data"""
        data = {
            "variant_notation": variant.hgvs_p or variant.hgvs_c or f"{variant.chromosome}:{variant.position}",
            "molecular_consequence": variant.consequence or "unknown consequence"
        }
        
        # Add variant type
        if variant.variant_type:
            data["variant_type"] = variant.variant_type
        elif "missense" in data["molecular_consequence"]:
            data["variant_type"] = "missense mutation"
        elif "frameshift" in data["molecular_consequence"]:
            data["variant_type"] = "frameshift mutation"
        else:
            data["variant_type"] = "variant"
            
        # Extract computational predictions
        predictions = []
        for evidence in evidence_list:
            if evidence.source_kb in ["ALPHAMISSENSE", "SIFT", "POLYPHEN"]:
                predictions.append(f"{evidence.source_kb}: {evidence.description}")
                
        if predictions:
            data["computational_prediction"] = f"is predicted to be {predictions[0]}"
            
        # Add population frequency
        for evidence in evidence_list:
            if evidence.source_kb == "GNOMAD" and evidence.metadata:
                if "af" in evidence.metadata:
                    af = evidence.metadata["af"]
                    if af < 0.0001:
                        data["pop_frequency"] = "absent from population databases"
                    else:
                        data["pop_frequency"] = f"{af:.2%} in gnomAD"
                        
        # Hotspot info
        for evidence in evidence_list:
            if "hotspot" in evidence.evidence_type.lower():
                data["hotspot_info"] = "This position is a known mutational hotspot."
                break
                
        return data
    
    def _collect_variant_dx_data(self,
                               variant: VariantAnnotation,
                               evidence_list: List[Evidence],
                               tier_result: TierResult,
                               cancer_type: str,
                               clinical_contexts: List[ClinicalContext],
                               kb_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect clinical interpretation data for variant"""
        data = {
            "gene_symbol": variant.gene_symbol,
            "variant_notation": variant.hgvs_p or variant.hgvs_c or "variant",
            "cancer_type": cancer_type
        }
        
        # Determine clinical significance
        if tier_result.oncokb_scoring and tier_result.oncokb_scoring.oncogenic_classification:
            data["clinical_significance"] = tier_result.oncokb_scoring.oncogenic_classification
        elif tier_result.vicc_scoring and tier_result.vicc_scoring.oncogenicity_classification:
            data["clinical_significance"] = tier_result.vicc_scoring.oncogenicity_classification
        else:
            data["clinical_significance"] = "of uncertain significance"
            
        # Extract therapeutic implications
        therapeutic_evidence = [e for e in evidence_list if e.evidence_type == "THERAPEUTIC"]
        if therapeutic_evidence:
            therapies = []
            for evidence in therapeutic_evidence:
                if evidence.metadata and "therapy" in evidence.metadata:
                    therapies.append(evidence.metadata["therapy"])
                    
            if therapies:
                data["therapeutic_implications"] = f"This variant may predict response to {', '.join(therapies)}."
                
        # Actionability statement
        if tier_result.amp_scoring:
            tier = tier_result.amp_scoring.tier
            if tier in ["IA", "IB"]:
                data["actionability_statement"] = "has strong clinical significance with FDA-approved or guideline-recommended therapies available"
            elif tier in ["IIC", "IID"]:
                data["actionability_statement"] = "has potential clinical significance with investigational options"
            else:
                data["actionability_statement"] = "is under investigation for clinical relevance"
                
        # Evidence basis
        evidence_sources = list(set(e.source_kb for e in evidence_list))
        if evidence_sources:
            data["evidence_basis"] = f"evidence from {', '.join(evidence_sources[:3])}"
            
        return data
    
    def _collect_incidental_findings_data(self,
                                        variant: VariantAnnotation,
                                        evidence_list: List[Evidence],
                                        cancer_type: str,
                                        kb_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect data for incidental findings"""
        data = {
            "gene_symbol": variant.gene_symbol,
            "variant_notation": variant.hgvs_p or variant.hgvs_c or "variant",
            "primary_indication": cancer_type
        }
        
        # Get germline classification
        for evidence in evidence_list:
            if evidence.source_kb == "CLINVAR" and "germline" in str(evidence.metadata).lower():
                if evidence.metadata and "classification" in evidence.metadata:
                    data["germline_classification"] = evidence.metadata["classification"]
                    
        data.setdefault("germline_classification", "pathogenic")
        
        # Determine associated condition
        acmg_conditions = {
            "BRCA1": "Hereditary Breast and Ovarian Cancer syndrome",
            "BRCA2": "Hereditary Breast and Ovarian Cancer syndrome",
            "MLH1": "Lynch syndrome",
            "MSH2": "Lynch syndrome",
            "TP53": "Li-Fraumeni syndrome",
            "APC": "Familial Adenomatous Polyposis"
        }
        
        data["hereditary_condition"] = acmg_conditions.get(
            variant.gene_symbol,
            "hereditary cancer predisposition"
        )
        
        data["condition_category"] = "hereditary cancer syndromes"
        data["clinical_management"] = "genetic counseling and cascade testing"
        
        return data
    
    def _collect_chromosomal_data(self,
                                variant: VariantAnnotation,
                                evidence_list: List[Evidence],
                                kb_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect data for chromosomal alterations"""
        data = {
            "genes_affected": variant.gene_symbol
        }
        
        # Determine alteration type
        if variant.variant_type:
            if "deletion" in variant.variant_type.lower():
                data["alteration_type"] = "deletion"
                data["gene_dosage_effect"] = "loss"
            elif "duplication" in variant.variant_type.lower():
                data["alteration_type"] = "duplication"
                data["gene_dosage_effect"] = "gain"
            elif "fusion" in variant.variant_type.lower():
                data["alteration_type"] = "fusion"
                data["gene_dosage_effect"] = "fusion product"
            else:
                data["alteration_type"] = "structural variant"
                data["gene_dosage_effect"] = "alteration"
                
        # Extract size if available
        if variant.metadata and "size" in variant.metadata:
            size_kb = variant.metadata["size"] / 1000
            data["size"] = f"{size_kb:.1f} kb"
            
        # Functional impact
        for evidence in evidence_list:
            if "haploinsufficient" in str(evidence.description).lower():
                data["functional_impact"] = "results in haploinsufficiency"
            elif "oncogenic fusion" in str(evidence.description).lower():
                data["functional_impact"] = "creates an oncogenic fusion protein"
                
        return data
    
    def _collect_pertinent_negatives_data(self,
                                        cancer_type: str,
                                        kb_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data for pertinent negatives"""
        data = {
            "cancer_type": cancer_type
        }
        
        if "negative_findings" in kb_data:
            negatives = kb_data["negative_findings"]
            
            if "genes_tested" in negatives:
                data["gene_list"] = ", ".join(negatives["genes_tested"][:5])
                data["gene_count"] = len(negatives["genes_tested"])
                
            if "gene_category" in negatives:
                data["gene_category"] = negatives["gene_category"]
            else:
                data["gene_category"] = "targetable driver genes"
                
            if "pathway" in negatives:
                data["pathway_name"] = negatives["pathway"]
                
        data.setdefault("gene_list", "commonly altered genes")
        data.setdefault("clinical_context", "targeted therapy selection")
        
        return data
    
    def _collect_biomarker_data(self,
                              cancer_type: str,
                              kb_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect biomarker data"""
        data = {}
        
        if "tmb" in kb_data:
            tmb_value = kb_data["tmb"]["value"]
            data["tmb_value"] = f"{tmb_value:.1f}"
            
            # Categorize TMB
            if tmb_value >= 20:
                data["tmb_category"] = "High"
                data["tmb_interpretation"] = "above"
                data["therapy_indication"] = "immune checkpoint inhibitor therapy"
            elif tmb_value >= 10:
                data["tmb_category"] = "Intermediate"
                data["tmb_interpretation"] = "near"
                data["therapy_indication"] = "consideration of immunotherapy"
            else:
                data["tmb_category"] = "Low"
                data["tmb_interpretation"] = "below"
                
        elif "msi" in kb_data:
            msi_status = kb_data["msi"]["status"]
            data["msi_status"] = msi_status
            
            if msi_status == "MSI-H":
                data["msi_interpretation"] = "High microsatellite instability detected."
                data["immunotherapy_implications"] = "This finding suggests potential benefit from immune checkpoint inhibitors."
            else:
                data["msi_interpretation"] = "Microsatellite stable."
                
        elif "biomarkers" in kb_data:
            # Generic biomarker
            biomarker = list(kb_data["biomarkers"].values())[0]
            data["biomarker_name"] = biomarker.get("name", "Biomarker")
            data["biomarker_value"] = str(biomarker.get("value", ""))
            data["biomarker_category"] = biomarker.get("category", "")
            
        return data
    
    def _extract_evidence_codes(self,
                              evidence_list: List[Evidence],
                              relevant_types: List[str]) -> List[str]:
        """Extract evidence codes matching relevant types"""
        codes = []
        
        for evidence in evidence_list:
            evidence_type_lower = evidence.evidence_type.lower() if evidence.evidence_type else ""
            if any(rtype in evidence_type_lower for rtype in relevant_types):
                code = f"{evidence.source_kb}:{evidence.evidence_code or evidence.evidence_type}"
                codes.append(code)
                
        return list(set(codes))  # Remove duplicates
    
    def _is_acmg_secondary_finding(self,
                                  variant: VariantAnnotation,
                                  evidence_list: List[Evidence],
                                  kb_data: Optional[Dict[str, Any]]) -> bool:
        """Check if variant is an ACMG secondary finding"""
        
        # ACMG SF v3.0 genes (simplified list)
        acmg_genes = {
            "BRCA1", "BRCA2", "MLH1", "MSH2", "MSH6", "PMS2",
            "APC", "MUTYH", "VHL", "MEN1", "RET", "PTEN",
            "TP53", "STK11", "CDH1", "BMPR1A", "SMAD4",
            "PALB2", "RAD51C", "RAD51D", "ATM", "CHEK2"
        }
        
        if variant.gene_symbol not in acmg_genes:
            return False
            
        # Check for pathogenic germline evidence
        for evidence in evidence_list:
            if evidence.source_kb == "CLINVAR":
                if evidence.metadata and evidence.metadata.get("review_status") == "germline":
                    if "pathogenic" in str(evidence.metadata.get("classification", "")).lower():
                        return True
                        
        return False
    
    def _is_chromosomal_alteration(self, variant: VariantAnnotation) -> bool:
        """Check if variant is a chromosomal alteration"""
        if variant.variant_type:
            structural_types = ["deletion", "duplication", "fusion", "translocation", "inversion"]
            return any(sv_type in variant.variant_type.lower() for sv_type in structural_types)
        return False