"""
Annotation Engine - Clinical Variant Annotation Pipeline

A comprehensive clinical variant annotation engine following AMP/ASCO/CAP 2017,
VICC 2022, and OncoKB guidelines for somatic variant interpretation.
"""

__version__ = "0.1.0"
__author__ = "Annotation Engine Team"

from .models import AnalysisType, VariantAnnotation, TierResult
from .evidence_aggregator import EvidenceAggregator
from .tiering import TieringEngine
from .vep_runner import VEPRunner, VEPConfiguration

__all__ = [
    "AnalysisType",
    "VariantAnnotation", 
    "TierResult",
    "EvidenceAggregator",
    "TieringEngine",
    "VEPRunner",
    "VEPConfiguration",
]