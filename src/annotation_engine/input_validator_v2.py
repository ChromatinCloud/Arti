"""
Input Validator V2 Implementation

Enhanced validator that follows the InputValidatorProtocol interface.
Validates and normalizes input data for the annotation pipeline, ensuring
all VCF files meet quality requirements and contain necessary fields.
"""

import re
import gzip
import json
import logging
from typing import Optional, List, Dict, Any, Tuple, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from .interfaces.validation_interfaces import (
    ValidatedInput,
    ValidatedVCF,
    PatientContext,
    ValidationResult,
    ValidationError,
    ValidationStatus,
    SampleType,
    InputValidatorProtocol
)

logger = logging.getLogger(__name__)


class InputValidatorV2(InputValidatorProtocol):
    """
    Enhanced input validator that implements the protocol interface
    
    Key improvements over V1:
    - Follows standardized interface for integration with workflow router
    - More comprehensive VCF quality checks
    - Better error reporting with structured ValidationError objects
    - Validates depth and quality metrics for clinical confidence
    """
    
    # Required INFO fields for clinical reporting
    REQUIRED_INFO_FIELDS = {
        "DP",  # Total depth - critical for confidence
    }
    
    # Recommended INFO fields
    RECOMMENDED_INFO_FIELDS = {
        "AF", "VAF", "FREQ",  # Allele frequency alternatives
        "MQ",  # Mapping quality
        "QD",  # Quality by depth
        "FS",  # Fisher strand bias
        "SOR",  # Strand odds ratio
    }
    
    # Required FORMAT fields per sample
    REQUIRED_FORMAT_FIELDS = {
        "GT",  # Genotype
        "DP",  # Sample depth
        "AD",  # Allelic depths - critical for VAF calculation
    }
    
    # Minimum quality thresholds
    MIN_VARIANTS_REQUIRED = 1
    MIN_DEPTH_WARNING = 20  # Warn if median depth < 20
    MIN_QUAL_WARNING = 30   # Warn if median QUAL < 30
    
    def __init__(self, oncotree_path: Optional[Path] = None):
        self.oncotree_codes = self._load_oncotree_codes(oncotree_path)
        self._validated_vcfs_cache = {}
        
    def validate(self,
                tumor_vcf_path: Path,
                patient_uid: str,
                case_id: str,
                oncotree_code: str,
                normal_vcf_path: Optional[Path] = None,
                tumor_purity: Optional[float] = None,
                purple_output_dir: Optional[Path] = None,
                requested_outputs: Optional[List[str]] = None,
                **kwargs) -> ValidationResult:
        """
        Main validation entry point
        
        Validates all inputs and returns ValidatedInput for the workflow router
        """
        errors = []
        warnings = []
        
        try:
            # Convert string paths to Path objects if needed
            tumor_vcf_path = Path(tumor_vcf_path)
            if normal_vcf_path:
                normal_vcf_path = Path(normal_vcf_path)
            if purple_output_dir:
                purple_output_dir = Path(purple_output_dir)
            
            # Validate tumor VCF
            logger.info(f"Validating tumor VCF: {tumor_vcf_path}")
            tumor_vcf, vcf_errors, vcf_warnings = self._validate_vcf_with_errors(
                tumor_vcf_path, SampleType.TUMOR
            )
            errors.extend(vcf_errors)
            warnings.extend(vcf_warnings)
            
            # Validate normal VCF if provided
            normal_vcf = None
            if normal_vcf_path:
                logger.info(f"Validating normal VCF: {normal_vcf_path}")
                normal_vcf, vcf_errors, vcf_warnings = self._validate_vcf_with_errors(
                    normal_vcf_path, SampleType.NORMAL
                )
                errors.extend(vcf_errors)
                warnings.extend(vcf_warnings)
                
                # Validate pairing
                if tumor_vcf and normal_vcf:
                    pairing_errors = self._validate_vcf_pairing(tumor_vcf, normal_vcf)
                    errors.extend(pairing_errors)
            
            # Validate patient context
            logger.info("Validating patient context")
            patient_context = None
            try:
                patient_context = self.validate_patient_context(
                    patient_uid, case_id, oncotree_code
                )
            except ValueError as e:
                errors.append(ValidationError(
                    field="patient_context",
                    message=str(e),
                    severity="error"
                ))
            
            # Validate additional parameters
            if tumor_purity is not None:
                if not isinstance(tumor_purity, (int, float)):
                    errors.append(ValidationError(
                        field="tumor_purity",
                        message=f"Tumor purity must be a number, got {type(tumor_purity).__name__}"
                    ))
                elif not 0.0 <= tumor_purity <= 1.0:
                    errors.append(ValidationError(
                        field="tumor_purity",
                        message=f"Tumor purity must be between 0 and 1, got {tumor_purity}"
                    ))
            
            if purple_output_dir and not purple_output_dir.exists():
                warnings.append(ValidationError(
                    field="purple_output_dir",
                    message=f"PURPLE output directory not found: {purple_output_dir}",
                    severity="warning"
                ))
            
            # Validate output formats
            valid_outputs = {"json", "phenopacket", "va", "tsv", "vcf"}
            requested_outputs = requested_outputs or ["json"]
            invalid_outputs = set(requested_outputs) - valid_outputs
            if invalid_outputs:
                errors.append(ValidationError(
                    field="requested_outputs",
                    message=f"Invalid output formats: {invalid_outputs}. Valid: {valid_outputs}",
                    severity="error"
                ))
            
            # Determine analysis type
            analysis_type = "tumor_normal" if normal_vcf else "tumor_only"
            
            # Build validated input if no errors
            if not errors and tumor_vcf and patient_context:
                validated_input = ValidatedInput(
                    tumor_vcf=tumor_vcf,
                    normal_vcf=normal_vcf,
                    patient=patient_context,
                    analysis_type=analysis_type,
                    requested_outputs=requested_outputs,
                    tumor_purity=tumor_purity,
                    purple_output_dir=purple_output_dir,
                    vrs_normalize=kwargs.get("vrs_normalize", False),
                    export_phenopacket="phenopacket" in requested_outputs or kwargs.get("export_phenopacket", False),
                    export_va="va" in requested_outputs or kwargs.get("export_va", False),
                    validation_timestamp=datetime.utcnow().isoformat(),
                    validation_warnings=warnings if warnings else None
                )
                
                return ValidationResult(
                    status=ValidationStatus.VALID if not warnings else ValidationStatus.WARNING,
                    validated_input=validated_input,
                    warnings=warnings
                )
            
        except Exception as e:
            logger.error(f"Validation failed with unexpected error: {e}", exc_info=True)
            errors.append(ValidationError(
                field="general",
                message=f"Unexpected validation error: {str(e)}",
                severity="error"
            ))
        
        return ValidationResult(
            status=ValidationStatus.INVALID,
            errors=errors,
            warnings=warnings
        )
    
    def validate_vcf(self, vcf_path: Path, sample_type: SampleType) -> ValidatedVCF:
        """
        Validate a VCF file - interface method
        
        Raises ValueError if validation fails
        """
        validated_vcf, errors, warnings = self._validate_vcf_with_errors(vcf_path, sample_type)
        
        if errors:
            error_messages = [e.message for e in errors]
            raise ValueError(f"VCF validation failed: {'; '.join(error_messages)}")
            
        return validated_vcf
    
    def _validate_vcf_with_errors(self, 
                                 vcf_path: Path, 
                                 sample_type: SampleType) -> Tuple[Optional[ValidatedVCF], List[ValidationError], List[ValidationError]]:
        """
        Comprehensive VCF validation with detailed error reporting
        
        Returns: (ValidatedVCF or None, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check file exists and is readable
        if not vcf_path.exists():
            errors.append(ValidationError(
                field=f"{sample_type.value}_vcf",
                message=f"VCF file not found: {vcf_path}",
                severity="error"
            ))
            return None, errors, warnings
        
        if not vcf_path.is_file():
            errors.append(ValidationError(
                field=f"{sample_type.value}_vcf",
                message=f"Path is not a file: {vcf_path}",
                severity="error"
            ))
            return None, errors, warnings
        
        # Check if gzipped
        is_gzipped = vcf_path.suffix == ".gz"
        open_func = gzip.open if is_gzipped else open
        mode = "rt" if is_gzipped else "r"
        
        try:
            # Parse VCF headers and collect metadata
            headers = []
            info_fields = {}
            format_fields = set()
            sample_names = []
            genome_version = "Unknown"
            has_standard_headers = False
            
            with open_func(vcf_path, mode) as f:
                line_count = 0
                for line in f:
                    line_count += 1
                    line = line.strip()
                    
                    if line.startswith("##"):
                        headers.append(line)
                        
                        # Parse INFO fields
                        if line.startswith("##INFO="):
                            info_match = re.match(r'##INFO=<ID=([^,]+),.*>', line)
                            if info_match:
                                info_fields[info_match.group(1)] = line
                        
                        # Parse FORMAT fields
                        elif line.startswith("##FORMAT="):
                            format_match = re.match(r'##FORMAT=<ID=([^,]+),.*>', line)
                            if format_match:
                                format_fields.add(format_match.group(1))
                        
                        # Detect genome version
                        if "reference" in line.lower() or "assembly" in line.lower():
                            if any(ref in line for ref in ["GRCh37", "hg19", "b37"]):
                                genome_version = "GRCh37"
                            elif any(ref in line for ref in ["GRCh38", "hg38"]):
                                genome_version = "GRCh38"
                        
                        # Check for required headers
                        if line.startswith("##fileformat=VCF"):
                            has_standard_headers = True
                            
                    elif line.startswith("#CHROM"):
                        # Parse sample names
                        columns = line.split("\t")
                        if len(columns) >= 9:
                            sample_names = columns[9:]
                        break
                    
                    # Prevent reading entire file in header parsing
                    if line_count > 10000:
                        errors.append(ValidationError(
                            field=f"{sample_type.value}_vcf",
                            message="VCF header exceeds 10000 lines",
                            severity="error"
                        ))
                        return None, errors, warnings
            
            # Validate headers
            if not has_standard_headers:
                errors.append(ValidationError(
                    field=f"{sample_type.value}_vcf_header",
                    message="Missing required VCF header: ##fileformat=VCFv",
                    severity="error"
                ))
            
            if not sample_names:
                errors.append(ValidationError(
                    field=f"{sample_type.value}_vcf_samples",
                    message="No samples found in VCF",
                    severity="error"
                ))
                return None, errors, warnings
            
            # Validate INFO fields - Important for clinical confidence
            missing_required_info = self.REQUIRED_INFO_FIELDS - set(info_fields.keys())
            if missing_required_info:
                warnings.append(ValidationError(
                    field=f"{sample_type.value}_vcf_info",
                    message=f"Missing INFO field DP (depth). This is critical for variant quality assessment. "
                           f"Clinical confidence scores may be affected.",
                    severity="warning",
                    details={"missing_fields": list(missing_required_info)}
                ))
            
            # Check for allele frequency fields
            af_fields = {"AF", "VAF", "FREQ"}
            if not any(field in info_fields for field in af_fields):
                warnings.append(ValidationError(
                    field=f"{sample_type.value}_vcf_info",
                    message="No allele frequency fields (AF/VAF/FREQ) found in INFO. "
                           "Will rely on FORMAT/AD for VAF calculation.",
                    severity="warning"
                ))
            
            # Validate FORMAT fields
            missing_format = self.REQUIRED_FORMAT_FIELDS - format_fields
            if missing_format:
                errors.append(ValidationError(
                    field=f"{sample_type.value}_vcf_format",
                    message=f"Missing required FORMAT fields: {missing_format}. "
                           f"These are essential for VAF calculation and genotyping.",
                    severity="error",
                    details={"missing_fields": list(missing_format)}
                ))
            
            # Sample validation
            if sample_type == SampleType.NORMAL and len(sample_names) > 1:
                warnings.append(ValidationError(
                    field=f"{sample_type.value}_vcf_samples",
                    message=f"Normal VCF contains {len(sample_names)} samples. "
                           f"Will use first sample: {sample_names[0]}",
                    severity="warning",
                    details={"all_samples": sample_names}
                ))
            
            # Now scan variants for quality metrics
            variant_stats = self._analyze_variant_quality(
                vcf_path, open_func, mode, sample_type
            )
            
            # Add warnings based on variant analysis
            if variant_stats["variant_count"] == 0:
                errors.append(ValidationError(
                    field=f"{sample_type.value}_vcf_variants",
                    message="VCF contains no variants",
                    severity="error"
                ))
                return None, errors, warnings
            
            if variant_stats["variant_count"] < self.MIN_VARIANTS_REQUIRED:
                warnings.append(ValidationError(
                    field=f"{sample_type.value}_vcf_variants",
                    message=f"VCF contains only {variant_stats['variant_count']} variants",
                    severity="warning"
                ))
            
            # Check depth statistics
            if variant_stats["median_depth"] is not None:
                if variant_stats["median_depth"] < self.MIN_DEPTH_WARNING:
                    warnings.append(ValidationError(
                        field=f"{sample_type.value}_vcf_depth",
                        message=f"Low median depth: {variant_stats['median_depth']}x. "
                               f"Recommend ≥{self.MIN_DEPTH_WARNING}x for confident variant calling. "
                               f"Low depth may affect tier assignment confidence.",
                        severity="warning",
                        details={"median_depth": variant_stats["median_depth"]}
                    ))
            else:
                warnings.append(ValidationError(
                    field=f"{sample_type.value}_vcf_depth",
                    message="No depth information available. Cannot assess sequencing quality. "
                           "This will impact confidence scoring.",
                    severity="warning"
                ))
            
            # Check quality scores
            if variant_stats["median_qual"] is not None:
                if variant_stats["median_qual"] < self.MIN_QUAL_WARNING:
                    warnings.append(ValidationError(
                        field=f"{sample_type.value}_vcf_quality",
                        message=f"Low median quality score: {variant_stats['median_qual']}. "
                               f"Recommend QUAL ≥{self.MIN_QUAL_WARNING} for confident calls.",
                        severity="warning",
                        details={"median_qual": variant_stats["median_qual"]}
                    ))
            
            # Build validated VCF object
            validated_vcf = ValidatedVCF(
                path=vcf_path,
                sample_type=sample_type,
                sample_names=sample_names,
                variant_count=variant_stats["variant_count"],
                has_genotypes="GT" in format_fields,
                has_allele_frequencies=variant_stats["has_af_info"],
                genome_version=genome_version,
                normalized_chromosomes=variant_stats["normalized_chromosomes"]
            )
            
            # Add quality summary to details
            validated_vcf.quality_summary = {
                "median_depth": variant_stats["median_depth"],
                "median_qual": variant_stats["median_qual"],
                "has_depth_info": variant_stats["has_depth_info"],
                "low_depth_fraction": variant_stats.get("low_depth_fraction", 0)
            }
            
            return validated_vcf, errors, warnings
            
        except Exception as e:
            errors.append(ValidationError(
                field=f"{sample_type.value}_vcf",
                message=f"Error reading VCF file: {str(e)}",
                severity="error"
            ))
            return None, errors, warnings
    
    def _analyze_variant_quality(self, 
                               vcf_path: Path,
                               open_func,
                               mode: str,
                               sample_type: SampleType) -> Dict[str, Any]:
        """
        Analyze variant quality metrics from VCF
        
        Returns statistics about depth, quality, and other metrics
        """
        variant_count = 0
        depths = []
        quals = []
        normalized_chromosomes = None
        has_af_info = False
        has_depth_info = False
        low_depth_count = 0
        
        with open_func(vcf_path, mode) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                    
                variant_count += 1
                fields = line.strip().split("\t")
                
                if len(fields) < 8:
                    continue
                
                # Check chromosome format on first variant
                if variant_count == 1:
                    chrom = fields[0]
                    normalized_chromosomes = chrom.startswith("chr")
                
                # Parse QUAL
                try:
                    qual = float(fields[5]) if fields[5] != "." else None
                    if qual is not None:
                        quals.append(qual)
                except:
                    pass
                
                # Parse INFO for depth and AF
                info = fields[7]
                info_dict = self._parse_info_field(info)
                
                # Check for depth in INFO
                if "DP" in info_dict:
                    has_depth_info = True
                    try:
                        depth = int(info_dict["DP"])
                        depths.append(depth)
                        if depth < self.MIN_DEPTH_WARNING:
                            low_depth_count += 1
                    except:
                        pass
                
                # Also check FORMAT field for sample depth if available
                if len(fields) > 9 and not has_depth_info:
                    format_field = fields[8]
                    if "DP" in format_field:
                        format_values = fields[9].split(":")
                        format_keys = format_field.split(":")
                        if "DP" in format_keys:
                            dp_index = format_keys.index("DP")
                            if dp_index < len(format_values):
                                try:
                                    depth = int(format_values[dp_index])
                                    depths.append(depth)
                                    has_depth_info = True
                                    if depth < self.MIN_DEPTH_WARNING:
                                        low_depth_count += 1
                                except:
                                    pass
                
                # Check for AF fields
                if any(af in info_dict for af in ["AF", "VAF", "FREQ"]):
                    has_af_info = True
                
                # Sample first 1000 variants for statistics
                if variant_count >= 1000:
                    break
        
        # Calculate statistics
        median_depth = None
        median_qual = None
        low_depth_fraction = 0
        
        if depths:
            depths.sort()
            median_depth = depths[len(depths) // 2]
            low_depth_fraction = low_depth_count / len(depths)
            
        if quals:
            quals.sort()
            median_qual = quals[len(quals) // 2]
        
        return {
            "variant_count": variant_count,
            "median_depth": median_depth,
            "median_qual": median_qual,
            "normalized_chromosomes": normalized_chromosomes,
            "has_af_info": has_af_info,
            "has_depth_info": has_depth_info,
            "low_depth_fraction": low_depth_fraction
        }
    
    def _parse_info_field(self, info_str: str) -> Dict[str, str]:
        """Parse VCF INFO field into dictionary"""
        info_dict = {}
        if info_str == ".":
            return info_dict
            
        for item in info_str.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                info_dict[key] = value
            else:
                info_dict[item] = "true"
                
        return info_dict
    
    def _validate_vcf_pairing(self, 
                            tumor_vcf: ValidatedVCF,
                            normal_vcf: ValidatedVCF) -> List[ValidationError]:
        """
        Validate that tumor and normal VCFs are properly paired
        """
        errors = []
        
        # Check genome versions match
        if tumor_vcf.genome_version != normal_vcf.genome_version:
            errors.append(ValidationError(
                field="vcf_pairing",
                message=f"Genome version mismatch: tumor={tumor_vcf.genome_version}, "
                       f"normal={normal_vcf.genome_version}",
                severity="error"
            ))
        
        # Check chromosome naming consistency
        if tumor_vcf.normalized_chromosomes != normal_vcf.normalized_chromosomes:
            errors.append(ValidationError(
                field="vcf_pairing",
                message=f"Chromosome naming inconsistent: tumor uses "
                       f"{'chr prefix' if tumor_vcf.normalized_chromosomes else 'no prefix'}, "
                       f"normal uses {'chr prefix' if normal_vcf.normalized_chromosomes else 'no prefix'}",
                severity="error"
            ))
        
        return errors
    
    def validate_patient_context(self,
                               patient_uid: str,
                               case_id: str,
                               oncotree_code: str) -> PatientContext:
        """
        Validate patient and clinical context
        """
        # Validate patient UID
        if not patient_uid or not patient_uid.strip():
            raise ValueError("Patient UID is required")
        
        patient_uid = patient_uid.strip()
        if not self._is_valid_patient_uid(patient_uid):
            raise ValueError(
                f"Invalid patient UID format: {patient_uid}. "
                f"Must be alphanumeric with optional hyphens or underscores."
            )
        
        # Validate case ID
        if not case_id or not case_id.strip():
            raise ValueError("Case ID is required")
        
        case_id = case_id.strip()
        
        # Validate OncoTree code
        if not oncotree_code or not oncotree_code.strip():
            raise ValueError("OncoTree code is required")
        
        oncotree_code = oncotree_code.strip().upper()
        
        if oncotree_code not in self.oncotree_codes:
            # Try to find close matches
            close_matches = self._find_close_oncotree_matches(oncotree_code)
            if close_matches:
                raise ValueError(
                    f"Unknown OncoTree code: {oncotree_code}. "
                    f"Did you mean one of: {', '.join(close_matches)}?"
                )
            else:
                # List some common codes
                common_codes = ["LUAD", "BRCA", "PRAD", "COAD", "SKCM", "OV", "GBM", "HNSC", "THCA", "STAD"]
                examples = [c for c in common_codes if c in self.oncotree_codes][:5]
                raise ValueError(
                    f"Unknown OncoTree code: {oncotree_code}. "
                    f"Examples of valid codes: {', '.join(examples)}"
                )
        
        # Get cancer information
        cancer_info = self.oncotree_codes[oncotree_code]
        
        return PatientContext(
            patient_uid=patient_uid,
            case_id=case_id,
            cancer_type=oncotree_code,
            cancer_display_name=cancer_info.get("name", oncotree_code),
            primary_site=cancer_info.get("primary_site"),
            stage=None,  # Could be added as parameter
            prior_treatments=None,
            clinical_notes=None
        )
    
    def _is_valid_patient_uid(self, uid: str) -> bool:
        """Validate patient UID format"""
        # Allow alphanumeric with hyphens, underscores
        # Must start with letter or number
        return bool(re.match(r'^[A-Za-z0-9][A-Za-z0-9\-_]*$', uid))
    
    def _find_close_oncotree_matches(self, code: str) -> List[str]:
        """Find OncoTree codes similar to the input"""
        matches = []
        code_upper = code.upper()
        
        # Exact prefix matches
        for valid_code in self.oncotree_codes:
            if valid_code.startswith(code_upper) or code_upper.startswith(valid_code):
                matches.append(valid_code)
        
        # If no prefix matches, try edit distance
        if not matches and len(code) >= 3:
            for valid_code in self.oncotree_codes:
                if self._edit_distance(code_upper, valid_code) <= 1:
                    matches.append(valid_code)
        
        return sorted(matches)[:5]  # Return top 5 matches
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """Simple edit distance calculation"""
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _load_oncotree_codes(self, oncotree_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
        """Load OncoTree code mappings"""
        # Default path
        if oncotree_path is None:
            oncotree_path = Path(__file__).parent / "data" / "oncotree_codes.json"
        
        # If file doesn't exist, use embedded subset
        if not oncotree_path.exists():
            logger.warning(f"OncoTree file not found at {oncotree_path}, using embedded subset")
            return self._get_embedded_oncotree_codes()
        
        try:
            with open(oncotree_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load OncoTree codes: {e}")
            return self._get_embedded_oncotree_codes()
    
    def _get_embedded_oncotree_codes(self) -> Dict[str, Dict[str, str]]:
        """Embedded subset of common OncoTree codes"""
        return {
            # Lung
            "LUAD": {"name": "Lung Adenocarcinoma", "primary_site": "Lung", "tissue": "Lung"},
            "LUSC": {"name": "Lung Squamous Cell Carcinoma", "primary_site": "Lung", "tissue": "Lung"},
            "SCLC": {"name": "Small Cell Lung Cancer", "primary_site": "Lung", "tissue": "Lung"},
            "NSCLC": {"name": "Non-Small Cell Lung Cancer", "primary_site": "Lung", "tissue": "Lung"},
            
            # Breast
            "BRCA": {"name": "Invasive Breast Carcinoma", "primary_site": "Breast", "tissue": "Breast"},
            "IDC": {"name": "Breast Invasive Ductal Carcinoma", "primary_site": "Breast", "tissue": "Breast"},
            "ILC": {"name": "Breast Invasive Lobular Carcinoma", "primary_site": "Breast", "tissue": "Breast"},
            
            # Colorectal
            "COAD": {"name": "Colon Adenocarcinoma", "primary_site": "Colon", "tissue": "Bowel"},
            "READ": {"name": "Rectal Adenocarcinoma", "primary_site": "Rectum", "tissue": "Bowel"},
            "COADREAD": {"name": "Colorectal Adenocarcinoma", "primary_site": "Colorectum", "tissue": "Bowel"},
            
            # Prostate
            "PRAD": {"name": "Prostate Adenocarcinoma", "primary_site": "Prostate", "tissue": "Prostate"},
            
            # Skin
            "SKCM": {"name": "Cutaneous Melanoma", "primary_site": "Skin", "tissue": "Skin"},
            "MEL": {"name": "Melanoma", "primary_site": "Skin", "tissue": "Skin"},
            
            # Brain
            "GBM": {"name": "Glioblastoma Multiforme", "primary_site": "Brain", "tissue": "CNS/Brain"},
            "LGG": {"name": "Brain Lower Grade Glioma", "primary_site": "Brain", "tissue": "CNS/Brain"},
            
            # Ovarian
            "OV": {"name": "Ovarian Serous Cystadenocarcinoma", "primary_site": "Ovary", "tissue": "Ovary"},
            "HGSOC": {"name": "High-Grade Serous Ovarian Cancer", "primary_site": "Ovary", "tissue": "Ovary"},
            
            # Pancreatic
            "PAAD": {"name": "Pancreatic Adenocarcinoma", "primary_site": "Pancreas", "tissue": "Pancreas"},
            
            # Head and Neck
            "HNSC": {"name": "Head and Neck Squamous Cell Carcinoma", "primary_site": "Head and Neck", "tissue": "Head and Neck"},
            
            # Thyroid
            "THCA": {"name": "Thyroid Carcinoma", "primary_site": "Thyroid", "tissue": "Thyroid"},
            "THPA": {"name": "Papillary Thyroid Cancer", "primary_site": "Thyroid", "tissue": "Thyroid"},
            
            # Stomach
            "STAD": {"name": "Stomach Adenocarcinoma", "primary_site": "Stomach", "tissue": "Stomach"},
            
            # Bladder
            "BLCA": {"name": "Bladder Urothelial Carcinoma", "primary_site": "Bladder", "tissue": "Bladder"},
            
            # Kidney
            "KIRC": {"name": "Kidney Renal Clear Cell Carcinoma", "primary_site": "Kidney", "tissue": "Kidney"},
            "KIRP": {"name": "Kidney Renal Papillary Cell Carcinoma", "primary_site": "Kidney", "tissue": "Kidney"},
            
            # Liver
            "LIHC": {"name": "Liver Hepatocellular Carcinoma", "primary_site": "Liver", "tissue": "Liver"},
            "CHOL": {"name": "Cholangiocarcinoma", "primary_site": "Bile Duct", "tissue": "Biliary Tract"},
            
            # Blood
            "AML": {"name": "Acute Myeloid Leukemia", "primary_site": "Blood", "tissue": "Myeloid"},
            "ALL": {"name": "Acute Lymphoblastic Leukemia", "primary_site": "Blood", "tissue": "Lymphoid"},
            "CLL": {"name": "Chronic Lymphocytic Leukemia", "primary_site": "Blood", "tissue": "Lymphoid"},
            "DLBCL": {"name": "Diffuse Large B-Cell Lymphoma", "primary_site": "Lymph Node", "tissue": "Lymphoid"},
            "MM": {"name": "Multiple Myeloma", "primary_site": "Bone Marrow", "tissue": "Myeloid"},
        }