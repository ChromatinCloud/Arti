# VEP Plugin Configuration and Implementation

**Last Updated**: 2025-06-17  
**Purpose**: Document the actual VEP plugin configuration and implementation status for the annotation engine.

## Plugin Implementation Strategy

### Hybrid Approach
- **VEP Plugins**: Used for functional predictions requiring complex consequence logic
- **Direct KB Access**: Used for clinical evidence requiring custom scoring algorithms

## Configured VEP Plugins

### 1. dbNSFP
**Status**: ✅ Available (VCF format)  
**Path**: `.refs/variant/vcf/dbnsfp/dbnsfp.vcf.gz`  
**Configuration**:
```bash
--plugin dbNSFP,.refs/variant/vcf/dbnsfp/dbnsfp.vcf.gz,SIFT_score,Polyphen2_HDIV_score,CADD_phred,REVEL_score,MetaSVM_score,MutationTaster_score
```
**Purpose**: Comprehensive functional prediction scores from multiple algorithms

### 2. AlphaMissense
**Status**: ✅ Available  
**Path**: `.refs/functional_predictions/plugin_data/protein_impact/AlphaMissense_hg38.tsv.gz`  
**Configuration**:
```bash
--plugin AlphaMissense,.refs/functional_predictions/plugin_data/protein_impact/AlphaMissense_hg38.tsv.gz
```
**Purpose**: DeepMind's missense pathogenicity predictions

### 3. Conservation
**Status**: ⚠️ Needs configuration  
**Path**: `.refs/misc/bed/gerp/gerp.bed.gz`  
**Configuration**:
```bash
--plugin Conservation,.refs/misc/bed/gerp/gerp.bed.gz
```
**Purpose**: GERP conservation scores

### 4. SpliceAI
**Status**: ✅ Available (large files)  
**Paths**: 
- `.refs/spliceai/spliceai_scores.raw.snv.ensembl_mane.grch38.110.vcf.gz` (27GB)
- `.refs/spliceai/spliceai_scores.raw.indel.hg38.vcf.gz` (65GB)
**Configuration**:
```bash
--plugin SpliceAI,snv=.refs/spliceai/spliceai_scores.raw.snv.ensembl_mane.grch38.110.vcf.gz,indel=.refs/spliceai/spliceai_scores.raw.indel.hg38.vcf.gz
```
**Purpose**: Deep learning splice impact predictions

### 5. LoFtool
**Status**: ✅ Available  
**Path**: `.refs/functional_predictions/plugin_data/gene_constraint/LoFtool_scores.txt`  
**Configuration**:
```bash
--plugin LoFtool,.refs/functional_predictions/plugin_data/gene_constraint/LoFtool_scores.txt
```
**Purpose**: Gene-level loss-of-function intolerance scores

### 6. dbscSNV
**Status**: ⚠️ File not found at expected location  
**Expected Path**: `.refs/functional_predictions/plugin_data/splicing/dbscSNV1.1_GRCh38.txt.gz`  
**Purpose**: Splice consensus predictions

### 7. PrimateAI
**Status**: ⚠️ File not found at expected location  
**Expected Path**: `.refs/functional_predictions/plugin_data/protein_impact/PrimateAI_scores_v0.2.tsv.gz`  
**Purpose**: Deep learning pathogenicity scores trained on primate variation

### 8. REVEL
**Status**: ⚠️ File not found at expected location  
**Expected Path**: `.refs/functional_predictions/plugin_data/pathogenicity/revel_all_chromosomes.tsv.gz`  
**Purpose**: Ensemble missense pathogenicity meta-predictor

### 9. EVE
**Status**: ⚠️ Partial (individual protein files present)  
**Path**: `.refs/functional_predictions/plugin_data/protein_impact/eve_files/`  
**Note**: Contains individual VCF files per protein, needs merging
**Purpose**: Evolutionary model of variant effect

### 10. MaveDB
**Status**: ✅ Available  
**Path**: `.refs/functional_predictions/plugin_data/mavedb/MaveDB_variants.tsv.gz`  
**Configuration**:
```bash
--plugin MaveDB,.refs/functional_predictions/plugin_data/mavedb/MaveDB_variants.tsv.gz
```
**Purpose**: Deep mutational scanning experimental scores

## Complete VEP Command

```bash
vep \
  --format vcf \
  --json \
  --cache \
  --dir_cache .refs/functional_predictions/vep_cache \
  --dir_plugins .refs/functional_predictions/vep_plugins \
  --plugin dbNSFP,.refs/variant/vcf/dbnsfp/dbnsfp.vcf.gz,SIFT_score,Polyphen2_HDIV_score,CADD_phred,REVEL_score \
  --plugin AlphaMissense,.refs/functional_predictions/plugin_data/protein_impact/AlphaMissense_hg38.tsv.gz \
  --plugin SpliceAI,snv=.refs/spliceai/spliceai_scores.raw.snv.ensembl_mane.grch38.110.vcf.gz,indel=.refs/spliceai/spliceai_scores.raw.indel.hg38.vcf.gz \
  --plugin Conservation,.refs/misc/bed/gerp/gerp.bed.gz \
  --plugin LoFtool,.refs/functional_predictions/plugin_data/gene_constraint/LoFtool_scores.txt \
  --plugin MaveDB,.refs/functional_predictions/plugin_data/mavedb/MaveDB_variants.tsv.gz \
  --fasta .refs/misc/fasta/assembly/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz \
  --assembly GRCh38 \
  --use_given_ref \
  --force_overwrite \
  --offline
```

## Plugin Fallback Mechanisms

For plugins with missing data files, the system implements fallbacks:

1. **Primary**: Use VEP plugin if data file exists
2. **Secondary**: Query PCGR-processed VCF files if available
3. **Tertiary**: Skip annotation for that specific score

See `src/annotation_engine/plugin_fallbacks.py` for implementation details.

## Direct Access Knowledge Bases

The following are accessed directly, not through VEP plugins:

### Clinical Evidence
- **ClinVar**: `.refs/clinical_evidence/clinvar/`
- **CIViC**: `.refs/clinical_evidence/civic/`
- **OncoKB**: `.refs/clinical_evidence/oncokb/`
- **Cancer Hotspots**: `.refs/cancer_signatures/hotspots/`

### Population Frequencies
- **gnomAD**: `.refs/population_frequencies/gnomad/`
- **dbSNP**: `.refs/population_frequencies/dbsnp/`

## Missing Critical Plugin Data

The following plugin data files need to be downloaded:

1. **PrimateAI**: Download from [Illumina BaseSpace](https://basespace.illumina.com/s/yYGFdGih1rXL)
2. **REVEL**: Download from [REVEL website](https://sites.google.com/site/revelgenomics/downloads)
3. **dbscSNV**: Download from [dbscSNV website](http://www.liulab.science/dbscsnv.html)
4. **BayesDel**: Download from VEP plugin repository

## Performance Considerations

- **SpliceAI**: Very large files (92GB total), consider filtering to exonic regions
- **dbNSFP**: Currently using VCF format (1.7GB), full version is ~15GB
- **EVE**: Individual protein files need merging for efficient access

## Testing Status

- ✅ Basic VEP execution working
- ✅ Fallback to direct VCF parsing implemented
- ⚠️ Full plugin integration pending missing data files
- ⚠️ Performance optimization needed for large files

---

*This document reflects the actual implementation status as of 2025-06-17. Update as plugin data is downloaded and configurations are tested.*