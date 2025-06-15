# API Routing and Information Flow Blueprint

## Overview

This document maps the complete information flow from variant input through knowledge base annotation, rule invocation, tiering, interpretation generation, and final sign-out. The API supports both single variant and small batch processing (≤20 variants) with comprehensive audit trails.

## Technology Stack Integration

- **FastAPI**: REST API endpoints with automatic OpenAPI documentation
- **SQLAlchemy**: Database operations and relationship management
- **Pydantic**: Request/response validation and serialization
- **Uvicorn**: ASGI server for async operations
- **Background Tasks**: Long-running processes (VEP, KB lookups)

## User Types and Permissions

```python
class UserRole(str, Enum):
    TRAINEE = "trainee"      # Can analyze, interpret, but not sign out
    ATTENDING = "attending"  # Full permissions including sign-out
    # MVP: No authentication - default to attending
```

## Complete Information Flow Architecture

### Phase 1: Variant Input and Analysis

```
VCF/API Input → VEP Analysis → KB Annotation → Rule Engine → Tiering → Canned Text Generation
```

### Phase 2: Review and Interpretation

```
Bundled Results → User Review → Interpretation Selection/Creation → Sign-out → Audit Trail
```

## API Endpoint Structure

### 1. Variant Analysis Endpoints

#### Submit Variant Analysis
```python
POST /api/v1/analyses/
Content-Type: multipart/form-data OR application/json

# VCF Upload
{
    "case_uid": "CASE_001",
    "patient_uid": "PAT_001", 
    "vcf_file": <file>,
    "cancer_type": "lung_adenocarcinoma",
    "oncotree_id": "LUAD",
    "tissue": "primary_tumor",
    "technical_notes": "Optional notes",
    "qc_notes": "Optional QC info"
}

# Single Variant API
{
    "case_uid": "CASE_001",
    "patient_uid": "PAT_001",
    "variant": {
        "chromosome": "17",
        "position": 7674220,
        "reference": "G",
        "alternate": "A",
        "gene_symbol": "TP53"
    },
    "cancer_type": "lung_adenocarcinoma",
    "oncotree_id": "LUAD"
}

Response: 202 Accepted
{
    "analysis_id": "ANALYSIS_12345",
    "status": "processing",
    "estimated_completion": "2024-01-01T10:05:00Z",
    "status_url": "/api/v1/analyses/ANALYSIS_12345/status"
}
```

#### Check Analysis Status
```python
GET /api/v1/analyses/{analysis_id}/status

Response: 200 OK
{
    "analysis_id": "ANALYSIS_12345",
    "status": "completed",  # processing, completed, failed
    "progress": 100,
    "started_at": "2024-01-01T10:00:00Z",
    "completed_at": "2024-01-01T10:05:00Z",
    "variants_processed": 15,
    "variants_total": 15,
    "errors": []
}
```

### 2. Results Retrieval Endpoints

#### Get Analysis Results
```python
GET /api/v1/analyses/{analysis_id}/results

Response: 200 OK
{
    "analysis_id": "ANALYSIS_12345",
    "case_info": {
        "case_uid": "CASE_001",
        "patient_uid": "PAT_001",
        "cancer_type": "lung_adenocarcinoma",
        "oncotree_id": "LUAD",
        "tissue": "primary_tumor"
    },
    "kb_versions": {
        "oncokb": "2024-01-01",
        "civic": "2024-01-01",
        "cosmic": "v99",
        "clinvar": "2024-01-01",
        "gnomad": "v4.0.0"
    },
    "variants": [
        {
            "variant_id": "VAR_001",
            "genomic_info": {
                "chromosome": "17",
                "position": 7674220,
                "reference": "G",
                "alternate": "A",
                "gene_symbol": "TP53",
                "transcript_id": "NM_000546.6",
                "hgvsc": "c.733G>A",
                "hgvsp": "p.Gly245Ser",
                "consequence": "missense_variant"
            },
            "kb_annotations": {
                "oncokb": {...},
                "civic": {...},
                "cosmic": {...},
                "clinvar": {...},
                "gnomad": {...}
            },
            "tiering_results": {
                "amp_acmg": {
                    "tier": "Tier_I",
                    "confidence_score": 0.95,
                    "rules_invoked": [
                        {
                            "rule_id": "PS1",
                            "rule_name": "Pathogenic Strong 1",
                            "description": "Same amino acid change as established pathogenic variant",
                            "evidence_strength": "STRONG",
                            "weight_applied": 0.8,
                            "evidence_sources": ["ClinVar:12345", "COSMIC:COSV123"]
                        }
                    ]
                },
                "cgc_vicc": {...},
                "oncokb": {...}
            },
            "canned_interpretations": {
                "general_gene_info": "TP53 encodes tumor protein p53...",
                "gene_dx_interpretation": "TP53 is frequently mutated in lung adenocarcinoma...",
                "general_variant_info": "This missense variant affects codon 245...",
                "variant_dx_interpretation": "p.Gly245Ser has been reported as pathogenic...",
                "incidental_findings": null,
                "chr_alteration_interp": null,
                "technical_comments": "Variant called with high confidence (DP=150, VAF=0.45)",
                "pertinent_negatives": "No actionable variants detected in EGFR, ALK, ROS1",
                "biomarkers": "TMB: 12 mutations/Mb (high), MSI: stable"
            },
            "existing_interpretations": [
                {
                    "interpretation_id": "INTERP_001",
                    "guideline_framework": "AMP_ACMG",
                    "clinical_significance": "Pathogenic",
                    "interpretation_text": "This variant is pathogenic for Li-Fraumeni syndrome...",
                    "confidence_level": "HIGH",
                    "created_by": "Dr. Smith",
                    "created_at": "2023-12-01T09:00:00Z",
                    "usage_count": 15
                }
            ]
        }
    ]
}
```

### 3. Interpretation Management Endpoints

#### Get Variant Interpretation Options
```python
GET /api/v1/variants/{variant_id}/interpretations
?cancer_type=lung_adenocarcinoma
&guideline_framework=AMP_ACMG

Response: 200 OK
{
    "variant_id": "VAR_001",
    "available_interpretations": [
        {
            "interpretation_id": "INTERP_001",
            "interpretation_text": "Pathogenic variant associated with...",
            "clinical_significance": "Pathogenic",
            "match_score": 0.95,  # How well it matches this case
            "usage_count": 15,
            "last_used": "2023-12-15T10:00:00Z"
        }
    ],
    "suggested_new_interpretation": {
        "based_on_tier": "Tier_I",
        "confidence_score": 0.95,
        "template_text": "Based on the evidence, this variant is classified as...",
        "clinical_significance": "Pathogenic"
    }
}
```

#### Create New Interpretation
```python
POST /api/v1/interpretations/

{
    "variant_id": "VAR_001",
    "case_uid": "CASE_001",
    "guideline_framework": "AMP_ACMG",
    "interpretation_text": "Custom interpretation text...",
    "clinical_significance": "Pathogenic",
    "therapeutic_implications": "Consider platinum-based therapy",
    "confidence_level": "HIGH",
    "interpreter_notes": "Novel variant, literature review performed"
}

Response: 201 Created
{
    "interpretation_id": "INTERP_NEW_001",
    "status": "draft",
    "created_at": "2024-01-01T10:00:00Z"
}
```

#### Select Interpretation for Case
```python
POST /api/v1/cases/{case_uid}/variants/{variant_id}/select-interpretation

{
    "interpretation_id": "INTERP_001",
    "guideline_framework": "AMP_ACMG",
    "reviewer_notes": "Approved for sign-out"
}

Response: 200 OK
{
    "status": "selected",
    "ready_for_signout": true
}
```

### 4. Sign-out and Finalization Endpoints

#### Get Case Sign-out Summary
```python
GET /api/v1/cases/{case_uid}/signout-summary

Response: 200 OK
{
    "case_uid": "CASE_001",
    "patient_uid": "PAT_001",
    "analysis_summary": {
        "total_variants": 15,
        "significant_variants": 3,
        "actionable_variants": 1,
        "incidental_findings": 0
    },
    "variants_for_signout": [
        {
            "variant_id": "VAR_001",
            "gene_symbol": "TP53",
            "genomic_change": "c.733G>A (p.Gly245Ser)",
            "selected_interpretation": {
                "interpretation_id": "INTERP_001",
                "clinical_significance": "Pathogenic",
                "guideline_framework": "AMP_ACMG",
                "interpretation_text": "...",
                "tier": "Tier_I",
                "confidence_score": 0.95
            },
            "supporting_evidence": {
                "rules_invoked": ["PS1", "PM2"],
                "kb_sources": ["ClinVar", "OncoKB"],
                "literature_count": 25
            }
        }
    ],
    "pertinent_negatives": "No actionable variants in EGFR, ALK, ROS1",
    "biomarkers": {
        "tmb": "12 mutations/Mb (high)",
        "msi": "stable",
        "hrr": "not assessed"
    }
}
```

#### Sign Out Case
```python
POST /api/v1/cases/{case_uid}/signout

{
    "attending_id": "attending_001",  # MVP: optional
    "signout_notes": "Case reviewed and approved",
    "final_interpretations": [
        {
            "variant_id": "VAR_001",
            "interpretation_id": "INTERP_001",
            "guideline_framework": "AMP_ACMG"
        }
    ]
}

Response: 200 OK
{
    "case_uid": "CASE_001",
    "status": "signed_out",
    "signed_out_at": "2024-01-01T15:00:00Z",
    "signed_out_by": "attending_001",
    "report_id": "REPORT_001",
    "audit_log_id": "AUDIT_001"
}
```

### 5. Audit and History Endpoints

#### Get Case Audit Trail
```python
GET /api/v1/cases/{case_uid}/audit

Response: 200 OK
{
    "case_uid": "CASE_001",
    "audit_events": [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "action": "analysis_started",
            "user_id": "user_001",
            "details": {
                "analysis_id": "ANALYSIS_12345",
                "kb_versions": {...}
            }
        },
        {
            "timestamp": "2024-01-01T14:30:00Z",
            "action": "interpretation_selected",
            "user_id": "user_001",
            "details": {
                "variant_id": "VAR_001",
                "interpretation_id": "INTERP_001",
                "previous_selection": null
            }
        },
        {
            "timestamp": "2024-01-01T15:00:00Z",
            "action": "case_signed_out",
            "user_id": "attending_001",
            "details": {
                "final_interpretations": [...]
            }
        }
    ]
}
```

#### Get Variant Interpretation History
```python
GET /api/v1/variants/{variant_id}/history
?cancer_type=lung_adenocarcinoma

Response: 200 OK
{
    "variant_id": "VAR_001",
    "interpretation_history": [
        {
            "case_uid": "CASE_001",
            "interpretation_id": "INTERP_001",
            "clinical_significance": "Pathogenic",
            "cancer_type": "lung_adenocarcinoma",
            "signed_out_date": "2024-01-01T15:00:00Z",
            "attending": "Dr. Smith"
        }
    ],
    "interpretation_evolution": [
        {
            "date": "2023-01-01",
            "interpretation": "VUS",
            "evidence_count": 2
        },
        {
            "date": "2024-01-01", 
            "interpretation": "Pathogenic",
            "evidence_count": 15
        }
    ]
}
```

### 6. Knowledge Base and Rule Explanation Endpoints

#### Get Rule Explanation
```python
GET /api/v1/rules/{rule_id}/explanation
?variant_id=VAR_001

Response: 200 OK
{
    "rule_id": "PS1",
    "rule_name": "Pathogenic Strong 1",
    "description": "Same amino acid change as established pathogenic variant",
    "guideline_framework": "AMP_ACMG",
    "evidence_required": "Same amino acid change with ClinVar pathogenic classification",
    "weight": 0.8,
    "application_context": {
        "variant_id": "VAR_001",
        "why_invoked": "p.Gly245Ser matches ClinVar pathogenic variant at same position",
        "evidence_sources": [
            {
                "source": "ClinVar",
                "variant_id": "12345",
                "classification": "Pathogenic",
                "review_status": "reviewed_by_expert_panel"
            }
        ],
        "confidence": "HIGH"
    }
}
```

#### Get KB Annotation Details
```python
GET /api/v1/variants/{variant_id}/kb-annotations
?source=oncokb,civic,cosmic

Response: 200 OK
{
    "variant_id": "VAR_001",
    "kb_annotations": {
        "oncokb": {
            "oncogenicity": "Oncogenic",
            "mutation_effect": "Loss-of-function",
            "citations": ["PMID:12345", "PMID:67890"],
            "clinical_trials": [
                {
                    "nct_id": "NCT12345",
                    "title": "Study of drug X in TP53 mutant tumors"
                }
            ]
        },
        "civic": {
            "evidence_items": [
                {
                    "evidence_id": "EID123",
                    "evidence_level": "B",
                    "evidence_type": "Predictive",
                    "drugs": ["Platinum compounds"],
                    "disease": "Lung Adenocarcinoma"
                }
            ]
        },
        "cosmic": {
            "mutation_id": "COSV123456",
            "occurrence_count": 45,
            "tumor_types": ["lung", "breast", "colorectal"]
        }
    }
}
```

## Information Flow State Machine

### Analysis State Transitions
```python
class AnalysisStatus(str, Enum):
    SUBMITTED = "submitted"
    VEP_PROCESSING = "vep_processing" 
    KB_ANNOTATION = "kb_annotation"
    RULE_EVALUATION = "rule_evaluation"
    TIERING_COMPLETE = "tiering_complete"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Case State Transitions
```python
class CaseStatus(str, Enum):
    ANALYSIS_PENDING = "analysis_pending"
    REVIEW_IN_PROGRESS = "review_in_progress"
    READY_FOR_SIGNOUT = "ready_for_signout"
    SIGNED_OUT = "signed_out"
    ARCHIVED = "archived"
```

## Canned Text Generation Mapping

### KB Source → Canned Text Type Mapping

| Canned Text Type | Primary KB Sources | API Integration |
|------------------|-------------------|-----------------|
| **General Gene Info** | MyGene.info, UniProt, HGNC | `GET /api/v1/genes/{gene_symbol}/summary` |
| **Gene Dx Interpretation** | CIViC gene-level, OncoKB, CGC | `GET /api/v1/genes/{gene_symbol}/clinical-significance?cancer_type={type}` |
| **General Variant Info** | ClinVar, COSMIC, gnomAD, dbSNP, VEP | `GET /api/v1/variants/{variant_id}/population-data` |
| **Variant Dx Interpretation** | CIViC evidence, OncoKB, JAX-CKB | `GET /api/v1/variants/{variant_id}/clinical-evidence` |
| **Incidental Findings** | ACMG SF v3.2, ClinGen | `GET /api/v1/variants/{variant_id}/incidental-findings` |
| **Chr Alteration Interp** | Mitelman, COSMIC fusions | `GET /api/v1/variants/{variant_id}/structural-significance` |
| **Technical Comments** | Internal docs, CAP checklist | `GET /api/v1/variants/{variant_id}/technical-assessment` |
| **Pertinent Negatives** | OncoKB Tiers 1-4, CIViC hotspots | `GET /api/v1/cases/{case_uid}/pertinent-negatives` |
| **Biomarkers** | TCGA, OncoKB biomarkers, FDA CDx | `GET /api/v1/cases/{case_uid}/biomarkers` |

## Background Processing Architecture

### Async Task Management
```python
from fastapi import BackgroundTasks

@app.post("/api/v1/analyses/")
async def submit_analysis(
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    analysis_id = create_analysis_record(analysis_request)
    background_tasks.add_task(process_analysis, analysis_id)
    return {"analysis_id": analysis_id, "status": "processing"}

async def process_analysis(analysis_id: str):
    # 1. Run VEP analysis
    # 2. Perform KB lookups
    # 3. Invoke rule engine
    # 4. Calculate tiers and confidence scores
    # 5. Generate canned text
    # 6. Update analysis status
    pass
```

## Error Handling and Validation

### Comprehensive Error Responses
```python
class APIError(BaseModel):
    error_code: str
    error_message: str
    details: Optional[Dict] = None
    timestamp: datetime
    request_id: str

# Example error responses
{
    "error_code": "VEP_ANALYSIS_FAILED",
    "error_message": "VEP analysis failed for variant chr17:7674220G>A",
    "details": {
        "variant_id": "VAR_001",
        "vep_error": "Invalid genomic coordinates"
    },
    "timestamp": "2024-01-01T10:00:00Z",
    "request_id": "req_12345"
}
```

## API Documentation and Testing

### OpenAPI Integration
- Automatic API documentation via FastAPI
- Interactive testing interface at `/docs`
- Comprehensive request/response examples
- Schema validation and error reporting

This API routing structure provides complete traceability from variant input through final sign-out, with comprehensive audit trails and flexible interpretation management.