"""
VCF File Utilities with Tabix Support

Comprehensive VCF file handling supporting both plain text and gzipped VCF files
with tabix indexing for efficient region-based queries.
"""

import gzip
import logging
import os
from pathlib import Path
from typing import Iterator, Dict, Any, List, Optional, Union, Tuple
import tempfile

import pysam
import vcfpy

from .validation.error_handler import ValidationError

logger = logging.getLogger(__name__)


class VCFFileHandler:
    """
    Comprehensive VCF file handler with support for:
    - Plain text VCF files (.vcf)
    - Gzipped VCF files (.vcf.gz)
    - Tabix indexing (.vcf.gz.tbi)
    - Region-based queries
    - Efficient variant streaming
    """
    
    def __init__(self, vcf_path: Path):
        self.vcf_path = Path(vcf_path)
        self.is_gzipped = self._is_gzipped()
        self.is_indexed = self._check_tabix_index()
        
        # Validate file exists
        if not self.vcf_path.exists():
            raise ValidationError(
                error_type="file_not_found",
                message=f"VCF file not found: {vcf_path}",
                details={"file_path": str(vcf_path)}
            )
        
        logger.debug(f"VCF handler initialized: {vcf_path} (gzipped: {self.is_gzipped}, indexed: {self.is_indexed})")
    
    def _is_gzipped(self) -> bool:
        """Check if VCF file is gzipped"""
        if self.vcf_path.suffix == '.gz':
            return True
        
        # Check file magic number for gzip
        try:
            with open(self.vcf_path, 'rb') as f:
                magic = f.read(2)
                return magic == b'\x1f\x8b'
        except Exception:
            return False
    
    def _check_tabix_index(self) -> bool:
        """Check if tabix index exists"""
        if not self.is_gzipped:
            return False
        
        # Check for .tbi file
        tbi_path = Path(str(self.vcf_path) + '.tbi')
        if tbi_path.exists():
            return True
        
        # Check for .csi file (alternative index format)
        csi_path = Path(str(self.vcf_path) + '.csi')
        if csi_path.exists():
            return True
        
        return False
    
    def create_tabix_index(self, force: bool = False) -> bool:
        """
        Create tabix index for gzipped VCF file
        
        Args:
            force: Force recreation of existing index
            
        Returns:
            True if index was created or already exists
        """
        if not self.is_gzipped:
            logger.warning(f"Cannot create tabix index for uncompressed file: {self.vcf_path}")
            return False
        
        tbi_path = Path(str(self.vcf_path) + '.tbi')
        
        if self.is_indexed and not force:
            logger.debug(f"Tabix index already exists: {tbi_path}")
            return True
        
        try:
            logger.info(f"Creating tabix index for: {self.vcf_path}")
            pysam.tabix_index(str(self.vcf_path), preset='vcf', force=force)
            
            # Update index status
            self.is_indexed = self._check_tabix_index()
            
            logger.info(f"Tabix index created: {tbi_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create tabix index: {e}")
            raise ValidationError(
                error_type="tabix_index_error",
                message=f"Failed to create tabix index: {e}",
                details={
                    "vcf_path": str(self.vcf_path),
                    "error": str(e)
                }
            )
    
    def get_file_stats(self) -> Dict[str, Any]:
        """Get comprehensive file statistics"""
        stats = {
            "file_path": str(self.vcf_path),
            "file_size": self.vcf_path.stat().st_size,
            "is_gzipped": self.is_gzipped,
            "is_indexed": self.is_indexed,
            "format_valid": False,
            "total_variants": 0,
            "chromosomes": set(),
            "has_samples": False,
            "sample_count": 0,
            "sample_names": []
        }
        
        try:
            # Use vcfpy for comprehensive parsing
            reader = self._get_vcfpy_reader()
            
            # Check header
            stats["format_valid"] = True
            
            # Handle SamplesInfos object properly
            try:
                sample_names = list(reader.header.samples)
                stats["has_samples"] = len(sample_names) > 0
                stats["sample_count"] = len(sample_names)
                stats["sample_names"] = sample_names
            except (TypeError, AttributeError) as sample_error:
                # Fallback for SamplesInfos objects that don't support len()
                try:
                    sample_names = [str(s) for s in reader.header.samples]
                    stats["has_samples"] = len(sample_names) > 0
                    stats["sample_count"] = len(sample_names)
                    stats["sample_names"] = sample_names
                except Exception:
                    logger.debug(f"Could not extract sample info: {sample_error}")
                    stats["has_samples"] = False
                    stats["sample_count"] = 0
                    stats["sample_names"] = []
            
            # Count variants and chromosomes
            variant_count = 0
            chromosomes = set()
            
            for record in reader:
                variant_count += 1
                chromosomes.add(record.CHROM)
                
                # Limit to prevent long scanning
                if variant_count >= 10000:
                    stats["total_variants"] = f"{variant_count}+"
                    break
            else:
                stats["total_variants"] = variant_count
            
            stats["chromosomes"] = sorted(list(chromosomes))
            
            reader.close()
            
        except Exception as e:
            logger.warning(f"Failed to get complete file stats: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def _get_vcfpy_reader(self) -> vcfpy.Reader:
        """Get vcfpy Reader for the VCF file"""
        if self.is_gzipped:
            return vcfpy.Reader.from_path(str(self.vcf_path))
        else:
            return vcfpy.Reader.from_path(str(self.vcf_path))
    
    def _get_pysam_reader(self) -> Union[pysam.VariantFile, pysam.TabixFile]:
        """Get pysam reader for the VCF file"""
        if self.is_indexed:
            return pysam.TabixFile(str(self.vcf_path))
        else:
            return pysam.VariantFile(str(self.vcf_path))
    
    def iterate_variants(self, region: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """
        Iterate through variants in the VCF file
        
        Args:
            region: Optional region string (e.g., "chr1:1000-2000")
            
        Yields:
            Dictionary representation of each variant
        """
        try:
            if region and self.is_indexed:
                # Use tabix for region-based query
                yield from self._iterate_variants_tabix(region)
            else:
                # Use vcfpy for full file iteration
                yield from self._iterate_variants_vcfpy()
                
        except Exception as e:
            raise ValidationError(
                error_type="vcf_iteration_error",
                message=f"Failed to iterate variants: {e}",
                details={
                    "vcf_path": str(self.vcf_path),
                    "region": region,
                    "error": str(e)
                }
            )
    
    def _iterate_variants_vcfpy(self) -> Iterator[Dict[str, Any]]:
        """Iterate variants using vcfpy (full file scan)"""
        reader = self._get_vcfpy_reader()
        
        try:
            for record in reader:
                variant_dict = self._vcfpy_record_to_dict(record)
                yield variant_dict
        finally:
            reader.close()
    
    def _iterate_variants_tabix(self, region: str) -> Iterator[Dict[str, Any]]:
        """Iterate variants using tabix (region-based query)"""
        if not self.is_indexed:
            raise ValidationError(
                error_type="tabix_not_indexed",
                message=f"VCF file is not indexed for tabix queries: {self.vcf_path}"
            )
        
        try:
            # Parse region string (e.g., "chr1:1000-2000")
            chrom, positions = region.split(':') if ':' in region else (region, None)
            start, end = positions.split('-') if positions and '-' in positions else (None, None)
            
            # Use pysam tabix for region query
            tabix_file = pysam.TabixFile(str(self.vcf_path))
            
            try:
                if start and end:
                    records = tabix_file.fetch(chrom, int(start), int(end))
                else:
                    records = tabix_file.fetch(chrom)
                
                # Parse each tabix record
                for record_line in records:
                    variant_dict = self._tabix_line_to_dict(record_line)
                    yield variant_dict
                    
            finally:
                tabix_file.close()
                
        except Exception as e:
            raise ValidationError(
                error_type="tabix_query_error",
                message=f"Tabix region query failed: {e}",
                details={
                    "region": region,
                    "vcf_path": str(self.vcf_path),
                    "error": str(e)
                }
            )
    
    def _vcfpy_record_to_dict(self, record: vcfpy.Record) -> Dict[str, Any]:
        """Convert vcfpy Record to dictionary"""
        
        # Extract sample data
        samples = []
        for call in record.calls:
            sample_name = call.sample
            sample_data = {
                "name": sample_name,
                "genotype": call.gt_alleles if hasattr(call, 'gt_alleles') else None,
                "data": {}
            }
            
            # Extract format fields
            if hasattr(call.data, '_asdict'):
                # call.data is a namedtuple
                for key, value in call.data._asdict().items():
                    if value is not None:
                        sample_data["data"][key] = value
            elif hasattr(call.data, 'items'):
                # call.data is already a dict
                for key, value in call.data.items():
                    if value is not None:
                        sample_data["data"][key] = value
            else:
                # call.data is something else, try to iterate as dict
                try:
                    for key in dir(call.data):
                        if not key.startswith('_'):
                            value = getattr(call.data, key)
                            if value is not None and not callable(value):
                                sample_data["data"][key] = value
                except Exception:
                    # Skip format field extraction if we can't figure it out
                    pass
            
            samples.append(sample_data)
        
        # Extract INFO field
        info_dict = {}
        for key, value in record.INFO.items():
            info_dict[key] = value
        
        return {
            "chromosome": record.CHROM,
            "position": record.POS,
            "id": record.ID[0] if record.ID else None,
            "reference": record.REF,
            "alternate": str(record.ALT[0]) if record.ALT else None,
            "quality_score": record.QUAL,
            "filter_status": record.FILTER,
            "info": info_dict,
            "format": list(record.FORMAT) if record.FORMAT else [],
            "samples": samples,
            
            # Additional extracted fields for convenience
            "allele_frequency": self._extract_af_from_info(info_dict),
            "total_depth": self._extract_dp_from_info(info_dict),
            "variant_type": self._determine_variant_type(record.REF, str(record.ALT[0]) if record.ALT else "")
        }
    
    def _tabix_line_to_dict(self, line: str) -> Dict[str, Any]:
        """Convert tabix line to dictionary (basic parsing)"""
        fields = line.strip().split('\t')
        
        if len(fields) < 8:
            raise ValueError(f"Invalid VCF line: {line}")
        
        # Parse INFO field
        info_dict = {}
        info_string = fields[7]
        if info_string != '.':
            for item in info_string.split(';'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    info_dict[key] = value
                else:
                    info_dict[item] = True
        
        # Parse sample data if present
        samples = []
        if len(fields) > 9:
            format_fields = fields[8].split(':') if fields[8] != '.' else []
            for i, sample_data in enumerate(fields[9:]):
                sample_values = sample_data.split(':')
                sample_dict = {
                    "name": f"SAMPLE_{i}",
                    "data": {}
                }
                
                for j, fmt_field in enumerate(format_fields):
                    if j < len(sample_values):
                        sample_dict["data"][fmt_field] = sample_values[j]
                
                samples.append(sample_dict)
        
        return {
            "chromosome": fields[0],
            "position": int(fields[1]),
            "id": fields[2] if fields[2] != '.' else None,
            "reference": fields[3],
            "alternate": fields[4],
            "quality_score": float(fields[5]) if fields[5] != '.' else None,
            "filter_status": fields[6].split(';') if fields[6] != '.' else ['PASS'],
            "info": info_dict,
            "format": fields[8].split(':') if len(fields) > 8 and fields[8] != '.' else [],
            "samples": samples,
            
            # Additional extracted fields
            "allele_frequency": self._extract_af_from_info(info_dict),
            "total_depth": self._extract_dp_from_info(info_dict),
            "variant_type": self._determine_variant_type(fields[3], fields[4])
        }
    
    def _extract_af_from_info(self, info_dict: Dict[str, Any]) -> Optional[float]:
        """Extract allele frequency from INFO field"""
        for af_field in ['AF', 'VAF', 'FREQ']:
            if af_field in info_dict:
                try:
                    af_value = info_dict[af_field]
                    if isinstance(af_value, list):
                        return float(af_value[0])
                    return float(af_value)
                except (ValueError, TypeError):
                    continue
        return None
    
    def _extract_dp_from_info(self, info_dict: Dict[str, Any]) -> Optional[int]:
        """Extract depth from INFO field"""
        for dp_field in ['DP', 'DEPTH']:
            if dp_field in info_dict:
                try:
                    return int(info_dict[dp_field])
                except (ValueError, TypeError):
                    continue
        return None
    
    def _determine_variant_type(self, ref: str, alt: str) -> str:
        """Determine variant type from REF and ALT"""
        if not alt or alt == '.':
            return 'unknown'
        
        if len(ref) == 1 and len(alt) == 1:
            return 'SNV'
        elif len(ref) > len(alt):
            return 'deletion'
        elif len(ref) < len(alt):
            return 'insertion'
        else:
            return 'complex'
    
    def query_region(self, chrom: str, start: Optional[int] = None, end: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query variants in a specific genomic region
        
        Args:
            chrom: Chromosome name
            start: Start position (1-based, optional)
            end: End position (1-based, optional)
            
        Returns:
            List of variant dictionaries in the region
        """
        if not self.is_indexed:
            logger.warning(f"VCF file not indexed, performing full scan for region query")
            return self._query_region_full_scan(chrom, start, end)
        
        # Build region string
        if start and end:
            region = f"{chrom}:{start}-{end}"
        elif start:
            region = f"{chrom}:{start}-{start+1000000}"  # Default to 1MB window
        else:
            region = chrom
        
        variants = list(self.iterate_variants(region=region))
        logger.debug(f"Found {len(variants)} variants in region {region}")
        
        return variants
    
    def _query_region_full_scan(self, chrom: str, start: Optional[int], end: Optional[int]) -> List[Dict[str, Any]]:
        """Query region by scanning entire file (fallback when not indexed)"""
        variants = []
        
        for variant in self.iterate_variants():
            # Check chromosome
            if variant["chromosome"] != chrom:
                continue
            
            # Check position range
            pos = variant["position"]
            if start is not None and pos < start:
                continue
            if end is not None and pos > end:
                continue
            
            variants.append(variant)
        
        return variants
    
    def ensure_bgzip_and_index(self, output_path: Optional[Path] = None, force: bool = False) -> Path:
        """
        Ensure VCF file is bgzipped and tabix indexed
        
        Args:
            output_path: Output path for bgzipped file (optional)
            force: Force recreation even if already exists
            
        Returns:
            Path to bgzipped and indexed VCF file
        """
        if output_path is None:
            if self.is_gzipped:
                output_path = self.vcf_path
            else:
                output_path = Path(str(self.vcf_path) + '.gz')
        
        # Check if already properly formatted
        if output_path.exists() and not force:
            handler = VCFFileHandler(output_path)
            if handler.is_gzipped and handler.is_indexed:
                logger.debug(f"VCF already bgzipped and indexed: {output_path}")
                return output_path
        
        # Create bgzipped version if needed
        if not self.is_gzipped or force:
            logger.info(f"Creating bgzipped VCF: {output_path}")
            self._create_bgzipped_vcf(output_path)
        
        # Create tabix index
        bgzipped_handler = VCFFileHandler(output_path)
        bgzipped_handler.create_tabix_index(force=force)
        
        return output_path
    
    def _create_bgzipped_vcf(self, output_path: Path):
        """Create bgzipped VCF file"""
        try:
            # Use pysam to create properly bgzipped file
            with pysam.VariantFile(str(self.vcf_path)) as input_vcf:
                with pysam.VariantFile(str(output_path), 'w', header=input_vcf.header) as output_vcf:
                    for record in input_vcf:
                        output_vcf.write(record)
            
            logger.info(f"Created bgzipped VCF: {output_path}")
            
        except Exception as e:
            raise ValidationError(
                error_type="bgzip_creation_error",
                message=f"Failed to create bgzipped VCF: {e}",
                details={
                    "input_path": str(self.vcf_path),
                    "output_path": str(output_path),
                    "error": str(e)
                }
            )


def detect_vcf_file_type(file_path: Path) -> Dict[str, Any]:
    """
    Detect VCF file type and characteristics
    
    Args:
        file_path: Path to potential VCF file
        
    Returns:
        Dictionary with file type information
    """
    file_path = Path(file_path)
    
    result = {
        "is_vcf": False,
        "is_gzipped": False,
        "is_indexed": False,
        "is_tabix_index": False,
        "file_type": "unknown",
        "can_process": False
    }
    
    # Check file extensions
    if file_path.suffix == '.vcf':
        result["is_vcf"] = True
        result["file_type"] = "vcf"
        result["can_process"] = True
        
    elif file_path.suffixes == ['.vcf', '.gz']:
        result["is_vcf"] = True
        result["is_gzipped"] = True
        result["file_type"] = "vcf.gz"
        result["can_process"] = True
        
        # Check for index
        tbi_path = Path(str(file_path) + '.tbi')
        csi_path = Path(str(file_path) + '.csi')
        result["is_indexed"] = tbi_path.exists() or csi_path.exists()
        
    elif file_path.suffixes == ['.vcf', '.gz', '.tbi']:
        result["is_tabix_index"] = True
        result["file_type"] = "tabix_index"
        result["can_process"] = False
        
    elif file_path.suffix == '.tbi':
        result["is_tabix_index"] = True
        result["file_type"] = "tabix_index"
        result["can_process"] = False
        
    elif file_path.suffix == '.csi':
        result["is_tabix_index"] = True
        result["file_type"] = "csi_index"
        result["can_process"] = False
    
    return result


def get_vcf_handler(vcf_path: Path, auto_index: bool = False) -> VCFFileHandler:
    """
    Get VCF handler with optional auto-indexing
    
    Args:
        vcf_path: Path to VCF file
        auto_index: Automatically create index if missing
        
    Returns:
        VCFFileHandler instance
    """
    handler = VCFFileHandler(vcf_path)
    
    if auto_index and handler.is_gzipped and not handler.is_indexed:
        logger.info(f"Auto-creating tabix index for: {vcf_path}")
        handler.create_tabix_index()
    
    return handler


def validate_vcf_files(*vcf_paths: Path) -> Dict[Path, Dict[str, Any]]:
    """
    Validate multiple VCF files
    
    Args:
        vcf_paths: Paths to VCF files to validate
        
    Returns:
        Dictionary mapping file paths to validation results
    """
    results = {}
    
    for vcf_path in vcf_paths:
        try:
            file_type = detect_vcf_file_type(vcf_path)
            
            if file_type["can_process"]:
                handler = VCFFileHandler(vcf_path)
                stats = handler.get_file_stats()
                
                results[vcf_path] = {
                    "valid": True,
                    "file_type": file_type,
                    "stats": stats
                }
            else:
                results[vcf_path] = {
                    "valid": False,
                    "file_type": file_type,
                    "reason": f"Cannot process file type: {file_type['file_type']}"
                }
                
        except Exception as e:
            results[vcf_path] = {
                "valid": False,
                "error": str(e)
            }
    
    return results