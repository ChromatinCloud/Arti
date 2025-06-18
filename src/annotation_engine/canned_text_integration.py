"""
Integration module to connect the comprehensive canned text generator
with the existing tiering system
"""

from typing import List, Dict, Any, Optional
import logging

from .models import (
    VariantAnnotation, Evidence, TierResult,
    CannedText, CannedTextType
)
from .canned_text_generator import CannedTextGenerator
from .interfaces import CannedTextGeneratorInterface

logger = logging.getLogger(__name__)


class ComprehensiveCannedTextGenerator(CannedTextGeneratorInterface):
    """
    Adapter class that implements the CannedTextGeneratorInterface
    using the new comprehensive canned text generation system
    """
    
    def __init__(self):
        self.generator = CannedTextGenerator()
        
    def generate_gene_info_text(self, 
                              variant: VariantAnnotation, 
                              evidence_list: List[Evidence]) -> Optional[CannedText]:
        """Generate general gene information text"""
        # Create minimal tier result for generator
        tier_result = self._create_minimal_tier_result(variant, evidence_list)
        
        # Generate all texts
        texts = self.generator.generate_all_canned_texts(
            variant=variant,
            evidence_list=evidence_list,
            tier_result=tier_result,
            cancer_type="cancer",  # Generic cancer type
            kb_data=self._extract_kb_data(evidence_list)
        )
        
        # Find and return gene info text
        for text in texts:
            if text.text_type == CannedTextType.GENERAL_GENE_INFO:
                return text
        return None
    
    def generate_variant_info_text(self,
                                 variant: VariantAnnotation,
                                 evidence_list: List[Evidence]) -> Optional[CannedText]:
        """Generate general variant information text"""
        tier_result = self._create_minimal_tier_result(variant, evidence_list)
        
        texts = self.generator.generate_all_canned_texts(
            variant=variant,
            evidence_list=evidence_list,
            tier_result=tier_result,
            cancer_type="cancer",
            kb_data=self._extract_kb_data(evidence_list)
        )
        
        for text in texts:
            if text.text_type == CannedTextType.GENERAL_VARIANT_INFO:
                return text
        return None
    
    def generate_diagnostic_interpretation_text(self,
                                              tier_result: TierResult) -> Optional[CannedText]:
        """Generate diagnostic interpretation text"""
        # Extract variant annotation from evidence
        variant = self._extract_variant_annotation(tier_result)
        if not variant:
            return None
            
        texts = self.generator.generate_all_canned_texts(
            variant=variant,
            evidence_list=tier_result.evidence,
            tier_result=tier_result,
            cancer_type=tier_result.cancer_type or "cancer",
            kb_data=self._extract_kb_data(tier_result.evidence)
        )
        
        # Return either gene dx or variant dx interpretation
        for text in texts:
            if text.text_type in [CannedTextType.GENE_DX_INTERPRETATION, 
                                CannedTextType.VARIANT_DX_INTERPRETATION]:
                return text
        return None
    
    def generate_biomarker_text(self,
                              tier_result: TierResult) -> Optional[CannedText]:
        """Generate biomarker interpretation text"""
        variant = self._extract_variant_annotation(tier_result)
        if not variant:
            return None
            
        # Check if we have biomarker data
        kb_data = self._extract_kb_data(tier_result.evidence)
        if not any(k in kb_data for k in ["tmb", "msi", "biomarkers"]):
            return None
            
        texts = self.generator.generate_all_canned_texts(
            variant=variant,
            evidence_list=tier_result.evidence,
            tier_result=tier_result,
            cancer_type=tier_result.cancer_type or "cancer",
            kb_data=kb_data
        )
        
        for text in texts:
            if text.text_type == CannedTextType.BIOMARKERS:
                return text
        return None
    
    def generate_technical_comments(self,
                                  tier_result: TierResult) -> Optional[CannedText]:
        """Generate technical quality comments"""
        # For now, return None as technical comments are institution-specific
        # This would be implemented based on QC flags in internal/
        return None
    
    def generate_tumor_only_disclaimers(self,
                                      tier_result: TierResult) -> Optional[CannedText]:
        """Generate tumor-only analysis disclaimers"""
        return CannedText(
            text_type=CannedTextType.TECHNICAL_COMMENTS,
            content=(
                "This analysis was performed on tumor tissue only, without a matched normal sample. "
                "Variants identified may include both somatic alterations and germline variants. "
                "Clinical correlation and additional testing may be warranted to distinguish "
                "somatic from germline events, particularly for variants in genes associated "
                "with hereditary cancer syndromes."
            ),
            confidence=1.0,
            evidence_support=["tumor_only_analysis"],
            triggered_by=["Analysis type: Tumor-only"]
        )
    
    def generate_all_texts(self,
                         variant: VariantAnnotation,
                         evidence_list: List[Evidence],
                         tier_result: TierResult,
                         cancer_type: str,
                         kb_data: Optional[Dict[str, Any]] = None) -> List[CannedText]:
        """
        Generate all applicable canned texts
        
        This is the main entry point for comprehensive text generation
        """
        return self.generator.generate_all_canned_texts(
            variant=variant,
            evidence_list=evidence_list,
            tier_result=tier_result,
            cancer_type=cancer_type,
            kb_data=kb_data or self._extract_kb_data(evidence_list)
        )
    
    # Helper methods
    
    def _create_minimal_tier_result(self,
                                  variant: VariantAnnotation,
                                  evidence_list: List[Evidence]) -> TierResult:
        """Create minimal tier result for generators that don't have full context"""
        from .models import AnalysisType
        
        return TierResult(
            variant_id="temp",
            gene_symbol=variant.gene_symbol,
            hgvs_p=variant.hgvs_p,
            analysis_type=AnalysisType.TUMOR_ONLY,
            amp_scoring=None,
            vicc_scoring=None,
            oncokb_scoring=None,
            evidence=evidence_list,
            cancer_type="cancer",
            canned_texts=[],
            confidence_score=0.5,
            annotation_completeness=0.5
        )
    
    def _extract_variant_annotation(self, tier_result: TierResult) -> Optional[VariantAnnotation]:
        """Extract variant annotation from tier result"""
        # Try to reconstruct from tier result
        variant = VariantAnnotation(
            gene_symbol=tier_result.gene_symbol,
            hgvs_p=tier_result.hgvs_p,
            chromosome="unknown",
            position=0,
            ref="N",
            alt="N"
        )
        
        # Try to get more info from evidence
        for evidence in tier_result.evidence:
            if evidence.metadata:
                if "chromosome" in evidence.metadata:
                    variant.chromosome = evidence.metadata["chromosome"]
                if "position" in evidence.metadata:
                    variant.position = evidence.metadata["position"]
                if "hgvs_c" in evidence.metadata:
                    variant.hgvs_c = evidence.metadata["hgvs_c"]
                if "consequence" in evidence.metadata:
                    variant.consequence = evidence.metadata["consequence"]
                    
        return variant
    
    def _extract_kb_data(self, evidence_list: List[Evidence]) -> Dict[str, Any]:
        """Extract knowledge base data from evidence"""
        kb_data = {}
        
        for evidence in evidence_list:
            if not evidence.metadata:
                continue
                
            # Extract biomarker data
            if "tmb" in evidence.metadata:
                kb_data["tmb"] = evidence.metadata["tmb"]
            elif "msi" in evidence.metadata:
                kb_data["msi"] = evidence.metadata["msi"]
            elif "biomarker" in evidence.metadata:
                if "biomarkers" not in kb_data:
                    kb_data["biomarkers"] = {}
                kb_data["biomarkers"][evidence.metadata["biomarker"]["name"]] = evidence.metadata["biomarker"]
                
            # Extract gene info
            if evidence.source_kb in ["NCBI_GENE", "UNIPROT", "HGNC"]:
                if "gene_info" not in kb_data:
                    kb_data["gene_info"] = {}
                kb_data["gene_info"].update(evidence.metadata)
                
            # Extract negative findings
            if "negative_findings" in evidence.metadata:
                kb_data["negative_findings"] = evidence.metadata["negative_findings"]
                
        return kb_data


# Example usage functions

def generate_comprehensive_report_text(tier_result: TierResult,
                                     variant: VariantAnnotation,
                                     cancer_type: str,
                                     kb_data: Optional[Dict[str, Any]] = None) -> Dict[CannedTextType, CannedText]:
    """
    Generate comprehensive report text for a variant
    
    Returns a dictionary mapping text types to generated texts
    """
    generator = ComprehensiveCannedTextGenerator()
    
    all_texts = generator.generate_all_texts(
        variant=variant,
        evidence_list=tier_result.evidence,
        tier_result=tier_result,
        cancer_type=cancer_type,
        kb_data=kb_data
    )
    
    # Organize by type
    texts_by_type = {}
    for text in all_texts:
        texts_by_type[text.text_type] = text
        
    return texts_by_type


def format_canned_texts_for_report(texts: List[CannedText]) -> str:
    """
    Format canned texts for inclusion in a clinical report
    
    Returns formatted text string
    """
    sections = []
    
    # Define section order
    section_order = [
        (CannedTextType.GENERAL_GENE_INFO, "Gene Information"),
        (CannedTextType.GENE_DX_INTERPRETATION, "Gene Clinical Significance"),
        (CannedTextType.GENERAL_VARIANT_INFO, "Variant Description"),
        (CannedTextType.VARIANT_DX_INTERPRETATION, "Variant Clinical Interpretation"),
        (CannedTextType.BIOMARKERS, "Biomarker Results"),
        (CannedTextType.INCIDENTAL_SECONDARY_FINDINGS, "Secondary Findings"),
        (CannedTextType.CHROMOSOMAL_ALTERATION_INTERPRETATION, "Structural Alterations"),
        (CannedTextType.PERTINENT_NEGATIVES, "Negative Results"),
        (CannedTextType.TECHNICAL_COMMENTS, "Technical Notes")
    ]
    
    # Group texts by type
    texts_by_type = {}
    for text in texts:
        texts_by_type[text.text_type] = text
        
    # Format sections
    for text_type, section_title in section_order:
        if text_type in texts_by_type:
            text = texts_by_type[text_type]
            section = f"### {section_title}\n{text.content}\n"
            if text.confidence < 0.8:
                section += f"*Confidence: {text.confidence:.1%}*\n"
            sections.append(section)
            
    return "\n".join(sections)