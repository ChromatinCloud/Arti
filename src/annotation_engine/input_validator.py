"""
Input Validation Module

Validates VCF files and clinical metadata for the annotation pipeline.
Handles format validation, sample detection, and data standardization.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import gzip

from .models import AnalysisType

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, any]
    
    def add_error(self, error: str):
        """Add an error to the result"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a warning to the result"""
        self.warnings.append(warning)


class VCFValidator:
    """Validates VCF file format and content"""
    
    # Required VCF header fields
    REQUIRED_HEADERS = [
        "##fileformat=VCF",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
    ]
    
    # Required INFO fields for proper annotation
    REQUIRED_INFO_FIELDS = {
        "DP": "Total depth",
        "AF": "Allele frequency", 
        "AD": "Allelic depths"
    }
    
    # Chromosome naming patterns
    CHR_PATTERNS = {
        "with_chr": re.compile(r"^chr([0-9]+|[XYM])$"),
        "without_chr": re.compile(r"^([0-9]+|[XYM])$")
    }
    
    def __init__(self):
        self.samples: List[str] = []
        self.info_fields: Set[str] = set()
        self.format_fields: Set[str] = set()
        self.chr_style: Optional[str] = None
        
    def validate_vcf(self, vcf_path: Path) -> ValidationResult:
        """
        Validate a VCF file
        
        Args:
            vcf_path: Path to VCF file
            
        Returns:
            ValidationResult with status and metadata
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            metadata={}
        )
        
        if not vcf_path.exists():
            result.add_error(f"VCF file not found: {vcf_path}")
            return result
        
        try:
            # Open file (handle gzip if needed)
            if vcf_path.suffix == ".gz":
                f = gzip.open(vcf_path, 'rt')
            else:
                f = open(vcf_path, 'r')
            
            with f:
                # Validate headers
                self._validate_headers(f, result)
                
                # Validate variants (first 100)
                self._validate_variants(f, result, max_variants=100)
            
            # Add metadata
            result.metadata.update({
                "samples": self.samples,
                "sample_count": len(self.samples),
                "info_fields": list(self.info_fields),
                "format_fields": list(self.format_fields),
                "chromosome_style": self.chr_style
            })
            
        except Exception as e:
            result.add_error(f"Failed to read VCF: {str(e)}")
        
        return result
    
    def _validate_headers(self, file_handle, result: ValidationResult):
        """Validate VCF headers"""
        found_fileformat = False
        found_column_header = False
        
        for line in file_handle:
            line = line.strip()
            
            if not line:
                continue
                
            # Check for required headers
            if line.startswith("##fileformat=VCF"):
                found_fileformat = True
                version_match = re.match(r"##fileformat=VCFv([\d\.]+)", line)
                if version_match:
                    result.metadata["vcf_version"] = version_match.group(1)
            
            # Parse INFO fields
            elif line.startswith("##INFO="):
                info_match = re.match(r'##INFO=<ID=([^,]+)', line)
                if info_match:
                    self.info_fields.add(info_match.group(1))
            
            # Parse FORMAT fields
            elif line.startswith("##FORMAT="):
                format_match = re.match(r'##FORMAT=<ID=([^,]+)', line)
                if format_match:
                    self.format_fields.add(format_match.group(1))
            
            # Parse column header
            elif line.startswith("#CHROM"):
                found_column_header = True
                columns = line.split('\t')
                
                # Validate required columns
                required_cols = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
                for col in required_cols:
                    if col not in columns[:8]:
                        result.add_error(f"Missing required column: {col}")
                
                # Extract sample names
                if len(columns) > 9:
                    self.samples = columns[9:]
                    
                break  # Stop after column header
        
        # Check required headers were found
        if not found_fileformat:
            result.add_error("Missing ##fileformat header")
        if not found_column_header:
            result.add_error("Missing #CHROM column header")
        
        # Check for required INFO fields
        for field, desc in self.REQUIRED_INFO_FIELDS.items():
            if field not in self.info_fields:
                result.add_warning(f"Missing recommended INFO field {field} ({desc})")
    
    def _validate_variants(self, file_handle, result: ValidationResult, max_variants: int = 100):
        """Validate variant records"""
        variant_count = 0
        chromosomes_seen = set()
        
        for line in file_handle:
            line = line.strip()
            
            if not line or line.startswith("#"):
                continue
            
            variant_count += 1
            if variant_count > max_variants:
                break
            
            fields = line.split('\t')
            
            # Validate field count
            expected_fields = 8 if not self.samples else 9 + len(self.samples)
            if len(fields) < 8:
                result.add_error(f"Variant line {variant_count}: insufficient fields ({len(fields)} < 8)")
                continue
            
            # Extract fields
            chrom = fields[0]
            pos = fields[1]
            ref = fields[3]
            alt = fields[4]
            
            # Validate chromosome
            chromosomes_seen.add(chrom)
            if not self.chr_style:
                if self.CHR_PATTERNS["with_chr"].match(chrom):
                    self.chr_style = "with_chr"
                elif self.CHR_PATTERNS["without_chr"].match(chrom):
                    self.chr_style = "without_chr"
                else:
                    result.add_warning(f"Non-standard chromosome name: {chrom}")
            
            # Validate position
            try:
                pos_int = int(pos)
                if pos_int <= 0:
                    result.add_error(f"Invalid position at line {variant_count}: {pos}")
            except ValueError:
                result.add_error(f"Non-numeric position at line {variant_count}: {pos}")
            
            # Validate alleles
            if not re.match(r'^[ACGTN]+$', ref, re.IGNORECASE):
                result.add_error(f"Invalid reference allele at line {variant_count}: {ref}")
            if not all(re.match(r'^[ACGTN]+$', a, re.IGNORECASE) for a in alt.split(',')):
                result.add_error(f"Invalid alternate allele at line {variant_count}: {alt}")
        
        result.metadata["variant_count_checked"] = variant_count
        result.metadata["chromosomes_seen"] = list(chromosomes_seen)


class SampleDetector:
    """Detects and validates sample relationships"""
    
    def detect_sample_type(self, samples: List[str]) -> Tuple[AnalysisType, Dict[str, str]]:
        """
        Detect sample type from sample names
        
        Args:
            samples: List of sample names from VCF
            
        Returns:
            Tuple of (AnalysisType, sample mapping dict)
        """
        if not samples:
            return AnalysisType.TUMOR_ONLY, {}
        
        # Single sample - tumor only
        if len(samples) == 1:
            return AnalysisType.TUMOR_ONLY, {"tumor": samples[0]}
        
        # Two samples - check for tumor/normal pattern
        if len(samples) == 2:
            sample_map = self._match_tumor_normal_pair(samples)
            if sample_map:
                return AnalysisType.TUMOR_NORMAL, sample_map
        
        # Multiple samples - need user input
        logger.warning(f"Multiple samples detected ({len(samples)}), defaulting to first as tumor-only")
        return AnalysisType.TUMOR_ONLY, {"tumor": samples[0]}
    
    def _match_tumor_normal_pair(self, samples: List[str]) -> Optional[Dict[str, str]]:
        """
        Match tumor/normal pairs based on naming patterns
        
        Common patterns:
        - sample_T / sample_N
        - sample_tumor / sample_normal
        - sample_t / sample_n
        - sample.tumor / sample.normal
        """
        if len(samples) != 2:
            return None
        
        s1, s2 = samples
        
        # Direct pattern checks - simpler and more reliable
        # Check for tumor/normal keywords
        if "tumor" in s1.lower() and "normal" in s2.lower():
            return {"tumor": s1, "normal": s2}
        elif "tumor" in s2.lower() and "normal" in s1.lower():
            return {"tumor": s2, "normal": s1}
        
        # Check for T/N suffixes
        # Pattern: same prefix, different T/N suffix
        for sep in ['_', '-', '.']:
            # Check _T/_N pattern
            if s1.endswith(f"{sep}T") and s2.endswith(f"{sep}N"):
                prefix1 = s1[:-2]
                prefix2 = s2[:-2]
                if prefix1 == prefix2:
                    return {"tumor": s1, "normal": s2}
            elif s2.endswith(f"{sep}T") and s1.endswith(f"{sep}N"):
                prefix1 = s1[:-2]
                prefix2 = s2[:-2]
                if prefix1 == prefix2:
                    return {"tumor": s2, "normal": s1}
        
        # Check T1/N1 or similar patterns
        t_match = re.match(r'^(.*)T(\d*)$', s1)
        n_match = re.match(r'^(.*)N(\d*)$', s2)
        if t_match and n_match:
            if t_match.group(1) == n_match.group(1) and t_match.group(2) == n_match.group(2):
                return {"tumor": s1, "normal": s2}
        
        t_match = re.match(r'^(.*)T(\d*)$', s2)
        n_match = re.match(r'^(.*)N(\d*)$', s1)
        if t_match and n_match:
            if t_match.group(1) == n_match.group(1) and t_match.group(2) == n_match.group(2):
                return {"tumor": s2, "normal": s1}
        
        return None


class ChromosomeStandardizer:
    """Standardizes chromosome naming conventions"""
    
    @staticmethod
    def standardize_chromosome(chrom: str, target_style: str = "with_chr") -> str:
        """
        Standardize chromosome name to target style
        
        Args:
            chrom: Input chromosome name
            target_style: "with_chr" or "without_chr"
            
        Returns:
            Standardized chromosome name
        """
        # Already in target style
        if target_style == "with_chr" and chrom.startswith("chr"):
            return chrom
        elif target_style == "without_chr" and not chrom.startswith("chr"):
            return chrom
        
        # Convert to target style
        if target_style == "with_chr" and not chrom.startswith("chr"):
            return f"chr{chrom}"
        elif target_style == "without_chr" and chrom.startswith("chr"):
            return chrom[3:]
        
        return chrom


class InputValidator:
    """Main input validation orchestrator"""
    
    def __init__(self):
        self.vcf_validator = VCFValidator()
        self.sample_detector = SampleDetector()
        self.chr_standardizer = ChromosomeStandardizer()
    
    def validate_input(self, 
                      vcf_path: Path,
                      patient_uid: Optional[str] = None,
                      case_uid: Optional[str] = None,
                      oncotree_code: Optional[str] = None) -> ValidationResult:
        """
        Validate all inputs for annotation pipeline
        
        Args:
            vcf_path: Path to VCF file
            patient_uid: Patient identifier
            case_uid: Case identifier
            oncotree_code: OncoTree disease code
            
        Returns:
            Comprehensive ValidationResult
        """
        # Start with VCF validation
        result = self.vcf_validator.validate_vcf(vcf_path)
        
        if not result.is_valid:
            return result
        
        # Detect sample type
        samples = result.metadata.get("samples", [])
        analysis_type, sample_map = self.sample_detector.detect_sample_type(samples)
        
        result.metadata["analysis_type"] = analysis_type
        result.metadata["sample_mapping"] = sample_map
        
        # Validate identifiers
        if patient_uid and not self._validate_uid(patient_uid):
            result.add_warning(f"Invalid patient UID format: {patient_uid}")
        
        if case_uid and not self._validate_uid(case_uid):
            result.add_warning(f"Invalid case UID format: {case_uid}")
        
        # Validate OncoTree code (basic check)
        if oncotree_code and not re.match(r'^[A-Z0-9_]+$', oncotree_code):
            result.add_warning(f"Invalid OncoTree code format: {oncotree_code}")
        
        return result
    
    def _validate_uid(self, uid: str) -> bool:
        """Validate UID format (alphanumeric + dash/underscore)"""
        return bool(re.match(r'^[A-Za-z0-9_-]+$', uid))