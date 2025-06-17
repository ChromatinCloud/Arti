"""
Database module for Clinical Variant Annotation Engine

Provides SQLAlchemy-based database models and session management
for storing clinical interpretations, audit trails, and metadata.
"""

from .base import Base, get_session, init_db
from .models import (
    Patient,
    Case, 
    VariantAnalysis,
    Variant,
    TieringResult,
    CannedInterpretation,
    VariantInterpretation,
    AuditLog,
    GuidelineFramework,
    ConfidenceLevel
)

__all__ = [
    "Base",
    "get_session", 
    "init_db",
    "Patient",
    "Case",
    "VariantAnalysis", 
    "Variant",
    "TieringResult",
    "CannedInterpretation",
    "VariantInterpretation",
    "AuditLog",
    "GuidelineFramework",
    "ConfidenceLevel"
]