# Arti Clinical Interpretation UI Specification

> Generated: 2025-01-19  
> Based on: Complete codebase analysis including Phase 3A database, API endpoints, and tech filtering module

## Executive Summary

This document specifies the comprehensive user interface for Arti's main clinical variant interpretation application. The UI integrates with:
- Technical filtering pre-processor (completed)
- Phase 3A database with 21 tables
- Comprehensive canned text system (8 types)
- Multi-guideline tiering engine (OncoKB, CGC/VICC, AMP/ASCO)
- Advanced evidence aggregation from multiple knowledge bases

## UI Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Header & Navigation                       │
├─────────────────┬───────────────────────────┬──────────────────┤
│   Variant List  │   Variant Detail View     │  Interpretation  │
│   (Left Panel)  │   (Center Panel)          │  Tools (Right)   │
├─────────────────┴───────────────────────────┴──────────────────┤
│                        Status Bar & Actions                      │
└─────────────────────────────────────────────────────────────────┘
```

## 1. Core Layout Components

### 1.1 Header Section

#### Case Information Banner
```jsx
<CaseInfoBanner>
  <PatientInfo>
    - Patient UID: {patientUID}
    - Case ID: {caseID} [Required]
    - Status: {In Progress | Review | Signed Out}
  </PatientInfo>
  
  <ClinicalContext>
    - Cancer Type: {oncotreeCode} - {displayName} [Required]
    - Analysis Mode: {Tumor-Only | Tumor-Normal}
    - Specimen: {FFPE | Fresh Frozen | Blood}
    - Tumor Purity: {0-100%}
  </ClinicalContext>
  
  <Actions>
    - Save Progress
    - Export Case
    - Sign Out
  </Actions>
</CaseInfoBanner>
```

#### Navigation Tabs
- **Overview**: Dashboard with metrics and quick actions
- **Variants**: Main interpretation workspace
- **Evidence**: Knowledge base explorer
- **Reports**: Generation and history
- **Analytics**: Quality metrics and insights
- **Settings**: User preferences and configurations

### 1.2 User Context Bar
- Current user: {name} ({role})
- Permission level indicator
- Notification icon with count
- Quick case switcher dropdown
- Help/documentation link

## 2. Dashboard/Overview Page

### 2.1 Key Metrics Cards
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Total      │  Tier I     │  Tier II    │  Progress   │
│  Variants   │  Actionable │  Potential  │             │
│    487      │     3       │     12      │  85/487     │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### 2.2 Quick Actions
- 📤 Upload New VCF (links to tech filtering)
- 📝 Resume Recent Case
- 📊 Generate Report
- 💾 Export Data
- 🔄 Refresh Knowledge Bases

### 2.3 Recent Activity Feed
```
- ✅ BRAF p.V600E interpretation approved (2 min ago)
- 📝 TP53 tier changed from III to II (15 min ago)
- 🔄 OncoKB database updated to v3.14 (1 hour ago)
- 📋 Case CASE_001 ready for review (2 hours ago)
```

## 3. Main Variant Interpretation Workspace

### 3.1 Left Panel - Variant List

#### Filterable/Sortable Table
| Gene | Variant | Tier | VAF | Depth | Status |
|------|---------|------|-----|-------|---------|
| BRAF | p.V600E | I-A | 45% | 250x | ✅ Reviewed |
| TP53 | p.R273H | II-C | 38% | 180x | 🔄 In Progress |
| KRAS | p.G12D | I-A | 12% | 320x | ⚠️ Needs Review |

#### Filter Controls
- **By Tier**: [ ] I [ ] II [ ] III [ ] IV
- **By Status**: [ ] Reviewed [ ] In Progress [ ] Flagged
- **By Gene**: Search or multi-select
- **By Evidence**: [ ] FDA Approved [ ] Clinical Trials [ ] Preclinical
- **Custom Filters**: VAF range, depth threshold, consequence type

### 3.2 Center Panel - Variant Detail View

#### 3.2.1 Genomic Information Section
```
Gene: BRAF (ENSG00000157764) [🔗 GeneCards] [🔗 COSMIC]
Position: chr7:140,753,336 (GRCh38)
HGVS:
  - Genomic: NC_000007.14:g.140753336A>T
  - Coding: NM_004333.6:c.1799T>A
  - Protein: NP_004324.2:p.Val600Glu
Transcript: ENST00000646891 (canonical)
Consequence: Missense variant
Exon: 15/18
```

#### 3.2.2 Functional Predictions
```
┌─────────────────────────────────────────────────┐
│ Pathogenicity Predictions                       │
├─────────────────┬───────────────┬──────────────┤
│ AlphaMissense   │ Pathogenic    │ Score: 0.98  │
│ REVEL          │ Pathogenic    │ Score: 0.95  │
│ BayesDel       │ Damaging      │ Score: 0.89  │
│ SIFT           │ Deleterious   │ Score: 0.00  │
│ PolyPhen-2     │ Prob. Damaging│ Score: 1.00  │
└─────────────────┴───────────────┴──────────────┘

Conservation Scores:
- GERP++: 5.29 (highly conserved)
- PhyloP100way: 7.536
- PhastCons100way: 1.000
```

#### 3.2.3 Population Frequencies
```
Database         | Overall AF | Popmax AF | Population
-----------------|------------|-----------|------------
gnomAD Exomes    | 0.00001    | 0.00003   | African
gnomAD Genomes   | Not found  | -         | -
ExAC             | 0.00002    | 0.00004   | African
Local Database   | 0.00      | -         | -
```

#### 3.2.4 Clinical Evidence
```
ClinVar:
- Classification: Pathogenic (5 stars)
- Review Status: Expert panel reviewed
- Conditions: Melanoma, Colorectal cancer, NSCLC

OncoKB:
- Level: 1 (FDA-approved biomarker)
- Drugs: Vemurafenib, Dabrafenib, Encorafenib
- Indications: Melanoma (Level 1), CRC (Level 3A)

CIViC:
- Evidence Items: 47
- Clinical Significance: Predictive
- Evidence Direction: Supports

COSMIC:
- Hotspot: Yes (Tier 1)
- Cancer Types: Melanoma (45%), Thyroid (40%), CRC (10%)
- Sample Count: 12,847
```

#### 3.2.5 Tier Assignment
```
Guideline         | Tier  | Confidence | Rules Fired
------------------|-------|------------|-------------
OncoKB           | 1     | High       | FDA-approved
CGC/VICC         | I-A   | High       | Biomarker match
AMP/ASCO 2017    | I-A   | High       | Strong evidence

[Override Tier] [View Rule Details] [History]
```

### 3.3 Right Panel - Interpretation Tools

#### 3.3.1 Canned Text Selector
```
Text Type: [Variant Dx Interpretation ▼]

Available Templates:
┌─────────────────────────────────────────┐
│ ✓ BRAF V600E Melanoma Standard         │
│   BRAF V600E NSCLC                     │
│   BRAF V600E Colorectal                │
│   Custom Template...                    │
└─────────────────────────────────────────┘

Preview:
┌─────────────────────────────────────────┐
│ The BRAF p.V600E (c.1799T>A) missense │
│ variant is a well-characterized        │
│ oncogenic driver mutation found in     │
│ approximately 50% of melanomas...      │
│                                        │
│ [Edit] [Apply] [Save as Template]     │
└─────────────────────────────────────────┘
```

#### 3.3.2 Evidence Summary
```
Key Evidence Points:
✓ FDA-approved targeted therapy available
✓ Level 1 evidence in patient's cancer type
✓ Absent from population databases
✓ Functional studies confirm oncogenicity
⚠️ Consider resistance mechanisms

Supporting Citations: [12]
Conflicting Evidence: [0]
```

#### 3.3.3 Clinical Actions
```
[✓ Mark as Reviewed]
[Approve Tier Assignment]
[Add Clinical Note]
[Flag for Discussion]
[Request Second Review]

Sign-off Status:
- Technical Review: ✅ Complete
- Clinical Review: ⏳ Pending
- Final Sign-off: ⏹️ Not Started
```

## 4. Evidence Explorer

### 4.1 Knowledge Base Dashboard
```
Knowledge Base    | Version | Last Updated | Coverage
------------------|---------|--------------|----------
OncoKB           | v3.14   | 2 hours ago  | 95%
ClinVar          | 2025.01 | 1 day ago    | 98%
COSMIC           | v98     | 1 week ago   | 92%
CIViC            | 2025.01 | 3 days ago   | 88%
gnomAD           | v4.0    | 1 month ago  | 100%

[Refresh All] [Check for Updates] [View Logs]
```

### 4.2 Evidence Search Interface
- Search by: Gene | Variant | Drug | Clinical Trial
- Filters: Evidence Level | Cancer Type | Therapy Type
- Results displayed in sortable table with preview

## 5. Report Generation Module

### 5.1 Report Builder Interface
```
Template: [Comprehensive Clinical Report ▼]

Sections:
☑ Executive Summary
☑ Tiered Variant List
☑ Variant Interpretations
☑ Pertinent Negatives
☑ Technical Summary
☐ Appendix - Full Evidence
☐ Appendix - Methods

Format: [PDF] [Word] [JSON]

[Preview Report] [Generate] [Save Template]
```

### 5.2 Report Customization
- Logo upload
- Header/footer customization
- Font and color schemes
- Section reordering
- Custom disclaimers

## 6. Advanced Features

### 6.1 Batch Operations
- Multi-select variants from list
- Actions: Bulk approve | Export selected | Apply template | Change tier
- Progress indicator for batch processing

### 6.2 Collaboration Features
```
Case Sharing:
- Share with: [Select users/groups]
- Permission level: [View | Comment | Edit]
- Expiration: [Never | 7 days | 30 days]

Comments & Discussion:
- Variant-specific comment threads
- @mentions for notifications
- Attachments support
- Resolution tracking
```

### 6.3 Audit Trail Viewer
```
Timestamp         | User    | Action              | Details
------------------|---------|---------------------|----------
2025-01-19 14:32 | jsmith  | Tier changed       | II → I
2025-01-19 14:30 | jsmith  | Interpretation edit| Added FDA note
2025-01-19 14:15 | system  | Auto-annotation    | OncoKB Level 1
```

## 7. Technical Implementation

### 7.1 State Management
```typescript
interface AppState {
  case: CaseInfo;
  variants: Variant[];
  selectedVariant: Variant | null;
  filters: FilterState;
  user: UserInfo;
  ui: UIState;
}
```

### 7.2 API Integration
- RESTful endpoints from Phase 3B API
- WebSocket for real-time updates
- Optimistic UI updates
- Offline queue for actions

### 7.3 Performance Requirements
- Initial load: < 2 seconds
- Variant switching: < 100ms
- Search results: < 500ms
- Report generation: < 10 seconds

### 7.4 Security Requirements
- JWT authentication
- Role-based access control
- PHI data encryption
- Audit logging for all actions
- Session timeout handling

## 8. Responsive Design

### Desktop (1920x1080)
- Full three-panel layout
- All features accessible
- Keyboard shortcuts enabled

### Tablet (1024x768)
- Two-panel layout (list + detail)
- Touch-optimized controls
- Interpretation tools in modal

### Mobile (375x812)
- Single panel with navigation
- Essential features only
- Read-only report viewing

## 9. Integration Points

### 9.1 Tech Filtering Module
- Seamless handoff of filtered VCFs
- Metadata preservation
- Job status tracking

### 9.2 External Systems
- LIMS integration via API
- EMR data export
- Cloud storage support
- Webhook notifications

## 10. Future Enhancements

- AI-assisted interpretation suggestions
- Real-time collaborative editing
- Voice dictation for notes
- Advanced visualization tools
- Automated literature monitoring
- Integration with clinical trials databases

---

This UI specification provides a comprehensive blueprint for Arti's clinical interpretation interface, incorporating all advanced features from the codebase while maintaining usability and clinical workflow efficiency.