# Variant Annotation Flow Visualization

## Overview

The Arti annotation engine now provides an interactive flow diagram that visualizes the complete annotation pipeline for each variant in real-time. The flow shows the progression from variant → annotations → rules → tier/oncogenicity → interpretation.

## Visual Flow Architecture

```
┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌────────────┐    ┌───────────────┐
│ Variant │───▶│ Annotations │───▶│  Rules   │───▶│ Tier/Level │───▶│ Interpretation│
└─────────┘    └─────────────┘    └──────────┘    └────────────┘    └───────────────┘
     │                │                  │               │                    │
     │                │                  │               │                    │
  Position         VEP, gnomAD      CBP1-CBP6      AMP Tier I-IV        Clinical text
  Reference        OncoKB, CIViC    scoring        VICC Oncogenic       Recommendations
  Alternate        COSMIC, REVEL    triggered      Confidence %          Significance
```

## Features

### 1. Dual View Mode

**Flow View** (Default)
- Interactive flow diagrams for each variant
- Left sidebar shows variant list with tier indicators
- Important variants (Tier I/II) highlighted with colored borders
- Click any variant to see its complete annotation flow

**Table View**
- Traditional tabular display
- All variants visible at once
- Sortable columns
- Quick access to variant details

### 2. Real-time Animation

As variants are processed:
- Flow diagrams build stage-by-stage
- Each stage animates in sequence (800ms intervals)
- Active stage highlighted with primary color border
- Progress flows from left to right

### 3. Interactive Components

Click any stage in the flow to view detailed information:

**Variant Stage**
- Genomic coordinates
- Reference/alternate alleles
- Gene symbol

**Annotations Stage**
- All annotation sources (VEP, gnomAD, OncoKB, etc.)
- Annotation types (functional, population, clinical)
- Confidence scores for each annotation
- Expandable list view

**Rules Stage**
- Triggered rules with checkmarks
- Rule names and IDs (CBP1-CBP6)
- Individual rule scores
- Evidence supporting each rule
- Total cumulative score

**Tier/Level Stage**
- AMP/ASCO/CAP 2017 tier (I-IV)
- VICC 2022 oncogenicity classification
- Overall confidence percentage
- Color-coded chips

**Interpretation Stage**
- Clinical interpretation summary
- Clinical significance assessment
- Specific recommendations
- Treatment implications

### 4. Visual Indicators

**Confidence Icons**
- ✓ Green check: High confidence (≥80%)
- ⚠ Yellow warning: Medium confidence (50-79%)
- ✗ Red X: Low confidence (<50%)

**Tier Colors**
- Tier I: Red (error)
- Tier II: Orange (warning)
- Tier III: Blue (info)
- Tier IV: Gray (default)

**Important Variants**
- Left border highlighting for Tier I/II variants
- Automatic selection of first important variant
- Rule count display in variant list

## Implementation Details

### Backend Data Structure

Each variant includes flow_data:
```json
{
  "flow_data": {
    "annotations": [
      {
        "source": "VEP",
        "type": "functional",
        "value": "missense_variant",
        "confidence": 0.9
      },
      {
        "source": "gnomAD",
        "type": "population",
        "value": "AF: 1.2e-05",
        "confidence": 1.0
      }
    ],
    "rules": [
      {
        "id": "CBP1",
        "name": "Strong clinical evidence",
        "triggered": true,
        "score": 8,
        "evidence": ["OncoKB/CIViC annotation present"]
      }
    ],
    "triggered_rules": ["CBP1", "CBP3", "CBP4"],
    "tier_rationale": ["Strong evidence from multiple sources"]
  }
}
```

### Rule System

**CBP1**: Strong clinical evidence (OncoKB/CIViC) - 8 points
**CBP2**: Cancer hotspot (COSMIC) - 6 points
**CBP3**: Deleterious consequence - 4 points
**CBP4**: Rare variant (AF < 1%) - 3 points
**CBP5**: High pathogenicity score - 4 points
**CBP6**: Highly conserved region - 2 points

Tier Assignment:
- Tier I: Score ≥ 20
- Tier II: Score ≥ 15
- Tier III: Score ≥ 10
- Tier IV: Score ≥ 5

### Frontend Components

**VariantFlowDiagram.tsx**
- Renders the interactive flow diagram
- Handles stage animations
- Manages click interactions
- Responsive design with horizontal scrolling

**JobDetail.tsx**
- Manages WebSocket connection for real-time updates
- Stores variant and flow data
- Handles view mode switching
- Displays detail dialogs

## Usage

1. **Upload VCF**: Start analysis from Dashboard
2. **View Progress**: Navigate to job detail page
3. **Watch Flow Build**: See variants appear with animated flows
4. **Interact**: Click variants to explore, click stages for details
5. **Switch Views**: Toggle between flow and table as needed

## Performance Considerations

- Flow data sent only for completed variants
- Animations use CSS transitions for smooth performance
- Virtual scrolling for large variant lists
- Lazy loading of flow diagrams
- WebSocket compression for large datasets

## Future Enhancements

1. **Export Flow Diagrams**: Save as PNG/SVG
2. **Filter by Tier**: Show only important variants
3. **Batch View**: Multiple flows on screen
4. **Custom Rules**: User-defined scoring rules
5. **Comparison Mode**: Compare variant flows
6. **3D Visualization**: Protein structure context