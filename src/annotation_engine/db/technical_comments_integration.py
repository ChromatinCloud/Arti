"""
Database integration for technical comments in Phase 3A schema

This module adds technical comment support to the existing database schema,
integrating with the enhanced text template system.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, Boolean, ForeignKey, Index
from sqlalchemy.orm import sessionmaker, relationship
from .base import Base
from .expanded_models import TextTemplateType
import uuid
import yaml


class TechnicalCommentTemplate(Base):
    """Technical comment templates for challenging genomic regions"""
    __tablename__ = "technical_comment_templates"
    
    comment_id = Column(String(50), primary_key=True)  # e.g., TC001
    technical_term = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, unknown
    
    # Template content
    comment_template = Column(Text, nullable=False)
    trigger_conditions = Column(JSON)  # Conditions that trigger this comment
    
    # Categorization
    applies_to_regions = Column(Boolean, default=True)
    applies_to_variants = Column(Boolean, default=True)
    assay_specific = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    variant_comments = relationship("VariantTechnicalComment", back_populates="template")
    
    # Indexes
    __table_args__ = (
        Index("idx_tech_comment_category", "category"),
        Index("idx_tech_comment_severity", "severity"),
        Index("idx_tech_comment_active", "is_active"),
    )


class VariantTechnicalComment(Base):
    """Applied technical comments for specific variants"""
    __tablename__ = "variant_technical_comments"
    
    comment_instance_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    variant_id = Column(String(255), ForeignKey("variants.variant_id"), nullable=False)
    comment_id = Column(String(50), ForeignKey("technical_comment_templates.comment_id"), nullable=False)
    analysis_id = Column(String(255), ForeignKey("variant_analyses.analysis_id"))
    
    # Applied comment details
    applied_comment = Column(Text, nullable=False)  # Filled template
    trigger_values = Column(JSON)  # Actual values that triggered the comment
    
    # Context
    region_name = Column(String(200))  # e.g., "BRAF_exon15_homopolymer"
    genomic_context = Column(JSON)  # Additional context (GC%, coverage, etc.)
    
    # Review status
    reviewed = Column(Boolean, default=False)
    reviewer_id = Column(String(255))
    review_date = Column(DateTime)
    include_in_report = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship("TechnicalCommentTemplate", back_populates="variant_comments")
    
    # Indexes
    __table_args__ = (
        Index("idx_var_tech_comment_variant", "variant_id"),
        Index("idx_var_tech_comment_analysis", "analysis_id"),
        Index("idx_var_tech_comment_reviewed", "reviewed"),
    )


class ChallengingRegion(Base):
    """Assay-specific challenging genomic regions"""
    __tablename__ = "challenging_regions"
    
    region_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Genomic coordinates
    chromosome = Column(String(10), nullable=False)
    start_pos = Column(Integer, nullable=False)
    end_pos = Column(Integer, nullable=False)
    region_name = Column(String(200))
    gene = Column(String(100))
    
    # Challenge type
    challenge_type = Column(String(100), nullable=False)  # Maps to technical_comment_templates
    assay_name = Column(String(100), nullable=False)
    
    # Challenge details
    challenge_description = Column(Text)
    severity = Column(String(20))
    evidence_basis = Column(Text)  # How this region was identified
    
    # Metrics
    failure_rate = Column(JSON)  # Historical failure rates
    avg_coverage = Column(JSON)  # Average coverage statistics
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_challenging_region_coords", "chromosome", "start_pos", "end_pos"),
        Index("idx_challenging_region_assay", "assay_name"),
        Index("idx_challenging_region_type", "challenge_type"),
        Index("idx_challenging_region_gene", "gene"),
    )


def populate_technical_comments(session):
    """Populate technical comment templates from configuration"""
    
    # Load configuration
    config_path = "resources/assay/default_assay/technical_comments_config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load TSV data
    import pandas as pd
    tsv_path = "resources/assay/default_assay/technical_comments_canned_text.tsv"
    df = pd.read_csv(tsv_path, sep='\t')
    
    # Create templates
    for _, row in df.iterrows():
        # Get template from config if available
        template_config = config['technical_comments'].get(row['comment_id'], {})
        
        template = TechnicalCommentTemplate(
            comment_id=row['comment_id'],
            technical_term=row['technical_term'],
            category=row['category'],
            severity=row['severity'],
            comment_template=row['canned_text'],
            trigger_conditions=template_config.get('trigger_conditions', {})
        )
        
        # Check if already exists
        existing = session.query(TechnicalCommentTemplate).filter_by(
            comment_id=row['comment_id']
        ).first()
        
        if not existing:
            session.add(template)
        else:
            # Update existing
            existing.technical_term = row['technical_term']
            existing.category = row['category']
            existing.severity = row['severity']
            existing.comment_template = row['canned_text']
            existing.updated_at = datetime.utcnow()
    
    session.commit()
    print(f"Loaded {len(df)} technical comment templates")


def apply_technical_comments(session, variant_id, analysis_id, genomic_context):
    """Apply relevant technical comments to a variant based on genomic context"""
    
    comments_applied = []
    
    # Get all active templates
    templates = session.query(TechnicalCommentTemplate).filter_by(is_active=True).all()
    
    for template in templates:
        # Check trigger conditions
        if should_apply_comment(template, genomic_context):
            # Fill template with actual values
            filled_comment = fill_template(template.comment_template, genomic_context)
            
            # Create comment instance
            comment = VariantTechnicalComment(
                variant_id=variant_id,
                comment_id=template.comment_id,
                analysis_id=analysis_id,
                applied_comment=filled_comment,
                trigger_values=extract_trigger_values(template, genomic_context),
                genomic_context=genomic_context
            )
            
            session.add(comment)
            comments_applied.append(template.technical_term)
    
    if comments_applied:
        session.commit()
        print(f"Applied {len(comments_applied)} technical comments to variant {variant_id}")
    
    return comments_applied


def should_apply_comment(template, context):
    """Determine if a technical comment should be applied based on context"""
    
    conditions = template.trigger_conditions or {}
    
    # Example logic for different comment types
    if template.comment_id == 'TC001':  # Coverage dropout
        return context.get('mean_coverage', 100) < conditions.get('min_depth', 20)
    
    elif template.comment_id == 'TC002':  # High GC
        return context.get('gc_content', 0) > conditions.get('gc_threshold', 0.75)
    
    elif template.comment_id == 'TC003':  # Tandem repeat
        return context.get('in_repeat_region', False)
    
    elif template.comment_id == 'TC006':  # Strand bias
        alt_forward = context.get('alt_reads_forward', 0)
        alt_reverse = context.get('alt_reads_reverse', 0)
        total_alt = alt_forward + alt_reverse
        if total_alt > 0:
            bias = max(alt_forward, alt_reverse) / total_alt
            return bias > conditions.get('strand_bias_threshold', 0.9)
    
    elif template.comment_id == 'TC009':  # Homopolymer
        return context.get('homopolymer_length', 0) >= conditions.get('min_homopolymer_length', 6)
    
    elif template.comment_id == 'TC010':  # FFPE artifact
        is_ffpe = context.get('specimen_type') == 'FFPE'
        is_ct_transition = context.get('variant_type') in ['C>T', 'G>A']
        low_vaf = context.get('vaf', 1.0) < conditions.get('vaf_threshold', 0.1)
        return is_ffpe and is_ct_transition and low_vaf
    
    # Default: don't apply
    return False


def fill_template(template_text, context):
    """Fill template placeholders with actual values"""
    
    # Simple placeholder replacement
    filled = template_text
    
    # Replace common placeholders
    replacements = {
        '{min_depth}': str(context.get('min_depth', 20)),
        '{fraction}': str(int(context.get('fraction_low_coverage', 0.3) * 100)),
        '{gc_percent}': str(int(context.get('gc_content', 0) * 100)),
        '{window}': str(context.get('gc_window', 100)),
        '{bias_percent}': str(int(context.get('strand_bias', 0) * 100)),
        '{length}': str(context.get('homopolymer_length', 0)),
        '{variant_type}': context.get('variant_type', 'variant'),
        '{vaf}': f"{context.get('vaf', 0) * 100:.1f}",
        '{distance}': str(context.get('distance_from_edge', 0))
    }
    
    for placeholder, value in replacements.items():
        filled = filled.replace(placeholder, value)
    
    return filled


def extract_trigger_values(template, context):
    """Extract the actual values that triggered the comment"""
    
    trigger_values = {}
    conditions = template.trigger_conditions or {}
    
    # Extract relevant values based on comment type
    if template.comment_id == 'TC001':
        trigger_values['coverage'] = context.get('mean_coverage')
        trigger_values['fraction_low_coverage'] = context.get('fraction_low_coverage')
    
    elif template.comment_id == 'TC002':
        trigger_values['gc_content'] = context.get('gc_content')
        trigger_values['gc_window'] = context.get('gc_window', 100)
    
    elif template.comment_id == 'TC006':
        trigger_values['strand_bias'] = context.get('strand_bias')
        trigger_values['alt_reads_forward'] = context.get('alt_reads_forward')
        trigger_values['alt_reads_reverse'] = context.get('alt_reads_reverse')
    
    return trigger_values


if __name__ == "__main__":
    # Example usage
    from .base import get_engine, get_session
    
    engine = get_engine()
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Populate templates
    session = get_session()
    populate_technical_comments(session)
    
    # Example: Apply comments to a variant
    example_context = {
        'mean_coverage': 15,
        'gc_content': 0.82,
        'specimen_type': 'FFPE',
        'variant_type': 'C>T',
        'vaf': 0.08,
        'homopolymer_length': 7
    }
    
    comments = apply_technical_comments(
        session,
        variant_id="chr7:140453136:A>T",
        analysis_id="analysis_001",
        genomic_context=example_context
    )
    
    print(f"Applied comments: {comments}")