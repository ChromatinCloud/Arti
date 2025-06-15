# VCF Parsing and Processing Blueprint

## Overview

This document defines VCF parsing strategies based on best practices from leading clinical annotation tools (Nirvana, PCGR, Hartwig, CancerVar). We adopt a **multi-allelic aware**, **quality-filtered** approach with comprehensive INFO field extraction.

## VCF Processing Architecture

### Core Principles (Based on Industry Leaders)

1. **Allele-Specific Processing** (PCGR/vcfanno pattern): Each alternate allele processed separately
2. **Quality-First Filtering** (Hartwig SAGE pattern): Rigorous quality thresholds before annotation
3. **Comprehensive INFO Extraction** (Nirvana pattern): Preserve all relevant technical information
4. **Assembly Flexibility** (PCGR pattern): Support both GRCh37/GRCh38

## VCF Field Extraction Strategy

### Required VCF Fields

Based on **Nirvana's** comprehensive annotation approach and **PCGR's** precision oncology focus:

```python
# src/annotation_engine/vcf/parser.py
class VCFFieldExtractor:
    """Extract and normalize VCF fields for clinical annotation"""
    
    # Core VCF fields (always required)
    CORE_FIELDS = [
        'CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT'
    ]
    
    # INFO fields for clinical interpretation
    CLINICAL_INFO_FIELDS = {
        # Variant calling quality
        'DP': 'Total read depth',
        'AD': 'Allelic depths for REF and ALT alleles',
        'AF': 'Allele frequency',
        'VAF': 'Variant allele frequency',
        'MQ': 'Mapping quality',
        'QD': 'Quality by depth',
        'FS': 'Fisher strand bias',
        'SOR': 'Strand odds ratio',
        'MQRankSum': 'Mapping quality rank sum',
        'ReadPosRankSum': 'Read position rank sum',
        
        # Somatic variant calling (following Hartwig SAGE)
        'TIER': 'Variant tier (HOTSPOT, PANEL, HIGH_CONFIDENCE, LOW_CONFIDENCE)',
        'SOMATIC_FLAG': 'Somatic variant flag',
        'GERMLINE_FLAG': 'Germline variant flag',
        'TUMOR_VAF': 'Tumor variant allele frequency',
        'NORMAL_VAF': 'Normal variant allele frequency',
        'TUMOR_DP': 'Tumor read depth',
        'NORMAL_DP': 'Normal read depth',
        
        # Copy number and structural variants
        'SVTYPE': 'Structural variant type',
        'SVLEN': 'Structural variant length',
        'END': 'End position for structural variants',
        'CN': 'Copy number',
        'CNV': 'Copy number variant flag',
        
        # Population databases (pre-annotation)
        'gnomAD_AF': 'gnomAD allele frequency',
        'gnomAD_AC': 'gnomAD allele count',
        'gnomAD_AN': 'gnomAD allele number',
        'COSMIC_ID': 'COSMIC mutation identifier',
        'dbSNP_RS': 'dbSNP rsID',
        
        # Technical annotations
        'MULTIALLELIC': 'Multi-allelic site flag',
        'OLD_MULTIALLELIC': 'Original multi-allelic representation',
        'STRAND_BIAS': 'Strand bias annotation',
        'BASE_QUALITY': 'Base quality metrics'
    }
    
    # FORMAT fields for sample-specific data
    SAMPLE_FORMAT_FIELDS = {
        'GT': 'Genotype',
        'AD': 'Allelic depths',
        'DP': 'Read depth',
        'GQ': 'Genotype quality',
        'PL': 'Phred-scaled likelihoods',
        'VAF': 'Variant allele frequency',
        'AF': 'Allele frequency'
    }
```

### Multi-Allelic Variant Handling

Following **PCGR's** vcfanno approach and **Nirvana's** allele-specific processing:

```python
class MultiAllelicProcessor:
    """Handle multi-allelic variants following clinical best practices"""
    
    def __init__(self):
        self.normalization_engine = VariantNormalizer()
    
    def process_multiallelic_record(self, vcf_record: dict) -> List[dict]:
        """
        Split multi-allelic variants into separate records
        Following PCGR/vcfanno methodology
        """
        if len(vcf_record['ALT']) == 1:
            return [vcf_record]  # Single allele, no processing needed
        
        split_records = []
        ref_allele = vcf_record['REF']
        
        for alt_index, alt_allele in enumerate(vcf_record['ALT']):
            # Create new record for this allele
            split_record = {
                'CHROM': vcf_record['CHROM'],
                'POS': vcf_record['POS'],
                'ID': vcf_record.get('ID', '.'),
                'REF': ref_allele,
                'ALT': [alt_allele],
                'QUAL': vcf_record.get('QUAL', '.'),
                'FILTER': vcf_record.get('FILTER', '.'),
                'INFO': self._split_info_fields(vcf_record['INFO'], alt_index),
                'FORMAT': vcf_record.get('FORMAT', {}),
                'samples': self._split_sample_data(vcf_record.get('samples', {}), alt_index)
            }
            
            # Add multi-allelic tracking
            split_record['INFO']['MULTIALLELIC'] = 'TRUE'
            split_record['INFO']['OLD_MULTIALLELIC'] = f"{ref_allele}>{','.join(vcf_record['ALT'])}"
            split_record['INFO']['ALLELE_INDEX'] = str(alt_index + 1)
            
            # Normalize the variant
            normalized_record = self.normalization_engine.normalize(split_record)
            split_records.append(normalized_record)
        
        return split_records
    
    def _split_info_fields(self, info_dict: dict, alt_index: int) -> dict:
        """Split INFO fields that are allele-specific"""
        split_info = {}
        
        # Fields that need allele-specific splitting
        ALLELE_SPECIFIC_FIELDS = ['AF', 'AC', 'VAF', 'AD']
        
        for key, value in info_dict.items():
            if key in ALLELE_SPECIFIC_FIELDS and isinstance(value, list):
                # Take value for this specific allele
                if len(value) > alt_index:
                    split_info[key] = value[alt_index]
                else:
                    split_info[key] = '.'
            else:
                # Keep non-allele-specific fields as-is
                split_info[key] = value
        
        return split_info
```

### Variant Normalization

Based on **Nirvana's** normalization approach:

```python
class VariantNormalizer:
    """Normalize variants to standard representation"""
    
    def normalize(self, variant_record: dict) -> dict:
        """
        Normalize variant following HGVS and clinical standards
        - Left-align indels
        - Trim common prefixes/suffixes
        - Handle complex variants
        """
        chrom = variant_record['CHROM']
        pos = int(variant_record['POS'])
        ref = variant_record['REF']
        alt = variant_record['ALT'][0]  # Assuming single allele after splitting
        
        # Left-align indels
        if len(ref) != len(alt):
            normalized_pos, normalized_ref, normalized_alt = self._left_align_indel(
                pos, ref, alt, chrom
            )
        else:
            normalized_pos, normalized_ref, normalized_alt = pos, ref, alt
        
        # Update record with normalized values
        variant_record['POS'] = normalized_pos
        variant_record['REF'] = normalized_ref
        variant_record['ALT'] = [normalized_alt]
        
        # Add normalization metadata
        if (normalized_pos != pos or normalized_ref != ref or normalized_alt != alt):
            variant_record['INFO']['NORMALIZED'] = 'TRUE'
            variant_record['INFO']['ORIGINAL_VARIANT'] = f"{chrom}:{pos}:{ref}>{alt}"
        
        return variant_record
    
    def _left_align_indel(self, pos: int, ref: str, alt: str, chrom: str) -> tuple:
        """Left-align indel following standard practice"""
        # Implementation would use reference genome for left-alignment
        # This is a simplified version
        return pos, ref, alt
```

## Quality Filtering Strategy

### GATK-Based Quality Filters

Following **Hartwig SAGE** quality filtering approach:

```python
class QualityFilter:
    """Quality filtering following clinical-grade standards"""
    
    def __init__(self, config_path: str = "config/quality_thresholds.yaml"):
        self.thresholds = self._load_thresholds(config_path)
    
    def apply_quality_filters(self, variant_record: dict) -> tuple[bool, List[str]]:
        """
        Apply quality filters and return (pass_flag, failure_reasons)
        Following Hartwig and PCGR quality standards
        """
        failures = []
        
        # Basic quality thresholds
        if not self._check_basic_quality(variant_record, failures):
            return False, failures
        
        # Somatic-specific quality (if applicable)
        if variant_record['INFO'].get('SOMATIC_FLAG'):
            if not self._check_somatic_quality(variant_record, failures):
                return False, failures
        
        # Germline-specific quality (if applicable)
        if variant_record['INFO'].get('GERMLINE_FLAG'):
            if not self._check_germline_quality(variant_record, failures):
                return False, failures
        
        # Strand bias and technical artifacts
        if not self._check_technical_quality(variant_record, failures):
            return False, failures
        
        return len(failures) == 0, failures
    
    def _check_basic_quality(self, record: dict, failures: list) -> bool:
        """Basic quality thresholds"""
        info = record['INFO']
        
        # Minimum read depth
        dp = info.get('DP', 0)
        if dp < self.thresholds['min_depth']:
            failures.append(f"Low depth: {dp} < {self.thresholds['min_depth']}")
            return False
        
        # Minimum variant allele frequency
        vaf = info.get('VAF', info.get('AF', 0))
        if isinstance(vaf, list):
            vaf = max(vaf)  # Take highest VAF for multi-allelic
        
        if vaf < self.thresholds['min_vaf']:
            failures.append(f"Low VAF: {vaf} < {self.thresholds['min_vaf']}")
            return False
        
        # Mapping quality
        mq = info.get('MQ', 0)
        if mq < self.thresholds['min_mapping_quality']:
            failures.append(f"Low mapping quality: {mq} < {self.thresholds['min_mapping_quality']}")
            return False
        
        return True
    
    def _check_somatic_quality(self, record: dict, failures: list) -> bool:
        """Somatic variant specific quality checks"""
        info = record['INFO']
        
        # Tumor VAF threshold
        tumor_vaf = info.get('TUMOR_VAF', 0)
        if tumor_vaf < self.thresholds['somatic']['min_tumor_vaf']:
            failures.append(f"Low tumor VAF: {tumor_vaf}")
            return False
        
        # Normal VAF threshold (should be low)
        normal_vaf = info.get('NORMAL_VAF', 0)
        if normal_vaf > self.thresholds['somatic']['max_normal_vaf']:
            failures.append(f"High normal VAF: {normal_vaf}")
            return False
        
        # Tumor depth
        tumor_dp = info.get('TUMOR_DP', 0)
        if tumor_dp < self.thresholds['somatic']['min_tumor_depth']:
            failures.append(f"Low tumor depth: {tumor_dp}")
            return False
        
        return True
    
    def _check_technical_quality(self, record: dict, failures: list) -> bool:
        """Technical quality checks for artifacts"""
        info = record['INFO']
        
        # Strand bias (Fisher's exact test)
        fs = info.get('FS', 0)
        if fs > self.thresholds['max_fisher_strand']:
            failures.append(f"High strand bias: {fs}")
            return False
        
        # Strand odds ratio
        sor = info.get('SOR', 0)
        if sor > self.thresholds['max_strand_odds_ratio']:
            failures.append(f"High strand odds ratio: {sor}")
            return False
        
        # Quality by depth
        qd = info.get('QD', 0)
        if qd < self.thresholds['min_quality_by_depth']:
            failures.append(f"Low quality by depth: {qd}")
            return False
        
        return True
```

### Quality Threshold Configuration

Following **PCGR's** TOML-based configuration approach:

```yaml
# config/quality_thresholds.yaml
basic_quality:
  min_depth: 10
  min_vaf: 0.05
  min_mapping_quality: 20
  min_quality_by_depth: 2.0
  max_fisher_strand: 60.0
  max_strand_odds_ratio: 3.0

somatic:
  min_tumor_vaf: 0.1
  max_normal_vaf: 0.02
  min_tumor_depth: 20
  min_normal_depth: 10
  min_alt_reads: 3

germline:
  min_gq: 20
  min_depth: 20
  min_vaf: 0.2
  het_vaf_range: [0.3, 0.7]
  hom_vaf_min: 0.8

technical_filters:
  max_repeat_length: 50
  min_base_quality: 20
  max_indel_length: 100
  
# Variant type specific thresholds
variant_type_thresholds:
  snv:
    min_depth: 10
    min_vaf: 0.05
  indel:
    min_depth: 20
    min_vaf: 0.1
  structural:
    min_supporting_reads: 5
    min_quality: 100
```

## VCF Processing Pipeline

### Complete Processing Workflow

```python
class VCFProcessor:
    """Complete VCF processing pipeline following clinical standards"""
    
    def __init__(self, config: dict):
        self.multiallelic_processor = MultiAllelicProcessor()
        self.quality_filter = QualityFilter()
        self.field_extractor = VCFFieldExtractor()
        self.normalizer = VariantNormalizer()
    
    def process_vcf(self, vcf_path: str) -> List[dict]:
        """
        Complete VCF processing pipeline:
        1. Parse VCF records
        2. Split multi-allelic variants
        3. Normalize variants
        4. Apply quality filters
        5. Extract clinical fields
        """
        processed_variants = []
        
        with open(vcf_path, 'r') as vcf_file:
            for line_num, line in enumerate(vcf_file):
                if line.startswith('#'):
                    continue  # Skip header lines
                
                try:
                    # Parse VCF line
                    raw_record = self._parse_vcf_line(line)
                    
                    # Split multi-allelic variants
                    split_records = self.multiallelic_processor.process_multiallelic_record(raw_record)
                    
                    for record in split_records:
                        # Normalize variant representation
                        normalized_record = self.normalizer.normalize(record)
                        
                        # Apply quality filters
                        passes_qc, failure_reasons = self.quality_filter.apply_quality_filters(normalized_record)
                        
                        if passes_qc:
                            # Extract clinical fields
                            clinical_record = self.field_extractor.extract_clinical_fields(normalized_record)
                            clinical_record['vcf_line_number'] = line_num
                            processed_variants.append(clinical_record)
                        else:
                            # Log QC failures
                            self._log_qc_failure(normalized_record, failure_reasons, line_num)
                
                except Exception as e:
                    self._log_parsing_error(line, line_num, str(e))
        
        return processed_variants
    
    def _parse_vcf_line(self, line: str) -> dict:
        """Parse a single VCF line into structured data"""
        fields = line.strip().split('\t')
        
        if len(fields) < 8:
            raise ValueError(f"Invalid VCF line: insufficient fields")
        
        # Parse INFO field
        info_dict = {}
        if fields[7] != '.':
            for info_item in fields[7].split(';'):
                if '=' in info_item:
                    key, value = info_item.split('=', 1)
                    # Handle multiple values
                    if ',' in value:
                        info_dict[key] = value.split(',')
                    else:
                        info_dict[key] = value
                else:
                    info_dict[info_item] = True
        
        # Parse sample data if present
        samples = {}
        if len(fields) > 9:
            format_fields = fields[8].split(':') if fields[8] != '.' else []
            for i, sample_data in enumerate(fields[9:]):
                sample_values = sample_data.split(':')
                sample_dict = {}
                for j, format_field in enumerate(format_fields):
                    if j < len(sample_values):
                        sample_dict[format_field] = sample_values[j]
                samples[f'SAMPLE_{i}'] = sample_dict
        
        return {
            'CHROM': fields[0],
            'POS': int(fields[1]),
            'ID': fields[2] if fields[2] != '.' else None,
            'REF': fields[3],
            'ALT': fields[4].split(','),
            'QUAL': float(fields[5]) if fields[5] != '.' else None,
            'FILTER': fields[6] if fields[6] != '.' else None,
            'INFO': info_dict,
            'samples': samples
        }
```

## Variant Type Classification

Following **Nirvana's** comprehensive variant classification:

```python
class VariantClassifier:
    """Classify variants by type for appropriate processing"""
    
    @staticmethod
    def classify_variant(ref: str, alt: str) -> str:
        """Classify variant type following Nirvana's approach"""
        ref_len = len(ref)
        alt_len = len(alt)
        
        if ref_len == 1 and alt_len == 1:
            return "SNV"
        elif ref_len == alt_len and ref_len > 1:
            return "MNV"  # Multi-nucleotide variant
        elif ref_len < alt_len:
            return "insertion"
        elif ref_len > alt_len:
            return "deletion"
        else:
            return "complex"  # Complex rearrangement
    
    @staticmethod
    def is_structural_variant(info_dict: dict) -> bool:
        """Identify structural variants"""
        return any([
            info_dict.get('SVTYPE'),
            info_dict.get('SVLEN'),
            info_dict.get('END'),
            info_dict.get('CIPOS'),
            info_dict.get('CIEND')
        ])
```

## Output Format

Following **PCGR's** structured output approach:

```python
class VCFOutputFormatter:
    """Format processed VCF data for downstream analysis"""
    
    def format_for_annotation(self, processed_variants: List[dict]) -> List[dict]:
        """Format variants for clinical annotation pipeline"""
        formatted_variants = []
        
        for variant in processed_variants:
            formatted_variant = {
                # Core genomic information
                "chromosome": variant['CHROM'],
                "position": variant['POS'],
                "reference_allele": variant['REF'],
                "alternate_allele": variant['ALT'][0],
                "variant_type": VariantClassifier.classify_variant(
                    variant['REF'], variant['ALT'][0]
                ),
                
                # Quality information
                "quality_score": variant.get('QUAL'),
                "filter_status": variant.get('FILTER'),
                "depth": variant['INFO'].get('DP'),
                "variant_allele_frequency": variant['INFO'].get('VAF', variant['INFO'].get('AF')),
                
                # Technical metadata
                "vcf_info": variant['INFO'],
                "sample_data": variant.get('samples', {}),
                "processing_flags": {
                    "multiallelic": variant['INFO'].get('MULTIALLELIC', False),
                    "normalized": variant['INFO'].get('NORMALIZED', False)
                }
            }
            
            formatted_variants.append(formatted_variant)
        
        return formatted_variants
```

This VCF processing approach provides clinical-grade variant parsing with comprehensive quality control, following industry best practices from leading annotation tools.