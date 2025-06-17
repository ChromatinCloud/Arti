"""
Workflow Router for Variant Annotation Pipeline

Routes variants through appropriate analysis pathways based on sample type
(tumor-only vs tumor-normal) and configures knowledge base priorities,
evidence weights, and VAF thresholds accordingly.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

from .models import AnalysisType

logger = logging.getLogger(__name__)


class EvidenceSource(str, Enum):
    """Evidence source types for prioritization"""
    # Tier I/II sources (highest priority)
    ONCOKB = "OncoKB"
    CIVIC = "CIViC"
    COSMIC_TIER1 = "COSMIC_Tier1"
    FDA_APPROVED = "FDA_Approved"
    NCCN_GUIDELINE = "NCCN_Guideline"
    
    # Tier III sources (moderate priority)
    COSMIC_HOTSPOT = "COSMIC_Hotspot"
    MSK_HOTSPOT = "MSK_Hotspot"
    CANCERMINE = "CancerMine"
    CGI = "CGI"
    PMKB = "PMKB"
    
    # Tier IV sources (supportive)
    GNOMAD = "gnomAD"
    CLINVAR = "ClinVar"
    DBSNP = "dbSNP"
    
    # Computational predictions
    ALPHAMISSENSE = "AlphaMissense"
    REVEL = "REVEL"
    SPLICEAI = "SpliceAI"
    POLYPHEN = "PolyPhen"
    SIFT = "SIFT"
    
    # Conservation/constraint
    GERP = "GERP"
    PHYLOP = "PhyloP"
    LOFTOOL = "LoFtool"
    
    # Other
    VEP_CONSEQUENCE = "VEP_Consequence"
    LITERATURE = "Literature"


@dataclass
class PathwayConfig:
    """Configuration for a specific analysis pathway"""
    name: str
    analysis_type: AnalysisType
    kb_priorities: List[EvidenceSource]
    evidence_weights: Dict[EvidenceSource, float]
    vaf_thresholds: Dict[str, float]
    min_coverage: int
    require_normal_comparison: bool
    
    # Pathway-specific flags
    use_population_filtering: bool
    use_germline_filtering: bool
    prioritize_therapeutic: bool
    prioritize_hotspots: bool


class WorkflowRouter:
    """Routes variants through appropriate analysis pathways"""
    
    def __init__(self, 
                 analysis_type: AnalysisType,
                 tumor_type: Optional[str] = None,
                 config_path: Optional[Path] = None):
        """
        Initialize workflow router
        
        Args:
            analysis_type: TUMOR_ONLY or TUMOR_NORMAL
            tumor_type: OncoTree code for tumor type
            config_path: Optional path to custom config
        """
        self.analysis_type = analysis_type
        self.tumor_type = tumor_type
        self.config_path = config_path
        
        # Load pathway configuration
        self.pathway = self._load_pathway_config()
        
        logger.info(f"Initialized workflow router for {self.pathway.name} pathway")
        logger.debug(f"KB priorities: {[src.value for src in self.pathway.kb_priorities[:5]]}...")
    
    def _load_pathway_config(self) -> PathwayConfig:
        """Load configuration for the selected pathway"""
        
        if self.analysis_type == AnalysisType.TUMOR_NORMAL:
            return self._get_tumor_normal_config()
        else:
            return self._get_tumor_only_config()
    
    def _get_tumor_normal_config(self) -> PathwayConfig:
        """Configuration for tumor-normal analysis"""
        
        # Prioritize clinical databases and de-emphasize population databases
        kb_priorities = [
            # Tier I/II evidence (highest priority)
            EvidenceSource.ONCOKB,
            EvidenceSource.FDA_APPROVED,
            EvidenceSource.CIVIC,
            EvidenceSource.NCCN_GUIDELINE,
            EvidenceSource.COSMIC_TIER1,
            
            # Hotspots (high priority for somatic)
            EvidenceSource.COSMIC_HOTSPOT,
            EvidenceSource.MSK_HOTSPOT,
            
            # Other clinical sources
            EvidenceSource.CGI,
            EvidenceSource.PMKB,
            EvidenceSource.CANCERMINE,
            
            # Computational (moderate priority)
            EvidenceSource.ALPHAMISSENSE,
            EvidenceSource.REVEL,
            EvidenceSource.SPLICEAI,
            
            # Population (low priority - germline filtering)
            EvidenceSource.GNOMAD,
            EvidenceSource.CLINVAR,
            EvidenceSource.DBSNP,
            
            # Conservation (supportive)
            EvidenceSource.GERP,
            EvidenceSource.PHYLOP,
            EvidenceSource.LOFTOOL,
            
            # Other
            EvidenceSource.VEP_CONSEQUENCE,
            EvidenceSource.LITERATURE,
        ]
        
        # Higher weights for clinical evidence in tumor-normal
        evidence_weights = {
            # Clinical databases (highest weight)
            EvidenceSource.ONCOKB: 1.0,
            EvidenceSource.FDA_APPROVED: 1.0,
            EvidenceSource.CIVIC: 0.9,
            EvidenceSource.NCCN_GUIDELINE: 0.95,
            EvidenceSource.COSMIC_TIER1: 0.9,
            
            # Hotspots (high weight for somatic)
            EvidenceSource.COSMIC_HOTSPOT: 0.85,
            EvidenceSource.MSK_HOTSPOT: 0.85,
            
            # Other clinical
            EvidenceSource.CGI: 0.7,
            EvidenceSource.PMKB: 0.7,
            EvidenceSource.CANCERMINE: 0.6,
            
            # Computational (moderate)
            EvidenceSource.ALPHAMISSENSE: 0.5,
            EvidenceSource.REVEL: 0.5,
            EvidenceSource.SPLICEAI: 0.6,
            EvidenceSource.POLYPHEN: 0.4,
            EvidenceSource.SIFT: 0.4,
            
            # Population (low - for filtering)
            EvidenceSource.GNOMAD: 0.2,
            EvidenceSource.CLINVAR: 0.3,
            EvidenceSource.DBSNP: 0.1,
            
            # Conservation
            EvidenceSource.GERP: 0.3,
            EvidenceSource.PHYLOP: 0.3,
            EvidenceSource.LOFTOOL: 0.4,
            
            # Other
            EvidenceSource.VEP_CONSEQUENCE: 0.5,
            EvidenceSource.LITERATURE: 0.6,
        }
        
        # Tumor-normal specific thresholds
        vaf_thresholds = {
            "min_tumor_vaf": 0.05,      # 5% minimum in tumor
            "max_normal_vaf": 0.02,      # 2% maximum in normal
            "min_vaf_ratio": 5.0,        # Tumor/normal ratio
            "subclonal_threshold": 0.25,  # <25% VAF considered subclonal
            "clonal_threshold": 0.40,     # >40% VAF considered clonal
        }
        
        return PathwayConfig(
            name="Tumor-Normal Somatic",
            analysis_type=AnalysisType.TUMOR_NORMAL,
            kb_priorities=kb_priorities,
            evidence_weights=evidence_weights,
            vaf_thresholds=vaf_thresholds,
            min_coverage=50,
            require_normal_comparison=True,
            use_population_filtering=True,
            use_germline_filtering=True,
            prioritize_therapeutic=True,
            prioritize_hotspots=True
        )
    
    def _get_tumor_only_config(self) -> PathwayConfig:
        """Configuration for tumor-only analysis"""
        
        # Different priorities for tumor-only (more reliance on databases)
        kb_priorities = [
            # Clinical evidence (still highest)
            EvidenceSource.ONCOKB,
            EvidenceSource.FDA_APPROVED,
            EvidenceSource.CIVIC,
            EvidenceSource.NCCN_GUIDELINE,
            EvidenceSource.COSMIC_TIER1,
            
            # Population databases (higher priority for filtering)
            EvidenceSource.GNOMAD,
            EvidenceSource.CLINVAR,
            EvidenceSource.DBSNP,
            
            # Hotspots
            EvidenceSource.COSMIC_HOTSPOT,
            EvidenceSource.MSK_HOTSPOT,
            
            # Other clinical
            EvidenceSource.CGI,
            EvidenceSource.PMKB,
            EvidenceSource.CANCERMINE,
            
            # Computational (important for tumor-only)
            EvidenceSource.ALPHAMISSENSE,
            EvidenceSource.REVEL,
            EvidenceSource.SPLICEAI,
            EvidenceSource.POLYPHEN,
            EvidenceSource.SIFT,
            
            # Conservation (more important without normal)
            EvidenceSource.GERP,
            EvidenceSource.PHYLOP,
            EvidenceSource.LOFTOOL,
            
            # Other
            EvidenceSource.VEP_CONSEQUENCE,
            EvidenceSource.LITERATURE,
        ]
        
        # Adjusted weights for tumor-only
        evidence_weights = {
            # Clinical databases
            EvidenceSource.ONCOKB: 1.0,
            EvidenceSource.FDA_APPROVED: 1.0,
            EvidenceSource.CIVIC: 0.9,
            EvidenceSource.NCCN_GUIDELINE: 0.95,
            EvidenceSource.COSMIC_TIER1: 0.9,
            
            # Population (higher weight for filtering)
            EvidenceSource.GNOMAD: 0.7,  # Much higher for tumor-only
            EvidenceSource.CLINVAR: 0.6,
            EvidenceSource.DBSNP: 0.5,
            
            # Hotspots
            EvidenceSource.COSMIC_HOTSPOT: 0.8,
            EvidenceSource.MSK_HOTSPOT: 0.8,
            
            # Other clinical
            EvidenceSource.CGI: 0.7,
            EvidenceSource.PMKB: 0.7,
            EvidenceSource.CANCERMINE: 0.6,
            
            # Computational (more important)
            EvidenceSource.ALPHAMISSENSE: 0.6,
            EvidenceSource.REVEL: 0.6,
            EvidenceSource.SPLICEAI: 0.7,
            EvidenceSource.POLYPHEN: 0.5,
            EvidenceSource.SIFT: 0.5,
            
            # Conservation (more weight)
            EvidenceSource.GERP: 0.5,
            EvidenceSource.PHYLOP: 0.5,
            EvidenceSource.LOFTOOL: 0.6,
            
            # Other
            EvidenceSource.VEP_CONSEQUENCE: 0.6,
            EvidenceSource.LITERATURE: 0.7,
        }
        
        # Tumor-only specific thresholds (more conservative)
        vaf_thresholds = {
            "min_tumor_vaf": 0.10,        # 10% minimum (higher than T/N)
            "max_population_af": 0.001,    # 0.1% max population frequency
            "cancer_hotspot_min_vaf": 0.05, # Lower threshold for hotspots
            "subclonal_threshold": 0.20,   # <20% VAF considered subclonal
            "clonal_threshold": 0.35,      # >35% VAF considered clonal
        }
        
        return PathwayConfig(
            name="Tumor-Only Somatic",
            analysis_type=AnalysisType.TUMOR_ONLY,
            kb_priorities=kb_priorities,
            evidence_weights=evidence_weights,
            vaf_thresholds=vaf_thresholds,
            min_coverage=100,  # Higher coverage requirement
            require_normal_comparison=False,
            use_population_filtering=True,
            use_germline_filtering=True,
            prioritize_therapeutic=True,
            prioritize_hotspots=True
        )
    
    def get_kb_priority_order(self) -> List[EvidenceSource]:
        """Get ordered list of KB priorities for this pathway"""
        return self.pathway.kb_priorities
    
    def get_evidence_weight(self, source: EvidenceSource) -> float:
        """Get weight multiplier for evidence from a specific source"""
        return self.pathway.evidence_weights.get(source, 0.5)
    
    def get_vaf_threshold(self, threshold_type: str) -> float:
        """Get VAF threshold for a specific check"""
        return self.pathway.vaf_thresholds.get(threshold_type, 0.0)
    
    def should_filter_variant(self, 
                            tumor_vaf: float,
                            normal_vaf: Optional[float] = None,
                            population_af: Optional[float] = None,
                            is_hotspot: bool = False) -> bool:
        """
        Determine if variant should be filtered based on pathway rules
        
        Args:
            tumor_vaf: Variant allele frequency in tumor
            normal_vaf: VAF in normal (if available)
            population_af: Population allele frequency
            is_hotspot: Whether variant is in cancer hotspot
            
        Returns:
            True if variant should be filtered out
        """
        
        # Check minimum tumor VAF
        min_vaf = self.get_vaf_threshold("min_tumor_vaf")
        if is_hotspot:
            min_vaf = self.get_vaf_threshold("cancer_hotspot_min_vaf")
        
        if tumor_vaf < min_vaf:
            logger.debug(f"Filtering variant with tumor VAF {tumor_vaf} < {min_vaf}")
            return True
        
        # Tumor-normal specific filtering
        if self.pathway.analysis_type == AnalysisType.TUMOR_NORMAL and normal_vaf is not None:
            max_normal = self.get_vaf_threshold("max_normal_vaf")
            if normal_vaf > max_normal:
                logger.debug(f"Filtering variant with normal VAF {normal_vaf} > {max_normal}")
                return True
            
            # Check tumor/normal ratio
            if normal_vaf > 0:
                ratio = tumor_vaf / normal_vaf
                min_ratio = self.get_vaf_threshold("min_vaf_ratio")
                if ratio < min_ratio:
                    logger.debug(f"Filtering variant with T/N ratio {ratio} < {min_ratio}")
                    return True
        
        # Population frequency filtering (more strict for tumor-only)
        if population_af is not None and self.pathway.use_population_filtering:
            if self.pathway.analysis_type == AnalysisType.TUMOR_ONLY:
                max_pop_af = self.get_vaf_threshold("max_population_af")
                if population_af > max_pop_af and not is_hotspot:
                    logger.debug(f"Filtering variant with population AF {population_af} > {max_pop_af}")
                    return True
        
        return False
    
    def classify_vaf_clonality(self, vaf: float) -> str:
        """
        Classify variant clonality based on VAF
        
        Args:
            vaf: Variant allele frequency
            
        Returns:
            "clonal", "subclonal", or "indeterminate"
        """
        subclonal_threshold = self.get_vaf_threshold("subclonal_threshold")
        clonal_threshold = self.get_vaf_threshold("clonal_threshold")
        
        if vaf >= clonal_threshold:
            return "clonal"
        elif vaf <= subclonal_threshold:
            return "subclonal"
        else:
            return "indeterminate"
    
    def adjust_evidence_scores(self, evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Adjust evidence scores based on pathway-specific weights
        
        Args:
            evidence_list: List of evidence items with 'source' and 'score' fields
            
        Returns:
            Evidence list with adjusted scores
        """
        adjusted_evidence = []
        
        for evidence in evidence_list:
            evidence_copy = evidence.copy()
            source = evidence.get("source_kb", "").upper()
            
            # Find matching evidence source
            weight = 0.5  # Default weight
            for evidence_source in EvidenceSource:
                if source in evidence_source.value.upper():
                    weight = self.get_evidence_weight(evidence_source)
                    break
            
            # Adjust score if present
            if "score" in evidence_copy:
                original_score = evidence_copy["score"]
                evidence_copy["adjusted_score"] = original_score * weight
                evidence_copy["pathway_weight"] = weight
            
            adjusted_evidence.append(evidence_copy)
        
        return adjusted_evidence
    
    def get_pathway_summary(self) -> Dict[str, Any]:
        """Get summary of current pathway configuration"""
        return {
            "pathway_name": self.pathway.name,
            "analysis_type": self.pathway.analysis_type.value,
            "tumor_type": self.tumor_type,
            "min_coverage": self.pathway.min_coverage,
            "vaf_thresholds": self.pathway.vaf_thresholds,
            "top_5_kb_priorities": [src.value for src in self.pathway.kb_priorities[:5]],
            "flags": {
                "use_population_filtering": self.pathway.use_population_filtering,
                "use_germline_filtering": self.pathway.use_germline_filtering,
                "prioritize_therapeutic": self.pathway.prioritize_therapeutic,
                "prioritize_hotspots": self.pathway.prioritize_hotspots,
            }
        }


def create_workflow_router(analysis_type: AnalysisType,
                          tumor_type: Optional[str] = None) -> WorkflowRouter:
    """
    Factory function to create appropriate workflow router
    
    Args:
        analysis_type: TUMOR_ONLY or TUMOR_NORMAL
        tumor_type: OncoTree code for tumor type
        
    Returns:
        Configured WorkflowRouter instance
    """
    return WorkflowRouter(analysis_type, tumor_type)