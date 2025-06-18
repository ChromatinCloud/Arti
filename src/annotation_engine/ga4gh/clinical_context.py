"""
Clinical Context Extractor for GA4GH Integration

Extracts and standardizes clinical context from various sources
to enhance variant interpretation and enable cross-framework evidence mapping.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
import logging

from ..models import VariantAnnotation, Evidence

logger = logging.getLogger(__name__)


class ClinicalContextType(str, Enum):
    """Types of clinical context"""
    CANCER_TYPE = "cancer_type"
    THERAPY = "therapy"
    RESISTANCE = "resistance"
    PROGNOSIS = "prognosis"
    DIAGNOSIS = "diagnosis"
    PREDISPOSITION = "predisposition"
    

@dataclass
class ClinicalContext:
    """Standardized clinical context"""
    context_type: ClinicalContextType
    primary_condition: str
    specific_context: Optional[str] = None
    therapy_class: Optional[str] = None
    clinical_scenario: Optional[str] = None
    ontology_terms: Optional[List[Dict[str, str]]] = None
    

class ClinicalContextExtractor:
    """
    Extracts and standardizes clinical context to enable:
    1. Cross-guideline evidence mapping (OncoKB → CGC/VICC)
    2. Therapy-specific interpretations
    3. Resistance mechanism identification
    4. Prognostic implications
    """
    
    # Therapy class mappings
    THERAPY_CLASSES = {
        # Targeted therapies
        "imatinib": "TKI",
        "dasatinib": "TKI", 
        "nilotinib": "TKI",
        "erlotinib": "EGFR_TKI",
        "gefitinib": "EGFR_TKI",
        "osimertinib": "EGFR_TKI",
        "crizotinib": "ALK_inhibitor",
        "alectinib": "ALK_inhibitor",
        "vemurafenib": "BRAF_inhibitor",
        "dabrafenib": "BRAF_inhibitor",
        "trametinib": "MEK_inhibitor",
        "cobimetinib": "MEK_inhibitor",
        
        # Immunotherapies
        "pembrolizumab": "PD1_inhibitor",
        "nivolumab": "PD1_inhibitor",
        "atezolizumab": "PDL1_inhibitor",
        "durvalumab": "PDL1_inhibitor",
        "ipilimumab": "CTLA4_inhibitor",
        
        # Hormonal therapies
        "tamoxifen": "SERM",
        "letrozole": "aromatase_inhibitor",
        "anastrozole": "aromatase_inhibitor",
        "fulvestrant": "SERD",
        
        # Other
        "olaparib": "PARP_inhibitor",
        "rucaparib": "PARP_inhibitor",
        "trastuzumab": "HER2_antibody"
    }
    
    # Cancer type hierarchies
    CANCER_HIERARCHIES = {
        "nsclc": ["lung cancer", "lung adenocarcinoma", "lung squamous", "large cell"],
        "breast cancer": ["er+ breast", "her2+ breast", "tnbc", "inflammatory breast"],
        "colorectal": ["colon cancer", "rectal cancer", "crc"],
        "melanoma": ["cutaneous melanoma", "acral melanoma", "mucosal melanoma"],
        "glioma": ["glioblastoma", "astrocytoma", "oligodendroglioma"]
    }
    
    def extract_clinical_context(self,
                               evidence: Evidence,
                               variant: VariantAnnotation,
                               cancer_type: Optional[str] = None) -> ClinicalContext:
        """
        Extract standardized clinical context from evidence
        
        This enables cross-guideline mapping (e.g., OncoKB → CGC/VICC OS1)
        """
        context_type = self._determine_context_type(evidence)
        
        # Extract therapy information if therapeutic evidence
        therapy_info = self._extract_therapy_info(evidence)
        
        # Determine primary condition
        primary_condition = self._extract_primary_condition(
            evidence, cancer_type
        )
        
        # Get ontology terms
        ontology_terms = self._extract_ontology_terms(
            evidence, primary_condition
        )
        
        return ClinicalContext(
            context_type=context_type,
            primary_condition=primary_condition,
            specific_context=self._extract_specific_context(evidence),
            therapy_class=therapy_info.get("class") if therapy_info else None,
            clinical_scenario=self._build_clinical_scenario(
                evidence, variant, therapy_info
            ),
            ontology_terms=ontology_terms
        )
    
    def _determine_context_type(self, evidence: Evidence) -> ClinicalContextType:
        """Determine the type of clinical context"""
        evidence_type = evidence.evidence_type.lower() if evidence.evidence_type else ""
        description = evidence.description.lower()
        
        if "therapeutic" in evidence_type or "treatment" in description:
            if "resistance" in description:
                return ClinicalContextType.RESISTANCE
            return ClinicalContextType.THERAPY
        elif "prognostic" in evidence_type:
            return ClinicalContextType.PROGNOSIS
        elif "diagnostic" in evidence_type:
            return ClinicalContextType.DIAGNOSIS
        elif "predisposing" in description or "germline" in description:
            return ClinicalContextType.PREDISPOSITION
        else:
            return ClinicalContextType.DIAGNOSIS
    
    def _extract_therapy_info(self, evidence: Evidence) -> Optional[Dict]:
        """Extract therapy information from evidence"""
        if evidence.evidence_type != "THERAPEUTIC":
            return None
            
        therapy_info = {}
        
        # Check metadata first
        if evidence.metadata and "therapy" in evidence.metadata:
            therapy_name = evidence.metadata["therapy"].lower()
            therapy_info["name"] = therapy_name
            therapy_info["class"] = self.THERAPY_CLASSES.get(
                therapy_name, "other"
            )
            
        # Parse from description if needed
        else:
            therapy_match = re.search(
                r'(sensitiv|respon|resist)\w*\s+to\s+(\w+)',
                evidence.description,
                re.IGNORECASE
            )
            if therapy_match:
                therapy_info["name"] = therapy_match.group(2).lower()
                therapy_info["class"] = self.THERAPY_CLASSES.get(
                    therapy_info["name"], "other"
                )
                therapy_info["response"] = therapy_match.group(1).lower()
                
        return therapy_info if therapy_info else None
    
    def _extract_primary_condition(self,
                                 evidence: Evidence,
                                 cancer_type: Optional[str]) -> str:
        """Extract primary condition/cancer type"""
        # Check evidence metadata
        if evidence.metadata and "disease" in evidence.metadata:
            return evidence.metadata["disease"]
            
        # Use provided cancer type
        if cancer_type:
            return cancer_type
            
        # Try to extract from description
        for cancer_group, subtypes in self.CANCER_HIERARCHIES.items():
            all_types = [cancer_group] + subtypes
            for ctype in all_types:
                if ctype in evidence.description.lower():
                    return ctype
                    
        return "cancer"  # Generic fallback
    
    def _extract_specific_context(self, evidence: Evidence) -> Optional[str]:
        """Extract specific clinical context details"""
        description = evidence.description.lower()
        
        # Look for specific contexts
        contexts = []
        
        # Treatment line
        if "first-line" in description:
            contexts.append("first-line")
        elif "second-line" in description:
            contexts.append("second-line")
        elif "refractory" in description:
            contexts.append("refractory")
            
        # Combination therapy
        if "combination" in description:
            contexts.append("combination")
        elif "monotherapy" in description:
            contexts.append("monotherapy")
            
        # Special populations
        if "pediatric" in description:
            contexts.append("pediatric")
        elif "elderly" in description:
            contexts.append("elderly")
            
        return "; ".join(contexts) if contexts else None
    
    def _extract_ontology_terms(self,
                              evidence: Evidence,
                              condition: str) -> List[Dict[str, str]]:
        """Extract relevant ontology terms"""
        terms = []
        
        # Map to NCIt terms
        ncit_map = {
            "melanoma": {"id": "NCIT:C3224", "label": "Melanoma"},
            "nsclc": {"id": "NCIT:C2926", "label": "Non-Small Cell Lung Carcinoma"},
            "breast cancer": {"id": "NCIT:C4872", "label": "Breast Carcinoma"},
            "colorectal": {"id": "NCIT:C2955", "label": "Colorectal Carcinoma"}
        }
        
        # Check for exact matches
        for key, term in ncit_map.items():
            if key in condition.lower():
                terms.append(term)
                
        # Add therapy ontology if present
        if evidence.metadata and "therapy" in evidence.metadata:
            therapy = evidence.metadata["therapy"]
            # Would map to ChEBI or similar
            terms.append({
                "id": f"CHEBI:{hash(therapy) % 100000}",  # Placeholder
                "label": therapy
            })
            
        return terms
    
    def _build_clinical_scenario(self,
                               evidence: Evidence,
                               variant: VariantAnnotation,
                               therapy_info: Optional[Dict]) -> str:
        """Build human-readable clinical scenario"""
        parts = []
        
        # Gene and variant
        parts.append(f"{variant.gene_symbol} {variant.hgvs_p or 'variant'}")
        
        # Context type
        if evidence.evidence_type == "THERAPEUTIC":
            if therapy_info:
                response = therapy_info.get("response", "associated with")
                parts.append(f"{response} {therapy_info['name']}")
            else:
                parts.append("therapeutic implications")
        elif evidence.evidence_type == "PROGNOSTIC":
            parts.append("prognostic marker")
        elif evidence.evidence_type == "DIAGNOSTIC":
            parts.append("diagnostic marker")
            
        # Add condition
        if evidence.metadata and "disease" in evidence.metadata:
            parts.append(f"in {evidence.metadata['disease']}")
            
        return " ".join(parts)
    
    def map_oncokb_to_cgc_vicc(self,
                              oncokb_classification: str,
                              clinical_context: ClinicalContext) -> Dict[str, Any]:
        """
        Map OncoKB classification to CGC/VICC criteria
        
        Implements the cross-guideline mapping requested by the user
        """
        mapping = {
            "criterion": None,
            "confidence": 0.0,
            "rationale": ""
        }
        
        if oncokb_classification == "Oncogenic":
            mapping["criterion"] = "OS1"
            mapping["confidence"] = 0.95
            mapping["rationale"] = (
                "OncoKB 'Oncogenic' classification based on FDA-recognized "
                "expert curation meets OS1 (expert panel/database classification)"
            )
            
        elif oncokb_classification == "Likely Oncogenic":
            mapping["criterion"] = "OM1" 
            mapping["confidence"] = 0.85
            mapping["rationale"] = (
                "OncoKB 'Likely Oncogenic' suggests moderate evidence "
                "supporting oncogenicity (OM1)"
            )
            
        elif oncokb_classification == "Predicted Oncogenic":
            mapping["criterion"] = "OP1"
            mapping["confidence"] = 0.70
            mapping["rationale"] = (
                "OncoKB 'Predicted Oncogenic' based on computational "
                "evidence maps to OP1"
            )
            
        # Adjust based on clinical context
        if clinical_context.context_type == ClinicalContextType.RESISTANCE:
            mapping["confidence"] *= 0.9  # Slightly lower for resistance
            
        return mapping
    
    def extract_canned_text_components(self,
                                     evidence: Evidence,
                                     clinical_context: ClinicalContext) -> Dict[str, str]:
        """
        Extract components for generating canned text
        
        Supports the goal of standardized reporting text
        """
        components = {
            "variant_description": "",
            "clinical_significance": "",
            "evidence_summary": "",
            "recommendation": "",
            "references": ""
        }
        
        # Variant description
        if clinical_context.context_type == ClinicalContextType.THERAPY:
            components["variant_description"] = (
                f"This variant has been associated with response to "
                f"{clinical_context.therapy_class or 'targeted'} therapy"
            )
        elif clinical_context.context_type == ClinicalContextType.RESISTANCE:
            components["variant_description"] = (
                f"This variant confers resistance to "
                f"{clinical_context.therapy_class or 'certain'} therapies"
            )
            
        # Clinical significance
        components["clinical_significance"] = self._generate_significance_text(
            evidence, clinical_context
        )
        
        # Evidence summary
        components["evidence_summary"] = self._summarize_evidence(
            evidence, clinical_context
        )
        
        # Recommendation
        components["recommendation"] = self._generate_recommendation(
            evidence, clinical_context
        )
        
        # References
        if evidence.metadata and "pmids" in evidence.metadata:
            pmids = evidence.metadata["pmids"]
            components["references"] = f"PMID: {', '.join(map(str, pmids))}"
            
        return components
    
    def _generate_significance_text(self,
                                  evidence: Evidence,
                                  context: ClinicalContext) -> str:
        """Generate clinical significance text"""
        if evidence.source_kb == "ONCOKB":
            return (
                f"This variant is classified as clinically significant "
                f"for {context.primary_condition} based on OncoKB curation"
            )
        elif evidence.source_kb == "CIVIC":
            return (
                f"Clinical evidence supports the significance of this "
                f"variant in {context.primary_condition}"
            )
        else:
            return (
                f"This variant has reported clinical significance "
                f"in {context.primary_condition}"
            )
    
    def _summarize_evidence(self,
                          evidence: Evidence,
                          context: ClinicalContext) -> str:
        """Summarize evidence in readable format"""
        level_map = {
            10: "Level 1 (FDA-approved)",
            9: "Level 2 (Standard care)",
            8: "Level 3A (Clinical evidence)",
            7: "Level 3B (Pre-clinical)",
            6: "Level 4 (Biological)"
        }
        
        level_text = level_map.get(
            evidence.score,
            f"Level {evidence.score}"
        )
        
        return (
            f"{level_text} evidence from {evidence.source_kb} "
            f"database. {evidence.description}"
        )
    
    def _generate_recommendation(self,
                               evidence: Evidence,
                               context: ClinicalContext) -> str:
        """Generate clinical recommendation text"""
        if context.context_type == ClinicalContextType.THERAPY:
            if evidence.score >= 8:  # Level 1/2
                return (
                    "Consider treatment with indicated therapy based on "
                    "high-level clinical evidence"
                )
            else:
                return (
                    "Potential therapeutic option based on emerging evidence; "
                    "consider in appropriate clinical context"
                )
        elif context.context_type == ClinicalContextType.RESISTANCE:
            return (
                "Alternative therapeutic strategies should be considered "
                "due to likely resistance"
            )
        else:
            return "Consider in overall clinical assessment"