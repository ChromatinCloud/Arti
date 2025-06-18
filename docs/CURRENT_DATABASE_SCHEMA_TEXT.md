
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
