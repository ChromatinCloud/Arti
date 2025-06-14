# Claude Code – Working Instructions for “annotation-engine”
<!-- Detailed architecture in docs/ANNOTATION_PIPELINE_BLUEPRINT.md -->
<!-- For high-level vision and Phase-2 requirements see docs/ROADMAP.md -->

## Immediate priorities:
Iteratively transform this minimal scaffold into a production-grade somatic
variant annotation service that:
1. Runs Ensembl VEP + plugins to obtain consequence-level annotations.
2. Aggregates evidence from COSMIC Hotspots, dbNSFP, OncoKB, CIViC, and CGC.
3. Assigns AMP/ASCO/CAP 2017 clinical tiers **and** CGC/VICC 2022 oncogenicity
   classes, resolving conflicts quantitatively.
4. Outputs JSON lines suitable for downstream report templating.

## Coding Conventions
* Python ≥ 3.10.  Do **not** import `typing.Optional` or `typing.List`; use
  plain `| None` unions and builtin lists.
* Package: `src/annotation_engine/`.
* One public entry-point: `cli.py` (Click). Keep CLI thin; heavy logic lives in
  `annotation_engine.*` modules.
* Pydantic v2 for typed data models; no inline code comments inside functions.
  Module-level docstrings are allowed.
* All critical constants (e.g., biomarker thresholds) live in YAML under
  `config/`. Do **not** hard-code these in Python.

## Immediate TODOs
1. **vep_runner.py**  
   * Shell out to `vep --json`, parse its JSON output into Python objects
     aligned with `models.Evidence`.
   * Accept path to VCF and return list of per-variant dicts.

2. **evidence_aggregator.py**  
   * Load OncoKB JSON, COSMIC Hotspots TSV, CIViC TSV on first call (cache in
     global variables).
   * Match VEP variant (gene, hgvs, coordinates) against the above to assemble
     evidence objects.

3. **tiering.py**  
   * Implement scoring table equivalent to CancerVar’s 12 CBP criteria.
   * Provide `assign_tier(evidence_list) -> TierResult`.

4. Extend `tests/` with new cases after each module lands.

## Reference Data Paths
Assume `scripts/download_refs.sh` downloads and unpacks everything under
`$REPO_ROOT/.refs/` using a predictable sub-folder structure:
