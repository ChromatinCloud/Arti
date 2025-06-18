# Annotation Engine Implementation Roadmap

## Executive Summary

This roadmap outlines the complete implementation plan for the Annotation Engine, a reproducible CLI that processes VCF files (tumor-only or tumor-normal) through comprehensive annotation, tiering, and clinical interpretation. The system generates machine-readable JSON output with variant annotations, guideline-based tiers (OncoKB, CGC/VICC, AMP/ASCO 2017), and 8 types of canned text for clinical reporting.

## Key Documentation Links

### Foundation Documents
- **[ANNOTATION_BLUEPRINT.md](./ANNOTATION_BLUEPRINT.md)** - Core technical specification (400 lines)
- **[CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md)** - KB to guideline mappings (957 lines)
- **[RULES_IMPLEMENTATION.md](./RULES_IMPLEMENTATION.md)** - Clinical rule engine design
- **[RULES_IMPLEMENTATION_V2.md](./RULES_IMPLEMENTATION_V2.md)** - Updated rules with CGC/VICC implementation

### New Phase 2 Documents
- **[CGC_VICC_IMPLEMENTATION.md](./CGC_VICC_IMPLEMENTATION.md)** - Complete CGC/VICC classifier implementation guide
- **[GA4GH_INTEGRATION_PLAN.md](./GA4GH_INTEGRATION_PLAN.md)** - GA4GH standards integration roadmap
- **[ONCOKB_CLINVAR_INTEGRATION.md](./ONCOKB_CLINVAR_INTEGRATION.md)** - OncoKB/ClinVar data integration patterns
- **[INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md](./INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md)** - Multi-KB integration strategies
- **[INTER_GUIDELINE_EVIDENCE_MAPPING.md](./INTER_GUIDELINE_EVIDENCE_MAPPING.md)** - Cross-guideline evidence harmonization
- **[TIER_ASSIGNMENT_REALITY_CHECK.md](./TIER_ASSIGNMENT_REALITY_CHECK.md)** - Real-world tier assignment validation

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
- **Evidence Scoring Strategies** (550 lines) - Modular Strategy Pattern implementation
- **Dependency Injection** (200 lines) - Clean DI container with Protocol interfaces
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

#### Evidence Scoring System & Dependency Injection Refactoring (2025-06-17)
- **Strategy Pattern Implementation**: Decoupled evidence scoring from tiering logic
- **6 Specialized Scorers**: FDA, Guidelines, Clinical Studies, Expert Consensus, Case Reports, Preclinical
- **Dependency Injection Container**: Clean DI patterns eliminate complex manual mocking
- **Protocol-Based Interfaces**: Type-safe dependency contracts for all major components
- **Factory Pattern**: `TieringEngineFactory` for production and test configurations
- **Improved Testability**: 16 comprehensive unit tests for individual scorers + mockable dependencies
- **Maintainability**: Clear separation of concerns and single responsibility classes
- **Full Backward Compatibility**: No changes to external API or scoring behavior

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

### ✅ Phase 2A Complete (2025-01-18)

#### Major Achievements
- ✅ **ALL TESTS PASSING** - Fixed 39 failing tests → 0 failures!
- ✅ **CGC/VICC Classifier Implementation**
  - Full VICC 2022 evidence code system (OVS1, OS1-3, OM1-4, OP1-4, benign codes)
  - Oncogenicity classification with point-based scoring
  - Integration with OncoKB evidence levels and ClinVar pathogenicity
  - Comprehensive unit test suite (160+ tests passing)
  - Inter-guideline evidence mapping (OncoKB "Oncogenic" → OS1)
  
- ✅ **GA4GH Comprehensive Integration**
  - VRS Handler: Variant normalization and VRS ID generation
  - VICC Meta-KB Client: Access to 6 harmonized databases
  - Phenopackets v2.0: Cancer-specific clinical data exchange
  - VA Standard: Standardized annotation format
  - Service Info: GA4GH service discovery
  - Clinical Context Extractor: Cross-guideline mapping
  
- ✅ **Enhanced Oncogenicity Integration**
  - OncoKB/ClinVar data mapping and integration scripts
  - Inter-database concordance analysis (2 DBs=85%, 3 DBs=95%, 4+ DBs=99%)
  - Clinical context extraction for canned text generation
  
- ✅ **Production Infrastructure**
  - VEP Docker integration with 26 plugins (100% complete)
  - Full knowledge base loading (100% downloaded and integrated)
  - dbNSFP integration completed
  - Dependency injection pattern throughout test infrastructure

### ✅ Phase 2B Complete (2025-06-18) - Canned Text Generation System

#### Major Achievements
- ✅ **Complete Canned Text Generation System** - All 8 text types implemented
  - General Gene Info, Gene Dx Interpretation, General Variant Info, Variant Dx Interpretation
  - Incidental/Secondary Findings, Chromosomal Alteration Interpretation, Pertinent Negatives, Biomarkers
  - Sophisticated template system with confidence scoring
  - 6,632 lines of production code with comprehensive testing
  
- ✅ **Enhanced Pertinent Negatives** - Beyond gene mutations
  - Chromosomal alterations (+7/-10 in GBM, 1p/19q codeletion)
  - Methylation status (MGMT, TERT promoter, MLH1)
  - Specific variants (EGFRvIII, TERT promoter mutations)
  - Amplifications/deletions, fusion events, expression markers
  - Cancer-specific negative finding catalogs (GBM, colorectal, lung, breast)
  
- ✅ **Enhanced Deterministic Narrative Generator**
  - 5-tier source reliability system (FDA/Guidelines > Expert > Community > Computational)
  - Reliable citation management with automatic numbering
  - Evidence clustering and synthesis by conclusion
  - Professional narrative flow with proper transitions
  - Comprehensive reference sections with academic formatting
  
- ✅ **GA4GH Clinical Context Extension**
  - Extended existing clinical context extractor
  - Therapy class mapping and cancer type hierarchies
  - Cross-guideline evidence mapping (OncoKB → CGC/VICC)
  - Ontology term extraction and clinical scenario building

### 🚧 Phase 2C In Progress (Production Readiness)

## Detailed Implementation Plan

### Phase 2A: ✅ COMPLETE (Input Processing, CGC/VICC, GA4GH)
**📚 Key Documentation:** [CGC_VICC_IMPLEMENTATION.md](./CGC_VICC_IMPLEMENTATION.md), [GA4GH_INTEGRATION_PLAN.md](./GA4GH_INTEGRATION_PLAN.md), [INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md](./INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md)

#### Completed Features:
- ✅ CGC/VICC classifier with all 17 criteria
- ✅ Inter-guideline evidence mapping
- ✅ GA4GH comprehensive integration (VRS, VICC, Phenopackets, VA)
- ✅ Cross-database concordance analysis
- ✅ All tests passing (39 → 0 failures)
- ✅ dbNSFP integration complete
- ✅ VEP with 26 plugins fully configured

### Phase 2B: Production Readiness (Current - 2 weeks)
**📚 Key Documentation:** [SCHEMA_VALIDATION.md](./SCHEMA_VALIDATION.md), [VCF_PARSING.md](./VCF_PARSING.md), [WORKFLOW_KB_MAPPING.md](./WORKFLOW_KB_MAPPING.md)

#### Week 1: Input Validation & Patient Context
- [ ] Create `input_validator.py` module
  - Additional required field validation
  - Chromosome naming standardization
- [ ] Implement `patient_context.py`
  - Patient UID management
  - OncoTree disease code validation
  - Case metadata management

#### Week 2: Workflow Router & Performance
- [ ] Create `workflow_router.py`
  - KB priority configuration per pathway (see [WORKFLOW_KB_MAPPING.md](./WORKFLOW_KB_MAPPING.md))
  - Evidence weight multipliers
  - VAF threshold differences
- [ ] Performance optimization for production scale
  - Memory usage tracking
  - Progress bars for long operations
- [ ] CLI updates for GA4GH formats
  - `--output-format phenopacket`
  - `--vrs-normalize`
  - `--export-va`
- [ ] Integration testing with GA4GH modules
- [ ] Integrate comprehensive canned text system with tiering engine

### Phase 2C: ✅ COMPLETE (Clinical Text Generation)
**📚 Key Documentation:** [CANNED_TEXT_TYPES.md](./CANNED_TEXT_TYPES.md), [KB_TO_CANNED_TEXT_MAPPING.md](./KB_TO_CANNED_TEXT_MAPPING.md)

#### Completed Features:
- ✅ Extended GA4GH clinical context extractor for all 8 text types
- ✅ Created sophisticated template system with confidence scoring
- ✅ Implemented evidence-to-text mapping using cross-guideline mappings
- ✅ Gene-level text generators (General Info, Dx Interpretation)
- ✅ Variant-level text generators (General Info, Dx Interpretation)
- ✅ Special case generators (Incidental, Chromosomal, Negatives, Biomarkers)
- ✅ Enhanced pertinent negatives beyond gene mutations
- ✅ Deterministic narrative weaving with reliable citations
- ✅ Comprehensive testing and validation

#### Implementation Details:
- **Files Created**: 10 new modules (6,632 lines total)
- **Template System**: Sophisticated templates with required/optional fields
- **Citation Management**: 5-tier source reliability with automatic numbering
- **Evidence Synthesis**: Clustering and narrative flow generation
- **Quality Assurance**: Comprehensive test suite and validation
- **Documentation**: Complete implementation log and examples

### Phase 3: Production Deployment (3-4 weeks)

#### Phase 3A: Database Integration
**📚 Key Documentation:** [INTERP_DB_BLUEPRINT.md](./INTERP_DB_BLUEPRINT.md)
- [ ] Implement PostgreSQL schema for results storage
- [ ] Create variant interpretation history tracking
- [ ] Build audit trail for clinical use
- [ ] Implement caching layer for KB queries

#### Phase 3B: Web API Development
**📚 Key Documentation:** [API_ROUTING.md](./API_ROUTING.md), [FRONTEND_API_SCHEMA.md](./FRONTEND_API_SCHEMA.md)
- [ ] RESTful endpoints for all functionality
- [ ] GA4GH service-info endpoint
- [ ] Batch processing API
- [ ] Authentication and authorization

#### Phase 3C: Frontend Integration
**📚 Key Documentation:** [FRONTEND_SPECIFICATION.md](./FRONTEND_SPECIFICATION.md)
- [ ] Define API contract
- [ ] Create example bundles
- [ ] Document JSON schema
- [ ] Build reference UI components

### Phase 4: Clinical Validation & Deployment (4-6 weeks)

#### Phase 4A: Clinical Validation
- [ ] Validation dataset curation (100+ variants)
- [ ] Comparison with manual curation
- [ ] Performance metrics collection
- [ ] Clinical user feedback integration

#### Phase 4B: Production Deployment
**📚 Key Documentation:** [DEPLOYMENT_BLUEPRINT.md](./DEPLOYMENT_BLUEPRINT.md)
- [ ] Docker optimization
- [ ] Kubernetes deployment configs
- [ ] Monitoring and alerting setup
- [ ] Backup and recovery procedures

## Success Metrics

### Technical Metrics
- **Performance**: <5 seconds per variant end-to-end
- **Accuracy**: >95% concordance with expert curation
- **Reliability**: 99.9% uptime
- **Scalability**: Handle 1000+ samples/day

### Clinical Metrics
- **Tier Assignment**: 100% variants receive tier
- **Evidence Coverage**: >80% clinically significant variants have evidence
- **Text Generation**: All 8 text types for every variant
- **Turnaround Time**: <1 hour for typical VCF

### Quality Metrics
- **Test Coverage**: >90% code coverage
- **Documentation**: All modules documented
- **Validation**: Clinical validation complete
- **Compliance**: HIPAA/GDPR compliant

## Risk Mitigation

### Technical Risks
- **KB Updates**: Automated update notifications
- **VEP Version Changes**: Containerized environment
- **Performance Bottlenecks**: Profiling and optimization
- **Data Loss**: Regular backups

### Clinical Risks
- **Misinterpretation**: Clear disclaimers and confidence scores
- **Missing Evidence**: Multiple KB sources
- **Guideline Changes**: Modular rule system
- **Regulatory Compliance**: Audit trails

## Timeline Summary

- **Phase 1**: ✅ Complete (Core Engine)
- **Phase 2A**: ✅ Complete (CGC/VICC, GA4GH Integration)
- **Phase 2B**: 🚧 Current (Production Readiness) - 2 weeks
- **Phase 2C**: Clinical Text Generation - 2-3 weeks
- **Phase 3**: Production Deployment - 3-4 weeks
- **Phase 4**: Clinical Validation - 4-6 weeks

**Total Estimated Timeline**: 11-15 weeks from current state to production deployment

## Next Session Starting Points

```bash
# Check current status
poetry run pytest  # Should show 0 failures

# Test GA4GH integration
poetry run python -c "from annotation_engine.ga4gh import VRSHandler; print('GA4GH ready!')"

# Run full annotation with all features
poetry run annotation-engine --test --verbose

# Start Phase 2B implementation
# 1. Create input_validator.py
# 2. Create patient_context.py
# 3. Update CLI for GA4GH formats
```