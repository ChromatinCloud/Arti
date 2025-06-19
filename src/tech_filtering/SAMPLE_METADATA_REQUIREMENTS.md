# Sample Metadata Requirements for Technical Filtering

## Current State
The technical filtering frontend currently captures minimal metadata:
- **Analysis Mode**: tumor-only or tumor-normal
- **Assay**: default_assay (configurable)
- **Input VCF**: File path

## Missing Critical Metadata

### Sample Identification
- **Sample ID**: Unique identifier for the tumor sample
- **Normal Sample ID**: For tumor-normal mode
- **Patient/Case ID**: Links to clinical case
- **Accession Number**: Laboratory tracking ID

### Clinical Context
- **Cancer Type**: Required for Arti interpretation
  - Should use OncoTree codes (e.g., SKCM for melanoma)
  - Critical for tier assignment and therapy matching
- **Primary/Metastatic**: Sample site designation
- **Specimen Type**: FFPE, fresh frozen, blood, etc.
- **Collection Date**: For sample age considerations

### Technical Parameters
- **Sequencer**: Platform used (e.g., Illumina NextSeq)
- **Capture Kit**: Specific assay version
- **Reference Genome**: grch37 or grch38
- **Variant Caller**: Tool and version (e.g., Mutect2 v4.2)
- **Tumor Purity**: Estimated tumor cell fraction
- **Coverage Metrics**: Mean coverage depth

### Quality Control
- **Sample QC Status**: Pass/Fail/Conditional
- **DNA Quality Metrics**: DIN score, concentration
- **Library Prep Date**: For batch tracking
- **Run ID**: Sequencing run identifier

## Recommended Frontend Additions

### Minimal Required Fields
```typescript
interface SampleMetadata {
  // Identification
  sampleId: string;
  patientId: string;
  
  // Clinical
  cancerType: string;  // OncoTree code
  specimenType: 'FFPE' | 'FreshFrozen' | 'Blood' | 'Other';
  
  // Technical
  genomeBuild: 'grch37' | 'grch38';
  tumorPurity?: number;  // 0-1 scale
  
  // For tumor-normal mode
  normalSampleId?: string;
}
```

### Enhanced Metadata (Phase 2)
```typescript
interface EnhancedMetadata extends SampleMetadata {
  // Clinical details
  primarySite: string;
  metastaticSite?: string;
  priorTherapies?: string[];
  
  // Technical details
  sequencer: string;
  captureKit: string;
  variantCaller: string;
  meanCoverage: number;
  
  // Quality metrics
  dinScore?: number;
  libraryPrepDate: Date;
  sequencingDate: Date;
  
  // Tracking
  accessionNumber: string;
  runId: string;
  notes?: string;
}
```

## Implementation Recommendations

### 1. Update Frontend Form
Add a collapsible "Sample Information" section with:
- Required fields marked with asterisk
- Dropdown for OncoTree cancer types
- Validation for required fields
- Auto-population from previous runs

### 2. Modify API Request
Include metadata in the filtering request:
```typescript
interface FilteringRequest {
  mode: AnalysisMode;
  assay: string;
  inputVcf: string;
  filters: Record<string, any>;
  metadata: SampleMetadata;  // NEW
}
```

### 3. Pass to Arti
When sending to Arti, include:
```typescript
const artiRequest = {
  vcf_path: filteredVcfPath,
  case_uid: metadata.patientId,
  sample_id: metadata.sampleId,
  cancer_type: metadata.cancerType,
  analysis_type: mode,
  tumor_purity: metadata.tumorPurity,
  genome_build: metadata.genomeBuild
};
```

### 4. VCF Header Integration
Consider adding metadata to VCF header:
```
##SAMPLE=<ID=TUMOR,SampleID=TST001,PatientID=PT001,CancerType=SKCM,TumorPurity=0.75>
##SAMPLE=<ID=NORMAL,SampleID=NST001,PatientID=PT001>
##reference=GRCh38
##source=TechFiltering_v1.0
```

## Benefits of Complete Metadata

1. **Traceability**: Full audit trail from sequencing to interpretation
2. **Quality Control**: Identify batch effects and quality issues
3. **Clinical Context**: Proper tier assignment and therapy matching
4. **Reproducibility**: Re-run analysis with same parameters
5. **Integration**: Seamless handoff to downstream tools

## Priority Implementation

### Phase 1 (Current Sprint)
- Add minimal required fields to frontend
- Validate cancer type against OncoTree
- Pass metadata through to Arti

### Phase 2 (Future)
- Enhanced metadata collection
- VCF header integration
- Metadata persistence and recall
- Integration with LIMS