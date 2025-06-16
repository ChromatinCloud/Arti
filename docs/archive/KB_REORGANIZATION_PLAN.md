# Knowledge Base Reorganization Plan

## New KB Directory Structure

Based on data type, usage patterns, and canned text requirements, here's the proposed reorganization:

```
.refs/
├── clinical_evidence/           # For Variant Dx Interpretation (Text Type 4)
│   ├── clinvar/                # Pathogenicity classifications
│   ├── civic/                  # Clinical interpretations  
│   ├── oncokb/                 # Therapeutic levels
│   └── cgi/                    # Cancer Genome Interpreter
│
├── population_frequencies/      # For General Variant Info (Text Type 3)
│   ├── gnomad/                 # Population allele frequencies
│   ├── dbsnp/                  # Variant identifiers
│   └── tcga_frequencies/       # Cancer cohort frequencies
│
├── gene_annotations/           # For General Gene Info (Text Type 1)
│   ├── hgnc/                  # Official gene symbols
│   ├── ncbi_gene/             # Gene descriptions
│   ├── uniprot/               # Protein function
│   ├── pfam/                  # Domain architecture
│   └── gene_panels/           # Disease gene lists
│
├── cancer_genes/              # For Gene Dx Interpretation (Text Type 2)
│   ├── cosmic_cgc/            # Cancer Gene Census
│   ├── oncovi_lists/          # TSG/oncogene unions
│   ├── cancermine/            # Literature mining
│   └── clingen/               # Gene curation
│
├── hotspots/                  # For Variant Dx Interpretation (Text Type 4)
│   ├── msk_hotspots/          # Memorial Sloan Kettering
│   ├── cosmic_hotspots/       # COSMIC recurrence
│   ├── civic_hotspots/        # CIViC hotspots
│   ├── 3d_hotspots/           # Structure-based
│   └── oncovi_hotspots/       # Processed unions
│
├── functional_predictions/     # For Variant Dx Interpretation (Text Type 4)
│   ├── vep_cache/             # VEP cache files
│   ├── vep_plugins/           # Plugin .pm files
│   ├── plugin_data/           # Plugin data files
│   │   ├── conservation/      # PhyloP, GERP
│   │   ├── pathogenicity/     # dbNSFP, REVEL, etc
│   │   ├── splicing/          # SpliceAI, dbscSNV
│   │   └── protein_impact/    # AlphaMissense, EVE
│   └── indices/               # Index files
│
├── expression_functional/      # For Gene Dx Interpretation (Text Type 2)
│   ├── tcga_expression/       # TCGA TPM data
│   ├── depmap_effects/        # CRISPR dependencies
│   ├── depmap_expression/     # Cell line expression
│   └── gtex/                  # Normal tissue (future)
│
├── clinical_context/          # For multiple text types
│   ├── biomarkers/            # TMB/MSI thresholds (Text Type 8)
│   ├── oncotree/              # Cancer classifications
│   ├── drug_targets/          # DGIdb, Open Targets
│   └── clinical_trials/       # Trial matching
│
├── structural_variants/       # For Chromosomal Alterations (Text Type 6)
│   ├── fusion_databases/      # Gene fusions
│   ├── cnv_resources/         # Copy number
│   └── sv_annotations/        # Structural variants
│
├── secondary_findings/        # For Incidental Findings (Text Type 5)
│   ├── acmg_sf/              # ACMG SF gene lists
│   └── pharmgkb/             # Pharmacogenomics
│
├── integrated_bundles/        # Pre-processed combinations
│   ├── pcgr/                 # PCGR comprehensive bundle
│   └── processed/            # Our processed versions
│
└── infrastructure/           # Technical support files
    ├── indices/              # All index files
    ├── temp/                 # Temporary downloads
    └── metadata/             # Version info, checksums
```

## Mapping from Old to New Locations

### Core Clinical Evidence
```
OLD: .refs/clinvar/
NEW: .refs/clinical_evidence/clinvar/

OLD: .refs/civic/
NEW: .refs/clinical_evidence/civic/

OLD: .refs/oncokb/
NEW: .refs/clinical_evidence/oncokb/
```

### Population Data
```
OLD: .refs/gnomad/
NEW: .refs/population_frequencies/gnomad/

OLD: .refs/dbsnp/
NEW: .refs/population_frequencies/dbsnp/
```

### Gene Resources
```
OLD: .refs/gene_mappings/
NEW: .refs/gene_annotations/hgnc/

OLD: .refs/uniprot/
NEW: .refs/gene_annotations/uniprot/

OLD: .refs/pfam/
NEW: .refs/gene_annotations/pfam/
```

### Cancer-Specific
```
OLD: .refs/cosmic/
NEW: .refs/cancer_genes/cosmic_cgc/

OLD: .refs/cgc/
NEW: .refs/cancer_genes/cosmic_cgc/

OLD: .refs/cancermine/
NEW: .refs/cancer_genes/cancermine/

OLD: .refs/oncovi/tumor_suppressors.txt
NEW: .refs/cancer_genes/oncovi_lists/tumor_suppressors.txt

OLD: .refs/oncovi/oncogenes.txt
NEW: .refs/cancer_genes/oncovi_lists/oncogenes.txt
```

### Hotspots
```
OLD: .refs/cancer_hotspots/
NEW: .refs/hotspots/msk_hotspots/

OLD: .refs/oncovi/single_residue_hotspots.tsv
NEW: .refs/hotspots/oncovi_hotspots/single_residue_hotspots.tsv

OLD: .refs/oncovi/indel_hotspots.tsv
NEW: .refs/hotspots/oncovi_hotspots/indel_hotspots.tsv
```

### VEP Resources
```
OLD: .refs/vep/cache/
NEW: .refs/functional_predictions/vep_cache/

OLD: .refs/vep/plugins/
NEW: .refs/functional_predictions/vep_plugins/

OLD: .refs/vep/plugin_data/
NEW: .refs/functional_predictions/plugin_data/
```

### Expression Data
```
OLD: .refs/tcga/
NEW: .refs/expression_functional/tcga_expression/

OLD: .refs/depmap/
NEW: .refs/expression_functional/depmap_effects/
```

### Clinical Context
```
OLD: .refs/biomarkers/
NEW: .refs/clinical_context/biomarkers/

OLD: .refs/oncotree/
NEW: .refs/clinical_context/oncotree/

OLD: .refs/open_targets/
NEW: .refs/clinical_context/drug_targets/
```

### Structural Variants
```
OLD: .refs/fusion/
NEW: .refs/structural_variants/fusion_databases/

OLD: .refs/chr_alterations/
NEW: .refs/structural_variants/cnv_resources/
```

### Secondary Findings
```
OLD: .refs/secondary_findings/
NEW: .refs/secondary_findings/acmg_sf/
```

### PCGR Bundle
```
OLD: .refs/pcgr/
NEW: .refs/integrated_bundles/pcgr/
```

## Benefits of This Organization

1. **Clear data type grouping** - Easy to find related resources
2. **Usage-based organization** - Resources for each canned text type are grouped
3. **Reduced redundancy** - Clear primary location for each resource
4. **Scalability** - Easy to add new resources in appropriate categories
5. **Performance** - Related files accessed together are co-located
6. **Maintenance** - Clear ownership and versioning per category