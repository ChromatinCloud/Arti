# Frontend API Schema Blueprint

## Overview

This document defines API schemas optimized for frontend consumption based on patterns from leading clinical tools (OncoKB, PCGR, CIViC, Scout, cBioPortal). We adopt **UI-first data structures** with **progressive loading** and **real-time updates**.

## Frontend-Specific API Design

### Core Principles (Based on Industry Leaders)

1. **UI-First Schemas** (cBioPortal pattern): Data shaped for direct component consumption
2. **Progressive Loading** (OncoKB pattern): Summary → Details → Complete data
3. **Real-Time Updates** (CIViC pattern): WebSocket events for live collaboration
4. **Optimistic Updates** (Scout pattern): Immediate UI feedback with rollback capability

## API Response Structures

### 1. Case Overview Response

Following **PCGR's** report structure with **Scout's** case management:

```typescript
interface CaseOverviewResponse {
  // Basic case information
  case: {
    case_uid: string;
    patient_uid: string;
    status: CaseStatus;
    created_at: string;
    last_updated: string;
    
    // Clinical context
    cancer_type: string;
    oncotree_id: string;
    tissue_type: string;
    diagnosis: string;
    
    // Technical metadata
    vcf_file: string;
    analysis_date: string;
    kb_versions: KBVersionSummary;
  };
  
  // Analysis summary for dashboard
  summary: {
    total_variants: number;
    variants_by_tier: {
      tier_i: number;
      tier_ii: number;
      tier_iii: number;
      tier_iv: number;
    };
    actionable_variants: number;
    incidental_findings: number;
    
    // Quality metrics
    mean_depth: number;
    variants_passing_qc: number;
    analysis_completion: number; // percentage
  };
  
  // Quick access to key variants
  featured_variants: VariantSummary[];
  
  // Biomarker summary
  biomarkers: {
    tmb: BiomarkerResult;
    msi: BiomarkerResult;
    hrd: BiomarkerResult;
    signatures: SignatureResult[];
  };
  
  // Review status
  review_status: {
    variants_reviewed: number;
    variants_interpreted: number;
    ready_for_signout: boolean;
    signed_out: boolean;
    signed_out_by?: string;
    signed_out_at?: string;
  };
}

interface VariantSummary {
  variant_id: string;
  gene_symbol: string;
  genomic_change: string;    // "chr17:7673803G>A"
  protein_change: string;    // "p.Arg273His"
  tier: TierAssignment;
  significance: ClinicalSignificance;
  confidence: number;
  actionable: boolean;
  evidence_count: number;
  interpretation_status: InterpretationStatus;
}
```

### 2. Variant List Response

Based on **Scout's** variant table optimization:

```typescript
interface VariantListResponse {
  // Pagination metadata
  pagination: {
    total: number;
    page: number;
    size: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  
  // Filter metadata
  filters_applied: VariantFilters;
  sort_config: {
    field: string;
    direction: 'asc' | 'desc';
  };
  
  // Optimized variant data for table display
  variants: VariantTableRow[];
  
  // Aggregations for filter UI
  aggregations: {
    genes: { gene: string; count: number }[];
    consequences: { consequence: string; count: number }[];
    tiers: { tier: string; count: number }[];
    evidence_sources: { source: string; count: number }[];
  };
  
  // Export metadata
  export_available: boolean;
  total_export_size: number;
}

interface VariantTableRow {
  // Core identifiers
  variant_id: string;
  analysis_id: string;
  
  // Genomic information (formatted for display)
  gene_symbol: string;
  chromosome: string;
  position: number;
  ref_alt: string;           // "G>A"
  genomic_coord: string;     // "chr17:7673803"
  hgvsc: string;
  hgvsp: string;
  consequence: string;
  consequence_display: string; // Human-friendly version
  
  // Clinical interpretation (pre-computed for performance)
  tier_assignment: {
    amp_acmg: TierResult;
    cgc_vicc: TierResult;
    oncokb: TierResult;
  };
  
  // Evidence summary (for quick scanning)
  evidence_summary: {
    sources: string[];        // ["OncoKB", "ClinVar", "CIViC"]
    strength_indicator: 'strong' | 'moderate' | 'supporting' | 'conflicting';
    total_citations: number;
    fda_approved: boolean;
  };
  
  // Actionability (high-priority for clinicians)
  therapeutic_implications: {
    has_therapy: boolean;
    therapy_count: number;
    approval_status: 'fda' | 'guideline' | 'clinical_trial' | 'preclinical';
    resistance_associated: boolean;
  };
  
  // Technical quality (for filtering)
  technical_metrics: {
    depth: number;
    vaf: number;
    quality_score: number;
    filter_status: string;
  };
  
  // Review tracking
  review_metadata: {
    interpretation_status: InterpretationStatus;
    selected_interpretation_id?: string;
    reviewed_by?: string;
    review_timestamp?: string;
    has_notes: boolean;
  };
  
  // UI state helpers
  ui_metadata: {
    is_actionable: boolean;
    is_incidental: boolean;
    needs_attention: boolean;
    color_code: string;       // For consistent theming
    priority_score: number;   // For default sorting
  };
}

interface TierResult {
  tier: string;
  confidence: number;
  rules_summary: string;     // "PS1, PM1, PP3"
  rule_count: number;
}
```

### 3. Variant Detail Response

Following **OncoKB's** comprehensive evidence display:

```typescript
interface VariantDetailResponse {
  // Complete variant information
  variant: {
    // Basic genomic data
    variant_id: string;
    chromosome: string;
    position: number;
    reference: string;
    alternate: string;
    variant_type: string;
    
    // Gene and transcript information
    gene_symbol: string;
    gene_id: string;
    transcript_id: string;
    transcript_biotype: string;
    canonical_transcript: boolean;
    
    // HGVS notation
    hgvsc: string;
    hgvsp: string;
    hgvsg: string;
    
    // Consequence information
    consequence: string[];
    impact: string;
    exon: string;
    intron: string;
    
    // Technical details
    vcf_info: Record<string, any>;
    quality_metrics: QualityMetrics;
    
    // Population context
    allele_frequency: {
      gnomad: PopulationFrequency;
      exac: PopulationFrequency;
      local?: PopulationFrequency;
    };
  };
  
  // Knowledge base annotations (structured for UI consumption)
  knowledge_base_evidence: {
    oncokb: OncoKBEvidence;
    clinvar: ClinVarEvidence;
    civic: CivicEvidence;
    cosmic: CosmicEvidence;
    hotspots: HotspotEvidence;
  };
  
  // Computational predictions (organized by category)
  computational_predictions: {
    deleteriousness: {
      sift: PredictionScore;
      polyphen2: PredictionScore;
      mutation_taster: PredictionScore;
      fathmm: PredictionScore;
    };
    conservation: {
      phylop: ConservationScore;
      phastcons: ConservationScore;
      gerp: ConservationScore;
    };
    pathogenicity: {
      cadd: number;
      revel: number;
      primateai: number;
      alphamissense: number;
    };
    splicing: {
      spliceai: SpliceScore;
      maxentscan: SpliceScore;
      dbscsnv: SpliceScore;
    };
  };
  
  // Clinical interpretation results
  tiering_results: {
    amp_acmg: DetailedTieringResult;
    cgc_vicc: DetailedTieringResult;
    oncokb: DetailedTieringResult;
  };
  
  // Available interpretations
  interpretations: {
    existing: ExistingInterpretation[];
    suggested: SuggestedInterpretation[];
    selected?: SelectedInterpretation;
  };
  
  // Generated text summaries
  canned_text: {
    general_gene_info: CannedTextBlock;
    gene_dx_interpretation: CannedTextBlock;
    general_variant_info: CannedTextBlock;
    variant_dx_interpretation: CannedTextBlock;
    incidental_findings?: CannedTextBlock;
    technical_comments: CannedTextBlock;
  };
  
  // Literature and citations
  literature: {
    primary_citations: Citation[];
    review_articles: Citation[];
    clinical_trials: ClinicalTrial[];
    functional_studies: FunctionalStudy[];
  };
  
  // Similar variants (for context)
  related_variants: RelatedVariant[];
}

interface DetailedTieringResult {
  tier_assigned: string;
  confidence_score: number;
  
  // Rule explanations (formatted for UI)
  rules_invoked: RuleExplanation[];
  
  // Evidence summary
  evidence_summary: {
    supporting_count: number;
    conflicting_count: number;
    total_weight: number;
    confidence_factors: string[];
  };
  
  // Reasoning chain (for transparency)
  reasoning_chain: ReasoningStep[];
}

interface RuleExplanation {
  rule_id: string;
  rule_name: string;
  category: string;          // "Pathogenic Strong"
  weight_applied: number;
  evidence_strength: string;
  
  // Why this rule fired (human-readable)
  explanation: {
    summary: string;         // "Same amino acid change as pathogenic variant"
    details: string;         // "p.Arg273His reported as Pathogenic in ClinVar..."
    evidence_sources: EvidenceSource[];
  };
  
  // UI display helpers
  display: {
    color: string;
    icon: string;
    priority: number;
  };
}
```

### 4. Interpretation Management Responses

Based on **CIViC's** curation workflows:

```typescript
interface InterpretationOptionsResponse {
  variant_id: string;
  cancer_type: string;
  guideline_framework: string;
  
  // Existing interpretations (sorted by relevance)
  existing_interpretations: ExistingInterpretation[];
  
  // AI-suggested interpretations
  suggested_interpretations: SuggestedInterpretation[];
  
  // Template options
  canned_templates: InterpretationTemplate[];
  
  // Creation options
  creation_options: {
    can_create_new: boolean;
    can_modify_existing: boolean;
    required_fields: string[];
    validation_rules: ValidationRule[];
  };
}

interface ExistingInterpretation {
  interpretation_id: string;
  interpretation_text: string;
  clinical_significance: string;
  therapeutic_implications: string;
  
  // Relevance scoring
  match_score: number;       // 0-1, how well it fits this case
  similarity_factors: string[]; // What makes it similar
  
  // Usage metadata
  usage_count: number;
  last_used: string;
  success_rate: number;      // How often it's been accepted
  
  // Quality indicators
  confidence_level: string;
  evidence_level: string;
  created_by: string;
  review_status: string;
  
  // Customization needs
  requires_modification: boolean;
  suggested_changes: string[];
}

interface SuggestedInterpretation {
  suggestion_id: string;
  interpretation_text: string;
  confidence: number;
  
  // Generation metadata
  based_on: {
    tier_result: TierResult;
    evidence_sources: string[];
    similar_cases: string[];
  };
  
  // Customization options
  editable_sections: string[];
  alternative_phrasings: Record<string, string[]>;
}
```

### 5. Real-Time Update Schemas

Following **CIViC's** collaborative editing patterns:

```typescript
// WebSocket message schemas
interface WebSocketMessage {
  type: WSMessageType;
  timestamp: string;
  user_id: string;
  session_id: string;
  data: any;
}

type WSMessageType = 
  | 'analysis_progress'
  | 'interpretation_update'
  | 'case_status_change'
  | 'user_presence'
  | 'conflict_detection'
  | 'system_notification';

interface AnalysisProgressMessage {
  type: 'analysis_progress';
  data: {
    analysis_id: string;
    step: string;           // "vep_annotation", "kb_lookup", "tiering"
    progress: number;       // 0-100
    estimated_completion: string;
    current_variant: number;
    total_variants: number;
    errors: ErrorReport[];
  };
}

interface InterpretationUpdateMessage {
  type: 'interpretation_update';
  data: {
    variant_id: string;
    interpretation_id: string;
    change_type: 'created' | 'modified' | 'selected' | 'deleted';
    changes: Record<string, any>;
    updated_by: string;
  };
}

interface UserPresenceMessage {
  type: 'user_presence';
  data: {
    case_uid: string;
    active_users: {
      user_id: string;
      user_name: string;
      current_variant?: string;
      activity: 'viewing' | 'editing' | 'reviewing';
      last_activity: string;
    }[];
  };
}
```

### 6. Export and Reporting Schemas

Based on **PCGR's** multi-format outputs:

```typescript
interface ExportRequestSchema {
  case_uid: string;
  format: 'json' | 'excel' | 'pdf' | 'html';
  
  // Content selection
  include: {
    variant_summary: boolean;
    detailed_evidence: boolean;
    interpretations: boolean;
    biomarkers: boolean;
    technical_details: boolean;
    audit_trail: boolean;
  };
  
  // Filtering options
  filters: {
    tiers: string[];
    significance: string[];
    actionable_only: boolean;
    reviewed_only: boolean;
  };
  
  // Customization
  customization: {
    institution_name?: string;
    report_title?: string;
    include_logo: boolean;
    footer_text?: string;
    
    // Format-specific options
    excel_options?: {
      separate_sheets: boolean;
      include_formulas: boolean;
    };
    
    pdf_options?: {
      include_plots: boolean;
      page_layout: 'portrait' | 'landscape';
      include_appendices: boolean;
    };
  };
}

interface ExportStatusResponse {
  export_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  estimated_completion?: string;
  
  // When completed
  download_url?: string;
  file_size?: number;
  expires_at?: string;
  
  // If failed
  error_message?: string;
  retry_available: boolean;
}
```

## Performance Optimizations

### 1. Progressive Loading Strategy

Following **cBioPortal's** data loading patterns:

```typescript
interface ProgressiveLoadingEndpoints {
  // Level 1: Immediate UI load
  '/api/cases/{case_uid}/summary': CaseSummaryResponse;
  
  // Level 2: Primary data table
  '/api/cases/{case_uid}/variants/list': VariantListResponse;
  
  // Level 3: Detailed view (on-demand)
  '/api/variants/{variant_id}/details': VariantDetailResponse;
  
  // Level 4: Heavy computations (background)
  '/api/variants/{variant_id}/literature': LiteratureResponse;
  '/api/variants/{variant_id}/similar': SimilarVariantsResponse;
}

interface CaseSummaryResponse {
  // Minimal data for immediate page load
  case_uid: string;
  status: string;
  variant_count: number;
  key_findings: string[];
  
  // Precomputed aggregations
  tier_distribution: Record<string, number>;
  actionable_count: number;
  
  // UI state
  last_viewed_variant?: string;
  user_bookmarks: string[];
}
```

### 2. Caching Strategy

Based on **OncoKB's** API optimization:

```typescript
interface CacheHeaders {
  // Static reference data (long cache)
  '/api/genes/*': {
    'Cache-Control': 'public, max-age=86400'; // 24 hours
    'ETag': string;
  };
  
  // Dynamic interpretation data (short cache)
  '/api/variants/*/interpretations': {
    'Cache-Control': 'private, max-age=300'; // 5 minutes
    'ETag': string;
  };
  
  // User-specific data (no cache)
  '/api/cases/*/review-status': {
    'Cache-Control': 'no-cache, no-store';
  };
}

interface ClientSideCaching {
  // Local storage for user preferences
  userPreferences: {
    storage: 'localStorage';
    ttl: 'indefinite';
    keys: ['filter_defaults', 'column_preferences', 'view_settings'];
  };
  
  // Session storage for temporary data
  sessionData: {
    storage: 'sessionStorage';
    keys: ['current_filters', 'scroll_position', 'expanded_sections'];
  };
  
  // Memory cache for API responses
  apiCache: {
    strategy: 'lru';
    maxEntries: 100;
    ttl: 300000; // 5 minutes
  };
}
```

### 3. Error Handling Schemas

Following clinical application standards:

```typescript
interface ErrorResponse {
  error: {
    code: string;           // "VARIANT_NOT_FOUND"
    message: string;        // User-friendly message
    details?: any;          // Technical details for debugging
    
    // Error classification
    category: 'client' | 'server' | 'network' | 'validation';
    severity: 'low' | 'medium' | 'high' | 'critical';
    
    // Recovery options
    recoverable: boolean;
    retry_after?: number;   // Seconds to wait before retry
    alternative_actions?: string[];
    
    // Context
    request_id: string;
    timestamp: string;
    user_id?: string;
    session_id?: string;
  };
  
  // Partial data (if available)
  partial_data?: any;
  
  // UI guidance
  ui_guidance: {
    show_error_boundary: boolean;
    allow_retry: boolean;
    fallback_content?: any;
    user_actions: string[];
  };
}

interface ValidationErrorResponse {
  error: {
    code: 'VALIDATION_ERROR';
    message: string;
    
    // Field-specific errors
    field_errors: {
      field: string;
      message: string;
      code: string;
    }[];
    
    // Global validation errors
    global_errors: {
      message: string;
      code: string;
    }[];
  };
}
```

This frontend API schema provides optimized data structures for clinical variant annotation interfaces, following proven patterns from leading genomics tools while ensuring performance, usability, and real-time collaboration capabilities.