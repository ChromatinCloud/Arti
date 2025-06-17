# Clinical Rules Implementation Blueprint

## Overview

This document defines how clinical interpretation rules are implemented based on best practices from leading tools (InterVar, CancerVar, PCGR, OncoKB, CGI). We adopt a **Guidelines-as-Code** approach with transparent evidence mapping and modular rule engines.

## Implementation Architecture

### Primary Templates & Implementation Strategy

**Primary Templates:**
- **InterVar:** ACMG/AMP evidence code implementation patterns (re-implement in our environment)
- **CancerVar:** Cancer-specific adaptations with CBP criteria (emulate rule logic)
- **PCGR:** ClinGen/CGC/VICC oncogenicity codes (ONCG_* patterns, re-implement clean)

**Implementation Approach:**
- **No External APIs:** Use local KB bundles instead of OncoKB API calls
- **Clean Re-implementation:** Take proven patterns but build in our modern environment
- **YAML-Driven Rules:** Transparent, updateable rule definitions

### Core Principles (Based on Industry Leaders)

1. **Evidence-Based Configuration** (InterVar pattern): Rules map directly to local KB evidence with explicit scoring
2. **Modular Rule Engines** (Hartwig pattern): Separate engines for each guideline framework
3. **Transparent Scoring** (OncoVI pattern): Complete audit trail of rule invocation
4. **Guidelines Traceability** (CancerVar pattern): Direct mapping from published guidelines to code
5. **Local Knowledge Bases** (Our approach): All KB data pre-indexed in versioned bundles

## Rule Engine Structure

### 0. Evidence Scoring Architecture (Updated 2025-06-17)

**Strategy Pattern Implementation** for modular, testable evidence scoring:

```python
# src/annotation_engine/scoring_strategies.py
class EvidenceScorer(ABC):
    """Abstract base for evidence scoring strategies"""
    @abstractmethod
    def can_score(self, evidence: Evidence) -> bool: ...
    @abstractmethod 
    def calculate_score(self, evidence: Evidence, context: ActionabilityType) -> float: ...

class FDAApprovedScorer(EvidenceScorer):
    """Handles FDA-approved biomarker evidence (highest weight)"""
    def can_score(self, evidence: Evidence) -> bool:
        return "FDA" in evidence.description or evidence.source_kb == "FDA"

class EvidenceScoringManager:
    """Coordinates all scoring strategies using Strategy Pattern"""
    def __init__(self, weights: EvidenceWeights):
        self.scorers = [FDAApprovedScorer(weights), GuidelineEvidenceScorer(weights), ...]
```

**Key Benefits:**
- **Isolated Testing**: Each scorer can be unit tested independently
- **Clean Separation**: Scoring logic decoupled from tiering engine
- **Easy Extension**: New evidence types add new scorer classes
- **Dependency Injection**: Mock scorers for comprehensive testing

### 1. AMP/ACMG Guidelines Implementation

Following **InterVar's** evidence-based approach with **CancerVar's** cancer-specific adaptations:

```yaml
# config/amp_acmg_rules.yaml
rules:
  pathogenic_very_strong:
    PVS1:
      name: "Null variant in tumor suppressor gene"
      description: "Nonsense, frameshift, canonical ±1 or 2 splice sites, initiation codon, single/multi-exon deletion in tumor suppressor"
      weight: 1.0
      evidence_sources:
        - vep_consequence: ["stop_gained", "frameshift_variant", "splice_donor_variant", "splice_acceptor_variant"]
        - cgc_role: "TSG"
        - cosmic_census: true
      implementation:
        function: "check_null_variant_in_tsg"
        parameters:
          consequences: ["stop_gained", "frameshift_variant"]
          splice_regions: ["splice_donor_variant", "splice_acceptor_variant"]
  
  pathogenic_strong:
    PS1:
      name: "Same amino acid change as established pathogenic variant"
      description: "Different nucleotide change but same amino acid change as established pathogenic variant"
      weight: 0.8
      evidence_sources:
        - clinvar_significance: ["Pathogenic", "Likely pathogenic"]
        - clinvar_review_status: ["reviewed_by_expert_panel", "criteria_provided_multiple_submitters"]
        - hgvsp_match: true
      implementation:
        function: "check_amino_acid_pathogenic_match"
        parameters:
          min_stars: 2
          exclude_conflicting: true
    
    PS2:
      name: "De novo in patient with disease and no family history"
      description: "Confirmed de novo occurrence in individual with disease and unaffected parents"
      weight: 0.8
      evidence_sources:
        - inheritance_pattern: "de_novo"
        - family_history: false
      implementation:
        function: "check_de_novo_occurrence"
        note: "Requires pedigree data - not implemented in MVP"
    
    PS3:
      name: "Well-established functional studies"
      description: "Well-established in vitro or in vivo functional studies supportive of damaging effect"
      weight: 0.8
      evidence_sources:
        - oncokb_mutation_effect: ["Loss-of-function", "Gain-of-function"]
        - civic_evidence_level: ["A", "B"]
        - functional_studies_count: ">= 3"
      implementation:
        function: "check_functional_evidence"
        parameters:
          min_studies: 3
          accepted_effects: ["Loss-of-function", "Gain-of-function"]
    
    PS4:
      name: "Prevalence in affected significantly increased"
      description: "Prevalence of variant in affected individuals significantly increased compared to controls"
      weight: 0.8
      evidence_sources:
        - cosmic_count: ">= 10"
        - gnomad_af: "<= 0.0001"
        - tumor_frequency: ">= 0.01"
      implementation:
        function: "check_prevalence_in_cancer"
        parameters:
          min_cosmic_count: 10
          max_population_af: 0.0001
          min_tumor_frequency: 0.01

  pathogenic_moderate:
    PM1:
      name: "Mutational hot spot or critical domain"
      description: "Located in mutational hot spot and/or critical and well-established functional domain"
      weight: 0.5
      evidence_sources:
        - cosmic_hotspot: true
        - pfam_domain: "critical"
        - oncokb_hotspot: true
      implementation:
        function: "check_hotspot_or_domain"
        parameters:
          hotspot_sources: ["cosmic", "oncokb", "civic"]
          critical_domains: true
    
    PM2:
      name: "Absent from controls"
      description: "Absent from controls or extremely low frequency if recessive"
      weight: 0.5
      evidence_sources:
        - gnomad_ac: 0
        - gnomad_af: "<= 0.00001"
      implementation:
        function: "check_population_frequency"
        parameters:
          max_allele_count: 0
          max_allele_frequency: 0.00001
    
    PM3:
      name: "Recessive disorder, detected in trans"
      description: "For recessive disorders, detected in trans with pathogenic variant"
      weight: 0.5
      implementation:
        function: "check_compound_heterozygote"
        note: "Requires phasing data - limited implementation in MVP"
    
    PM4:
      name: "Protein length changes"
      description: "Protein length changes due to in-frame indels in non-repeat region"
      weight: 0.5
      evidence_sources:
        - vep_consequence: ["inframe_insertion", "inframe_deletion"]
        - repeat_region: false
      implementation:
        function: "check_inframe_indel_non_repeat"
    
    PM5:
      name: "Novel missense at pathogenic amino acid"
      description: "Novel missense change at amino acid residue where different missense change determined to be pathogenic"
      weight: 0.5
      evidence_sources:
        - clinvar_same_codon: "pathogenic"
        - novel_change: true
      implementation:
        function: "check_novel_missense_pathogenic_codon"

  pathogenic_supporting:
    PP1:
      name: "Cosegregation with disease"
      weight: 0.25
      implementation:
        note: "Requires family studies - not implemented in MVP"
    
    PP2:
      name: "Missense variant in gene with low tolerance"
      description: "Missense variant in gene that has low rate of benign missense variation"
      weight: 0.25
      evidence_sources:
        - gene_constraint: "high"
        - missense_z_score: ">= 3.09"
      implementation:
        function: "check_gene_constraint"
        parameters:
          min_z_score: 3.09
    
    PP3:
      name: "Multiple computational evidence"
      description: "Multiple lines of computational evidence support deleterious effect"
      weight: 0.25
      evidence_sources:
        - sift_pred: "deleterious"
        - polyphen_pred: "probably_damaging"
        - cadd_phred: ">= 20"
        - revel_score: ">= 0.7"
      implementation:
        function: "check_computational_predictions"
        parameters:
          required_tools: 3
          cadd_threshold: 20
          revel_threshold: 0.7
    
    PP4:
      name: "Patient phenotype highly specific"
      weight: 0.25
      implementation:
        note: "Requires phenotype data - not implemented in MVP"
    
    PP5:
      name: "Reputable source recently reported pathogenic"
      description: "Reputable source recently reports variant as pathogenic but evidence not available"
      weight: 0.25
      evidence_sources:
        - oncokb_oncogenicity: "Oncogenic"
        - civic_significance: "Pathogenic"
      implementation:
        function: "check_reputable_source_pathogenic"

# Benign criteria follow similar structure...
```

### 2. CGC/VICC Guidelines Implementation

Based on **PCGR's** VICC integration and **CGI's** cancer-specific rules:

```yaml
# config/cgc_vicc_rules.yaml
oncogenicity_rules:
  oncogenic:
    ONC1:
      name: "Variant in oncogene with oncogenic mechanism"
      description: "Activating variant in known oncogene"
      weight: 1.0
      evidence_sources:
        - cgc_role: "oncogene"
        - oncokb_mutation_effect: "Gain-of-function"
        - cosmic_tier: 1
      implementation:
        function: "check_oncogene_activating"
    
    ONC2:
      name: "Tumor suppressor loss-of-function"
      description: "Inactivating variant in tumor suppressor gene"
      weight: 1.0
      evidence_sources:
        - cgc_role: "TSG"
        - vep_consequence: ["stop_gained", "frameshift_variant"]
        - oncokb_mutation_effect: "Loss-of-function"
      implementation:
        function: "check_tsg_inactivating"

  likely_oncogenic:
    LON1:
      name: "Variant in cancer gene with supportive evidence"
      weight: 0.7
      evidence_sources:
        - cgc_gene: true
        - cosmic_count: ">= 5"
        - functional_evidence: "moderate"
      implementation:
        function: "check_cancer_gene_supportive"

actionability_rules:
  tier_1:
    T1A:
      name: "FDA-approved therapy"
      description: "Biomarker required for FDA-approved therapy"
      weight: 1.0
      evidence_sources:
        - oncokb_level: "1"
        - fda_approval: true
      implementation:
        function: "check_fda_approved_biomarker"
    
    T1B:
      name: "Professional guideline therapy"
      description: "Biomarker included in professional guidelines"
      weight: 1.0
      evidence_sources:
        - oncokb_level: ["1", "2"]
        - nccn_inclusion: true
      implementation:
        function: "check_guideline_biomarker"

  tier_2:
    T2A:
      name: "Well-powered clinical trial"
      weight: 0.8
      evidence_sources:
        - oncokb_level: "3A"
        - clinical_trials: ">= 1"
      implementation:
        function: "check_clinical_trial_evidence"
```

### 3. OncoKB Integration Rules

Following **OncoKB's** structured annotation approach:

```yaml
# config/oncokb_rules.yaml
oncogenicity_mapping:
  oncogenic:
    weight: 1.0
    tier_impact: "increase"
  likely_oncogenic:
    weight: 0.7
    tier_impact: "increase" 
  resistance:
    weight: 0.5
    tier_impact: "resistance_note"
  vus:
    weight: 0.0
    tier_impact: "neutral"

therapeutic_levels:
  level_1:
    description: "FDA-recognized biomarker predictive of response to FDA-approved drug"
    tier_assignment: "Tier_I"
    weight: 1.0
  level_2:
    description: "Standard care biomarker predictive of response to FDA-approved drug"
    tier_assignment: "Tier_I"
    weight: 0.9
  level_3a:
    description: "Compelling clinical evidence supports biomarker as predictive"
    tier_assignment: "Tier_II"
    weight: 0.7
  level_3b:
    description: "Standard care or investigational biomarker predictive of response"
    tier_assignment: "Tier_II"
    weight: 0.6
  level_4:
    description: "Compelling biological evidence supports biomarker as predictive"
    tier_assignment: "Tier_III"
    weight: 0.4
```

## KB Field Mapping Implementation

### ClinVar Integration

```python
# src/annotation_engine/rules/clinvar_mapper.py
class ClinVarMapper:
    """Maps ClinVar annotations to rule evidence"""
    
    PATHOGENIC_TERMS = [
        "Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"
    ]
    
    REVIEW_STATUS_WEIGHTS = {
        "reviewed_by_expert_panel": 1.0,
        "criteria_provided_multiple_submitters": 0.8,
        "criteria_provided_single_submitter": 0.6,
        "no_assertion_provided": 0.2
    }
    
    def extract_evidence(self, clinvar_annotation: dict) -> dict:
        """Extract rule evidence from ClinVar annotation"""
        return {
            "is_pathogenic": clinvar_annotation.get("clinical_significance") in self.PATHOGENIC_TERMS,
            "review_weight": self.REVIEW_STATUS_WEIGHTS.get(
                clinvar_annotation.get("review_status"), 0.1
            ),
            "star_rating": self._calculate_star_rating(clinvar_annotation),
            "condition_match": self._check_condition_relevance(clinvar_annotation)
        }
```

### OncoKB Integration (Local Bundle Approach)

```python
# src/annotation_engine/rules/oncokb_mapper.py
class OncoKBLocalMapper:
    """Maps local OncoKB bundle data to rule evidence (no API calls)"""
    
    def __init__(self, kb_bundle_path: str):
        self.kb_bundle_path = kb_bundle_path
        self.oncokb_data = self._load_local_oncokb_data()
    
    def _load_local_oncokb_data(self) -> dict:
        """Load pre-downloaded OncoKB data from bundle"""
        import pandas as pd
        import json
        
        bundle_path = Path(self.kb_bundle_path) / "oncokb"
        
        # Load pre-processed OncoKB data
        with open(bundle_path / "variants.json") as f:
            variants = json.load(f)
        
        with open(bundle_path / "treatments.json") as f:
            treatments = json.load(f)
            
        # Load pre-built index for fast lookup
        variant_index = pd.read_pickle(bundle_path / "variant_index.pkl")
        
        return {
            "variants": variants,
            "treatments": treatments,
            "index": variant_index
        }
    
    ONCOGENICITY_WEIGHTS = {
        "Oncogenic": 1.0,
        "Likely Oncogenic": 0.7,
        "Predicted Oncogenic": 0.5,
        "Resistance": 0.5,
        "Likely Neutral": -0.3,
        "Inconclusive": 0.0
    }
    
    def extract_therapeutic_evidence(self, variant: dict) -> dict:
        """Extract therapeutic implications from local OncoKB data"""
        # Fast lookup in pre-indexed data
        variant_key = f"{variant['gene']}_{variant['hgvsp']}"
        oncokb_match = self.oncokb_data["index"].get(variant_key, {})
        
        if not oncokb_match:
            return {"no_oncokb_match": True}
            
        treatments = oncokb_match.get("treatments", [])
        return {
            "highest_level": self._get_highest_level(treatments),
            "fda_approved": any(t.get("fdaApproved") for t in treatments),
            "level_1_drugs": [t for t in treatments if t.get("level") == "LEVEL_1"],
            "resistance_drugs": [t for t in treatments if "Resistant" in t.get("levelLabel", "")],
            "oncogenicity": oncokb_match.get("oncogenicity", "Unknown"),
            "mutation_effect": oncokb_match.get("mutationEffect", "Unknown")
        }
```

### COSMIC Integration

```python
# src/annotation_engine/rules/cosmic_mapper.py
class COSMICMapper:
    """Maps COSMIC annotations to rule evidence"""
    
    def extract_hotspot_evidence(self, cosmic_annotation: dict) -> dict:
        """Extract hotspot and prevalence evidence"""
        return {
            "is_hotspot": cosmic_annotation.get("mutation_count", 0) >= 10,
            "cancer_types": cosmic_annotation.get("primary_sites", []),
            "prevalence_score": self._calculate_prevalence_score(cosmic_annotation),
            "tier_1_cancer": cosmic_annotation.get("tier") == 1
        }
```

## Rule Engine Implementation

### Core Rule Engine

```python
# src/annotation_engine/rules/engine.py
class RuleEngine:
    """Core rule evaluation engine following InterVar pattern"""
    
    def __init__(self, guideline_framework: str):
        self.framework = guideline_framework
        self.rules = self._load_rules(guideline_framework)
        self.evidence_cache = {}
    
    def evaluate_variant(self, variant: Variant, kb_annotations: dict) -> TieringResult:
        """Evaluate all rules for a variant"""
        invoked_rules = []
        total_weight = 0.0
        
        for rule_id, rule_config in self.rules.items():
            evidence = self._extract_rule_evidence(rule_config, kb_annotations)
            
            if self._rule_applies(rule_config, evidence):
                invocation = RuleInvocation(
                    rule_id=rule_id,
                    evidence_strength=self._calculate_evidence_strength(evidence),
                    applied_weight=self._calculate_applied_weight(rule_config, evidence),
                    evidence_sources=evidence.get("sources", []),
                    rule_context=evidence
                )
                invoked_rules.append(invocation)
                total_weight += invocation.applied_weight
        
        tier = self._assign_tier(total_weight, invoked_rules)
        confidence = self._calculate_confidence(invoked_rules, total_weight)
        
        return TieringResult(
            variant_id=variant.variant_id,
            guideline_framework=self.framework,
            tier_assigned=tier,
            confidence_score=confidence,
            rules_invoked=invoked_rules
        )
    
    def _extract_rule_evidence(self, rule_config: dict, kb_annotations: dict) -> dict:
        """Extract evidence for a specific rule"""
        evidence = {"sources": []}
        
        for source_type, criteria in rule_config.get("evidence_sources", {}).items():
            if source_type in kb_annotations:
                source_evidence = self._evaluate_criteria(
                    criteria, kb_annotations[source_type]
                )
                evidence.update(source_evidence)
                if source_evidence.get("matches"):
                    evidence["sources"].append(source_type)
        
        return evidence
```

### Conflict Resolution

Following **CancerVar's** approach to handling conflicting evidence:

```python
class ConflictResolver:
    """Resolves conflicts between different evidence sources"""
    
    def resolve_conflicts(self, rule_invocations: List[RuleInvocation]) -> List[RuleInvocation]:
        """Apply conflict resolution rules"""
        pathogenic_rules = [r for r in rule_invocations if r.rule_id.startswith(('PVS', 'PS', 'PM', 'PP'))]
        benign_rules = [r for r in rule_invocations if r.rule_id.startswith(('BA', 'BS', 'BP'))]
        
        # Apply ACMG conflict resolution guidelines
        if pathogenic_rules and benign_rules:
            return self._apply_acmg_conflict_resolution(pathogenic_rules, benign_rules)
        
        return rule_invocations
    
    def _apply_acmg_conflict_resolution(self, pathogenic, benign):
        """Implement ACMG conflict resolution algorithm"""
        # Strong pathogenic evidence overrides moderate benign
        strong_pathogenic = [r for r in pathogenic if r.rule_id.startswith(('PVS', 'PS'))]
        strong_benign = [r for r in benign if r.rule_id.startswith(('BA', 'BS'))]
        
        if strong_pathogenic and not strong_benign:
            # Downweight conflicting benign evidence
            for rule in benign:
                if rule.evidence_strength != EvidenceStrength.STRONG:
                    rule.applied_weight *= 0.5
        
        return pathogenic + benign
```

## Threshold Management

Based on **PCGR's** configuration approach:

```yaml
# config/clinical_thresholds.yaml
population_frequency:
  rare_variant_threshold: 0.01
  very_rare_threshold: 0.001
  absent_threshold: 0.00001

computational_predictions:
  cadd_pathogenic_threshold: 20
  revel_pathogenic_threshold: 0.7
  sift_deleterious_threshold: 0.05
  polyphen_damaging_threshold: 0.453

cancer_specific:
  cosmic_hotspot_min_count: 10
  tumor_frequency_threshold: 0.01
  oncokb_level_weights:
    level_1: 1.0
    level_2: 0.9
    level_3a: 0.7
    level_3b: 0.6
    level_4: 0.4

tier_assignment:
  amp_acmg:
    tier_i_min_weight: 0.9
    tier_ii_min_weight: 0.6
    tier_iii_min_weight: 0.3
  
  cgc_vicc:
    oncogenic_min_weight: 0.8
    likely_oncogenic_min_weight: 0.5
    
  oncokb:
    level_1_2: "Tier_I"
    level_3a_3b: "Tier_II"
    level_4: "Tier_III"
```

This implementation provides transparent, auditable rule evaluation following best practices from leading clinical annotation tools, with complete traceability from clinical guidelines to code execution.