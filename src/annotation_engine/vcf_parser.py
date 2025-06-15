"""
VCF Field Extraction Module

Uses battle-tested pysam library to extract standard VCF specification fields
for variant identification and clinical interpretation.
"""

import pysam
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

from .validation.error_handler import ValidationError
from .vcf_utils import VCFFileHandler, detect_vcf_file_type


class VCFFieldExtractor:
    """
    Robust VCF field extractor using pysam
    
    Extracts standard VCF specification fields without assuming pre-annotations.
    Based on VCF spec 4.2-4.5 reserved and standard fields only.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_metadata_bundle(self, vcf_path: Path, analysis_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract complete metadata bundle from VCF header and analysis context
        
        Args:
            vcf_path: Path to VCF file
            analysis_context: CLI-provided analysis parameters
            
        Returns:
            Complete metadata bundle
        """
        try:
            with pysam.VariantFile(str(vcf_path)) as vcf:
                # Extract header information
                header_metadata = self._extract_header_metadata(vcf.header)
                
                # Count variants for summary
                variant_count = sum(1 for _ in vcf.fetch())
                
                # Combine with analysis context
                metadata_bundle = {
                    # VCF header metadata
                    **header_metadata,
                    
                    # Analysis context
                    'case_uid': analysis_context.get('case_uid'),
                    'patient_uid': analysis_context.get('patient_uid'),
                    'cancer_type': analysis_context.get('cancer_type'),
                    'tissue_type': analysis_context.get('tissue_type'),
                    'oncotree_id': analysis_context.get('oncotree_id'),
                    'guidelines': analysis_context.get('guidelines', []),
                    'genome_build': analysis_context.get('genome_build'),
                    
                    # File metadata
                    'vcf_path': str(vcf_path),
                    'vcf_size': vcf_path.stat().st_size,
                    'total_variants': variant_count,
                    'processing_timestamp': datetime.utcnow().isoformat(),
                }
                
                return metadata_bundle
                
        except Exception as e:
            raise ValidationError(
                error_type="metadata_extraction_error",
                message=f"Failed to extract metadata from VCF: {str(e)}",
                details={"vcf_path": str(vcf_path), "error": str(e)}
            )
    
    def extract_variant_bundle(self, vcf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract complete variant bundles with standard VCF fields
        Supports both plain text and gzipped VCF files with tabix indexing
        
        Args:
            vcf_path: Path to VCF file (.vcf or .vcf.gz)
            
        Returns:
            List of variant bundles with standard VCF spec fields
        """
        try:
            # Detect and validate VCF file type
            file_type = detect_vcf_file_type(vcf_path)
            
            if not file_type["can_process"]:
                raise ValidationError(
                    error_type="unsupported_file_type",
                    message=f"Cannot process file type: {file_type['file_type']}",
                    details={"vcf_path": str(vcf_path), "file_type": file_type}
                )
            
            # Use VCF handler for robust file handling
            vcf_handler = VCFFileHandler(vcf_path)
            
            # Auto-create tabix index if gzipped but not indexed
            if vcf_handler.is_gzipped and not vcf_handler.is_indexed:
                self.logger.info(f"Creating tabix index for gzipped VCF: {vcf_path}")
                try:
                    vcf_handler.create_tabix_index()
                except Exception as e:
                    self.logger.warning(f"Failed to create tabix index (continuing anyway): {e}")
            
            # Extract variants using our enhanced handler
            variant_bundles = []
            for variant_dict in vcf_handler.iterate_variants():
                # Convert to our expected format if needed
                variant_bundle = self._standardize_variant_dict(variant_dict)
                variant_bundles.append(variant_bundle)
            
            self.logger.info(f"Extracted {len(variant_bundles)} variants from {vcf_path}")
            return variant_bundles
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                error_type="variant_extraction_error",
                message=f"Failed to extract variants from VCF: {str(e)}",
                details={"vcf_path": str(vcf_path), "error": str(e)}
            )
    
    def _extract_header_metadata(self, header) -> Dict[str, Any]:
        """Extract metadata from VCF header"""
        
        metadata = {
            'vcf_version': None,
            'genome_build': None,
            'sample_names': [],
            'info_definitions': {},
            'format_definitions': {},
            'filter_definitions': {},
            'contig_info': {},
        }
        
        # Extract basic header info
        if hasattr(header, 'version'):
            metadata['vcf_version'] = header.version
        
        # Extract sample names
        if hasattr(header, 'samples'):
            metadata['sample_names'] = list(header.samples)
        
        # Extract reference genome
        for record in header.records:
            record_str = str(record)
            if 'reference=' in record_str:
                metadata['genome_build'] = record_str.split('##reference=')[1].strip()
                break
        
        # Extract INFO field definitions
        for record in header.records:
            if record.type == 'INFO':
                metadata['info_definitions'][record['ID']] = {
                    'number': record.get('Number'),
                    'type': record.get('Type'),
                    'description': record.get('Description', '')
                }
        
        # Extract FORMAT field definitions
        for record in header.records:
            if record.type == 'FORMAT':
                metadata['format_definitions'][record['ID']] = {
                    'number': record.get('Number'),
                    'type': record.get('Type'),
                    'description': record.get('Description', '')
                }
        
        # Extract FILTER definitions
        for record in header.records:
            if record.type == 'FILTER':
                metadata['filter_definitions'][record['ID']] = {
                    'description': record.get('Description', '')
                }
        
        # Extract contig information
        for record in header.records:
            if record.type == 'contig':
                contig_id = record['ID']
                metadata['contig_info'][contig_id] = {
                    'length': record.get('length'),
                    'assembly': record.get('assembly'),
                    'species': record.get('species')
                }
        
        return metadata
    
    def _extract_variant_fields(self, record) -> Dict[str, Any]:
        """Extract standard VCF specification fields from variant record"""
        
        # Core identification (VCF columns 1-4)
        variant_bundle = {
            'chromosome': record.chrom,
            'position': record.pos,
            'reference': record.ref,
            'alternate': record.alts[0] if record.alts else None,
            
            # Quality & filter (VCF columns 5-6)
            'quality_score': record.qual,
            'filter_status': record.filter.keys() if record.filter else ['PASS'],
            
            # Standard INFO fields (VCF spec reserved keys)
            'allele_count': self._safe_extract_info(record, 'AC'),
            'allele_frequency': self._safe_extract_info(record, 'AF'),
            'total_alleles': self._safe_extract_info(record, 'AN'),
            'total_depth': self._safe_extract_info(record, 'DP'),
            'num_samples': self._safe_extract_info(record, 'NS'),
            'dbsnp_member': 'DB' in record.info,
            'somatic_flag': 'SOMATIC' in record.info,
            
            # Structural variant INFO fields (VCF spec 4.4+)
            'sv_type': self._safe_extract_info(record, 'SVTYPE'),
            'sv_length': self._safe_extract_info(record, 'SVLEN'),
            'sv_end': self._safe_extract_info(record, 'END'),
            'imprecise_flag': 'IMPRECISE' in record.info,
            'ci_pos': self._safe_extract_info(record, 'CIPOS'),
            'ci_end': self._safe_extract_info(record, 'CIEND'),
            
            # Sample-specific data (FORMAT fields)
            'samples': []
        }
        
        # Extract per-sample FORMAT data
        for sample_name in record.samples:
            sample_data = self._extract_sample_data(record, sample_name)
            variant_bundle['samples'].append({
                'sample_name': sample_name,
                **sample_data
            })
        
        return variant_bundle
    
    def _extract_sample_data(self, record, sample_name: str) -> Dict[str, Any]:
        """Extract standard FORMAT fields for a specific sample"""
        
        sample = record.samples[sample_name]
        
        return {
            # Standard FORMAT fields (VCF spec)
            'genotype': self._format_genotype(sample.get('GT')),
            'sample_depth': sample.get('DP'),
            'allelic_depths': sample.get('AD'),
            'genotype_quality': sample.get('GQ'),
            'genotype_likelihoods': sample.get('PL'),
            
            # Additional common FORMAT fields
            'phase_set': sample.get('PS'),
            'read_position_rank_sum': sample.get('ReadPosRankSum'),
            'mapping_quality_rank_sum': sample.get('MQRankSum'),
            'variant_allele_frequency': self._calculate_vaf(sample.get('AD')),
        }
    
    def _safe_extract_info(self, record, key: str) -> Any:
        """Safely extract INFO field value, returning None if not present"""
        try:
            if key in record.info:
                value = record.info[key]
                # Handle single-element tuples/lists
                if isinstance(value, (tuple, list)) and len(value) == 1:
                    return value[0]
                return value
            return None
        except (KeyError, AttributeError, ValueError):
            return None
    
    def _format_genotype(self, gt_tuple) -> Optional[str]:
        """Format genotype tuple to standard string representation"""
        if gt_tuple is None:
            return None
        
        try:
            # Convert genotype tuple to standard format
            if len(gt_tuple) == 2:
                return f"{gt_tuple[0]}/{gt_tuple[1]}"
            elif len(gt_tuple) == 1:
                return str(gt_tuple[0])
            else:
                return "/".join(map(str, gt_tuple))
        except (TypeError, IndexError):
            return str(gt_tuple)
    
    def _calculate_vaf(self, allelic_depths) -> Optional[float]:
        """Calculate variant allele frequency from allelic depths"""
        if not allelic_depths or len(allelic_depths) < 2:
            return None
        
        try:
            ref_depth = allelic_depths[0]
            alt_depth = allelic_depths[1]
            total_depth = ref_depth + alt_depth
            
            if total_depth > 0:
                return alt_depth / total_depth
            return None
        except (TypeError, IndexError, ZeroDivisionError):
            return None
    
    def _standardize_variant_dict(self, variant_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize variant dictionary from VCF utilities to expected format
        
        This method ensures compatibility between VCFFileHandler output
        and the format expected by downstream components.
        """
        # If already in expected format, return as-is
        if 'samples' in variant_dict and isinstance(variant_dict['samples'], list):
            # Calculate VAF for samples if not present
            for sample in variant_dict['samples']:
                if 'variant_allele_frequency' not in sample and 'data' in sample:
                    # Try to calculate VAF from AD field
                    ad_data = sample['data'].get('AD')
                    if ad_data:
                        # Handle different AD formats
                        if isinstance(ad_data, str):
                            try:
                                ad_values = [int(x) for x in ad_data.split(',')]
                                if len(ad_values) >= 2:
                                    total_depth = sum(ad_values)
                                    if total_depth > 0:
                                        sample['variant_allele_frequency'] = ad_values[1] / total_depth
                            except (ValueError, IndexError):
                                pass
                        elif isinstance(ad_data, list) and len(ad_data) >= 2:
                            try:
                                total_depth = sum(ad_data)
                                if total_depth > 0:
                                    sample['variant_allele_frequency'] = ad_data[1] / total_depth
                            except (TypeError, ZeroDivisionError):
                                pass
            
            return variant_dict
        
        # Convert from VCFFileHandler format to expected format
        standardized = {
            'chromosome': variant_dict.get('chromosome'),
            'position': variant_dict.get('position'),
            'reference': variant_dict.get('reference'),
            'alternate': variant_dict.get('alternate'),
            'quality_score': variant_dict.get('quality_score'),
            'filter_status': variant_dict.get('filter_status', ['PASS']),
            
            # Standard INFO fields
            'allele_frequency': variant_dict.get('allele_frequency'),
            'total_depth': variant_dict.get('total_depth'),
            'dbsnp_member': variant_dict.get('info', {}).get('DB', False),
            'somatic_flag': variant_dict.get('info', {}).get('SOMATIC', False),
            
            # Sample data conversion
            'samples': []
        }
        
        # Convert sample format
        vcf_samples = variant_dict.get('samples', [])
        for sample in vcf_samples:
            sample_data = {
                'sample_name': sample.get('name', 'UNKNOWN'),
                'genotype': self._format_genotype_from_sample(sample),
                'variant_allele_frequency': self._extract_vaf_from_sample(sample)
            }
            
            # Add additional sample data
            if 'data' in sample:
                sample_data.update({
                    'sample_depth': sample['data'].get('DP'),
                    'allelic_depths': self._parse_allelic_depths(sample['data'].get('AD')),
                    'genotype_quality': sample['data'].get('GQ'),
                })
            
            standardized['samples'].append(sample_data)
        
        return standardized
    
    def _format_genotype_from_sample(self, sample: Dict[str, Any]) -> Optional[str]:
        """Format genotype from sample data"""
        if 'genotype' in sample and sample['genotype']:
            gt = sample['genotype']
            if isinstance(gt, list):
                return '/'.join(map(str, gt))
            return str(gt)
        
        # Try to get from data.GT
        if 'data' in sample and 'GT' in sample['data']:
            gt_data = sample['data']['GT']
            if isinstance(gt_data, str):
                return gt_data
            elif isinstance(gt_data, list):
                return '/'.join(map(str, gt_data))
        
        return None
    
    def _extract_vaf_from_sample(self, sample: Dict[str, Any]) -> Optional[float]:
        """Extract VAF from sample data"""
        if 'data' not in sample:
            return None
        
        data = sample['data']
        
        # Try common VAF fields
        for vaf_field in ['VAF', 'AF', 'FREQ']:
            if vaf_field in data:
                try:
                    vaf_value = data[vaf_field]
                    if isinstance(vaf_value, str):
                        # Handle percentage strings
                        if vaf_value.endswith('%'):
                            return float(vaf_value.rstrip('%')) / 100.0
                        return float(vaf_value)
                    return float(vaf_value)
                except (ValueError, TypeError):
                    continue
        
        # Calculate from AD if available
        if 'AD' in data:
            ad_data = data['AD']
            allelic_depths = self._parse_allelic_depths(ad_data)
            if allelic_depths and len(allelic_depths) >= 2:
                return self._calculate_vaf(allelic_depths)
        
        return None
    
    def _parse_allelic_depths(self, ad_data) -> Optional[List[int]]:
        """Parse allelic depths from various formats"""
        if not ad_data:
            return None
        
        try:
            if isinstance(ad_data, str):
                return [int(x) for x in ad_data.split(',')]
            elif isinstance(ad_data, list):
                return [int(x) for x in ad_data]
            elif isinstance(ad_data, (int, float)):
                return [int(ad_data)]
        except (ValueError, TypeError):
            pass
        
        return None
    
    def extract_genome_build_from_header(self, vcf_path: Path) -> Optional[str]:
        """Quick extraction of genome build from VCF header"""
        try:
            with pysam.VariantFile(str(vcf_path)) as vcf:
                for record in vcf.header.records:
                    record_str = str(record)
                    if 'reference=' in record_str:
                        return record_str.split('##reference=')[1].strip()
                return None
        except Exception:
            return None