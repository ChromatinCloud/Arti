# Resources Directory Contents

This directory contains reference data files and assay-specific configuration files used by the Annotation Engine technical filtering module. These files are excluded from git tracking due to their size, but this document describes their expected contents.

## Directory Structure

```
resources/
├── reference/              # Reference genome data
│   └── genome/            # Genome-specific files
│       ├── grch38/        # GRCh38/hg38 reference files
│       │   ├── blacklist.grch38.bed.gz     # ENCODE/Amemiya blacklist regions for GRCh38
│       │   └── gnomad.freq.vcf.gz          # gnomAD population frequencies (compact)
│       └── grch37/        # GRCh37/hg19 reference files
│           ├── blacklist.grch37.bed.gz     # ENCODE/Amemiya blacklist regions for GRCh37
│           └── gnomad.freq.vcf.gz          # gnomAD population frequencies (compact)
└── assay/                 # Assay-specific files
    └── default_assay/     # Default clinical sequencing panel
        ├── panel.bed                       # Target regions for the assay
        ├── blacklist.assay.bed            # Assay-specific problematic regions
        └── config.yaml                    # Assay configuration and thresholds
```

## File Descriptions

### Reference Files (Genome-level)

#### blacklist.grch38.bed.gz / blacklist.grch37.bed.gz
- **Source**: ENCODE Project blacklist v2 (Amemiya et al.)
- **Description**: Genomic regions with anomalous, unstructured, or high signal in NGS experiments
- **Format**: BED format (chr, start, end)
- **Size**: ~5-10 KB compressed
- **Usage**: Remove variants in problematic genomic regions

#### gnomad.freq.vcf.gz
- **Source**: gnomAD v4.1 (or latest)
- **Description**: Compact VCF with population allele frequencies only
- **Format**: VCF with INFO fields for AF, AF_popmax, AC, AN
- **Size**: Target <1GB (not the full 450GB gnomAD release)
- **Usage**: Filter common variants based on population frequency

### Assay Files (Panel-specific)

#### panel.bed
- **Source**: Assay manufacturer or institutional design
- **Description**: Genomic regions targeted by the sequencing panel
- **Format**: BED format (chr, start, end, gene_name)
- **Size**: Typically <1 MB
- **Usage**: Restrict analysis to on-target regions

#### blacklist.assay.bed
- **Source**: Internal validation and QC
- **Description**: Panel-specific regions with poor coverage or systematic artifacts
- **Format**: BED format (chr, start, end, reason)
- **Size**: Typically <100 KB
- **Usage**: Remove variants in assay-specific problematic regions

#### config.yaml
- **Source**: Clinical laboratory settings
- **Description**: Assay-specific filter thresholds and parameters
- **Format**: YAML configuration file
- **Size**: <10 KB
- **Usage**: Define assay-specific filtering parameters

## Adding Files

To set up the resources directory:

1. **Genome reference files** (one-time setup):
   ```bash
   # Already placed:
   - resources/reference/genome/grch38/blacklist.grch38.bed.gz
   - resources/reference/genome/grch37/blacklist.grch37.bed.gz
   
   # Still needed:
   - Compact gnomAD frequency files for each genome build
   ```

2. **Assay files** (per assay):
   ```bash
   # Place your files in:
   resources/assay/default_assay/
   
   # Required files:
   - panel.bed (your assay's target regions)
   - blacklist.assay.bed (your assay's problematic regions)
   ```

## Git Configuration

The `.gitignore` is configured to:
- Track this CONTENTS.md file
- Track the directory structure
- Exclude all data files (*.bed, *.bed.gz, *.vcf, *.vcf.gz, *.bcf)
- Track configuration files (*.yaml, *.json)

This ensures the repository maintains the expected structure without storing large data files.