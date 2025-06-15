#!/usr/bin/env bash
set -euo pipefail

#
# Bootstrap script for the “annotation-engine” starter repo.
# Creates the directory skeleton and placeholder files required
# for Claude Code to iteratively fill in.
#

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

mkdir -p "$root_dir"/{config,docker,env,scripts,src/annotation_engine,tests,.github/workflows}

# Core text files
cat > "$root_dir/README.md" <<'EOF'
# Annotation-Engine (MVP)

Minimal, open-source scaffold for an AMP/CGC/OncoKB-aware somatic variant
annotation service.  Designed for expansion by Claude Code.
EOF

cat > "$root_dir/LICENSE" <<'EOF'
MIT License
EOF

cat > "$root_dir/.gitignore" <<'EOF'
__pycache__/
*.pyc
*.log
.env
.env.*
.cache/
.envrc
.idea/
.vscode/
dist/
build/
*.egg-info/
.venv/
.vep/
EOF

cat > "$root_dir/pyproject.toml" <<'EOF'
[tool.poetry]
name = "annotation-engine"
version = "0.0.1"
description = "Minimal AMP/CGC/OncoKB annotation starter"
authors = ["<YOUR NAME> <you@example.com>"]
packages = [{ include = "src" }]

[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.7"
click = "^8.1"
pandas = "^2.2"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2"
ruff   = "^0.4"
EOF

# Docker
cat > "$root_dir/docker/Dockerfile" <<'EOF'
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y curl perl build-essential git
# VEP install stub – Claude to append full commands.
COPY . /app
WORKDIR /app
RUN pip install poetry && poetry install --no-root
ENTRYPOINT ["poetry", "run", "python", "cli.py"]
EOF

# Conda environment
cat > "$root_dir/env/conda.yaml" <<'EOF'
name: annotation-engine
channels:
  - conda-forge
dependencies:
  - python=3.10
  - pip
  - pip:
      - pydantic==2.7.*
      - click==8.1.*
      - pandas==2.2.*
EOF

# Bash helper stubs
cat > "$root_dir/scripts/download_refs.sh" <<'EOF'
#!/usr/bin/env bash
# Placeholder – Claude will implement:
#   • Download dbNSFP, COSMIC Hotspots, OncoKB JSON, CIViC TSV, CGC list
#   • Verify checksums
echo "Stub for reference download script."
EOF
chmod +x "$root_dir/scripts/download_refs.sh"

cat > "$root_dir/scripts/build_vep_cache.sh" <<'EOF'
#!/usr/bin/env bash
# Placeholder – Claude will implement VEP cache + plugin setup.
echo "Stub for VEP cache builder."
EOF
chmod +x "$root_dir/scripts/build_vep_cache.sh"

# Config files
cat > "$root_dir/config/thresholds.yaml" <<'EOF'
tmb_high_cutoff: 10
msi_positive_values: ["MSI-H", "MSI-High"]
hrd_high_cutoff: 42
EOF

cat > "$root_dir/config/tumor_drivers.yaml" <<'EOF'
# Placeholder mapping: tumor_type ➜ list of canonical driver genes
lung:
  - EGFR
  - KRAS
EOF

# Source package stubs
touch "$root_dir/src/annotation_engine/__init__.py"

cat > "$root_dir/src/annotation_engine/models.py" <<'EOF'
from pydantic import BaseModel

class Evidence(BaseModel):
    code: str
    score: int
    data: dict

class TierResult(BaseModel):
    tier: str
    total_score: int
    evidence: list[Evidence]
EOF

for module in vep_runner evidence_aggregator tiering; do
  cat > "$root_dir/src/annotation_engine/${module}.py" <<EOF
\"\"\"Stub for ${module}. Claude Code will implement.\"\"\"
EOF
done

# CLI
cat > "$root_dir/cli.py" <<'EOF'
import json
import click
from pathlib import Path
from annotation_engine.vep_runner import run_vep
from annotation_engine.evidence_aggregator import gather_evidence
from annotation_engine.tiering import assign_tier

@click.command()
@click.argument("vcf", type=click.Path(exists=True))
@click.option("--cancer-type", required=True)
@click.option("--out", type=click.Path(), default="annotated.json")
def main(vcf, cancer_type, out):
    vep_json = run_vep(Path(vcf))
    ev = gather_evidence(vep_json, cancer_type)
    tiers = [assign_tier(item) for item in ev]
    Path(out).write_text(json.dumps([t.model_dump() for t in tiers], indent=2))

if __name__ == "__main__":
    main()
EOF

# Tests
mkdir -p "$root_dir/tests"
cat > "$root_dir/tests/test_smoke.py" <<'EOF'
def test_placeholder():
    assert True
EOF

# CI workflow
mkdir -p "$root_dir/.github/workflows"
cat > "$root_dir/.github/workflows/ci.yml" <<'EOF'
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: snok/install-poetry@v1
      - run: poetry install --no-root
      - run: poetry run pytest -q
EOF

echo "Repo skeleton created. Next: commit and let Claude Code expand each stub."

