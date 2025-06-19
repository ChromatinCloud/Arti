# DGG OncoSeq Panel Analysis Summary

## Overview
The DGG OncoSeq assay is version 7 (`oncoseq-v7`) that uses GOAL probe technology. After analyzing the data files, I found that the panel information is distributed across multiple files that need to be combined.

## Key Files Analyzed

### 1. **DGG_Onco_Seq_Probe_Info.tsv** (Primary Source)
- Contains 1,133 unique probe pools (genes/regions)
- Maps probe pools to subpools and stock plates
- This is the authoritative list of what's included in OncoSeq

### 2. **target_goal_all_mapped_v0_250304.bed** (Genomic Coordinates)
- Contains 27,561 total target regions from the entire GOAL panel
- **2,351 regions match OncoSeq probe pools**
- Covers 207 unique genes/pools (out of 1,133 in probe info)
- Total coverage: 893,992 bases

### 3. **probe_goal_all_v0_250304.tsv** (Detailed Probe Info)
- 70,493 total probes in GOAL
- 9,757 probes match OncoSeq pools
- Contains both hg19 and hg38 coordinates

## Panel Composition

### Top Genes by Probe Count:
1. RSPO3_Fusion (509 probes)
2. ETV6_Fusion (486 probes)
3. FGFR2_Fusion (417 probes)
4. PAX8_Fusion (367 probes)
5. ROS1_Fusion (312 probes)
6. RxPGX_loci (262 probes) - Pharmacogenomics
7. BRAF_Fusion (215 probes)
8. NTRK2_Fusion (215 probes)

### Coverage:
- **Chromosomes**: All autosomes (1-22), X, Y, and mitochondrial
- **Total Regions**: 2,351
- **Total Bases**: 893,992
- **Unique Genes/Targets**: 207 with coordinates (out of 1,133 total)

## Data Integration Strategy

The target BED file (`target_goal_all_mapped_v0_250304.bed`) serves as the **single source of truth** for genomic coordinates, filtered for OncoSeq-specific probe pools. However, it only contains 207 of the 1,133 probe pools listed in the probe info file.

### Missing Targets
Many probe pools in `DGG_Onco_Seq_Probe_Info.tsv` don't have corresponding regions in the target BED file, including:
- Viral sequences (HPV_Viral)
- Some fusion detection probes
- UTR regions
- SNP panels

These may require special handling or separate coordinate files.

## Panel File Created

**File**: `resources/assay/default_assay/panel.oncoseq.bed.gz`
- BED format with 2,351 regions
- Contains: chr, start, end, gene_name, score, strand
- Filtered specifically for OncoSeq probe pools
- Ready for use in technical filtering

## Blacklist Regions

No explicit blacklist files were found in the OncoSeq data. The mdl-run4 folder contains QC metrics and plots but no specific problematic region lists. Blacklist regions would need to be determined from:
1. Analysis of coverage uniformity across samples
2. Regions with systematic artifacts in the run data
3. External validation against known problematic regions

## Recommendations

1. **Panel Coverage**: The current panel BED file covers the main targeted regions but may be missing some specialized probes (viral, SNPs).

2. **Blacklist Development**: Consider analyzing the QC data in mdl-run4 to identify:
   - Regions with consistently low coverage
   - High duplicate rates
   - AT dropout regions
   - Off-target hotspots

3. **Version Control**: This is OncoSeq v7 - ensure compatibility with analysis pipelines.

4. **Additional Files**: Some fusion and viral probes may need separate handling as they don't map to standard genomic coordinates.