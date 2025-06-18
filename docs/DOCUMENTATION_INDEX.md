# Annotation Engine Documentation Index

> Last Updated: 2025-06-18

This index provides a comprehensive guide to all documentation in the Annotation Engine project, organized by purpose and implementation phase.

## 📋 Core Documentation

### Foundation Documents
- **[ANNOTATION_BLUEPRINT.md](./ANNOTATION_BLUEPRINT.md)** - Core technical specification detailing the complete annotation engine architecture
- **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** - Phase-by-phase development plan with current progress tracking
- **[README.md](../README.md)** - Project overview and quick start guide

### Development Guidance
- **[CLAUDE.md](../CLAUDE.md)** - AI assistant instructions and coding conventions
- **[TODO.md](../TODO.md)** - Current sprint tasks and immediate priorities
- **[USAGE.md](../USAGE.md)** - Comprehensive CLI usage guide and examples

## 🧬 Clinical Guidelines Implementation

### Evidence Classification Systems
- **[CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md)** - Comprehensive mapping of knowledge bases to clinical guidelines
- **[AMP_ASCO_TIERS_AND_EVIDENCE.md](./AMP_ASCO_TIERS_AND_EVIDENCE.md)** - AMP/ASCO/CAP 2017 tier system implementation
- **[CGC_VICC_IMPLEMENTATION.md](./CGC_VICC_IMPLEMENTATION.md)** ⭐ - VICC 2022 oncogenicity classification system (NEW)
- **[INTER_GUIDELINE_EVIDENCE_MAPPING.md](./INTER_GUIDELINE_EVIDENCE_MAPPING.md)** - Cross-guideline evidence harmonization

### Clinical Rules Engine
- **[RULES_IMPLEMENTATION.md](./RULES_IMPLEMENTATION.md)** - Original rules engine design
- **[RULES_IMPLEMENTATION_V2.md](./RULES_IMPLEMENTATION_V2.md)** ⭐ - Enhanced rules with CGC/VICC integration (NEW)
- **[TIER_ASSIGNMENT_REALITY_CHECK.md](./TIER_ASSIGNMENT_REALITY_CHECK.md)** - Real-world tier assignment validation

## 💾 Knowledge Base Integration

### Knowledge Base Management
- **[KB_DOWNLOAD_BLUEPRINT.md](./KB_DOWNLOAD_BLUEPRINT.md)** - Complete inventory of 42 clinical databases
- **[KB_IMPLEMENTATION_GUIDE.md](./KB_IMPLEMENTATION_GUIDE.md)** - Knowledge base loading and query patterns
- **[KB_AND_PLUGIN_REGISTRY.md](./KB_AND_PLUGIN_REGISTRY.md)** - Registry of all KBs and VEP plugins
- **[KB_TO_CANNED_TEXT_MAPPING.md](./KB_TO_CANNED_TEXT_MAPPING.md)** - KB evidence to clinical text mapping

### Cross-Database Integration
- **[ONCOKB_CLINVAR_INTEGRATION.md](./ONCOKB_CLINVAR_INTEGRATION.md)** ⭐ - OncoKB/ClinVar harmonization patterns (NEW)
- **[INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md](./INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md)** ⭐ - Multi-KB integration strategies (NEW)

### VEP Plugin System
- **[VEP_DOCKER_SETUP.md](./VEP_DOCKER_SETUP.md)** - VEP containerization guide
- **[VEP_PLUGIN_KB_ANALYSIS.md](./VEP_PLUGIN_KB_ANALYSIS.md)** - Analysis of 26 VEP plugins
- **[VEP_CACHE_AND_PLUGIN_OVERVIEW.md](./VEP_CACHE_AND_PLUGIN_OVERVIEW.md)** - VEP cache structure and plugin details

## 🔬 Technical Implementation

### Input/Output Processing
- **[VCF_PARSING.md](./VCF_PARSING.md)** - VCF format handling and validation
- **[SCHEMA_VALIDATION.md](./SCHEMA_VALIDATION.md)** - Input/output schema definitions
- **[OUTPUT_JSON_STRUCTURE.md](./OUTPUT_JSON_STRUCTURE.md)** - Detailed output format specification

### Workflow Management
- **[TN_VERSUS_TO.md](./TN_VERSUS_TO.md)** - Tumor-normal vs tumor-only workflow differences
- **[WORKFLOW_KB_MAPPING.md](./WORKFLOW_KB_MAPPING.md)** - Pathway-specific KB prioritization

### Clinical Reporting
- **[CANNED_TEXT_TYPES.md](./CANNED_TEXT_TYPES.md)** - Nine types of standardized clinical text
- **[CANONICAL_TRANSCRIPTS.md](./CANONICAL_TRANSCRIPTS.md)** - Transcript selection logic

### Standards and Interoperability
- **[GA4GH_INTEGRATION_PLAN.md](./GA4GH_INTEGRATION_PLAN.md)** ⭐ - GA4GH VRS/VR-Spec integration roadmap (NEW)

## 🧪 Testing and Validation

- **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** - Comprehensive testing approach
- **[VALIDATION_CASES.md](./VALIDATION_CASES.md)** - Clinical validation test cases
- **[TEST_DATA_GENERATION.md](./TEST_DATA_GENERATION.md)** - Test data creation guide

## 🛠️ Development Workflows

- **[SOFTWARE_DEVELOPMENT_WORKFLOW.md](./SOFTWARE_DEVELOPMENT_WORKFLOW.md)** - Git workflow and code review process
- **[LOGGING_STRATEGY.md](./LOGGING_STRATEGY.md)** - Structured logging approach
- **[CONFIGURATION_MANAGEMENT.md](./CONFIGURATION_MANAGEMENT.md)** - Configuration file organization

## 📦 Archived Documentation

Located in `docs/archive/`:
- Previous implementation attempts
- Deprecated approaches
- Historical design decisions

## 🚀 Quick Navigation by Task

### Setting Up the Project
1. Start with [README.md](../README.md)
2. Follow [KB_DOWNLOAD_BLUEPRINT.md](./KB_DOWNLOAD_BLUEPRINT.md) for knowledge base setup
3. Use [VEP_DOCKER_SETUP.md](./VEP_DOCKER_SETUP.md) for VEP installation

### Understanding Clinical Guidelines
1. Read [CLINICAL_GUIDELINES_MAPPING.md](./CLINICAL_GUIDELINES_MAPPING.md)
2. Study [CGC_VICC_IMPLEMENTATION.md](./CGC_VICC_IMPLEMENTATION.md) for oncogenicity
3. Review [AMP_ASCO_TIERS_AND_EVIDENCE.md](./AMP_ASCO_TIERS_AND_EVIDENCE.md) for therapeutic tiers

### Implementing New Features
1. Check [TODO.md](../TODO.md) for current tasks
2. Consult [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for context
3. Follow patterns in [RULES_IMPLEMENTATION_V2.md](./RULES_IMPLEMENTATION_V2.md)

### Working with Knowledge Bases
1. See [KB_IMPLEMENTATION_GUIDE.md](./KB_IMPLEMENTATION_GUIDE.md) for integration patterns
2. Use [ONCOKB_CLINVAR_INTEGRATION.md](./ONCOKB_CLINVAR_INTEGRATION.md) for cross-DB work
3. Apply [INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md](./INTER_DATABASE_CONCORDANCE_BEST_PRACTICES.md)

## 📝 Documentation Maintenance

When adding new documentation:
1. Place in appropriate section of this index
2. Use descriptive filename in SCREAMING_SNAKE_CASE
3. Include "Last Updated" timestamp
4. Cross-reference related documents
5. Mark with ⭐ if created in current phase

## 🔍 Search Keywords

- **Clinical Guidelines**: AMP, ASCO, CAP, VICC, CGC, OncoKB
- **Knowledge Bases**: ClinVar, COSMIC, CIViC, gnomAD, dbNSFP
- **Technologies**: VEP, Docker, GA4GH, VRS, Pydantic
- **Workflows**: Tumor-only, Tumor-normal, DSC, Purity
- **Features**: Tiering, Oncogenicity, Canned text, Evidence