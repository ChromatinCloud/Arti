# Annotation-Engine

> **Status:** Comprehensive knowledge base system implemented – ready for Phase 1 development  
> **Goal:** A reproducible CLI that ingests a tumor‐only or matched‐pair VCF, annotates each variant with AMP 2017 and VICC 2022 evidence, assigns tiers, emits confidence scores, and writes machine-readable JSON for downstream report generation.

---

## Why this repo exists

1. **Clinical need** – Labs require repeatable, auditable variant interpretation that keeps pace with evolving guidelines.
2. **Engineering goal** – Achieve high coverage with comprehensive external knowledge bases: VEP + 33 curated clinical databases covering all major genomics resources.
3. **Design principle** – Build around a modular rules engine so guideline updates are YAML-driven, not code rewrites.

For detailed architecture, see `docs/ANNOTATION_BLUEPRINT.md` (full spec) and `docs/ROADMAP.md` (phase timeline).

---

## Quick-start (developer)

```bash
# Setup Python environment
pipx install poetry  # or brew install poetry
poetry install --no-root

# Setup comprehensive knowledge bases (choose your scope)
./scripts/setup_comprehensive_kb.sh --essential    # Core databases (~550MB)
./scripts/setup_comprehensive_kb.sh --all          # Full setup with prompts

# Setup VEP with Docker and plugins
./scripts/setup_vep.sh

# Run tests
poetry run pytest -q

# Annotate tumor-only VCF
poetry run python cli.py example.vcf --cancer-type lung --out example.json

# Annotate tumor-normal pair
poetry run python cli.py --tumor-vcf tumor.vcf --normal-vcf normal.vcf --cancer-type lung --out results.json

# Provide tumor purity for enhanced confidence scoring
poetry run python cli.py example.vcf --cancer-type lung --tumor-purity 0.75 --out example.json
```

---

## Comprehensive Knowledge Base System

Our annotation engine integrates **42 curated knowledge bases** covering all major clinical genomics resources. **Current Status: 15/42 successfully downloaded (1.1GB)** Each knowledge base serves specific clinical classification frameworks:

### Clinical Classification Frameworks Supported

1. **AMP/ASCO/CAP Guidelines** (2017) - Somatic variant therapeutic actionability (Tiers I-IV)
2. **ClinGen/CGC/VICC Guidelines** (2022) - Somatic oncogenicity assessment  
3. **OncoKB Therapeutic Guidelines** - Clinical actionability tiers
4. **Canned Text Types** - Nine standardized report components

### Knowledge Base Inventory by Clinical Purpose

#### **Population Frequencies & Variant Context** (AMP 2017: Tier filtering; VICC: SBVS1, OP4)
- **gnomAD Exomes** (20GB) - Filter common germline variants in tumor-only sequencing
- **gnomAD Genomes** (150GB) - Comprehensive population frequencies including structural variants
- **dbSNP** (25GB) - Variant identifiers and common variant flagging for somatic filtering
- **ClinVar VCF & TSV** (350MB) - Clinical significance for somatic variant interpretation (VICC: OS2)

#### **Clinical Evidence & Therapeutic Actionability** (AMP 2017 Tiers; VICC Oncogenicity)
- **CIViC Variants & Hotspots** (15MB) - Clinical evidence summaries for cancer variants
- **OncoKB Genes** (1MB) - Curated cancer gene lists and actionability
- **CancerMine** (20MB) - Literature-mined oncogenes and tumor suppressors

#### **Cancer Hotspots & Recurrent Mutations** (VICC: OS3, OM3)
- **Cancer Hotspots VCF** (5MB) - Memorial Sloan Kettering recurrent mutations
- **MSK SNV Hotspots** (10MB) - Single nucleotide variant hotspots from cBioPortal
- **MSK Indel Hotspots** (5MB) - Insertion/deletion hotspots
- **MSK 3D Hotspots** (5MB) - Protein structure-based hotspot predictions
- **COSMIC Cancer Gene Census** (2MB) - Curated cancer gene classifications (VICC: OVS1)

#### **Gene Function & Protein Domains** (VICC: OM1; ACMG: PVS1 mechanism)
- **UniProt Swiss-Prot** (300MB) - Curated protein sequences and functional annotations
- **Pfam Domains** (100MB) - Protein family and domain classifications
- **NCBI Gene Info** (200MB) - Comprehensive gene annotations and mappings
- **HGNC Mappings** (5MB) - Official gene symbol standardization

#### **Clinical Biomarkers & Thresholds** (Canned Text: Biomarkers)
- **Clinical Biomarkers** (2MB) - Curated biomarker definitions and clinical thresholds
- **OncoTree Classifications** (1MB) - Cancer type taxonomies for context-specific interpretation

#### **Gene Dosage Sensitivity** (ACMG: PVS1 refinement)
- **ClinGen Gene Curation** (2MB) - Expert-curated gene-disease relationships
- **ClinGen Haploinsufficiency** (1MB) - Genes sensitive to single-copy loss
- **ClinGen Triplosensitivity** (1MB) - Genes sensitive to extra copies

#### **Drug-Target Associations** (Canned Text: General Gene Info, Variant Dx Interpretation)
- **Open Targets Platform** (500MB) - Disease-target and drug-target associations
- **DGIdb Interactions** (50MB) - Drug-gene interaction database

#### **Disease & Pathway Context** (Canned Text: Gene Dx Interpretation)
- **MONDO Disease Ontology** (50MB) - Structured disease classifications
- **TCGA MC3 Mutations** (200MB) - Pan-cancer somatic mutation landscape

#### **Cell Line & Functional Genomics** (Research context and validation)
- **DepMap Mutations** (100MB) - Cell line somatic mutation profiles
- **DepMap Gene Effects** (200MB) - CRISPR screen dependency data

#### **Oncovi Curated Resources** (MGCarta) - Advanced Clinical Interpretation
- **Oncovi Tumor Suppressors** (1KB) - Union of COSMIC CGC + OncoKB TSGs (VICC: OVS1)
- **Oncovi Oncogenes** (1KB) - Union of COSMIC CGC + OncoKB oncogenes (VICC: OS1)
- **Oncovi Single Residue Hotspots** (5MB) - Detailed mutation frequency data (VICC: OS3)
- **Oncovi Indel Hotspots** (1MB) - In-frame indel hotspot annotations (VICC: OM3)
- **Oncovi Protein Domains** (2MB) - Processed UniProt domain annotations (VICC: OM1)
- **Oncovi CGI Mutations** (3MB) - Cancer Genome Interpreter validated mutations
- **Oncovi OS2 Criteria** (1KB) - Manually curated ClinVar significance mappings
- **Oncovi Amino Acid Utils** (6KB) - Conversion dictionaries and Grantham distances

#### **VEP Plugin Data** (ACMG: PP3, BP4; VICC: OP1, SBP1)
Managed by VEP setup rather than direct download:
- **dbNSFP** - SIFT, PolyPhen, CADD, REVEL functional predictions
- **AlphaMissense** - DeepMind protein structure-based predictions  
- **SpliceAI** - Deep learning splice site predictions

### Clinical Rule Mapping

| Framework | Evidence Type | Knowledge Bases Used | Somatic Application |
|-----------|---------------|---------------------|-------------------|
| **AMP/ASCO/CAP 2017** | Therapeutic actionability | OncoKB, CIViC, DGIdb | Tier I (FDA-approved), Tier II (investigational) |
| **AMP/ASCO/CAP 2017** | Cancer gene context | Cancer Gene Census, OncoVI TSG/Oncogenes | Driver gene classification for tier assignment |
| **AMP/ASCO/CAP 2017** | Hotspot evidence | MSK Hotspots, COSMIC, OncoVI | Recurrent mutations indicate driver status |
| **AMP/ASCO/CAP 2017** | Population filtering | gnomAD, dbSNP | Remove common germline variants in tumor-only |
| **VICC 2022** | Oncogenicity assessment | Cancer Gene Census | OVS1 (+8 points: null in tumor suppressor) |
| **VICC 2022** | Hotspot evidence | Cancer Hotspots, MSK | OS3 (+4 points: recurrent at position) |
| **VICC 2022** | Functional domain | Pfam, UniProt, OncoVI | OM1 (+2 points: critical domain) |
| **VICC 2022** | Clinical significance | ClinVar, CIViC | OS2 (+4 points: pathogenic in ClinVar) |
| **OncoKB** | Evidence levels | OncoKB curated genes | Level 1-4 therapeutic evidence hierarchy |

### Canned Text Report Types Supported

1. **General Gene Info** - UniProt, HGNC, Open Targets, DGIdb
2. **Gene Dx Interpretation** - ClinGen, MONDO, TCGA, Cancer Gene Census  
3. **General Variant Info** - ClinVar, population frequencies, functional predictions
4. **Variant Dx Interpretation** - CIViC, OncoKB, cancer hotspots
5. **Incidental/Secondary Findings** - ACMG actionable gene list (ClinGen)
6. **Chromosomal Alteration Interpretation** - Cancer gene context, dosage sensitivity
7. **Pertinent Negatives** - Coverage analysis with gene lists
8. **Biomarkers** - TMB/MSI calculations, clinical biomarker thresholds
9. **Technical Comments** - Institution-specific QC flags (internal/)

### Usage Examples

```bash
# Essential clinical databases (quick start)
./scripts/setup_comprehensive_kb.sh --essential

# Population frequencies (large downloads)  
./scripts/setup_comprehensive_kb.sh --population

# Specialized research databases
./scripts/setup_comprehensive_kb.sh --specialized

# Complete setup with interactive prompts
./scripts/setup_comprehensive_kb.sh --all

# List all available knowledge bases
./scripts/setup_comprehensive_kb.sh --list

# Verify downloaded files
./scripts/setup_comprehensive_kb.sh --verify
```

---

## Architecture Overview

### Core Components
- `src/annotation_engine/` - Main package with clinical interpretation logic
- `scripts/` - Knowledge base setup and VEP installation
- `config/` - Clinical thresholds and tumor-specific gene mappings
- `internal/` - Institution-specific QC flags and technical comments
- `.refs/` - Downloaded knowledge base files (git-ignored, structure preserved)

### Development Workflow
1. **Setup**: Download knowledge bases and install VEP
2. **Annotation**: Process VCF through VEP with comprehensive plugin data
3. **Evidence Aggregation**: Query 42 knowledge bases for variant evidence
4. **Classification**: Apply ACMG/AMP and VICC guidelines automatically
5. **Reporting**: Generate structured JSON for downstream report generation

### Design Principles
- **Modular**: Each knowledge base and classification rule is independently configurable
- **Reproducible**: All downloads scripted and versioned, deterministic processing
- **Clinical-grade**: Implements published clinical guidelines with full traceability
- **Scalable**: Supports both single-variant queries and batch processing
- **Compliant**: Handles commercial licensing requirements (OncoKB, COSMIC alternatives)

---

## Repository Structure

```
annotation-engine/
├── README.md                    # This file
├── CLAUDE.md                    # Development guidance
├── scripts/
│   ├── setup_comprehensive_kb.sh  # Download 33 knowledge bases
│   └── setup_vep.sh              # VEP installation via Docker
├── src/annotation_engine/
│   ├── models.py                  # Pydantic data models
│   ├── vep_runner.py             # VEP execution and parsing
│   ├── evidence_aggregator.py    # Query knowledge bases
│   ├── tiering.py                # ACMG/VICC classification
│   ├── api_clients.py            # CIViC/OncoKB API integration
│   └── plugin_manager.py         # VEP plugin configuration
├── config/
│   ├── thresholds.yaml           # Clinical cutoffs (TMB, MSI, etc.)
│   └── tumor_drivers.yaml        # Cancer type-specific gene lists
├── internal/
│   ├── QC_Flags.tsv.gz          # Standardized quality control flags
│   └── Technical_Comments.tsv.gz # Pre-written technical interpretations
├── docs/
│   ├── ANNOTATION_BLUEPRINT.md   # Detailed clinical requirements
│   ├── KB_DOWNLOAD_BLUEPRINT.md  # Knowledge base documentation
│   └── ROADMAP.md                # Development phases
└── .refs/                        # Downloaded knowledge bases (33 databases)
    ├── clinvar/                  # Clinical significance data
    ├── civic/                    # Clinical evidence summaries
    ├── cancer_hotspots/          # Recurrent mutation data
    ├── gnomad/                   # Population frequencies
    ├── gene_mappings/            # Gene symbol standardization
    ├── biomarkers/               # Clinical thresholds
    └── [28 more subdirectories]  # Complete knowledge base collection
```

For complete documentation of all 33 knowledge bases, see `docs/KB_DOWNLOAD_BLUEPRINT.md`.