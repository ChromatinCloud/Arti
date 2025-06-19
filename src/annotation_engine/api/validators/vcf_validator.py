"""
VCF validation for tumor-only and tumor-normal analysis modes

Handles:
- Single vs multi-sample VCFs
- Mode-appropriate sample counts
- Sample name extraction
- Format validation
"""

import gzip
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from enum import Enum

class VCFValidationError(Exception):
    """Custom exception for VCF validation errors"""
    pass

class AnalysisMode(str, Enum):
    TUMOR_ONLY = "tumor_only"
    TUMOR_NORMAL = "tumor_normal"

class VCFValidator:
    """Validates VCF files for compatibility with analysis mode"""
    
    def __init__(self):
        self.sample_pattern = re.compile(r'^#CHROM\s+POS\s+ID\s+REF\s+ALT\s+QUAL\s+FILTER\s+INFO\s+FORMAT\s+(.+)$')
        self.vcf_version_pattern = re.compile(r'^##fileformat=VCFv(\d+\.\d+)')
        
    def validate_vcf_for_mode(
        self, 
        vcf_paths: List[str], 
        mode: AnalysisMode,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Validate VCF file(s) against specified analysis mode
        
        Args:
            vcf_paths: List of VCF file paths (1 for TO or multi-sample TN, 2 for separate TN)
            mode: Analysis mode (tumor_only or tumor_normal)
            metadata: Optional metadata including expected sample names
            
        Returns:
            Validation result with sample information
            
        Raises:
            VCFValidationError: If validation fails
        """
        
        # Basic file existence check
        for path in vcf_paths:
            if not Path(path).exists():
                raise VCFValidationError(f"VCF file not found: {path}")
        
        # Mode-specific validation
        if mode == AnalysisMode.TUMOR_ONLY:
            return self._validate_tumor_only(vcf_paths[0], metadata)
        else:  # TUMOR_NORMAL
            if len(vcf_paths) == 1:
                # Multi-sample VCF
                return self._validate_tumor_normal_multisample(vcf_paths[0], metadata)
            elif len(vcf_paths) == 2:
                # Separate tumor and normal VCFs
                return self._validate_tumor_normal_separate(vcf_paths, metadata)
            else:
                raise VCFValidationError(
                    f"Tumor-normal mode requires either 1 multi-sample VCF or 2 separate VCFs, got {len(vcf_paths)}"
                )
    
    def _validate_tumor_only(self, vcf_path: str, metadata: Optional[Dict]) -> Dict:
        """Validate tumor-only VCF"""
        samples = self._extract_samples(vcf_path)
        
        if len(samples) == 0:
            raise VCFValidationError("No samples found in VCF header")
        elif len(samples) > 1:
            raise VCFValidationError(
                f"Tumor-only mode requires single-sample VCF, found {len(samples)} samples: {', '.join(samples)}"
            )
        
        # Validate VCF format
        version = self._get_vcf_version(vcf_path)
        if not version:
            raise VCFValidationError("Invalid VCF format: missing ##fileformat header")
        
        # Check for required fields
        self._validate_vcf_structure(vcf_path)
        
        return {
            "valid": True,
            "mode": "tumor_only",
            "samples": {
                "tumor": samples[0]
            },
            "vcf_version": version,
            "variant_count": self._count_variants(vcf_path)
        }
    
    def _validate_tumor_normal_multisample(self, vcf_path: str, metadata: Optional[Dict]) -> Dict:
        """Validate multi-sample tumor-normal VCF"""
        samples = self._extract_samples(vcf_path)
        
        if len(samples) < 2:
            raise VCFValidationError(
                f"Multi-sample tumor-normal VCF requires at least 2 samples, found {len(samples)}"
            )
        
        # Try to identify tumor and normal samples
        tumor_sample, normal_sample = self._identify_tn_samples(samples, metadata)
        
        # Validate VCF format
        version = self._get_vcf_version(vcf_path)
        if not version:
            raise VCFValidationError("Invalid VCF format: missing ##fileformat header")
        
        # Check for tumor-normal specific INFO fields
        self._validate_tn_annotations(vcf_path)
        
        return {
            "valid": True,
            "mode": "tumor_normal",
            "samples": {
                "tumor": tumor_sample,
                "normal": normal_sample,
                "all": samples
            },
            "vcf_version": version,
            "variant_count": self._count_variants(vcf_path),
            "multi_sample": True
        }
    
    def _validate_tumor_normal_separate(self, vcf_paths: List[str], metadata: Optional[Dict]) -> Dict:
        """Validate separate tumor and normal VCFs"""
        tumor_path, normal_path = vcf_paths
        
        # Extract samples from each file
        tumor_samples = self._extract_samples(tumor_path)
        normal_samples = self._extract_samples(normal_path)
        
        # Each file should have exactly one sample
        if len(tumor_samples) != 1:
            raise VCFValidationError(
                f"Tumor VCF must contain exactly 1 sample, found {len(tumor_samples)}"
            )
        if len(normal_samples) != 1:
            raise VCFValidationError(
                f"Normal VCF must contain exactly 1 sample, found {len(normal_samples)}"
            )
        
        # Validate both files have same structure
        tumor_version = self._get_vcf_version(tumor_path)
        normal_version = self._get_vcf_version(normal_path)
        
        if tumor_version != normal_version:
            raise VCFValidationError(
                f"VCF version mismatch: tumor={tumor_version}, normal={normal_version}"
            )
        
        # Check variant overlap
        tumor_variants = self._get_variant_positions(tumor_path)
        normal_variants = self._get_variant_positions(normal_path)
        overlap = tumor_variants.intersection(normal_variants)
        
        return {
            "valid": True,
            "mode": "tumor_normal",
            "samples": {
                "tumor": tumor_samples[0],
                "normal": normal_samples[0]
            },
            "vcf_version": tumor_version,
            "variant_counts": {
                "tumor": len(tumor_variants),
                "normal": len(normal_variants),
                "overlap": len(overlap)
            },
            "multi_sample": False,
            "separate_files": True
        }
    
    def _extract_samples(self, vcf_path: str) -> List[str]:
        """Extract sample names from VCF header"""
        samples = []
        
        opener = gzip.open if vcf_path.endswith('.gz') else open
        with opener(vcf_path, 'rt') as f:
            for line in f:
                if line.startswith('#CHROM'):
                    match = self.sample_pattern.match(line.strip())
                    if match:
                        samples = match.group(1).split('\t')
                    break
                elif not line.startswith('#'):
                    # Reached data lines without finding header
                    break
        
        return samples
    
    def _get_vcf_version(self, vcf_path: str) -> Optional[str]:
        """Extract VCF version from header"""
        opener = gzip.open if vcf_path.endswith('.gz') else open
        with opener(vcf_path, 'rt') as f:
            for line in f:
                if line.startswith('##fileformat='):
                    match = self.vcf_version_pattern.match(line.strip())
                    if match:
                        return match.group(1)
                elif not line.startswith('#'):
                    break
        return None
    
    def _identify_tn_samples(self, samples: List[str], metadata: Optional[Dict]) -> Tuple[str, str]:
        """
        Identify tumor and normal samples from sample names
        
        Uses common naming patterns or metadata hints
        """
        tumor_sample = None
        normal_sample = None
        
        # Check metadata for sample names
        if metadata:
            if 'tumor_sample' in metadata and metadata['tumor_sample'] in samples:
                tumor_sample = metadata['tumor_sample']
            if 'normal_sample' in metadata and metadata['normal_sample'] in samples:
                normal_sample = metadata['normal_sample']
        
        # If not in metadata, use naming heuristics
        if not tumor_sample or not normal_sample:
            for sample in samples:
                sample_lower = sample.lower()
                if any(t in sample_lower for t in ['tumor', 'cancer', 'disease', '_t']):
                    tumor_sample = sample
                elif any(n in sample_lower for n in ['normal', 'blood', 'germline', '_n']):
                    normal_sample = sample
        
        # If still not found, assume first is tumor, second is normal
        if not tumor_sample and len(samples) >= 1:
            tumor_sample = samples[0]
        if not normal_sample and len(samples) >= 2:
            normal_sample = samples[1]
        
        if not tumor_sample or not normal_sample:
            raise VCFValidationError(
                f"Could not identify tumor and normal samples from: {samples}. "
                "Please provide sample names in metadata."
            )
        
        return tumor_sample, normal_sample
    
    def _validate_vcf_structure(self, vcf_path: str):
        """Validate basic VCF structure"""
        required_columns = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT']
        
        opener = gzip.open if vcf_path.endswith('.gz') else open
        header_found = False
        
        with opener(vcf_path, 'rt') as f:
            for line in f:
                if line.startswith('#CHROM'):
                    header_found = True
                    columns = line.strip().split('\t')
                    for req_col in required_columns:
                        if req_col not in columns:
                            raise VCFValidationError(f"Missing required column: {req_col}")
                    break
        
        if not header_found:
            raise VCFValidationError("No valid VCF header found")
    
    def _validate_tn_annotations(self, vcf_path: str):
        """Check for tumor-normal specific annotations"""
        # Look for common TN caller annotations
        tn_info_fields = ['SOMATIC', 'SS', 'NORMAL_AF', 'TUMOR_AF']
        found_fields = set()
        
        opener = gzip.open if vcf_path.endswith('.gz') else open
        with opener(vcf_path, 'rt') as f:
            for line in f:
                if line.startswith('##INFO='):
                    for field in tn_info_fields:
                        if f'ID={field}' in line:
                            found_fields.add(field)
                elif not line.startswith('#'):
                    break
        
        if not found_fields:
            # Warning, not error - some TN callers don't add specific annotations
            pass
    
    def _count_variants(self, vcf_path: str) -> int:
        """Count non-header lines in VCF"""
        count = 0
        opener = gzip.open if vcf_path.endswith('.gz') else open
        
        with opener(vcf_path, 'rt') as f:
            for line in f:
                if not line.startswith('#'):
                    count += 1
        
        return count
    
    def _get_variant_positions(self, vcf_path: str) -> set:
        """Extract variant positions for overlap analysis"""
        positions = set()
        opener = gzip.open if vcf_path.endswith('.gz') else open
        
        with opener(vcf_path, 'rt') as f:
            for line in f:
                if not line.startswith('#'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 5:
                        chrom = parts[0]
                        pos = parts[1]
                        ref = parts[3]
                        alt = parts[4]
                        positions.add(f"{chrom}:{pos}:{ref}>{alt}")
        
        return positions


class MetadataValidator:
    """Validates sample metadata requirements"""
    
    REQUIRED_FIELDS = {
        "case_id": str,
        "cancer_type": str  # OncoTree code
    }
    
    OPTIONAL_FIELDS = {
        "patient_uid": str,
        "tumor_purity": (float, lambda x: 0.0 <= x <= 1.0),
        "specimen_type": str,
        "tumor_sample": str,
        "normal_sample": str
    }
    
    VALID_SPECIMEN_TYPES = ["FFPE", "Fresh Frozen", "Blood", "Buccal", "Saliva"]
    
    @classmethod
    def validate(cls, metadata: Dict) -> Dict[str, any]:
        """
        Validate metadata completeness and format
        
        Returns:
            Validation result with warnings for missing optional fields
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field, expected_type in cls.REQUIRED_FIELDS.items():
            if field not in metadata:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(metadata[field], expected_type):
                errors.append(f"Invalid type for {field}: expected {expected_type.__name__}")
        
        # Check OncoTree code format (basic validation)
        if "cancer_type" in metadata:
            oncotree_code = metadata["cancer_type"]
            if not re.match(r'^[A-Z]{2,10}$', oncotree_code):
                warnings.append(f"OncoTree code '{oncotree_code}' may be invalid (expected uppercase letters)")
        
        # Check optional fields
        for field, validator in cls.OPTIONAL_FIELDS.items():
            if field in metadata:
                value = metadata[field]
                if isinstance(validator, tuple):
                    expected_type, constraint = validator
                    if not isinstance(value, expected_type):
                        errors.append(f"Invalid type for {field}: expected {expected_type.__name__}")
                    elif not constraint(value):
                        errors.append(f"Invalid value for {field}: {value}")
                else:
                    if not isinstance(value, validator):
                        errors.append(f"Invalid type for {field}: expected {validator.__name__}")
        
        # Specimen type validation
        if "specimen_type" in metadata:
            if metadata["specimen_type"] not in cls.VALID_SPECIMEN_TYPES:
                warnings.append(
                    f"Specimen type '{metadata['specimen_type']}' not in standard list: "
                    f"{', '.join(cls.VALID_SPECIMEN_TYPES)}"
                )
        
        # Check for tumor purity in FFPE samples
        if metadata.get("specimen_type") == "FFPE" and "tumor_purity" not in metadata:
            warnings.append("Tumor purity is recommended for FFPE samples")
        
        if errors:
            raise VCFValidationError("; ".join(errors))
        
        return {
            "valid": True,
            "warnings": warnings,
            "has_oncotree_code": "cancer_type" in metadata,
            "has_tumor_purity": "tumor_purity" in metadata
        }