# Configuration Management Blueprint

## Overview

This document defines configuration management strategies based on best practices from leading clinical annotation tools (OncoKB, PCGR, CGI, CancerVar, InterVar). We adopt a **versioned configuration** approach with **guidelines-as-code** and **hot-reload capability**.

## Configuration Architecture

### Core Principles (Based on Industry Leaders)

1. **Versioned Configurations** (OncoKB pattern): Track configuration changes with clinical impact
2. **YAML-First Approach** (CGI/CKG pattern): Human-readable, structured configuration
3. **Modular Configuration** (PCGR pattern): Separate concerns by clinical domain
4. **Hot-Reload Capability** (Enterprise pattern): Update configurations without service restart

## Configuration Structure

### Directory Organization

Following **PCGR's** modular approach with **OncoKB's** versioning strategy:

```
config/
├── version.yaml                    # Configuration version metadata
├── clinical_guidelines/            # Clinical interpretation rules
│   ├── amp_acmg_2015.yaml         # AMP/ACMG guidelines v2015
│   ├── amp_acmg_2017.yaml         # AMP/ACMG guidelines v2017 (current)
│   ├── cgc_vicc_2022.yaml         # CGC/VICC guidelines v2022
│   └── oncokb_levels.yaml         # OncoKB therapeutic levels
├── thresholds/                     # Clinical thresholds
│   ├── population_frequency.yaml   # Population frequency cutoffs
│   ├── computational_scores.yaml   # CADD, REVEL, SIFT thresholds
│   ├── quality_filters.yaml       # VCF quality thresholds
│   └── biomarker_cutoffs.yaml     # TMB, MSI, HRD cutoffs
├── knowledge_bases/               # KB configuration
│   ├── oncokb_config.yaml        # OncoKB API and processing
│   ├── civic_config.yaml         # CIViC data processing
│   ├── cosmic_config.yaml        # COSMIC data processing
│   └── clinvar_config.yaml       # ClinVar data processing
├── canned_text/                   # Text generation templates
│   ├── templates.yaml            # Canned text templates
│   └── kb_mappings.yaml          # KB to text mappings
└── environments/                  # Environment-specific configs
    ├── development.yaml
    ├── staging.yaml
    └── production.yaml
```

### Version Metadata

Following **OncoKB's** versioning approach:

```yaml
# config/version.yaml
configuration_version: "v2024.1.0"
created_date: "2024-01-01"
effective_date: "2024-01-15"
guidelines_implemented:
  amp_acmg: "2017"
  cgc_vicc: "2022"
  oncokb: "v2024.01"
knowledge_base_versions:
  oncokb: "2024-01-01"
  civic: "2024-01-01"
  cosmic: "v99"
  clinvar: "2024-01-01"
  gnomad: "v4.0.0"
deprecation_date: "2024-07-01"  # When this config becomes obsolete
changelog:
  - version: "v2024.1.0"
    date: "2024-01-01"
    changes:
      - "Updated OncoKB therapeutic levels"
      - "Added new COSMIC hotspot thresholds"
      - "Refined ACMG PP3 computational evidence criteria"
```

## Clinical Guidelines Configuration

### AMP/ACMG Rules Configuration

Based on **InterVar's** evidence-based approach with **CancerVar's** cancer adaptations:

```yaml
# config/clinical_guidelines/amp_acmg_2017.yaml
metadata:
  guideline_name: "AMP/ACMG/CAP Guidelines for Sequence Variant Interpretation"
  version: "2017"
  publication: "PMID:28552198"
  implementation_date: "2024-01-01"
  last_updated: "2024-01-01"

evidence_codes:
  pathogenic_very_strong:
    PVS1:
      name: "null variant (nonsense, frameshift, canonical ±1 or 2 splice sites, initiation codon, single or multiexon deletion) in a gene where LOF is a known mechanism of disease"
      weight: 1.0
      category: "LOF"
      implementation:
        vep_consequences:
          - "stop_gained"
          - "frameshift_variant"
          - "splice_donor_variant"
          - "splice_acceptor_variant"
          - "start_lost"
        gene_mechanism: "LOF"
        exclusions:
          - "splice_region_variant"  # Not canonical splice site
          - "last_exon_nonsense"     # May escape NMD
      knowledge_base_requirements:
        cgc_role: ["TSG", "oncogene"]  # Must be in Cancer Gene Census
        oncokb_gene: true              # Must be in OncoKB
      thresholds:
        min_exon_number: 2            # Exclude single exon genes
        canonical_splice_distance: 2  # ±2 from exon boundary

  pathogenic_strong:
    PS1:
      name: "Same amino acid change as a previously established pathogenic variant regardless of nucleotide change"
      weight: 0.8
      category: "functional"
      implementation:
        hgvsp_match: true
        nucleotide_different: true
      knowledge_base_requirements:
        clinvar_pathogenic: true
        min_review_stars: 2
      exclusions:
        - "synonymous_variant"
        - "stop_retained_variant"
      thresholds:
        min_clinvar_submissions: 3
        required_review_status:
          - "reviewed_by_expert_panel"
          - "criteria_provided_multiple_submitters"

    PS2:
      name: "De novo (both maternity and paternity confirmed) in a patient with the disease and no family history"
      weight: 0.8
      category: "segregation"
      implementation:
        inheritance_pattern: "de_novo"
        family_confirmation: required
      note: "Requires pedigree data - implementation pending"
      
    PS3:
      name: "Well-established in vitro or in vivo functional studies supportive of a damaging effect on the gene or gene product"
      weight: 0.8
      category: "functional"
      implementation:
        functional_studies: true
      knowledge_base_requirements:
        oncokb_mutation_effect: 
          - "Loss-of-function"
          - "Gain-of-function"
        civic_evidence_level: ["A", "B"]
        min_pmid_count: 3
      thresholds:
        min_functional_studies: 2
        accepted_study_types:
          - "cell_viability"
          - "protein_function"
          - "transcriptional_activity"

    PS4:
      name: "The prevalence of the variant in affected individuals is significantly increased compared with the prevalence in controls"
      weight: 0.8
      category: "prevalence"
      implementation:
        case_control_analysis: true
      knowledge_base_requirements:
        cosmic_count: ">= 10"
        gnomad_af: "<= 0.0001"
      thresholds:
        min_cosmic_occurrences: 10
        max_population_af: 0.0001
        min_tumor_frequency: 0.01

  pathogenic_moderate:
    PM1:
      name: "Located in a mutational hot spot and/or critical and well-established functional domain without benign variation"
      weight: 0.5
      category: "location"
      implementation:
        hotspot_check: true
        critical_domain: true
        benign_variation_check: true
      knowledge_base_requirements:
        cosmic_hotspot: true
        pfam_domain: "critical"
        oncokb_hotspot: true
      thresholds:
        min_hotspot_count: 5
        benign_variation_threshold: 2  # Max benign variants in domain

    PM2:
      name: "Absent from controls (or at extremely low frequency if recessive) in Exome Sequencing Project, 1000 Genomes Project, or Exome Aggregation Consortium"
      weight: 0.5
      category: "frequency"
      implementation:
        population_frequency: true
      knowledge_base_requirements:
        gnomad_ac: 0
        gnomad_af: "<= 0.00001"
      thresholds:
        max_allele_count: 0
        max_allele_frequency: 0.00001
        population_databases:
          - "gnomAD"
          - "ExAC"
          - "1000G"

    PM3:
      name: "For recessive disorders, detected in trans with a pathogenic variant"
      weight: 0.5
      category: "segregation"
      implementation:
        compound_heterozygote: true
        phase_information: required
      note: "Requires phasing data - implementation pending"

    PM4:
      name: "Protein length changes as a result of in-frame deletions/insertions in a nonrepeat region or stop-loss variants"
      weight: 0.5
      category: "structural"
      implementation:
        protein_length_change: true
        repeat_region_check: true
      vep_consequences:
        - "inframe_insertion"
        - "inframe_deletion"
        - "stop_lost"
      thresholds:
        min_length_change: 1  # amino acids
        repeat_region_exclusion: true

    PM5:
      name: "Novel missense change at an amino acid residue where a different missense change determined to be pathogenic has been seen before"
      weight: 0.5
      category: "functional"
      implementation:
        novel_missense: true
        same_codon_pathogenic: true
      knowledge_base_requirements:
        clinvar_same_codon: "pathogenic"
        different_nucleotide: true

    PM6:
      name: "Assumed de novo, but without confirmation of paternity and maternity"
      weight: 0.5
      category: "segregation"
      implementation:
        assumed_de_novo: true
      note: "Requires pedigree data - implementation pending"

  pathogenic_supporting:
    PP1:
      name: "Cosegregation with disease in multiple affected family members in a gene definitively known to cause the disease"
      weight: 0.25
      category: "segregation"
      note: "Requires family studies - implementation pending"

    PP2:
      name: "Missense variant in a gene that has a low rate of benign missense variation and in which missense variants are a common mechanism of disease"
      weight: 0.25
      category: "gene_constraint"
      implementation:
        gene_constraint: true
        missense_mechanism: true
      knowledge_base_requirements:
        missense_z_score: ">= 3.09"
        gene_tolerance: "intolerant"
      thresholds:
        min_z_score: 3.09
        max_oe_lof: 0.35

    PP3:
      name: "Multiple lines of computational evidence support a deleterious effect on the gene or gene product"
      weight: 0.25
      category: "computational"
      implementation:
        computational_predictions: true
      computational_tools:
        sift:
          threshold: 0.05
          prediction: "deleterious"
        polyphen2:
          threshold: 0.453
          prediction: "probably_damaging"
        cadd:
          threshold: 20
        revel:
          threshold: 0.7
        mutationtaster:
          prediction: "disease_causing"
      thresholds:
        min_supporting_tools: 3
        consensus_requirement: 0.7  # 70% of tools must agree

    PP4:
      name: "Patient's phenotype or family history is highly specific for a disease with a single genetic etiology"
      weight: 0.25
      category: "phenotype"
      note: "Requires phenotype data - implementation pending"

    PP5:
      name: "Reputable source recently reports variant as pathogenic, but the evidence is not available to the laboratory to perform an independent evaluation"
      weight: 0.25
      category: "literature"
      implementation:
        reputable_source: true
      knowledge_base_requirements:
        oncokb_oncogenicity: "Oncogenic"
        civic_significance: "Pathogenic"
        recent_publication: true
      thresholds:
        max_age_months: 12  # Publication within last year

# Benign criteria would follow similar structure...
```

### CGC/VICC Guidelines Configuration

Following **PCGR's** VICC implementation:

```yaml
# config/clinical_guidelines/cgc_vicc_2022.yaml
metadata:
  guideline_name: "VICC Variant Interpretation for Cancer Consortium"
  version: "2022"
  publication: "PMID:35101186"
  implementation_date: "2024-01-01"

oncogenicity_classification:
  oncogenic:
    criteria:
      - rule_id: "ONC1"
        name: "Variant is a hotspot in cancer or located in critical functional domain"
        weight: 1.0
        requirements:
          cosmic_hotspot: true
          critical_domain: true
      - rule_id: "ONC2"
        name: "Variant is a well-characterized oncogenic variant"
        weight: 1.0
        requirements:
          oncokb_oncogenicity: "Oncogenic"
          literature_support: "strong"

  likely_oncogenic:
    criteria:
      - rule_id: "LON1"
        name: "Variant is in oncogene with supportive functional evidence"
        weight: 0.7
        requirements:
          cgc_role: "oncogene"
          functional_evidence: "moderate"

actionability_classification:
  tier_i:
    criteria:
      - rule_id: "T1A"
        name: "Variants that predict response or resistance to therapies that are FDA approved or included in professional guidelines for the tumor type in question"
        weight: 1.0
        requirements:
          oncokb_level: ["1", "2"]
          fda_approval: true
      - rule_id: "T1B"
        name: "Variants that predict response or resistance to therapies with professional guideline support"
        weight: 1.0
        requirements:
          professional_guidelines: true
          nccn_inclusion: true

  tier_ii:
    criteria:
      - rule_id: "T2A"
        name: "Variants that predict response or resistance to therapies with well-powered studies"
        weight: 0.8
        requirements:
          oncokb_level: ["3A", "3B"]
          clinical_evidence: "strong"

  tier_iii:
    criteria:
      - rule_id: "T3A"
        name: "Variants that predict response or resistance to therapies based on compelling biological evidence"
        weight: 0.6
        requirements:
          oncokb_level: "4"
          biological_evidence: "compelling"

  tier_iv:
    criteria:
      - rule_id: "T4A"
        name: "Variants of unknown clinical significance"
        weight: 0.0
        requirements:
          insufficient_evidence: true
```

## Threshold Configuration

### Population Frequency Thresholds

Based on **CancerVar** and **PCGR** approaches:

```yaml
# config/thresholds/population_frequency.yaml
metadata:
  name: "Population Frequency Thresholds"
  version: "v2024.1"
  based_on: "ACMG/AMP Guidelines and Cancer-specific adaptations"

# ACMG/AMP frequency thresholds
acmg_thresholds:
  pm2_absent_threshold: 0.00001      # PM2: Absent from controls
  ba1_common_threshold: 0.05         # BA1: Common in population
  bs1_frequent_threshold: 0.01       # BS1: Frequent in population

# Cancer-specific frequency thresholds
cancer_thresholds:
  somatic_rare_threshold: 0.001      # Rare in population for somatic variants
  germline_rare_threshold: 0.0001    # Rare in population for germline variants
  founder_mutation_threshold: 0.01   # Founder mutations may be more frequent

# Population-specific thresholds
population_specific:
  african:
    pm2_threshold: 0.00001
    bs1_threshold: 0.01
  european:
    pm2_threshold: 0.00001
    bs1_threshold: 0.01
  east_asian:
    pm2_threshold: 0.00001
    bs1_threshold: 0.01
  latino:
    pm2_threshold: 0.00001
    bs1_threshold: 0.01

# Database-specific configurations
databases:
  gnomad:
    version: "v4.0.0"
    total_alleles_threshold: 100000    # Minimum total alleles for reliable frequency
    quality_filters: ["PASS"]
  
  exac:
    version: "v0.3.1"
    deprecated: true
    use_if_gnomad_unavailable: true
```

### Computational Score Thresholds

Following **InterVar** and **CancerVar** computational evidence approaches:

```yaml
# config/thresholds/computational_scores.yaml
metadata:
  name: "Computational Prediction Thresholds"
  version: "v2024.1"
  last_updated: "2024-01-01"

# ACMG PP3/BP4 computational evidence
pp3_criteria:
  name: "Multiple lines of computational evidence support deleterious effect"
  required_tools: 3
  consensus_threshold: 0.7
  
  tools:
    sift:
      pathogenic_threshold: 0.05
      pathogenic_prediction: "deleterious"
      weight: 1.0
    
    polyphen2_hdiv:
      pathogenic_threshold: 0.453
      pathogenic_prediction: "probably_damaging"
      weight: 1.0
    
    polyphen2_hvar:
      pathogenic_threshold: 0.453
      pathogenic_prediction: "probably_damaging"
      weight: 1.0
    
    mutation_taster:
      pathogenic_prediction: "disease_causing"
      weight: 1.0
    
    cadd:
      pathogenic_threshold: 20.0
      weight: 1.5  # Higher weight for integrative score
    
    revel:
      pathogenic_threshold: 0.7
      weight: 1.5
    
    dann:
      pathogenic_threshold: 0.98
      weight: 1.0
    
    fathmm:
      pathogenic_threshold: -1.5
      pathogenic_prediction: "damaging"
      weight: 1.0
    
    provean:
      pathogenic_threshold: -2.5
      pathogenic_prediction: "deleterious"
      weight: 1.0

bp4_criteria:
  name: "Multiple lines of computational evidence support benign effect"
  required_tools: 3
  consensus_threshold: 0.7
  
  benign_predictions:
    sift: "tolerated"
    polyphen2: "benign"
    mutation_taster: "polymorphism"
    fathmm: "tolerated"
    provean: "neutral"

# Cancer-specific computational thresholds
cancer_specific:
  oncogene_thresholds:
    cadd_min: 15.0    # Lower threshold for oncogenes
    revel_min: 0.5
  
  tumor_suppressor_thresholds:
    cadd_min: 20.0    # Standard threshold for TSGs
    revel_min: 0.7

# Meta-predictor thresholds
meta_predictors:
  metasvm:
    pathogenic_prediction: "D"
    pathogenic_score: 0.5
  
  metalr:
    pathogenic_prediction: "D"
    pathogenic_score: 0.5
  
  m_cap:
    pathogenic_threshold: 0.025
  
  primateai:
    pathogenic_threshold: 0.8
```

### Biomarker Cutoffs

Following **PCGR's** biomarker integration:

```yaml
# config/thresholds/biomarker_cutoffs.yaml
metadata:
  name: "Clinical Biomarker Thresholds"
  version: "v2024.1"
  guidelines: "ESMO/NCCN/CAP recommendations"

tumor_mutational_burden:
  high_tmb_threshold: 10.0          # mutations per Mb
  very_high_tmb_threshold: 20.0     # mutations per Mb
  assay_type_adjustments:
    wes: 1.0                        # Whole exome multiplier
    wgs: 0.8                        # Whole genome multiplier (lower background)
    panel: 1.2                      # Panel-based (higher noise)
  
  cancer_type_specific:
    colorectal: 12.0
    endometrial: 15.0
    melanoma: 10.0
    lung: 10.0
    bladder: 10.0

microsatellite_instability:
  msi_high_threshold: 0.3           # MSI score threshold
  markers_required: 5               # Minimum markers for assessment
  instability_threshold: 0.2        # Per-marker instability threshold

homologous_recombination_deficiency:
  hrd_positive_threshold: 42        # HRD score threshold
  loh_threshold: 16                 # Loss of heterozygosity score
  tai_threshold: 11                 # Telomeric allelic imbalance
  lst_threshold: 15                 # Large-scale state transitions

expression_biomarkers:
  pd_l1:
    high_expression: 50             # % positive cells
    moderate_expression: 20
    low_expression: 1
  
  her2:
    positive_threshold: 3           # IHC 3+
    equivocal_range: [2, 2]        # IHC 2+
```

## Knowledge Base Configuration

### OncoKB Configuration

Following **OncoKB's** API integration approach:

```yaml
# config/knowledge_bases/oncokb_config.yaml
metadata:
  name: "OncoKB Configuration"
  version: "v2024.01"
  api_version: "v1"

api_settings:
  base_url: "https://oncokb.org/api/v1"
  timeout: 30
  retry_attempts: 3
  rate_limiting:
    requests_per_minute: 60
    burst_limit: 10

authentication:
  token_required: true
  token_env_var: "ONCOKB_API_TOKEN"
  
endpoints:
  genes: "/genes"
  variants: "/variants"
  evidence: "/evidence"
  levels: "/levels"
  treatments: "/treatments"

data_processing:
  cache_duration: 3600              # seconds
  batch_size: 100                   # variants per batch
  
  level_mapping:
    "LEVEL_1": "Tier_I"
    "LEVEL_2": "Tier_I"
    "LEVEL_3A": "Tier_II"
    "LEVEL_3B": "Tier_II"
    "LEVEL_4": "Tier_III"
    "LEVEL_R1": "Resistance"
    "LEVEL_R2": "Resistance"

  oncogenicity_mapping:
    "Oncogenic": 1.0
    "Likely Oncogenic": 0.7
    "Predicted Oncogenic": 0.5
    "Resistance": 0.5
    "Likely Neutral": -0.3
    "Inconclusive": 0.0

quality_control:
  required_fields:
    - "oncogenicity"
    - "mutationEffect"
    - "highestSensitiveLevel"
  
  validation_rules:
    - field: "oncogenicity"
      allowed_values: ["Oncogenic", "Likely Oncogenic", "Predicted Oncogenic", "Resistance", "Likely Neutral", "Inconclusive"]
    - field: "mutationEffect"
      allowed_values: ["Gain-of-function", "Loss-of-function", "Switch-of-function", "Neutral", "Inconclusive"]
```

## Environment-Specific Configuration

### Development Environment

```yaml
# config/environments/development.yaml
environment: "development"

database:
  url: "postgresql://localhost:5432/annotation_engine_dev"
  echo_sql: true
  pool_size: 5

logging:
  level: "DEBUG"
  format: "detailed"
  file_logging: true
  
api:
  debug: true
  reload: true
  host: "127.0.0.1"
  port: 8000

knowledge_bases:
  cache_enabled: false              # Disable caching for development
  mock_responses: true              # Use mock data when APIs unavailable
  
quality_filters:
  strict_mode: false                # Relaxed QC for testing
  
performance:
  background_tasks: false           # Synchronous processing for debugging
```

### Production Environment

```yaml
# config/environments/production.yaml
environment: "production"

database:
  url_env_var: "DATABASE_URL"
  echo_sql: false
  pool_size: 20
  pool_timeout: 30
  
logging:
  level: "INFO"
  format: "json"
  file_logging: true
  audit_logging: true

api:
  debug: false
  reload: false
  host: "0.0.0.0"
  port: 8000
  workers: 4

knowledge_bases:
  cache_enabled: true
  cache_ttl: 86400                  # 24 hours
  mock_responses: false
  
quality_filters:
  strict_mode: true                 # Enforce all quality checks
  
performance:
  background_tasks: true
  task_queue: "redis"
  
security:
  cors_enabled: true
  allowed_origins: ["https://annotation-ui.hospital.org"]
  api_key_required: true
```

## Configuration Loading and Validation

### Configuration Manager

```python
# src/annotation_engine/config/manager.py
class ConfigurationManager:
    """Manage configuration loading, validation, and hot-reload"""
    
    def __init__(self, config_dir: str = "config", environment: str = "development"):
        self.config_dir = Path(config_dir)
        self.environment = environment
        self.config_cache = {}
        self.last_modified = {}
        
    def load_configuration(self) -> dict:
        """Load complete configuration with validation"""
        config = {
            "version": self._load_yaml("version.yaml"),
            "clinical_guidelines": self._load_clinical_guidelines(),
            "thresholds": self._load_thresholds(),
            "knowledge_bases": self._load_knowledge_base_configs(),
            "environment": self._load_environment_config()
        }
        
        self._validate_configuration(config)
        return config
    
    def _load_clinical_guidelines(self) -> dict:
        """Load all clinical guideline configurations"""
        guidelines_dir = self.config_dir / "clinical_guidelines"
        guidelines = {}
        
        for guideline_file in guidelines_dir.glob("*.yaml"):
            guideline_name = guideline_file.stem
            guidelines[guideline_name] = self._load_yaml(guideline_file)
        
        return guidelines
    
    def _validate_configuration(self, config: dict):
        """Validate configuration integrity"""
        # Check version compatibility
        version = config["version"]["configuration_version"]
        if not self._is_compatible_version(version):
            raise ConfigurationError(f"Incompatible configuration version: {version}")
        
        # Validate clinical guidelines
        for guideline_name, guideline_config in config["clinical_guidelines"].items():
            self._validate_guideline_config(guideline_name, guideline_config)
        
        # Validate thresholds
        self._validate_thresholds(config["thresholds"])
    
    def hot_reload(self) -> bool:
        """Check for configuration changes and reload if necessary"""
        modified = False
        
        for config_file in self.config_dir.rglob("*.yaml"):
            current_mtime = config_file.stat().st_mtime
            if config_file not in self.last_modified or current_mtime > self.last_modified[config_file]:
                self.last_modified[config_file] = current_mtime
                modified = True
        
        if modified:
            self.config_cache.clear()
            return True
        
        return False
```

This configuration management approach provides clinical-grade reliability with transparent versioning, validation, and hot-reload capabilities following industry best practices.