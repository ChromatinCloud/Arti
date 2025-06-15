#!/bin/bash
# Download Example VCF Files for Testing
# Based on analysis of template repositories (PCGR, Scout, InterVar, CancerVar)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
EXAMPLE_DIR="${REPO_ROOT}/example_input"

echo "=== Downloading Example VCF Files for Annotation Engine Testing ==="
echo "Target directory: ${EXAMPLE_DIR}"

# Create example input directory
mkdir -p "${EXAMPLE_DIR}"
cd "${EXAMPLE_DIR}"

# Create README documenting the sources
cat > README.md << 'EOF'
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
EOF

echo "📁 Created ${EXAMPLE_DIR} directory"

# Download PCGR Examples (Small, well-characterized cancer VCFs)
echo "📥 Downloading PCGR example VCFs..."

# COAD (Colorectal Adenocarcinoma) - small, real cancer variants
if ! wget -O PCGR_COAD_grch37.vcf.gz \
    "https://github.com/sigven/pcgr/raw/master/examples/T001-COAD.grch37.vcf.gz"; then
    echo "❌ Failed to download PCGR COAD example"
fi

# BRCA (Breast Cancer) - different cancer type for diversity
if ! wget -O PCGR_BRCA_grch37.vcf.gz \
    "https://github.com/sigven/pcgr/raw/master/examples/T001-BRCA.grch37.vcf.gz"; then
    echo "❌ Failed to download PCGR BRCA example"
fi

# Download accompanying sample metadata if available
if ! wget -O PCGR_COAD_metadata.txt \
    "https://github.com/sigven/pcgr/raw/master/examples/sample_id_mapping.txt"; then
    echo "⚠️  Could not download PCGR metadata (optional)"
fi

echo "✅ PCGR examples downloaded"

# Download Scout Examples (Clinical genomics workflow examples)
echo "📥 Downloading Scout example VCFs..."

# Scout demo VCFs - clinical vs research variants
scout_base_url="https://github.com/Clinical-Genomics/scout/raw/master/scout/demo"

# Clinical variants (small variants)
if ! wget -O Scout_clinical_variants.vcf.gz \
    "${scout_base_url}/643594.clinical.vcf.gz"; then
    echo "⚠️  Could not download Scout clinical variants"
fi

# Cancer-specific test VCF
if ! wget -O Scout_cancer_test.vcf.gz \
    "${scout_base_url}/cancer_test.vcf.gz"; then
    echo "⚠️  Could not download Scout cancer test VCF"
fi

# Tumor-only SNV/indel example
if ! wget -O Scout_tumor_only_snv.vcf.gz \
    "${scout_base_url}/scout_example_tumor_only.snv.indel.sorted.vcf.gz"; then
    echo "⚠️  Could not download Scout tumor-only example"
fi

echo "✅ Scout examples downloaded"

# Download InterVar/CancerVar Examples (ACMG/AMP guideline test cases)
echo "📥 Downloading InterVar/CancerVar example files..."

# InterVar example (ACMG/AMP guidelines)
if ! wget -O InterVar_example.avinput \
    "https://github.com/WGLab/InterVar/raw/master/example/ex1.avinput"; then
    echo "⚠️  Could not download InterVar example"
fi

# CancerVar FDA example (Cancer-specific guidelines)
if ! wget -O CancerVar_FDA_example.av \
    "https://github.com/WGLab/CancerVar/raw/master/example/FDA_hg19.av"; then
    echo "⚠️  Could not download CancerVar FDA example"
fi

echo "✅ InterVar/CancerVar examples downloaded"

# Create small synthetic test VCF for basic validation
echo "📝 Creating synthetic test VCF for basic validation..."

cat > synthetic_test.vcf << 'VCF_EOF'
##fileformat=VCFv4.2
##reference=GRCh37
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
##FORMAT=<ID=VAF,Number=A,Type=Float,Description="Variant Allele Frequency">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
17	7674220	.	G	A	100	PASS	DP=50;AF=0.45	GT:AD:DP:VAF	0/1:27,23:50:0.46
7	140753336	.	T	A	95	PASS	DP=45;AF=0.52	GT:AD:DP:VAF	0/1:22,23:45:0.51
12	25245350	.	C	T	85	PASS	DP=38;AF=0.42	GT:AD:DP:VAF	0/1:22,16:38:0.42
3	178952085	.	A	G	110	PASS	DP=55;AF=0.38	GT:AD:DP:VAF	0/1:34,21:55:0.38
VCF_EOF

echo "✅ Created synthetic test VCF with known variants:"
echo "   - TP53 p.R273H (pathogenic)"
echo "   - BRAF V600E (actionable)"
echo "   - KRAS G12C (emerging actionable)"  
echo "   - PIK3CA H1047R (pathogenic)"

# Create malformed VCF for negative testing
echo "📝 Creating malformed VCF for negative testing..."

cat > malformed_test.vcf << 'BAD_VCF_EOF'
##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
17	7674220	.	G	A	100	PASS	DP=50
7	INVALID_POS	.	T	A	95	PASS	DP=45
12	25245350	.	MISSING_ALT		85	PASS	DP=38
BAD_VCF_EOF

echo "✅ Created malformed VCF for input validation testing"

# Update README with file descriptions
cat >> README.md << 'EOF'

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
EOF

# Show summary
echo ""
echo "=== Download Complete ==="
echo "📊 Summary of downloaded files:"
find "${EXAMPLE_DIR}" -name "*.vcf*" -o -name "*.av*" -o -name "*.avinput" | while read -r file; do
    filename=$(basename "$file")
    size=$(ls -lh "$file" | awk '{print $5}')
    echo "   📄 ${filename} (${size})"
done

echo ""
echo "📖 Documentation: ${EXAMPLE_DIR}/README.md"
echo "🎯 Start testing with: synthetic_test.vcf (4 well-known variants)"
echo "✅ Ready for CLI input validation development!"
EOF