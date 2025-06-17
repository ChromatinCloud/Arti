# Workflow Router Implementation

## Overview

The workflow router provides pathway-specific analysis for tumor-only vs tumor-normal variant interpretation. It adjusts knowledge base priorities, evidence weights, and VAF thresholds based on the analysis type.

## Key Components

### 1. WorkflowRouter (`workflow_router.py`)

Main class that manages pathway-specific configuration:
- **Tumor-Normal Pathway**: Emphasizes clinical databases, strict normal filtering
- **Tumor-Only Pathway**: Higher weight on population databases, conservative VAF thresholds

### 2. PathwayConfig

Configuration dataclass containing:
- KB priority ordering
- Evidence weight multipliers
- VAF filtering thresholds
- Pathway-specific flags

### 3. Integration Points

#### Evidence Aggregator
- Accepts workflow router in constructor
- Adjusts evidence confidence scores based on pathway weights
- Maintains original scores while adding pathway-adjusted confidence

#### Tiering Engine
- Uses workflow router for pre-filtering variants
- Applies pathway-specific VAF thresholds
- Returns Tier IV for filtered variants with explanation

#### CLI
- Creates workflow router based on analysis type
- Displays pathway configuration to user
- Passes router through the annotation pipeline

## Key Features

### VAF Thresholds

**Tumor-Normal:**
- Min tumor VAF: 5%
- Max normal VAF: 2%
- Min T/N ratio: 5x
- Clonal threshold: 40%

**Tumor-Only:**
- Min tumor VAF: 10% (higher due to no normal)
- Max population AF: 0.1%
- Hotspot min VAF: 5%
- Clonal threshold: 35%

### Evidence Weights

**Tumor-Normal Weights:**
- Clinical DBs (OncoKB, FDA): 1.0
- Hotspots: 0.85
- Population DBs: 0.2 (for filtering)
- Computational: 0.5

**Tumor-Only Weights:**
- Clinical DBs: 1.0 (unchanged)
- Population DBs: 0.7 (much higher)
- Computational: 0.6 (more important)
- Conservation: 0.5 (higher weight)

### KB Priority Differences

Both pathways prioritize clinical evidence, but tumor-only brings population databases higher in the priority list for better germline filtering.

## Usage Example

```python
from annotation_engine.workflow_router import create_workflow_router
from annotation_engine.models import AnalysisType

# Create router
router = create_workflow_router(
    analysis_type=AnalysisType.TUMOR_NORMAL,
    tumor_type="LUAD"
)

# Check if variant should be filtered
should_filter = router.should_filter_variant(
    tumor_vaf=0.15,
    normal_vaf=0.01,
    population_af=0.0001,
    is_hotspot=False
)

# Adjust evidence scores
adjusted_evidence = router.adjust_evidence_scores(evidence_list)

# Get clonality
clonality = router.classify_vaf_clonality(0.35)  # "indeterminate"
```

## Benefits

1. **Appropriate Filtering**: Different VAF thresholds for each analysis type
2. **Evidence Prioritization**: Pathway-specific weighting of evidence sources
3. **Germline Handling**: Better germline filtering for tumor-only samples
4. **Flexibility**: Easy to add new pathways or adjust configurations
5. **Transparency**: Clear reporting of filtering decisions

## Testing

Comprehensive test suite in `test_workflow_router.py` covering:
- Configuration loading
- VAF filtering logic
- Evidence weight adjustment
- Clonality classification
- Integration with tiering engine

## Future Enhancements

1. **Disease-Specific Pathways**: Custom rules for specific cancer types
2. **Custom Thresholds**: User-configurable VAF thresholds
3. **Additional Pathways**: Liquid biopsy, constitutional analysis
4. **ML Integration**: Learn optimal weights from validation data