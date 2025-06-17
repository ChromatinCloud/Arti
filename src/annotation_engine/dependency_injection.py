"""
Dependency Injection Container for Annotation Engine

Provides clean dependency injection patterns to eliminate complex manual mocking
in tests and improve code maintainability.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol
from pathlib import Path

from .models import (
    Evidence, VariantAnnotation, VICCScoring, OncoKBScoring, 
    DynamicSomaticConfidence, AnalysisType, AnnotationConfig
)


class EvidenceAggregatorInterface(Protocol):
    """Interface for evidence aggregation services"""
    
    def aggregate_evidence(self, variant_annotation: VariantAnnotation, 
                         cancer_type: str, analysis_type: AnalysisType) -> List[Evidence]:
        """Aggregate evidence from all knowledge bases"""
        ...
    
    def calculate_vicc_score(self, evidence_list: List[Evidence]) -> VICCScoring:
        """Calculate VICC/CGC 2022 oncogenicity scoring"""
        ...
    
    def calculate_oncokb_score(self, evidence_list: List[Evidence], 
                             oncokb_evidence: Optional[Dict[str, Any]] = None) -> OncoKBScoring:
        """Calculate OncoKB therapeutic scoring"""
        ...
    
    def calculate_dsc_score(self, variant_annotation: VariantAnnotation, 
                          evidence_list: List[Evidence], 
                          tumor_purity: Optional[float] = None) -> Optional[DynamicSomaticConfidence]:
        """Calculate Dynamic Somatic Confidence for tumor-only analysis"""
        ...


class WorkflowRouterInterface(Protocol):
    """Interface for workflow routing services"""
    
    def should_include_variant(self, variant_annotation: VariantAnnotation, 
                             analysis_type: AnalysisType) -> bool:
        """Determine if variant should be included in analysis"""
        ...


class CannedTextGeneratorInterface(Protocol):
    """Interface for canned text generation services"""
    
    def generate_gene_info_text(self, variant: VariantAnnotation, 
                              evidence_list: List[Evidence]) -> Optional[Any]:
        """Generate general gene information text"""
        ...
    
    def generate_variant_info_text(self, variant: VariantAnnotation, 
                                 evidence_list: List[Evidence]) -> Optional[Any]:
        """Generate general variant information text"""
        ...


class ScoringManagerInterface(Protocol):
    """Interface for evidence scoring services"""
    
    def calculate_evidence_score(self, evidence_list: List[Evidence], 
                               context: Any) -> float:
        """Calculate quantitative evidence score for a specific context"""
        ...
    
    def _is_evidence_relevant_to_context(self, evidence: Evidence, context: Any) -> bool:
        """Determine if evidence is relevant to a specific context"""
        ...


class DependencyContainer:
    """Dependency injection container for the annotation engine"""
    
    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
    
    def register_instance(self, name: str, instance: Any) -> None:
        """Register a singleton instance"""
        self._instances[name] = instance
    
    def register_factory(self, name: str, factory: callable) -> None:
        """Register a factory function for creating instances"""
        self._factories[name] = factory
    
    def get(self, name: str) -> Any:
        """Get an instance by name"""
        if name in self._instances:
            return self._instances[name]
        
        if name in self._factories:
            instance = self._factories[name]()
            self._instances[name] = instance  # Cache as singleton
            return instance
        
        raise KeyError(f"No registration found for '{name}'")
    
    def clear(self) -> None:
        """Clear all registrations (useful for testing)"""
        self._instances.clear()
        self._factories.clear()


class TieringEngineFactory:
    """Factory for creating properly configured TieringEngine instances"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
    
    def create_production_engine(self, config: Optional[AnnotationConfig] = None) -> 'TieringEngine':
        """Create a production TieringEngine with real dependencies"""
        from .tiering import TieringEngine
        from .evidence_aggregator import EvidenceAggregator
        from .tiering import CannedTextGenerator
        from .scoring_strategies import EvidenceScoringManager
        
        # Use provided config or create default
        if config is None:
            config = AnnotationConfig(kb_base_path=".refs")
        
        # Register real implementations
        self.container.register_factory(
            "evidence_aggregator", 
            lambda: EvidenceAggregator(config.kb_base_path, None)
        )
        self.container.register_factory(
            "text_generator",
            lambda: CannedTextGenerator()
        )
        self.container.register_factory(
            "scoring_manager",
            lambda: EvidenceScoringManager(config.evidence_weights)
        )
        
        # Create engine with dependencies
        return TieringEngine(
            config=config,
            evidence_aggregator=self.container.get("evidence_aggregator"),
            text_generator=self.container.get("text_generator"),
            scoring_manager=self.container.get("scoring_manager"),
            workflow_router=None
        )
    
    def create_test_engine(self, config: Optional[AnnotationConfig] = None,
                          evidence_aggregator: Optional[EvidenceAggregatorInterface] = None,
                          text_generator: Optional[CannedTextGeneratorInterface] = None,
                          scoring_manager: Optional[ScoringManagerInterface] = None,
                          workflow_router: Optional[WorkflowRouterInterface] = None) -> 'TieringEngine':
        """Create a test TieringEngine with injectable mock dependencies"""
        from .tiering import TieringEngine
        
        # Use provided config or create test config
        if config is None:
            config = AnnotationConfig(kb_base_path=".refs")
        
        # Use provided dependencies or create defaults
        if evidence_aggregator is not None:
            self.container.register_instance("evidence_aggregator", evidence_aggregator)
        if text_generator is not None:
            self.container.register_instance("text_generator", text_generator)
        if scoring_manager is not None:
            self.container.register_instance("scoring_manager", scoring_manager)
        if workflow_router is not None:
            self.container.register_instance("workflow_router", workflow_router)
        
        # Create engine with injected dependencies
        return TieringEngine(
            config=config,
            evidence_aggregator=self.container.get("evidence_aggregator") if evidence_aggregator else None,
            text_generator=self.container.get("text_generator") if text_generator else None,
            scoring_manager=self.container.get("scoring_manager") if scoring_manager else None,
            workflow_router=self.container.get("workflow_router") if workflow_router else None
        )


# Global dependency container (can be replaced for testing)
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container"""
    return _container


def create_tiering_engine_factory() -> TieringEngineFactory:
    """Create a new factory with fresh container"""
    container = DependencyContainer()
    return TieringEngineFactory(container)


def create_production_tiering_engine(config: Optional[AnnotationConfig] = None) -> 'TieringEngine':
    """Convenience function to create production TieringEngine"""
    factory = create_tiering_engine_factory()
    return factory.create_production_engine(config)


def create_test_tiering_engine(**kwargs) -> 'TieringEngine':
    """Convenience function to create test TieringEngine with injectable dependencies"""
    factory = create_tiering_engine_factory()
    return factory.create_test_engine(**kwargs)