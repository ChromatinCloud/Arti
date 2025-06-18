"""
GA4GH Variant Annotation (VA) Standard Implementation

Implements the GA4GH VA specification for standardized variant annotations.
Enables interoperable exchange of variant interpretations.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json
import logging

from ..models import VariantAnnotation, Evidence, TierResult
from .vrs_handler import VRSHandler

logger = logging.getLogger(__name__)


class EvidenceType(str, Enum):
    """GA4GH standard evidence types"""
    COMPUTATIONAL = "computational"
    FUNCTIONAL = "functional"
    CLINICAL = "clinical"
    POPULATION = "population"
    LITERATURE = "literature"
    
    
class ClinicalSignificance(str, Enum):
    """GA4GH clinical significance categories"""
    PATHOGENIC = "pathogenic"
    LIKELY_PATHOGENIC = "likely_pathogenic"
    UNCERTAIN_SIGNIFICANCE = "uncertain_significance"
    LIKELY_BENIGN = "likely_benign"
    BENIGN = "benign"
    # Cancer-specific
    ONCOGENIC = "oncogenic"
    LIKELY_ONCOGENIC = "likely_oncogenic"
    UNCERTAIN_ONCOGENICITY = "uncertain_oncogenicity"
    LIKELY_BENIGN_ONCOGENICITY = "likely_benign_oncogenicity"
    BENIGN_ONCOGENICITY = "benign_oncogenicity"


class GA4GHVariantAnnotation:
    """
    Implements GA4GH Variant Annotation standard
    
    Provides standardized format for variant annotations
    that can be exchanged between systems
    """
    
    VERSION = "0.2.0"  # VA specification version
    
    def __init__(self, vrs_handler: Optional[VRSHandler] = None):
        self.vrs_handler = vrs_handler or VRSHandler()
        
    def create_va_message(self,
                         variant: VariantAnnotation,
                         evidence_list: List[Evidence],
                         tier_result: Optional[TierResult] = None,
                         additional_annotations: Optional[Dict] = None) -> Dict:
        """
        Create GA4GH VA-compliant annotation message
        
        Args:
            variant: Annotated variant
            evidence_list: Supporting evidence
            tier_result: Tier classification results
            additional_annotations: Extra annotations to include
            
        Returns:
            VA-compliant annotation message
        """
        # Ensure variant has VRS ID
        if not variant.vrs_id:
            variant.vrs_id = self.vrs_handler.get_vrs_id(variant)
            
        va_message = {
            "version": self.VERSION,
            "annotationSource": {
                "name": "annotation_engine",
                "version": "1.0.0",
                "type": "automated_pipeline"
            },
            "variant": self._create_variant_descriptor(variant),
            "annotations": self._create_annotations(
                variant, evidence_list, tier_result
            ),
            "metadata": self._create_metadata(variant)
        }
        
        # Add any additional annotations
        if additional_annotations:
            va_message["extensions"] = additional_annotations
            
        return va_message
    
    def _create_variant_descriptor(self, variant: VariantAnnotation) -> Dict:
        """Create standardized variant descriptor"""
        descriptor = {
            "id": variant.vrs_id,
            "type": "Allele",  # Could also be CNV, Fusion, etc.
            "variation": variant.vrs_allele if variant.vrs_allele else None,
            "expressions": []
        }
        
        # Add various expressions
        if variant.hgvs_g:
            descriptor["expressions"].append({
                "syntax": "hgvs.g",
                "value": variant.hgvs_g,
                "reference": "GRCh38"
            })
        if variant.hgvs_c:
            descriptor["expressions"].append({
                "syntax": "hgvs.c",
                "value": variant.hgvs_c,
                "transcript": variant.transcript_id
            })
        if variant.hgvs_p:
            descriptor["expressions"].append({
                "syntax": "hgvs.p",
                "value": variant.hgvs_p
            })
            
        # Add gene context
        if variant.gene_symbol:
            descriptor["geneContext"] = {
                "symbol": variant.gene_symbol,
                "id": variant.gene_id
            }
            
        return descriptor
    
    def _create_annotations(self,
                          variant: VariantAnnotation,
                          evidence_list: List[Evidence],
                          tier_result: Optional[TierResult]) -> List[Dict]:
        """Create list of standardized annotations"""
        annotations = []
        
        # Clinical significance annotation
        if tier_result:
            annotations.append(self._create_clinical_significance_annotation(
                variant, tier_result
            ))
            
        # Evidence-based annotations
        for evidence in evidence_list:
            annotation = self._evidence_to_annotation(evidence, variant)
            if annotation:
                annotations.append(annotation)
                
        # Population frequency annotation
        if variant.population_frequencies:
            annotations.append(self._create_population_annotation(variant))
            
        # Functional annotations
        if variant.functional_predictions:
            annotations.extend(self._create_functional_annotations(variant))
            
        # Conservation annotation
        if hasattr(variant, 'conservation_scores'):
            annotations.append(self._create_conservation_annotation(variant))
            
        return annotations
    
    def _evidence_to_annotation(self, 
                              evidence: Evidence,
                              variant: VariantAnnotation) -> Optional[Dict]:
        """Convert internal evidence to GA4GH annotation"""
        # Map evidence type
        evidence_type_map = {
            "ONCOKB": EvidenceType.CLINICAL,
            "CIVIC": EvidenceType.CLINICAL,
            "COSMIC": EvidenceType.CLINICAL,
            "CLINVAR": EvidenceType.CLINICAL,
            "FUNCTIONAL": EvidenceType.FUNCTIONAL,
            "COMPUTATIONAL": EvidenceType.COMPUTATIONAL
        }
        
        evidence_type = EvidenceType.CLINICAL  # Default
        for key, etype in evidence_type_map.items():
            if key in evidence.code:
                evidence_type = etype
                break
                
        annotation = {
            "type": evidence_type.value,
            "assertion": {
                "code": evidence.code,
                "system": evidence.guideline,
                "display": evidence.description
            },
            "evidenceLevel": {
                "score": evidence.score,
                "confidence": evidence.confidence
            },
            "source": {
                "name": evidence.source_kb,
                "version": evidence.metadata.get("version", "unknown") if evidence.metadata else "unknown"
            }
        }
        
        # Add evidence-specific details
        if evidence.evidence_type:
            annotation["evidenceCategory"] = evidence.evidence_type
            
        if evidence.metadata:
            # Add publications
            if "pmids" in evidence.metadata:
                annotation["citations"] = [
                    {"id": f"PMID:{pmid}", "type": "primary_literature"}
                    for pmid in evidence.metadata["pmids"]
                ]
            
            # Add therapy context if therapeutic evidence
            if evidence.evidence_type == "THERAPEUTIC" and "therapy" in evidence.metadata:
                annotation["therapeuticContext"] = {
                    "therapy": evidence.metadata["therapy"],
                    "indication": evidence.metadata.get("indication", variant.cancer_type)
                }
                
        return annotation
    
    def _create_clinical_significance_annotation(self,
                                               variant: VariantAnnotation,
                                               tier_result: TierResult) -> Dict:
        """Create clinical significance annotation from tier result"""
        annotation = {
            "type": "clinical_significance",
            "clinicalSignificance": {},
            "guidelines": []
        }
        
        # AMP/ASCO/CAP classification
        if tier_result.amp_scoring:
            amp_sig = self._map_amp_tier_to_significance(
                tier_result.amp_scoring.tier.value
            )
            annotation["clinicalSignificance"]["amp"] = amp_sig
            annotation["guidelines"].append({
                "name": "AMP/ASCO/CAP 2017",
                "version": "2017",
                "tier": tier_result.amp_scoring.tier.value,
                "score": tier_result.amp_scoring.total_score
            })
            
        # CGC/VICC oncogenicity
        if tier_result.cgc_vicc_oncogenicity:
            annotation["clinicalSignificance"]["oncogenicity"] = \
                tier_result.cgc_vicc_oncogenicity.classification.lower()
            annotation["guidelines"].append({
                "name": "CGC/VICC 2022",
                "version": "2022",
                "classification": tier_result.cgc_vicc_oncogenicity.classification,
                "criteria_met": tier_result.cgc_vicc_oncogenicity.criteria_met
            })
            
        # OncoKB levels
        if tier_result.oncokb_scoring:
            annotation["therapeuticImplications"] = {
                "level": tier_result.oncokb_scoring.therapeutic_level.value,
                "source": "OncoKB",
                "fda_approved": tier_result.oncokb_scoring.fda_approved
            }
            
        return annotation
    
    def _create_population_annotation(self, variant: VariantAnnotation) -> Dict:
        """Create population frequency annotation"""
        frequencies = []
        
        for pop, freq in variant.population_frequencies.items():
            frequencies.append({
                "population": pop,
                "alleleFrequency": freq,
                "source": "gnomAD" if "gnomad" in pop.lower() else "unknown"
            })
            
        return {
            "type": "population_frequency",
            "frequencies": frequencies,
            "maxFrequency": max(variant.population_frequencies.values())
        }
    
    def _create_functional_annotations(self, variant: VariantAnnotation) -> List[Dict]:
        """Create functional prediction annotations"""
        annotations = []
        
        for tool, prediction in variant.functional_predictions.items():
            annotation = {
                "type": "functional_prediction",
                "predictor": {
                    "name": tool,
                    "version": prediction.get("version", "unknown")
                },
                "prediction": prediction.get("prediction"),
                "score": prediction.get("score"),
                "interpretation": prediction.get("interpretation", "unknown")
            }
            
            # Add tool-specific details
            if tool == "AlphaMissense" and "class" in prediction:
                annotation["classification"] = prediction["class"]
            elif tool == "SpliceAI" and "delta_scores" in prediction:
                annotation["spliceEffect"] = prediction["delta_scores"]
                
            annotations.append(annotation)
            
        return annotations
    
    def _create_conservation_annotation(self, variant: VariantAnnotation) -> Dict:
        """Create conservation score annotation"""
        scores = {}
        
        if hasattr(variant, 'conservation_scores'):
            for method, score in variant.conservation_scores.items():
                scores[method] = {
                    "score": score,
                    "interpretation": self._interpret_conservation_score(method, score)
                }
                
        return {
            "type": "conservation",
            "scores": scores,
            "overallConservation": self._overall_conservation(scores)
        }
    
    def _create_metadata(self, variant: VariantAnnotation) -> Dict:
        """Create metadata section"""
        return {
            "annotationDate": datetime.utcnow().isoformat() + "Z",
            "genomeAssembly": variant.assembly or "GRCh38",
            "transcriptSet": "RefSeq" if variant.transcript_id and variant.transcript_id.startswith("NM_") else "Ensembl",
            "annotationTools": [
                {"name": "VEP", "version": "111"},
                {"name": "annotation_engine", "version": "1.0.0"}
            ]
        }
    
    def _map_amp_tier_to_significance(self, tier: str) -> str:
        """Map AMP tier to clinical significance"""
        mapping = {
            "TIER_I": ClinicalSignificance.PATHOGENIC.value,
            "TIER_II": ClinicalSignificance.LIKELY_PATHOGENIC.value,
            "TIER_III": ClinicalSignificance.UNCERTAIN_SIGNIFICANCE.value,
            "TIER_IV": ClinicalSignificance.LIKELY_BENIGN.value
        }
        return mapping.get(tier, ClinicalSignificance.UNCERTAIN_SIGNIFICANCE.value)
    
    def _interpret_conservation_score(self, method: str, score: float) -> str:
        """Interpret conservation score"""
        if method == "phyloP":
            if score > 7: return "highly_conserved"
            elif score > 2: return "conserved"
            else: return "not_conserved"
        elif method == "GERP":
            if score > 4: return "highly_conserved"
            elif score > 2: return "conserved"
            else: return "not_conserved"
        else:
            return "unknown"
            
    def _overall_conservation(self, scores: Dict) -> str:
        """Determine overall conservation level"""
        conserved_count = sum(
            1 for s in scores.values() 
            if s["interpretation"] in ["conserved", "highly_conserved"]
        )
        
        if conserved_count >= 2:
            return "conserved"
        elif conserved_count >= 1:
            return "possibly_conserved"
        else:
            return "not_conserved"


class AnnotationExporter:
    """
    Export annotations in various GA4GH-compliant formats
    """
    
    def __init__(self):
        self.va_handler = GA4GHVariantAnnotation()
        
    def export_batch_annotations(self,
                               annotation_results: List[Dict],
                               format: str = "va") -> Union[List[Dict], str]:
        """
        Export batch of annotations in specified format
        
        Args:
            annotation_results: List of annotation engine results
            format: Export format (va, vcf, tsv)
            
        Returns:
            Formatted annotations
        """
        if format == "va":
            return self._export_as_va(annotation_results)
        elif format == "vcf":
            return self._export_as_annotated_vcf(annotation_results)
        elif format == "tsv":
            return self._export_as_tsv(annotation_results)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _export_as_va(self, results: List[Dict]) -> List[Dict]:
        """Export as GA4GH VA messages"""
        va_messages = []
        
        for result in results:
            variant = result.get("variant")
            evidence = result.get("evidence", [])
            tier_result = result.get("tier_result")
            
            if variant:
                va_message = self.va_handler.create_va_message(
                    variant, evidence, tier_result
                )
                va_messages.append(va_message)
                
        return va_messages
    
    def _export_as_annotated_vcf(self, results: List[Dict]) -> str:
        """Export as VCF with GA4GH annotations in INFO field"""
        vcf_lines = []
        
        # Add header
        vcf_lines.append("##fileformat=VCFv4.3")
        vcf_lines.append(f"##fileDate={datetime.utcnow().strftime('%Y%m%d')}")
        vcf_lines.append("##source=annotation_engine_ga4gh")
        vcf_lines.append("##INFO=<ID=VRS_ID,Number=1,Type=String,Description=\"GA4GH VRS identifier\">")
        vcf_lines.append("##INFO=<ID=AMP_TIER,Number=1,Type=String,Description=\"AMP/ASCO/CAP tier\">")
        vcf_lines.append("##INFO=<ID=CGC_VICC,Number=1,Type=String,Description=\"CGC/VICC oncogenicity\">")
        vcf_lines.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO")
        
        # Add variants
        for result in results:
            variant = result.get("variant")
            tier_result = result.get("tier_result")
            
            if variant:
                info_fields = []
                
                if variant.vrs_id:
                    info_fields.append(f"VRS_ID={variant.vrs_id}")
                    
                if tier_result:
                    if tier_result.amp_scoring:
                        info_fields.append(f"AMP_TIER={tier_result.amp_scoring.tier.value}")
                    if tier_result.cgc_vicc_oncogenicity:
                        info_fields.append(f"CGC_VICC={tier_result.cgc_vicc_oncogenicity.classification}")
                        
                vcf_line = "\t".join([
                    variant.chromosome,
                    str(variant.position),
                    ".",
                    variant.reference,
                    variant.alternate,
                    ".",
                    "PASS",
                    ";".join(info_fields) if info_fields else "."
                ])
                
                vcf_lines.append(vcf_line)
                
        return "\n".join(vcf_lines)
    
    def _export_as_tsv(self, results: List[Dict]) -> str:
        """Export as TSV with key annotations"""
        headers = [
            "VRS_ID", "Gene", "HGVS_p", "HGVS_c", "Consequence",
            "AMP_Tier", "CGC_VICC_Class", "OncoKB_Level",
            "Clinical_Significance", "Evidence_Count"
        ]
        
        rows = ["\t".join(headers)]
        
        for result in results:
            variant = result.get("variant")
            tier_result = result.get("tier_result")
            evidence = result.get("evidence", [])
            
            if variant:
                row = [
                    variant.vrs_id or "",
                    variant.gene_symbol or "",
                    variant.hgvs_p or "",
                    variant.hgvs_c or "",
                    variant.consequence or "",
                    tier_result.amp_scoring.tier.value if tier_result and tier_result.amp_scoring else "",
                    tier_result.cgc_vicc_oncogenicity.classification if tier_result and tier_result.cgc_vicc_oncogenicity else "",
                    tier_result.oncokb_scoring.therapeutic_level.value if tier_result and tier_result.oncokb_scoring else "",
                    self._get_clinical_significance(tier_result),
                    str(len(evidence))
                ]
                
                rows.append("\t".join(row))
                
        return "\n".join(rows)
    
    def _get_clinical_significance(self, tier_result: Optional[TierResult]) -> str:
        """Extract clinical significance from tier result"""
        if not tier_result:
            return ""
            
        significances = []
        
        if tier_result.amp_scoring:
            significances.append(f"AMP:{tier_result.amp_scoring.tier.value}")
            
        if tier_result.cgc_vicc_oncogenicity:
            significances.append(f"Onco:{tier_result.cgc_vicc_oncogenicity.classification}")
            
        return ";".join(significances)