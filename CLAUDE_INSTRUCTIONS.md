<!-- Detailed architecture lives in docs/ANNOTATION_PIPELINE_BLUEPRINT.md -->
<!-- Phase-2/3 backlog lives in docs/ROADMAP.md -->
<!-- Current sprint tasks live in TODO.md -->

# Claude Code – Project Guard-rails for “annotation-engine”

This file is **stable**. It tells Claude *how to work*; it does **not** list
ephemeral tasks.

---

## Coding Conventions (apply to every PR)

* Python ≥ 3.10 – use `| None` unions, no `typing.Optional`.
* One top-level package: `src/annotation_engine/`.
* No inline comments; put explanatory text in module docstrings.
* Config lives in `config/*.yaml`; never hard-code thresholds.
* Style/lint: `ruff --select I --target-version py310`.
* Unit tests in `tests/`, must run via `pytest -q`.
* Reference data expected under:

refs/
oncokb/oncokb_public.json
civic/civic_evidence.tsv
cosmic/cancer_hotspots.tsv
dbnsfp/dbNSFP4.5a.grch38.gz
cgc/cgc.tsv


---

## Phase-1 Mission  (unchanged)

1. Run **VEP + plugins** on VCF, output JSON.
2. Aggregate evidence from **dbNSFP, COSMIC Hotspots, OncoKB, CIViC, CGC**.
3. Score AMP 2017 tiers **and** VICC 2022 oncogenicity classes.
4. Emit `tier`, `confidence`, raw evidence per variant.

*See `TODO.md` for the tasks currently in flight.*
