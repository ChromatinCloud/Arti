# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Annotation-Engine is a reproducible CLI that ingests a tumor-only or matched-pair VCF, annotates each variant with AMP 2017 and VICC 2022 evidence, assigns tiers, emits confidence scores, and writes machine-readable JSON for downstream report generation.

### Why This Repo Exists
1. **Clinical need** – Labs require repeatable, auditable variant interpretation that keeps pace with evolving guidelines
2. **Engineering goal** – Achieve high coverage with minimal external dependencies: VEP + five reference blobs (OncoKB, CIViC, COSMIC Hotspots, dbNSFP, CGC)
3. **Design principle** – Build around a modular rules engine so guideline updates are YAML-driven, not code rewrites

## Stable Development Guidelines (Do NOT Change)

### Coding Conventions
* Python ≥ 3.10 – use `| None` unions, no `typing.Optional`
* One top-level package: `src/annotation_engine/`
* No inline comments; put explanatory text in module docstrings
* Config lives in `config/*.yaml`; never hard-code thresholds
* Style/lint: `ruff --select I --target-version py310`
* Unit tests in `tests/`, must run via `pytest -q`

### Architecture Principles
* Keep CLI thin (`cli.py`) – heavy logic lives in `annotation_engine.*` modules
* Pydantic v2 for typed data models
* All critical constants (e.g., biomarker thresholds) live in YAML
* Modular rules engine for guideline updates without code rewrites

## Development Commands

### Command Execution Policy
**Commands that do NOT require specific approval:**
- All file reading operations (`cat`, `head`, `tail`, `less`, `more`, `grep`, `find`, `ls`, `wc`, etc.)
- Code quality and linting commands (`ruff`, `pytest`, `mypy`, etc.)
- Environment inspection (`which`, `python --version`, `poetry env info`, etc.)
- Git status/inspection commands (`git status`, `git diff`, `git log`, etc.)
- Docker inspection commands (`docker ps`, `docker images`, etc.)
- System information commands (`df`, `ps`, `top`, `uname`, etc.)

**Commands that require explicit approval:**
- File modification/deletion operations (`rm`, `mv`, `cp` to overwrite, etc.)
- Git modification commands (`git add`, `git commit`, `git push`, etc.)
- Package installation (`pip install`, `brew install`, etc.)
- System configuration changes

### Logging Policy
**When user says "log this" or "log that":**
- Create log files in `./out/logs/` directory
- Use descriptive filenames based on content (e.g., `vep_setup_issues_20250616.log`, `test_failures_analysis.log`)
- Include timestamps and context in log entries

**Periodic progress logging:**
- Automatically log significant milestones and completion notes
- Document any issues encountered and their resolutions
- Log test results, build outcomes, and deployment status
- Use format: `session_progress_YYYYMMDD_HHMMSS.log`

### Documentation Policy
**When user says "document this" or "document that":**
- Create new `.md` files in `./docs/` directory OR add to existing relevant documentation
- Use descriptive filenames (e.g., `VEP_PLUGIN_TROUBLESHOOTING.md`, `TESTING_WORKFLOW.md`)
- Format for maximum readability by AI agents like Claude Code:
  - Clear section headers with `##` and `###`
  - Code blocks with proper language tags
  - Bullet points for lists and procedures
  - File paths in backticks
  - Commands in code blocks
  - Include context about "why" not just "what"
  - Cross-reference related files and sections
  - Use consistent terminology matching the codebase

### TODO.md and Implementation Guide Synchronization Policy
**File Relationship:**
- `TODO.md` = Current sprint backlog (actionable tasks)
- `docs/IMPLEMENTATION_ROADMAP.md` = Project status and context

**Synchronization Rules:**
1. **When TODO.md changes:**
   - Check if "Current Sprint Focus" section in Implementation Guide needs updating
   - Update Implementation Guide's "In Progress" section if tasks move to completed
   - Ensure task descriptions remain consistent between files

2. **When Implementation Guide changes:**
   - Check if TODO.md tasks need to be added, modified, or marked complete
   - Verify that "Current Sprint Focus" section accurately reflects TODO.md content
   - Update sprint timeline if scope changes

3. **Proactive Synchronization:**
   - Before marking any task as completed, update both files
   - When starting new sprint, update TODO.md first, then sync Implementation Guide
   - Weekly check: ensure both files are aligned and current

**Change Detection Triggers:**
- Task completion status changes
- New tasks added to sprint
- Task descriptions or scope modifications
- Architecture or approach changes
- Sprint planning or timeline updates

**Responsibility:**
- Always check both files when making changes to either
- Maintain TODO.md as single source of truth for current sprint
- Keep Implementation Guide as authoritative project overview

### Environment Setup
```bash
# Install dependencies
pipx install poetry  # or /opt/homebrew/bin/brew install poetry
brew install openjdk@17  # For Nextflow
poetry install
poetry update
poetry show --tree

# Setup Java for Nextflow
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
export PATH="$HOME/bin:$PATH"

# Or run the setup script
./setup_env.sh
```

### Code Quality and Linting
```bash
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
poetry run ruff --select I --target-version py310
```

### Testing
```bash
poetry run pytest -q
poetry run pytest -v
poetry run pytest tests/test_smoke.py
poetry run pytest tests/test_end_to_end_workflow.py
poetry run pytest --cov=src/annotation_engine
```

### Running the CLI
```bash
# Quick test (0.20 seconds)
poetry run annotation-engine --test

# Full annotation  
poetry run annotation-engine --input example.vcf --case-uid CASE001 --cancer-type melanoma

# See USAGE.md for comprehensive command reference and examples
```

### Data Setup and Knowledge Bases
```bash
# Setup comprehensive knowledge bases using "recipe approach"
./scripts/setup_comprehensive_kb.sh --essential    # Core databases (~550MB)
./scripts/setup_comprehensive_kb.sh --all          # Full setup with prompts

# Setup VEP via Docker with plugins
./scripts/setup_vep.sh
./scripts/setup_vep_plugins.sh
./scripts/download_plugin_data.sh
```

### VEP Operations
```bash
vep --help
vep --json --input_file input.vcf --output_file output.json
```

### Docker Operations
```bash
docker build -t annotation-engine .
docker-compose up
docker-compose down
./scripts/docker_build.sh
```

### Git Operations
```bash
git status
git diff
git log --oneline -10
git add .
git commit -m "message"
git push origin main
```

### File Operations and Exploration
```bash
find . -name "*.py" -type f
find . -name "*.vcf*" -type f
ls -la .refs/
ls -la out/
grep -r "TODO" src/
grep -r "FIXME" src/
```

### Data Validation and Testing
```bash
python scripts/comprehensive_test.py
python scripts/update_kb_paths.py
```

### System and Environment
```bash
which poetry
which python
python --version
poetry env info
```

### Nextflow Workflows
```bash
nextflow run workflows/simple_test.nf
nextflow run workflows/test.nf
```

### File Inspection (for debugging)
```bash
head -20 example_input/proper_test.vcf
tail -20 out/logs/latest.log
wc -l .refs/civic/civic_variants.tsv
```

## Architecture and Key Components

### Phase 1 Mission
1. Run **VEP + plugins** on VCF, output JSON
2. Aggregate evidence from **dbNSFP, COSMIC Hotspots, OncoKB, CIViC, CGC**
3. Score AMP 2017 tiers **and** VICC 2022 oncogenicity classes
4. Emit `tier`, `confidence`, raw evidence per variant

### Core Package Structure
- `src/annotation_engine/` - Main package directory
  - `models.py` - Pydantic v2 data models (Evidence, TierResult)
  - `vep_runner.py` - Executes VEP and parses JSON output
  - `evidence_aggregator.py` - Loads and matches against OncoKB, COSMIC, CIViC
  - `tiering.py` - Implements scoring table for AMP/VICC tier assignment
  - `api_clients.py` - API clients for CIViC and OncoKB real-time queries
  - `plugin_manager.py` - VEP plugin management and configuration

### Configuration
- `config/thresholds.yaml` - Clinical thresholds (TMB, MSI, HRD cutoffs)
- `config/tumor_drivers.yaml` - Tumor type to driver gene mappings

### Reference Data Organization
Expected structure under `$REPO_ROOT/.refs/` (managed by setup scripts):
```
.refs/
├── clinical_evidence/           # Clinical significance and evidence
│   ├── clinvar/                # ClinVar VCF and TSV files
│   ├── civic/                  # CIViC variant and evidence files
│   ├── oncokb/                 # OncoKB gene lists and annotations
│   ├── clingen/                # ClinGen dosage sensitivity
│   └── biomarkers/             # Clinical biomarker thresholds
├── population_frequencies/      # Population allele frequencies
│   ├── gnomad/                 # gnomAD exomes and genomes (large files)
│   ├── dbsnp/                  # dbSNP common variants
│   └── exac/                   # ExAC population data
├── functional_predictions/      # VEP and functional prediction tools
│   ├── vep_cache/              # VEP offline cache (15-20GB)
│   ├── vep_plugins/            # VEP plugin source code
│   └── plugin_data/            # Plugin data files organized by type:
│       ├── pathogenicity/      # REVEL, BayesDel, ClinPred, FATHMM, dbNSFP
│       ├── protein_impact/     # AlphaMissense, PrimateAI, EVE, VARITY
│       ├── splicing/           # SpliceAI, dbscSNV, SpliceRegion, NMD
│       ├── conservation/       # GERP, PhyloP, PhastCons scores
│       ├── gene_constraint/    # LoFtool constraint scores
│       ├── regulatory/         # Enformer regulatory predictions
│       ├── utr/                # UTRAnnotator 5'/3' UTR effects
│       ├── clinvar/            # ClinVar plugin data
│       └── mavedb/             # MaveDB experimental scores
├── cancer_signatures/          # Cancer-specific databases
│   ├── hotspots/               # Cancer hotspots (MSK, CIViC, 3D, OncoVI)
│   ├── cosmic/                 # COSMIC Cancer Gene Census
│   ├── tcga/                   # TCGA somatic mutations
│   └── depmap/                 # DepMap cell line data
├── structural_variants/        # Structural variant annotations
│   └── sv_annotations/         # SV overlap annotations
├── literature_mining/          # Literature-mined data
│   ├── cancermine/             # CancerMine text mining
│   └── pubmed/                 # PubMed literature data
├── reference_assemblies/       # Genome reference data
│   ├── gencode/                # GENCODE gene annotations and mappings
│   ├── ensembl/                # Ensembl gene annotations
│   └── refseq/                 # RefSeq annotations
├── vep_setup/                  # VEP installation files
│   ├── cache/                  # VEP setup cache
│   ├── plugins/                # VEP setup plugins
│   └── references/             # VEP reference files
├── pharmacogenomics/           # Drug-gene interactions
│   ├── pharmgkb/               # PharmGKB drug-gene data
│   └── cpic/                   # CPIC guidelines
└── sample_data/                # Test and example data
    ├── test_vcfs/              # Test VCF files
    └── examples/               # Example input files
```

**Note**: Backward compatibility symlinks are maintained:
- `.refs/vep_cache` → `functional_predictions/vep_cache`
- `.refs/vep_plugins` → `functional_predictions/vep_plugins`
- `.refs/clinvar` → `clinical_evidence/clinvar`
- `.refs/gnomad` → `population_frequencies/gnomad`
- `.refs/cancer_hotspots` → `cancer_signatures/hotspots`

## Current Implementation Status

### ✅ Phase 1 COMPLETE (2025-06-16)
- **VEP Runner** (927 lines): JSON parsing, 26 plugin support, graceful fallbacks
- **Evidence Aggregator** (2,069 lines): Full KB integration, DSC scoring, caching
- **Tiering Module** (975 lines): Complete AMP/VICC implementation
- **CLI**: Full-featured with test mode, JSON/TSV output
- **Performance**: 0.20s without VEP, 77s with fallback
- **Validation**: BRAF V600E correctly tiered (Tier III)

### 🚀 Phase 2A Progress (2025-06-17)
- **Knowledge Bases**: 100% completeness achieved (was 73.9%)
- **VEP Plugins**: 23/26 ready (88% - waiting on dbNSFP)
- **New Modules**: AlphaMissense, GERP/PhyloP conservation, plugin fallbacks
- **Database**: SQLAlchemy models complete, initialization ready
- **Validation Tool**: `validate_knowledge_bases.py` for KB status

### 📋 Current Sprint Focus (Phase 2A Week 1)

1. **Input Validation Module**
   * Create `input_validator.py` for VCF format validation
   * Implement `patient_context.py` for patient/case management
   * Add OncoTree disease code validation
   * Update CLI with `--patient-uid`, `--oncotree-code`

2. **Workflow Router**
   * Create `workflow_router.py` for tumor-only vs tumor-normal pathways
   * Configure KB priorities per pathway
   * Integrate pathway-specific confidence calculations

3. **Complete Plugin Integration**
   * Wait for dbNSFP5.1a download (enables 4 more plugins)
   * Validate all 26 plugins working correctly
   * Performance optimization for full plugin stack

### Already Implemented Beyond Roadmap ✅
- Database schema (SQLAlchemy models in `db/`)
- AlphaMissense integration (`alpha_missense.py`)
- GERP conservation scores (`conservation.py`)
- Plugin fallback mechanisms (`plugin_fallbacks.py`)
- Tumor purity estimation (`purity_estimation.py`)
- Dynamic Somatic Confidence (DSC) scoring

## Key Implementation Notes

- Use `scripts/setup_comprehensive_kb.sh` to download knowledge bases under `$REPO_ROOT/.refs/` using predictable sub-folder structure
- VEP runner should return list of dicts compatible with `models.Evidence`
- Evidence aggregator should lazy-load data from `.refs/`
- Tiering module should implement 12 CancerVar CBP weights and return `TierResult`

## Links to Detailed Documentation

- **Detailed Architecture**: `docs/ANNOTATION_BLUEPRINT.md` - Full 400-line spec with clinical guidelines
- **Future Roadmap**: `docs/ROADMAP.md` - Phase 2/3 requirements (database, web UI, quantitative accuracy)
- **Current Sprint Tasks**: `TODO.md` - Update/rename each sprint with immediate tasks