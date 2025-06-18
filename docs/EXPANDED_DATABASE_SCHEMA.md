# Expanded Database Schema for Comprehensive KB Integration

**Date**: 2025-06-18  
**Status**: Implemented  
**Schema Version**: 2.0  

## Overview

The expanded database schema extends the original 8-table design to 21 tables, adding comprehensive support for:

1. **ClinVar Integration** - Full clinical significance tracking with review status
2. **OncoKB Integration** - Therapeutic annotations with evidence levels  
3. **Citation System** - Literature tracking with reliability tiers
4. **Therapy Management** - Comprehensive drug information with interactions
5. **Enhanced Text System** - Template versioning with citation integration
6. **Performance Caching** - Intelligent caching for expensive KB queries

## Schema Statistics

- **Total Tables**: 21 (13 new + 8 original)
- **Original Core Tables**: 8 
- **New Expanded Tables**: 13
- **Estimated Storage**: 10-50GB for full KB integration
- **Expected Performance**: Sub-second queries with proper indexing

## Table Categories

### 🏗️ Core Tables (8) - Original Schema
- `patients` - Patient information
- `cases` - Clinical case information  
- `variant_analyses` - Analysis run metadata
- `variants` - Individual variant data
- `tiering_results` - Guideline-based tier assignments
- `canned_interpretations` - Template interpretations
- `variant_interpretations` - Final clinical interpretations
- `audit_log` - Comprehensive audit trail

### 🧬 ClinVar Integration (2 tables)
- `clinvar_variants` - ClinVar annotations with full metadata
- `clinvar_citations` - ClinVar-specific literature citations

### 💊 OncoKB Integration (2 tables)  
- `oncokb_genes` - OncoKB gene-level annotations
- `oncokb_therapeutic_annotations` - Therapeutic evidence with levels

### 📚 Citations & Literature (2 tables)
- `citation_sources` - Master source catalog with reliability tiers
- `literature_citations` - Literature with comprehensive metadata

### 💉 Therapy & Drug Information (3 tables)
- `drug_classes` - Hierarchical drug classification
- `therapies` - Comprehensive drug information
- `drug_interactions` - Drug-drug interaction tracking

### 📝 Enhanced Text System (3 tables)
- `text_templates` - Versioned templates with citation support
- `generated_texts` - Generated text instances with provenance
- `text_citations` - Citations embedded in generated text

### ⚡ Performance & Caching (1 table)
- `kb_cache` - Intelligent caching for expensive KB queries

## Key Schema Enhancements

### 1. ClinVar Integration Capabilities

```sql
-- Full ClinVar variant tracking
CREATE TABLE clinvar_variants (
    clinvar_variant_id VARCHAR(50) PRIMARY KEY,
    variant_id VARCHAR(255) REFERENCES variants(variant_id),
    variation_id INTEGER NOT NULL,                    -- ClinVar VariationID
    clinical_significance ENUM(ClinVarSignificance), -- Pathogenic, VUS, etc.
    review_status ENUM(ClinVarReviewStatus),         -- Expert panel, etc.
    star_rating INTEGER,                             -- 0-4 star quality
    condition_names JSON,                            -- Associated conditions
    conflicting_interpretations JSON,                -- Interpretation conflicts
    -- ... additional ClinVar metadata
);
```

**Capabilities:**
- Track all ClinVar submissions and conflicts
- Review status and star rating quality metrics
- Condition and phenotype associations
- Submitter information and assertion methods

### 2. OncoKB Therapeutic Integration

```sql
-- OncoKB therapeutic annotations with evidence levels
CREATE TABLE oncokb_therapeutic_annotations (
    annotation_id VARCHAR(255) PRIMARY KEY,
    variant_id VARCHAR(255) REFERENCES variants(variant_id),
    evidence_level ENUM(OncoKBEvidenceLevel),        -- LEVEL_1, LEVEL_2, etc.
    cancer_type VARCHAR(200),                        -- Tumor type specificity
    fda_approved BOOLEAN DEFAULT FALSE,              -- FDA approval status
    therapeutic_implication TEXT,                    -- Clinical implications
    supporting_pmids JSON,                           -- Literature support
    -- ... additional therapeutic metadata
);
```

**Capabilities:**
- FDA-approved vs investigational therapies
- Tumor type-specific annotations
- Resistance mutation tracking
- Evidence level hierarchies (1, 2, 3A, 3B, 4, R1, R2)

### 3. Comprehensive Citation System

```sql
-- Literature citations with reliability tiers
CREATE TABLE literature_citations (
    citation_id VARCHAR(255) PRIMARY KEY,
    pmid VARCHAR(20) UNIQUE,                         -- PubMed ID
    title TEXT NOT NULL,                             -- Publication title
    source_id VARCHAR(100) REFERENCES citation_sources(source_id),
    impact_score NUMERIC(5,2),                       -- Citation impact
    evidence_strength VARCHAR(50),                   -- Evidence quality
    -- ... comprehensive publication metadata
);

-- Source reliability catalog
CREATE TABLE citation_sources (
    source_id VARCHAR(100) PRIMARY KEY,
    source_name VARCHAR(200) NOT NULL,
    reliability_tier ENUM(SourceReliability),        -- Tier 1-5 reliability
    quality_score NUMERIC(3,2),                      -- 0.0-1.0 quality
    citation_format VARCHAR(500),                    -- Formatting template
    -- ... source quality metadata
);
```

**Capabilities:**
- 5-tier source reliability system (FDA > Guidelines > Expert > Community > Computational)
- Automatic citation formatting and numbering
- Impact factor and quality scoring
- Literature mining integration

### 4. Advanced Therapy Management

```sql
-- Comprehensive drug information
CREATE TABLE therapies (
    therapy_id VARCHAR(255) PRIMARY KEY,
    drug_name VARCHAR(200) NOT NULL,
    generic_names JSON,                              -- Array of generic names
    brand_names JSON,                                -- Array of brand names
    mechanism_of_action TEXT,                        -- MOA description
    molecular_targets JSON,                          -- Protein targets
    fda_approval_status VARCHAR(50),                 -- Approval status
    drugbank_id VARCHAR(20),                         -- External identifiers
    -- ... comprehensive drug metadata
);

-- Drug interaction tracking
CREATE TABLE drug_interactions (
    interaction_id VARCHAR(255) PRIMARY KEY,
    therapy_id VARCHAR(255) REFERENCES therapies(therapy_id),
    interacting_therapy_id VARCHAR(255) REFERENCES therapies(therapy_id),
    interaction_type VARCHAR(100),                   -- major, moderate, minor
    clinical_effect TEXT,                            -- Interaction effects
    management_recommendation TEXT,                  -- Clinical guidance
    -- ... interaction metadata
);
```

**Capabilities:**
- Hierarchical drug classification (targeted, immuno, chemo)
- Drug-drug interaction tracking
- FDA approval status and dates
- Mechanism of action and target pathways

### 5. Enhanced Text Generation System

```sql
-- Versioned text templates with citation support
CREATE TABLE text_templates (
    template_id VARCHAR(255) PRIMARY KEY,
    template_type ENUM(TextTemplateType),            -- 8 canned text types
    template_content TEXT NOT NULL,                  -- Template with placeholders
    confidence_factors JSON,                         -- Field confidence weights
    cancer_types JSON,                               -- Applicable cancer types
    version VARCHAR(20) NOT NULL,                    -- Template version
    -- ... template metadata
);

-- Generated text with full provenance
CREATE TABLE generated_texts (
    generated_text_id VARCHAR(255) PRIMARY KEY,
    variant_id VARCHAR(255) REFERENCES variants(variant_id),
    template_id VARCHAR(255) REFERENCES text_templates(template_id),
    generated_content TEXT NOT NULL,                 -- Final generated text
    confidence_score NUMERIC(3,2),                   -- Generation confidence
    evidence_sources JSON,                           -- Evidence source IDs
    generation_context JSON,                         -- Context data used
    -- ... generation metadata
);
```

**Capabilities:**
- Template versioning and management
- Citation integration with generated text
- Confidence scoring based on evidence completeness
- Cancer-specific text variations
- Full generation provenance tracking

## Performance Considerations

### Indexing Strategy

**Primary Performance Indexes:**
```sql
-- Variant lookups (most common query pattern)
CREATE INDEX idx_variant_comprehensive ON variants(gene_symbol, chromosome, position);
CREATE INDEX idx_clinvar_variant_lookup ON clinvar_variants(variant_id, clinical_significance);
CREATE INDEX idx_oncokb_variant_therapy ON oncokb_therapeutic_annotations(variant_id, evidence_level);

-- Literature and citation performance
CREATE INDEX idx_literature_pmid_impact ON literature_citations(pmid, impact_score);
CREATE INDEX idx_citation_reliability ON citation_sources(reliability_tier, quality_score);

-- Text generation performance  
CREATE INDEX idx_generated_text_variant_type ON generated_texts(variant_id, text_type);
CREATE INDEX idx_template_active_type ON text_templates(is_active, template_type);

-- Caching performance
CREATE INDEX idx_kb_cache_lookup ON kb_cache(cache_key, kb_source, expires_at);
```

### Storage Estimates

| Table Category | Estimated Size | Growth Rate |
|----------------|----------------|-------------|
| Core Tables | 1-5 GB | Linear with cases |
| ClinVar Integration | 5-15 GB | ~20% annually |
| OncoKB Integration | 2-8 GB | ~30% annually |
| Literature Citations | 3-10 GB | ~15% annually |
| Therapy Information | 1-3 GB | ~10% annually |
| Generated Texts | 500 MB - 2 GB | Linear with usage |
| KB Cache | 500 MB - 5 GB | Stable (with TTL) |
| **Total Estimated** | **10-50 GB** | **15-25% annually** |

### Query Performance Targets

- **Variant lookup**: <50ms
- **ClinVar annotation**: <100ms  
- **OncoKB therapeutic**: <100ms
- **Citation formatting**: <10ms
- **Text generation**: <200ms
- **Cache retrieval**: <5ms

## Data Integration Flows

### 1. ClinVar Data Ingestion
```
ClinVar XML/TSV → Parse submissions → Extract conflicts → Store with metadata → Index for search
```

### 2. OncoKB Integration
```
OncoKB API → Therapeutic annotations → Evidence levels → Tumor type mapping → Store with versioning
```

### 3. Literature Processing
```
PubMed API → Citation metadata → Source reliability → Impact scoring → Full-text analysis → Storage
```

### 4. Text Generation Pipeline
```
Evidence gathering → Template selection → Citation integration → Confidence scoring → Storage with provenance
```

## Migration Strategy

### Phase 1: Core Schema (✅ Complete)
- Implement original 8 tables
- Basic tiering and interpretation functionality

### Phase 2: Expanded Schema (🚧 Current)
- Add ClinVar and OncoKB integration tables
- Implement citation system
- Enhanced text generation

### Phase 3: Production Optimization (📅 Next)
- Performance tuning and indexing
- Caching layer implementation
- Data archival and cleanup

### Phase 4: Advanced Features (📅 Future)
- Real-time data synchronization
- Machine learning model integration
- Advanced analytics and reporting

## Compliance and Security

### HIPAA Compliance
- Patient data encryption at rest and in transit
- Audit trail for all patient data access
- Data retention and deletion policies

### Data Integrity
- Foreign key constraints enforced
- JSON schema validation where applicable
- Comprehensive audit logging

### Performance Monitoring
- Query performance metrics
- Cache hit/miss ratios
- Data freshness indicators

## API Impact

### New Endpoints Required
- `/clinvar/variants/{variant_id}` - ClinVar annotations
- `/oncokb/therapeutic/{variant_id}` - OncoKB therapeutic data
- `/citations/literature/{pmid}` - Literature citations
- `/therapies/drug/{drug_name}` - Drug information
- `/text/generate/{text_type}` - Enhanced text generation
- `/cache/stats` - Cache performance metrics

### Updated Endpoints
- `/variants/{variant_id}` - Include expanded annotations
- `/interpretations/{interpretation_id}` - Include citation data
- `/cases/{case_id}/summary` - Enhanced summary with new data

## Conclusion

The expanded schema provides a comprehensive foundation for integrating major knowledge bases while maintaining performance and clinical utility. The design supports:

- **Scalability**: Handles large-scale KB data (millions of variants)
- **Performance**: Sub-second queries with proper indexing
- **Flexibility**: Extensible design for future KB additions
- **Quality**: Citation tracking and confidence scoring
- **Compliance**: Full audit trail and data governance

**Total Enhancement**: 162.5% increase in schema coverage (13 new tables + enhanced functionality)

---
*Schema designed for clinical-grade variant interpretation with comprehensive KB integration*