# Technical Filtering Module Specification
## Pre-Processing Interface for Arti Clinical Interpretation

### Overview
This module provides a modern, intuitive interface for technical variant filtering prior to clinical interpretation in Arti. It supports both tumor-only and tumor-normal modes with assay-specific configurations.

---

## Core Architecture

### Technology Stack
- **Frontend**: React 18 with TypeScript
- **State Management**: Zustand (lightweight alternative to Redux)
- **UI Components**: Custom components with Tailwind CSS for modern styling
- **Backend**: FastAPI endpoint for bcftools orchestration
- **Styling**: Mode-specific themes (tumor-only vs tumor-normal)

### Mode & Assay Configuration
```typescript
interface FilteringConfig {
  mode: 'tumor-only' | 'tumor-normal';  // Future: 'germline'
  assay: string;  // Default: 'default_assay'
  genomeBuild: 'grch38' | 'grch37';
  referenceFiles: {
    panelBed: string;
    blacklistRef: string;
    blacklistAssay: string;
    gnomadBcf: string;
  };
}
```

---

## Filter Specifications by Mode

### Tumor-Only Mode Filters
All 13 filters from the specification, with tumor-specific defaults:
- **MIN_VAF**: Default 0.05 (5%) for tumor tissue
- **MAX_POP_AF**: Default 0.01 (1%) to catch somatic variants
- **HET_AB_RANGE**: May be relaxed for tumor heterogeneity

### Tumor-Normal Mode Filters
Same filters with adjusted logic:
- **Somatic-Specific Filters**: Compare tumor vs normal genotypes
- **Germline Subtraction**: Remove variants present in matched normal
- **Contamination Check**: Flag potential normal contamination

---

## User Interface Design

### Layout Structure
```
┌─────────────────────────────────────────────────┐
│  Mode: [Tumor-Only ▼]  Assay: [Default ▼]      │
├─────────────────────────────────────────────────┤
│  Input VCF: example_input/large_sample.vcf      │
│  ─────────────────────────────────────────────  │
│                                                  │
│  ┌─ Quality Filters ──────────────────────┐     │
│  │ ☑ PASS variants only                   │     │
│  │ ☑ Min QUAL: [====|====] 50            │     │
│  │ ☑ Min GQ:   [===|=====] 30            │     │
│  │ ☑ Min DP:   [==|======] 20            │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Allele Filters ───────────────────────┐     │
│  │ ☑ Min ALT reads: [=====|===] 10       │     │
│  │ ☑ Min VAF:       [=|=======] 0.05     │     │
│  │ ☑ Het balance:   0.25 - 0.75          │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Technical Filters ────────────────────┐     │
│  │ ☑ Max strand bias (FS): [======|==] 60│     │
│  │ ☑ Min mapping quality:  [====|====] 40│     │
│  │ ☑ Panel regions only                   │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Population & Impact Filters ──────────┐     │
│  │ ☑ Max population AF: [=|=======] 0.01  │     │
│  │ ☑ Impact: ☑ HIGH  ☑ MODERATE          │     │
│  │ ☑ Remove blacklisted variants          │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  Variants: 50,000 → 487 (filtered)              │
│                                                  │
│  [Apply Filters] [Reset] [Export VCF]           │
└─────────────────────────────────────────────────┘
```

### Mode-Specific Styling

#### Tumor-Only Theme
```css
/* Warm, focused palette */
--primary: #DC2626;      /* Red-600 */
--secondary: #F59E0B;    /* Amber-500 */
--accent: #EF4444;       /* Red-500 */
--background: #FEF2F2;   /* Red-50 */
--surface: #FFFFFF;
--text: #7F1D1D;         /* Red-900 */
```

#### Tumor-Normal Theme
```css
/* Cool, comparative palette */
--primary: #2563EB;      /* Blue-600 */
--secondary: #10B981;    /* Emerald-500 */
--accent: #3B82F6;       /* Blue-500 */
--background: #EFF6FF;   /* Blue-50 */
--surface: #FFFFFF;
--text: #1E3A8A;         /* Blue-900 */
```

---

## Component Architecture

### Filter Components
```typescript
// Individual filter control
interface FilterControl {
  id: string;
  name: string;
  type: 'slider' | 'checkbox' | 'range' | 'multiselect';
  value: number | boolean | [number, number] | string[];
  enabled: boolean;
  modeSpecific?: {
    'tumor-only'?: FilterConfig;
    'tumor-normal'?: FilterConfig;
  };
}

// Filter groups for organization
interface FilterGroup {
  name: string;
  filters: FilterControl[];
  expanded: boolean;
}
```

### State Management (Zustand)
```typescript
interface TechFilteringStore {
  // State
  mode: 'tumor-only' | 'tumor-normal';
  assay: string;
  filters: Record<string, FilterControl>;
  inputVcf: string;
  outputVcf: string | null;
  variantCounts: {
    input: number;
    filtered: number;
  };
  
  // Actions
  setMode: (mode: string) => void;
  updateFilter: (id: string, value: any) => void;
  toggleFilter: (id: string) => void;
  applyFilters: () => Promise<void>;
  resetFilters: () => void;
  exportVcf: () => void;
}
```

---

## Backend Implementation

### FastAPI Endpoint
```python
@router.post("/api/v1/tech-filtering/apply")
async def apply_technical_filters(
    request: TechFilteringRequest,
    background_tasks: BackgroundTasks
) -> TechFilteringResponse:
    """
    Apply sequential bcftools filters based on user selections
    """
    # Validate input VCF exists
    # Build bcftools command pipeline
    # Execute filters sequentially
    # Return filtered VCF path and statistics
```

### BCFtools Command Builder
```python
class BCFtoolsFilterBuilder:
    def __init__(self, mode: str, assay: str):
        self.mode = mode
        self.assay = assay
        self.commands = []
        
    def add_filter(self, filter_id: str, params: dict):
        """Add appropriate bcftools command based on filter type"""
        
    def build_pipeline(self) -> List[str]:
        """Return ordered list of bcftools commands"""
```

---

## Integration with Arti

### API Handoff
```typescript
// After filtering completion
const handleSendToArti = async () => {
  const response = await fetch('/api/v1/variants/annotate', {
    method: 'POST',
    body: JSON.stringify({
      vcf_path: filteredVcfPath,
      case_uid: generateCaseId(),
      cancer_type: getCancerTypeFromMode(mode),
      analysis_type: mode
    })
  });
  
  if (response.ok) {
    showArtiPrompt();
  }
};

// Prompt component
const ArtiPrompt = () => (
  <Modal>
    <h2>Technical filtering complete!</h2>
    <p>{variantCounts.filtered} variants ready for clinical interpretation</p>
    <Button onClick={navigateToArti}>Go to Arti?</Button>
  </Modal>
);
```

---

## Implementation Timeline

### Week 1: Core Infrastructure
1. Set up tech_filtering module structure
2. Create Zustand store and type definitions
3. Build basic UI layout with mode switching
4. Implement filter controls (sliders, checkboxes)

### Week 2: Backend Integration
1. Create FastAPI endpoints for filtering
2. Implement bcftools command builder
3. Add file handling and temporary storage
4. Connect frontend to backend

### Week 3: Polish & Integration
1. Mode-specific styling and themes
2. Variant count tracking
3. Arti integration and handoff
4. Testing and validation

---

## File Structure
```
src/
├── tech_filtering/
│   ├── components/
│   │   ├── TechFilteringPage.tsx
│   │   ├── FilterPanel.tsx
│   │   ├── FilterControl.tsx
│   │   ├── ModeSelector.tsx
│   │   ├── VariantCounter.tsx
│   │   └── ArtiHandoff.tsx
│   ├── store/
│   │   └── filteringStore.ts
│   ├── types/
│   │   └── filtering.types.ts
│   ├── utils/
│   │   ├── filterDefaults.ts
│   │   └── modeConfigs.ts
│   └── styles/
│       ├── tumor-only.css
│       └── tumor-normal.css
├── assay_configs/
│   ├── reference_files/
│   │   ├── genome_specific/
│   │   │   └── grch38/
│   │   └── assay_specific/
│   │       └── default_assay/
│   └── configs/
│       └── default_assay.yaml
└── annotation_engine/
    └── api/
        └── routers/
            └── tech_filtering.py
```

This specification provides a clean, modern interface for technical filtering that seamlessly integrates with Arti while maintaining clear separation of concerns.