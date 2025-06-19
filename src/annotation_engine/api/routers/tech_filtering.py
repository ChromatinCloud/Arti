"""
Technical filtering API endpoints for pre-processing VCF files
"""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..core.config import settings
from ..validators.vcf_validator import VCFValidator, MetadataValidator, AnalysisMode, VCFValidationError


router = APIRouter(prefix="/api/v1/tech-filtering", tags=["technical-filtering"])


class SampleMetadata(BaseModel):
    patient_uid: Optional[str] = None
    case_id: Optional[str] = None
    oncotree_code: Optional[str] = None
    tumor_purity: Optional[float] = None
    specimen_type: Optional[str] = None


class FilteringRequest(BaseModel):
    mode: str  # 'tumor-only' or 'tumor-normal'
    assay: str = "default_assay"
    input_vcf: str  # Can be single file or comma-separated list for TN
    filters: Dict[str, any]
    metadata: Optional[SampleMetadata] = None
    tumor_sample_name: Optional[str] = None  # For multi-sample VCF
    normal_sample_name: Optional[str] = None  # For multi-sample VCF


class FilteringResponse(BaseModel):
    success: bool
    output_vcf: Optional[str] = None
    variant_counts: Optional[Dict[str, int]] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


class BCFtoolsFilterBuilder:
    """Build sequential bcftools commands based on filter selections"""
    
    def __init__(self, mode: str, assay: str):
        self.mode = mode
        self.assay = assay
        self.commands = []
        self.temp_files = []
        
        # Load assay configuration
        config_path = Path(__file__).parent.parent.parent.parent.parent / f"resources/assay/{assay}/config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Default configuration if assay config not found"""
        return {
            "assay_info": {
                "genome_build": "grch38"
            }
        }
    
    def _get_ref_file_path(self, ref_type: str) -> Path:
        """Get full path to reference file"""
        resources_base = Path(__file__).parent.parent.parent.parent.parent / "resources"
        genome_build = self.config.get("assay_info", {}).get("genome_build", "grch38")
        
        if ref_type in ["blacklist_ref", "gnomad_freq"]:
            # Reference genome files
            if ref_type == "blacklist_ref":
                return resources_base / f"reference/genome/{genome_build}/blacklist.{genome_build}.bed.gz"
            elif ref_type == "gnomad_freq":
                return resources_base / f"reference/genome/{genome_build}/gnomad.freq.vcf.gz"
        else:
            # Assay-specific files
            if ref_type == "panel_bed":
                return resources_base / f"assay/{self.assay}/panel.bed"
            elif ref_type == "blacklist_assay":
                return resources_base / f"assay/{self.assay}/blacklist.assay.bed"
        
        return Path("")  # Return empty path if not found
    
    def add_filter(self, filter_id: str, params: any, enabled: bool = True):
        """Add appropriate bcftools command based on filter type"""
        if not enabled:
            return
            
        if filter_id == "FILTER_PASS" and params:
            self.commands.append("bcftools view -f PASS")
            
        elif filter_id == "MIN_QUAL":
            self.commands.append(f"bcftools filter -e 'QUAL<{params}'")
            
        elif filter_id == "MIN_GQ":
            self.commands.append(f"bcftools filter -S . -e 'FMT/GQ<{params}'")
            
        elif filter_id == "MIN_DP":
            self.commands.append(f"bcftools filter -S . -e 'FMT/DP<{params}'")
            
        elif filter_id == "MIN_ALT_COUNT":
            self.commands.append(f"bcftools filter -S . -e 'FMT/AD[1]<{params}'")
            
        elif filter_id == "MIN_VAF":
            # For tumor-normal, check tumor VAF
            if self.mode == "tumor-normal":
                self.commands.append(f"bcftools filter -e 'INFO/AF<{params}'")
            else:
                self.commands.append(f"bcftools filter -e 'INFO/AF<{params}'")
                
        elif filter_id == "HET_AB_RANGE" and isinstance(params, list):
            min_ab, max_ab = params
            self.commands.append(
                f"bcftools +setGT -n . -e 'FMT/AD[1]/(FMT/AD[0]+FMT/AD[1])<{min_ab} || "
                f"FMT/AD[1]/(FMT/AD[0]+FMT/AD[1])>{max_ab}'"
            )
            
        elif filter_id == "STRAND_BIAS" and isinstance(params, list):
            fs_max, sor_max = params
            self.commands.append(f"bcftools filter -e 'INFO/FS>{fs_max} || INFO/SOR>{sor_max}'")
            
        elif filter_id == "MIN_MQ":
            self.commands.append(f"bcftools filter -e 'INFO/MQ<{params}'")
            
        elif filter_id == "ROI_ONLY" and params:
            panel_bed = self._get_ref_file_path("panel_bed")
            if panel_bed.exists():
                self.commands.append(f"bcftools view -R {panel_bed}")
                
        elif filter_id == "MAX_POP_AF":
            # This would require gnomAD annotation first
            self.commands.append(f"bcftools filter -e 'INFO/AF_popmax>{params}'")
            
        elif filter_id == "EFFECT_IMPACT" and isinstance(params, list):
            # Build VEP impact filter
            impact_expr = " && ".join([f'INFO/IMPACT!="{impact}"' for impact in params])
            self.commands.append(f"bcftools filter -e '{impact_expr}'")
            
        elif filter_id == "BLACKLIST" and params:
            blacklist_ref = self._get_ref_file_path("blacklist_ref")
            if blacklist_ref.exists():
                self.commands.append(f"bcftools isec -C -w1 -o - - {blacklist_ref}")
                
        # Tumor-normal specific filters
        elif filter_id == "NORMAL_VAF_MAX" and self.mode == "tumor-normal":
            # Filter variants with high VAF in normal
            self.commands.append(f"bcftools filter -e 'NORMAL_AF>{params}'")
            
        elif filter_id == "TUMOR_NORMAL_VAF_RATIO" and self.mode == "tumor-normal":
            # Ensure tumor VAF is significantly higher than normal
            self.commands.append(f"bcftools filter -e 'TUMOR_AF/NORMAL_AF<{params}'")
    
    def build_pipeline(self, input_vcf: str, output_vcf: str) -> List[str]:
        """Build the complete pipeline of commands"""
        if not self.commands:
            return []
            
        # Create pipeline with intermediate files
        pipeline = []
        current_input = input_vcf
        
        for i, cmd in enumerate(self.commands):
            if i == len(self.commands) - 1:
                # Last command outputs to final file
                full_cmd = f"{cmd} {current_input} -Oz -o {output_vcf}"
            else:
                # Intermediate commands use temp files
                temp_file = tempfile.mktemp(suffix=".vcf.gz")
                self.temp_files.append(temp_file)
                full_cmd = f"{cmd} {current_input} -Oz -o {temp_file}"
                current_input = temp_file
                
            pipeline.append(full_cmd)
            
        # Add indexing command
        pipeline.append(f"tabix -p vcf {output_vcf}")
        
        return pipeline
    
    def cleanup(self):
        """Remove temporary files"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)


@router.post("/apply")
async def apply_technical_filters(
    request: FilteringRequest,
    background_tasks: BackgroundTasks
) -> FilteringResponse:
    """Apply technical filters to VCF file"""
    
    import time
    start_time = time.time()
    
    # Parse input VCF paths (single or comma-separated)
    vcf_paths = [p.strip() for p in request.input_vcf.split(',')]
    
    # Validate metadata
    try:
        if request.metadata:
            metadata_dict = request.metadata.dict(exclude_none=True)
            if request.tumor_sample_name:
                metadata_dict['tumor_sample'] = request.tumor_sample_name
            if request.normal_sample_name:
                metadata_dict['normal_sample'] = request.normal_sample_name
            
            MetadataValidator.validate(metadata_dict)
    except VCFValidationError as e:
        return FilteringResponse(
            success=False,
            error=f"Metadata validation failed: {str(e)}"
        )
    
    # Validate VCF files against mode
    validator = VCFValidator()
    try:
        analysis_mode = AnalysisMode.TUMOR_ONLY if request.mode == "tumor-only" else AnalysisMode.TUMOR_NORMAL
        validation_result = validator.validate_vcf_for_mode(
            vcf_paths, 
            analysis_mode,
            metadata_dict if request.metadata else None
        )
    except VCFValidationError as e:
        return FilteringResponse(
            success=False,
            error=f"VCF validation failed: {str(e)}"
        )
    
    # For multi-sample VCFs in TN mode, we need to split samples
    if validation_result.get('multi_sample') and len(vcf_paths) == 1:
        # TODO: Implement sample splitting for multi-sample VCFs
        # For now, process as-is with a warning
        print(f"Multi-sample VCF detected with samples: {validation_result['samples']}")
    
    # Create output filename
    output_dir = Path("out/filtered_vcfs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"filtered_{uuid.uuid4().hex[:8]}.vcf.gz"
    output_path = output_dir / output_filename
    
    # Build filter pipeline
    builder = BCFtoolsFilterBuilder(request.mode, request.assay)
    
    # Add filters based on request
    for filter_id, value in request.filters.items():
        # Check if filter is enabled (for checkbox filters)
        if isinstance(value, bool):
            enabled = value
            value = True
        else:
            enabled = True
            
        builder.add_filter(filter_id, value, enabled)
    
    # Get pipeline commands
    commands = builder.build_pipeline(request.input_vcf, str(output_path))
    
    if not commands:
        return FilteringResponse(
            success=False,
            error="No filters selected"
        )
    
    try:
        # Execute commands sequentially
        for cmd in commands:
            print(f"Executing: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Command failed: {result.stderr}")
        
        # Get variant counts
        input_count = get_variant_count(request.input_vcf)
        output_count = get_variant_count(str(output_path))
        
        # Clean up temp files in background
        background_tasks.add_task(builder.cleanup)
        
        processing_time = time.time() - start_time
        
        return FilteringResponse(
            success=True,
            output_vcf=str(output_path),
            variant_counts={
                "input": input_count,
                "filtered": output_count
            },
            processing_time=processing_time
        )
        
    except Exception as e:
        builder.cleanup()
        return FilteringResponse(
            success=False,
            error=str(e)
        )


@router.get("/variant-count")
async def get_variant_count_endpoint(vcf_path: str) -> Dict[str, int]:
    """Get number of variants in a VCF file"""
    try:
        count = get_variant_count(vcf_path)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_variant_count(vcf_path: str) -> int:
    """Count variants in VCF file using bcftools"""
    try:
        # Use bcftools to count variants
        cmd = f"bcftools view -H {vcf_path} | wc -l"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return int(result.stdout.strip())
        else:
            # Fallback: try without bcftools
            if vcf_path.endswith(".gz"):
                cmd = f"zgrep -v '^#' {vcf_path} | wc -l"
            else:
                cmd = f"grep -v '^#' {vcf_path} | wc -l"
                
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return int(result.stdout.strip())
            
    except Exception:
        return 0


@router.get("/download")
async def download_filtered_vcf(file: str):
    """Download filtered VCF file"""
    from fastapi.responses import FileResponse
    
    file_path = Path(file)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/gzip"
    )