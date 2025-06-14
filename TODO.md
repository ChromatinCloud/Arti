# TODO – Sprint starting 2025-06-14

> Update, rename, or replace this file each sprint.

## Immediate tasks

1. **vep_runner.py**
   * Execute `vep --json`; return list of dicts compatible with `models.Evidence`.

2. **evidence_aggregator.py**
   * Lazy-load data from `.refs/`; attach OncoKB, CIViC, COSMIC, dbNSFP evidence.

3. **tiering.py**
   * Implement 12 CancerVar CBP weights; return `TierResult`.

4. **Smoke test**
   * Expand `tests/test_smoke.py` so demo variants yield Tier I and Tier III.