import { VariantWithFlow } from '../types/variant.types';

export const mockVariants: VariantWithFlow[] = [
  {
    variantId: 'chr7:140753336:A>T',
    chromosome: 'chr7',
    position: 140753336,
    reference: 'A',
    alternate: 'T',
    gene: {
      symbol: 'BRAF',
      ensemblId: 'ENSG00000157764',
      name: 'B-Raf proto-oncogene',
      strand: '+',
      transcriptId: 'ENST00000646891'
    },
    hgvs: {
      genomic: 'NC_000007.14:g.140753336A>T',
      coding: 'NM_004333.6:c.1799T>A',
      protein: 'p.Val600Glu'
    },
    consequence: ['missense_variant'],
    vaf: 0.45,
    depth: 250,
    quality: 100,
    status: 'reviewed',
    annotations: [
      {
        source: 'OncoKB',
        type: 'therapeutic',
        data: {
          level: '1',
          drugs: ['Vemurafenib', 'Dabrafenib', 'Encorafenib'],
          cancerTypes: ['Melanoma', 'Colorectal Cancer', 'NSCLC'],
          fdaApproved: true
        },
        confidence: 0.99,
        version: 'v3.14'
      },
      {
        source: 'ClinVar',
        type: 'pathogenicity',
        data: {
          clinicalSignificance: 'Pathogenic',
          reviewStatus: '5 stars',
          conditions: ['Melanoma', 'Noonan syndrome']
        },
        confidence: 0.98,
        version: '2025.01'
      },
      {
        source: 'COSMIC',
        type: 'frequency',
        data: {
          hotspot: true,
          tier: 1,
          sampleCount: 12847,
          cancerTypeDistribution: {
            'Melanoma': 0.45,
            'Thyroid': 0.40,
            'Colorectal': 0.10
          }
        },
        confidence: 0.95,
        version: 'v98'
      },
      {
        source: 'Functional',
        type: 'functional',
        data: {
          alphaMissense: { score: 0.98, prediction: 'Pathogenic' },
          revel: { score: 0.95 },
          cadd: { score: 29.4 },
          conservation: { gerp: 5.29, phyloP: 7.536 }
        },
        confidence: 0.94,
        version: '2024.12'
      }
    ],
    rulesEvaluated: [
      {
        ruleId: 'ONCOKB_FDA_APPROVED',
        ruleName: 'FDA_APPROVED_SAME_CANCER',
        guideline: 'OncoKB',
        fired: true,
        evidence: [
          { type: 'annotation', value: 'Level 1', source: 'OncoKB', supporting: true },
          { type: 'cancer_match', value: 'Melanoma', source: 'Case', supporting: true }
        ],
        outcome: 'Level 1',
        confidence: 0.99,
        logic: 'IF variant.oncokb_level == "1" AND cancer_type IN approved_indications THEN Level 1',
        impact: 'high'
      },
      {
        ruleId: 'VICC_BIOMARKER_MATCH',
        ruleName: 'VICC_BIOMARKER_MATCH',
        guideline: 'CGC_VICC',
        fired: true,
        evidence: [
          { type: 'biomarker', value: 'BRAF V600E', source: 'OncoKB', supporting: true },
          { type: 'fda_approval', value: true, source: 'OncoKB', supporting: true }
        ],
        outcome: 'Tier I-A',
        confidence: 0.98,
        logic: 'IF is_biomarker(variant, cancer_type) AND has_fda_approval THEN Tier I-A',
        impact: 'high'
      }
    ],
    tierAssignments: [
      {
        guideline: 'OncoKB',
        tier: 'Level 1',
        confidence: 0.99,
        justification: 'FDA-approved biomarker in patient\'s cancer type',
        rules: ['ONCOKB_FDA_APPROVED']
      },
      {
        guideline: 'CGC_VICC',
        tier: 'Tier I-A',
        confidence: 0.98,
        justification: 'Biomarker with regulatory approval',
        rules: ['VICC_BIOMARKER_MATCH', 'ONCOGENICITY_SCORE']
      },
      {
        guideline: 'AMP_ASCO',
        tier: 'Tier I-A',
        confidence: 0.97,
        justification: 'Strong clinical significance with FDA approval',
        rules: ['AMP_STRONG_CLINICAL']
      }
    ],
    interpretations: [
      {
        id: 'interp_001',
        templateId: 'BRAF_V600E_MELANOMA',
        templateName: 'BRAF V600E - Melanoma Standard',
        content: `The BRAF p.V600E (c.1799T>A) missense variant is a well-characterized oncogenic driver mutation found in approximately 50% of melanomas. This variant results in constitutive activation of the MAPK signaling pathway.

This variant is an FDA-approved biomarker for targeted therapy with BRAF inhibitors (vemurafenib, dabrafenib, encorafenib) in combination with MEK inhibitors.`,
        confidence: 0.98,
        citations: [
          { id: '1', text: 'Chapman et al., NEJM 2011', pmid: '21639808' },
          { id: '2', text: 'Robert et al., NEJM 2015', pmid: '25399551' }
        ],
        evidence: ['OncoKB Level 1', 'ClinVar Pathogenic', 'COSMIC Hotspot'],
        diseaseContext: ['Melanoma', 'Skin Cancer'],
        lastModified: '2025-06-19T10:30:00Z',
        createdBy: 'Dr. Smith',
        isCustom: false
      },
      {
        id: 'interp_002',
        templateId: 'BRAF_V600E_COLORECTAL',
        templateName: 'BRAF V600E - Colorectal Context',
        content: `The BRAF p.V600E variant in colorectal cancer represents a distinct molecular subtype with poor prognosis. Unlike melanoma, BRAF V600E colorectal cancers show resistance to anti-EGFR therapy and require different treatment approaches.

Current evidence supports combination therapy with BRAF + MEK + EGFR inhibition (encorafenib + cetuximab + binimetinib) as FDA-approved treatment.`,
        confidence: 0.94,
        citations: [
          { id: '3', text: 'Kopetz et al., NEJM 2019', pmid: '31566309' },
          { id: '4', text: 'Tabernero et al., Lancet Oncol 2021', pmid: '33549177' }
        ],
        evidence: ['OncoKB Level 1', 'NCCN Guidelines', 'FDA Approved'],
        diseaseContext: ['Colorectal Cancer', 'Gastrointestinal Cancer'],
        lastModified: '2025-06-18T14:15:00Z',
        createdBy: 'Dr. Johnson',
        isCustom: false
      },
      {
        id: 'interp_003',
        templateId: 'BRAF_V600E_GENERAL',
        templateName: 'BRAF V600E - Pan-Cancer',
        content: `The BRAF p.V600E mutation is found across multiple cancer types and generally represents an oncogenic driver event. The therapeutic implications vary significantly by tumor type and require context-specific interpretation.

This variant should be evaluated in conjunction with tumor type, stage, and other molecular features to determine optimal treatment strategy.`,
        confidence: 0.85,
        citations: [
          { id: '5', text: 'Davies et al., Nature 2002', pmid: '12068308' },
          { id: '6', text: 'Planchard et al., Lancet Oncol 2016', pmid: '27283860' }
        ],
        evidence: ['OncoKB Level 1', 'COSMIC Hotspot', 'Literature Support'],
        diseaseContext: ['Pan-Cancer'],
        lastModified: '2025-06-17T09:45:00Z',
        createdBy: 'System',
        isCustom: false
      }
    ]
  },
  {
    variantId: 'chr17:7574003:G>A',
    chromosome: 'chr17',
    position: 7574003,
    reference: 'G',
    alternate: 'A',
    gene: {
      symbol: 'TP53',
      ensemblId: 'ENSG00000141510',
      name: 'Tumor protein p53',
      strand: '-',
      transcriptId: 'ENST00000269305'
    },
    hgvs: {
      genomic: 'NC_000017.11:g.7574003G>A',
      coding: 'NM_000546.6:c.818G>A',
      protein: 'p.Arg273His'
    },
    consequence: ['missense_variant'],
    vaf: 0.38,
    depth: 180,
    quality: 95,
    status: 'in_progress',
    annotations: [],
    rulesEvaluated: [],
    tierAssignments: [
      {
        guideline: 'CGC_VICC',
        tier: 'Tier II-C',
        confidence: 0.85,
        justification: 'Known pathogenic variant in tumor suppressor',
        rules: ['TSG_PATHOGENIC']
      }
    ],
    interpretations: []
  },
  {
    variantId: 'chr12:25245347:C>T',
    chromosome: 'chr12',
    position: 25245347,
    reference: 'C',
    alternate: 'T',
    gene: {
      symbol: 'KRAS',
      ensemblId: 'ENSG00000133703',
      name: 'KRAS proto-oncogene',
      strand: '-',
      transcriptId: 'ENST00000256078'
    },
    hgvs: {
      genomic: 'NC_000012.12:g.25245347C>T',
      coding: 'NM_033360.4:c.35G>A',
      protein: 'p.Gly12Asp'
    },
    consequence: ['missense_variant'],
    vaf: 0.12,
    depth: 320,
    quality: 98,
    status: 'pending',
    annotations: [],
    rulesEvaluated: [],
    tierAssignments: [
      {
        guideline: 'OncoKB',
        tier: 'Level 1',
        confidence: 0.95,
        justification: 'Predictive biomarker for therapy selection',
        rules: ['ONCOKB_PREDICTIVE']
      }
    ],
    interpretations: []
  }
];