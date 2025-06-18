#!/usr/bin/env python3
"""
Generate ERD from existing database schema and create expanded schema for new KBs
"""

import sys
sys.path.append('src')

def generate_current_erd():
    """Generate ERD from current database schema"""
    try:
        from eralchemy2 import render_er
        from annotation_engine.db.base import get_database_url
        
        # Generate ERD from current models
        database_url = get_database_url()
        print(f"Generating ERD from database: {database_url}")
        
        # Generate PNG ERD
        render_er(database_url, 'docs/CURRENT_DATABASE_ERD.png')
        print("✅ Current ERD saved to: docs/CURRENT_DATABASE_ERD.png")
        
        # Generate DOT file for text representation
        render_er(database_url, 'docs/CURRENT_DATABASE_ERD.dot')
        print("✅ Current ERD DOT file saved to: docs/CURRENT_DATABASE_ERD.dot")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating ERD: {e}")
        return False

def analyze_schema_expansion_needs():
    """Analyze what needs to be added for new KBs"""
    print("\n🔍 Analyzing Schema Expansion Requirements")
    print("=" * 50)
    
    expansion_requirements = {
        "ClinVar Integration": [
            "Clinical significance tracking",
            "Review status and submission history", 
            "ClinVar variant IDs and accession numbers",
            "Submitter information and conflicts",
            "Star ratings and review status"
        ],
        "OncoKB Integration": [
            "Therapeutic annotations and drug mappings",
            "Evidence levels and biomarker annotations",
            "Tumor type specific annotations",
            "FDA/guideline approval status",
            "Resistance mutation tracking"
        ],
        "Citations and Literature": [
            "PMID and DOI tracking",
            "Evidence source attribution",
            "Citation quality and impact factors",
            "Literature mining results",
            "Automatic citation updates"
        ],
        "Therapy and Drug Information": [
            "Drug names and synonyms",
            "Mechanism of action",
            "FDA approval status and dates",
            "Clinical trial information",
            "Drug-drug interactions",
            "Dosing and administration",
            "Biomarker-therapy relationships"
        ],
        "Enhanced Canned Text System": [
            "Template versioning and management",
            "Citation integration with text",
            "Source reliability scoring",
            "Text confidence metrics",
            "Cancer-specific text variants"
        ]
    }
    
    for category, requirements in expansion_requirements.items():
        print(f"\n📋 {category}:")
        for req in requirements:
            print(f"   • {req}")
    
    return expansion_requirements

def create_text_erd_representation():
    """Create a text-based ERD representation"""
    try:
        with open('docs/CURRENT_DATABASE_ERD.dot', 'r') as f:
            dot_content = f.read()
        
        # Create a simplified text representation
        text_erd = """
# Current Database Schema (Text Representation)

## Core Tables

### patients
- patient_uid (PK)
- created_at, updated_at

### cases  
- case_uid (PK)
- patient_uid (FK → patients)
- tissue, diagnosis, oncotree_id
- technical_notes, qc_notes
- created_at, updated_at

### variant_analyses
- analysis_id (PK) 
- case_uid (FK → cases)
- vcf_file_path, vcf_file_hash
- total_variants_input, variants_passing_qc
- kb_version_snapshot (JSON)
- vep_version, analysis_date

### variants
- variant_id (PK)
- analysis_id (FK → variant_analyses)
- chromosome, position, reference_allele, alternate_allele
- variant_type, gene_symbol, transcript_id
- hgvsc, hgvsp, consequence
- vcf_info (JSON), vep_annotations (JSON)
- vaf, total_depth

### tiering_results
- tiering_id (PK)
- variant_id (FK → variants)
- guideline_framework (ENUM: AMP_ACMG, CGC_VICC, ONCOKB)
- tier_assigned, confidence_score
- rules_invoked (JSON), rule_evidence (JSON)
- kb_lookups_performed (JSON)
- tiering_timestamp

### canned_interpretations
- template_id (PK)
- guideline_framework, tier
- interpretation_text, clinical_significance
- therapeutic_implications
- version, active, created_at

### variant_interpretations
- interpretation_id (PK)
- variant_id (FK → variants)
- case_uid (FK → cases)
- guideline_framework
- tiering_id (FK → tiering_results)
- selected_template_id (FK → canned_interpretations)
- custom_interpretation, clinical_significance
- therapeutic_implications, confidence_level
- interpreter_notes, created_by, created_at

### audit_log
- log_id (PK)
- table_name, record_id, action
- old_values (JSON), new_values (JSON)
- user_id, timestamp, session_id

## Relationships
- patients → cases (1:many)
- cases → variant_analyses (1:many)
- variant_analyses → variants (1:many)
- variants → tiering_results (1:many)
- variants → variant_interpretations (1:many)
- cases → variant_interpretations (1:many)
- tiering_results → variant_interpretations (1:many)
- canned_interpretations → variant_interpretations (1:many)
"""
        
        with open('docs/CURRENT_DATABASE_SCHEMA_TEXT.md', 'w') as f:
            f.write(text_erd)
        
        print("✅ Text ERD representation saved to: docs/CURRENT_DATABASE_SCHEMA_TEXT.md")
        return True
        
    except Exception as e:
        print(f"❌ Error creating text ERD: {e}")
        return False

def main():
    print("🗃️  Database Schema Analysis and ERD Generation")
    print("=" * 60)
    
    # Generate current ERD
    erd_success = generate_current_erd()
    
    # Create text representation
    text_success = create_text_erd_representation()
    
    # Analyze expansion requirements
    expansion_requirements = analyze_schema_expansion_needs()
    
    print(f"\n📊 Summary:")
    print(f"✅ ERD Generation: {'Success' if erd_success else 'Failed'}")
    print(f"✅ Text Representation: {'Success' if text_success else 'Failed'}")
    print(f"✅ Expansion Analysis: Complete")
    print(f"\n🎯 Ready to design expanded schema for:")
    for category in expansion_requirements.keys():
        print(f"   • {category}")

if __name__ == "__main__":
    main()