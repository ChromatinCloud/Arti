"""
Workflow Router for Variant Annotation Pipeline (Person B Implementation)

Routes validated input from Person A through appropriate analysis pathways based on
analysis type (tumor-only vs tumor-normal) and cancer type. Implements the
WorkflowRouterProtocol interface for Person A ↔ Person B integration.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

from .models import AnalysisType
from .interfaces.workflow_interfaces import (
    WorkflowRouterProtocol,
    WorkflowContext,
    WorkflowRoute,
    WorkflowConfiguration,
    AnalysisType as InterfaceAnalysisType,
    EvidenceSource as InterfaceEvidenceSource,
    KnowledgeBasePriority
)
from .interfaces.validation_interfaces import ValidatedInput

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


class WorkflowRouter(WorkflowRouterProtocol):
    """
    Routes variants through appropriate analysis pathways
    
    Implements WorkflowRouterProtocol for Person A ↔ Person B integration
    """
    
    def __init__(self, 
                 analysis_type: Optional[AnalysisType] = None,
                 tumor_type: Optional[str] = None,
                 config_path: Optional[Path] = None):
        """
        Initialize workflow router
        
        Args:
            analysis_type: TUMOR_ONLY or TUMOR_NORMAL (optional for protocol interface)
            tumor_type: OncoTree code for tumor type  
            config_path: Optional path to custom config
        """
        self.analysis_type = analysis_type
        self.tumor_type = tumor_type
        self.config_path = config_path
        
        # Load pathway configuration if analysis type provided
        if analysis_type:
            self.pathway = self._load_pathway_config()
            logger.info(f"Initialized workflow router for {self.pathway.name} pathway")
            logger.debug(f"KB priorities: {[src.value for src in self.pathway.kb_priorities[:5]]}...")
        else:
            self.pathway = None
            logger.info("Initialized workflow router for dynamic routing")
    
    # Protocol interface methods (Person A ↔ Person B integration)
    
    def route(self, validated_input: ValidatedInput) -> WorkflowContext:
        """
        Main routing method that creates WorkflowContext
        
        This is the primary interface method that downstream components will use
        """
        try:
            logger.info(f"Routing workflow for case {validated_input.patient.case_id}")
            
            # 1. Determine analysis type
            analysis_type = self.determine_analysis_type(validated_input)
            
            # 2. Get workflow configuration
            config = self.get_workflow_configuration(
                analysis_type, 
                validated_input.patient.cancer_type
            )
            
            # 3. Build processing steps
            processing_steps = self._build_processing_steps(validated_input)
            
            # 4. Create workflow route
            route = WorkflowRoute(
                analysis_type=analysis_type,
                workflow_name=self._get_workflow_name(analysis_type, validated_input),
                configuration=config,
                processing_steps=processing_steps,
                filter_config=self._convert_to_filter_config(analysis_type),
                aggregator_config=self._convert_to_aggregator_config(),
                tiering_config=self._convert_to_tiering_config(),
                output_formats=validated_input.requested_outputs or ["json"]
            )
            
            # 5. Create workflow context
            context = WorkflowContext(
                validated_input=validated_input,
                route=route,
                execution_id=str(uuid.uuid4()),
                start_time=datetime.utcnow().isoformat()
            )
            
            logger.info(f"Workflow routed: {route.workflow_name} (execution_id: {context.execution_id})")
            return context
            
        except Exception as e:
            logger.error(f"Workflow routing failed: {e}")
            raise ValueError(f"Failed to route workflow: {str(e)}")
    
    def determine_analysis_type(self, validated_input: ValidatedInput) -> InterfaceAnalysisType:
        """Determine analysis type from validated input"""
        if validated_input.analysis_type == "tumor_normal":
            return InterfaceAnalysisType.TUMOR_NORMAL
        else:
            return InterfaceAnalysisType.TUMOR_ONLY
    
    def get_workflow_configuration(self, 
                                 analysis_type: InterfaceAnalysisType,
                                 cancer_type: str) -> WorkflowConfiguration:
        """Get workflow configuration for analysis type and cancer"""
        
        # Convert to internal analysis type and set up router
        internal_analysis_type = (AnalysisType.TUMOR_NORMAL if 
                                analysis_type == InterfaceAnalysisType.TUMOR_NORMAL 
                                else AnalysisType.TUMOR_ONLY)
        
        # Update internal state for pathway loading
        old_analysis_type = self.analysis_type
        old_tumor_type = self.tumor_type
        
        self.analysis_type = internal_analysis_type
        self.tumor_type = cancer_type
        self.pathway = self._load_pathway_config()
        
        # Convert internal pathway config to interface config
        kb_priorities = self._convert_kb_priorities(self.pathway.kb_priorities)
        
        config = WorkflowConfiguration(
            kb_priorities=kb_priorities,
            min_tumor_vaf=self.pathway.vaf_thresholds.get("min_tumor_vaf", 0.05),
            min_normal_vaf=self.pathway.vaf_thresholds.get("max_normal_vaf", 0.02),
            min_coverage=self.pathway.min_coverage,
            min_alt_reads=4,
            population_af_threshold=self.pathway.vaf_thresholds.get("max_population_af", 0.01),
            require_somatic_evidence=analysis_type == InterfaceAnalysisType.TUMOR_ONLY,
            penalize_germline_evidence=analysis_type == InterfaceAnalysisType.TUMOR_ONLY,
            boost_hotspot_variants=self.pathway.prioritize_hotspots,
            check_signatures=analysis_type == InterfaceAnalysisType.TUMOR_NORMAL,
            infer_clonality=analysis_type == InterfaceAnalysisType.TUMOR_NORMAL
        )
        
        # Restore original state
        self.analysis_type = old_analysis_type
        self.tumor_type = old_tumor_type
        
        return config
    
    def get_available_workflows(self) -> List[str]:
        """Get list of available workflow names"""
        return [
            "tumor_only_standard",
            "tumor_only_with_phenopacket",
            "tumor_only_with_va", 
            "tumor_normal_standard",
            "tumor_normal_with_phenopacket",
            "tumor_normal_with_va"
        ]
    
    def validate_workflow_config(self, config: WorkflowConfiguration) -> List[str]:
        """Validate a workflow configuration, return any issues"""
        issues = []
        
        if config.min_tumor_vaf <= 0 or config.min_tumor_vaf > 1:
            issues.append(f"Invalid tumor VAF threshold: {config.min_tumor_vaf}")
        
        if config.min_coverage < 10:
            issues.append(f"Minimum coverage too low: {config.min_coverage}")
        
        if not config.kb_priorities:
            issues.append("No knowledge base priorities configured")
        
        return issues
    
    # Helper methods for protocol interface
    
    def _convert_kb_priorities(self, internal_priorities: List[EvidenceSource]) -> List[KnowledgeBasePriority]:
        """Convert internal EvidenceSource priorities to interface KnowledgeBasePriority"""
        kb_priorities = []
        
        for priority in internal_priorities:
            # Map internal sources to interface sources
            interface_source = self._map_evidence_source(priority)
            if interface_source:
                weight = self.get_evidence_weight(priority)
                kb_priorities.append(KnowledgeBasePriority(
                    source=interface_source,
                    weight=weight,
                    enabled=True
                ))
        
        return kb_priorities
    
    def _map_evidence_source(self, internal_source: EvidenceSource) -> Optional[InterfaceEvidenceSource]:
        """Map internal EvidenceSource to interface EvidenceSource"""
        mapping = {
            EvidenceSource.ONCOKB: InterfaceEvidenceSource.ONCOKB,
            EvidenceSource.CIVIC: InterfaceEvidenceSource.CIVIC,
            EvidenceSource.COSMIC_HOTSPOT: InterfaceEvidenceSource.COSMIC,
            EvidenceSource.MSK_HOTSPOT: InterfaceEvidenceSource.MSK_HOTSPOTS,
            EvidenceSource.CLINVAR: InterfaceEvidenceSource.CLINVAR,
            EvidenceSource.GNOMAD: InterfaceEvidenceSource.GNOMAD,
        }
        return mapping.get(internal_source)
    
    def _build_processing_steps(self, validated_input: ValidatedInput) -> List[str]:
        """Build ordered processing steps based on input"""
        steps = ["vep"]
        
        if validated_input.analysis_type == "tumor_normal":
            steps.append("somatic_calling")
        
        steps.extend(["evidence_aggregation", "tiering"])
        
        if validated_input.export_phenopacket:
            steps.append("phenopacket_export")
        
        if validated_input.export_va:
            steps.append("va_export")
        
        if validated_input.vrs_normalize:
            steps.append("vrs_normalization")
        
        steps.append("canned_text_generation")
        
        return steps
    
    def _get_workflow_name(self, analysis_type: InterfaceAnalysisType, validated_input: ValidatedInput) -> str:
        """Generate workflow name based on analysis type and outputs"""
        base_name = analysis_type.value
        
        if validated_input.export_phenopacket:
            return f"{base_name}_with_phenopacket"
        elif validated_input.export_va:
            return f"{base_name}_with_va"
        else:
            return f"{base_name}_standard"
    
    def _convert_to_filter_config(self, analysis_type: InterfaceAnalysisType) -> Dict[str, Any]:
        """Convert pathway config to filter config"""
        if not self.pathway:
            return {}
        
        return {
            "min_depth": self.pathway.min_coverage,
            "min_tumor_vaf": self.pathway.vaf_thresholds.get("min_tumor_vaf", 0.05),
            "use_population_filtering": self.pathway.use_population_filtering,
            "use_germline_filtering": self.pathway.use_germline_filtering
        }
    
    def _convert_to_aggregator_config(self) -> Dict[str, Any]:
        """Convert pathway config to aggregator config"""
        if not self.pathway:
            return {}
        
        return {
            "prioritize_therapeutic": self.pathway.prioritize_therapeutic,
            "prioritize_hotspots": self.pathway.prioritize_hotspots
        }
    
    def _convert_to_tiering_config(self) -> Dict[str, Any]:
        """Convert pathway config to tiering config"""
        return {
            "amp_guidelines": True,
            "vicc_guidelines": True,
            "oncokb_levels": True
        }
    
    # Original pathway methods (for backward compatibility)
    
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