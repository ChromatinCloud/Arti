# Knowledge Base and VEP Plugin Registry

**Last Updated**: 2025-06-17  
**Purpose**: Central registry for all knowledge bases and VEP plugins used in the annotation engine, including file paths, usage patterns, and implementation strategies.

## Executive Summary

This document serves as the authoritative registry for:
1. **Knowledge Base Locations** - Where each KB file is stored in the `.refs/` directory
2. **VEP Plugin Mappings** - Which KBs are used as VEP plugins vs direct access
3. **Implementation Strategy** - Hybrid approach using VEP plugins for functional predictions and direct KB access for clinical evidence
4. **File Path Mappings** - Current organizational structure under `.refs/`

## Implementation Strategy: Hybrid Approach

### VEP Plugins (Functional Predictions)
Use VEP plugins for complex functional predictions requiring:
- Tabix indexing for large files
- Complex consequence-dependent logic
- Standardized output format
- Efficient batch processing

### Direct KB Access (Clinical Evidence)
Use direct access for clinical evidence requiring:
- Custom scoring algorithms (AMP/VICC)
- Flexible evidence weighting
- Institution-specific filtering
- Complex aggregation logic

## Knowledge Base Registry

### Clinical Evidence Databases (Direct Access)

| Knowledge Base | Path | Size | Usage | Status |
|----------------|------|------|-------|---------|
| **ClinVar** | `.refs/clinical_evidence/clinvar/` | 350MB | Clinical significance, pathogenicity | ✅ Available |
| **CIViC** | `.refs/clinical_evidence/civic/` | 15MB | Therapeutic evidence, clinical trials | ✅ Available |
| **OncoKB** | `.refs/clinical_evidence/oncokb/` | 1MB | Actionability levels, treatment options | ✅ Available |
| **ClinGen** | `.refs/clinical_evidence/clingen/` | 10MB | Dosage sensitivity, gene curation | ✅ Available |

### Population Frequencies (Mixed Access)

| Knowledge Base | Path | Size | Usage | Access Method |
|----------------|------|------|-------|---------------|
| **gnomAD** | `.refs/population_frequencies/gnomad/` | 20-150GB | AF filtering | Direct + VEP Plugin |
| **dbSNP** | `.refs/population_frequencies/dbsnp/` | 5GB | Common variants | Direct Access |
| **ExAC** | `.refs/population_frequencies/exac/` | 10GB | Legacy AF data | Direct Access |

### Cancer-Specific Resources (Direct Access)

| Knowledge Base | Path | Size | Usage | Status |
|----------------|------|------|-------|---------|
| **Cancer Hotspots** | `.refs/cancer_signatures/hotspots/` | 5MB | Recurrence evidence | ✅ Available |
| **COSMIC CGC** | `.refs/cancer_signatures/cosmic/` | 50MB | Cancer gene census | ✅ Available |
| **TCGA** | `.refs/cancer_signatures/tcga/` | 1GB | Somatic mutations | ⚠️ Partial |
| **DepMap** | `.refs/cancer_signatures/depmap/` | 500MB | Cell line dependencies | ⚠️ Partial |

### Functional Predictions (VEP Plugins)

#### High-Priority Plugins

| Plugin | Data File | Path | Size | Status |
|--------|-----------|------|------|---------|
| **dbNSFP** | `dbnsfp.vcf.gz` | `.refs/variant/vcf/dbnsfp/` | 1.7GB | ✅ Available (VCF format) |
| **AlphaMissense** | `AlphaMissense_hg38.tsv.gz` | `.refs/functional_predictions/plugin_data/protein_impact/` | 1.1GB | ✅ Available |
| **REVEL** | `revel_all_chromosomes.tsv.gz` | `.refs/functional_predictions/plugin_data/pathogenicity/` | ~1GB | ⚠️ Partial |
| **SpliceAI** | `spliceai_scores.masked.snv.hg38.vcf.gz` | `.refs/functional_predictions/plugin_data/splicing/` | Large | ⚠️ Partial |
| **PrimateAI** | `PrimateAI_scores_v0.2.tsv.gz` | `.refs/functional_predictions/plugin_data/protein_impact/` | 868MB | ✅ Available |

#### Additional Plugins

| Plugin | Data File | Path | Purpose | Status |
|--------|-----------|------|---------|---------|
| **Conservation** | `conservation_scores.wig.gz` | `.refs/functional_predictions/plugin_data/conservation/` | GERP/PhyloP scores | ⚠️ Needs update |
| **LoFtool** | `LoFtool_scores.txt` | `.refs/functional_predictions/plugin_data/gene_constraint/` | Gene constraint | ✅ Available |
| **BayesDel** | `BayesDel_addAF_V1.2.tsv.gz` | `.refs/functional_predictions/plugin_data/pathogenicity/` | Deleteriousness | ⚠️ Partial |
| **ClinPred** | `clinpred_scores.tsv.gz` | `.refs/functional_predictions/plugin_data/pathogenicity/` | Clinical prediction | ⚠️ Partial |
| **FATHMM** | `fathmm_scores.tsv.gz` | `.refs/functional_predictions/plugin_data/pathogenicity/` | Functional impact | ❌ Missing |
| **EVE** | `eve_merged.vcf.gz` | `.refs/functional_predictions/plugin_data/protein_impact/` | Evolutionary model | ⚠️ Partial |
| **VARITY** | `VARITY_R_LOO_v1.0.tsv.gz` | `.refs/functional_predictions/plugin_data/protein_impact/` | Variant effect | ⚠️ Partial |
| **dbscSNV** | `dbscSNV1.1_GRCh38.txt.gz` | `.refs/functional_predictions/plugin_data/splicing/` | Splice consensus | ✅ Available |
| **MaveDB** | `mavedb_scores.tsv.gz` | `.refs/functional_predictions/plugin_data/mavedb/` | Experimental scores | ⚠️ Partial |
| **UTRAnnotator** | `utr_annotations.gff.gz` | `.refs/functional_predictions/plugin_data/utr/` | UTR effects | ⚠️ Partial |
| **Enformer** | `enformer_predictions.tsv.gz` | `.refs/functional_predictions/plugin_data/regulatory/` | Regulatory impact | ⚠️ Partial |
| **NMD** | `nmd_predictions.tsv.gz` | `.refs/functional_predictions/plugin_data/splicing/` | Nonsense-mediated decay | ⚠️ Partial |

### Gene Annotations (Direct Access)

| Resource | Path | Purpose | Status |
|----------|------|---------|---------|
| **HGNC** | `.refs/reference_assemblies/gencode/` | Gene symbols, aliases | ✅ Available |
| **UniProt** | `.refs/reference_assemblies/ensembl/` | Protein annotations | ✅ Available |
| **RefSeq** | `.refs/reference_assemblies/refseq/` | Transcript mappings | ✅ Available |

### Structural Variants (Direct Access)

| Resource | Path | Purpose | Status |
|----------|------|---------|---------|
| **SV Annotations** | `.refs/structural_variants/sv_annotations/` | CNV/fusion interpretation | ⚠️ Partial |

## VEP Configuration

### Recommended Plugin Configuration

```bash
vep \
  --format vcf \
  --json \
  --cache \
  --dir_cache .refs/functional_predictions/vep_cache \
  --dir_plugins .refs/functional_predictions/vep_plugins \
  --plugin dbNSFP,.refs/functional_predictions/plugin_data/pathogenicity/dbNSFP5.1.gz,SIFT_score,Polyphen2_HDIV_score,CADD_phred,REVEL_score,MetaSVM_score \
  --plugin AlphaMissense,.refs/functional_predictions/plugin_data/protein_impact/AlphaMissense_hg38.tsv.gz \
  --plugin SpliceAI,.refs/functional_predictions/plugin_data/splicing/spliceai_scores.masked.snv.hg38.vcf.gz \
  --plugin Conservation,.refs/functional_predictions/plugin_data/conservation/conservation_scores.wig.gz \
  --plugin REVEL,.refs/functional_predictions/plugin_data/pathogenicity/revel_all_chromosomes.tsv.gz \
  --plugin PrimateAI,.refs/functional_predictions/plugin_data/protein_impact/PrimateAI_scores_v0.2.tsv.gz \
  --fasta .refs/reference_assemblies/Homo_sapiens.GRCh38.dna.primary_assembly.fa
```

## Path Mapping Reference

### Backward Compatibility Symlinks

The following symlinks are maintained for backward compatibility:

```bash
.refs/vep_cache → .refs/functional_predictions/vep_cache
.refs/vep_plugins → .refs/functional_predictions/vep_plugins
.refs/clinvar → .refs/clinical_evidence/clinvar
.refs/gnomad → .refs/population_frequencies/gnomad
.refs/cancer_hotspots → .refs/cancer_signatures/hotspots
```

### Directory Structure

```
.refs/
├── clinical_evidence/           # Clinical significance databases
│   ├── clinvar/
│   ├── civic/
│   ├── oncokb/
│   ├── clingen/
│   └── biomarkers/
├── population_frequencies/      # Population allele frequencies
│   ├── gnomad/
│   ├── dbsnp/
│   └── exac/
├── functional_predictions/      # VEP and prediction tools
│   ├── vep_cache/              # VEP offline cache
│   ├── vep_plugins/            # Plugin source code
│   └── plugin_data/            # Plugin data files:
│       ├── pathogenicity/      # dbNSFP, REVEL, BayesDel, etc.
│       ├── protein_impact/     # AlphaMissense, PrimateAI, EVE
│       ├── splicing/           # SpliceAI, dbscSNV, NMD
│       ├── conservation/       # GERP, PhyloP scores
│       ├── gene_constraint/    # LoFtool scores
│       ├── regulatory/         # Enformer predictions
│       ├── utr/               # UTR annotations
│       ├── clinvar/           # ClinVar plugin data
│       └── mavedb/            # Experimental scores
├── cancer_signatures/          # Cancer-specific databases
│   ├── hotspots/              # MSK, CIViC, 3D, OncoVI hotspots
│   ├── cosmic/                # COSMIC CGC
│   ├── tcga/                  # TCGA mutations
│   └── depmap/                # Cell line data
├── structural_variants/        # SV annotations
├── reference_assemblies/       # Reference genome data
├── vep_setup/                 # VEP installation files
├── pharmacogenomics/          # Drug-gene interactions
└── sample_data/               # Test files
```

## Missing Critical Files

### High Priority Downloads Needed

1. **gnomAD VCF**: `gnomad.genomes.v3.1.2.sites.vcf.bgz` (~150GB)
   - Required for population frequency filtering
   - Download from: https://gnomad.broadinstitute.org/downloads

2. **dbNSFP**: `dbNSFP5.1.gz` (~15GB)
   - Comprehensive functional prediction scores
   - Download from: https://sites.google.com/site/jpopgen/dbNSFP

3. **FATHMM**: Plugin data files
   - Functional impact predictions
   - Download from VEP plugin repository

## Implementation Checklist

### Phase 1: Complete KB Downloads
- [ ] Download missing gnomAD data
- [ ] Download dbNSFP v5.1
- [ ] Complete REVEL scores
- [ ] Download FATHMM data
- [ ] Verify all plugin data files

### Phase 2: VEP Integration
- [ ] Configure VEP with selected plugins
- [ ] Test plugin functionality
- [ ] Validate output format
- [ ] Performance optimization

### Phase 3: Direct KB Access
- [ ] Implement ClinVar query logic
- [ ] Implement CIViC aggregation
- [ ] Implement OncoKB integration
- [ ] Implement hotspot checking

### Phase 4: Evidence Aggregation
- [ ] Parse VEP JSON for functional scores
- [ ] Query clinical KBs directly
- [ ] Combine evidence types
- [ ] Apply AMP/VICC scoring

## Maintenance Notes

### Version Tracking
- Each KB should have version info in its directory
- Update this registry when KBs are updated
- Maintain compatibility matrix for plugin versions

### Storage Optimization
- Consider filtering gnomAD to rare variants (AF < 1%) for somatic analysis
- ClinVar can be filtered to pathogenic/likely pathogenic only
- Keep full files for VEP plugins (required for indexing)

### Performance Considerations
- VEP plugin phase: 30-60 minutes for whole genome
- Evidence aggregation: 5-10 minutes
- Tier assignment: 1-2 minutes
- Total disk space required: ~200GB (full setup)

---

*This registry should be updated whenever knowledge bases are added, moved, or updated. It serves as the single source of truth for KB locations and usage patterns in the annotation engine.*