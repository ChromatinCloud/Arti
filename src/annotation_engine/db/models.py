"""
SQLAlchemy database models for Clinical Variant Annotation Engine

Implements the complete database schema as defined in INTERP_DB_BLUEPRINT.md
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Text, JSON, Boolean,
    Numeric, ForeignKey, Index, UniqueConstraint, text
)
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base
import uuid


class GuidelineFramework(str, Enum):
    """Supported clinical guideline frameworks"""
    AMP_ACMG = "AMP_ACMG"
    CGC_VICC = "CGC_VICC" 
    ONCOKB = "ONCOKB"


class ConfidenceLevel(str, Enum):
    """Confidence levels for interpretations"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AuditAction(str, Enum):
    """Audit log action types"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SELECT = "SELECT"


class Patient(Base):
    """Patient information table"""
    __tablename__ = "patients"
    
    patient_uid = Column(String(255), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cases = relationship("Case", back_populates="patient")


class Case(Base):
    """Clinical case information"""
    __tablename__ = "cases"
    
    case_uid = Column(String(255), primary_key=True)
    patient_uid = Column(String(255), ForeignKey("patients.patient_uid"), nullable=False)
    tissue = Column(String(100))
    diagnosis = Column(String(500))
    oncotree_id = Column(String(50))
    technical_notes = Column(Text)
    qc_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="cases")
    variant_analyses = relationship("VariantAnalysis", back_populates="case")
    interpretations = relationship("VariantInterpretation", back_populates="case")
    
    # Indexes
    __table_args__ = (
        Index("idx_patient_case", "patient_uid", "case_uid"),
        Index("idx_oncotree", "oncotree_id"),
    )


class VariantAnalysis(Base):
    """Variant analysis run information"""
    __tablename__ = "variant_analyses"
    
    analysis_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_uid = Column(String(255), ForeignKey("cases.case_uid"), nullable=False)
    vcf_file_path = Column(String(500))
    vcf_file_hash = Column(String(64))
    total_variants_input = Column(Integer)
    variants_passing_qc = Column(Integer)
    kb_version_snapshot = Column(JSON)  # Knowledge base versions used
    vep_version = Column(String(50))
    analysis_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="variant_analyses")
    variants = relationship("Variant", back_populates="analysis")
    
    # Indexes
    __table_args__ = (
        Index("idx_case_analysis", "case_uid", "analysis_date"),
    )


class Variant(Base):
    """Individual variant information"""
    __tablename__ = "variants"
    
    variant_id = Column(String(255), primary_key=True)
    analysis_id = Column(String(255), ForeignKey("variant_analyses.analysis_id"), nullable=False)
    chromosome = Column(String(10))
    position = Column(BigInteger)
    reference_allele = Column(String(1000))
    alternate_allele = Column(String(1000))
    variant_type = Column(String(50))
    gene_symbol = Column(String(100))
    transcript_id = Column(String(100))
    hgvsc = Column(String(500))
    hgvsp = Column(String(500))
    consequence = Column(String(200))
    vcf_info = Column(JSON)  # Complete VCF INFO field
    vep_annotations = Column(JSON)  # Complete VEP output
    
    # Quality metrics
    vaf = Column(Numeric(5, 4))  # Variant allele frequency
    total_depth = Column(Integer)
    
    # Relationships
    analysis = relationship("VariantAnalysis", back_populates="variants")
    tiering_results = relationship("TieringResult", back_populates="variant")
    interpretations = relationship("VariantInterpretation", back_populates="variant")
    
    # Indexes
    __table_args__ = (
        Index("idx_analysis_variant", "analysis_id", "variant_id"),
        Index("idx_gene_variant", "gene_symbol", "chromosome", "position"),
        Index("idx_coordinates", "chromosome", "position"),
    )


class TieringResult(Base):
    """Tiering results for variants under different guidelines"""
    __tablename__ = "tiering_results"
    
    tiering_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id = Column(String(255), ForeignKey("variants.variant_id"), nullable=False)
    guideline_framework = Column(SQLEnum(GuidelineFramework), nullable=False)
    tier_assigned = Column(String(20))
    confidence_score = Column(Numeric(5, 4))
    rules_invoked = Column(JSON)  # Array of rule IDs that fired
    rule_evidence = Column(JSON)  # Evidence supporting each rule
    kb_lookups_performed = Column(JSON)  # Knowledge base queries made
    tiering_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    variant = relationship("Variant", back_populates="tiering_results")
    interpretations = relationship("VariantInterpretation", back_populates="tiering")
    
    # Constraints and indexes
    __table_args__ = (
        Index("idx_variant_tiering", "variant_id", "guideline_framework"),
        Index("idx_tier_confidence", "tier_assigned", "confidence_score"),
        UniqueConstraint("variant_id", "guideline_framework", name="unique_variant_guideline"),
    )


class CannedInterpretation(Base):
    """Template interpretations for consistent reporting"""
    __tablename__ = "canned_interpretations"
    
    template_id = Column(String(255), primary_key=True)
    guideline_framework = Column(SQLEnum(GuidelineFramework), nullable=False)
    tier = Column(String(20), nullable=False)
    interpretation_text = Column(Text, nullable=False)
    clinical_significance = Column(String(100))
    therapeutic_implications = Column(Text)
    version = Column(String(20))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    interpretations = relationship("VariantInterpretation", back_populates="template")
    
    # Indexes
    __table_args__ = (
        Index("idx_framework_tier", "guideline_framework", "tier"),
        # Removed unique constraint to allow multiple templates per tier
        # UniqueConstraint("guideline_framework", "tier", "version", name="unique_framework_tier_version"),
    )


class VariantInterpretation(Base):
    """Final clinical interpretations for variants"""
    __tablename__ = "variant_interpretations"
    
    interpretation_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id = Column(String(255), ForeignKey("variants.variant_id"), nullable=False)
    case_uid = Column(String(255), ForeignKey("cases.case_uid"), nullable=False)
    guideline_framework = Column(SQLEnum(GuidelineFramework), nullable=False)
    tiering_id = Column(String(255), ForeignKey("tiering_results.tiering_id"))
    selected_template_id = Column(String(255), ForeignKey("canned_interpretations.template_id"))
    custom_interpretation = Column(Text)
    clinical_significance = Column(String(100))
    therapeutic_implications = Column(Text)
    confidence_level = Column(SQLEnum(ConfidenceLevel))
    interpreter_notes = Column(Text)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    variant = relationship("Variant", back_populates="interpretations")
    case = relationship("Case", back_populates="interpretations")
    tiering = relationship("TieringResult", back_populates="interpretations")
    template = relationship("CannedInterpretation", back_populates="interpretations")
    
    # Indexes
    __table_args__ = (
        Index("idx_variant_dx_interp", "variant_id", "case_uid", "guideline_framework"),
        Index("idx_case_interpretations", "case_uid", "created_at"),
        UniqueConstraint("variant_id", "case_uid", "guideline_framework", name="unique_variant_case_framework"),
    )


class AuditLog(Base):
    """Comprehensive audit trail for all database operations"""
    __tablename__ = "audit_log"
    
    log_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(255), nullable=False)
    action = Column(SQLEnum(AuditAction), nullable=False)
    old_values = Column(JSON)
    new_values = Column(JSON)
    user_id = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String(255))
    
    # Indexes
    __table_args__ = (
        Index("idx_table_record", "table_name", "record_id"),
        Index("idx_timestamp", "timestamp"),
        Index("idx_user_audit", "user_id", "timestamp"),
    )