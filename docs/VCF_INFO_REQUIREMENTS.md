# VCF INFO Field Requirements for Clinical Reporting

## Executive Summary

Based on analysis of the existing codebase and clinical requirements, here are the essential VCF INFO and FORMAT fields needed for confident clinical variant annotation and reporting.

## Critical Fields for Clinical Confidence

### **Required for Tier Assignment**

#### INFO Fields
1. **DP** (Total Read Depth)
   - **Why Critical**: Primary metric for variant calling confidence
   - **Clinical Impact**: Affects tier assignment confidence scores
   - **Threshold**: Minimum 20x for tumor-only, 10x for tumor-normal
   - **Used By**: Quality filtering, confidence scoring, clinical disclaimers

2. **QUAL** (Quality Score)
   - **Why Critical**: Variant calling confidence
   - **Clinical Impact**: Low quality variants may be filtered or flagged
   - **Threshold**: Recommend ≥30 for clinical reporting
   - **Used By**: Variant filtering, quality assessment

#### FORMAT Fields (Per-Sample)
1. **GT** (Genotype)
   - **Why Critical**: Determines zygosity (het/hom)
   - **Clinical Impact**: Affects pathogenicity assessment and inheritance
   - **Required**: Yes - essential for variant interpretation

2. **AD** (Allelic Depths)
   - **Why Critical**: Used to calculate VAF (Variant Allele Frequency)
   - **Clinical Impact**: VAF determines somatic vs germline classification
   - **Formula**: VAF = alt_depth / (ref_depth + alt_depth)
   - **Used By**: Somatic classification, purity estimation, filtering

3. **DP** (Sample Depth)
   - **Why Critical**: Per-sample coverage depth
   - **Clinical Impact**: Sample-specific quality assessment
   - **Used By**: Quality control, confidence scoring

### **Highly Recommended for Enhanced Reporting**

#### Allele Frequency (Multiple Options)
- **AF** (Allele Frequency) - Pre-calculated frequency
- **VAF** (Variant Allele Frequency) - Alternative to AF
- **FREQ** (Frequency) - Some callers use this field

*Note: If these aren't present, VAF is calculated from FORMAT/AD*

#### Quality Metrics
1. **MQ** (Mapping Quality)
   - **Purpose**: Assess read mapping confidence
   - **Clinical Use**: Flag variants in low-mappability regions

2. **QD** (Quality by Depth)
   - **Purpose**: Normalize quality by depth
   - **Clinical Use**: More robust quality metric than raw QUAL

3. **FS** (Fisher Strand Bias)
   - **Purpose**: Detect strand bias artifacts
   - **Clinical Use**: Flag potential sequencing artifacts

4. **SOR** (Strand Odds Ratio)
   - **Purpose**: Alternative strand bias metric
   - **Clinical Use**: More sensitive than FS in some cases

#### Additional Quality Fields
- **BaseQRankSum** - Base quality rank sum test
- **MQRankSum** - Mapping quality rank sum test
- **ReadPosRankSum** - Read position bias test

## Current Implementation Analysis

### **Fields Currently Parsed** (from codebase analysis):

#### Standard VCF Fields
- ✅ **DP** - Total depth (INFO)
- ✅ **AF** - Allele frequency (INFO)
- ✅ **AC** - Allele count
- ✅ **AN** - Total alleles
- ✅ **QUAL** - Quality score (main column)
- ✅ **FILTER** - Filter status (main column)

#### FORMAT Fields
- ✅ **GT** - Genotype
- ✅ **AD** - Allelic depths
- ✅ **DP** - Sample depth
- ✅ **GQ** - Genotype quality

#### Special Fields
- ✅ **SOMATIC** - Somatic variant flag
- ✅ **DB** - dbSNP membership

### **Missing but Recommended**:
- ⚠️ **MQ** - Mapping quality
- ⚠️ **QD** - Quality by depth
- ⚠️ **FS** - Fisher strand bias
- ⚠️ **SOR** - Strand odds ratio

## Clinical Impact of Missing Fields

### **If DP is Missing**:
```
WARNING: Cannot assess variant calling confidence
IMPACT: All variants flagged with low confidence
RECOMMENDATION: Include in tumor-only disclaimer
```

### **If AD is Missing**:
```
ERROR: Cannot calculate VAF
IMPACT: Cannot perform somatic classification
RECOMMENDATION: Require AD for processing
```

### **If Quality Metrics Missing**:
```
WARNING: Limited quality assessment available
IMPACT: May include low-quality variants in report
RECOMMENDATION: Manual review of variant calls
```

## Validation Logic Implementation

### **Input Validator Checks**:

```python
# Required fields (will cause errors)
REQUIRED_INFO_FIELDS = {"DP"}
REQUIRED_FORMAT_FIELDS = {"GT", "AD", "DP"}

# Recommended fields (will cause warnings)
RECOMMENDED_INFO_FIELDS = {"AF", "VAF", "FREQ", "MQ", "QD", "FS"}
```

### **Quality Assessment**:

```python
def assess_vcf_quality(vcf_path):
    """Assess VCF quality for clinical use"""
    stats = {
        "median_depth": None,
        "median_qual": None,
        "low_depth_fraction": 0,
        "has_quality_metrics": False
    }
    
    # Parse first 1000 variants for statistics
    for variant in parse_vcf(vcf_path, limit=1000):
        # Collect depth from INFO/DP or FORMAT/DP
        if variant.info.get("DP"):
            depths.append(int(variant.info["DP"]))
        
        # Collect quality scores
        if variant.qual and variant.qual != ".":
            quals.append(float(variant.qual))
    
    # Calculate statistics and warnings
    if median_depth < 20:
        warnings.append("Low median depth may affect variant confidence")
    
    if median_qual < 30:
        warnings.append("Low quality scores may indicate calling issues")
```

## Recommendations for Clinical Labs

### **Minimum Requirements**:
1. **Always include**: DP (INFO), GT/AD/DP (FORMAT), QUAL (column)
2. **Include if possible**: AF/VAF, MQ, QD, FS
3. **Document thresholds**: Depth, quality, VAF cutoffs used

### **Best Practices**:
1. **Depth**: Aim for ≥30x median depth for confident calling
2. **Quality**: Use QUAL ≥30 for most variant callers
3. **Strand bias**: Include FS or SOR to detect artifacts
4. **Mapping**: Include MQ to assess repetitive regions

### **Clinical Disclaimers**:

```
When depth < 20x:
"Variant calling confidence may be reduced due to low sequencing depth (median: Xx). 
Clinical correlation recommended for critical decisions."

When quality metrics missing:
"Limited quality metrics available. Variants should be confirmed by orthogonal method 
if clinically significant."
```

## Tool-Specific Considerations

### **GATK HaplotypeCaller**:
- Produces: DP, AF, MQ, QD, FS, SOR, BaseQRankSum, MQRankSum
- Quality: Excellent for SNVs, good for indels
- Recommendation: Use all available fields

### **FreeBayes**:
- Produces: DP, AF, MQM, MQMR (mapping quality)
- Quality: Good for population calling
- Note: Different field names (MQM vs MQ)

### **VarScan2**:
- Produces: DP, FREQ (instead of AF), custom fields
- Quality: Good for somatic calling
- Note: Uses FREQ instead of AF

### **Strelka2**:
- Produces: DP, custom tier fields, strand bias
- Quality: Excellent for somatic variants
- Note: Has built-in quality tiers

## Implementation in Input Validator

The new `InputValidatorV2` implements these requirements:

1. **Required Field Validation**: Errors if GT/AD/DP missing
2. **Quality Assessment**: Warns on low depth/quality
3. **Clinical Context**: Explains impact of missing fields
4. **Flexible AF Handling**: Accepts AF, VAF, or FREQ
5. **Depth Statistics**: Calculates median and low-depth fraction

This ensures clinical reports include appropriate confidence levels and disclaimers based on VCF quality.