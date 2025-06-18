"""
VICC Meta-Knowledgebase Integration

Integrates with the Variant Interpretation for Cancer Consortium (VICC)
meta-knowledgebase using GA4GH VRS identifiers.

Provides access to harmonized interpretations from:
- OncoKB
- CIViC  
- JAX Clinical Knowledgebase
- CGI (Cancer Genome Interpreter)
- Molecular Match
- PMKB (Precision Medicine Knowledgebase)
"""

import requests
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum

from ..models import Evidence, VariantAnnotation
from .vrs_handler import VRSHandler

logger = logging.getLogger(__name__)


class VICCEvidenceLevel(str, Enum):
    """VICC harmonized evidence levels"""
    LEVEL_1A = "1A"  # FDA-approved therapy
    LEVEL_1B = "1B"  # Professional guideline
    LEVEL_2A = "2A"  # FDA-approved (different context)
    LEVEL_2B = "2B"  # Professional guideline (different context)
    LEVEL_3A = "3A"  # Clinical evidence
    LEVEL_3B = "3B"  # Pre-clinical evidence
    LEVEL_4 = "4"    # Biological evidence
    
    
@dataclass
class VICCAssociation:
    """Represents a VICC association (variant-evidence link)"""
    id: str
    source: str  # OncoKB, CIViC, etc.
    variant: Dict
    disease: Optional[Dict]
    therapy: Optional[Dict]
    evidence_level: Optional[str]
    evidence_type: str  # therapeutic, diagnostic, prognostic
    evidence_direction: str  # supports, does_not_support
    description: str
    publications: List[str]
    
    
class VICCMetaKnowledgebaseClient:
    """
    Client for querying VICC Meta-Knowledgebase
    
    Leverages VRS IDs for cross-database variant matching
    """
    
    BASE_URL = "https://search.cancervariants.org/api/v1"
    
    def __init__(self, vrs_handler: Optional[VRSHandler] = None):
        self.vrs_handler = vrs_handler or VRSHandler()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AnnotationEngine/1.0"
        })
        
    def search_by_vrs_id(self, vrs_id: str, 
                        size: int = 10,
                        include_sources: Optional[List[str]] = None) -> List[VICCAssociation]:
        """
        Search VICC by VRS identifier
        
        Args:
            vrs_id: GA4GH VRS computed identifier
            size: Maximum number of results
            include_sources: Filter by sources (e.g., ['oncokb', 'civic'])
            
        Returns:
            List of VICC associations
        """
        params = {
            "q": vrs_id,
            "size": size
        }
        
        if include_sources:
            params["sources"] = ",".join(include_sources)
            
        try:
            response = self.session.get(
                f"{self.BASE_URL}/associations",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            associations = []
            
            for item in data.get("associations", []):
                association = self._parse_association(item)
                if association:
                    associations.append(association)
                    
            logger.info(f"Found {len(associations)} associations for {vrs_id}")
            return associations
            
        except Exception as e:
            logger.error(f"VICC query failed for {vrs_id}: {e}")
            return []
    
    def search_by_variant(self, variant: VariantAnnotation,
                         cancer_type: Optional[str] = None) -> List[VICCAssociation]:
        """
        Search VICC using variant annotation
        
        First generates VRS ID, then queries
        """
        # Get or generate VRS ID
        if not variant.vrs_id:
            vrs_id = self.vrs_handler.get_vrs_id(variant)
        else:
            vrs_id = variant.vrs_id
            
        associations = self.search_by_vrs_id(vrs_id)
        
        # Filter by cancer type if provided
        if cancer_type and associations:
            filtered = []
            for assoc in associations:
                if assoc.disease and self._matches_cancer_type(
                    assoc.disease, cancer_type
                ):
                    filtered.append(assoc)
            associations = filtered
            
        return associations
    
    def get_harmonized_evidence(self, 
                              variant: VariantAnnotation,
                              cancer_type: Optional[str] = None) -> List[Evidence]:
        """
        Get harmonized evidence from VICC as Evidence objects
        
        Converts VICC associations to standard Evidence format
        """
        associations = self.search_by_variant(variant, cancer_type)
        evidence_list = []
        
        for assoc in associations:
            evidence = self._association_to_evidence(assoc, variant)
            if evidence:
                evidence_list.append(evidence)
                
        # Deduplicate by source and evidence type
        unique_evidence = self._deduplicate_evidence(evidence_list)
        
        return unique_evidence
    
    def _parse_association(self, data: Dict) -> Optional[VICCAssociation]:
        """Parse VICC API response into Association object"""
        try:
            return VICCAssociation(
                id=data.get("id", ""),
                source=data.get("source", ""),
                variant=data.get("variant", {}),
                disease=data.get("disease"),
                therapy=data.get("therapy"),
                evidence_level=data.get("evidence_level"),
                evidence_type=data.get("evidence_type", ""),
                evidence_direction=data.get("evidence_direction", "supports"),
                description=data.get("description", ""),
                publications=data.get("publications", [])
            )
        except Exception as e:
            logger.error(f"Failed to parse association: {e}")
            return None
    
    def _association_to_evidence(self, 
                               assoc: VICCAssociation,
                               variant: VariantAnnotation) -> Optional[Evidence]:
        """Convert VICC association to Evidence object"""
        # Map VICC evidence levels to scores
        level_scores = {
            "1A": 10, "1B": 9,
            "2A": 8, "2B": 7,
            "3A": 6, "3B": 5,
            "4": 4
        }
        
        score = level_scores.get(assoc.evidence_level, 3)
        
        # Map evidence type to code
        code_map = {
            ("therapeutic", "oncokb"): "ONCOKB_THERAPEUTIC",
            ("therapeutic", "civic"): "CIVIC_THERAPEUTIC",
            ("diagnostic", "oncokb"): "ONCOKB_DIAGNOSTIC",
            ("prognostic", "civic"): "CIVIC_PROGNOSTIC"
        }
        
        code = code_map.get(
            (assoc.evidence_type.lower(), assoc.source.lower()),
            f"VICC_{assoc.evidence_type.upper()}"
        )
        
        # Build description
        description_parts = [assoc.description]
        if assoc.therapy:
            description_parts.append(f"Therapy: {assoc.therapy.get('name', 'Unknown')}")
        if assoc.disease:
            description_parts.append(f"Disease: {assoc.disease.get('name', 'Unknown')}")
            
        return Evidence(
            code=code,
            score=score,
            guideline="VICC Meta-KB",
            source_kb=f"VICC_{assoc.source.upper()}",
            description=" | ".join(description_parts),
            evidence_type=assoc.evidence_type.upper(),
            confidence=0.9 if assoc.evidence_level in ["1A", "1B"] else 0.7,
            metadata={
                "vicc_id": assoc.id,
                "evidence_level": assoc.evidence_level,
                "publications": assoc.publications,
                "vrs_id": variant.vrs_id
            }
        )
    
    def _matches_cancer_type(self, disease: Dict, cancer_type: str) -> bool:
        """Check if disease matches cancer type"""
        disease_name = disease.get("name", "").lower()
        cancer_type_lower = cancer_type.lower()
        
        # Direct match
        if cancer_type_lower in disease_name:
            return True
            
        # OncoTree mapping would go here
        oncotree_map = {
            "melanoma": ["skin melanoma", "cutaneous melanoma"],
            "lung adenocarcinoma": ["luad", "lung adenocarcinoma", "nsclc"],
            "breast cancer": ["breast", "brca"]
        }
        
        if cancer_type_lower in oncotree_map:
            for term in oncotree_map[cancer_type_lower]:
                if term in disease_name:
                    return True
                    
        return False
    
    def _deduplicate_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """Remove duplicate evidence, keeping highest scoring"""
        unique_map = {}
        
        for evidence in evidence_list:
            key = (evidence.source_kb, evidence.evidence_type, evidence.code)
            
            if key not in unique_map or evidence.score > unique_map[key].score:
                unique_map[key] = evidence
                
        return list(unique_map.values())
    
    def get_sources_summary(self, variant: VariantAnnotation) -> Dict[str, int]:
        """
        Get summary of evidence by source
        
        Returns count of evidence items per source database
        """
        associations = self.search_by_variant(variant)
        
        source_counts = {}
        for assoc in associations:
            source = assoc.source
            source_counts[source] = source_counts.get(source, 0) + 1
            
        return source_counts
    
    def get_cross_database_concordance(self, 
                                     variant: VariantAnnotation,
                                     evidence_type: str = "therapeutic") -> Dict:
        """
        Analyze concordance across databases for a variant
        
        Returns concordance metrics and conflicting interpretations
        """
        associations = self.search_by_variant(variant)
        
        # Filter by evidence type
        filtered = [a for a in associations if a.evidence_type == evidence_type]
        
        # Group by evidence level
        level_by_source = {}
        for assoc in filtered:
            if assoc.source not in level_by_source:
                level_by_source[assoc.source] = []
            level_by_source[assoc.source].append(assoc.evidence_level)
            
        # Calculate concordance
        all_levels = []
        for levels in level_by_source.values():
            all_levels.extend(levels)
            
        unique_levels = set(all_levels)
        concordance = 1.0 if len(unique_levels) == 1 else len(unique_levels) / len(level_by_source)
        
        return {
            "sources": list(level_by_source.keys()),
            "levels_by_source": level_by_source,
            "unique_levels": list(unique_levels),
            "concordance_score": concordance,
            "is_concordant": len(unique_levels) == 1,
            "total_interpretations": len(filtered)
        }