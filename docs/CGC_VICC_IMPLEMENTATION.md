# CGC/VICC 2022 Oncogenicity Classification Implementation

## Overview

We have implemented the Clinical Genome Resource (ClinGen) Cancer Variant Curation Expert Panel (CG-CV-VCEP) and Variant Interpretation for Cancer Consortium (VICC) oncogenicity classification framework based on the 2022 manuscript (https://pubmed.ncbi.nlm.nih.gov/36063163/).

This implementation leverages all available knowledge bases in the `.refs/` directory to provide comprehensive oncogenicity classification as the foundation for clinical tier assignment.

## Architecture

### 1. Core Classifier (`cgc_vicc_classifier.py`)

The main implementation includes:

- **17 Criteria Implementation**:
  - Oncogenic: OVS1, OS1-3, OM1-4, OP1-4
  - Benign: SBVS1, SBS1-2, SBP1-2
  
- **Knowledge Base Integration**:
  - **Hotspots**: MSK Cancer Hotspots, OncoVI hotspots, COSMIC
  - **Population**: gnomAD v4.1
  - **Clinical**: OncoKB, CIViC, ClinVar (somatic)
  - **Functional**: AlphaMissense, SpliceAI
  - **Cancer Genes**: COSMIC CGC, OncoKB curated genes

- **Classification Logic**:
  - Implements official combination rules from Table 2 of the manuscript
  - Returns one of 5 classifications: Oncogenic, Likely Oncogenic, VUS, Likely Benign, Benign

### 2. Integration Module (`oncogenicity_integration.py`)

Implements the two-layer sequential approach:

- **Layer 1**: CGC/VICC oncogenicity (biological impact)
- **Layer 2**: AMP/ASCO/CAP tiers (clinical actionability)

Key features:
- `OncogenicityAwareTieringEngine` that wraps existing tiering
- Oncogenicity classification serves as foundation for tier assignment
- Comprehensive JSON output with full evidence trail

## Criteria Implementation Details

### Strong Evidence Examples

**OVS1** (Very Strong): Null variant in tumor suppressor gene
```python
# Frameshift in TP53 → Oncogenic
if variant.consequence in ["frameshift_variant", "stop_gained"] and variant.is_tumor_suppressor:
    return OVS1_met
```

**OS3** (Strong): Well-established cancer hotspot
```python
# BRAF V600E with >50 samples → Strong evidence
if hotspot_samples >= 50 or cancerhotspots_qvalue < 0.01:
    return OS3_met
```

### Population Evidence

**SBVS1** (Very Strong Benign): MAF >5% in gnomAD
```python
# Common polymorphism → Benign
if gnomad_af > 0.05:
    return SBVS1_met
```

## Knowledge Base Usage

### 1. Hotspot Databases
- **MSK Cancer Hotspots v2.5**: Statistical hotspot detection
- **OncoVI Hotspots**: Single residue and indel hotspots
- **COSMIC Hotspots**: If available in `.refs/cancer_signatures/cosmic/`

### 2. Population Databases
- **gnomAD**: Gold standard for population frequencies
- Thresholds: >5% (SBVS1), >1% (SBS1), <0.00001 (OP4)

### 3. Clinical Evidence
- **OncoKB**: For same amino acid changes (OS1)
- **CIViC**: Supporting clinical evidence
- **ClinVar**: Somatic interpretations

### 4. Functional Predictions
- **AlphaMissense**: Missense pathogenicity
- **SpliceAI**: Splice effect predictions
- **CADD/REVEL**: General pathogenicity scores

## Usage Example

```python
from annotation_engine.cgc_vicc_classifier import CGCVICCClassifier
from annotation_engine.models import VariantAnnotation

# Initialize classifier
classifier = CGCVICCClassifier(kb_path=Path("./.refs"))

# Create variant
variant = VariantAnnotation(
    chromosome="7",
    position=140453136,
    reference="A", 
    alternate="T",
    gene_symbol="BRAF",
    hgvs_p="p.Val600Glu",
    # ... other fields
)

# Classify
result = classifier.classify_variant(variant, cancer_type="Melanoma")

print(f"Classification: {result.classification}")
print(f"Confidence: {result.confidence_score}")
print(f"Criteria met: {[c.criterion.value for c in result.criteria_met]}")
```

## Integration with Tiering

```python
from annotation_engine.oncogenicity_integration import OncogenicityAwareTieringEngine

# Initialize integrated engine
engine = OncogenicityAwareTieringEngine()

# Get tier with oncogenicity consideration
tier_result = engine.assign_tier_with_oncogenicity(
    variant,
    cancer_type="Melanoma",
    analysis_type=AnalysisType.TUMOR_ONLY
)

# Result includes both layers
print(f"Clinical Tier: {tier_result.amp_scoring.tier}")
print(f"Oncogenicity: {tier_result.metadata['oncogenicity_classification']}")
```

## Output Format

The complete JSON output includes:

```json
{
  "classification": {
    "clinical_tier": {
      "tier": "Tier I",
      "confidence": 0.95
    },
    "oncogenicity": {
      "classification": "Oncogenic",
      "confidence": 0.98,
      "criteria_met": ["OS1", "OS3"],
      "rationale": "Classified as Oncogenic based on CGC/VICC criteria..."
    }
  },
  "evidence": {
    "oncogenic": [
      {
        "criterion": "OS3",
        "description": "Located at well-established cancer hotspot",
        "confidence": 0.9
      }
    ],
    "therapeutic": [...]
  }
}
```

## Testing

Comprehensive test suite in `test_cgc_vicc_classifier.py`:
- Tests each criterion individually
- Tests combination rules
- Tests conflicting evidence handling
- Tests cancer type specificity
- Tests integration with tiering

## Future Enhancements

1. **Additional Criteria**: Implement experimental evidence criteria when data available
2. **Machine Learning**: Use classification results to train improved models
3. **Real-time Updates**: Connect to live knowledge base APIs
4. **Validation Studies**: Compare with expert classifications

## References

1. Horak P, et al. Standards for the classification of pathogenicity of somatic variants in cancer (oncogenicity): Joint recommendations of Clinical Genome Resource (ClinGen), Cancer Genomics Consortium (CGC), and Variant Interpretation for Cancer Consortium (VICC). Genet Med. 2022 May;24(5):986-998.

2. Additional manuscript recommendations incorporated from CGC/VICC working groups.