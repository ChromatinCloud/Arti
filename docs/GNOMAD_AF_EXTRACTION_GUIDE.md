# gnomAD Population AF Extraction Guide

## Overview

This guide documents the tools and approaches for extracting population allele frequencies from gnomAD v4 and All of Us datasets.

## gnomAD v4.0 vs v4.1

Both versions contain data from **807,162 individuals** (730,947 exomes + 76,215 genomes):

### v4.0 (November 2023)
- Initial release with core features
- Basic variant frequencies and annotations
- Aligned to GRCh38

### v4.1 (April 2024) 
- Same underlying data as v4.0
- Added browser features, REVEL scores, gene constraints
- Bug fixes including allele number issues

**For AF extraction, either version works** - they have identical variant data.

## Population Groups in gnomAD v4

- **afr**: African/African American
- **ami**: Amish
- **amr**: Admixed American  
- **asj**: Ashkenazi Jewish
- **eas**: East Asian
- **fin**: Finnish
- **mid**: Middle Eastern
- **nfe**: Non-Finnish European
- **sas**: South Asian
- **remaining**: 31,256 unclustered samples

## Available Scripts

### 1. `gnomad_v4_final.py` - Recommended
Works with both v4.0 and v4.1, automatically detects which is accessible.

```bash
# Extract AFs for your variants
poetry run python scripts/gnomad_v4_final.py input.vcf --output gnomad_afs.tsv

# Test with demo variants
poetry run python scripts/gnomad_v4_final.py --demo
```

### 2. `gnomad_bigquery_extractor.py` - For gnomAD v2.1.1
Uses BigQuery to extract from gnomAD v2.1.1 (v4 not available in BigQuery yet).

```bash
# Setup BigQuery first
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Extract gnomAD v2.1.1 data
poetry run python scripts/gnomad_bigquery_extractor.py input.vcf --output gnomad_v2_afs.tsv
```

### 3. `bigquery_af_extractor.py` - Multiple datasets
Extracts from 1000 Genomes and gnomAD v2.1.1 via BigQuery.

```bash
# Check setup
poetry run python scripts/bigquery_af_extractor.py --check-setup

# Extract specific chromosome
poetry run python scripts/bigquery_af_extractor.py --dataset kg1_phase3 --chromosome 7 --output kg_chr7.tsv
```

## Important Notes

1. **Variant Existence**: Your variants must exist in gnomAD to get AF data. gnomAD only contains variants observed in their cohort.

2. **Access Methods**:
   - **Direct HTTP**: Uses bcftools/tabix on public Google Cloud Storage URLs
   - **BigQuery**: Only has gnomAD v2.1.1 and 1000 Genomes (not v4 yet)
   - **API**: GraphQL API available but limited to small queries

3. **URL Formats**:
   ```
   # gnomAD v4.1
   https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{CHR}.vcf.bgz
   
   # gnomAD v4.0  
   https://storage.googleapis.com/gcp-public-data--gnomad/release/4.0/vcf/genomes/gnomad.genomes.v4.0.sites.chr{CHR}.vcf.bgz
   ```

## All of Us Dataset

All of Us v7 requires authenticated access through Terra platform:
- Visit: https://www.researchallofus.org/data-tools/workbench/
- Use BigQuery queries in Terra workspace
- Contains diverse US population data

## Troubleshooting

### No variants found
- This is normal - your variants may not exist in gnomAD
- Try known common variants (rs IDs from dbSNP)
- Check cancer hotspot databases for somatic variants

### Access issues
- Ensure bcftools is installed: `brew install bcftools`
- Check internet connectivity to Google Cloud Storage
- For BigQuery: ensure `gcloud auth login` is complete

### Performance
- Query by chromosome to reduce data transfer
- Use specific regions rather than whole genome
- Consider caching results locally

## Example Output Format

```tsv
CHROM	POS	REF	ALT	AF	AN	AC	AF_afr	AF_ami	AF_amr	AF_asj	AF_eas	AF_fin	AF_mid	AF_nfe	AF_sas	AF_remaining
7	140753336	T	A	0.00123	1614340	1987	0.00234	0	0.00156	0.00089	0.00012	0.00198	0.00145	0.00098	0.00067	0.00134
```

## Performance Comparison

| Method | Speed | Setup | Limitations |
|--------|-------|-------|-------------|
| bcftools on URLs | Fast for small queries | None | Network dependent |
| BigQuery | Very fast | gcloud auth | Only v2.1.1 |
| VEP plugin | Slow | VEP + plugin setup | Full annotation overhead |
| Pre-extraction | Fastest lookup | Large storage | Initial setup time |

## Next Steps

1. For production use, consider pre-extracting common variants
2. Set up local cache for frequently queried regions
3. Use BigQuery for large-scale analysis of v2.1.1 data
4. Monitor gnomAD releases for v4 availability in BigQuery