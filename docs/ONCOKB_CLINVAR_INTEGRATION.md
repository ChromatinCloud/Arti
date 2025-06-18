# OncoKB-ClinVar Integration

## Overview
This document describes the integration between ClinVar pathogenicity data and OncoKB therapeutic annotations.

## Implementation Summary

### Scripts Created

1. **`clinvar_to_oncokb.py`**
   - Converts ClinVar variants to HGVS genomic notation
   - Queries OncoKB API in 1000-variant batches
   - Handles all variant types (SNV, Indel, Deletion, Duplication, etc.)
   - Includes retry logic and rate limiting
   - Saves combined ClinVar + OncoKB data

2. **`analyze_oncokb_results.py`**
   - Separates variants with/without OncoKB annotations
   - Creates tabular format for variants with therapeutic relevance
   - Logs variants without annotations for review

3. **`process_all_clinvar_oncokb.py`**
   - Processes all ClinVar significance files
   - Prioritizes pathogenic variants
   - Resumable processing
   - Estimated 6-7 hours for complete run

### Key Optimizations

- **Batch Size**: 1000 variants per API call (reduced from 50)
- **API Calls**: ~10,000 total (reduced from ~200,000)
- **Processing Time**: ~6-7 hours (reduced from ~140 hours)
- **Rate Limiting**: 0.5 seconds between batches
- **Retry Logic**: Automatic retry with exponential backoff

## Results from Test Run

From 10,000 pathogenic/likely pathogenic ClinVar variants:
- **440 unique variants** had OncoKB annotations
- **3,517 total annotations** (multiple per variant for different cancer types)
- **3,343 variants with treatment annotations**
- **1,883 Level 1 annotations** (FDA-approved treatments)

### Top Annotated Genes
1. BRCA1/BRCA2 (2,296 annotations)
2. KRAS (210 annotations)
3. BRAF (178 annotations)
4. TSC2 (105 annotations)
5. MAP2K1 (70 annotations)

### Treatment Examples
- **NF1 mutations**: Mirdametinib, Selumetinib (Level 1)
- **BRAF mutations**: Various targeted therapies
- **KRAS mutations**: Context-dependent treatments

## File Organization

```
.refs/clinical_evidence/
├── clinvar/
│   └── clinvar_by_significance/
│       ├── PLP.tsv     # Pathogenic/Likely Pathogenic
│       ├── P.tsv       # Pathogenic
│       ├── VUS.tsv     # Variants of Uncertain Significance
│       ├── C.tsv       # Conflicting
│       ├── BLB.tsv     # Benign/Likely Benign
│       ├── B.tsv       # Benign
│       └── Other.tsv   # Other classifications
└── oncokb/
    └── oncokb_by_significance/
        └── [Same structure with OncoKB annotations]
```

## Usage

### Process Single File
```bash
python scripts/clinvar_to_oncokb.py
```

### Process All Files
```bash
python scripts/process_all_clinvar_oncokb.py
```

### Analyze Results
```bash
python scripts/analyze_oncokb_results.py
```

## Integration with Annotation Engine

The OncoKB-annotated ClinVar data can be used to:
1. Pre-populate therapeutic annotations for known pathogenic variants
2. Provide confidence scores based on ClinVar + OncoKB agreement
3. Fast-track tier assignment for variants with Level 1/2 evidence
4. Enhance evidence aggregation with pre-computed annotations

## Next Steps

1. Run full processing on all ClinVar files
2. Create indexed database for fast lookup
3. Integrate into main annotation pipeline
4. Add to evidence aggregator as additional source
5. Update tiering logic to incorporate pre-computed evidence