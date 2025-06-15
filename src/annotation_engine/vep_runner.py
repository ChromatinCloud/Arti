"""
VEP Runner Module for Somatic Variant Annotation

Executes VEP (Variant Effect Predictor) with proper plugins and parses JSON output
into VariantAnnotation objects for the annotation engine pipeline.

Supports both Docker and native VEP installations with comprehensive error handling.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import shutil
import os

from .models import VariantAnnotation, PopulationFrequency
from .validation.error_handler import ValidationError

logger = logging.getLogger(__name__)


class VEPConfiguration:
    """VEP configuration and validation"""
    
    def __init__(self, 
                 vep_command: Optional[str] = None,
                 cache_dir: Optional[Path] = None,
                 plugins_dir: Optional[Path] = None,
                 assembly: str = "GRCh37",
                 use_docker: bool = True,
                 docker_image: str = "ensemblorg/ensembl-vep:release_114.1"):
        
        self.assembly = assembly
        self.use_docker = use_docker
        self.docker_image = docker_image
        
        # Auto-detect paths
        self.repo_root = self._find_repo_root()
        self.refs_dir = self.repo_root / ".refs"
        
        # Set VEP paths
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self.refs_dir / "vep" / "cache"
            
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir)
        else:
            self.plugins_dir = self.refs_dir / "vep" / "plugins"
        
        # VEP command detection
        if vep_command:
            self.vep_command = vep_command
        else:
            self.vep_command = self._detect_vep_command()
    
    def _find_repo_root(self) -> Path:
        """Find repository root directory"""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists() or (current / "pyproject.toml").exists():
                return current
            current = current.parent
        return Path.cwd()
    
    def _detect_vep_command(self) -> str:
        """Detect available VEP command"""
        
        # Check for wrapper script first
        wrapper_script = self.repo_root / "scripts" / "vep"
        if wrapper_script.exists() and wrapper_script.is_file():
            logger.info(f"Using VEP wrapper script: {wrapper_script}")
            return str(wrapper_script)
        
        # Check for native VEP installation
        if shutil.which("vep"):
            logger.info("Using native VEP installation")
            return "vep"
        
        # Fall back to Docker
        if self.use_docker and shutil.which("docker"):
            logger.info(f"Using VEP Docker image: {self.docker_image}")
            return "docker"
        
        raise ValidationError(
            error_type="vep_not_found",
            message="VEP not found. Install VEP or run ./scripts/setup_vep.sh",
            details={
                "checked_paths": [str(wrapper_script), "vep", "docker"],
                "use_docker": self.use_docker,
                "docker_image": self.docker_image
            }
        )
    
    def validate(self) -> bool:
        """Validate VEP configuration"""
        
        if self.use_docker:
            return self._validate_docker_config()
        else:
            return self._validate_native_config()
    
    def _validate_docker_config(self) -> bool:
        """Validate Docker VEP configuration"""
        
        if not shutil.which("docker"):
            raise ValidationError(
                error_type="docker_not_found",
                message="Docker not found but use_docker=True"
            )
        
        # Check if Docker daemon is running
        try:
            subprocess.run(["docker", "info"], 
                         capture_output=True, check=True, timeout=10)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            raise ValidationError(
                error_type="docker_not_running",
                message="Docker daemon is not running"
            )
        
        return True
    
    def _validate_native_config(self) -> bool:
        """Validate native VEP configuration"""
        
        if not shutil.which("vep"):
            raise ValidationError(
                error_type="vep_not_found",
                message="VEP command not found in PATH"
            )
        
        if not self.cache_dir.exists():
            logger.warning(f"VEP cache directory not found: {self.cache_dir}")
        
        return True


class VEPRunner:
    """
    VEP (Variant Effect Predictor) runner with Docker and native support
    
    Executes VEP with proper plugins and configuration for clinical variant annotation.
    """
    
    def __init__(self, config: Optional[VEPConfiguration] = None):
        self.config = config or VEPConfiguration()
        self.config.validate()
        
        # VEP plugins for clinical annotation
        self.default_plugins = [
            "dbNSFP,{plugins_dir}/dbNSFP4.4a.gz,ALL",
            "COSMIC,{plugins_dir}/CosmicCodingMuts.normal.vcf.gz",
            "gnomADg,{plugins_dir}/gnomad.genomes.v3.1.2.sites.vcf.bgz",
            "ClinVar,{plugins_dir}/clinvar.vcf.gz,exact",
            "CADD,{plugins_dir}/whole_genome_SNVs.tsv.gz",
        ]
    
    def annotate_vcf(self, 
                    input_vcf: Path,
                    output_format: str = "json",
                    plugins: Optional[List[str]] = None) -> Union[Path, List[VariantAnnotation]]:
        """
        Annotate VCF file with VEP
        
        Args:
            input_vcf: Path to input VCF file
            output_format: Output format ("json", "vcf", or "annotations")
            plugins: List of VEP plugins to use
            
        Returns:
            Output file path (for json/vcf) or VariantAnnotation objects (for annotations)
        """
        
        logger.info(f"Starting VEP annotation: {input_vcf}")
        
        if not input_vcf.exists():
            raise ValidationError(
                error_type="file_not_found",
                message=f"Input VCF file not found: {input_vcf}"
            )
        
        # Prepare output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            if output_format == "json":
                output_file = temp_path / f"{input_vcf.stem}_vep.json"
            elif output_format == "vcf":
                output_file = temp_path / f"{input_vcf.stem}_vep.vcf"
            else:
                output_file = temp_path / f"{input_vcf.stem}_vep.json"
            
            # Build VEP command
            vep_cmd = self._build_vep_command(
                input_vcf=input_vcf,
                output_file=output_file,
                output_format=output_format,
                plugins=plugins or self.default_plugins
            )
            
            # Execute VEP
            logger.info(f"Executing VEP: {' '.join(vep_cmd[:3])}...")  # Log abbreviated command
            
            try:
                result = subprocess.run(
                    vep_cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                    check=True
                )
                
                logger.info("VEP annotation completed successfully")
                
                if result.stderr:
                    logger.debug(f"VEP stderr: {result.stderr}")
                
            except subprocess.CalledProcessError as e:
                raise ValidationError(
                    error_type="vep_execution_error",
                    message=f"VEP annotation failed: {e}",
                    details={
                        "return_code": e.returncode,
                        "stdout": e.stdout,
                        "stderr": e.stderr,
                        "command": " ".join(vep_cmd[:5])  # First few args only
                    }
                )
            except subprocess.TimeoutExpired:
                raise ValidationError(
                    error_type="vep_timeout",
                    message="VEP annotation timed out after 1 hour"
                )
            
            # Process output
            if output_format == "annotations":
                return self._parse_vep_json_to_annotations(output_file)
            else:
                # Copy output to permanent location
                permanent_output = input_vcf.parent / output_file.name
                shutil.copy2(output_file, permanent_output)
                return permanent_output
    
    def _build_vep_command(self, 
                          input_vcf: Path,
                          output_file: Path,
                          output_format: str,
                          plugins: List[str]) -> List[str]:
        """Build VEP command with appropriate arguments"""
        
        if self.config.vep_command == "docker":
            return self._build_docker_command(input_vcf, output_file, output_format, plugins)
        else:
            return self._build_native_command(input_vcf, output_file, output_format, plugins)
    
    def _build_docker_command(self, 
                             input_vcf: Path,
                             output_file: Path,
                             output_format: str,
                             plugins: List[str]) -> List[str]:
        """Build Docker VEP command"""
        
        input_dir = input_vcf.parent.absolute()
        output_dir = output_file.parent.absolute()
        
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.config.cache_dir}:/opt/vep/.vep:ro",
            "-v", f"{self.config.plugins_dir}:/opt/vep/plugins:ro",
            "-v", f"{input_dir}:/input:ro",
            "-v", f"{output_dir}:/output",
            "-w", "/input",
            self.config.docker_image,
            "vep"
        ]
        
        # Add VEP arguments
        cmd.extend(self._get_vep_args(
            input_file=f"/input/{input_vcf.name}",
            output_file=f"/output/{output_file.name}",
            output_format=output_format,
            plugins=plugins,
            cache_dir="/opt/vep/.vep",
            plugins_dir="/opt/vep/plugins"
        ))
        
        return cmd
    
    def _build_native_command(self, 
                             input_vcf: Path,
                             output_file: Path,
                             output_format: str,
                             plugins: List[str]) -> List[str]:
        """Build native VEP command"""
        
        cmd = [self.config.vep_command]
        
        cmd.extend(self._get_vep_args(
            input_file=str(input_vcf),
            output_file=str(output_file),
            output_format=output_format,
            plugins=plugins,
            cache_dir=str(self.config.cache_dir),
            plugins_dir=str(self.config.plugins_dir)
        ))
        
        return cmd
    
    def _get_vep_args(self, 
                     input_file: str,
                     output_file: str,
                     output_format: str,
                     plugins: List[str],
                     cache_dir: str,
                     plugins_dir: str) -> List[str]:
        """Get VEP arguments for annotation"""
        
        args = [
            "--input_file", input_file,
            "--output_file", output_file,
            "--format", "vcf",
            "--cache",
            "--offline",
            "--dir_cache", cache_dir,
            "--dir_plugins", plugins_dir,
            "--assembly", self.config.assembly,
            "--force_overwrite",
            "--no_stats",
            "--everything",  # Include all standard annotations
            "--terms", "SO",  # Use Sequence Ontology terms
            "--canonical",   # Mark canonical transcripts
            "--protein",     # Include protein consequences
            "--uniprot",     # Include UniProt annotations
            "--symbol",      # Include gene symbols
            "--ccds",        # Include CCDS annotations
            "--domains",     # Include protein domain annotations
            "--regulatory",  # Include regulatory features
            "--pubmed",      # Include PubMed IDs
            "--variant_class", # Include variant class
        ]
        
        # Set output format
        if output_format == "json":
            args.extend(["--json", "--most_severe"])
        elif output_format == "vcf":
            args.extend(["--vcf"])
        
        # Add plugins
        for plugin in plugins:
            formatted_plugin = plugin.format(plugins_dir=plugins_dir)
            args.extend(["--plugin", formatted_plugin])
        
        return args
    
    def _parse_vep_json_to_annotations(self, vep_json_file: Path) -> List[VariantAnnotation]:
        """Parse VEP JSON output to VariantAnnotation objects"""
        
        logger.info(f"Parsing VEP JSON output: {vep_json_file}")
        
        if not vep_json_file.exists():
            raise ValidationError(
                error_type="vep_output_missing",
                message=f"VEP output file not found: {vep_json_file}"
            )
        
        variant_annotations = []
        
        try:
            with open(vep_json_file, 'r') as f:
                vep_data = json.load(f)
            
            for variant_data in vep_data:
                annotation = self._create_variant_annotation_from_vep(variant_data)
                if annotation:
                    variant_annotations.append(annotation)
            
            logger.info(f"Parsed {len(variant_annotations)} variant annotations from VEP output")
            return variant_annotations
            
        except Exception as e:
            raise ValidationError(
                error_type="vep_parsing_error",
                message=f"Failed to parse VEP JSON output: {e}",
                details={
                    "file": str(vep_json_file),
                    "error": str(e)
                }
            )
    
    def _create_variant_annotation_from_vep(self, vep_variant: Dict[str, Any]) -> Optional[VariantAnnotation]:
        """Create VariantAnnotation from VEP JSON variant"""
        
        try:
            # Extract basic variant information
            variant_id = vep_variant.get("id", "")
            input_data = vep_variant.get("input", "").split("\t")
            
            if len(input_data) < 5:
                logger.warning(f"Insufficient variant data: {variant_id}")
                return None
            
            chromosome = input_data[0]
            position = int(input_data[1])
            reference = input_data[3]
            alternate = input_data[4]
            
            # Extract the most severe consequence
            most_severe = vep_variant.get("most_severe_consequence", "")
            
            # Get transcript consequences
            transcript_consequences = vep_variant.get("transcript_consequences", [])
            
            # Find the canonical transcript or the first one
            canonical_consequence = None
            for tc in transcript_consequences:
                if tc.get("canonical") == 1:
                    canonical_consequence = tc
                    break
            
            if not canonical_consequence and transcript_consequences:
                canonical_consequence = transcript_consequences[0]
            
            # Extract annotation details
            gene_symbol = ""
            transcript_id = ""
            consequence = [most_severe] if most_severe else []
            hgvs_c = ""
            hgvs_p = ""
            impact = ""
            
            if canonical_consequence:
                gene_symbol = canonical_consequence.get("gene_symbol", "")
                transcript_id = canonical_consequence.get("transcript_id", "")
                consequence = canonical_consequence.get("consequence_terms", [most_severe])
                hgvs_c = canonical_consequence.get("hgvsc", "")
                hgvs_p = canonical_consequence.get("hgvsp", "")
                impact = canonical_consequence.get("impact", "")
            
            # Extract colocated variants (population frequencies)
            population_frequencies = []
            colocated_variants = vep_variant.get("colocated_variants", [])
            for cv in colocated_variants:
                frequencies = cv.get("frequencies", {})
                source_db = cv.get("id", "unknown")
                for pop, freq in frequencies.items():
                    if freq is not None:
                        # Determine database from population name
                        if "gnomad" in pop.lower():
                            database = "gnomAD"
                        elif "exac" in pop.lower():
                            database = "ExAC"
                        elif "1000genomes" in pop.lower() or "1kg" in pop.lower():
                            database = "1000Genomes"
                        else:
                            database = source_db
                        
                        population_frequencies.append(PopulationFrequency(
                            database=database,
                            population=pop,
                            allele_frequency=float(freq)
                        ))
            
            # Create VariantAnnotation object
            variant_annotation = VariantAnnotation(
                chromosome=chromosome,
                position=position,
                reference=reference,
                alternate=alternate,
                gene_symbol=gene_symbol,
                transcript_id=transcript_id,
                consequence=consequence,
                hgvs_c=hgvs_c,
                hgvs_p=hgvs_p,
                impact=impact,
                
                # Population frequencies
                population_frequencies=population_frequencies,
                
                # Placeholders for evidence (to be filled by evidence aggregator)
                hotspot_evidence=[],
                functional_predictions=[],
                civic_evidence=[],
                therapeutic_implications=[],
                
                # VEP metadata
                vep_version=vep_variant.get("assembly_name", ""),
                annotation_source="VEP"
            )
            
            return variant_annotation
            
        except Exception as e:
            logger.warning(f"Failed to create variant annotation from VEP data: {e}")
            return None


def annotate_vcf_with_vep(input_vcf: Path,
                         output_format: str = "annotations",
                         config: Optional[VEPConfiguration] = None) -> Union[Path, List[VariantAnnotation]]:
    """
    Convenience function to annotate VCF with VEP
    
    Args:
        input_vcf: Path to input VCF file
        output_format: Output format ("json", "vcf", or "annotations")
        config: VEP configuration (optional)
        
    Returns:
        Output file path or list of VariantAnnotation objects
    """
    runner = VEPRunner(config)
    return runner.annotate_vcf(input_vcf, output_format)


def get_vep_version(config: Optional[VEPConfiguration] = None) -> str:
    """Get VEP version information"""
    
    config = config or VEPConfiguration()
    
    try:
        if config.vep_command == "docker":
            cmd = ["docker", "run", "--rm", config.docker_image, "vep", "--help"]
        else:
            cmd = [config.vep_command, "--help"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Parse version from help output
        for line in result.stdout.split('\n'):
            if 'ensembl-vep' in line.lower():
                return line.strip()
        
        return "VEP version unknown"
        
    except Exception as e:
        return f"VEP version check failed: {e}"