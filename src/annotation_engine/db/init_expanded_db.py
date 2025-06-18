"""
Database initialization for expanded schema with comprehensive KB integration

This module provides functions to initialize the database with both original
and expanded schemas, handle migrations, and populate reference data.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .base import Base, get_database_url, init_db
from .models import *  # Import original models
from .expanded_models import *  # Import expanded models

logger = logging.getLogger(__name__)


def init_expanded_database(database_url: Optional[str] = None, 
                         echo: bool = False,
                         include_sample_data: bool = False) -> None:
    """
    Initialize database with expanded schema for comprehensive KB integration
    
    Args:
        database_url: Database connection URL (defaults to environment/config)
        echo: Enable SQL query logging
        include_sample_data: Whether to populate with sample reference data
    """
    
    if database_url is None:
        database_url = get_database_url()
    
    logger.info(f"Initializing expanded database schema: {database_url}")
    
    # Create engine
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False}
        )
    else:
        engine = create_engine(database_url, echo=echo)
    
    # Create all tables (both original and expanded)
    Base.metadata.create_all(bind=engine)
    logger.info("All database tables created successfully")
    
    # Initialize sample data if requested
    if include_sample_data:
        _populate_reference_data(engine)
    
    logger.info("Expanded database initialization complete")


def _populate_reference_data(engine) -> None:
    """Populate database with essential reference data"""
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        logger.info("Populating reference data...")
        
        # 1. Drug classes
        _create_drug_classes(session)
        
        # 2. Citation sources with reliability tiers
        _create_citation_sources(session)
        
        # 3. Sample text templates
        _create_sample_text_templates(session)
        
        session.commit()
        logger.info("Reference data populated successfully")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error populating reference data: {e}")
        raise
    finally:
        session.close()


def _create_drug_classes(session) -> None:
    """Create hierarchical drug class structure"""
    
    drug_classes = [
        # Top-level classes
        {"id": "targeted_therapy", "name": "Targeted Therapy", 
         "mechanism": "Targeted inhibition of specific molecular pathways", "parent": None},
        {"id": "immunotherapy", "name": "Immunotherapy",
         "mechanism": "Modulation of immune system response", "parent": None},
        {"id": "chemotherapy", "name": "Chemotherapy",
         "mechanism": "Cytotoxic agents affecting cell division", "parent": None},
        
        # Targeted therapy subclasses
        {"id": "tyrosine_kinase_inhibitor", "name": "Tyrosine Kinase Inhibitor",
         "mechanism": "Inhibition of tyrosine kinase enzymes", "parent": "targeted_therapy"},
        {"id": "monoclonal_antibody", "name": "Monoclonal Antibody",
         "mechanism": "Targeted binding to specific antigens", "parent": "targeted_therapy"},
        {"id": "proteasome_inhibitor", "name": "Proteasome Inhibitor",
         "mechanism": "Inhibition of proteasome-mediated protein degradation", "parent": "targeted_therapy"},
        
        # Immunotherapy subclasses
        {"id": "checkpoint_inhibitor", "name": "Checkpoint Inhibitor",
         "mechanism": "Inhibition of immune checkpoint proteins", "parent": "immunotherapy"},
        {"id": "car_t_therapy", "name": "CAR-T Therapy",
         "mechanism": "Genetically modified T-cell therapy", "parent": "immunotherapy"},
        
        # Specific targeted classes
        {"id": "egfr_inhibitor", "name": "EGFR Inhibitor",
         "mechanism": "Inhibition of epidermal growth factor receptor", "parent": "tyrosine_kinase_inhibitor"},
        {"id": "braf_inhibitor", "name": "BRAF Inhibitor",
         "mechanism": "Inhibition of BRAF kinase", "parent": "tyrosine_kinase_inhibitor"},
        {"id": "mek_inhibitor", "name": "MEK Inhibitor",
         "mechanism": "Inhibition of MEK kinase", "parent": "tyrosine_kinase_inhibitor"},
        {"id": "pd1_inhibitor", "name": "PD-1 Inhibitor",
         "mechanism": "Inhibition of PD-1 checkpoint protein", "parent": "checkpoint_inhibitor"},
        {"id": "pdl1_inhibitor", "name": "PD-L1 Inhibitor",
         "mechanism": "Inhibition of PD-L1 checkpoint protein", "parent": "checkpoint_inhibitor"},
    ]
    
    for dc in drug_classes:
        drug_class = DrugClass(
            drug_class_id=dc["id"],
            class_name=dc["name"],
            mechanism_of_action=dc["mechanism"],
            parent_class_id=dc["parent"]
        )
        session.merge(drug_class)


def _create_citation_sources(session) -> None:
    """Create citation sources with reliability tiers"""
    
    sources = [
        # Tier 1: Regulatory
        {"id": "FDA", "name": "U.S. Food and Drug Administration", "type": "regulatory",
         "tier": SourceReliability.TIER_1_REGULATORY, 
         "format": "U.S. Food and Drug Administration. {title}. {date}.",
         "url": "https://www.fda.gov/", "impact": None, "quality": 1.0},
        
        {"id": "EMA", "name": "European Medicines Agency", "type": "regulatory",
         "tier": SourceReliability.TIER_1_REGULATORY,
         "format": "European Medicines Agency. {title}. {date}.",
         "url": "https://www.ema.europa.eu/", "impact": None, "quality": 1.0},
        
        # Tier 2: Professional Guidelines
        {"id": "NCCN", "name": "National Comprehensive Cancer Network", "type": "guideline",
         "tier": SourceReliability.TIER_2_GUIDELINES,
         "format": "NCCN Clinical Practice Guidelines in Oncology. {guideline}. Version {version}.",
         "url": "https://www.nccn.org/", "impact": None, "quality": 0.95},
        
        {"id": "ASCO", "name": "American Society of Clinical Oncology", "type": "guideline",
         "tier": SourceReliability.TIER_2_GUIDELINES,
         "format": "American Society of Clinical Oncology. {title}. {journal}. {year}.",
         "url": "https://www.asco.org/", "impact": None, "quality": 0.95},
        
        # Tier 3: Expert Curated
        {"id": "ONCOKB", "name": "OncoKB", "type": "database",
         "tier": SourceReliability.TIER_3_EXPERT_CURATED,
         "format": "Chakravarty D, et al. OncoKB: A Precision Oncology Knowledge Base. JCO Precis Oncol. 2017.",
         "url": "https://www.oncokb.org/", "impact": None, "quality": 0.9},
        
        {"id": "CIVIC", "name": "CIViC", "type": "database",
         "tier": SourceReliability.TIER_3_EXPERT_CURATED,
         "format": "Griffith M, et al. CIViC: a community knowledgebase for expert crowdsourcing...",
         "url": "https://civicdb.org/", "impact": None, "quality": 0.9},
        
        {"id": "CLINVAR", "name": "ClinVar", "type": "database",
         "tier": SourceReliability.TIER_3_EXPERT_CURATED,
         "format": "Landrum MJ, et al. ClinVar: improving access to variant interpretations...",
         "url": "https://www.ncbi.nlm.nih.gov/clinvar/", "impact": None, "quality": 0.85},
        
        # Tier 4: Community/Research
        {"id": "COSMIC", "name": "COSMIC", "type": "database",
         "tier": SourceReliability.TIER_4_COMMUNITY,
         "format": "Tate JG, et al. COSMIC: the Catalogue Of Somatic Mutations In Cancer...",
         "url": "https://cancer.sanger.ac.uk/", "impact": None, "quality": 0.8},
        
        {"id": "GNOMAD", "name": "gnomAD", "type": "database",
         "tier": SourceReliability.TIER_4_COMMUNITY,
         "format": "Karczewski KJ, et al. The mutational constraint spectrum quantified...",
         "url": "https://gnomad.broadinstitute.org/", "impact": None, "quality": 0.8},
        
        # Tier 5: Computational
        {"id": "ALPHAMISSENSE", "name": "AlphaMissense", "type": "computational",
         "tier": SourceReliability.TIER_5_COMPUTATIONAL,
         "format": "Cheng J, et al. Accurate proteome-wide missense variant effect prediction...",
         "url": "https://alphamissense.hegelab.org/", "impact": None, "quality": 0.7},
        
        {"id": "REVEL", "name": "REVEL", "type": "computational", 
         "tier": SourceReliability.TIER_5_COMPUTATIONAL,
         "format": "Ioannidis NM, et al. REVEL: An Ensemble Method for Predicting...",
         "url": "https://sites.google.com/site/revelgenomics/", "impact": None, "quality": 0.7},
    ]
    
    for source in sources:
        citation_source = CitationSource(
            source_id=source["id"],
            source_name=source["name"],
            source_type=source["type"],
            reliability_tier=source["tier"],
            citation_format=source["format"],
            url_pattern=source["url"],
            impact_factor=source["impact"],
            quality_score=source["quality"]
        )
        session.merge(citation_source)


def _create_sample_text_templates(session) -> None:
    """Create sample text templates for each type"""
    
    templates = [
        {
            "name": "Basic Gene Information",
            "type": TextTemplateType.GENERAL_GENE_INFO,
            "version": "1.0",
            "content": "{gene_symbol} ({gene_name}) encodes {protein_function}. This gene is located on chromosome {chromosome} and has been associated with {associated_conditions}.",
            "required": ["gene_symbol", "protein_function"],
            "optional": ["gene_name", "chromosome", "associated_conditions"],
            "factors": {"gene_name": 0.1, "chromosome": 0.05, "associated_conditions": 0.2}
        },
        {
            "name": "Variant Clinical Interpretation",
            "type": TextTemplateType.VARIANT_DX_INTERPRETATION,
            "version": "1.0", 
            "content": "This {gene_symbol} {variant_notation} variant is classified as {clinical_significance} for {cancer_type} based on {evidence_basis}. {therapeutic_implications}",
            "required": ["gene_symbol", "variant_notation", "clinical_significance", "cancer_type"],
            "optional": ["evidence_basis", "therapeutic_implications"],
            "factors": {"evidence_basis": 0.3, "therapeutic_implications": 0.4}
        },
        {
            "name": "Biomarker Results", 
            "type": TextTemplateType.BIOMARKERS,
            "version": "1.0",
            "content": "Tumor Mutational Burden (TMB): {tmb_value} mutations/Mb ({tmb_category}). This is {tmb_interpretation} the threshold for {therapy_indication}.",
            "required": ["tmb_value", "tmb_category"],
            "optional": ["tmb_interpretation", "therapy_indication"],
            "factors": {"tmb_interpretation": 0.2, "therapy_indication": 0.3}
        }
    ]
    
    for template in templates:
        text_template = TextTemplate(
            template_name=template["name"],
            template_type=template["type"],
            version=template["version"],
            template_content=template["content"],
            required_fields=template["required"],
            optional_fields=template["optional"],
            confidence_factors=template["factors"],
            cancer_types=["all"],  # Applicable to all cancer types
            guideline_frameworks=["AMP_ACMG", "CGC_VICC", "ONCOKB"],
            created_by="system"
        )
        session.add(text_template)


def create_expanded_erd(output_path: str = "docs/EXPANDED_DATABASE_ERD.png") -> bool:
    """Generate ERD for the expanded schema"""
    
    try:
        from eralchemy2 import render_er
        
        # Create a temporary database with expanded schema
        temp_db_url = "sqlite:///temp_expanded_schema.db"
        init_expanded_database(temp_db_url, echo=False)
        
        # Generate ERD
        render_er(temp_db_url, output_path)
        
        # Clean up temp database
        import os
        if os.path.exists("temp_expanded_schema.db"):
            os.remove("temp_expanded_schema.db")
        
        logger.info(f"Expanded ERD generated: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating expanded ERD: {e}")
        return False


def get_schema_statistics() -> Dict[str, Any]:
    """Get statistics about the expanded schema"""
    
    # Count tables and relationships
    tables = Base.metadata.tables
    
    stats = {
        "total_tables": len(tables),
        "original_tables": 0,
        "expanded_tables": 0,
        "table_categories": {
            "core": [],
            "clinvar": [],
            "oncokb": [],
            "citations": [],
            "therapies": [],
            "templates": [],
            "caching": []
        }
    }
    
    # Categorize tables
    for table_name in tables.keys():
        if table_name in ["patients", "cases", "variant_analyses", "variants", 
                         "tiering_results", "canned_interpretations", 
                         "variant_interpretations", "audit_log"]:
            stats["original_tables"] += 1
            stats["table_categories"]["core"].append(table_name)
        else:
            stats["expanded_tables"] += 1
            
            if "clinvar" in table_name:
                stats["table_categories"]["clinvar"].append(table_name)
            elif "oncokb" in table_name:
                stats["table_categories"]["oncokb"].append(table_name)
            elif "citation" in table_name or "literature" in table_name:
                stats["table_categories"]["citations"].append(table_name)
            elif "drug" in table_name or "therapy" in table_name:
                stats["table_categories"]["therapies"].append(table_name)
            elif "text" in table_name or "template" in table_name:
                stats["table_categories"]["templates"].append(table_name)
            elif "cache" in table_name:
                stats["table_categories"]["caching"].append(table_name)
    
    return stats


if __name__ == "__main__":
    # Initialize expanded database with sample data
    init_expanded_database(include_sample_data=True)
    
    # Generate ERD
    create_expanded_erd()
    
    # Print statistics
    stats = get_schema_statistics()
    print(f"Schema Statistics:")
    print(f"  Total tables: {stats['total_tables']}")
    print(f"  Original tables: {stats['original_tables']}")
    print(f"  Expanded tables: {stats['expanded_tables']}")
    print(f"  Table categories: {list(stats['table_categories'].keys())}")