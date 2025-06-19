# Arti UI

Clinical variant interpretation interface for the Arti annotation engine.

## Overview

Arti UI provides a visual interface for interpreting clinical variants, showing the complete evidence flow from variant annotation through tier assignment to final interpretation. The interface makes the "black box" of variant interpretation completely transparent.

## Features

- **Three-Panel Layout**
  - Left: Variant list with filtering
  - Center: Evidence flow pipeline visualization
  - Right: Interpretation tools and actions

- **Evidence Flow Pipeline**
  - Variant details with VAF visualization
  - Evidence collection from multiple knowledge bases
  - Rule evaluation with transparent logic
  - Tier assignment across multiple guidelines
  - Clinical interpretation templates

- **Advanced Interpretation Management**
  - **Custom Interpretation Entry**: Clinicians can write their own interpretations when existing templates don't fit their needs
  - **Flexible Sorting**: Sort interpretations by most recent, highest confidence, or disease relevance
  - **Disease-Specific Filtering**: Show only interpretations relevant to the current cancer type
  - **Template Organization**: Browse, copy, and edit existing interpretation templates
  - **Metadata Display**: See confidence scores, disease context, and modification dates

- **Multi-Guideline Support**
  - OncoKB
  - CGC/VICC
  - AMP/ASCO

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Or use the start script
./start.sh
```

## Technology Stack

- React 18 with TypeScript
- Vite for fast development
- Tailwind CSS for styling
- Zustand for state management
- Recharts for data visualization
- Lucide React for icons

## Project Structure

```
src/
├── components/         # React components
│   ├── pipeline/      # Evidence flow pipeline components
│   ├── CaseHeader.tsx
│   ├── VariantList.tsx
│   ├── EvidenceFlowPipeline.tsx
│   └── InterpretationPanel.tsx
├── types/             # TypeScript type definitions
├── store/             # Zustand state management
├── utils/             # Utility functions
└── styles/            # CSS styles
```

## Development

The UI is designed to work with the Arti annotation engine backend. Currently using mock data for development.

### Key Components

1. **VariantCard** - Shows variant genomic details
2. **AnnotationsCard** - Displays evidence from knowledge bases
3. **RulesCard** - Shows which classification rules fired
4. **TierAssignmentCard** - Displays tier assignments from each guideline
5. **InterpretationCard** - Clinical interpretation templates

### State Management

Using Zustand for global state management. The main store (`interpretationStore.ts`) manages:
- Current case information
- Variant list and selection
- UI state (expanded sections, view mode)
- Filters and search

### Interpretation Workflow

The interpretation system supports clinical decision-making with:

1. **Template-Based Interpretations**: Pre-written interpretations for common variants and disease contexts
2. **Custom Interpretation Entry**: Full-featured text editor for clinicians to write custom interpretations
3. **Intelligent Sorting**: 
   - **Most Recent**: Shows newest interpretations first
   - **Highest Confidence**: Prioritizes high-confidence interpretations
   - **Disease Relevance**: Matches interpretations to current case disease type
4. **Disease Filtering**: Toggle to show only interpretations relevant to the current cancer type
5. **Template Management**: Browse, copy, edit, and organize interpretation templates

### Clinical Features

- **Evidence Integration**: Interpretations automatically link to supporting evidence
- **Citation Management**: PubMed links and reference tracking
- **Version Control**: Track modification dates and authors
- **Confidence Scoring**: Display confidence levels for each interpretation
- **Disease Context**: Tag interpretations with relevant cancer types

## API Integration

The UI expects to connect to the Arti backend API at `/api`. Update the API endpoint in the configuration as needed.