"""
VEP Runner Module for Somatic Variant Annotation

Executes VEP (Variant Effect Predictor) with proper plugins and parses JSON output
into VariantAnnotation objects for the annotation engine pipeline.

Supports both Docker and native VEP installations with comprehensive error handling.
Uses centralized VEP Docker Manager for consistent mount configurations.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import shutil
import os
import time
from tqdm import tqdm

from .models import VariantAnnotation, PopulationFrequency
from .validation.error_handler import ValidationError
from .vep_docker_manager import VEPDockerManager, VEPDockerConfig, VEPDockerMode

logger = logging.getLogger(__name__)


class VEPConfiguration:
    """VEP configuration and validation"""
    
    def __init__(self, 
                 vep_command: Optional[str] = None,
                 cache_dir: Optional[Path] = None,
                 plugins_dir: Optional[Path] = None,
                 assembly: str = "GRCh38",
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
            self.cache_dir = self.refs_dir / "functional_predictions" / "vep_cache"
            
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir)
        else:
            self.plugins_dir = self.refs_dir / "functional_predictions" / "vep_plugins"
        
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
            validation_result = self._validate_docker_config()
        else:
            validation_result = self._validate_native_config()
        
        # Validate plugin data files
        self._validate_plugin_data()
        
        return validation_result
    
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
    
    def _validate_plugin_data(self) -> None:
        """Validate VEP plugin data files existence"""
        
        missing_plugins = []
        available_plugins = []
        
        # Default plugins that should be checked
        plugin_checks = {
            "dbNSFP": self.refs_dir / "variant" / "vcf" / "dbnsfp" / "dbnsfp.vcf.gz",
            "AlphaMissense": self.refs_dir / "alphamissense" / "AlphaMissense_hg38.tsv.gz",
            "REVEL": self.refs_dir / "functional_predictions" / "plugin_data" / "pathogenicity" / "revel_with_transcript_ids",
            "SpliceAI": self.refs_dir / "spliceai" / "spliceai_scores.raw.snv.ensembl_mane.grch38.110.vcf.gz",
            "gnomAD": self.refs_dir / "population_frequencies" / "gnomad" / "gnomad.genomes.v3.1.2.sites.vcf.bgz",
            "ClinVar": self.refs_dir / "clinical_evidence" / "clinvar" / "clinvar.vcf.gz",
            "LoFtool": self.refs_dir / "functional_predictions" / "plugin_data" / "gene_constraint" / "LoFtool_scores.txt"
        }
        
        for plugin_name, plugin_path in plugin_checks.items():
            if plugin_path.exists():
                available_plugins.append(plugin_name)
            else:
                missing_plugins.append(f"{plugin_name}: {plugin_path}")
        
        if missing_plugins:
            logger.warning(f"Missing VEP plugin data files: {len(missing_plugins)}/{len(plugin_checks)}")
            for missing in missing_plugins[:5]:  # Show first 5
                logger.warning(f"  - {missing}")
            if len(missing_plugins) > 5:
                logger.warning(f"  ... and {len(missing_plugins) - 5} more")
        
        if available_plugins:
            logger.info(f"Available VEP plugins: {', '.join(available_plugins)}")
        else:
            logger.warning("No VEP plugin data files found - VEP will run with basic annotation only")


class VEPRunner:
    """
    VEP (Variant Effect Predictor) runner with Docker and native support
    
    Executes VEP with proper plugins and configuration for clinical variant annotation.
    Uses centralized VEP Docker Manager for consistent Docker operations.
    """
    
    def __init__(self, config: Optional[VEPConfiguration] = None):
        self.config = config or VEPConfiguration()
        self.config.validate()
        
        # Initialize Docker manager for Docker-based execution
        if self.config.use_docker:
            docker_config = VEPDockerConfig(
                repo_root=self.config.repo_root,
                refs_dir=self.config.refs_dir,
                cache_dir=self.config.cache_dir,
                plugins_dir=self.config.plugins_dir,
                docker_image=self.config.docker_image,
                assembly=self.config.assembly
            )
            self.docker_manager = VEPDockerManager(docker_config)
        else:
            self.docker_manager = None
        
        # VEP plugins for clinical annotation (evidence-based selection)
        # NOTE: Plugin selection rationale in ./docs/VEP_PLUGINS.md 
        # Plugins marked as "Yes-Plugin" - used via VEP for efficient consequence-dependent lookup
        # AVADA marked as "Yes-Flatfile" - used via direct file access for custom evidence aggregation
        # Some plugins excluded due to file size constraints (e.g., FATHMM_MKL)
        self.default_plugins = [
            # Core pathogenicity predictors (High Evidence) - FILES AVAILABLE ✓
            "AlphaMissense,{refs_dir}/alphamissense/AlphaMissense_hg38.tsv.gz",
            "dbNSFP,{refs_dir}/variant/vcf/dbnsfp/dbnsfp.vcf.gz,ALL",
            "FATHMM,{refs_dir}/functional_predictions/plugin_data/pathogenicity/fathmm.v2.3.SQL.gz",
            "PrimateAI,{refs_dir}/functional_predictions/plugin_data/protein_impact/PrimateAI_scores_v0.2_hg38.tsv.gz",
            "REVEL,{refs_dir}/functional_predictions/plugin_data/pathogenicity/revel_with_transcript_ids",
            "SpliceAI,{refs_dir}/spliceai/spliceai_scores.raw.snv.ensembl_mane.grch38.110.vcf.gz",
            
            # Moderate Evidence predictors - FILES AVAILABLE ✓  
            "BayesDel,{refs_dir}/functional_predictions/plugin_data/pathogenicity/BayesDel_170824_noAF.tgz",
            "Conservation,{refs_dir}/functional_predictions/plugin_data/conservation/hg38.phyloP100way.bw,phyloP100way",
            "LoFtool,{refs_dir}/functional_predictions/plugin_data/gene_constraint/LoFtool_scores.txt",
            "MaveDB,{refs_dir}/functional_predictions/plugin_data/mavedb/MaveDB_variants.tsv.gz",
            "Phenotypes,{refs_dir}/functional_predictions/plugin_data/phenotype/PhenotypesOrthologous_homo_sapiens_112_GRCh38.gff3.gz",
            "UTRAnnotator,{refs_dir}/functional_predictions/plugin_data/utr/uORF_5UTR_GRCh38_PUBLIC.txt",
            
            # Population frequency 
            "gnomAD,{refs_dir}/variant/vcf/gnomad_non_cancer/gnomad_non_cancer.vcf.gz",
            
            # Clinical evidence
            "ClinVar,{refs_dir}/clinical_evidence/clinvar/clinvar.vcf.gz,exact",
            
            # Structural variants
            "StructuralVariantOverlap,{refs_dir}/population_frequencies/gnomad/gnomad_v2.1_sv.sites.vcf.gz",
            
            # Emerging Evidence predictors - FILES AVAILABLE ✓
            "Enformer,{refs_dir}/functional_predictions/plugin_data/regulatory/enformer_grch38.vcf.gz",
            
            # API/Rule-based plugins (no external data files required)
            "GeneBe",  # Automatic ACMG flags via API/rules
            "NMD",     # NMD escape prediction via rules
            "SpliceRegion",  # Built-in VEP plugin for splice region annotation
            
            # Additional evidence predictors - FILES AVAILABLE ✓
            "EVE,{refs_dir}/functional_predictions/plugin_data/protein_impact/eve_merged.vcf",
            "PolyPhen_SIFT,{refs_dir}/functional_predictions/plugin_data/protein_impact/homo_sapiens_pangenome_PolyPhen_SIFT_20240502.db",
            
            # === UNAVAILABLE PLUGINS (Files Not Found) ===
            # These 4 plugins are unavailable and need data files to be obtained:
            
            # "ClinPred,{refs_dir}/functional_predictions/plugin_data/pathogenicity/ClinPred_scores.vcf.gz",  # ❌ Missing
            # "dbscSNV,{refs_dir}/functional_predictions/plugin_data/splicing/dbscSNV1.1_hg38.txt.gz",      # ❌ Missing
            # "VARITY,{refs_dir}/functional_predictions/plugin_data/protein_impact/VARITY_R_LOO_v1.0.tsv.gz",  # ❌ Missing (trying install.pl)
            # "gnomADc,{refs_dir}/population_frequencies/gnomad/gnomad_coverage.vcf.gz",                   # ❌ Missing
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
            
            # Execute VEP with progress indication
            logger.info(f"Executing VEP: {' '.join(vep_cmd[:3])}...")  # Log abbreviated command
            
            try:
                # Start VEP process
                process = subprocess.Popen(
                    vep_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Show progress during execution
                with tqdm(desc="VEP annotation", unit="sec", dynamic_ncols=True) as pbar:
                    start_time = time.time()
                    while process.poll() is None:
                        elapsed = time.time() - start_time
                        pbar.set_postfix(elapsed=f"{elapsed:.1f}s")
                        pbar.update(1)
                        time.sleep(1)
                    
                    # Get final result
                    stdout, stderr = process.communicate()
                    elapsed = time.time() - start_time
                    pbar.set_postfix(elapsed=f"{elapsed:.1f}s", status="complete")
                
                # Check if process succeeded
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, vep_cmd, stdout, stderr
                    )
                
                # Create result object for compatibility
                class VEPResult:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                
                result = VEPResult(process.returncode, stdout, stderr)
                logger.info(f"VEP annotation completed successfully in {elapsed:.1f} seconds")
                
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
        """Build Docker VEP command using centralized Docker manager"""
        
        if not self.docker_manager:
            raise ValidationError(
                error_type="docker_manager_not_initialized",
                message="Docker manager not initialized but Docker execution requested"
            )
        
        # Get VEP arguments for container paths
        vep_args = self._get_vep_args(
            input_file=f"/input/{input_vcf.name}",
            output_file=f"/output/{output_file.name}",
            output_format=output_format,
            plugins=plugins,
            cache_dir="/opt/vep/.vep",
            plugins_dir="/opt/vep/plugins",
            refs_dir="/.refs"  # Docker-mounted refs directory
        )
        
        # Use Docker manager to build command
        cmd = self.docker_manager.build_docker_command(
            input_file=input_vcf,
            output_file=output_file,
            vep_args=vep_args,
            mode=VEPDockerMode.ANNOTATION
        )
        
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
            plugins_dir=str(self.config.plugins_dir),
            refs_dir=str(self.config.refs_dir)
        ))
        
        return cmd
    
    def _get_vep_args(self, 
                     input_file: str,
                     output_file: str,
                     output_format: str,
                     plugins: List[str],
                     cache_dir: str,
                     plugins_dir: str,
                     refs_dir: Optional[str] = None) -> List[str]:
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
        
        # Add plugins with availability filtering
        available_plugins = self._filter_available_plugins(plugins, refs_dir or str(self.config.refs_dir))
        for plugin in available_plugins:
            formatted_plugin = plugin.format(plugins_dir=plugins_dir, refs_dir=refs_dir or str(self.config.refs_dir))
            args.extend(["--plugin", formatted_plugin])
        
        if len(available_plugins) < len(plugins):
            logger.info(f"Using {len(available_plugins)}/{len(plugins)} available VEP plugins")
        
        return args
    
    def _filter_available_plugins(self, plugins: List[str], refs_dir: str) -> List[str]:
        """Filter plugins based on data file availability"""
        
        available_plugins = []
        refs_path = Path(refs_dir)
        
        for plugin_spec in plugins:
            plugin_parts = plugin_spec.split(",")
            plugin_name = plugin_parts[0]
            
            if len(plugin_parts) > 1:
                data_file_pattern = plugin_parts[1]
                
                # Check if data file exists (handle both absolute and relative paths)
                if data_file_pattern.startswith(".refs/") or data_file_pattern.startswith("/.refs/"):
                    # Remove leading .refs/ or /.refs/ and rebuild path
                    relative_path = data_file_pattern.replace("/.refs/", "").replace(".refs/", "")
                    data_file_path = refs_path / relative_path
                else:
                    data_file_path = Path(data_file_pattern)
                
                if data_file_path.exists():
                    available_plugins.append(plugin_spec)
                else:
                    logger.debug(f"Skipping plugin {plugin_name} - data file not found: {data_file_path}")
            else:
                # Plugin with no data file requirement
                available_plugins.append(plugin_spec)
        
        return available_plugins
    
    def _select_best_transcript(self, transcript_consequences: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best transcript using prioritized criteria (MANE Select > Canonical > First)"""
        
        if not transcript_consequences:
            return None
        
        # Priority 1: MANE Select transcript
        for tc in transcript_consequences:
            if tc.get("mane_select"):
                logger.debug(f"Selected MANE Select transcript: {tc.get('transcript_id')}")
                return tc
        
        # Priority 2: MANE Plus Clinical transcript
        for tc in transcript_consequences:
            if tc.get("mane_plus_clinical"):
                logger.debug(f"Selected MANE Plus Clinical transcript: {tc.get('transcript_id')}")
                return tc
        
        # Priority 3: Canonical transcript
        for tc in transcript_consequences:
            if tc.get("canonical") == 1:
                logger.debug(f"Selected canonical transcript: {tc.get('transcript_id')}")
                return tc
        
        # Priority 4: Ensembl canonical transcript
        for tc in transcript_consequences:
            if tc.get("gene_symbol_source") == "HGNC" and tc.get("biotype") == "protein_coding":
                logger.debug(f"Selected protein-coding transcript: {tc.get('transcript_id')}")
                return tc
        
        # Priority 5: First available transcript
        logger.debug(f"Selected first available transcript: {transcript_consequences[0].get('transcript_id')}")
        return transcript_consequences[0]
    
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
            
            # Find the best transcript using prioritized selection
            canonical_consequence = self._select_best_transcript(transcript_consequences)
            
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
            
            # Extract VEP plugin data for evidence aggregation
            plugin_data = self._extract_plugin_data(canonical_consequence, vep_variant)
            
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
                annotation_source="VEP",
                
                # Plugin data (raw data to be processed by evidence aggregator)
                plugin_data=plugin_data
            )
            
            return variant_annotation
            
        except Exception as e:
            logger.warning(f"Failed to create variant annotation from VEP data: {e}")
            return None
    
    def _extract_plugin_data(self, transcript_consequence: Optional[Dict[str, Any]], 
                           vep_variant: Dict[str, Any]) -> Dict[str, Any]:
        """Extract plugin data from VEP output for evidence aggregation"""
        
        plugin_data = {}
        
        if not transcript_consequence:
            return plugin_data
            
        # Core pathogenicity predictors
        plugin_data.update(self._extract_pathogenicity_scores(transcript_consequence))
        
        # Splicing predictors  
        plugin_data.update(self._extract_splicing_scores(transcript_consequence))
        
        # Population and coverage data
        plugin_data.update(self._extract_population_data(transcript_consequence, vep_variant))
        
        # Clinical and phenotype data
        plugin_data.update(self._extract_clinical_data(transcript_consequence))
        
        # Conservation and constraint
        plugin_data.update(self._extract_conservation_data(transcript_consequence))
        
        # Literature and experimental evidence
        plugin_data.update(self._extract_literature_data(transcript_consequence))
        
        # Structural and regulatory
        plugin_data.update(self._extract_regulatory_data(transcript_consequence))
        
        # Quality control and ACMG
        plugin_data.update(self._extract_qc_data(transcript_consequence))
        
        return plugin_data
    
    def _extract_pathogenicity_scores(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pathogenicity prediction scores"""
        scores = {}
        
        # AlphaMissense
        if "alphamissense_score" in tc:
            scores["alphamissense"] = {
                "score": tc.get("alphamissense_score"),
                "prediction": tc.get("alphamissense_prediction")
            }
        
        # REVEL
        if "revel_score" in tc:
            scores["revel"] = {"score": tc.get("revel_score")}
            
        # PrimateAI  
        if "primateai_score" in tc:
            scores["primateai"] = {
                "score": tc.get("primateai_score"),
                "prediction": tc.get("primateai_pred")
            }
            
        # EVE
        if "eve_score" in tc:
            scores["eve"] = {
                "score": tc.get("eve_score"),
                "class": tc.get("eve_class")
            }
            
        # VARITY
        if "varity_r" in tc:
            scores["varity"] = {"score": tc.get("varity_r")}
            
        # BayesDel
        if "bayesdel_adaf_score" in tc:
            scores["bayesdel"] = {
                "score": tc.get("bayesdel_adaf_score"),
                "prediction": tc.get("bayesdel_adaf_pred")
            }
            
        # ClinPred
        if "clinpred_score" in tc:
            scores["clinpred"] = {
                "score": tc.get("clinpred_score"),
                "prediction": tc.get("clinpred_pred")
            }
            
        # FATHMM variants
        if "fathmm_score" in tc:
            scores["fathmm"] = {
                "score": tc.get("fathmm_score"),
                "prediction": tc.get("fathmm_pred")
            }
        if "fathmm_mkl_coding_score" in tc:
            scores["fathmm_mkl"] = {
                "score": tc.get("fathmm_mkl_coding_score"),
                "prediction": tc.get("fathmm_mkl_coding_pred")
            }
            
        # PolyPhen/SIFT (if not in dbNSFP)
        if "polyphen_score" in tc:
            scores["polyphen"] = {
                "score": tc.get("polyphen_score"),
                "prediction": tc.get("polyphen_prediction")
            }
        if "sift_score" in tc:
            scores["sift"] = {
                "score": tc.get("sift_score"),
                "prediction": tc.get("sift_prediction")
            }
            
        return {"pathogenicity_scores": scores}
    
    def _extract_splicing_scores(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract splicing prediction scores"""
        splicing = {}
        
        # SpliceAI
        if "spliceai_pred_ds_ag" in tc:
            splicing["spliceai"] = {
                "ds_ag": tc.get("spliceai_pred_ds_ag"),
                "ds_al": tc.get("spliceai_pred_ds_al"), 
                "ds_dg": tc.get("spliceai_pred_ds_dg"),
                "ds_dl": tc.get("spliceai_pred_ds_dl"),
                "dp_ag": tc.get("spliceai_pred_dp_ag"),
                "dp_al": tc.get("spliceai_pred_dp_al"),
                "dp_dg": tc.get("spliceai_pred_dp_dg"),
                "dp_dl": tc.get("spliceai_pred_dp_dl")
            }
            
        # dbscSNV
        if "ada_score" in tc:
            splicing["dbscsnv"] = {
                "ada_score": tc.get("ada_score"),
                "rf_score": tc.get("rf_score")
            }
            
        # SpliceRegion
        if "splice_region_variant" in tc:
            splicing["splice_region"] = tc.get("splice_region_variant")
            
        return {"splicing_scores": splicing}
    
    def _extract_population_data(self, tc: Dict[str, Any], vep_variant: Dict[str, Any]) -> Dict[str, Any]:
        """Extract population frequency and coverage data"""
        population = {}
        
        # gnomAD frequencies (handled in main population_frequencies)
        # gnomADc coverage data
        if "gnomad_exome_coverage" in tc:
            population["gnomad_coverage"] = {
                "exome_mean": tc.get("gnomad_exome_coverage"),
                "genome_mean": tc.get("gnomad_genome_coverage")
            }
            
        return {"population_data": population}
    
    def _extract_clinical_data(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract clinical and phenotype data"""
        clinical = {}
        
        # ClinVar (handled separately)
        # Phenotypes
        if "phenotype" in tc:
            clinical["phenotypes"] = tc.get("phenotype")
            
        return {"clinical_data": clinical}
    
    def _extract_conservation_data(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract conservation and constraint scores"""
        conservation = {}
        
        # Conservation scores
        if "gerp_rs" in tc:
            conservation["gerp"] = tc.get("gerp_rs")
        if "phylop_score" in tc:
            conservation["phylop"] = tc.get("phylop_score")
        if "phastcons_score" in tc:
            conservation["phastcons"] = tc.get("phastcons_score")
            
        # LoFtool
        if "loftool" in tc:
            conservation["loftool"] = tc.get("loftool")
            
        return {"conservation_data": conservation}
    
    def _extract_literature_data(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract literature and experimental evidence"""
        literature = {}
        
        # AVADA
        if "avada_score" in tc:
            literature["avada"] = {
                "score": tc.get("avada_score"),
                "evidence": tc.get("avada_evidence")
            }
            
        # MaveDB
        if "mavedb_score" in tc:
            literature["mavedb"] = {
                "score": tc.get("mavedb_score"),
                "assay": tc.get("mavedb_assay")
            }
            
        return {"literature_data": literature}
    
    def _extract_regulatory_data(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structural and regulatory data"""
        regulatory = {}
        
        # StructuralVariantOverlap
        if "sv_overlap" in tc:
            regulatory["sv_overlap"] = tc.get("sv_overlap")
            
        # UTRAnnotator
        if "utr_annotation" in tc:
            regulatory["utr_annotation"] = tc.get("utr_annotation")
            
        # Enformer
        if "enformer_score" in tc:
            regulatory["enformer"] = tc.get("enformer_score")
            
        return {"regulatory_data": regulatory}
    
    def _extract_qc_data(self, tc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract quality control and ACMG data"""
        qc = {}
        
        # GeneBe ACMG
        if "genebe_acmg" in tc:
            qc["genebe_acmg"] = tc.get("genebe_acmg")
            
        # NMD
        if "nmd_escape" in tc:
            qc["nmd_escape"] = tc.get("nmd_escape")
            
        return {"qc_data": qc}


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