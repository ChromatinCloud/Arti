"""
Enhanced Pertinent Negatives Generation for Comprehensive Reporting

This module extends the canned text generator to handle diverse types of
pertinent negatives beyond just gene mutations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .models import CannedText, CannedTextType
from .canned_text_generator import TextTemplate


class NegativeFindingType(str, Enum):
    """Types of negative findings"""
    GENE_MUTATION = "gene_mutation"
    CHROMOSOMAL_ALTERATION = "chromosomal_alteration"
    METHYLATION = "methylation"
    AMPLIFICATION = "amplification"
    FUSION = "fusion"
    EXPRESSION = "expression"
    PROTEIN = "protein"
    PATHWAY = "pathway"
    SIGNATURE = "signature"
    VARIANT_SPECIFIC = "variant_specific"


@dataclass
class NegativeFinding:
    """Represents a negative finding"""
    finding_type: NegativeFindingType
    target: str  # What was tested (gene, chromosome, promoter, etc.)
    description: str
    clinical_relevance: str
    method: Optional[str] = None
    coverage_quality: Optional[str] = None


class EnhancedPertinentNegativesGenerator:
    """
    Generates comprehensive pertinent negatives text covering:
    - Gene mutations
    - Chromosomal alterations
    - Methylation status
    - Amplifications/deletions
    - Fusion events
    - Expression levels
    - Protein markers
    - Pathway alterations
    - Mutational signatures
    """
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.cancer_specific_negatives = self._initialize_cancer_specific_negatives()
    
    def _initialize_templates(self) -> Dict[NegativeFindingType, List[TextTemplate]]:
        """Initialize templates for different types of negative findings"""
        return {
            NegativeFindingType.GENE_MUTATION: [
                TextTemplate(
                    template=(
                        "No pathogenic mutations were identified in {gene_list}. "
                        "{clinical_context} {coverage_info}"
                    ),
                    required_fields=["gene_list"],
                    optional_fields=["clinical_context", "coverage_info"]
                )
            ],
            
            NegativeFindingType.CHROMOSOMAL_ALTERATION: [
                TextTemplate(
                    template=(
                        "Chromosomal analysis revealed no evidence of {alteration_type}. "
                        "{clinical_significance} {method_note}"
                    ),
                    required_fields=["alteration_type"],
                    optional_fields=["clinical_significance", "method_note"]
                ),
                TextTemplate(
                    template=(
                        "The characteristic {alteration_pattern} was not detected. "
                        "{diagnostic_implication}"
                    ),
                    required_fields=["alteration_pattern"],
                    optional_fields=["diagnostic_implication"]
                )
            ],
            
            NegativeFindingType.METHYLATION: [
                TextTemplate(
                    template=(
                        "{target} methylation was not detected. "
                        "{therapeutic_implication} {prognostic_note}"
                    ),
                    required_fields=["target"],
                    optional_fields=["therapeutic_implication", "prognostic_note"]
                ),
                TextTemplate(
                    template=(
                        "Analysis of {target} promoter methylation status: unmethylated. "
                        "{clinical_impact}"
                    ),
                    required_fields=["target"],
                    optional_fields=["clinical_impact"]
                )
            ],
            
            NegativeFindingType.AMPLIFICATION: [
                TextTemplate(
                    template=(
                        "No amplification of {gene} was detected (copy number: {copy_number}). "
                        "{therapeutic_relevance}"
                    ),
                    required_fields=["gene"],
                    optional_fields=["copy_number", "therapeutic_relevance"]
                )
            ],
            
            NegativeFindingType.FUSION: [
                TextTemplate(
                    template=(
                        "No {fusion_type} fusions were identified. "
                        "{genes_tested} {clinical_relevance}"
                    ),
                    required_fields=["fusion_type"],
                    optional_fields=["genes_tested", "clinical_relevance"]
                )
            ],
            
            NegativeFindingType.VARIANT_SPECIFIC: [
                TextTemplate(
                    template=(
                        "The {specific_variant} was not detected. "
                        "{frequency_note} {clinical_implication}"
                    ),
                    required_fields=["specific_variant"],
                    optional_fields=["frequency_note", "clinical_implication"]
                )
            ],
            
            NegativeFindingType.EXPRESSION: [
                TextTemplate(
                    template=(
                        "{marker} expression: {level}. "
                        "{interpretation} {therapy_implication}"
                    ),
                    required_fields=["marker", "level"],
                    optional_fields=["interpretation", "therapy_implication"]
                )
            ],
            
            NegativeFindingType.PATHWAY: [
                TextTemplate(
                    template=(
                        "No alterations were identified in {pathway} pathway genes "
                        "({gene_count} genes analyzed). {therapeutic_note}"
                    ),
                    required_fields=["pathway", "gene_count"],
                    optional_fields=["therapeutic_note"]
                )
            ],
            
            NegativeFindingType.SIGNATURE: [
                TextTemplate(
                    template=(
                        "{signature_type} signature: {status}. "
                        "{interpretation} {clinical_relevance}"
                    ),
                    required_fields=["signature_type", "status"],
                    optional_fields=["interpretation", "clinical_relevance"]
                )
            ]
        }
    
    def _initialize_cancer_specific_negatives(self) -> Dict[str, List[NegativeFinding]]:
        """Define cancer-specific important negative findings"""
        return {
            "glioblastoma": [
                NegativeFinding(
                    finding_type=NegativeFindingType.CHROMOSOMAL_ALTERATION,
                    target="chr7_gain_chr10_loss",
                    description="+7/-10 signature",
                    clinical_relevance="This characteristic GBM chromosomal pattern helps distinguish primary from secondary GBM"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.METHYLATION,
                    target="MGMT",
                    description="MGMT promoter methylation",
                    clinical_relevance="MGMT methylation status is prognostic and predictive of response to alkylating agents"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.METHYLATION,
                    target="TERT",
                    description="TERT promoter methylation",
                    clinical_relevance="TERT promoter mutations are associated with poor prognosis in IDH-wildtype gliomas"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.VARIANT_SPECIFIC,
                    target="EGFRvIII",
                    description="EGFR variant III",
                    clinical_relevance="EGFRvIII is a tumor-specific variant that may be targetable"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.AMPLIFICATION,
                    target="EGFR",
                    description="EGFR amplification",
                    clinical_relevance="EGFR amplification is common in primary GBM"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.GENE_MUTATION,
                    target="IDH1/2",
                    description="IDH1/2 mutations",
                    clinical_relevance="IDH mutation status is the key molecular classifier for adult diffuse gliomas"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.FUSION,
                    target="FGFR-TACC",
                    description="FGFR-TACC fusions",
                    clinical_relevance="These fusions may be targeted with FGFR inhibitors"
                )
            ],
            
            "colorectal": [
                NegativeFinding(
                    finding_type=NegativeFindingType.GENE_MUTATION,
                    target="KRAS/NRAS/BRAF",
                    description="RAS/RAF mutations",
                    clinical_relevance="RAS/RAF wild-type status is required for anti-EGFR therapy eligibility"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.METHYLATION,
                    target="MLH1",
                    description="MLH1 promoter methylation",
                    clinical_relevance="MLH1 methylation indicates sporadic MSI-H rather than Lynch syndrome"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.AMPLIFICATION,
                    target="HER2",
                    description="HER2 amplification",
                    clinical_relevance="HER2 amplification may indicate eligibility for HER2-targeted therapy"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.SIGNATURE,
                    target="CMS",
                    description="Consensus Molecular Subtype",
                    clinical_relevance="CMS classification has prognostic and potential predictive value"
                )
            ],
            
            "breast cancer": [
                NegativeFinding(
                    finding_type=NegativeFindingType.AMPLIFICATION,
                    target="HER2",
                    description="HER2 amplification",
                    clinical_relevance="HER2 status determines eligibility for HER2-targeted therapies"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.EXPRESSION,
                    target="ER/PR",
                    description="Estrogen/Progesterone receptor expression",
                    clinical_relevance="Hormone receptor status guides endocrine therapy decisions"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.GENE_MUTATION,
                    target="PIK3CA",
                    description="PIK3CA mutations",
                    clinical_relevance="PIK3CA mutations may indicate benefit from PI3K inhibitors"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.SIGNATURE,
                    target="HRD",
                    description="Homologous Recombination Deficiency",
                    clinical_relevance="HRD status may predict PARP inhibitor sensitivity"
                )
            ],
            
            "lung adenocarcinoma": [
                NegativeFinding(
                    finding_type=NegativeFindingType.GENE_MUTATION,
                    target="EGFR/ALK/ROS1/BRAF/MET/RET/KRAS",
                    description="Targetable driver mutations",
                    clinical_relevance="These alterations have FDA-approved targeted therapies"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.FUSION,
                    target="ALK/ROS1/RET/NTRK",
                    description="Targetable fusion events",
                    clinical_relevance="Gene fusions may be targeted with specific TKIs"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.AMPLIFICATION,
                    target="MET",
                    description="MET amplification",
                    clinical_relevance="High-level MET amplification may respond to MET inhibitors"
                ),
                NegativeFinding(
                    finding_type=NegativeFindingType.EXPRESSION,
                    target="PD-L1",
                    description="PD-L1 expression",
                    clinical_relevance="PD-L1 expression level guides immunotherapy decisions"
                )
            ]
        }
    
    def generate_pertinent_negatives(self,
                                   cancer_type: str,
                                   negative_findings_data: Dict[str, Any],
                                   additional_context: Optional[Dict[str, Any]] = None) -> List[CannedText]:
        """
        Generate pertinent negatives text based on cancer type and findings
        
        Args:
            cancer_type: The cancer type (e.g., "glioblastoma", "colorectal")
            negative_findings_data: Dictionary containing negative results
            additional_context: Additional clinical context
            
        Returns:
            List of CannedText objects for pertinent negatives
        """
        texts = []
        
        # Get cancer-specific negatives
        cancer_negatives = self.cancer_specific_negatives.get(
            cancer_type.lower(), 
            []
        )
        
        # Process each type of negative finding
        for negative in cancer_negatives:
            if self._is_finding_tested(negative, negative_findings_data):
                text = self._generate_negative_text(
                    negative, 
                    negative_findings_data,
                    additional_context
                )
                if text:
                    texts.append(text)
        
        # Add any additional negative findings from data
        if "additional_negatives" in negative_findings_data:
            for finding in negative_findings_data["additional_negatives"]:
                text = self._generate_custom_negative_text(finding)
                if text:
                    texts.append(text)
        
        # Combine related findings into comprehensive text
        combined_text = self._combine_negative_texts(texts, cancer_type)
        
        return [combined_text] if combined_text else texts
    
    def _is_finding_tested(self, 
                         negative: NegativeFinding,
                         findings_data: Dict[str, Any]) -> bool:
        """Check if a specific negative finding was tested"""
        # Check various data structures for evidence of testing
        if negative.finding_type == NegativeFindingType.GENE_MUTATION:
            return negative.target in findings_data.get("genes_tested", [])
        elif negative.finding_type == NegativeFindingType.CHROMOSOMAL_ALTERATION:
            return "chromosomal_analysis" in findings_data
        elif negative.finding_type == NegativeFindingType.METHYLATION:
            return negative.target in findings_data.get("methylation_tested", [])
        elif negative.finding_type == NegativeFindingType.AMPLIFICATION:
            return negative.target in findings_data.get("copy_number_tested", [])
        elif negative.finding_type == NegativeFindingType.FUSION:
            return "fusion_analysis" in findings_data
        elif negative.finding_type == NegativeFindingType.VARIANT_SPECIFIC:
            return negative.target in findings_data.get("specific_variants_tested", [])
        elif negative.finding_type == NegativeFindingType.EXPRESSION:
            return negative.target in findings_data.get("expression_markers", {})
        elif negative.finding_type == NegativeFindingType.SIGNATURE:
            return negative.target in findings_data.get("signatures_analyzed", [])
        
        return False
    
    def _generate_negative_text(self,
                              negative: NegativeFinding,
                              findings_data: Dict[str, Any],
                              additional_context: Optional[Dict[str, Any]]) -> Optional[CannedText]:
        """Generate text for a specific negative finding"""
        templates = self.templates.get(negative.finding_type, [])
        if not templates:
            return None
        
        # Prepare data for template
        template_data = self._prepare_template_data(
            negative, 
            findings_data,
            additional_context
        )
        
        # Select best template
        best_template = None
        for template in templates:
            if all(field in template_data for field in template.required_fields):
                best_template = template
                break
        
        if not best_template:
            return None
        
        # Fill template
        try:
            content = best_template.template.format(**template_data)
            
            return CannedText(
                text_type=CannedTextType.PERTINENT_NEGATIVES,
                content=content,
                confidence=0.9,
                evidence_support=[f"{negative.finding_type}:{negative.target}"],
                triggered_by=[f"Negative: {negative.target}"]
            )
        except Exception:
            return None
    
    def _prepare_template_data(self,
                             negative: NegativeFinding,
                             findings_data: Dict[str, Any],
                             additional_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for template filling"""
        data = {}
        
        if negative.finding_type == NegativeFindingType.GENE_MUTATION:
            genes = findings_data.get("genes_tested", [])
            if negative.target in ["KRAS/NRAS/BRAF", "EGFR/ALK/ROS1/BRAF/MET/RET/KRAS"]:
                # Handle gene groups
                gene_parts = negative.target.split("/")
                tested_genes = [g for g in gene_parts if g in genes]
                data["gene_list"] = ", ".join(tested_genes)
            else:
                data["gene_list"] = negative.target
            data["clinical_context"] = negative.clinical_relevance
            
        elif negative.finding_type == NegativeFindingType.CHROMOSOMAL_ALTERATION:
            if negative.target == "chr7_gain_chr10_loss":
                data["alteration_type"] = "concurrent chromosome 7 gain and chromosome 10 loss (+7/-10)"
                data["alteration_pattern"] = "+7/-10 signature"
                data["clinical_significance"] = negative.clinical_relevance
                data["diagnostic_implication"] = "This suggests a non-primary GBM molecular profile"
            else:
                data["alteration_type"] = negative.description
                data["clinical_significance"] = negative.clinical_relevance
                
        elif negative.finding_type == NegativeFindingType.METHYLATION:
            data["target"] = f"{negative.target} promoter"
            if negative.target == "MGMT":
                data["therapeutic_implication"] = "This may be associated with reduced benefit from temozolomide"
                data["prognostic_note"] = "MGMT unmethylated status is associated with shorter survival"
            elif negative.target == "MLH1":
                data["clinical_impact"] = "This suggests Lynch syndrome should be considered if MSI-H"
            else:
                data["clinical_impact"] = negative.clinical_relevance
                
        elif negative.finding_type == NegativeFindingType.AMPLIFICATION:
            data["gene"] = negative.target
            copy_number = findings_data.get("copy_number_results", {}).get(negative.target, 2)
            data["copy_number"] = str(copy_number)
            data["therapeutic_relevance"] = negative.clinical_relevance
            
        elif negative.finding_type == NegativeFindingType.VARIANT_SPECIFIC:
            data["specific_variant"] = negative.description
            data["clinical_implication"] = negative.clinical_relevance
            if negative.target == "EGFRvIII":
                data["frequency_note"] = "This variant is found in ~30% of EGFR-amplified GBMs"
                
        elif negative.finding_type == NegativeFindingType.FUSION:
            data["fusion_type"] = negative.target
            data["clinical_relevance"] = negative.clinical_relevance
            
        elif negative.finding_type == NegativeFindingType.EXPRESSION:
            data["marker"] = negative.target
            level = findings_data.get("expression_markers", {}).get(negative.target, "negative")
            data["level"] = level
            data["interpretation"] = f"This indicates {negative.target}-negative status"
            
        elif negative.finding_type == NegativeFindingType.SIGNATURE:
            data["signature_type"] = negative.description
            data["status"] = "not detected"
            data["clinical_relevance"] = negative.clinical_relevance
            
        # Add coverage/quality info if available
        if "coverage_info" in findings_data:
            data["coverage_info"] = findings_data["coverage_info"]
        if "method_note" in findings_data:
            data["method_note"] = findings_data["method_note"]
            
        return data
    
    def _combine_negative_texts(self,
                              texts: List[CannedText],
                              cancer_type: str) -> Optional[CannedText]:
        """Combine multiple negative findings into comprehensive text"""
        if not texts:
            return None
        
        if len(texts) == 1:
            return texts[0]
        
        # Group by finding type
        grouped = {}
        for text in texts:
            finding_type = text.evidence_support[0].split(":")[0] if text.evidence_support else "other"
            if finding_type not in grouped:
                grouped[finding_type] = []
            grouped[finding_type].append(text.content)
        
        # Build combined content
        sections = []
        
        # Start with overview
        sections.append(f"Comprehensive molecular profiling for {cancer_type} revealed the following negative findings:")
        
        # Add each group
        if "gene_mutation" in grouped:
            sections.append(f"\n**Mutations**: {' '.join(grouped['gene_mutation'])}")
        if "chromosomal_alteration" in grouped:
            sections.append(f"\n**Chromosomal Alterations**: {' '.join(grouped['chromosomal_alteration'])}")
        if "methylation" in grouped:
            sections.append(f"\n**Methylation Status**: {' '.join(grouped['methylation'])}")
        if "amplification" in grouped:
            sections.append(f"\n**Copy Number**: {' '.join(grouped['amplification'])}")
        if "fusion" in grouped:
            sections.append(f"\n**Fusions**: {' '.join(grouped['fusion'])}")
        if "variant_specific" in grouped:
            sections.append(f"\n**Specific Variants**: {' '.join(grouped['variant_specific'])}")
        if "expression" in grouped:
            sections.append(f"\n**Expression Markers**: {' '.join(grouped['expression'])}")
        if "signature" in grouped:
            sections.append(f"\n**Molecular Signatures**: {' '.join(grouped['signature'])}")
        
        # Add summary
        sections.append("\n\nThese negative findings provide important information for treatment selection and prognosis.")
        
        combined_content = "\n".join(sections)
        
        # Collect all evidence
        all_evidence = []
        all_triggers = []
        for text in texts:
            all_evidence.extend(text.evidence_support)
            all_triggers.extend(text.triggered_by)
        
        return CannedText(
            text_type=CannedTextType.PERTINENT_NEGATIVES,
            content=combined_content,
            confidence=0.9,
            evidence_support=list(set(all_evidence)),
            triggered_by=list(set(all_triggers))
        )
    
    def _generate_custom_negative_text(self,
                                     finding: Dict[str, Any]) -> Optional[CannedText]:
        """Generate text for custom negative findings not in predefined list"""
        content = finding.get("description", "")
        if not content:
            return None
            
        return CannedText(
            text_type=CannedTextType.PERTINENT_NEGATIVES,
            content=content,
            confidence=0.8,
            evidence_support=[finding.get("type", "custom")],
            triggered_by=[finding.get("target", "custom finding")]
        )


# Example usage for GBM
def generate_gbm_pertinent_negatives_example():
    """Example of comprehensive GBM pertinent negatives"""
    
    generator = EnhancedPertinentNegativesGenerator()
    
    # Example negative findings data for GBM
    negative_findings_data = {
        "genes_tested": ["IDH1", "IDH2", "ATRX", "TP53", "PTEN", "CDKN2A", "CDKN2B"],
        "chromosomal_analysis": {
            "chr7_gain": False,
            "chr10_loss": False,
            "chr1p19q_codeletion": False
        },
        "methylation_tested": ["MGMT", "TERT"],
        "methylation_results": {
            "MGMT": "unmethylated",
            "TERT": "unmethylated"
        },
        "copy_number_tested": ["EGFR", "PDGFRA", "CDK4", "MDM2"],
        "copy_number_results": {
            "EGFR": 2,  # Normal
            "PDGFRA": 2,
            "CDK4": 2,
            "MDM2": 2
        },
        "specific_variants_tested": ["EGFRvIII"],
        "fusion_analysis": {
            "fusions_tested": ["FGFR3-TACC3", "FGFR1-TACC1"],
            "results": "negative"
        },
        "coverage_info": "All regions achieved >500x coverage",
        "method_note": "Analysis performed using targeted NGS panel and methylation-specific PCR"
    }
    
    texts = generator.generate_pertinent_negatives(
        cancer_type="glioblastoma",
        negative_findings_data=negative_findings_data
    )
    
    return texts