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

### Environment Setup
```bash
pipx install poetry  # or /opt/homebrew/bin/brew install poetry
poetry install --no-root
```

### Running Tests
```bash
poetry run pytest -q
```

### Linting
```bash
poetry run ruff --select I --target-version py310
```

### Running the CLI
```bash
# After TODOs are implemented:
poetry run python cli.py example.vcf --cancer-type lung --out example.json
```

### Reference Data
```bash
# Setup comprehensive knowledge bases using "recipe approach"
./scripts/setup_comprehensive_kb.sh --essential    # Core databases (~550MB)
./scripts/setup_comprehensive_kb.sh --all          # Full setup with prompts

# Setup VEP via Docker with plugins
./scripts/setup_vep.sh
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
├── clinvar/          # ClinVar VCF and TSV files
├── civic/            # CIViC variant and evidence files
├── oncokb/           # OncoKB gene lists
├── cancer_hotspots/  # Multiple hotspot sources (MSK, CIVIC, 3D)
├── gnomad/           # gnomAD population frequencies (large files)
├── biomarkers/       # Clinical biomarker thresholds
├── gene_mappings/    # Gene symbol and ID mappings
├── oncotree/         # Disease classification ontologies
└── [other KB dirs]   # Additional specialized databases
```

## Current Implementation Priorities

### Immediate TODOs (See TODO.md for current sprint)

1. **vep_runner.py**
   * Shell out to `vep --json`, parse its JSON output into Python objects aligned with `models.Evidence`
   * Accept path to VCF and return list of per-variant dicts

2. **evidence_aggregator.py**
   * Load OncoKB JSON, COSMIC Hotspots TSV, CIViC TSV on first call (cache in global variables)
   * Match VEP variant (gene, hgvs, coordinates) against the above to assemble evidence objects

3. **tiering.py**
   * Implement scoring table equivalent to CancerVar's 12 CBP criteria
   * Provide `assign_tier(evidence_list) -> TierResult`

4. **tests/**
   * Expand `tests/test_smoke.py` so demo variants yield Tier I and Tier III
   * Add new test cases after each module lands

## Key Implementation Notes

- Use `scripts/setup_comprehensive_kb.sh` to download knowledge bases under `$REPO_ROOT/.refs/` using predictable sub-folder structure
- VEP runner should return list of dicts compatible with `models.Evidence`
- Evidence aggregator should lazy-load data from `.refs/`
- Tiering module should implement 12 CancerVar CBP weights and return `TierResult`

## Links to Detailed Documentation

- **Detailed Architecture**: `docs/ANNOTATION_BLUEPRINT.md` - Full 400-line spec with clinical guidelines
- **Future Roadmap**: `docs/ROADMAP.md` - Phase 2/3 requirements (database, web UI, quantitative accuracy)
- **Current Sprint Tasks**: `TODO.md` - Update/rename each sprint with immediate tasks