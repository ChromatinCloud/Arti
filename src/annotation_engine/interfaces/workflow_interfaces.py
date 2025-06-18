"""
Workflow Routing Interfaces

Defines the contract for workflow routing that Person B will implement.
"""

from typing import Protocol, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .validation_interfaces import ValidatedInput


class AnalysisType(str, Enum):
    """Types of analysis workflows"""
    TUMOR_ONLY = "tumor_only"
    TUMOR_NORMAL = "tumor_normal"
    

class EvidenceSource(str, Enum):
    """Knowledge base sources"""
    ONCOKB = "oncokb"
    CIVIC = "civic"
    CLINVAR = "clinvar"
    COSMIC = "cosmic"
    GNOMAD = "gnomad"
    MSK_HOTSPOTS = "msk_hotspots"
    CGC = "cgc"
    VICC = "vicc"
    

@dataclass
class KnowledgeBasePriority:
    """Priority configuration for a knowledge base"""
    source: EvidenceSource
    weight: float = 1.0  # Evidence weight multiplier
    enabled: bool = True
    min_evidence_level: Optional[str] = None
    

@dataclass
class WorkflowConfiguration:
    """Configuration for a specific workflow"""
    # Knowledge base priorities (ordered)
    kb_priorities: List[KnowledgeBasePriority]
    
    # VAF thresholds
    min_tumor_vaf: float = 0.05
    min_normal_vaf: float = 0.02  # For filtering germline
    
    # Evidence weights
    evidence_weight_multipliers: Dict[str, float] = field(default_factory=dict)
    
    # Filtering parameters
    min_coverage: int = 20
    min_alt_reads: int = 4
    population_af_threshold: float = 0.01
    
    # Tiering adjustments
    require_somatic_evidence: bool = True
    penalize_germline_evidence: bool = True
    boost_hotspot_variants: bool = True
    
    # Special handling
    check_signatures: bool = False
    infer_clonality: bool = False
    

@dataclass
class WorkflowRoute:
    """
    Result of workflow routing - contains all configuration needed
    for downstream processing
    """
    # Basic info
    analysis_type: AnalysisType
    workflow_name: str
    
    # Configuration
    configuration: WorkflowConfiguration
    
    # Processing instructions
    processing_steps: List[str]  # Ordered list of steps to execute
    
    # Component configurations
    filter_config: Dict[str, Any]
    aggregator_config: Dict[str, Any]
    tiering_config: Dict[str, Any]
    
    # Output configurations
    output_formats: List[str]
    include_filtered_variants: bool = False
    include_germline_findings: bool = False
    

@dataclass
class WorkflowContext:
    """
    Runtime context for workflow execution
    
    This gets passed through the entire pipeline
    """
    # Input data
    validated_input: ValidatedInput
    
    # Routing decision
    route: WorkflowRoute
    
    # Runtime state
    execution_id: str
    start_time: str
    
    # Tracking
    processed_variants: int = 0
    filtered_variants: int = 0
    tiered_variants: int = 0
    
    # Caching hints
    enable_caching: bool = True
    cache_namespace: Optional[str] = None
    
    def get_kb_weight(self, source: EvidenceSource) -> float:
        """Get weight multiplier for a knowledge base"""
        for kb in self.route.configuration.kb_priorities:
            if kb.source == source:
                return kb.weight if kb.enabled else 0.0
        return 0.0
    
    def is_kb_enabled(self, source: EvidenceSource) -> bool:
        """Check if a knowledge base is enabled"""
        for kb in self.route.configuration.kb_priorities:
            if kb.source == source:
                return kb.enabled
        return False


class WorkflowRouterProtocol(Protocol):
    """
    Protocol that Person B's WorkflowRouter must implement
    
    This defines the interface without implementation details
    """
    
    def determine_analysis_type(self, validated_input: ValidatedInput) -> AnalysisType:
        """Determine the analysis type from validated input"""
        ...
    
    def get_workflow_configuration(self, 
                                 analysis_type: AnalysisType,
                                 cancer_type: str) -> WorkflowConfiguration:
        """Get workflow configuration for analysis type and cancer"""
        ...
    
    def route(self, validated_input: ValidatedInput) -> WorkflowContext:
        """
        Main routing method that creates WorkflowContext
        
        This is the primary interface method that downstream components will use
        """
        ...
    
    def get_available_workflows(self) -> List[str]:
        """Get list of available workflow names"""
        ...
    
    def validate_workflow_config(self, config: WorkflowConfiguration) -> List[str]:
        """Validate a workflow configuration, return any issues"""
        ...