# Complete Guide: Extracting ALL gnomAD v4 Variant AFs

## Overview

You want the AF of EVERY variant in gnomAD v4. This guide provides multiple approaches ranked by efficiency.

**gnomAD v4.1 Stats:**
- **807,162 individuals** (730,947 exomes + 76,215 genomes)
- **~786 million SNVs** passing QC
- **~122 million InDels** passing QC
- **Total: ~900 million variants**

## Method Comparison

| Method | Speed | Storage | Setup | Best For |
|--------|-------|---------|-------|----------|
| Stream (bcftools) | Medium | None | Simple | Real-time processing |
| BigQuery | Fastest | None | gcloud auth | v2.1.1 only (for now) |
| Download + Extract | Slow | ~150GB | wget | Offline analysis |
| Pre-built Tables | - | - | - | Not available yet |

## Method 1: Stream Without Downloading (Recommended)

**Script:** `stream_gnomad_v4_afs.py`

### Basic Usage
```bash
# Stream all genome AFs (takes ~2-4 hours)
poetry run python scripts/stream_gnomad_v4_afs.py \
  --dataset genomes \
  --output gnomad_v4_genome_afs.tsv

# Stream all exome AFs  
poetry run python scripts/stream_gnomad_v4_afs.py \
  --dataset exomes \
  --output gnomad_v4_exome_afs.tsv
```

### Parallel Streaming (Faster)
```bash
# Use 8 threads to stream in parallel
poetry run python scripts/stream_gnomad_v4_afs.py \
  --dataset genomes \
  --output gnomad_v4_genome_afs.tsv \
  --threads 8
```

### Get Only Common Variants
```bash
# Only variants with AF >= 0.1% (reduces size by ~95%)
poetry run python scripts/stream_gnomad_v4_afs.py \
  --dataset genomes \
  --output gnomad_common_variants.tsv \
  --min-af 0.001 \
  --threads 4
```

### Output Formats

**Minimal** (smallest file):
```
CHROM  POS      REF  ALT  AF        AF_grpmax
1      69511    A    G    0.00234   0.00456
```

**Populations** (recommended):
```
CHROM  POS    REF  ALT  AF      AF_afr   AF_ami  AF_amr  AF_asj  AF_eas  AF_fin  AF_mid  AF_nfe  AF_sas  AF_remaining
1      69511  A    G    0.0023  0.0045   0       0.0012  0.0008  0.0001  0.0034  0.0015  0.0019  0.0011  0.0022
```

**Comprehensive** (all fields):
```
# Includes AN (allele number), AC (allele count), popmax population
```

## Method 2: BigQuery Export (Currently v2.1.1 only)

**Script:** `gnomad_v4_bigquery_export.py`

### Setup
```bash
# Install and authenticate
pip install google-cloud-bigquery
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Export All v2.1.1 AFs
```bash
# Export to Google Cloud Storage
poetry run python scripts/gnomad_v4_bigquery_export.py \
  --export \
  --bucket gs://my-bucket/gnomad_export \
  --project my-project-id

# Download locally
poetry run python scripts/gnomad_v4_bigquery_export.py \
  --download \
  --bucket gs://my-bucket/gnomad_export \
  --output ./gnomad_data
```

## Method 3: Download Everything

**Script:** `download_all_gnomad_v4.py`

⚠️ **Warning:** Requires ~150GB for compressed files, ~750GB uncompressed!

### Download + Extract Pipeline
```bash
# Download genomes + extract AFs + combine
poetry run python scripts/download_all_gnomad_v4.py \
  --output-dir /path/to/large/disk \
  --dataset genomes \
  --extract \
  --combine \
  --threads 4
```

### Extract from Existing Downloads
```bash
# If you already downloaded the VCFs
poetry run python scripts/download_all_gnomad_v4.py \
  --output-dir /path/to/downloads \
  --extract-only \
  --combine
```

## Expected Output Sizes

| Dataset | Format | Common (AF≥0.1%) | All Variants |
|---------|--------|------------------|--------------|
| Genomes | Minimal | ~500MB | ~25GB |
| Genomes | Populations | ~1GB | ~50GB |
| Genomes | Comprehensive | ~1.5GB | ~75GB |
| Exomes | Minimal | ~300MB | ~15GB |
| Exomes | Populations | ~600MB | ~30GB |
| Combined | Populations | ~1.6GB | ~80GB |

## Performance Tips

1. **Use parallel streaming** with 4-8 threads
2. **Filter by AF** if you only need common variants
3. **Process by chromosome** to checkpoint progress
4. **Use SSDs** for output files
5. **Compress output** with bgzip for storage

## Example: Production Pipeline

```bash
#!/bin/bash
# Full extraction pipeline

OUTPUT_DIR="./gnomad_v4_afs"
mkdir -p $OUTPUT_DIR

# 1. Stream common variants first (quick test)
echo "Extracting common variants..."
poetry run python scripts/stream_gnomad_v4_afs.py \
  --dataset genomes \
  --output $OUTPUT_DIR/gnomad_v4_common.tsv \
  --min-af 0.001 \
  --threads 8

# 2. Stream all genome variants
echo "Extracting all genome variants..."
poetry run python scripts/stream_gnomad_v4_afs.py \
  --dataset genomes \
  --output $OUTPUT_DIR/gnomad_v4_genomes_all.tsv \
  --fields populations \
  --threads 8

# 3. Compress and index
echo "Compressing..."
bgzip $OUTPUT_DIR/gnomad_v4_genomes_all.tsv
tabix -s1 -b2 -e2 $OUTPUT_DIR/gnomad_v4_genomes_all.tsv.gz

echo "Done! Results in $OUTPUT_DIR"
```

## Using the Data

### Quick lookups
```bash
# Look up specific variant
tabix gnomad_v4_genomes_all.tsv.gz 7:140753336-140753336

# Get all variants in a gene region
tabix gnomad_v4_genomes_all.tsv.gz 17:7571720-7590868
```

### Load into database
```sql
-- PostgreSQL example
CREATE TABLE gnomad_v4_afs (
    chrom VARCHAR(2),
    pos INTEGER,
    ref VARCHAR(1000),
    alt VARCHAR(1000),
    af REAL,
    af_afr REAL,
    af_ami REAL,
    af_amr REAL,
    af_asj REAL,
    af_eas REAL,
    af_fin REAL,
    af_mid REAL,
    af_nfe REAL,
    af_sas REAL,
    af_remaining REAL
);

\COPY gnomad_v4_afs FROM 'gnomad_v4_genomes_all.tsv' CSV HEADER DELIMITER E'\t';
CREATE INDEX idx_variant ON gnomad_v4_afs(chrom, pos);
```

## Troubleshooting

### "No space left on device"
- Stream directly without downloading
- Use `--min-af` to reduce size
- Process chromosomes separately

### "Connection timeout"
- Use fewer threads
- Process smaller chromosomes first
- Check internet stability

### "Memory error"
- Process one chromosome at a time
- Use streaming instead of loading all data

## Future: When gnomAD v4 is in BigQuery

Once available, this will be the fastest method:
```sql
-- Export all v4 AFs in minutes
CREATE OR REPLACE TABLE my_dataset.gnomad_v4_all_afs AS
SELECT 
  chrom, pos, ref, alt,
  af, af_afr, af_ami, af_amr, af_asj, 
  af_eas, af_fin, af_mid, af_nfe, af_sas
FROM `bigquery-public-data.gnomAD.v4_1_genomes`
```

Until then, streaming is your best option for getting all gnomAD v4 AFs.