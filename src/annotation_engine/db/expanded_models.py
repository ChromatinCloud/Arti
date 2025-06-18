"""
Expanded SQLAlchemy models for comprehensive KB integration

This module extends the base schema with support for:
1. ClinVar integration with full metadata
2. OncoKB therapeutic annotations  
3. Citation and literature tracking
4. Comprehensive therapy/drug information
5. Enhanced canned text system with citations

These models are designed to handle the large-scale data from ClinVar, OncoKB,
and other major knowledge bases while maintaining performance.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Text, JSON, Boolean,
    Numeric, Float, ForeignKey, Index, UniqueConstraint, text, ARRAY
)
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base
import uuid


# ============================================================================
# ENUMS FOR EXPANDED SCHEMA
# ============================================================================

class ClinVarSignificance(str, Enum):
    """ClinVar clinical significance categories"""
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely pathogenic"
    VUS = "Uncertain significance"
    LIKELY_BENIGN = "Likely benign" 
    BENIGN = "Benign"
    DRUG_RESPONSE = "drug response"
    ASSOCIATION = "association"
    RISK_FACTOR = "risk factor"
    PROTECTIVE = "protective"
    CONFLICTING = "Conflicting interpretations of pathogenicity"
    OTHER = "other"


class ClinVarReviewStatus(str, Enum):
    """ClinVar review status levels"""
    NO_ASSERTION = "no assertion criteria provided"
    NO_INTERPRETATION = "no interpretation for the single variant"
    CRITERIA_PROVIDED = "criteria provided, single submitter"
    CRITERIA_PROVIDED_MULTIPLE = "criteria provided, multiple submitters"
    CRITERIA_PROVIDED_CONFLICTING = "criteria provided, conflicting interpretations"
    REVIEWED_BY_EXPERT = "reviewed by expert panel"
    PRACTICE_GUIDELINE = "practice guideline"


class OncoKBEvidenceLevel(str, Enum):
    """OncoKB evidence levels for therapeutic annotations"""
    LEVEL_1 = "LEVEL_1"      # FDA-approved
    LEVEL_2 = "LEVEL_2"      # Standard care
    LEVEL_3A = "LEVEL_3A"    # Compelling clinical evidence
    LEVEL_3B = "LEVEL_3B"    # Standard care in other tumors
    LEVEL_4 = "LEVEL_4"      # Compelling biological evidence
    LEVEL_R1 = "LEVEL_R1"    # Resistance - standard care
    LEVEL_R2 = "LEVEL_R2"    # Resistance - investigational


class TherapyType(str, Enum):
    """Types of therapeutic interventions"""
    TARGETED_THERAPY = "Targeted therapy"
    IMMUNOTHERAPY = "Immunotherapy"
    CHEMOTHERAPY = "Chemotherapy"
    HORMONE_THERAPY = "Hormone therapy"
    RADIATION_THERAPY = "Radiation therapy"
    SURGERY = "Surgery"
    COMBINATION = "Combination therapy"
    OTHER = "Other"


class SourceReliability(str, Enum):
    """Source reliability tiers for citation system"""
    TIER_1_REGULATORY = "FDA/EMA"
    TIER_2_GUIDELINES = "Professional guidelines"
    TIER_3_EXPERT_CURATED = "Expert curated"
    TIER_4_COMMUNITY = "Community/Research"
    TIER_5_COMPUTATIONAL = "Computational"


class TextTemplateType(str, Enum):
    """Enhanced canned text template types"""
    GENERAL_GENE_INFO = "General Gene Info"
    GENE_DX_INTERPRETATION = "Gene Dx Interpretation"
    GENERAL_VARIANT_INFO = "General Variant Info"
    VARIANT_DX_INTERPRETATION = "Variant Dx Interpretation"
    INCIDENTAL_SECONDARY_FINDINGS = "Incidental/Secondary Findings"
    CHROMOSOMAL_ALTERATION_INTERPRETATION = "Chromosomal Alteration Interpretation"
    PERTINENT_NEGATIVES = "Pertinent Negatives"
    BIOMARKERS = "Biomarkers"


# ============================================================================
# CLINVAR INTEGRATION MODELS
# ============================================================================

class ClinVarVariant(Base):
    """ClinVar variant annotations with full metadata"""
    __tablename__ = "clinvar_variants"
    
    clinvar_variant_id = Column(String(50), primary_key=True)  # ClinVar VariationID
    variant_id = Column(String(255), ForeignKey("variants.variant_id"), nullable=False)
    
    # ClinVar identifiers
    variation_id = Column(Integer, nullable=False)
    allele_id = Column(Integer)
    rcv_accession = Column(String(20))  # e.g., RCV000123456
    scv_accessions = Column(JSON)  # Array of SCV accessions
    
    # Clinical significance
    clinical_significance = Column(SQLEnum(ClinVarSignificance))
    review_status = Column(SQLEnum(ClinVarReviewStatus))
    star_rating = Column(Integer)  # 0-4 stars
    assertion_method = Column(String(200))
    
    # Submission details
    submitter_info = Column(JSON)  # Submitter details and counts
    submission_date = Column(DateTime)
    last_evaluated = Column(DateTime)
    
    # Clinical details
    condition_names = Column(JSON)  # Array of condition names
    medgen_cuis = Column(JSON)     # Array of MedGen CUIs
    omim_ids = Column(JSON)        # Array of OMIM IDs
    
    # Molecular consequence
    molecular_consequence = Column(String(100))
    protein_change = Column(String(200))
    
    # Conflict and interpretation
    interpretation_summary = Column(Text)
    conflicting_interpretations = Column(JSON)
    
    # Relationships
    variant = relationship("Variant", backref="clinvar_annotations")
    citations = relationship("ClinVarCitation", back_populates="clinvar_variant")
    
    # Indexes
    __table_args__ = (
        Index("idx_clinvar_variant", "variant_id"),
        Index("idx_clinvar_variation", "variation_id"),
        Index("idx_clinvar_significance", "clinical_significance", "review_status"),
        Index("idx_clinvar_star_rating", "star_rating"),
    )


class ClinVarCitation(Base):
    """Citations associated with ClinVar submissions"""
    __tablename__ = "clinvar_citations"
    
    citation_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinvar_variant_id = Column(String(50), ForeignKey("clinvar_variants.clinvar_variant_id"))
    
    # Publication details
    pmid = Column(String(20))
    doi = Column(String(100))
    title = Column(Text)
    authors = Column(Text)
    journal = Column(String(200))
    publication_year = Column(Integer)
    
    # Citation context
    citation_type = Column(String(50))  # e.g., "support", "refute", "general"
    supporting_evidence = Column(Text)
    
    # Relationships
    clinvar_variant = relationship("ClinVarVariant", back_populates="citations")
    
    # Indexes
    __table_args__ = (
        Index("idx_clinvar_citation_pmid", "pmid"),
        Index("idx_clinvar_citation_variant", "clinvar_variant_id"),
    )


# ============================================================================
# ONCOKB INTEGRATION MODELS  
# ============================================================================

class OncoKBGene(Base):
    """OncoKB gene-level annotations"""
    __tablename__ = "oncokb_genes"
    
    oncokb_gene_id = Column(String(50), primary_key=True)  # OncoKB internal ID
    gene_symbol = Column(String(100), nullable=False)
    gene_aliases = Column(JSON)  # Array of gene aliases
    
    # Gene properties
    is_oncogene = Column(Boolean, default=False)
    is_tumor_suppressor = Column(Boolean, default=False)
    is_biomarker = Column(Boolean, default=False)
    
    # Clinical relevance
    oncokb_summary = Column(Text)
    background = Column(Text)
    
    # Last updated
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    therapeutic_annotations = relationship("OncoKBTherapeuticAnnotation", back_populates="gene")
    
    # Indexes
    __table_args__ = (
        Index("idx_oncokb_gene_symbol", "gene_symbol"),
        UniqueConstraint("gene_symbol", name="uq_oncokb_gene_symbol"),
    )


class OncoKBTherapeuticAnnotation(Base):
    """OncoKB therapeutic annotations with evidence levels"""
    __tablename__ = "oncokb_therapeutic_annotations"
    
    annotation_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id = Column(String(255), ForeignKey("variants.variant_id"))
    oncokb_gene_id = Column(String(50), ForeignKey("oncokb_genes.oncokb_gene_id"))
    therapy_id = Column(String(255), ForeignKey("therapies.therapy_id"))
    
    # Evidence classification
    evidence_level = Column(SQLEnum(OncoKBEvidenceLevel))
    evidence_type = Column(String(50))  # Therapeutic, Diagnostic, Prognostic
    
    # Tumor type specificity
    cancer_type = Column(String(200))
    cancer_type_detailed = Column(String(300))
    oncotree_codes = Column(JSON)  # Array of OncoTree codes
    
    # Clinical details
    clinical_significance = Column(String(100))
    therapeutic_implication = Column(Text)
    resistance_info = Column(Text)
    
    # Evidence details
    evidence_description = Column(Text)
    supporting_pmids = Column(JSON)  # Array of PMIDs
    
    # FDA/guideline status
    fda_approved = Column(Boolean, default=False)
    guideline_recommendation = Column(String(100))
    approval_date = Column(DateTime)
    
    # Quality metrics
    confidence_score = Column(Numeric(3, 2))
    last_reviewed = Column(DateTime)
    
    # Relationships
    variant = relationship("Variant", backref="oncokb_annotations")
    gene = relationship("OncoKBGene", back_populates="therapeutic_annotations")
    therapy = relationship("Therapy", back_populates="oncokb_annotations")
    
    # Indexes
    __table_args__ = (
        Index("idx_oncokb_variant", "variant_id"),
        Index("idx_oncokb_therapy", "therapy_id"),
        Index("idx_oncokb_evidence_level", "evidence_level"),
        Index("idx_oncokb_cancer_type", "cancer_type"),
        Index("idx_oncokb_fda_approved", "fda_approved"),
    )


# ============================================================================
# THERAPY AND DRUG INFORMATION MODELS
# ============================================================================

class DrugClass(Base):
    """Drug classification and mechanism information"""
    __tablename__ = "drug_classes"
    
    drug_class_id = Column(String(100), primary_key=True)
    class_name = Column(String(200), nullable=False)
    mechanism_of_action = Column(Text)
    target_pathway = Column(String(200))
    
    # Parent-child relationships for hierarchical classification
    parent_class_id = Column(String(100), ForeignKey("drug_classes.drug_class_id"))
    parent_class = relationship("DrugClass", remote_side="DrugClass.drug_class_id")
    
    # Relationships
    therapies = relationship("Therapy", back_populates="drug_class")


class Therapy(Base):
    """Comprehensive therapy/drug information"""
    __tablename__ = "therapies"
    
    therapy_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic drug information
    drug_name = Column(String(200), nullable=False)
    generic_names = Column(JSON)  # Array of generic names
    brand_names = Column(JSON)   # Array of brand names
    drug_synonyms = Column(JSON) # Array of synonyms
    
    # Drug classification
    drug_class_id = Column(String(100), ForeignKey("drug_classes.drug_class_id"))
    therapy_type = Column(SQLEnum(TherapyType))
    
    # Mechanism and targets
    mechanism_of_action = Column(Text)
    molecular_targets = Column(JSON)  # Array of protein targets
    target_pathways = Column(JSON)    # Array of pathway names
    
    # Regulatory information
    fda_approval_status = Column(String(50))
    fda_approval_date = Column(DateTime)
    indication_approved = Column(Text)
    
    # Clinical information
    dosing_information = Column(Text)
    administration_route = Column(String(100))
    contraindications = Column(Text)
    side_effects = Column(Text)
    
    # External identifiers
    drugbank_id = Column(String(20))
    chembl_id = Column(String(20))
    pubchem_cid = Column(String(20))
    
    # Relationships
    drug_class = relationship("DrugClass", back_populates="therapies")
    oncokb_annotations = relationship("OncoKBTherapeuticAnnotation", back_populates="therapy")
    drug_interactions = relationship("DrugInteraction", 
                                   foreign_keys="DrugInteraction.therapy_id",
                                   back_populates="therapy")
    
    # Indexes
    __table_args__ = (
        Index("idx_therapy_drug_name", "drug_name"),
        Index("idx_therapy_class", "drug_class_id"),
        Index("idx_therapy_fda_status", "fda_approval_status"),
        Index("idx_therapy_drugbank", "drugbank_id"),
    )


class DrugInteraction(Base):
    """Drug-drug interaction information"""
    __tablename__ = "drug_interactions"
    
    interaction_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    therapy_id = Column(String(255), ForeignKey("therapies.therapy_id"), nullable=False)
    interacting_therapy_id = Column(String(255), ForeignKey("therapies.therapy_id"))
    
    # Interaction details
    interaction_type = Column(String(100))  # "major", "moderate", "minor"
    interaction_mechanism = Column(Text)
    clinical_effect = Column(Text)
    management_recommendation = Column(Text)
    
    # Evidence
    evidence_level = Column(String(50))
    supporting_pmids = Column(JSON)
    
    # Relationships
    therapy = relationship("Therapy", 
                         foreign_keys=[therapy_id],
                         back_populates="drug_interactions")
    interacting_therapy = relationship("Therapy", foreign_keys=[interacting_therapy_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_drug_interaction_therapy", "therapy_id"),
        Index("idx_drug_interaction_type", "interaction_type"),
    )


# ============================================================================
# CITATIONS AND LITERATURE MODELS
# ============================================================================

class CitationSource(Base):
    """Master table for all citation sources with reliability metadata"""
    __tablename__ = "citation_sources"
    
    source_id = Column(String(100), primary_key=True)
    source_name = Column(String(200), nullable=False)
    source_type = Column(String(50))  # "journal", "database", "guideline", etc.
    
    # Reliability metadata
    reliability_tier = Column(SQLEnum(SourceReliability))
    citation_format = Column(String(500))
    url_pattern = Column(String(300))
    
    # Quality metrics
    impact_factor = Column(Float)
    h_index = Column(Integer)
    quality_score = Column(Numeric(3, 2))
    
    # Relationships
    literature_citations = relationship("LiteratureCitation", back_populates="source")
    
    # Indexes
    __table_args__ = (
        Index("idx_citation_source_reliability", "reliability_tier"),
        Index("idx_citation_source_quality", "quality_score"),
    )


class LiteratureCitation(Base):
    """Literature citations with comprehensive metadata"""
    __tablename__ = "literature_citations"
    
    citation_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Publication identifiers
    pmid = Column(String(20))
    doi = Column(String(100))
    pmc_id = Column(String(20))
    
    # Publication details
    title = Column(Text, nullable=False)
    authors = Column(Text)
    journal = Column(String(200))
    publication_year = Column(Integer)
    publication_date = Column(DateTime)
    volume = Column(String(20))
    issue = Column(String(20))
    pages = Column(String(50))
    
    # Source information
    source_id = Column(String(100), ForeignKey("citation_sources.source_id"))
    
    # Content analysis
    abstract = Column(Text)
    keywords = Column(JSON)  # Array of keywords
    mesh_terms = Column(JSON)  # Array of MeSH terms
    
    # Quality metrics
    citation_count = Column(Integer, default=0)
    impact_score = Column(Numeric(5, 2))
    evidence_strength = Column(String(50))
    
    # Last updated
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source = relationship("CitationSource", back_populates="literature_citations")
    text_citations = relationship("TextCitation", back_populates="literature_citation")
    
    # Indexes
    __table_args__ = (
        Index("idx_literature_pmid", "pmid"),
        Index("idx_literature_doi", "doi"),
        Index("idx_literature_journal_year", "journal", "publication_year"),
        Index("idx_literature_impact", "impact_score"),
        UniqueConstraint("pmid", name="uq_literature_pmid"),
    )


# ============================================================================
# ENHANCED CANNED TEXT SYSTEM MODELS
# ============================================================================

class TextTemplate(Base):
    """Enhanced text templates with versioning and citation support"""
    __tablename__ = "text_templates"
    
    template_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Template identification
    template_name = Column(String(200), nullable=False)
    template_type = Column(SQLEnum(TextTemplateType), nullable=False)
    version = Column(String(20), nullable=False)
    
    # Template content
    template_content = Column(Text, nullable=False)
    required_fields = Column(JSON)  # Array of required field names
    optional_fields = Column(JSON)  # Array of optional field names
    
    # Template metadata
    confidence_factors = Column(JSON)  # Field weights for confidence calculation
    cancer_types = Column(JSON)       # Array of applicable cancer types
    guideline_frameworks = Column(JSON)  # Array of applicable guidelines
    
    # Versioning and status
    is_active = Column(Boolean, default=True)
    parent_template_id = Column(String(255), ForeignKey("text_templates.template_id"))
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    deprecated_at = Column(DateTime)
    
    # Quality metrics
    usage_count = Column(Integer, default=0)
    avg_confidence_score = Column(Numeric(3, 2))
    
    # Relationships
    parent_template = relationship("TextTemplate", remote_side="TextTemplate.template_id")
    generated_texts = relationship("GeneratedText", back_populates="template")
    
    # Indexes
    __table_args__ = (
        Index("idx_text_template_type", "template_type"),
        Index("idx_text_template_active", "is_active", "template_type"),
        Index("idx_text_template_version", "template_name", "version"),
    )


class GeneratedText(Base):
    """Generated text instances with full provenance"""
    __tablename__ = "generated_texts"
    
    generated_text_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source information
    variant_id = Column(String(255), ForeignKey("variants.variant_id"))
    case_uid = Column(String(255), ForeignKey("cases.case_uid"))
    template_id = Column(String(255), ForeignKey("text_templates.template_id"))
    
    # Generated content
    text_type = Column(SQLEnum(TextTemplateType), nullable=False)
    generated_content = Column(Text, nullable=False)
    
    # Generation metadata
    generation_method = Column(String(50))  # "template", "enhanced_narrative", "ai"
    confidence_score = Column(Numeric(3, 2))
    evidence_completeness = Column(Numeric(3, 2))
    
    # Context used for generation
    generation_context = Column(JSON)  # Context data used
    evidence_sources = Column(JSON)    # Array of evidence source IDs
    
    # Quality and review
    reviewed = Column(Boolean, default=False)
    reviewer_id = Column(String(255))
    review_date = Column(DateTime)
    quality_rating = Column(Integer)  # 1-5 rating
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    variant = relationship("Variant", backref="generated_texts")
    case = relationship("Case", backref="generated_texts")
    template = relationship("TextTemplate", back_populates="generated_texts")
    citations = relationship("TextCitation", back_populates="generated_text")
    
    # Indexes
    __table_args__ = (
        Index("idx_generated_text_variant", "variant_id"),
        Index("idx_generated_text_case", "case_uid"),
        Index("idx_generated_text_type", "text_type"),
        Index("idx_generated_text_confidence", "confidence_score"),
        Index("idx_generated_text_reviewed", "reviewed"),
    )


class TextCitation(Base):
    """Citations embedded in generated text"""
    __tablename__ = "text_citations"
    
    text_citation_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    generated_text_id = Column(String(255), ForeignKey("generated_texts.generated_text_id"))
    literature_citation_id = Column(String(255), ForeignKey("literature_citations.citation_id"))
    
    # Citation placement
    citation_number = Column(Integer, nullable=False)
    citation_context = Column(Text)  # Text surrounding the citation
    citation_purpose = Column(String(100))  # "support", "contradict", "background"
    
    # Citation quality
    relevance_score = Column(Numeric(3, 2))
    evidence_strength = Column(String(50))
    
    # Relationships
    generated_text = relationship("GeneratedText", back_populates="citations")
    literature_citation = relationship("LiteratureCitation", back_populates="text_citations")
    
    # Indexes
    __table_args__ = (
        Index("idx_text_citation_generated", "generated_text_id"),
        Index("idx_text_citation_literature", "literature_citation_id"),
        Index("idx_text_citation_number", "generated_text_id", "citation_number"),
    )


# ============================================================================
# CACHING AND PERFORMANCE MODELS
# ============================================================================

class KnowledgeBaseCache(Base):
    """Cache for expensive knowledge base queries"""
    __tablename__ = "kb_cache"
    
    cache_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Cache key components
    cache_key = Column(String(500), nullable=False)  # Composite key for lookup
    kb_source = Column(String(100), nullable=False)  # e.g., "oncokb", "clinvar"
    query_type = Column(String(100), nullable=False) # e.g., "variant_lookup", "gene_search"
    
    # Cached data
    cached_result = Column(JSON, nullable=False)
    result_metadata = Column(JSON)  # Query metadata, performance stats
    
    # Cache management
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Data versioning
    kb_version = Column(String(50))
    data_checksum = Column(String(64))  # MD5 of cached result
    
    # Indexes
    __table_args__ = (
        Index("idx_kb_cache_key", "cache_key"),
        Index("idx_kb_cache_source", "kb_source", "query_type"),
        Index("idx_kb_cache_expires", "expires_at"),
        UniqueConstraint("cache_key", "kb_source", "query_type", name="uq_kb_cache_composite"),
    )


# ============================================================================
# RELATIONSHIP EXTENSIONS FOR EXISTING MODELS
# ============================================================================

# Add these relationships to existing models through backref/back_populates
# This would be done via model updates or database migrations