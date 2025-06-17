"""
Database initialization and data population

Creates the database tables and populates with synthetic interpretation data
from the internal reference files.
"""

import logging
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from .base import init_db, get_db_session
from .models import (
    Patient, Case, VariantAnalysis, Variant, TieringResult,
    CannedInterpretation, VariantInterpretation, AuditLog,
    GuidelineFramework, ConfidenceLevel
)

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize and populate the annotation engine database"""
    
    def __init__(self, repo_root: Path = None):
        if repo_root is None:
            repo_root = Path(__file__).parent.parent.parent.parent
        self.repo_root = repo_root
        self.internal_data_path = repo_root / ".refs" / "internal"
        
    def initialize_database(self, reset: bool = False) -> None:
        """Initialize database and populate with synthetic data"""
        logger.info("Initializing annotation engine database...")
        
        # Initialize database schema
        init_db()
        
        if reset:
            self._reset_database()
            
        # Populate with synthetic data
        self._populate_canned_interpretations()
        self._populate_tumor_type_mappings()
        
        logger.info("Database initialization complete")
        
    def _reset_database(self) -> None:
        """Reset database by clearing all data"""
        logger.warning("Resetting database - all data will be lost!")
        
        with get_db_session() as session:
            # Delete in reverse dependency order
            session.query(AuditLog).delete()
            session.query(VariantInterpretation).delete()
            session.query(CannedInterpretation).delete()
            session.query(TieringResult).delete()
            session.query(Variant).delete()
            session.query(VariantAnalysis).delete()
            session.query(Case).delete()
            session.query(Patient).delete()
            
        logger.info("Database reset complete")
        
    def _populate_canned_interpretations(self) -> None:
        """Populate canned interpretations from synthetic data"""
        logger.info("Populating canned interpretations...")
        
        # Load the reportable comments data
        comments_file = self.internal_data_path / "tbl_reportable_comments_proc.tsv"
        if not comments_file.exists():
            logger.warning(f"Synthetic data file not found: {comments_file}")
            return
            
        interpretations_added = 0
        
        with get_db_session() as session:
            # Read TSV file in chunks to avoid memory issues
            with open(comments_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                for row_num, row in enumerate(reader, 1):
                    if row_num % 100 == 0:
                        logger.debug(f"Processing row {row_num}...")
                        
                    # Extract key fields
                    variant_id = row.get('variant_id', '').strip()
                    tier = row.get('tier', '').strip()
                    interpretation_text = row.get('General_Gene_and_Variant_Info', '').strip()
                    clinical_implications = row.get('clinical_implications', '').strip()
                    clinical_trials = row.get('clinical_trials', '').strip()
                    references = row.get('references', '').strip()
                    
                    if not variant_id or not interpretation_text:
                        continue
                        
                    # Determine guideline framework based on tier format
                    guideline_framework = self._infer_guideline_framework(tier)
                    if not guideline_framework:
                        continue
                        
                    # Create unique template ID including row number to avoid constraint conflicts
                    template_id = f"{guideline_framework}_{tier}_{variant_id}_{row_num}".replace(' ', '_').replace('/', '_').replace(':', '_')
                    
                    # Check if template_id already exists
                    existing = session.query(CannedInterpretation).filter_by(
                        template_id=template_id
                    ).first()
                    
                    if existing:
                        continue
                        
                    # Create canned interpretation record
                    canned_interp = CannedInterpretation(
                        template_id=template_id,
                        guideline_framework=guideline_framework,
                        tier=tier,
                        interpretation_text=interpretation_text,
                        clinical_significance=self._extract_clinical_significance(interpretation_text),
                        therapeutic_implications=clinical_implications,
                        version="1.0",
                        active=True
                    )
                    
                    session.add(canned_interp)
                    interpretations_added += 1
                    
                    # Commit every 50 records to avoid memory issues
                    if interpretations_added % 50 == 0:
                        session.commit()
                        
        logger.info(f"Added {interpretations_added} canned interpretations")
        
    def _populate_tumor_type_mappings(self) -> None:
        """Load tumor type descriptions for validation"""
        logger.info("Loading tumor type mappings...")
        
        tumor_descriptions_file = self.internal_data_path / "tumor_descriptions.txt"
        tumor_types_file = self.internal_data_path / "tumor_type.txt"
        
        # Store tumor type mappings in memory for future use
        # This could be expanded to a separate table if needed
        tumor_mappings = {}
        
        if tumor_descriptions_file.exists():
            with open(tumor_descriptions_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    tumor_type = row.get('Tumor Type', '').strip()
                    description = row.get('Description', '').strip()
                    if tumor_type and description:
                        tumor_mappings[tumor_type] = description
                        
        logger.info(f"Loaded {len(tumor_mappings)} tumor type descriptions")
        
    def _infer_guideline_framework(self, tier: str) -> Optional[GuidelineFramework]:
        """Infer guideline framework from tier format"""
        if not tier:
            return None
            
        tier = tier.upper().strip()
        
        # AMP/ACMG tiers (Tier I, II, III, IV)
        if tier.startswith('TIER') or tier in ['LEVEL 1', 'LEVEL 2', 'LEVEL 3A', 'LEVEL 3B', 'LEVEL 4']:
            return GuidelineFramework.AMP_ACMG
            
        # OncoKB levels
        if tier.startswith('LEVEL') and any(x in tier for x in ['1', '2', '3A', '3B', '4', 'R1', 'R2']):
            return GuidelineFramework.ONCOKB
            
        # CGC/VICC oncogenicity
        if any(term in tier for term in ['ONCOGENIC', 'LIKELY_ONCOGENIC', 'VUS', 'LIKELY_BENIGN', 'BENIGN']):
            return GuidelineFramework.CGC_VICC
            
        # Default to AMP_ACMG
        return GuidelineFramework.AMP_ACMG
        
    def _extract_clinical_significance(self, interpretation_text: str) -> str:
        """Extract clinical significance from interpretation text"""
        if not interpretation_text:
            return "Unknown"
            
        text_lower = interpretation_text.lower()
        
        # Look for key phrases
        if any(phrase in text_lower for phrase in ['pathogenic', 'oncogenic', 'driver']):
            return "Pathogenic"
        elif any(phrase in text_lower for phrase in ['likely pathogenic', 'likely oncogenic']):
            return "Likely Pathogenic"
        elif any(phrase in text_lower for phrase in ['benign', 'non-pathogenic']):
            return "Benign"
        elif any(phrase in text_lower for phrase in ['likely benign']):
            return "Likely Benign"
        elif any(phrase in text_lower for phrase in ['vus', 'uncertain', 'unknown']):
            return "Uncertain Significance"
        else:
            return "Unknown"
            
    def create_test_case(self, case_uid: str = "TEST_CASE_001") -> str:
        """Create a test case for development/testing"""
        logger.info(f"Creating test case: {case_uid}")
        
        with get_db_session() as session:
            # Create patient
            patient = Patient(patient_uid=f"PATIENT_{case_uid}")
            session.add(patient)
            
            # Create case
            case = Case(
                case_uid=case_uid,
                patient_uid=patient.patient_uid,
                tissue="Primary Tumor",
                diagnosis="Melanoma",
                oncotree_id="MEL",
                technical_notes="Test case for development",
                qc_notes="Passed all QC checks"
            )
            session.add(case)
            
            # Create variant analysis
            analysis = VariantAnalysis(
                case_uid=case_uid,
                vcf_file_path="test_data/test.vcf",
                vcf_file_hash="test_hash_123",
                total_variants_input=4,
                variants_passing_qc=4,
                kb_version_snapshot={
                    "oncokb": "2024-01",
                    "civic": "2024-01", 
                    "oncovi": "2024-01",
                    "msk_hotspots": "v2"
                },
                vep_version="110.0"
            )
            session.add(analysis)
            session.flush()  # Get analysis_id
            
            # Create test variants
            test_variants = [
                {
                    "variant_id": "7_140753336_T_A",
                    "chromosome": "7",
                    "position": 140753336,
                    "reference_allele": "T",
                    "alternate_allele": "A",
                    "gene_symbol": "BRAF",
                    "hgvsp": "p.Val600Glu",
                    "tier": "Tier I",
                    "framework": GuidelineFramework.AMP_ACMG
                },
                {
                    "variant_id": "17_7674220_G_A", 
                    "chromosome": "17",
                    "position": 7674220,
                    "reference_allele": "G",
                    "alternate_allele": "A", 
                    "gene_symbol": "TP53",
                    "hgvsp": "p.Arg248Gln",
                    "tier": "Tier III",
                    "framework": GuidelineFramework.AMP_ACMG
                }
            ]
            
            for var_data in test_variants:
                # Create variant
                variant = Variant(
                    variant_id=var_data["variant_id"],
                    analysis_id=analysis.analysis_id,
                    chromosome=var_data["chromosome"],
                    position=var_data["position"],
                    reference_allele=var_data["reference_allele"],
                    alternate_allele=var_data["alternate_allele"],
                    gene_symbol=var_data["gene_symbol"],
                    hgvsp=var_data["hgvsp"],
                    consequence="missense_variant",
                    vaf=0.5,
                    total_depth=50
                )
                session.add(variant)
                
                # Create tiering result
                tiering_result = TieringResult(
                    variant_id=var_data["variant_id"],
                    guideline_framework=var_data["framework"],
                    tier_assigned=var_data["tier"],
                    confidence_score=0.85,
                    rules_invoked=["rule_1", "rule_2"],
                    rule_evidence={"oncokb": "Level 1", "civic": "Pathogenic"},
                    kb_lookups_performed=["oncokb", "civic", "oncovi"]
                )
                session.add(tiering_result)
                
        logger.info(f"Test case {case_uid} created successfully")
        return case_uid


def initialize_annotation_database(reset: bool = False) -> None:
    """Main function to initialize the annotation database"""
    initializer = DatabaseInitializer()
    initializer.initialize_database(reset=reset)
    
    # Create a test case for development
    initializer.create_test_case()


if __name__ == "__main__":
    # Initialize database with synthetic data
    initialize_annotation_database(reset=True)