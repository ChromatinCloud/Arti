export interface Variant {
  variantId: string;
  chromosome: string;
  position: number;
  reference: string;
  alternate: string;
  gene: Gene;
  hgvs: {
    genomic: string;
    coding: string;
    protein: string;
  };
  consequence: string[];
  vaf: number;
  depth: number;
  quality: number;
}

export interface Gene {
  symbol: string;
  ensemblId: string;
  name: string;
  strand: string;
  transcriptId: string;
}

export interface Annotation {
  source: 'OncoKB' | 'ClinVar' | 'COSMIC' | 'CIViC' | 'gnomAD' | 'Functional' | 'Conservation';
  type: 'therapeutic' | 'pathogenicity' | 'frequency' | 'functional' | 'conservation';
  data: any;
  confidence: number;
  version: string;
}

export interface RuleEvaluation {
  ruleId: string;
  ruleName: string;
  guideline: 'OncoKB' | 'CGC_VICC' | 'AMP_ASCO';
  fired: boolean;
  evidence: Evidence[];
  outcome: string;
  confidence: number;
  logic: string;
  impact: 'high' | 'medium' | 'low';
}

export interface Evidence {
  type: string;
  value: any;
  source: string;
  supporting: boolean;
}

export interface TierAssignment {
  guideline: 'OncoKB' | 'CGC_VICC' | 'AMP_ASCO';
  tier: string;
  confidence: number;
  justification: string;
  rules: string[];
}

export interface Interpretation {
  id: string;
  templateId: string;
  templateName: string;
  content: string;
  confidence: number;
  citations: Citation[];
  evidence: string[];
  diseaseContext?: string[];
  lastModified?: string;
  createdBy?: string;
  isCustom?: boolean;
}

export interface Citation {
  id: string;
  text: string;
  pmid?: string;
  doi?: string;
}

export interface Case {
  caseUid: string;
  patientUid: string;
  cancerType: string;
  oncotreeCode: string;
  specimenType?: string;
  tumorPurity?: number;
  analysisType: 'tumor_only' | 'tumor_normal';
  status: 'in_progress' | 'review' | 'signed_out';
}

export interface VariantWithFlow extends Variant {
  annotations: Annotation[];
  rulesEvaluated: RuleEvaluation[];
  tierAssignments: TierAssignment[];
  interpretations: Interpretation[];
  status: 'pending' | 'in_progress' | 'reviewed' | 'approved';
  reviewedBy?: string;
  reviewedAt?: Date;
}