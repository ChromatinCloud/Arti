# Pydantic Schema Validation Blueprint

## Overview

This document defines comprehensive Pydantic v2 schemas for all API request/response models, database entities, and internal data structures used throughout the annotation engine. Schemas are organized by functional domain and include validation rules, field constraints, and example usage.

## Base Configuration

```python
from pydantic import BaseModel, ConfigDict, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import re

class BaseSchema(BaseModel):
    """Base configuration for all Pydantic models"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        validate_default=True
    )
```

## Enumeration Types

```python
class GuidelineFramework(str, Enum):
    AMP_ACMG = "AMP_ACMG"
    CGC_VICC = "CGC_VICC"
    ONCOKB = "ONCOKB"

class AnalysisStatus(str, Enum):
    SUBMITTED = "submitted"
    VEP_PROCESSING = "vep_processing"
    KB_ANNOTATION = "kb_annotation"
    RULE_EVALUATION = "rule_evaluation"
    TIERING_COMPLETE = "tiering_complete"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    FAILED = "failed"

class CaseStatus(str, Enum):
    ANALYSIS_PENDING = "analysis_pending"
    REVIEW_IN_PROGRESS = "review_in_progress"
    READY_FOR_SIGNOUT = "ready_for_signout"
    SIGNED_OUT = "signed_out"
    ARCHIVED = "archived"

class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    CONFLICTING = "CONFLICTING"

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class UserRole(str, Enum):
    TRAINEE = "trainee"
    ATTENDING = "attending"

class ClinicalSignificance(str, Enum):
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    VUS = "Variant of Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"

class ScoringMethod(str, Enum):
    ONCOVI_RULES = "ONCOVI_RULES"
    ML_MODEL = "ML_MODEL"
    ENSEMBLE = "ENSEMBLE"
```

## Core Entity Schemas

### Patient and Case Schemas

```python
class PatientBase(BaseSchema):
    patient_uid: str = Field(..., min_length=1, max_length=255)

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    created_at: datetime
    updated_at: datetime

class CaseBase(BaseSchema):
    case_uid: str = Field(..., min_length=1, max_length=255)
    patient_uid: str = Field(..., min_length=1, max_length=255)
    tissue: Optional[str] = Field(None, max_length=100)
    diagnosis: Optional[str] = Field(None, max_length=500)
    oncotree_id: Optional[str] = Field(None, max_length=50)
    technical_notes: Optional[str] = None
    qc_notes: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseResponse(CaseBase):
    created_at: datetime
    updated_at: datetime
    status: CaseStatus = CaseStatus.ANALYSIS_PENDING
```

### Variant and Genomic Schemas

```python
class GenomicCoordinates(BaseSchema):
    chromosome: str = Field(..., regex=r'^(chr)?(1[0-9]|2[0-2]|[1-9]|X|Y|MT?)$')
    position: int = Field(..., gt=0)
    reference: str = Field(..., min_length=1, max_length=1000)
    alternate: str = Field(..., min_length=1, max_length=1000)
    
    @validator('chromosome')
    def normalize_chromosome(cls, v):
        """Normalize chromosome notation"""
        if v.startswith('chr'):
            return v[3:]
        return v

class VariantAnnotation(BaseSchema):
    gene_symbol: Optional[str] = Field(None, max_length=100)
    transcript_id: Optional[str] = Field(None, max_length=100)
    hgvsc: Optional[str] = Field(None, max_length=500)
    hgvsp: Optional[str] = Field(None, max_length=500)
    consequence: Optional[str] = Field(None, max_length=200)
    variant_type: Optional[str] = Field(None, max_length=50)

class VariantInput(BaseSchema):
    """Single variant input via API"""
    genomic_coordinates: GenomicCoordinates
    annotation: Optional[VariantAnnotation] = None

class VariantBase(BaseSchema):
    variant_id: str = Field(..., min_length=1, max_length=255)
    analysis_id: str = Field(..., min_length=1, max_length=255)
    chromosome: str
    position: int
    reference_allele: str
    alternate_allele: str
    variant_type: Optional[str] = Field(None, max_length=50)
    gene_symbol: Optional[str] = Field(None, max_length=100)
    transcript_id: Optional[str] = Field(None, max_length=100)
    hgvsc: Optional[str] = Field(None, max_length=500)
    hgvsp: Optional[str] = Field(None, max_length=500)
    consequence: Optional[str] = Field(None, max_length=200)
    vcf_info: Optional[Dict[str, Any]] = None
    vep_annotations: Optional[Dict[str, Any]] = None

class VariantCreate(VariantBase):
    pass

class VariantResponse(VariantBase):
    pass
```

### VEP Integration Schemas

```python
# PLACEHOLDER: VEP output schema - needs VEP JSON output format analysis
class VEPConsequence(BaseSchema):
    """
    Schema for VEP consequence annotations
    TODO: Define based on actual VEP --json output format
    Source: VEP documentation and sample outputs
    """
    allele_string: Optional[str] = None
    consequence_terms: Optional[List[str]] = None
    impact: Optional[str] = None  # HIGH, MODERATE, LOW, MODIFIER
    gene_id: Optional[str] = None
    gene_symbol: Optional[str] = None
    feature_type: Optional[str] = None  # Transcript, RegulatoryFeature, etc.
    feature_id: Optional[str] = None
    transcript_biotype: Optional[str] = None
    hgvsc: Optional[str] = None
    hgvsp: Optional[str] = None
    sift_prediction: Optional[str] = None
    sift_score: Optional[float] = None
    polyphen_prediction: Optional[str] = None
    polyphen_score: Optional[float] = None
    # Additional fields will be added based on VEP plugin outputs

class VEPResult(BaseSchema):
    """
    Complete VEP analysis result for a variant
    TODO: Refine based on actual VEP JSON structure
    """
    input: str  # Original input variant
    most_severe_consequence: Optional[str] = None
    transcript_consequences: List[VEPConsequence] = []
    colocated_variants: Optional[List[Dict[str, Any]]] = None
    # Plugin-specific annotations will be added
```

### Knowledge Base Annotation Schemas

```python
class OncoKBAnnotation(BaseSchema):
    """OncoKB variant annotation"""
    oncogenicity: Optional[str] = None  # Oncogenic, Likely Oncogenic, VUS, etc.
    mutation_effect: Optional[str] = None  # Gain-of-function, Loss-of-function, etc.
    highest_sensitive_level: Optional[str] = None  # Level 1, 2, 3A, 3B, 4
    highest_resistance_level: Optional[str] = None
    tumor_type_summary: Optional[str] = None
    variant_summary: Optional[str] = None
    gene_summary: Optional[str] = None
    diagnostic_summary: Optional[str] = None
    prognostic_summary: Optional[str] = None
    treatments: Optional[List[Dict[str, Any]]] = None
    diagnostic_implications: Optional[List[Dict[str, Any]]] = None
    prognostic_implications: Optional[List[Dict[str, Any]]] = None

class CIViCAnnotation(BaseSchema):
    """CIViC evidence annotation"""
    evidence_items: List[Dict[str, Any]] = []
    # PLACEHOLDER: Define based on CIViC API response format
    # Source: CIViC API documentation

class COSMICAnnotation(BaseSchema):
    """COSMIC mutation annotation"""
    mutation_id: Optional[str] = None
    legacy_mutation_id: Optional[str] = None
    mutation_cds: Optional[str] = None
    mutation_aa: Optional[str] = None
    mutation_description: Optional[str] = None
    mutation_zygosity: Optional[str] = None
    mutation_somatic_status: Optional[str] = None
    # PLACEHOLDER: Additional COSMIC fields based on export format

class ClinVarAnnotation(BaseSchema):
    """ClinVar variant annotation"""
    variation_id: Optional[int] = None
    clinical_significance: Optional[str] = None
    review_status: Optional[str] = None
    last_evaluated: Optional[str] = None
    submitter: Optional[str] = None
    condition: Optional[str] = None
    # PLACEHOLDER: Additional ClinVar fields based on VCF/API format

class GnomADAnnotation(BaseSchema):
    """gnomAD population frequency annotation"""
    allele_count: Optional[int] = None
    allele_number: Optional[int] = None
    allele_frequency: Optional[float] = None
    popmax_population: Optional[str] = None
    popmax_af: Optional[float] = None
    # Population-specific frequencies
    afr_af: Optional[float] = None
    amr_af: Optional[float] = None
    asj_af: Optional[float] = None
    eas_af: Optional[float] = None
    fin_af: Optional[float] = None
    nfe_af: Optional[float] = None
    sas_af: Optional[float] = None

class dbNSFPAnnotation(BaseSchema):
    """dbNSFP functional prediction annotation"""
    # PLACEHOLDER: Define based on dbNSFP field descriptions
    # Source: dbNSFP documentation and VEP plugin output
    sift_pred: Optional[str] = None
    sift_score: Optional[float] = None
    polyphen2_hdiv_pred: Optional[str] = None
    polyphen2_hdiv_score: Optional[float] = None
    lrt_pred: Optional[str] = None
    lrt_score: Optional[float] = None
    mutation_taster_pred: Optional[str] = None
    mutation_taster_score: Optional[float] = None
    fathmm_pred: Optional[str] = None
    fathmm_score: Optional[float] = None
    cadd_phred: Optional[float] = None
    cadd_raw: Optional[float] = None

class KnowledgeBaseAnnotations(BaseSchema):
    """Combined KB annotations for a variant"""
    oncokb: Optional[OncoKBAnnotation] = None
    civic: Optional[CIViCAnnotation] = None
    cosmic: Optional[COSMICAnnotation] = None
    clinvar: Optional[ClinVarAnnotation] = None
    gnomad: Optional[GnomADAnnotation] = None
    dbnsfp: Optional[dbNSFPAnnotation] = None
```

### Rule Engine and Tiering Schemas

```python
class RuleDefinition(BaseSchema):
    rule_id: str = Field(..., max_length=100)
    guideline_framework: GuidelineFramework
    rule_name: str = Field(..., max_length=200)
    rule_description: Optional[str] = None
    base_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_threshold: Optional[str] = Field(None, max_length=50)
    rule_version: Optional[str] = Field(None, max_length=20)
    active: bool = True

class RuleInvocation(BaseSchema):
    invocation_id: str = Field(..., max_length=255)
    tiering_id: str = Field(..., max_length=255)
    rule_id: str = Field(..., max_length=100)
    evidence_strength: EvidenceStrength
    applied_weight: float = Field(..., ge=0.0, le=1.0)
    evidence_sources: List[str] = []
    rule_context: Optional[Dict[str, Any]] = None

class TieringResult(BaseSchema):
    tiering_id: str = Field(..., max_length=255)
    variant_id: str = Field(..., max_length=255)
    guideline_framework: GuidelineFramework
    tier_assigned: Optional[str] = Field(None, max_length=20)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    rules_invoked: List[RuleInvocation] = []
    kb_lookups_performed: Optional[Dict[str, Any]] = None
    tiering_timestamp: datetime

class ConfidenceScore(BaseSchema):
    score_id: str = Field(..., max_length=255)
    tiering_id: str = Field(..., max_length=255)
    scoring_method: ScoringMethod
    confidence_value: float = Field(..., ge=0.0, le=1.0)
    model_version: Optional[str] = Field(None, max_length=50)
    feature_importance: Optional[Dict[str, float]] = None
    calibration_data: Optional[Dict[str, Any]] = None
    computed_at: datetime
```

### Canned Text Schemas

```python
class CannedTextType(str, Enum):
    GENERAL_GENE_INFO = "general_gene_info"
    GENE_DX_INTERPRETATION = "gene_dx_interpretation"
    GENERAL_VARIANT_INFO = "general_variant_info"
    VARIANT_DX_INTERPRETATION = "variant_dx_interpretation"
    INCIDENTAL_FINDINGS = "incidental_findings"
    CHR_ALTERATION_INTERP = "chr_alteration_interp"
    TECHNICAL_COMMENTS = "technical_comments"
    PERTINENT_NEGATIVES = "pertinent_negatives"
    BIOMARKERS = "biomarkers"

class CannedText(BaseSchema):
    text_type: CannedTextType
    content: str
    sources: List[str] = []  # KB sources used to generate text
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    generated_at: datetime

class CannedTextCollection(BaseSchema):
    """All canned text types for a variant"""
    general_gene_info: Optional[CannedText] = None
    gene_dx_interpretation: Optional[CannedText] = None
    general_variant_info: Optional[CannedText] = None
    variant_dx_interpretation: Optional[CannedText] = None
    incidental_findings: Optional[CannedText] = None
    chr_alteration_interp: Optional[CannedText] = None
    technical_comments: Optional[CannedText] = None
    pertinent_negatives: Optional[CannedText] = None
    biomarkers: Optional[CannedText] = None

class CannedInterpretationTemplate(BaseSchema):
    template_id: str = Field(..., max_length=255)
    guideline_framework: GuidelineFramework
    tier: str = Field(..., max_length=20)
    interpretation_text: str
    clinical_significance: Optional[str] = Field(None, max_length=100)
    therapeutic_implications: Optional[str] = None
    version: Optional[str] = Field(None, max_length=20)
    active: bool = True
```

### Interpretation Management Schemas

```python
class VariantInterpretationBase(BaseSchema):
    variant_id: str = Field(..., max_length=255)
    case_uid: str = Field(..., max_length=255)
    guideline_framework: GuidelineFramework
    clinical_significance: Optional[str] = Field(None, max_length=100)
    therapeutic_implications: Optional[str] = None
    confidence_level: Optional[ConfidenceLevel] = None
    interpreter_notes: Optional[str] = None

class VariantInterpretationCreate(VariantInterpretationBase):
    tiering_id: Optional[str] = Field(None, max_length=255)
    selected_template_id: Optional[str] = Field(None, max_length=255)
    custom_interpretation: Optional[str] = None
    created_by: Optional[str] = Field(None, max_length=255)

class VariantInterpretationResponse(VariantInterpretationBase):
    interpretation_id: str = Field(..., max_length=255)
    tiering_id: Optional[str] = None
    selected_template_id: Optional[str] = None
    custom_interpretation: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    usage_count: Optional[int] = 0
    last_used: Optional[datetime] = None

class InterpretationSelection(BaseSchema):
    interpretation_id: str = Field(..., max_length=255)
    guideline_framework: GuidelineFramework
    reviewer_notes: Optional[str] = None
```

### Analysis and Workflow Schemas

```python
class KnowledgeBaseVersions(BaseSchema):
    """Track KB versions used in analysis"""
    oncokb: Optional[str] = None
    civic: Optional[str] = None
    cosmic: Optional[str] = None
    clinvar: Optional[str] = None
    gnomad: Optional[str] = None
    dbnsfp: Optional[str] = None
    cgc: Optional[str] = None
    vep: Optional[str] = None
    capture_date: datetime

class VariantAnalysisBase(BaseSchema):
    analysis_id: str = Field(..., max_length=255)
    case_uid: str = Field(..., max_length=255)
    vcf_file_path: Optional[str] = Field(None, max_length=500)
    vcf_file_hash: Optional[str] = Field(None, max_length=64)
    total_variants_input: Optional[int] = Field(None, ge=0)
    variants_passing_qc: Optional[int] = Field(None, ge=0)
    kb_version_snapshot: Optional[KnowledgeBaseVersions] = None
    vep_version: Optional[str] = Field(None, max_length=50)

class VariantAnalysisCreate(VariantAnalysisBase):
    # For VCF upload
    vcf_file: Optional[bytes] = None
    # For single variant API
    single_variant: Optional[VariantInput] = None
    # Case information
    patient_uid: str = Field(..., max_length=255)
    cancer_type: Optional[str] = Field(None, max_length=100)
    oncotree_id: Optional[str] = Field(None, max_length=50)
    tissue: Optional[str] = Field(None, max_length=100)
    technical_notes: Optional[str] = None
    qc_notes: Optional[str] = None

class VariantAnalysisStatus(BaseSchema):
    analysis_id: str
    status: AnalysisStatus
    progress: int = Field(..., ge=0, le=100)
    started_at: datetime
    completed_at: Optional[datetime] = None
    variants_processed: Optional[int] = Field(None, ge=0)
    variants_total: Optional[int] = Field(None, ge=0)
    errors: List[str] = []
    estimated_completion: Optional[datetime] = None

class VariantAnalysisResult(BaseSchema):
    analysis_id: str
    case_info: CaseResponse
    kb_versions: KnowledgeBaseVersions
    variants: List['VariantResultBundle'] = []

class VariantResultBundle(BaseSchema):
    """Complete analysis result for a single variant"""
    variant_id: str
    genomic_info: VariantResponse
    kb_annotations: KnowledgeBaseAnnotations
    tiering_results: Dict[GuidelineFramework, TieringResult] = {}
    canned_interpretations: CannedTextCollection
    existing_interpretations: List[VariantInterpretationResponse] = []
    confidence_scores: List[ConfidenceScore] = []
```

### API Request/Response Schemas

```python
class APIError(BaseSchema):
    error_code: str = Field(..., max_length=100)
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: str = Field(..., max_length=255)

class APIResponse(BaseSchema):
    """Generic API response wrapper"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[APIError] = None
    request_id: str = Field(..., max_length=255)
    timestamp: datetime

class PaginatedResponse(BaseSchema):
    """Paginated API response"""
    items: List[Any] = []
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1, le=100)
    pages: int = Field(..., ge=1)

class RuleExplanation(BaseSchema):
    rule_id: str = Field(..., max_length=100)
    rule_name: str = Field(..., max_length=200)
    description: str
    guideline_framework: GuidelineFramework
    evidence_required: str
    weight: float = Field(..., ge=0.0, le=1.0)
    application_context: Dict[str, Any]

class KBAnnotationDetails(BaseSchema):
    variant_id: str = Field(..., max_length=255)
    kb_annotations: KnowledgeBaseAnnotations
    annotation_timestamp: datetime
    kb_versions: KnowledgeBaseVersions
```

### Audit and History Schemas

```python
class AuditAction(str, Enum):
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    INTERPRETATION_SELECTED = "interpretation_selected"
    INTERPRETATION_CREATED = "interpretation_created"
    CASE_SIGNED_OUT = "case_signed_out"
    RULE_MODIFIED = "rule_modified"
    KB_UPDATED = "kb_updated"

class AuditLogEntry(BaseSchema):
    log_id: str = Field(..., max_length=255)
    table_name: str = Field(..., max_length=100)
    record_id: str = Field(..., max_length=255)
    action: AuditAction
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = Field(None, max_length=255)
    timestamp: datetime
    session_id: Optional[str] = Field(None, max_length=255)

class CaseAuditTrail(BaseSchema):
    case_uid: str = Field(..., max_length=255)
    audit_events: List[AuditLogEntry] = []

class SignOutRequest(BaseSchema):
    attending_id: Optional[str] = Field(None, max_length=255)  # MVP: optional
    signout_notes: Optional[str] = None
    final_interpretations: List[InterpretationSelection] = []

class SignOutResponse(BaseSchema):
    case_uid: str = Field(..., max_length=255)
    status: CaseStatus
    signed_out_at: datetime
    signed_out_by: Optional[str] = Field(None, max_length=255)
    report_id: str = Field(..., max_length=255)
    audit_log_id: str = Field(..., max_length=255)

class CaseSignOutSummary(BaseSchema):
    case_uid: str = Field(..., max_length=255)
    patient_uid: str = Field(..., max_length=255)
    analysis_summary: Dict[str, int]
    variants_for_signout: List['SignOutVariant'] = []
    pertinent_negatives: Optional[str] = None
    biomarkers: Optional[Dict[str, str]] = None

class SignOutVariant(BaseSchema):
    variant_id: str = Field(..., max_length=255)
    gene_symbol: Optional[str] = None
    genomic_change: str
    selected_interpretation: VariantInterpretationResponse
    supporting_evidence: Dict[str, Any]
```

### ML Model Schemas

```python
class MLModelMetadata(BaseSchema):
    model_id: str = Field(..., max_length=255)
    model_name: str = Field(..., max_length=200)
    model_type: str = Field(..., max_length=100)
    guideline_framework: GuidelineFramework
    training_data_version: Optional[str] = Field(None, max_length=50)
    feature_set_version: Optional[str] = Field(None, max_length=50)
    model_artifact_path: Optional[str] = Field(None, max_length=500)
    performance_metrics: Optional[Dict[str, float]] = None
    calibration_curve: Optional[Dict[str, Any]] = None
    feature_definitions: Optional[Dict[str, str]] = None
    deployed_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None

# PLACEHOLDER: ML feature schemas - will be defined based on chosen ML approach
class MLFeatureVector(BaseSchema):
    """
    Feature vector for ML confidence prediction
    TODO: Define based on selected ML approach and feature engineering
    """
    rule_pattern: Optional[Dict[str, float]] = None
    evidence_strength_distribution: Optional[Dict[str, float]] = None
    variant_characteristics: Optional[Dict[str, Any]] = None
    knowledge_base_coverage: Optional[Dict[str, float]] = None
    historical_patterns: Optional[Dict[str, Any]] = None

class MLPrediction(BaseSchema):
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    feature_importance: Dict[str, float]
    model_version: str = Field(..., max_length=50)
    prediction_timestamp: datetime
```

## Validation Rules and Constraints

### Custom Validators

```python
class ValidationMixin:
    """Mixin with common validation methods"""
    
    @validator('*', pre=True)
    def empty_str_to_none(cls, v):
        """Convert empty strings to None"""
        if v == '':
            return None
        return v
    
    @validator('patient_uid', 'case_uid', 'variant_id', 'analysis_id')
    def validate_ids(cls, v):
        """Validate ID format"""
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('IDs must contain only alphanumeric characters, hyphens, and underscores')
        return v
    
    @validator('hgvsc', 'hgvsp')
    def validate_hgvs(cls, v):
        """Basic HGVS format validation"""
        if v and not re.match(r'^[cnpgmr]\..+', v):
            raise ValueError('Invalid HGVS notation')
        return v
```

### Field Constraints

```python
# Genomic coordinates validation
CHROMOSOME_PATTERN = r'^(chr)?(1[0-9]|2[0-2]|[1-9]|X|Y|MT?)$'
POSITION_MIN = 1
POSITION_MAX = 300_000_000  # Approximate max human chromosome length

# String length constraints
SHORT_STRING_MAX = 100
MEDIUM_STRING_MAX = 500
LONG_STRING_MAX = 1000
TEXT_FIELD_MAX = 10000

# Numeric constraints
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0
WEIGHT_MIN = 0.0
WEIGHT_MAX = 1.0
```

## Example Usage

```python
# Example variant analysis request
analysis_request = VariantAnalysisCreate(
    analysis_id="ANALYSIS_12345",
    case_uid="CASE_001",
    patient_uid="PAT_001",
    single_variant=VariantInput(
        genomic_coordinates=GenomicCoordinates(
            chromosome="17",
            position=7674220,
            reference="G",
            alternate="A"
        )
    ),
    cancer_type="lung_adenocarcinoma",
    oncotree_id="LUAD",
    tissue="primary_tumor"
)

# Validate the request
try:
    validated_request = analysis_request.model_validate(analysis_request.model_dump())
    print("Request is valid")
except ValidationError as e:
    print(f"Validation error: {e}")

# Example tiering result
tiering = TieringResult(
    tiering_id="TIER_001",
    variant_id="VAR_001",
    guideline_framework=GuidelineFramework.AMP_ACMG,
    tier_assigned="Tier_I",
    confidence_score=0.95,
    rules_invoked=[
        RuleInvocation(
            invocation_id="RULE_001",
            tiering_id="TIER_001",
            rule_id="PS1",
            evidence_strength=EvidenceStrength.STRONG,
            applied_weight=0.8,
            evidence_sources=["ClinVar:12345"]
        )
    ],
    tiering_timestamp=datetime.utcnow()
)
```

This comprehensive schema validation framework provides type safety, data integrity, and clear API contracts throughout the annotation engine application.