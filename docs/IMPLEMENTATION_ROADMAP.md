# Annotation Engine Implementation Roadmap

## Executive Summary

This roadmap outlines the complete implementation plan for the Annotation Engine, a reproducible CLI that processes VCF files (tumor-only or tumor-normal) through comprehensive annotation, tiering, and clinical interpretation. The system generates machine-readable JSON output with variant annotations, guideline-based tiers (OncoKB, CGC/VICC, AMP/ASCO 2017), and 8 types of canned text for clinical reporting.

## Key Documentation Links

### Foundation Documents
- **[ANNOTATION_BLUEPRINT.md](./ANNOTATION_BLUEPRINT.md)** - Core technical specification (400 lines)
- **[CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md)** - KB to guideline mappings (957 lines)
- **[RULES_IMPLEMENTATION.md](./RULES_IMPLEMENTATION.md)** - Clinical rule engine design

### Current Phase References
- **Phase 2A (Current)**: [SCHEMA_VALIDATION.md](./SCHEMA_VALIDATION.md), [VCF_PARSING.md](./VCF_PARSING.md), [TN_VERSUS_TO.md](./TN_VERSUS_TO.md)
- **Phase 2B**: [KB_DOWNLOAD_BLUEPRINT.md](./KB_DOWNLOAD_BLUEPRINT.md), [KB_IMPLEMENTATION_GUIDE.md](./KB_IMPLEMENTATION_GUIDE.md)
- **Phase 2C**: [CANNED_TEXT_TYPES.md](./CANNED_TEXT_TYPES.md), [KB_TO_CANNED_TEXT_MAPPING.md](./KB_TO_CANNED_TEXT_MAPPING.md)

## Core Architecture Overview

### Input Processing Flow
1. **VCF Input** → Line-by-line variant processing
2. **Input Validation** → Variant validity checks
3. **Additional Arguments**:
   - Patient UID
   - Case ID 
   - Disease name (OncoTree code)
   - Sample type (tumor-only vs tumor-normal, determined by VCF count)
   
### Annotation Pipeline
1. **Knowledge Base Integration** → Comprehensive variant annotation
2. **Diagnosis-Specific Processing** → Some annotations require dx context
3. **Separate Pathways**:
   - Tumor-only workflow (specific KB priorities)
   - Tumor-normal workflow (different KB emphasis)

### Output Generation
1. **Guideline Tiers** (3 types):
   - OncoKB
   - CGC/VICC
   - AMP/ASCO 2017
2. **Canned Text Comments** (8 types):
   - General Gene Info
   - Gene Dx Interpretation
   - General Variant Info
   - Variant Dx Interpretation
   - Incidental/Secondary Findings
   - Chromosomal Alteration Interpretation
   - Pertinent Negatives
   - Biomarkers (TMB, MSI, expression)

### Data Management
- **Frontend Bundle**: variant-dx-annotation-tier-initial interp
- **Backend Storage**: Selected interpretations with timestamps
- **Database Content**: patient, variant, annotation, rule, interpretation data
- **Audit Trail**: From YAML configuration

## Current Implementation Status

### ✅ Phase 1 Complete (Core Engine)
- **VEP Runner** (820 lines) - Executes VEP and parses JSON
- **Evidence Aggregator** (1,395 lines) - KB integration and matching
- **Tier Assignment** (976 lines) - AMP/VICC scoring implementation
- **Performance**: 0.20 seconds for 4-variant VCF

### ✅ Additional Completed Features

#### Tumor-Normal vs Tumor-Only Workflow Separation
- **Analysis Type Detection**: Automatic detection based on VCF inputs
- **Dual VCF Input Support**: `--tumor-vcf` and `--normal-vcf` parameters
- **Separate Filter Classes**: `TumorNormalFilter` (direct subtraction) and `TumorOnlyFilter` (population AF + PoN)
- **Legacy Support**: Single VCF input defaults to tumor-only

#### Dynamic Somatic Confidence (DSC) Model
- **Evidence-Based Scoring**: Replaces flat penalties with sophisticated multi-module approach
- **Three Components**:
  1. VAF/Purity Consistency - Evaluates expected somatic patterns
  2. Somatic vs Germline Prior - Leverages hotspots, population DBs
  3. Genomic Context - Placeholder for future LOH/signature analysis
- **Tier Requirements**:
  - Tier I: DSC > 0.9 (near-certain somatic)
  - Tier II: DSC > 0.6 (likely somatic)
  - Tier III: DSC 0.2-0.6 (uncertain)
  - Filtered: DSC < 0.2 (likely germline)

#### Tumor Purity Integration
- **PURPLE-Inspired VAF-Based Estimation**: Adapted from HMF methodology
- **Multiple Data Sources** (priority order):
  1. HMF PURPLE output files (if available)
  2. User-provided metadata (`--tumor-purity`)
  3. Automatic VAF-based estimation
- **Algorithm Features**:
  - Heterozygous peak detection (VAF ≈ purity/2)
  - Multiple scenario evaluation (het, LOH, subclonal)
  - Quality-based variant filtering
  - Confidence scoring for estimates

#### Enhanced Tier System with Sub-classifications
- **AMP/ASCO/CAP 2017 Tiers**:
  - Tier IA: FDA-approved therapies
  - Tier IB: Professional guidelines
  - Tier IIC: Clinical evidence (trials, studies)
  - Tier IID: Preclinical evidence
  - Tier IIE: Investigational/Emerging Evidence
  - Tier III: VUS
  - Tier IV: Benign/Likely Benign

#### VICC/CGC 2022 Evidence Codes
- **Evidence Strength Scoring**:
  - Very Strong (8 points): OVS1
  - Strong (4 points): OS1, OS2, OS3
  - Moderate (2 points): OM1, OM2, OM3, OM4
  - Supporting (1 point): OP1, OP2, OP3, OP4
  - Benign (negative): SBVS1, SBS1, SBS2, SBP1

#### Clinical Reporting Features
- **Canned Text Generation**: Nine standardized text types implemented
- **Dynamic Text**: Based on DSC scores
- **Mandatory Disclaimers**: For tumor-only analysis

#### Testing Infrastructure
- **Purity Integration Tests**: VAF-based estimation, metadata integration, PURPLE parsing
- **DSC Calculation Tests**: High/moderate/low confidence scenarios, tier validation
- **Tier Assignment Tests**: Multi-context assignment, DSC modulation, evidence integration

#### Configuration & CLI
- **CLI Parameters Added**:
  - `--tumor-vcf` / `--normal-vcf`: Dual VCF input
  - `--tumor-purity`: Direct purity input (0.0-1.0)
  - `--purple-output`: Path to HMF PURPLE results
- **Validation Schemas**: Updated with purity fields and analysis type detection

### 🚧 Phase 2 In Progress (Production Features)
- VEP Docker integration
- Full knowledge base loading
- Clinical validation framework
- End-to-end pipeline wiring

## Detailed Implementation Plan

### Phase 2A: Input Processing & Validation (2 weeks)
**📚 Key Documentation:** [SCHEMA_VALIDATION.md](./SCHEMA_VALIDATION.md), [VCF_PARSING.md](./VCF_PARSING.md), [TN_VERSUS_TO.md](./TN_VERSUS_TO.md), [WORKFLOW_KB_MAPPING.md](./WORKFLOW_KB_MAPPING.md)

#### Week 1: Enhanced Input Handler
- [x] ~~VCF format validation~~ (Completed in vcf_filtering.py)
- [x] ~~Multi-sample detection (tumor-normal vs tumor-only)~~ (Completed - AnalysisType enum)
- [ ] Create `input_validator.py` module
  - Additional required field validation (see [SCHEMA_VALIDATION.md](./SCHEMA_VALIDATION.md))
- [ ] Implement `patient_context.py`
  - Patient UID management
  - Case ID handling
  - OncoTree disease code validation (see [CONFIGURATION_MANAGEMENT.md](./CONFIGURATION_MANAGEMENT.md))
  - Sample type determination logic

#### Week 2: Workflow Router
- [x] ~~Tumor-only pathway definition~~ (Completed - TumorOnlyFilter)
- [x] ~~Tumor-normal pathway definition~~ (Completed - TumorNormalFilter)
- [ ] Create `workflow_router.py`
  - KB priority configuration per pathway (see [WORKFLOW_KB_MAPPING.md](./WORKFLOW_KB_MAPPING.md))
- [ ] Update `cli.py` with new arguments
  - `--patient-uid`
  - `--oncotree-code`
  - [x] ~~`--tumor-vcf` / `--normal-vcf`~~ (Already implemented)
  - [x] ~~`--tumor-purity`~~ (Already implemented)

### Phase 2B: Knowledge Base Enhancement (3 weeks)
**📚 Key Documentation:** [KB_DOWNLOAD_BLUEPRINT.md](./KB_DOWNLOAD_BLUEPRINT.md), [KB_IMPLEMENTATION_GUIDE.md](./KB_IMPLEMENTATION_GUIDE.md), [CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md), [VEP_PLUGIN_KB_ANALYSIS.md](./VEP_PLUGIN_KB_ANALYSIS.md)

#### Week 3: KB Loading Infrastructure
- [ ] Implement lazy-loading for all KBs in `evidence_aggregator.py` (see [KB_IMPLEMENTATION_GUIDE.md](./KB_IMPLEMENTATION_GUIDE.md))
- [ ] Create KB validation scripts
- [ ] Add KB version tracking
- [ ] Implement KB update notifications

#### Week 4: Diagnosis-Specific Annotation
- [ ] Create `dx_specific_annotator.py`
  - OncoTree integration
  - Disease-specific gene panels
  - Tissue-specific interpretation rules (see [CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md))
- [ ] Update evidence aggregator for dx context
- [ ] Implement tumor type → driver gene mappings

#### Week 5: Pathway-Specific KB Prioritization
- [ ] Define KB importance scores per pathway (see [WORKFLOW_KB_MAPPING.md](./WORKFLOW_KB_MAPPING.md))
- [ ] Implement weighted evidence aggregation
- [x] ~~Create pathway-specific confidence calculations~~ (Completed - DSC model)
- [ ] Add pathway selection to tiering logic

### Phase 2C: Canned Text Generation (4 weeks)
**📚 Key Documentation:** [CANNED_TEXT_TYPES.md](./CANNED_TEXT_TYPES.md), [KB_TO_CANNED_TEXT_MAPPING.md](./KB_TO_CANNED_TEXT_MAPPING.md), [AMP_ASCO_TIERS_AND_EVIDENCE.md](./AMP_ASCO_TIERS_AND_EVIDENCE.md)

#### Week 6: Text Generation Framework
- [x] ~~Implement text generation base~~ (Completed - CannedTextGenerator in tiering.py)
- [ ] Create template system for each text type (see [CANNED_TEXT_TYPES.md](./CANNED_TEXT_TYPES.md))
- [ ] Add evidence-to-text mapping logic (see [KB_TO_CANNED_TEXT_MAPPING.md](./KB_TO_CANNED_TEXT_MAPPING.md))
- [x] ~~Implement confidence scoring for text generation~~ (Completed - DSC-based)

#### Week 7: Gene-Level Text Generators
- [ ] General Gene Info generator
  - NCBI Gene Info, HGNC, UniProt integration
  - Pfam domain descriptions
  - COSMIC CGC summaries
- [ ] Gene Dx Interpretation generator
  - Disease-specific gene roles
  - OncoKB gene-level annotations
  - Pathway context

#### Week 8: Variant-Level Text Generators
- [ ] General Variant Info generator
  - Technical variant descriptions
  - Population frequencies
  - Computational predictions
- [ ] Variant Dx Interpretation generator
  - ClinVar, CIViC, OncoKB integration
  - Hotspot analysis
  - Treatment implications

#### Week 9: Special Case Generators
- [ ] Incidental/Secondary Findings generator
  - ACMG-SF gene list checking
  - Germline pathogenicity assessment
- [ ] Chromosomal Alteration generator
  - CNV interpretation
  - Fusion detection and description
- [ ] Pertinent Negatives generator
  - Expected alterations not found
  - Coverage assessment
- [ ] Biomarkers generator
  - TMB calculation and interpretation
  - MSI status determination
  - Expression level bucketing

### Phase 2D: Output Bundle Generation (2 weeks)

#### Week 10: Bundle Creator
- [ ] Create `output_bundler.py`
  - Combine all annotations
  - Format guideline tiers
  - Package canned texts
  - Generate JSON structure
- [ ] Implement `interpretation_bundler.py`
  - Initial interpretation packaging
  - Evidence trail compilation
  - Confidence score aggregation

#### Week 11: Frontend Interface Preparation
- [ ] Define API contract for frontend
- [ ] Create example output bundles
- [ ] Document JSON schema
- [ ] Implement output validation

### Phase 3A: Database Integration (3 weeks)
**📚 Key Documentation:** [INTERP_DB_BLUEPRINT.md](./INTERP_DB_BLUEPRINT.md)

#### Week 12: Database Schema Design
- [x] ~~Design schema~~ (Completed - see db/models.py)
  - Patient information
  - Variant storage (non-duplicative)
  - Annotation results
  - Rule execution logs
  - Interpretation history
- [ ] Create migration scripts (see [INTERP_DB_BLUEPRINT.md](./INTERP_DB_BLUEPRINT.md))
- [ ] Implement connection pooling

#### Week 13: Database Operations
- [ ] Create `db_manager.py`
  - CRUD operations for all entities
  - Transaction management
  - Audit trail implementation (see [INTERP_DB_BLUEPRINT.md](./INTERP_DB_BLUEPRINT.md))
- [ ] Implement `interpretation_storage.py`
  - Store selected interpretations
  - Timestamp management
  - User tracking (from YAML)

#### Week 14: Query & Retrieval
- [ ] Implement case history queries
- [ ] Create interpretation audit trails
- [ ] Add variant recurrence tracking
- [ ] Build reporting queries

### Phase 3B: Backend API Development (3 weeks)
**📚 Key Documentation:** [API_ROUTING.md](./API_ROUTING.md), [FRONTEND_API_SCHEMA.md](./FRONTEND_API_SCHEMA.md)

#### Week 15: REST API Framework
- [ ] Set up FastAPI application (see [API_ROUTING.md](./API_ROUTING.md))
- [ ] Define API endpoints:
  - `/annotate` - Process VCF input
  - `/interpretations` - Store/retrieve interpretations
  - `/cases` - Case management
  - `/audit` - Audit trail access
- [ ] Implement authentication

#### Week 16: API Integration
- [ ] Connect API to annotation engine
- [ ] Implement async processing for large VCFs
- [ ] Add result caching (see [FRONTEND_API_SCHEMA.md](./FRONTEND_API_SCHEMA.md))
- [ ] Create WebSocket support for progress updates

#### Week 17: API Testing & Documentation
- [ ] Create comprehensive API tests
- [ ] Generate OpenAPI documentation
- [ ] Implement rate limiting
- [ ] Add monitoring endpoints

### Phase 3C: Clinical Validation Framework (2 weeks)
**📚 Key Documentation:** [TESTING_STRATEGY.md](./TESTING_STRATEGY.md), [CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md)

#### Week 18: Validation Infrastructure
- [ ] Create test case repository (see [TESTING_STRATEGY.md](./TESTING_STRATEGY.md))
- [ ] Implement concordance testing
- [ ] Add regression test suite
- [ ] Build performance benchmarks

#### Week 19: Clinical Test Cases
- [ ] Curate known variant interpretations
- [ ] Test against published cases
- [ ] Validate canned text generation
- [ ] Document validation results

### Phase 4: Production Deployment (2 weeks)
**📚 Key Documentation:** [DEPLOYMENT_BLUEPRINT.md](./DEPLOYMENT_BLUEPRINT.md), [CONFIGURATION_MANAGEMENT.md](./CONFIGURATION_MANAGEMENT.md)

#### Week 20: Containerization & Deployment
- [ ] Complete Docker setup (see [DEPLOYMENT_BLUEPRINT.md](./DEPLOYMENT_BLUEPRINT.md))
- [ ] Create docker-compose for full stack
- [ ] Implement CI/CD pipeline
- [ ] Add deployment scripts

#### Week 21: Monitoring & Maintenance
- [ ] Set up logging infrastructure
- [ ] Implement performance monitoring
- [ ] Create backup procedures
- [ ] Document operational procedures

## Success Metrics

### Phase 2 Completion Criteria
- [ ] All 8 canned text types generating accurately
- [ ] Tumor-only and tumor-normal pathways functioning
- [ ] All KBs integrated and validated
- [ ] Output bundles match frontend requirements

### Phase 3 Completion Criteria
- [ ] Database storing all non-KB data
- [ ] API handling concurrent requests
- [ ] Audit trail complete and queryable
- [ ] Frontend successfully consuming API

### Phase 4 Completion Criteria
- [ ] System deployed in production environment
- [ ] Performance meeting SLA requirements
- [ ] Monitoring and alerting active
- [ ] Documentation complete for operations

## Technical Debt & Future Enhancements

### Immediate Technical Debt
1. Standardize error handling across modules
2. Implement comprehensive logging
3. Add retry logic for external KB queries
4. Optimize memory usage for large VCFs

### Future Enhancements (Phase 5+)
1. **Frontend Development**
   - React-based clinical interface
   - Variant review workflow
   - Report generation UI
   
2. **Advanced Analytics**
   - Cohort analysis features
   - Variant recurrence tracking
   - Treatment outcome correlation
   
3. **Integration Capabilities**
   - EHR integration
   - LIMS connectivity
   - External report delivery
   
4. **ML/AI Features**
   - Interpretation suggestion ranking
   - Anomaly detection
   - Natural language generation improvements

## Resource Requirements

### Development Team
- 2 Backend Engineers (Python)
- 1 Database Engineer
- 1 DevOps Engineer
- 1 Clinical Informaticist (part-time)

### Infrastructure
- Development environment with GPU (for VEP)
- Production database server
- API hosting environment
- KB storage (minimum 100GB)

### External Dependencies
- VEP Docker image maintenance
- KB update subscriptions
- OncoTree access
- Clinical validation partners

## Risk Mitigation

### Technical Risks
1. **KB Version Conflicts**
   - Mitigation: Strict version pinning, compatibility matrix
   
2. **Performance Degradation**
   - Mitigation: Horizontal scaling, caching strategy
   
3. **Data Consistency**
   - Mitigation: Transaction management, validation checksums

### Clinical Risks
1. **Interpretation Accuracy**
   - Mitigation: Clinical validation framework, expert review
   
2. **Guideline Updates**
   - Mitigation: YAML-driven rules, version tracking
   
3. **Regulatory Compliance**
   - Mitigation: Audit trails, data governance policies

## Implementation Notes

### Key Design Principles
1. **Modularity**: Each component independently testable
2. **Configurability**: YAML-driven thresholds and rules
3. **Auditability**: Complete evidence trail for every decision
4. **Performance**: Sub-second response for typical VCFs
5. **Maintainability**: Clear separation of concerns

### Critical Success Factors
1. Comprehensive KB integration
2. Accurate pathway-specific logic
3. Clinically valid text generation
4. Robust database design
5. Intuitive API design

### Next Immediate Steps
1. Begin Phase 2A implementation (Week 1-2)
2. Set up development database
3. Create API specification draft
4. Establish clinical validation partners

## Documentation Maintenance Notes

### Recently Updated Documents
The following documentation has been updated:
- **KB_AND_PLUGIN_REGISTRY.md** - Central registry for all KB locations and plugin status
- **VEP_PLUGINS.md** - Actual VEP plugin configurations and status
- **scripts/validate_knowledge_bases.py** - Updated with correct KB paths

### Living Documents
- **This IMPLEMENTATION_ROADMAP.md** - Primary planning document, update weekly
- **TODO.md** - Current sprint tasks, update daily
- **CLAUDE.md** - Development guidelines, update as needed

---

*This roadmap represents the complete vision for the Annotation Engine from current state through full production deployment and future enhancements. Updates should be made as implementation progresses and requirements evolve.*