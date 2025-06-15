"""
VCF File Validation Module

Robust VCF format validation using vcfpy library.
Follows clinical genomics best practices from PCGR, Scout, and Nirvana.
"""

import vcfpy
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
import logging

from .error_handler import ValidationError


class VCFValidator:
    """
    VCF file validator using vcfpy library
    
    Uses the proven vcfpy library for robust VCF parsing and validation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Clinical quality thresholds (configurable)
        self.quality_thresholds = {
            'min_depth': 10,
            'min_quality': 20,
            'max_missing_rate': 0.1
        }
    
    def validate_file(self, vcf_path: Path) -> Dict[str, Any]:
        """
        Validate complete VCF file using vcfpy
        
        Args:
            vcf_path: Path to VCF file
            
        Returns:
            Validation results with summary statistics
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Check file accessibility
            if not vcf_path.exists():
                raise ValidationError(
                    error_type="file_not_found",
                    message=f"VCF file not found: {vcf_path}",
                    details={"file_path": str(vcf_path)}
                )
            
            if vcf_path.stat().st_size == 0:
                raise ValidationError(
                    error_type="empty_file",
                    message=f"VCF file is empty: {vcf_path}",
                    details={"file_path": str(vcf_path)}
                )
            
            # Use vcfpy for robust VCF parsing and validation
            try:
                with vcfpy.Reader.from_path(str(vcf_path)) as vcf_reader:
                    validation_results = self._validate_vcf_with_vcfpy(vcf_reader, vcf_path)
            except Exception as e:
                raise ValidationError(
                    error_type="invalid_vcf_format",
                    message=f"Failed to parse VCF file: {str(e)}",
                    details={"file_path": str(vcf_path), "error": str(e)}
                )
            
            # Add file metadata
            validation_results.update({
                'file_path': str(vcf_path),
                'file_size': vcf_path.stat().st_size,
                'compressed': vcf_path.suffix.lower() == '.gz',
                'valid_format': True
            })
            
            return validation_results
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                error_type="file_read_error",
                message=f"Failed to read VCF file: {str(e)}",
                details={"file_path": str(vcf_path), "error": str(e)}
            )
    
    def _validate_vcf_with_vcfpy(self, vcf_reader, vcf_path: Path) -> Dict[str, Any]:
        """Validate VCF content using vcfpy and extract statistics"""
        
        # Initialize statistics tracking
        stats = {
            'total_variants': 0,
            'variant_types': defaultdict(int),
            'chromosomes': set(),
            'quality_distribution': [],
            'depth_distribution': [],
            'filter_status': defaultdict(int),
            'samples': []
        }
        
        errors = []
        warnings = []
        variants = []
        
        try:
            # Get sample names
            stats['samples'] = list(vcf_reader.header.samples.names)
            
            # Validate header information
            self._validate_header_info(vcf_reader.header, errors, warnings)
            
            # Process variants
            for variant_idx, record in enumerate(vcf_reader):
                try:
                    # Extract variant data
                    variant_data = self._extract_variant_data(record)
                    variants.append(variant_data)
                    
                    # Update statistics
                    self._update_statistics_vcfpy(variant_data, stats)
                    
                    # Validate variant quality
                    self._validate_variant_quality(record, variant_idx, warnings)
                    
                except Exception as e:
                    errors.append({
                        'line': variant_idx + 1,
                        'error': f'Error processing variant: {str(e)}',
                        'severity': 'warning'
                    })
                    continue
            
            # Check for critical issues
            if not variants:
                warnings.append({
                    'line': 0,
                    'warning': 'No variants found in VCF file',
                    'severity': 'warning'
                })
            
        except Exception as e:
            raise ValidationError(
                error_type="parsing_error",
                message=f"Error parsing VCF with vcfpy: {str(e)}",
                details={"error": str(e)}
            )
        
        # Compile final results
        results = {
            'valid_format': True,
            'total_variants': len(variants),
            'errors': errors,
            'warnings': warnings,
            'statistics': dict(stats),
            'sample_count': len(stats['samples']),
            'chromosomes': sorted(list(stats['chromosomes'])),
        }
        
        # Add variant type summary
        if stats['variant_types']:
            results['variant_types'] = dict(stats['variant_types'])
        
        # Add quality summary
        if stats['quality_distribution']:
            results['quality_summary'] = {
                'mean_quality': sum(stats['quality_distribution']) / len(stats['quality_distribution']),
                'min_quality': min(stats['quality_distribution']),
                'max_quality': max(stats['quality_distribution'])
            }
        
        return results
    
    def _validate_header_info(self, header, errors: List[Dict], warnings: List[Dict]) -> None:
        """Validate VCF header information"""
        
        # Check for required header fields
        if not hasattr(header, 'lines') or not header.lines:
            errors.append({
                'line': 0,
                'error': 'Missing VCF header',
                'severity': 'error'
            })
            return
        
        # Check for fileformat
        fileformat_found = False
        for line in header.lines:
            if hasattr(line, 'key') and line.key == 'fileformat':
                fileformat_found = True
                break
        
        if not fileformat_found:
            errors.append({
                'line': 0,
                'error': 'Missing ##fileformat header line',
                'severity': 'error'
            })
        
        # Check for reference
        reference_found = False
        for line in header.lines:
            if hasattr(line, 'key') and line.key == 'reference':
                reference_found = True
                break
        
        if not reference_found:
            warnings.append({
                'line': 0,
                'warning': 'Missing ##reference header line',
                'severity': 'warning'
            })
    
    def _extract_variant_data(self, record) -> Dict[str, Any]:
        """Extract data from vcfpy record object"""
        
        # Determine variant type
        variant_type = self._classify_variant_type_vcfpy(record)
        
        # Extract depth and VAF
        depth = self._extract_depth_vcfpy(record)
        vaf = self._extract_vaf_vcfpy(record)
        
        return {
            'chromosome': record.CHROM,
            'position': record.POS,
            'id': record.ID[0] if record.ID else None,
            'reference': record.REF,
            'alternate': record.ALT[0].value if record.ALT and hasattr(record.ALT[0], 'value') else (str(record.ALT[0]) if record.ALT else None),
            'quality': record.QUAL if record.QUAL is not None else None,
            'filter': record.FILTER[0] if record.FILTER else 'PASS',
            'variant_type': variant_type,
            'depth': depth,
            'vaf': vaf
        }
    
    def _classify_variant_type_vcfpy(self, record) -> str:
        """Classify variant type using vcfpy record object"""
        
        if not record.ALT:
            return 'unknown'
        
        ref = record.REF
        alt = record.ALT[0].value if hasattr(record.ALT[0], 'value') else str(record.ALT[0])
        
        if len(ref) == 1 and len(alt) == 1:
            return 'SNV'
        elif len(ref) == len(alt) and len(ref) > 1:
            return 'MNV'
        elif len(ref) < len(alt):
            return 'insertion'
        elif len(ref) > len(alt):
            return 'deletion'
        else:
            return 'complex'
    
    def _extract_depth_vcfpy(self, record) -> Optional[int]:
        """Extract depth information from vcfpy record"""
        
        # Try INFO DP field first
        if 'DP' in record.INFO:
            try:
                return int(record.INFO['DP'])
            except (ValueError, TypeError):
                pass
        
        # Try FORMAT DP field
        if record.calls and len(record.calls) > 0:
            call = record.calls[0]
            if 'DP' in call.data:
                try:
                    return int(call.data['DP'])
                except (ValueError, TypeError):
                    pass
        
        return None
    
    def _extract_vaf_vcfpy(self, record) -> Optional[float]:
        """Extract VAF information from vcfpy record"""
        
        # Try INFO AF field first
        if 'AF' in record.INFO:
            try:
                af = record.INFO['AF']
                if isinstance(af, (list, tuple)):
                    return float(af[0])
                return float(af)
            except (ValueError, TypeError):
                pass
        
        # Try FORMAT VAF field
        if record.calls and len(record.calls) > 0:
            call = record.calls[0]
            if 'VAF' in call.data:
                try:
                    return float(call.data['VAF'])
                except (ValueError, TypeError):
                    pass
        
        # Calculate from AD if available
        if record.calls and len(record.calls) > 0:
            call = record.calls[0]
            if 'AD' in call.data:
                try:
                    ad = call.data['AD']
                    if isinstance(ad, (list, tuple)) and len(ad) >= 2:
                        ref_count, alt_count = ad[0], ad[1]
                        if ref_count + alt_count > 0:
                            return alt_count / (ref_count + alt_count)
                except (ValueError, TypeError, IndexError):
                    pass
        
        return None
    
    def _validate_variant_quality(self, record, variant_idx: int, warnings: List[Dict]) -> None:
        """Validate individual variant quality metrics"""
        
        # Check quality score
        if record.QUAL is not None and record.QUAL < self.quality_thresholds['min_quality']:
            warnings.append({
                'line': variant_idx + 1,
                'warning': f'Low quality score: {record.QUAL}',
                'severity': 'warning'
            })
        
        # Check depth
        depth = self._extract_depth_vcfpy(record)
        if depth is not None and depth < self.quality_thresholds['min_depth']:
            warnings.append({
                'line': variant_idx + 1,
                'warning': f'Low depth: {depth}',
                'severity': 'warning'
            })
    
    def _update_statistics_vcfpy(self, variant_data: Dict[str, Any], stats: Dict[str, Any]) -> None:
        """Update running statistics with variant data"""
        
        stats['total_variants'] += 1
        stats['variant_types'][variant_data['variant_type']] += 1
        stats['chromosomes'].add(variant_data['chromosome'])
        stats['filter_status'][variant_data['filter']] += 1
        
        if variant_data['quality'] is not None:
            stats['quality_distribution'].append(variant_data['quality'])
        
        if variant_data['depth'] is not None:
            stats['depth_distribution'].append(variant_data['depth'])