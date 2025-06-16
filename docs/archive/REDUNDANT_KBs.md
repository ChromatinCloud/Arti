# Redundant Knowledge Bases Identified

## Redundancy Analysis

### 1. gnomAD Redundancies
**Keep**: `.refs/pcgr/data/grch38/variant/vcf/gnomad_non_cancer/gnomad_non_cancer.vcf.gz`
**Mark for deletion**:
- `.refs/gnomad/` directory (separate download)
- `.refs/vep/plugin_data/gnomad.genomes.r2.1.1.sites.grch38.vcf.bgz` (older version)
**Reason**: PCGR bundle has curated non-cancer subset which is more relevant for somatic filtering

### 2. ClinVar Redundancies
**Keep**: `.refs/pcgr/data/grch38/variant/vcf/clinvar/clinvar.vcf.gz` (with index and annotations)
**Mark for deletion**:
- `.refs/clinvar/` directory
- `.refs/vep/plugin_data/clinvar.vcf.gz`
**Reason**: PCGR version is pre-processed with cancer-relevant annotations

### 3. dbNSFP Redundancies
**Keep**: `.refs/pcgr/data/grch38/variant/vcf/dbnsfp/dbnsfp.vcf.gz`
**Mark for deletion**:
- Any separate dbNSFP downloads in vep/plugin_data
**Reason**: PCGR version is pre-processed and indexed for VEP use

### 4. COSMIC Redundancies
**Keep**: Integrated COSMIC data in PCGR bundle
**Mark for deletion**:
- `.refs/cosmic/` directory if it duplicates PCGR content
**Reason**: PCGR has processed COSMIC data integrated

### 5. Cancer Hotspots Redundancies
**Keep**: `.refs/cancer_hotspots/` (has multiple sources: MSK, CIViC, 3D)
**Integrate with**: PCGR hotspot data
**Reason**: Multiple complementary hotspot sources should be unified

### 6. Gene Symbol Mappings Redundancies
**Keep**: `.refs/pcgr/data/grch38/gene/tsv/gene_transcript_xref/`
**Mark for deletion**:
- `.refs/gene_mappings/` if duplicating HGNC/NCBI data
**Reason**: PCGR has comprehensive gene-transcript mappings

### 7. OncoTree Redundancies  
**Keep**: `.refs/oncotree/` (appears to have multiple versions)
**Reason**: Need to verify which version matches OncoKB requirements

### 8. VEP Cache and Plugin Redundancies
**Keep**: 
- `.refs/vep/cache/` (VEP cache)
- `.refs/vep/plugins/` (plugin files)
- `.refs/vep/plugin_data/` (specific plugin data files)
**Action**: Need to consolidate plugin data with PCGR resources

### 9. Expression Data Redundancies
**Keep**: `.refs/pcgr/data/grch38/expression/tsv/` (comprehensive TCGA + DepMap)
**Mark for deletion**:
- `.refs/tcga/` if it duplicates expression data
- `.refs/depmap/` if it duplicates expression data
**Reason**: PCGR has pre-processed expression matrices

### 10. Drug Data Redundancies
**Keep**: `.refs/pcgr/data/grch38/drug/tsv/`
**Check**: `.refs/drug/` directory for duplication
**Reason**: PCGR has curated drug-target relationships

## Unique Resources to Preserve

### Definitely Keep (Not in PCGR):
1. `.refs/mave/` - MaveDB functional scores
2. `.refs/open_targets/` - Disease associations
3. `.refs/secondary_findings/` - ACMG SF lists
4. `.refs/fusion/` - If contains unique fusion data beyond PCGR
5. `.refs/chr_alterations/` - Chromosomal alteration data
6. `.refs/biomarkers/` - Clinical biomarker thresholds

### Need Investigation:
1. `.refs/civic/` - Check if PCGR civic data is complete
2. `.refs/oncokb/` - Verify against PCGR content
3. `.refs/cgc/` - Check if duplicates COSMIC CGC in PCGR
4. `.refs/clingen/` - Likely unique, keep

## Recommended Action Plan

1. **Immediate redundancies** (safe to mark):
   - Older gnomAD versions
   - Duplicate ClinVar files
   - Raw unprocessed files when processed versions exist

2. **Requires verification**:
   - OncoKB vs PCGR coverage
   - CIViC completeness in PCGR
   - COSMIC data coverage

3. **Definitely preserve**:
   - All VEP infrastructure (cache, plugins)
   - Unique databases not in PCGR
   - Clinical interpretation resources