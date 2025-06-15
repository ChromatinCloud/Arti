# Example Input Files for Annotation Engine Testing

This directory contains curated VCF files from established clinical annotation tools for testing our annotation engine.

## File Sources and Descriptions

### PCGR Examples (Personal Cancer Genome Reporter)
- **Repository:** https://github.com/sigven/pcgr
- **Use Case:** Small, real cancer variants from TCGA samples
- **Testing Value:** Known pathogenic variants, quality metrics, cancer-specific

### Scout Examples (Clinical Genomics)
- **Repository:** https://github.com/Clinical-Genomics/scout
- **Use Case:** Clinical vs research variants, tumor-only samples
- **Testing Value:** Tier assignment validation, diverse variant types

### InterVar/CancerVar Examples
- **Repository:** https://github.com/WGLab/InterVar and CancerVar
- **Use Case:** ACMG/AMP guideline test cases
- **Testing Value:** Known tier assignments, FDA-validated variants

### COLO829 Benchmark
- **Repository:** Multiple sources (UMCUGenetics, Zenodo)
- **Use Case:** Industry standard somatic variant benchmark
- **Testing Value:** Gold standard for validation

## File Descriptions

### PCGR_COAD_grch37.vcf.gz
- **Source:** PCGR T001-COAD example (Colorectal Adenocarcinoma)
- **Variants:** ~50 somatic variants from TCGA sample
- **Use:** Real cancer variants with quality metrics
- **Testing:** Annotation pipeline validation, tier assignment

### PCGR_BRCA_grch37.vcf.gz  
- **Source:** PCGR T001-BRCA example (Breast Cancer)
- **Variants:** ~40 somatic variants from TCGA sample
- **Use:** Different cancer type for diversity testing
- **Testing:** Cancer-type specific annotation

### Scout_clinical_variants.vcf.gz
- **Source:** Scout demo clinical variants
- **Variants:** Clinical-grade variants with known interpretations
- **Use:** Clinical workflow testing
- **Testing:** Tier assignment validation

### Scout_cancer_test.vcf.gz
- **Source:** Scout cancer-specific test cases
- **Variants:** Cancer variants with expected tiers
- **Use:** Cancer annotation validation
- **Testing:** Oncogenicity assessment

### Scout_tumor_only_snv.vcf.gz
- **Source:** Scout tumor-only SNV/indel example
- **Variants:** Tumor-only somatic variants
- **Use:** Matches our primary use case
- **Testing:** Somatic annotation workflow

### InterVar_example.avinput
- **Source:** InterVar ACMG/AMP example
- **Variants:** ACMG/AMP guideline test cases
- **Use:** ACMG/AMP rule validation
- **Testing:** Evidence code assignment (PS1, PM1, etc.)

### CancerVar_FDA_example.av
- **Source:** CancerVar FDA benchmark
- **Variants:** FDA-validated cancer variants
- **Use:** Cancer-specific guideline testing
- **Testing:** AMP/ASCO/CAP tier assignment

### synthetic_test.vcf
- **Source:** Created for this project
- **Variants:** 4 well-known variants (TP53, BRAF, KRAS, PIK3CA)
- **Use:** Quick validation testing
- **Testing:** Basic annotation and tier assignment

### malformed_test.vcf
- **Source:** Created for this project
- **Variants:** Intentionally malformed VCF entries
- **Use:** Input validation testing
- **Testing:** Error handling and validation logic

## Usage Notes

1. **Start with synthetic_test.vcf** for initial development
2. **Use PCGR examples** for real cancer variant testing
3. **Use Scout examples** for clinical workflow validation
4. **Use InterVar/CancerVar** for guideline compliance testing
5. **Use malformed_test.vcf** for robust error handling

## File Sizes and Characteristics

- Small test files: synthetic_test.vcf (4 variants)
- Medium files: PCGR examples (30-50 variants)
- Diverse cancer types: COAD, BRCA, general cancer
- Variant types: SNVs, indels, multi-allelic
- Quality metrics: DP, VAF, quality scores included
- Error cases: malformed_test.vcf for negative testing
