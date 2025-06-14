# Roadmap – Annotation-Engine

This document records the **Phase 2 / Phase 3 scope** so that any code
assistant understands the eventual destination but doesn’t treat it as an
immediate sprint backlog.

---

## 1. Quantitative Accuracy Module

* Compute per-variant likelihood that AMP/ACMG tier assignment is correct.
* Initial plan: train logistic-regression calibrator on historical truth set
  (variant, true tier) using feature vector = evidence scores.
* Expose probability field `tier_confidence` in JSON output.

## 2. Persistent Case Database

| Table | Key fields | Notes |
|-------|------------|-------|
| `patient` | `patient_uid PK` | No PHI, link to external MRN in hospital system. |
| `case`    | `case_id PK`, `patient_uid FK`, `dx` | Each tumor sample / time-point. |
| `variant` | `variant_uid PK`, `case_id FK`, `vcf_repr` | One row per submitted variant. |
| `interp`  | `interp_uid PK`, `variant_uid FK`, `tier`, `clinician_comment`, `timestamp` | Audit trail of manual overrides. |

* Chosen stack:                 **PostgreSQL + SQLModel** (async)  
* Migrations via                **Alembic**  
* Audit logging via             `jsonb` column `audit` capturing inputs, DB state, code hash.

## 3. Web & API Front-End

* **Upload endpoint** accepts VCF (multi-sample allowed) or JSON payload.
* **REST route** `/annotate` → returns list `[{variant, evidence, tier, confidence, prior_interps[]}]`
* **Clinician UI** (React) shows each variant-dx pair with:
  1. evidence table,
  2. tiers from engine,
  3. previous interpretations,
  4. textarea to enter/update interpretation.

No duplicated data: UI pulls live from the same DB used by the engine.

---

_Phase 1 remains focused on CLI + scoring engine.  Phase 2 tasks move into the
backlog once tiering pipeline is stable._
