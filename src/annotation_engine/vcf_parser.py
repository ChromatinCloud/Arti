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
        
        Args:
            vcf_path: Path to VCF file
            
        Returns:
            List of variant bundles with standard VCF spec fields
        """
        try:
            variant_bundles = []
            
            with pysam.VariantFile(str(vcf_path)) as vcf:
                for record in vcf.fetch():
                    variant_bundle = self._extract_variant_fields(record)
                    variant_bundles.append(variant_bundle)
            
            return variant_bundles
            
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