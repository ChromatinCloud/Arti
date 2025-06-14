#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script for the “annotation-engine” starter repo.
# Creates directory skeleton, placeholder files, and initial docs.

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

mkdir -p "$root_dir"/{config,docker,env,scripts,src/annotation_engine,tests,.github/workflows,docs}

###############################################################################
# Core text files
###############################################################################
cat > "$root_dir/README.md" <<'EOF'
# Annotation-Engine (MVP)

Open-source scaffold for a somatic variant annotation service that
implements AMP 2017, VICC 2022, and OncoKB tiers.  Phase-1 target:
CLI tool returning JSON.  See docs/ROADMAP.md for long-term vision.
EOF

cat > "$root_dir/LICENSE" <<'EOF'
MIT License
EOF

cat > "$root_dir/.gitignore" <<'EOF'
__pycache__/
*.pyc
*.log
.venv/
.vep/
.cache/
build/
dist/
*.egg-info/
.env*
.idea/
.vscode/
EOF

###############################################################################
# Claude instructions
###############################################################################
cat > "$root_dir/CLAUDE_INSTRUCTIONS.md" <<'EOF'
<!-- Detailed architecture lives in docs/ANNOTATION_PIPELINE_BLUEPRINT.md -->
<!-- Phase-2/3 backlog lives in docs/ROADMAP.md -->

# Claude Code – Working Instructions for “annotation-engine”

> **Scope:** keep this file short.  Only the immediate sprint tasks appear
> here; everything else is referenced above so Claude can fetch it on demand.

---

## Mission (Phase 1)

Build a CLI-first somatic variant annotation engine that

1. Runs Ensembl **VEP** + plugins on VCF input and returns JSON.
2. Aggregates evidence from **dbNSFP, COSMIC Hotspots, OncoKB, CIViC, CGC**.
3. Scores AMP 2017 clinical tiers **and** VICC 2022 oncogenicity classes.
4. Outputs `tier`, `confidence`, and raw evidence for each variant.

A working smoke test on two demo variants is the Phase-1 exit criterion.

---

## Coding conventions

* Python ≥ 3.10 – use `| None` instead of `typing.Optional`.
* One top-level package: `src/annotation_engine/`.
* No inline comments; write explanatory text in module docstrings.
* Config in `config/*.yaml`; never hard-code thresholds in code.
* Keep files formatted by **ruff** (`ruff --select I --target-version py310`).

---

## Immediate TODOs

### 1  `vep_runner.py`
* Execute `vep --json` (assume cache installed under `.vep`).
* Return list of dicts compatible with `models.Evidence`.

### 2  `evidence_aggregator.py`
* Lazy-load reference files from `.refs/` the first time it’s called.
* For each variant, attach:
  * OncoKB tier/level (JSON dump)
  * CIViC evidence items
  * COSMIC hotspot flag
  * Population AF from dbNSFP

### 3  `tiering.py`
* Implement the 12 CancerVar CBP weights (dict in code is fine).
* Return `TierResult` with `tier`, `total_score`, and list of `Evidence`.

### 4  Tests
* Expand `tests/test_smoke.py` so both demo variants round-trip
  through CLI and produce a Tier I and Tier III result respectively.

---

## Reference data layout

