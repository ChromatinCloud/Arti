import { Filter, FilterGroup, AnalysisMode } from '../types/filtering.types';

export function getDefaultFilters(mode: AnalysisMode): {
  filters: Record<string, Filter>;
  filterGroups: FilterGroup[];
} {
  const filters: Record<string, Filter> = {
    // Quality Filters
    FILTER_PASS: {
      id: 'FILTER_PASS',
      name: 'Require caller PASS flag',
      type: 'checkbox',
      vcfFields: ['FILTER'],
      description: 'Drops any call the variant-caller itself marked as low confidence',
      enabled: true,
      value: true,
      command: 'bcftools view -f PASS'
    },
    MIN_QUAL: {
      id: 'MIN_QUAL',
      name: 'Minimum variant QUAL',
      type: 'slider',
      vcfFields: ['QUAL'],
      description: 'Phred-scaled confidence in the variant call',
      enabled: true,
      value: 50,
      min: 20,
      max: 100,
      unit: 'QUAL'
    },
    MIN_GQ: {
      id: 'MIN_GQ',
      name: 'Minimum genotype quality',
      type: 'slider',
      vcfFields: ['FORMAT/GQ'],
      description: 'Sample-specific confidence in the called genotype',
      enabled: true,
      value: 30,
      min: 10,
      max: 99,
      unit: 'GQ'
    },
    MIN_DP: {
      id: 'MIN_DP',
      name: 'Minimum read depth',
      type: 'slider',
      vcfFields: ['FORMAT/DP'],
      description: 'Ensures enough coverage at the locus',
      enabled: true,
      value: 20,
      min: 10,
      max: 100,
      unit: 'reads'
    },

    // Allele Filters
    MIN_ALT_COUNT: {
      id: 'MIN_ALT_COUNT',
      name: 'Minimum ALT read support',
      type: 'slider',
      vcfFields: ['FORMAT/AD'],
      description: 'Absolute number of reads supporting the alternate allele',
      enabled: true,
      value: 10,
      min: 5,
      max: 50,
      unit: 'reads'
    },
    MIN_VAF: {
      id: 'MIN_VAF',
      name: 'Minimum variant allele fraction',
      type: 'slider',
      vcfFields: ['INFO/AF', 'FORMAT/AD'],
      description: mode === 'tumor-only' 
        ? 'Removes low-level noise; 5% is typical for tumor tissue'
        : 'Minimum VAF in tumor sample for somatic calling',
      enabled: true,
      value: 0.05,
      min: 0.01,
      max: 0.5,
      step: 0.01,
      unit: '%'
    },
    HET_AB_RANGE: {
      id: 'HET_AB_RANGE',
      name: 'Acceptable allele balance for heterozygotes',
      type: 'range',
      vcfFields: ['FORMAT/AD'],
      description: 'Rejects mapping artifacts where ref/alt depth ratio is extreme',
      enabled: mode === 'tumor-normal', // More relevant for tumor-normal
      value: [0.25, 0.75],
      min: 0,
      max: 1,
      step: 0.05
    },

    // Technical Filters
    STRAND_BIAS: {
      id: 'STRAND_BIAS',
      name: 'Maximum strand bias',
      type: 'range',
      vcfFields: ['INFO/FS', 'INFO/SOR'],
      description: 'High strand bias suggests sequencing or alignment artifacts',
      enabled: true,
      value: [60, 3], // [FS max, SOR max]
      min: 0,
      max: 100,
      step: 1
    },
    MIN_MQ: {
      id: 'MIN_MQ',
      name: 'Minimum mapping quality',
      type: 'slider',
      vcfFields: ['INFO/MQ'],
      description: 'Ensures reads are uniquely and confidently mapped',
      enabled: true,
      value: 40,
      min: 20,
      max: 60,
      unit: 'MQ'
    },
    ROI_ONLY: {
      id: 'ROI_ONLY',
      name: 'Restrict to panel regions',
      type: 'checkbox',
      vcfFields: ['CHROM', 'POS'],
      description: 'Drops off-target calls and dramatically shrinks variant count',
      enabled: true,
      value: true
    },

    // Population & Impact Filters
    MAX_POP_AF: {
      id: 'MAX_POP_AF',
      name: 'Maximum population allele frequency',
      type: 'slider',
      vcfFields: ['INFO/AF', 'INFO/AF_popmax'],
      description: 'Excludes common benign polymorphisms',
      enabled: true,
      value: 0.01,
      min: 0,
      max: 0.05,
      step: 0.001,
      unit: '%'
    },
    EFFECT_IMPACT: {
      id: 'EFFECT_IMPACT',
      name: 'Keep only HIGH/MODERATE impact',
      type: 'multiselect',
      vcfFields: ['INFO/CSQ', 'INFO/ANN'],
      description: 'Focuses on variants most likely to be clinically relevant',
      enabled: true,
      value: ['HIGH', 'MODERATE'],
      options: ['HIGH', 'MODERATE', 'LOW', 'MODIFIER']
    },
    BLACKLIST: {
      id: 'BLACKLIST',
      name: 'Remove panel-of-normals/artifact blacklist',
      type: 'checkbox',
      vcfFields: ['CHROM', 'POS', 'REF', 'ALT'],
      description: 'Eliminates recurrent sequencing artifacts',
      enabled: true,
      value: true
    }
  };

  // Add tumor-normal specific filters
  if (mode === 'tumor-normal') {
    filters.NORMAL_VAF_MAX = {
      id: 'NORMAL_VAF_MAX',
      name: 'Maximum VAF in normal',
      type: 'slider',
      vcfFields: ['FORMAT/AD'],
      description: 'Maximum VAF allowed in matched normal sample',
      enabled: true,
      value: 0.02,
      min: 0,
      max: 0.1,
      step: 0.01,
      unit: '%'
    };

    filters.TUMOR_NORMAL_VAF_RATIO = {
      id: 'TUMOR_NORMAL_VAF_RATIO',
      name: 'Minimum tumor/normal VAF ratio',
      type: 'slider',
      vcfFields: ['FORMAT/AD'],
      description: 'Ensures tumor VAF is significantly higher than normal',
      enabled: true,
      value: 5,
      min: 2,
      max: 20,
      step: 1,
      unit: 'x'
    };
  }

  // Organize filters into groups
  const filterGroups: FilterGroup[] = [
    {
      id: 'quality',
      name: 'Quality Filters',
      filters: [
        filters.FILTER_PASS,
        filters.MIN_QUAL,
        filters.MIN_GQ,
        filters.MIN_DP
      ],
      expanded: true
    },
    {
      id: 'allele',
      name: 'Allele Filters',
      filters: [
        filters.MIN_ALT_COUNT,
        filters.MIN_VAF,
        filters.HET_AB_RANGE,
        ...(mode === 'tumor-normal' 
          ? [filters.NORMAL_VAF_MAX!, filters.TUMOR_NORMAL_VAF_RATIO!] 
          : [])
      ],
      expanded: true
    },
    {
      id: 'technical',
      name: 'Technical Filters',
      filters: [
        filters.STRAND_BIAS,
        filters.MIN_MQ,
        filters.ROI_ONLY
      ],
      expanded: true
    },
    {
      id: 'population',
      name: 'Population & Impact Filters',
      filters: [
        filters.MAX_POP_AF,
        filters.EFFECT_IMPACT,
        filters.BLACKLIST
      ],
      expanded: true
    }
  ];

  return { filters, filterGroups };
}