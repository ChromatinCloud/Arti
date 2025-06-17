"""
Input validation schemas using Pydantic v2

Defines comprehensive validation schemas for CLI and API inputs,
extending the schemas defined in SCHEMA_VALIDATION.md
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, validator
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from datetime import datetime
import re

from ..models import AnalysisType


class BaseSchema(BaseModel):
    """Base configuration for all validation schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        validate_default=True
    )


class CLIInputSchema(BaseSchema):
    """Schema for CLI input validation"""
    
    # Input files (mutually exclusive with dual input)
    input: Optional[Path] = Field(None, description="Input VCF file path (legacy single input)")
    tumor_vcf: Optional[Path] = Field(None, description="Tumor sample VCF file")
    normal_vcf: Optional[Path] = Field(None, description="Normal sample VCF file (optional)")
    api_mode: bool = Field(False, description="API mode flag")
    
    # Analysis type (auto-detected or explicit)
    analysis_type: Optional[AnalysisType] = Field(None, description="Analysis workflow type")
    
    # Case identifiers
    case_uid: str = Field(..., min_length=1, max_length=255, description="Case unique identifier")
    patient_uid: Optional[str] = Field(None, min_length=1, max_length=255, description="Patient unique identifier")
    
    # Clinical context
    cancer_type: str = Field(..., description="Cancer type for annotation context")
    oncotree_id: Optional[str] = Field(None, max_length=50, description="OncoTree disease code")
    tissue_type: str = Field("primary_tumor", description="Tissue type")
    
    # Tumor purity information
    tumor_purity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Estimated tumor purity (0.0-1.0)")
    purple_output: Optional[Path] = Field(None, description="Path to HMF PURPLE output directory")
    
    # Output configuration
    output: Path = Field(Path("./results"), description="Output directory")
    output_format: str = Field("all", description="Output format")
    
    # Analysis parameters
    genome: str = Field("GRCh38", description="Reference genome build")
    guidelines: List[str] = Field(["AMP_ACMG", "CGC_VICC", "ONCOKB"], description="Clinical guidelines")
    
    # Quality control
    min_depth: int = Field(10, ge=1, le=1000, description="Minimum read depth")
    min_vaf: float = Field(0.05, ge=0.0, le=1.0, description="Minimum variant allele frequency")
    skip_qc: bool = Field(False, description="Skip quality control")
    
    # Advanced options
    config: Optional[Path] = Field(None, description="Custom configuration file")
    kb_bundle: Optional[Path] = Field(None, description="Knowledge base bundle path")
    dry_run: bool = Field(False, description="Dry run mode")
    
    # Logging
    verbose: int = Field(0, ge=0, le=3, description="Verbosity level")
    quiet: bool = Field(False, description="Quiet mode")
    log_file: Optional[Path] = Field(None, description="Log file path")
    
    @field_validator('case_uid', 'patient_uid')
    @classmethod
    def validate_ids(cls, v):
        """Validate ID format"""
        if v and not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('IDs must contain only alphanumeric characters, hyphens, and underscores')
        return v
    
    @field_validator('input', 'tumor_vcf', 'normal_vcf')
    @classmethod
    def validate_vcf_file(cls, v):
        """Validate VCF file path and extension"""
        if v is None:
            return v
            
        if not v.suffix.lower() in ['.vcf', '.gz']:
            raise ValueError('VCF file must be .vcf or .vcf.gz format')
        
        # For .gz files, check if it's .vcf.gz
        if v.suffix.lower() == '.gz' and not v.stem.endswith('.vcf'):
            raise ValueError('Compressed files must be .vcf.gz format')
        
        return v
    
    @model_validator(mode='before')
    @classmethod
    def auto_detect_analysis_type(cls, values):
        """Auto-detect analysis type if not explicitly set"""
        if not isinstance(values, dict):
            return values
            
        analysis_type = values.get('analysis_type')
        if analysis_type is not None:
            return values
        
        # Check input patterns to auto-detect
        input_file = values.get('input')
        tumor_vcf = values.get('tumor_vcf')
        normal_vcf = values.get('normal_vcf')
        
        # Legacy single input - assume tumor-only
        if input_file and not tumor_vcf and not normal_vcf:
            values['analysis_type'] = AnalysisType.TUMOR_ONLY
        
        # Dual input with normal - tumor-normal
        elif tumor_vcf and normal_vcf:
            values['analysis_type'] = AnalysisType.TUMOR_NORMAL
        
        # Only tumor VCF specified - tumor-only
        elif tumor_vcf and not normal_vcf:
            values['analysis_type'] = AnalysisType.TUMOR_ONLY
        
        # Default to tumor-only if unclear
        else:
            values['analysis_type'] = AnalysisType.TUMOR_ONLY
            
        return values
    
    @model_validator(mode='after')
    @classmethod
    def validate_input_consistency(cls, values):
        """Validate input file consistency"""
        input_file = values.input
        tumor_vcf = values.tumor_vcf
        normal_vcf = values.normal_vcf
        analysis_type = values.analysis_type
        
        # Cannot mix legacy and new input styles
        if input_file and (tumor_vcf or normal_vcf):
            raise ValueError('Cannot specify both --input and --tumor-vcf/--normal-vcf')
        
        # Normal VCF requires tumor VCF
        if normal_vcf and not tumor_vcf:
            raise ValueError('--normal-vcf requires --tumor-vcf')
        
        # Analysis type consistency
        if analysis_type == AnalysisType.TUMOR_NORMAL and not normal_vcf:
            raise ValueError('TUMOR_NORMAL analysis requires --normal-vcf')
        
        return values
    
    @field_validator('cancer_type')
    @classmethod
    def validate_cancer_type(cls, v):
        """Validate cancer type"""
        valid_types = {
            'lung_adenocarcinoma', 'lung_squamous', 'breast_cancer',
            'colorectal_cancer', 'melanoma', 'ovarian_cancer',
            'pancreatic_cancer', 'prostate_cancer', 'glioblastoma',
            'acute_myeloid_leukemia', 'other'
        }
        if v not in valid_types:
            raise ValueError(f'Cancer type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('genome')
    @classmethod
    def validate_genome_build(cls, v):
        """Validate genome build"""
        if v not in ['GRCh37', 'GRCh38']:
            raise ValueError('Genome build must be GRCh37 or GRCh38')
        return v
    
    @field_validator('guidelines')
    @classmethod
    def validate_guidelines(cls, v):
        """Validate clinical guidelines"""
        valid_guidelines = {'AMP_ACMG', 'CGC_VICC', 'ONCOKB'}
        if not all(g in valid_guidelines for g in v):
            raise ValueError(f'Guidelines must be from: {", ".join(valid_guidelines)}')
        return v
    
    @field_validator('tissue_type')
    @classmethod
    def validate_tissue_type(cls, v):
        """Validate tissue type"""
        valid_types = {'primary_tumor', 'metastatic', 'recurrent', 'normal', 'unknown'}
        if v not in valid_types:
            raise ValueError(f'Tissue type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v):
        """Validate output format"""
        valid_formats = {'json', 'tsv', 'html', 'all'}
        if v not in valid_formats:
            raise ValueError(f'Output format must be one of: {", ".join(valid_formats)}')
        return v


class VCFVariantSchema(BaseSchema):
    """Schema for individual VCF variant validation"""
    
    chromosome: str = Field(..., description="Chromosome")
    position: int = Field(..., gt=0, description="Genomic position")
    reference: str = Field(..., min_length=1, description="Reference allele")
    alternate: str = Field(..., min_length=1, description="Alternate allele")
    quality: Optional[float] = Field(None, ge=0, description="Variant quality score")
    filter_status: Optional[str] = Field(None, description="Filter status")
    
    # INFO field data
    depth: Optional[int] = Field(None, ge=0, description="Read depth")
    allele_frequency: Optional[float] = Field(None, ge=0, le=1, description="Allele frequency")
    
    @field_validator('chromosome')
    @classmethod
    def validate_chromosome(cls, v):
        """Validate chromosome notation"""
        # Remove 'chr' prefix if present
        if v.startswith('chr'):
            v = v[3:]
        
        # Validate chromosome value
        valid_chroms = set([str(i) for i in range(1, 23)] + ['X', 'Y', 'M', 'MT'])
        if v not in valid_chroms:
            raise ValueError(f'Invalid chromosome: {v}')
        
        return v
    
    @field_validator('reference', 'alternate')
    @classmethod
    def validate_alleles(cls, v):
        """Validate allele sequences"""
        if not re.match(r'^[ATCGN-]+$', v.upper()):
            raise ValueError('Alleles must contain only valid nucleotide characters (ATCGN-)')
        return v.upper()


class AnalysisRequest(BaseSchema):
    """Complete analysis request schema"""
    
    # Case information
    case_uid: str = Field(..., description="Case unique identifier")
    patient_uid: str = Field(..., description="Patient unique identifier")
    
    # Input data
    vcf_file_path: Optional[str] = Field(None, description="VCF file path (legacy)")
    tumor_vcf_path: Optional[str] = Field(None, description="Tumor VCF file path")
    normal_vcf_path: Optional[str] = Field(None, description="Normal VCF file path")
    
    # Analysis workflow
    analysis_type: AnalysisType = Field(..., description="Analysis workflow type")
    
    # Clinical context
    cancer_type: str = Field(..., description="Cancer type")
    oncotree_id: Optional[str] = Field(None, description="OncoTree ID")
    tissue_type: str = Field("primary_tumor", description="Tissue type")
    
    # Analysis configuration
    output_directory: str = Field(..., description="Output directory")
    output_format: str = Field("all", description="Output format")
    genome_build: str = Field("GRCh37", description="Reference genome")
    guidelines: List[str] = Field(..., description="Clinical guidelines")
    
    # Quality control
    quality_filters: Dict[str, Any] = Field(..., description="Quality filter settings")
    
    # Tumor purity
    tumor_purity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Estimated tumor purity (0.0-1.0)")
    
    # VCF validation results
    vcf_summary: Dict[str, Any] = Field({}, description="VCF validation summary")
    
    # Optional configurations
    config_file: Optional[str] = Field(None, description="Configuration file path")
    kb_bundle: Optional[str] = Field(None, description="Knowledge base bundle path")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Request creation time")
    analysis_id: Optional[str] = Field(None, description="Analysis identifier")


class APIVariantInput(BaseSchema):
    """Schema for single variant API input"""
    
    # Genomic coordinates
    chromosome: str = Field(..., description="Chromosome")
    position: int = Field(..., gt=0, description="Genomic position") 
    reference: str = Field(..., min_length=1, description="Reference allele")
    alternate: str = Field(..., min_length=1, description="Alternate allele")
    
    # Optional annotation
    gene_symbol: Optional[str] = Field(None, max_length=100, description="Gene symbol")
    hgvsc: Optional[str] = Field(None, max_length=500, description="HGVS cDNA notation")
    hgvsp: Optional[str] = Field(None, max_length=500, description="HGVS protein notation")
    
    # Quality metrics
    depth: Optional[int] = Field(None, ge=0, description="Read depth")
    variant_allele_frequency: Optional[float] = Field(None, ge=0, le=1, description="VAF")
    quality_score: Optional[float] = Field(None, ge=0, description="Quality score")
    
    @field_validator('chromosome')
    @classmethod
    def normalize_chromosome(cls, v):
        """Normalize chromosome notation"""
        if v.startswith('chr'):
            return v[3:]
        return v


class APIAnalysisRequest(BaseSchema):
    """Schema for API analysis requests"""
    
    # Case information
    case_uid: str = Field(..., min_length=1, max_length=255)
    patient_uid: str = Field(..., min_length=1, max_length=255)
    
    # Input data (mutually exclusive)
    vcf_file: Optional[bytes] = Field(None, description="VCF file content")
    single_variant: Optional[APIVariantInput] = Field(None, description="Single variant input")
    
    # Clinical context
    cancer_type: str = Field(..., description="Cancer type")
    oncotree_id: Optional[str] = Field(None, max_length=50)
    tissue_type: str = Field("primary_tumor", description="Tissue type")
    
    # Analysis options
    guidelines: List[str] = Field(["AMP_ACMG", "CGC_VICC", "ONCOKB"], description="Guidelines")
    genome_build: str = Field("GRCh37", description="Genome build")
    
    # Quality filters
    min_depth: int = Field(10, ge=1, le=1000)
    min_vaf: float = Field(0.05, ge=0.0, le=1.0)
    skip_qc: bool = Field(False)
    
    @field_validator('case_uid', 'patient_uid')
    @classmethod
    def validate_api_ids(cls, v):
        """Validate API ID format"""
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('IDs must contain only alphanumeric characters, hyphens, and underscores')
        return v
    
    @model_validator(mode='after')
    @classmethod
    def validate_input_exclusivity(cls, values):
        """Ensure mutually exclusive input types"""
        vcf_file = values.vcf_file
        single_variant = values.single_variant
        
        if not (vcf_file or single_variant):
            raise ValueError('Either vcf_file or single_variant must be provided')
        
        if vcf_file and single_variant:
            raise ValueError('Cannot provide both vcf_file and single_variant')
        
        return values