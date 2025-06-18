# Inter-Guideline Evidence Mapping for CGC/VICC Implementation

## Overview

Different clinical interpretation frameworks provide **mutually reinforcing evidence** rather than operating in isolation. This document maps how evidence from one guideline system can directly support criteria in another, creating a more robust classification system.

## Key Insight

OncoKB's "Oncogenic" classification, CIViC's pathogenicity assessments, and ClinVar's somatic interpretations can serve as **direct evidence** for CGC/VICC criteria, not just as separate classification systems.

## Direct Evidence Mappings

### 1. OncoKB → CGC/VICC Criteria

#### OncoKB "Oncogenic" or "Likely Oncogenic" → OS1
```
If OncoKB classifies a variant as "Oncogenic":
  → This represents expert curation that the variant drives cancer
  → Can be used as evidence for OS1 (same amino acid change as established oncogenic)
  → Especially strong if OncoKB cites functional studies
```

#### OncoKB Mutation Effect → Multiple Criteria
```
OncoKB "Gain-of-function" in oncogene → Supports OM1
OncoKB "Loss-of-function" in TSG → Supports OVS1 or OS2
OncoKB "Neutral" → Supports SBS1 or SBP1
```

#### OncoKB Hotspot Annotation → OS3/OM3
```
If OncoKB marks variant as hotspot:
  → Direct evidence for OS3 (well-established hotspot)
  → Strength depends on OncoKB's evidence level
```

### 2. CIViC → CGC/VICC Criteria

#### CIViC Evidence Items with Oncogenic Direction
```
CIViC "Pathogenic" with Evidence Level A/B → OS1
CIViC "Pathogenic" with Evidence Level C/D → OM1 or OP1
CIViC "Benign" with strong evidence → SBS1
```

#### CIViC Functional Evidence
```
CIViC functional studies showing oncogenic effect → OP1
CIViC studies showing no effect → SBP1
```

### 3. ClinVar (Somatic) → CGC/VICC Criteria

#### ClinVar Somatic Pathogenic → OS1
```
If ClinVar has somatic submission classified as "Pathogenic":
  → Especially with multiple submitters
  → Especially with functional evidence cited
  → Maps to OS1 if well-supported
```

#### ClinVar Review Status Weighting
```
3+ stars (expert panel) → Strong evidence (OS1)
2 stars (multiple submitters) → Moderate evidence (OM1)
1 star (single submitter) → Supporting evidence (OP1)
```

### 4. COSMIC → CGC/VICC Criteria

#### COSMIC Tier 1 Genes → Gene-level Support
```
If gene is COSMIC Tier 1:
  → Supports OM1 (missense in genes where missense is oncogenic)
  → Supports OVS1 (if TSG with LOF mechanism)
```

#### COSMIC FATHMM Predictions → OP1
```
COSMIC FATHMM "Pathogenic" prediction → Supporting evidence for OP1
Combined with other predictors for computational consensus
```

## Implementation Strategy

### Enhanced OS1 Implementation

```python
def _evaluate_OS1_enhanced(self, variant: VariantAnnotation) -> CriterionEvidence:
    """
    OS1: Same amino acid change as established oncogenic variant
    Enhanced to use OncoKB/CIViC/ClinVar as direct evidence
    """
    evidence_sources = []
    
    # Check OncoKB oncogenicity
    if self._check_oncokb_oncogenic(variant):
        evidence_sources.append({
            "source": "OncoKB",
            "classification": "Oncogenic",
            "confidence": 0.95,
            "note": "OncoKB expert-curated oncogenic classification"
        })
    
    # Check CIViC pathogenic evidence
    civic_evidence = self._check_civic_pathogenic(variant)
    if civic_evidence and civic_evidence['level'] in ['A', 'B']:
        evidence_sources.append({
            "source": "CIViC",
            "evidence_level": civic_evidence['level'],
            "confidence": 0.9 if civic_evidence['level'] == 'A' else 0.8,
            "note": f"CIViC pathogenic with level {civic_evidence['level']} evidence"
        })
    
    # Check ClinVar somatic pathogenic
    clinvar_evidence = self._check_clinvar_somatic_pathogenic(variant)
    if clinvar_evidence and clinvar_evidence['stars'] >= 2:
        evidence_sources.append({
            "source": "ClinVar",
            "review_status": clinvar_evidence['review_status'],
            "confidence": 0.85,
            "note": "ClinVar somatic pathogenic interpretation"
        })
    
    if evidence_sources:
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OS1,
            is_met=True,
            strength="Strong",
            evidence_sources=evidence_sources,
            confidence=max(e['confidence'] for e in evidence_sources),
            notes="Established oncogenic based on expert curation databases"
        )
```

### Cross-Framework Evidence Aggregation

```python
class CrossFrameworkEvidenceAggregator:
    """Aggregates evidence across multiple interpretation frameworks"""
    
    def aggregate_oncogenic_evidence(self, variant):
        """Collect all oncogenic classifications from different frameworks"""
        
        oncogenic_evidence = {
            'strong': [],
            'moderate': [],
            'supporting': []
        }
        
        # OncoKB oncogenicity
        oncokb_class = self.get_oncokb_classification(variant)
        if oncokb_class == "Oncogenic":
            oncogenic_evidence['strong'].append({
                'framework': 'OncoKB',
                'classification': 'Oncogenic',
                'maps_to': 'OS1'
            })
        elif oncokb_class == "Likely Oncogenic":
            oncogenic_evidence['moderate'].append({
                'framework': 'OncoKB',
                'classification': 'Likely Oncogenic',
                'maps_to': 'OM1'
            })
        
        # CIViC evidence items
        civic_items = self.get_civic_evidence_items(variant)
        for item in civic_items:
            if item['clinical_significance'] == 'Pathogenic':
                if item['evidence_level'] in ['A', 'B']:
                    oncogenic_evidence['strong'].append({
                        'framework': 'CIViC',
                        'evidence_level': item['evidence_level'],
                        'maps_to': 'OS1'
                    })
                else:
                    oncogenic_evidence['supporting'].append({
                        'framework': 'CIViC',
                        'evidence_level': item['evidence_level'],
                        'maps_to': 'OP1'
                    })
        
        return oncogenic_evidence
```

## Practical Examples

### Example 1: BRAF V600E

```
OncoKB: "Oncogenic" → Satisfies OS1
CIViC: Level A Pathogenic → Reinforces OS1
COSMIC: Tier 1 gene, hotspot → Satisfies OS3
MSK Hotspots: q-value 0.0001 → Reinforces OS3

Result: Multiple strong criteria met, high confidence "Oncogenic"
```

### Example 2: TP53 R248Q

```
OncoKB: "Oncogenic" → Satisfies OS1
ClinVar Somatic: Pathogenic (3 stars) → Reinforces OS1
COSMIC: High frequency in TCGA → Supports OS3
Multiple computational tools: Damaging → Satisfies OP1

Result: Strong evidence from multiple frameworks
```

### Example 3: Novel Missense in KRAS

```
OncoKB: No exact match, but KRAS is oncogene
CIViC: Other KRAS variants pathogenic → Supports OM1
Not in population databases → Satisfies OP4
Computational predictions agree → Satisfies OP1

Result: Moderate evidence, "Likely Oncogenic"
```

## Benefits of Inter-Framework Evidence

1. **Increased Confidence**: Multiple frameworks agreeing increases confidence
2. **Evidence Redundancy**: If one KB missing, others can provide evidence
3. **Nuanced Classification**: Different frameworks capture different aspects
4. **Clinical Validity**: Leverages years of expert curation across platforms

## Implementation Recommendations

1. **Primary Evidence Sources**:
   - Use OncoKB "Oncogenic" as direct evidence for OS1
   - Use CIViC Level A/B as strong evidence
   - Use ClinVar 2+ stars as moderate evidence

2. **Evidence Weighting**:
   - Expert-curated (OncoKB, CIViC) > Automated predictions
   - Multiple concordant sources > Single source
   - Functional evidence > In silico predictions

3. **Conflict Resolution**:
   - If OncoKB says "Oncogenic" but ClinVar says "Benign" → Flag for review
   - Weight by evidence quality and recency
   - Consider cancer-type specificity

## Updated CGC/VICC Implementation

The enhanced implementation should:

1. **Check OncoKB first** for direct oncogenic classification
2. **Aggregate CIViC evidence** items by significance
3. **Include ClinVar somatic** interpretations
4. **Use COSMIC annotations** for gene-level context
5. **Combine all evidence** for stronger criteria satisfaction

This creates a more robust system that leverages the collective wisdom of the cancer genomics community rather than treating each guideline in isolation.