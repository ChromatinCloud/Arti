// Type definitions for technical filtering module

export type AnalysisMode = 'tumor-only' | 'tumor-normal';
export type FilterType = 'slider' | 'checkbox' | 'range' | 'multiselect';

export interface FilterDefinition {
  id: string;
  name: string;
  type: FilterType;
  vcfFields: string[];
  description: string;
  enabled: boolean;
  command?: string;
}

export interface SliderFilter extends FilterDefinition {
  type: 'slider';
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
}

export interface CheckboxFilter extends FilterDefinition {
  type: 'checkbox';
  value: boolean;
}

export interface RangeFilter extends FilterDefinition {
  type: 'range';
  value: [number, number];
  min: number;
  max: number;
  step?: number;
}

export interface MultiselectFilter extends FilterDefinition {
  type: 'multiselect';
  value: string[];
  options: string[];
}

export type Filter = SliderFilter | CheckboxFilter | RangeFilter | MultiselectFilter;

export interface FilterGroup {
  id: string;
  name: string;
  filters: Filter[];
  expanded: boolean;
}

export interface ReferenceFiles {
  panelBed: string;
  blacklistRef: string;
  blacklistAssay: string;
  gnomadFreq: string;
}

export interface AssayConfig {
  name: string;
  version: string;
  genomeBuild: string;
  description: string;
  referenceFiles: ReferenceFiles;
}

export interface VariantCounts {
  input: number;
  filtered: number;
  byFilter?: Record<string, number>;
}

export interface FilteringState {
  mode: AnalysisMode;
  assay: string;
  inputVcf: string;
  outputVcf: string | null;
  filters: Record<string, Filter>;
  filterGroups: FilterGroup[];
  variantCounts: VariantCounts;
  isProcessing: boolean;
  error: string | null;
}

export interface SampleMetadata {
  patientUID?: string;
  caseID?: string;
  oncotreeCode?: string;
  tumorPurity?: number;
  specimenType?: string;
}

export interface FilteringRequest {
  mode: AnalysisMode;
  assay: string;
  inputVcf: string;
  filters: Record<string, any>;
  metadata?: SampleMetadata;
}

export interface FilteringResponse {
  success: boolean;
  outputVcf?: string;
  variantCounts?: VariantCounts;
  processingTime?: number;
  error?: string;
}

export interface PresetConfig {
  name: string;
  description: string;
  overrides: Record<string, any>;
}