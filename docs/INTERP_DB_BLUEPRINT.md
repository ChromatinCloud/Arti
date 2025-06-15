# Clinical Interpretation Database Schema Blueprint

## Overview

This document defines the database schema for storing clinical variant interpretations, audit trails, and supporting metadata. The database serves as the system of record for all interpretation activities while maintaining minimal duplication with the comprehensive knowledge base library.

## Technology Stack

- **Database**: SQL (PostgreSQL recommended for production, SQLite for development)
- **ORM**: SQLAlchemy for database operations and model definitions
- **Schema Validation**: Pydantic v2 for API request/response validation
- **Migrations**: Alembic for database schema versioning and migrations
- **API Framework**: FastAPI for REST API endpoints
- **ASGI Server**: Uvicorn for production deployment
- **Dependency Management**: Poetry for package management and virtual environments

## Design Principles

1. **Minimal KB Duplication**: Reference external KB via fast lookup keys rather than storing redundant data
2. **Complete Audit Trail**: Every query, interpretation, and decision must be fully auditable
3. **Fast Variant-Dx Lookups**: Optimized for retrieving variant-diagnosis pairs and interpretation triplets
4. **Flexible Interpretation Storage**: Support for multiple guideline frameworks (AMP/ACMG, CGC/VICC, OncoKB)
5. **Canned Text Management**: Standardized interpretation text templates for consistency

## Core Entity Relationships

```
Patient → Case → Variant Analysis → Variant Interpretation
    ↓        ↓           ↓                    ↓
   UID   Tissue/Dx   Tiering Results    Selected Interp
```

## SQLAlchemy Models Structure

### Base Configuration
```python
# src/annotation_engine/db/base.py
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
metadata = MetaData()

# Convention for naming constraints
metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
```

## Database Schema

### 1. Patients Table
```sql
CREATE TABLE patients (
    patient_uid VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**SQLAlchemy Model:**
```python
class Patient(Base):
    __tablename__ = "patients"
    
    patient_uid = Column(String(255), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cases = relationship("Case", back_populates="patient")
```

**Pydantic Schema:**
```python
class PatientBase(BaseModel):
    patient_uid: str

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### 2. Cases Table
```sql
CREATE TABLE cases (
    case_uid VARCHAR(255) PRIMARY KEY,
    patient_uid VARCHAR(255) NOT NULL,
    tissue VARCHAR(100),
    diagnosis VARCHAR(500),
    oncotree_id VARCHAR(50),
    technical_notes TEXT,
    qc_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (patient_uid) REFERENCES patients(patient_uid),
    INDEX idx_patient_case (patient_uid, case_uid),
    INDEX idx_oncotree (oncotree_id)
);
```

**SQLAlchemy Model:**
```python
class Case(Base):
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
    
    # Indexes
    __table_args__ = (
        Index("idx_patient_case", "patient_uid", "case_uid"),
        Index("idx_oncotree", "oncotree_id"),
    )
```

### 3. Variant Analyses Table
```sql
CREATE TABLE variant_analyses (
    analysis_id VARCHAR(255) PRIMARY KEY,
    case_uid VARCHAR(255) NOT NULL,
    vcf_file_path VARCHAR(500),
    vcf_file_hash VARCHAR(64),
    total_variants_input INTEGER,
    variants_passing_qc INTEGER,
    kb_version_snapshot TEXT, -- JSON blob with all KB versions/dates
    vep_version VARCHAR(50),
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_uid) REFERENCES cases(case_uid),
    INDEX idx_case_analysis (case_uid, analysis_date),
    INDEX idx_kb_version (kb_version_snapshot(255))
);
```

**SQLAlchemy Model:**
```python
class VariantAnalysis(Base):
    __tablename__ = "variant_analyses"
    
    analysis_id = Column(String(255), primary_key=True)
    case_uid = Column(String(255), ForeignKey("cases.case_uid"), nullable=False)
    vcf_file_path = Column(String(500))
    vcf_file_hash = Column(String(64))
    total_variants_input = Column(Integer)
    variants_passing_qc = Column(Integer)
    kb_version_snapshot = Column(JSON)  # SQLAlchemy JSON type
    vep_version = Column(String(50))
    analysis_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="variant_analyses")
    variants = relationship("Variant", back_populates="analysis")
    
    # Indexes
    __table_args__ = (
        Index("idx_case_analysis", "case_uid", "analysis_date"),
        Index("idx_kb_version", text("(kb_version_snapshot->>'$.version')")),  # JSON path index
    )
```

### 4. Variants Table
```sql
CREATE TABLE variants (
    variant_id VARCHAR(255) PRIMARY KEY,
    analysis_id VARCHAR(255) NOT NULL,
    chromosome VARCHAR(10),
    position BIGINT,
    reference_allele VARCHAR(1000),
    alternate_allele VARCHAR(1000),
    variant_type VARCHAR(50),
    gene_symbol VARCHAR(100),
    transcript_id VARCHAR(100),
    hgvsc VARCHAR(500),
    hgvsp VARCHAR(500),
    consequence VARCHAR(200),
    vcf_info JSON, -- Store complete VCF INFO field
    vep_annotations JSON, -- Store complete VEP output for this variant
    
    FOREIGN KEY (analysis_id) REFERENCES variant_analyses(analysis_id),
    INDEX idx_analysis_variant (analysis_id, variant_id),
    INDEX idx_gene_variant (gene_symbol, chromosome, position),
    INDEX idx_coordinates (chromosome, position, reference_allele(100), alternate_allele(100))
);
```

### 5. Tiering Results Table
```sql
CREATE TABLE tiering_results (
    tiering_id VARCHAR(255) PRIMARY KEY,
    variant_id VARCHAR(255) NOT NULL,
    guideline_framework ENUM('AMP_ACMG', 'CGC_VICC', 'ONCOKB') NOT NULL,
    tier_assigned VARCHAR(20),
    confidence_score DECIMAL(5,4),
    rules_invoked JSON, -- Array of rule IDs that fired
    rule_evidence JSON, -- Evidence supporting each rule
    kb_lookups_performed JSON, -- What KB queries were made
    tiering_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id),
    INDEX idx_variant_tiering (variant_id, guideline_framework),
    INDEX idx_tier_confidence (tier_assigned, confidence_score),
    UNIQUE KEY unique_variant_guideline (variant_id, guideline_framework)
);
```

**SQLAlchemy Model:**
```python
from enum import Enum

class GuidelineFramework(str, Enum):
    AMP_ACMG = "AMP_ACMG"
    CGC_VICC = "CGC_VICC"
    ONCOKB = "ONCOKB"

class TieringResult(Base):
    __tablename__ = "tiering_results"
    
    tiering_id = Column(String(255), primary_key=True)
    variant_id = Column(String(255), ForeignKey("variants.variant_id"), nullable=False)
    guideline_framework = Column(Enum(GuidelineFramework), nullable=False)
    tier_assigned = Column(String(20))
    confidence_score = Column(Numeric(5, 4))
    rules_invoked = Column(JSON)
    rule_evidence = Column(JSON)
    kb_lookups_performed = Column(JSON)
    tiering_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    variant = relationship("Variant", back_populates="tiering_results")
    
    # Constraints and indexes
    __table_args__ = (
        Index("idx_variant_tiering", "variant_id", "guideline_framework"),
        Index("idx_tier_confidence", "tier_assigned", "confidence_score"),
        UniqueConstraint("variant_id", "guideline_framework", name="unique_variant_guideline"),
    )
```

### 6. Canned Interpretations Table
```sql
CREATE TABLE canned_interpretations (
    template_id VARCHAR(255) PRIMARY KEY,
    guideline_framework ENUM('AMP_ACMG', 'CGC_VICC', 'ONCOKB') NOT NULL,
    tier VARCHAR(20) NOT NULL,
    interpretation_text TEXT NOT NULL,
    clinical_significance VARCHAR(100),
    therapeutic_implications TEXT,
    version VARCHAR(20),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_framework_tier (guideline_framework, tier),
    UNIQUE KEY unique_framework_tier_version (guideline_framework, tier, version)
);
```

### 7. Variant Interpretations Table
```sql
CREATE TABLE variant_interpretations (
    interpretation_id VARCHAR(255) PRIMARY KEY,
    variant_id VARCHAR(255) NOT NULL,
    case_uid VARCHAR(255) NOT NULL,
    guideline_framework ENUM('AMP_ACMG', 'CGC_VICC', 'ONCOKB') NOT NULL,
    tiering_id VARCHAR(255), -- Links to the tiering that informed this interpretation
    selected_template_id VARCHAR(255), -- If using canned text
    custom_interpretation TEXT, -- If using custom text
    clinical_significance VARCHAR(100),
    therapeutic_implications TEXT,
    confidence_level ENUM('HIGH', 'MEDIUM', 'LOW'),
    interpreter_notes TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id),
    FOREIGN KEY (case_uid) REFERENCES cases(case_uid),
    FOREIGN KEY (tiering_id) REFERENCES tiering_results(tiering_id),
    FOREIGN KEY (selected_template_id) REFERENCES canned_interpretations(template_id),
    INDEX idx_variant_dx_interp (variant_id, case_uid, guideline_framework),
    INDEX idx_case_interpretations (case_uid, created_at),
    UNIQUE KEY unique_variant_case_framework (variant_id, case_uid, guideline_framework)
);
```

### 8. Audit Log Table
```sql
CREATE TABLE audit_log (
    log_id VARCHAR(255) PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(255) NOT NULL,
    action ENUM('INSERT', 'UPDATE', 'DELETE', 'SELECT') NOT NULL,
    old_values JSON,
    new_values JSON,
    user_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    
    INDEX idx_table_record (table_name, record_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_session (session_id)
);
```

## Alembic Migration Strategy

### Migration File Structure
```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_audit_triggers.py
│   └── 003_add_performance_indexes.py
├── env.py
├── script.py.mako
└── alembic.ini
```

### Sample Migration
```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create patients table
    op.create_table('patients',
        sa.Column('patient_uid', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('patient_uid')
    )
    
    # Additional table creation...

def downgrade():
    op.drop_table('patients')
    # Additional table drops...
```

## FastAPI Integration

### API Route Structure
```python
# src/annotation_engine/api/routes/interpretations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import VariantInterpretationCreate, VariantInterpretationResponse
from ..crud import variant_interpretations

router = APIRouter()

@router.post("/interpretations/", response_model=VariantInterpretationResponse)
async def create_interpretation(
    interpretation: VariantInterpretationCreate,
    db: Session = Depends(get_db)
):
    return variant_interpretations.create(db=db, obj_in=interpretation)

@router.get("/interpretations/variant/{variant_id}")
async def get_variant_interpretations(
    variant_id: str,
    db: Session = Depends(get_db)
):
    return variant_interpretations.get_by_variant(db=db, variant_id=variant_id)
```

## Fast Lookup Optimizations

### Key Query Patterns and Indexes

1. **Variant-Diagnosis Pairs**:
   ```sql
   -- Index: idx_variant_dx_pairs
   CREATE INDEX idx_variant_dx_pairs ON variant_interpretations 
   (variant_id, case_uid);
   ```

2. **Variant-Diagnosis-Interpretation Triplets**:
   ```sql
   -- Already covered by unique_variant_case_framework
   -- Supports: SELECT * FROM variant_interpretations 
   -- WHERE variant_id = ? AND case_uid = ? AND guideline_framework = ?
   ```

3. **Gene-Disease Combinations**:
   ```sql
   -- Cross-table query optimization
   CREATE INDEX idx_gene_oncotree ON cases (oncotree_id);
   -- Combined with idx_gene_variant on variants table
   ```

## KB Reference Strategy

Instead of duplicating KB data, store minimal sufficient statistics:

1. **OncoKB**: Store gene-alteration keys, reference by `oncokb_gene_id + alteration_hash`
2. **CIViC**: Store variant IDs, reference by `civic_variant_id`
3. **COSMIC**: Store mutation IDs, reference by `cosmic_mutation_id`
4. **dbNSFP**: Store coordinate-based keys, reference by `chr_pos_ref_alt_hash`
5. **CGC**: Store gene symbols, reference by `gene_symbol`

## Data Flow Architecture

### 1. Analysis Ingestion
```
VCF Input → VEP → Variant Analysis Record → Individual Variants → Tiering Results
```

### 2. Interpretation Workflow
```
Tiering Results → Available Templates → User Selection → Variant Interpretation Record
```

### 3. Audit Trail
```
Every Operation → Audit Log Entry → Complete Reconstruction Capability
```

## Development Workflow

### 1. Database Setup
```bash
# Install dependencies
poetry install

# Initialize Alembic
poetry run alembic init alembic

# Create migration
poetry run alembic revision --autogenerate -m "Initial schema"

# Apply migration
poetry run alembic upgrade head
```

### 2. FastAPI Server
```bash
# Run development server
poetry run uvicorn src.annotation_engine.api.main:app --reload

# Run production server
poetry run uvicorn src.annotation_engine.api.main:app --host 0.0.0.0 --port 8000
```

## Performance Considerations

1. **Partitioning**: Partition large tables by date ranges
2. **Archival**: Move old analyses to archive tables after configurable retention period
3. **Caching**: Implement application-level caching for frequent variant-dx lookups
4. **Read Replicas**: Use read replicas for reporting and audit queries
5. **Connection Pooling**: Configure SQLAlchemy with appropriate connection pool settings

## API Access Patterns

### Primary Queries
1. `get_variant_interpretation_history(variant_id, diagnosis)`
2. `get_case_summary(case_uid)`
3. `get_similar_interpretations(variant_id, oncotree_id)`
4. `audit_analysis_reconstruction(analysis_id)`

### Data Integrity
1. All foreign key constraints enforced via SQLAlchemy relationships
2. Pydantic schema validation on all API endpoints
3. Trigger-based audit logging (implemented via SQLAlchemy events)
4. Backup strategy with point-in-time recovery

## Confidence Scoring and ML Framework Architecture

### Dual Approach Strategy

The system implements both **explainable rule-based scoring** and **ML-based confidence estimation** to balance interpretability with quantitative accuracy.

#### 1. OncoVI-Style Explainable Engine
- **Rule Weights**: Each clinical rule has an assigned weight based on evidence strength
- **Transparency**: Complete audit trail of which rules fired and their individual contributions
- **Reproducibility**: Identical inputs always produce identical outputs with full explanation

#### 2. ML Confidence Framework (Implementation TBD)
- **Purpose**: Quantitative estimate of tier assignment correctness
- **Training Data**: Historical interpretations with known outcomes
- **Features**: Rule invocation patterns, evidence strength, variant characteristics
- **Output**: Probability score for tier assignment accuracy

### Extended Database Schema for Confidence Scoring

#### Rule Definitions Table
```sql
CREATE TABLE rule_definitions (
    rule_id VARCHAR(100) PRIMARY KEY,
    guideline_framework ENUM('AMP_ACMG', 'CGC_VICC', 'ONCOKB') NOT NULL,
    rule_name VARCHAR(200) NOT NULL,
    rule_description TEXT,
    base_weight DECIMAL(5,4), -- OncoVI-style base weight
    evidence_threshold VARCHAR(50), -- e.g., "strong", "moderate", "weak"
    rule_version VARCHAR(20),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_framework_rule (guideline_framework, rule_id),
    INDEX idx_active_rules (active, guideline_framework)
);
```

**SQLAlchemy Model:**
```python
class RuleDefinition(Base):
    __tablename__ = "rule_definitions"
    
    rule_id = Column(String(100), primary_key=True)
    guideline_framework = Column(Enum(GuidelineFramework), nullable=False)
    rule_name = Column(String(200), nullable=False)
    rule_description = Column(Text)
    base_weight = Column(Numeric(5, 4))
    evidence_threshold = Column(String(50))
    rule_version = Column(String(20))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    rule_invocations = relationship("RuleInvocation", back_populates="rule_definition")
```

#### Rule Invocations Table
```sql
CREATE TABLE rule_invocations (
    invocation_id VARCHAR(255) PRIMARY KEY,
    tiering_id VARCHAR(255) NOT NULL,
    rule_id VARCHAR(100) NOT NULL,
    evidence_strength ENUM('STRONG', 'MODERATE', 'WEAK', 'CONFLICTING'),
    applied_weight DECIMAL(5,4), -- Actual weight used (may differ from base_weight)
    evidence_sources JSON, -- KB sources that triggered this rule
    rule_context JSON, -- Additional context for rule firing
    
    FOREIGN KEY (tiering_id) REFERENCES tiering_results(tiering_id),
    FOREIGN KEY (rule_id) REFERENCES rule_definitions(rule_id),
    INDEX idx_tiering_rules (tiering_id, rule_id),
    INDEX idx_rule_strength (rule_id, evidence_strength)
);
```

#### Confidence Scores Table
```sql
CREATE TABLE confidence_scores (
    score_id VARCHAR(255) PRIMARY KEY,
    tiering_id VARCHAR(255) NOT NULL,
    scoring_method ENUM('ONCOVI_RULES', 'ML_MODEL', 'ENSEMBLE') NOT NULL,
    confidence_value DECIMAL(5,4), -- 0.0 to 1.0
    model_version VARCHAR(50), -- For ML models
    feature_importance JSON, -- What drove the confidence score
    calibration_data JSON, -- Model calibration metrics
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tiering_id) REFERENCES tiering_results(tiering_id),
    INDEX idx_tiering_confidence (tiering_id, scoring_method),
    INDEX idx_confidence_range (confidence_value, scoring_method)
);
```

#### ML Model Metadata Table
```sql
CREATE TABLE ml_models (
    model_id VARCHAR(255) PRIMARY KEY,
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(100), -- e.g., "random_forest", "neural_network", "ensemble"
    guideline_framework ENUM('AMP_ACMG', 'CGC_VICC', 'ONCOKB') NOT NULL,
    training_data_version VARCHAR(50),
    feature_set_version VARCHAR(50),
    model_artifact_path VARCHAR(500), -- Path to serialized model
    performance_metrics JSON, -- Accuracy, precision, recall, F1
    calibration_curve JSON, -- Calibration plot data
    feature_definitions JSON, -- What features the model expects
    deployed_at TIMESTAMP,
    deprecated_at TIMESTAMP,
    
    INDEX idx_active_models (deprecated_at, guideline_framework),
    INDEX idx_model_performance (model_type, guideline_framework)
);
```

### Confidence Scoring Workflow

#### 1. OncoVI-Style Explainable Scoring
```python
def calculate_oncovi_confidence(rule_invocations: List[RuleInvocation]) -> float:
    """
    Calculate confidence based on weighted rule contributions
    Similar to OncoVI's transparent scoring approach
    """
    total_weight = 0.0
    conflicting_weight = 0.0
    
    for invocation in rule_invocations:
        if invocation.evidence_strength == "CONFLICTING":
            conflicting_weight += invocation.applied_weight
        else:
            total_weight += invocation.applied_weight
    
    # Apply penalty for conflicting evidence
    confidence = max(0.0, total_weight - conflicting_weight) / max_possible_weight
    return min(1.0, confidence)
```

#### 2. ML Confidence Framework (Architecture)
```python
class VariantConfidenceModel:
    """
    ML model for predicting tier assignment confidence
    Implementation approach TBD - candidates include:
    - Gradient boosting (XGBoost, LightGBM)
    - Neural networks
    - Ensemble methods
    - Probabilistic models
    """
    
    def extract_features(self, variant: Variant, rules: List[RuleInvocation]) -> Dict:
        """Extract features for ML model prediction"""
        return {
            'rule_pattern': self._encode_rule_pattern(rules),
            'evidence_strength_distribution': self._calc_evidence_distribution(rules),
            'variant_characteristics': self._extract_variant_features(variant),
            'knowledge_base_coverage': self._assess_kb_coverage(variant),
            'historical_patterns': self._find_similar_cases(variant)
        }
    
    def predict_confidence(self, features: Dict) -> Tuple[float, Dict]:
        """
        Predict confidence and return feature importance
        Returns: (confidence_score, feature_importance_dict)
        """
        # Implementation TBD
        pass
```

### Explainability Requirements

#### Complete Audit Trail
Every confidence score must be fully explainable:

1. **Rule-Based Component**: 
   - Which rules fired
   - What evidence triggered each rule
   - How weights were calculated
   - Final weighted score computation

2. **ML Component** (when implemented):
   - Model version used
   - Feature values input to model
   - Feature importance scores
   - Model calibration data

#### API Endpoints for Explainability
```python
@router.get("/interpretations/{interpretation_id}/explanation")
async def get_interpretation_explanation(
    interpretation_id: str,
    include_ml_features: bool = False,
    db: Session = Depends(get_db)
):
    """
    Return complete explanation of how tier and confidence were calculated
    """
    return {
        "tier_assignment": {...},
        "rule_invocations": [...],
        "confidence_scores": {
            "oncovi_explainable": 0.85,
            "ml_estimated": 0.78,  # If available
            "ensemble": 0.82
        },
        "explanation": {
            "rules_fired": [...],
            "evidence_sources": [...],
            "weight_calculations": {...},
            "ml_features": {...} if include_ml_features else None
        }
    }
```

### Future ML Implementation Considerations

#### Training Data Requirements
- Historical interpretations with known clinical outcomes
- Expert consensus labels for training
- Variant characteristics and KB evidence patterns
- Cross-validation across different cancer types

#### Model Selection Criteria (TBD)
- **Interpretability**: SHAP values, feature importance
- **Calibration**: Reliable probability estimates
- **Performance**: Accuracy on held-out validation sets
- **Robustness**: Performance across different variant types

#### Deployment Strategy
- A/B testing framework for model comparison
- Gradual rollout with expert oversight
- Continuous monitoring and retraining pipeline
- Fallback to rule-based scoring if ML unavailable

## Migration and Versioning Strategy

1. **Schema Versioning**: Track schema version via Alembic
2. **Backward Compatibility**: Maintain compatibility for at least 2 major versions
3. **Data Migration**: Automated migration scripts via Alembic
4. **Rollback Capability**: Full rollback support for failed migrations

This schema provides the foundation for comprehensive clinical interpretation tracking while maintaining performance and audit requirements using modern Python tooling. The dual confidence scoring approach ensures both explainability and quantitative rigor in tier assignments.