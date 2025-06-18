"""
Input Validation Interfaces

Defines the contract for input validation that Person A will implement.
"""

from typing import Protocol, Optional, List, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class SampleType(str, Enum):
    """Types of samples in the analysis"""
    TUMOR = "tumor"
    NORMAL = "normal"
    TUMOR_ONLY = "tumor_only"
    

class ValidationStatus(str, Enum):
    """Validation result status"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class ValidationError:
    """Represents a validation error"""
    field: str
    message: str
    severity: str = "error"  # error, warning, info
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidatedVCF:
    """Validated VCF file information"""
    path: Path
    sample_type: SampleType
    sample_names: List[str]
    variant_count: int
    has_genotypes: bool
    has_allele_frequencies: bool
    genome_version: str  # GRCh37, GRCh38
    normalized_chromosomes: bool  # True if chr1 format, False if 1 format
    

@dataclass
class PatientContext:
    """Validated patient and clinical context"""
    patient_uid: str
    case_id: str
    cancer_type: str  # OncoTree code
    cancer_display_name: str  # Human readable
    primary_site: Optional[str] = None
    stage: Optional[str] = None
    prior_treatments: Optional[List[str]] = None
    clinical_notes: Optional[str] = None


@dataclass
class ValidatedInput:
    """
    Complete validated input ready for workflow routing
    
    This is the main data structure passed from InputValidator to WorkflowRouter
    """
    # VCF Information
    tumor_vcf: ValidatedVCF
    patient: PatientContext  # Patient Information
    analysis_type: str  # "tumor_only" or "tumor_normal"
    
    # Optional fields
    normal_vcf: Optional[ValidatedVCF] = None
    requested_outputs: Optional[List[str]] = None  # ["json", "phenopacket", "va"]
    
    # Optional Parameters
    tumor_purity: Optional[float] = None
    purple_output_dir: Optional[Path] = None
    
    # GA4GH Options
    vrs_normalize: bool = False
    export_phenopacket: bool = False
    export_va: bool = False
    
    # Validation Metadata
    validation_timestamp: str = None
    validation_warnings: List[ValidationError] = None
    
    def is_tumor_normal_pair(self) -> bool:
        """Check if this is a tumor-normal analysis"""
        return self.normal_vcf is not None
    
    def get_all_vcf_paths(self) -> List[Path]:
        """Get all VCF file paths"""
        paths = [self.tumor_vcf.path]
        if self.normal_vcf:
            paths.append(self.normal_vcf.path)
        return paths


@dataclass
class ValidationResult:
    """Result of validation process"""
    status: ValidationStatus
    validated_input: Optional[ValidatedInput] = None
    errors: List[ValidationError] = None
    warnings: List[ValidationError] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return self.status == ValidationStatus.VALID
    
    def get_all_messages(self) -> List[str]:
        """Get all error and warning messages"""
        messages = []
        if self.errors:
            messages.extend([f"ERROR: {e.field} - {e.message}" for e in self.errors])
        if self.warnings:
            messages.extend([f"WARNING: {w.field} - {w.message}" for w in self.warnings])
        return messages


class InputValidatorProtocol(Protocol):
    """
    Protocol that Person A's InputValidator must implement
    
    This defines the interface without implementation details
    """
    
    def validate_vcf(self, vcf_path: Path, sample_type: SampleType) -> ValidatedVCF:
        """Validate a single VCF file"""
        ...
    
    def validate_patient_context(self, 
                                patient_uid: str,
                                case_id: str,
                                oncotree_code: str) -> PatientContext:
        """Validate patient and clinical context"""
        ...
    
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
        Main validation method that returns ValidatedInput
        
        This is the primary interface method that workflow router will call
        """
        ...