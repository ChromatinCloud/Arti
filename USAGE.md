# Annotation Engine - Usage Guide

## Quick Start

### Installation
```bash
# Install dependencies
poetry install

# Quick test (0.20 seconds)
poetry run annotation-engine --test
```

### Basic Usage
```bash
# Annotate a VCF file
poetry run annotation-engine --input your_variants.vcf --case-uid CASE001 --cancer-type melanoma

# Validation only (dry run)
poetry run annotation-engine --input your_variants.vcf --case-uid CASE001 --cancer-type melanoma --dry-run
```

## CLI Reference

### Core Command
```bash
poetry run annotation-engine [OPTIONS]
```

### Required Arguments (for normal operation)
- `--input PATH` or `--tumor-vcf PATH`: Input VCF file
- `--case-uid TEXT`: Unique case identifier
- `--cancer-type CHOICE`: Cancer type from supported list

### Supported Cancer Types
- `lung_adenocarcinoma`
- `lung_squamous` 
- `breast_cancer`
- `colorectal_cancer`
- `melanoma`
- `ovarian_cancer`
- `pancreatic_cancer`
- `prostate_cancer`
- `glioblastoma`
- `acute_myeloid_leukemia`
- `other`

## Command Examples

### 1. Quick Test Mode
```bash
# Run built-in test with example data
poetry run annotation-engine --test

# Expected output: 4 variants processed in ~0.20 seconds
# Results saved to: results/test_mode/
```

### 2. Single Sample Analysis
```bash
# Basic tumor-only analysis
poetry run annotation-engine \
    --input tumor.vcf \
    --case-uid CASE_001 \
    --cancer-type melanoma \
    --output results/case001

# With custom quality filters
poetry run annotation-engine \
    --input tumor.vcf \
    --case-uid CASE_001 \
    --cancer-type melanoma \
    --min-depth 20 \
    --min-vaf 0.1 \
    --output results/case001_filtered
```

### 3. Tumor-Normal Analysis
```bash
# Paired tumor-normal analysis
poetry run annotation-engine \
    --tumor-vcf tumor.vcf \
    --normal-vcf normal.vcf \
    --case-uid CASE_001 \
    --cancer-type lung_adenocarcinoma \
    --output results/paired_analysis
```

### 4. Advanced Options
```bash
# With all clinical metadata
poetry run annotation-engine \
    --input tumor.vcf \
    --case-uid CASE_001 \
    --patient-uid PATIENT_001 \
    --cancer-type breast_cancer \
    --oncotree-id BRCA \
    --tissue-type primary_tumor \
    --tumor-purity 0.75 \
    --output results/comprehensive \
    --verbose

# Skip quality control filters
poetry run annotation-engine \
    --input tumor.vcf \
    --case-uid CASE_001 \
    --cancer-type melanoma \
    --skip-qc \
    --output results/no_filters
```

### 5. Validation and Testing
```bash
# Dry run - validation only
poetry run annotation-engine \
    --input tumor.vcf \
    --case-uid CASE_001 \
    --cancer-type melanoma \
    --dry-run

# Verbose output for debugging
poetry run annotation-engine \
    --input tumor.vcf \
    --case-uid CASE_001 \
    --cancer-type melanoma \
    --verbose \
    --output results/debug
```

## Output Files

Each analysis generates multiple output files:

### 1. `annotation_results.json`
Comprehensive results with metadata:
```json
{
  "metadata": {
    "version": "1.0.0",
    "analysis_type": "TUMOR_ONLY",
    "genome_build": "GRCh38",
    "case_uid": "CASE_001",
    "cancer_type": "melanoma",
    "total_variants": 4
  },
  "variants": [...],
  "summary": {
    "variants_by_tier": {"Tier IV": 4},
    "variants_by_gene": {"BRAF": 1, "TP53": 1}
  }
}
```

### 2. `variants_only.json`
Simple variant list for downstream processing:
```json
[
  {
    "variant_id": "7_140753336_T_A",
    "genomic_location": {...},
    "gene_annotation": {...},
    "clinical_classification": {...}
  }
]
```

### 3. `summary_report.txt`
Human-readable summary:
```
ANNOTATION ENGINE - SUMMARY REPORT
==================================================

Case ID: CASE_001
Cancer Type: melanoma
Total Variants: 4

Tier Distribution:
  Tier IV: 4

Gene Distribution:
  BRAF: 1
  TP53: 1
  KRAS: 1
  PIK3CA: 1

DETAILED VARIANT LIST
--------------------

1. BRAF p.Val600Glu
   Location: 7:140753336
   AMP Tier: Tier IV
   VICC: Likely Oncogenic
   VAF: 0.511
   Confidence: 0.34
```

### 4. `analysis_request.json` (verbose mode)
Complete analysis parameters for debugging

## Input File Requirements

### VCF Format
- **Supported formats**: `.vcf`, `.vcf.gz`
- **Required fields**: CHROM, POS, REF, ALT
- **Recommended fields**: INFO/DP, INFO/AF, FORMAT/GT, FORMAT/AD, FORMAT/VAF
- **Genome build**: GRCh38 (recommended)

### Example VCF Header
```
##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=VAF,Number=A,Type=Float,Description="Variant Allele Frequency">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
7	140753336	.	T	A	95	PASS	DP=45;AF=0.52	GT:AD:VAF	0/1:22,23:0.51
```

## Quality Control

### Default Filters
- **Minimum depth**: 10 reads
- **Minimum VAF**: 0.05 (5%)

### Custom Filters
```bash
# Strict quality filters
--min-depth 30 --min-vaf 0.15

# Skip all quality filters
--skip-qc
```

## Supported Guidelines

### Clinical Guidelines
- **AMP/ASCO/CAP 2017**: Tier I-IV therapeutic actionability
- **VICC/CGC 2022**: Oncogenicity classification
- **OncoKB**: Therapeutic evidence levels

### Evidence Sources
- OncoKB gene lists and therapeutic levels
- CIViC variant summaries and evidence
- COSMIC Cancer Gene Census
- MSK Cancer Hotspots
- OncoVI Oncogenes database

## Performance

### Processing Times
- **4 variants**: ~0.20 seconds
- **Small VCF (< 100 variants)**: < 1 second
- **Typical clinical panel**: 1-5 seconds

### Memory Usage
- **Base memory**: ~200MB for knowledge base loading
- **Per variant**: Minimal additional memory

## Troubleshooting

### Common Issues

1. **Missing VCF file**
   ```
   Error: VCF file not found: /path/to/file.vcf
   ```
   Solution: Check file path and permissions

2. **Invalid cancer type**
   ```
   Error: Invalid choice: 'lung' (choose from 'lung_adenocarcinoma', 'lung_squamous', ...)
   ```
   Solution: Use exact cancer type from supported list

3. **Low quality variants filtered out**
   ```
   Warning: Skipping variant 7:140753336: depth 8 < 10
   ```
   Solution: Adjust `--min-depth` or use `--skip-qc`

### Debug Mode
```bash
# Enable verbose output
poetry run annotation-engine --input data.vcf --case-uid CASE001 --cancer-type melanoma --verbose

# Check log files (if --log-file specified)
tail -f annotation.log
```

## Advanced Usage

### Environment Setup
```bash
# Setup with all dependencies
./setup_env.sh

# Setup knowledge bases
./scripts/setup_comprehensive_kb.sh --essential
```

### Development Commands
```bash
# Run tests
poetry run pytest -q

# Code linting
poetry run ruff --select I --target-version py310

# Type checking (if available)
poetry run mypy src/
```

### Integration with Workflows
```bash
# Nextflow integration (future)
nextflow run annotation-pipeline.nf --vcf input.vcf --cancer-type melanoma

# Batch processing (future)
poetry run annotation-engine --batch-mode --input-dir vcf_files/ --output-dir results/
```

## Getting Help

### CLI Help
```bash
# Show all options
poetry run annotation-engine --help

# Show version
poetry run annotation-engine --version
```

### Example Data
Test with provided example files:
```bash
# Example VCF files are in example_input/
ls example_input/
# proper_test.vcf, tumor_only_test.vcf, synthetic_test.vcf

# Test with example
poetry run annotation-engine --input example_input/proper_test.vcf --case-uid EXAMPLE --cancer-type melanoma
```

### Support
- Documentation: `/docs/` directory
- Issues: Report problems with specific command and error message
- Examples: See `tests/` directory for usage patterns

---

## Quick Reference Card

```bash
# Essential commands
poetry run annotation-engine --test                                    # Quick test
poetry run annotation-engine --input file.vcf --case-uid ID --cancer-type TYPE  # Basic usage
poetry run annotation-engine --help                                    # Full help

# Output locations
results/                     # Default output directory
  ├── annotation_results.json   # Complete results
  ├── variants_only.json        # Simple variant list  
  ├── summary_report.txt         # Human readable
  └── analysis_request.json     # Parameters (verbose mode)
```