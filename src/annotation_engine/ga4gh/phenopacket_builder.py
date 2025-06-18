"""
GA4GH Phenopackets Builder for Cancer Cases

Implements Phenopackets v2.0 with cancer-specific extensions.
Enables standardized clinical data exchange and interoperability.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import logging

from ..models import VariantAnnotation, TierResult, Evidence
from .vrs_handler import VRSHandler

logger = logging.getLogger(__name__)


@dataclass
class CancerClinicalData:
    """Clinical data specific to cancer cases"""
    cancer_type: str
    stage: Optional[str] = None
    grade: Optional[str] = None
    primary_site: Optional[str] = None
    metastatic_sites: Optional[List[str]] = None
    tnm_staging: Optional[Dict[str, str]] = None  # T, N, M components
    histology: Optional[str] = None
    molecular_subtype: Optional[str] = None


class PhenopacketBuilder:
    """
    Builds GA4GH Phenopackets for clinical variant interpretation
    
    Focuses on cancer use cases with variant annotations
    """
    
    # OncoTree to NCIt mappings for common cancers
    CANCER_ONTOLOGY_MAP = {
        "melanoma": {"id": "NCIT:C3224", "label": "Melanoma"},
        "lung adenocarcinoma": {"id": "NCIT:C3512", "label": "Lung Adenocarcinoma"},
        "breast cancer": {"id": "NCIT:C4872", "label": "Breast Carcinoma"},
        "colorectal cancer": {"id": "NCIT:C2955", "label": "Colorectal Carcinoma"},
        "prostate cancer": {"id": "NCIT:C4863", "label": "Prostate Carcinoma"},
        "ovarian cancer": {"id": "NCIT:C4908", "label": "Ovarian Carcinoma"},
        "pancreatic cancer": {"id": "NCIT:C8294", "label": "Pancreatic Carcinoma"},
        "glioblastoma": {"id": "NCIT:C3058", "label": "Glioblastoma"},
        "leukemia": {"id": "NCIT:C3161", "label": "Leukemia"},
        "lymphoma": {"id": "NCIT:C3208", "label": "Lymphoma"}
    }
    
    def __init__(self, vrs_handler: Optional[VRSHandler] = None):
        self.vrs_handler = vrs_handler or VRSHandler()
        
    def create_cancer_phenopacket(self,
                                 patient_id: str,
                                 cancer_data: CancerClinicalData,
                                 variants: List[VariantAnnotation],
                                 tier_results: List[TierResult],
                                 evidence_lists: List[List[Evidence]]) -> Dict:
        """
        Create a comprehensive phenopacket for a cancer case
        
        Args:
            patient_id: Patient identifier
            cancer_data: Clinical cancer information
            variants: List of annotated variants
            tier_results: Tier classifications for each variant
            evidence_lists: Evidence supporting each variant
            
        Returns:
            Phenopacket as dictionary (v2.0 schema)
        """
        phenopacket = {
            "id": f"{patient_id}_phenopacket_{datetime.utcnow().strftime('%Y%m%d')}",
            "subject": self._create_individual(patient_id),
            "phenotypicFeatures": [],  # Could add cancer symptoms
            "diseases": [self._create_disease(cancer_data)],
            "interpretations": self._create_interpretations(
                variants, tier_results, evidence_lists, cancer_data
            ),
            "metaData": self._create_metadata()
        }
        
        return phenopacket
    
    def _create_individual(self, patient_id: str) -> Dict:
        """Create individual/subject section"""
        return {
            "id": patient_id,
            "timeAtLastEncounter": {
                "age": {"iso8601duration": "P40Y"}  # Placeholder
            },
            "sex": "UNKNOWN_SEX",  # Would need actual data
            "karyotypicSex": "UNKNOWN_KARYOTYPE"
        }
    
    def _create_disease(self, cancer_data: CancerClinicalData) -> Dict:
        """Create disease representation for cancer"""
        # Get ontology term
        ontology = self.CANCER_ONTOLOGY_MAP.get(
            cancer_data.cancer_type.lower(),
            {"id": "NCIT:C9305", "label": "Malignant Neoplasm"}
        )
        
        disease = {
            "term": ontology,
            "onset": {"age": {"iso8601duration": "P35Y"}},  # Placeholder
            "diseaseStage": []
        }
        
        # Add staging information
        if cancer_data.stage:
            disease["diseaseStage"].append({
                "id": f"NCIT:C{self._stage_to_ncit_code(cancer_data.stage)}",
                "label": f"Stage {cancer_data.stage}"
            })
            
        if cancer_data.tnm_staging:
            disease["tnmFinding"] = self._create_tnm_finding(cancer_data.tnm_staging)
            
        # Add clinical modifiers
        if cancer_data.primary_site:
            disease["primarySite"] = {
                "id": "UBERON:0000000",  # Would map to actual anatomy
                "label": cancer_data.primary_site
            }
            
        return disease
    
    def _create_interpretations(self,
                              variants: List[VariantAnnotation],
                              tier_results: List[TierResult],
                              evidence_lists: List[List[Evidence]],
                              cancer_data: CancerClinicalData) -> List[Dict]:
        """Create genomic interpretations section"""
        interpretations = []
        
        for variant, tier_result, evidences in zip(variants, tier_results, evidence_lists):
            interpretation = {
                "id": f"interpretation_{variant.vrs_id or variant.hgvs_g}",
                "progressStatus": "SOLVED",  # Variant interpreted
                "diagnosis": {
                    "disease": self.CANCER_ONTOLOGY_MAP.get(
                        cancer_data.cancer_type.lower(),
                        {"id": "NCIT:C9305", "label": "Malignant Neoplasm"}
                    ),
                    "genomicInterpretations": [
                        self._create_genomic_interpretation(
                            variant, tier_result, evidences
                        )
                    ]
                }
            }
            interpretations.append(interpretation)
            
        return interpretations
    
    def _create_genomic_interpretation(self,
                                     variant: VariantAnnotation,
                                     tier_result: TierResult,
                                     evidences: List[Evidence]) -> Dict:
        """Create individual genomic interpretation"""
        interpretation = {
            "subjectOrBiosampleId": "placeholder_subject",
            "interpretationStatus": "CONTRIBUTORY",
            "variantInterpretation": {
                "variationDescriptor": self._create_variation_descriptor(variant),
                "variationInterpretation": {
                    "variationId": variant.vrs_id or f"local:{variant.hgvs_g}"
                }
            }
        }
        
        # Add AMP/ASCO/CAP classification
        if tier_result.amp_scoring:
            interpretation["variantInterpretation"]["acmgPathogenicityClassification"] = \
                self._map_amp_to_acmg(tier_result.amp_scoring.tier.value)
        
        # Add CGC/VICC oncogenicity
        if tier_result.cgc_vicc_oncogenicity:
            interpretation["variantInterpretation"]["oncogenicityClassification"] = \
                tier_result.cgc_vicc_oncogenicity.classification
        
        # Add therapeutic levels
        if tier_result.oncokb_scoring:
            interpretation["variantInterpretation"]["therapeuticActionability"] = {
                "level": tier_result.oncokb_scoring.therapeutic_level.value,
                "source": "OncoKB"
            }
            
        return interpretation
    
    def _create_variation_descriptor(self, variant: VariantAnnotation) -> Dict:
        """Create variation descriptor with VRS representation"""
        descriptor = {
            "id": variant.vrs_id or f"local:{variant.hgvs_g}",
            "variation": {},
            "label": f"{variant.gene_symbol} {variant.hgvs_p or variant.hgvs_c}",
            "geneContext": {
                "valueId": variant.gene_id,
                "symbol": variant.gene_symbol
            },
            "expressions": []
        }
        
        # Add VRS representation
        if variant.vrs_allele:
            descriptor["variation"] = variant.vrs_allele
        else:
            # Fallback to simple representation
            descriptor["variation"] = {
                "allele": {
                    "sequenceLocation": {
                        "sequenceId": f"refseq:{variant.chromosome}",
                        "sequenceInterval": {
                            "startNumber": {"value": variant.position},
                            "endNumber": {"value": variant.position + len(variant.reference)}
                        }
                    },
                    "literalSequenceExpression": {
                        "sequence": variant.alternate
                    }
                }
            }
            
        # Add HGVS expressions
        if variant.hgvs_g:
            descriptor["expressions"].append({
                "syntax": "hgvs.g",
                "value": variant.hgvs_g
            })
        if variant.hgvs_c:
            descriptor["expressions"].append({
                "syntax": "hgvs.c", 
                "value": variant.hgvs_c
            })
        if variant.hgvs_p:
            descriptor["expressions"].append({
                "syntax": "hgvs.p",
                "value": variant.hgvs_p
            })
            
        # Add molecular consequences
        if variant.consequence:
            descriptor["molecularConsequences"] = [{
                "id": f"SO:{self._consequence_to_so(variant.consequence)}",
                "label": variant.consequence
            }]
            
        return descriptor
    
    def _create_metadata(self) -> Dict:
        """Create metadata section"""
        return {
            "created": datetime.utcnow().isoformat() + "Z",
            "createdBy": "annotation_engine",
            "submittedBy": "clinical_laboratory",
            "resources": [
                {
                    "id": "hp",
                    "name": "Human Phenotype Ontology",
                    "url": "http://purl.obolibrary.org/obo/hp.owl",
                    "version": "2023-10-09"
                },
                {
                    "id": "ncit", 
                    "name": "NCI Thesaurus",
                    "url": "http://purl.obolibrary.org/obo/ncit.owl",
                    "version": "23.09d"
                },
                {
                    "id": "so",
                    "name": "Sequence Ontology",
                    "url": "http://purl.obolibrary.org/obo/so.owl",
                    "version": "2023-11-27"
                }
            ],
            "phenopacketSchemaVersion": "2.0.0",
            "externalReferences": [
                {
                    "id": "DOI:10.1038/s41588-020-0676-4",
                    "reference": "VICC Meta-Knowledgebase",
                    "description": "Wagner et al. 2020"
                }
            ]
        }
    
    def _stage_to_ncit_code(self, stage: str) -> str:
        """Map cancer stage to NCIt code suffix"""
        stage_map = {
            "I": "27966", "IA": "27967", "IB": "27968",
            "II": "27970", "IIA": "27971", "IIB": "27972", 
            "III": "27977", "IIIA": "27978", "IIIB": "27979", "IIIC": "27980",
            "IV": "27981", "IVA": "27982", "IVB": "27983"
        }
        return stage_map.get(stage.upper(), "25699")  # Default: Stage Unknown
    
    def _create_tnm_finding(self, tnm: Dict[str, str]) -> List[Dict]:
        """Create TNM staging findings"""
        findings = []
        
        tnm_codes = {
            "T": {"prefix": "NCIT:C48885", "label": "T Stage"},
            "N": {"prefix": "NCIT:C48884", "label": "N Stage"},  
            "M": {"prefix": "NCIT:C48883", "label": "M Stage"}
        }
        
        for component, value in tnm.items():
            if component in tnm_codes:
                findings.append({
                    "id": f"{tnm_codes[component]['prefix']}",
                    "label": f"{tnm_codes[component]['label']}: {value}"
                })
                
        return findings
    
    def _map_amp_to_acmg(self, amp_tier: str) -> str:
        """Map AMP tier to closest ACMG classification"""
        mapping = {
            "TIER_I": "PATHOGENIC",
            "TIER_II": "LIKELY_PATHOGENIC", 
            "TIER_III": "UNCERTAIN_SIGNIFICANCE",
            "TIER_IV": "LIKELY_BENIGN"
        }
        return mapping.get(amp_tier, "UNCERTAIN_SIGNIFICANCE")
    
    def _consequence_to_so(self, consequence: str) -> str:
        """Map consequence to Sequence Ontology ID"""
        so_map = {
            "missense_variant": "0001583",
            "stop_gained": "0001587",
            "frameshift_variant": "0001589",
            "splice_acceptor_variant": "0001574",
            "splice_donor_variant": "0001575",
            "inframe_insertion": "0001821",
            "inframe_deletion": "0001822"
        }
        return so_map.get(consequence, "0001060")  # Default: sequence_variant


class CancerPhenopacketCreator:
    """
    High-level interface for creating cancer phenopackets
    
    Simplifies the process for common use cases
    """
    
    def __init__(self):
        self.builder = PhenopacketBuilder()
        
    def create_from_annotation_results(self,
                                     patient_id: str,
                                     cancer_type: str,
                                     annotation_results: List[Dict]) -> Dict:
        """
        Create phenopacket from annotation engine results
        
        Args:
            patient_id: Patient identifier
            cancer_type: Cancer type string
            annotation_results: List of complete annotation results
            
        Returns:
            Complete phenopacket
        """
        # Extract components from results
        variants = []
        tier_results = []
        evidence_lists = []
        
        for result in annotation_results:
            if "variant" in result:
                variants.append(result["variant"])
            if "tier_result" in result:
                tier_results.append(result["tier_result"])
            if "evidence" in result:
                evidence_lists.append(result["evidence"])
                
        # Create cancer data
        cancer_data = CancerClinicalData(
            cancer_type=cancer_type,
            stage="Unknown",  # Would extract from clinical data
            primary_site=self._infer_primary_site(cancer_type)
        )
        
        # Build phenopacket
        return self.builder.create_cancer_phenopacket(
            patient_id=patient_id,
            cancer_data=cancer_data,
            variants=variants,
            tier_results=tier_results,
            evidence_lists=evidence_lists
        )
    
    def _infer_primary_site(self, cancer_type: str) -> str:
        """Infer primary site from cancer type"""
        site_map = {
            "melanoma": "skin",
            "lung": "lung",
            "breast": "breast", 
            "colorectal": "colon",
            "prostate": "prostate",
            "ovarian": "ovary",
            "pancreatic": "pancreas",
            "glioblastoma": "brain"
        }
        
        for key, site in site_map.items():
            if key in cancer_type.lower():
                return site
                
        return "unknown primary"
    
    def export_to_file(self, phenopacket: Dict, filepath: str):
        """Export phenopacket to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(phenopacket, f, indent=2)
            
        logger.info(f"Exported phenopacket to {filepath}")