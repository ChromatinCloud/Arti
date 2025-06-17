"""
VEP Docker Manager - Centralized VEP Docker Configuration and Execution

Provides a unified interface for VEP Docker operations with consistent
mount configurations, path validation, and error handling.
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class VEPDockerMode(str, Enum):
    """VEP Docker execution modes"""
    ANNOTATION = "annotation"      # Standard variant annotation
    PLUGIN_TEST = "plugin_test"    # Plugin functionality testing  
    CACHE_VALIDATION = "cache_validation"  # Cache integrity checking
    DIAGNOSTIC = "diagnostic"      # System diagnostics


@dataclass
class VEPDockerConfig:
    """Centralized VEP Docker configuration"""
    
    # Core paths (auto-detected from repository structure)
    repo_root: Path
    refs_dir: Path  
    cache_dir: Path
    plugins_dir: Path
    
    # Docker configuration
    docker_image: str = "ensemblorg/ensembl-vep:release_114.1"
    docker_timeout: int = 300  # 5 minutes default
    
    # VEP-specific settings
    assembly: str = "GRCh38"
    vep_cache_version: str = "114"
    
    # Execution settings
    working_directory: str = "/input"
    use_read_only_mounts: bool = True
    
    def __post_init__(self):
        """Validate paths and configuration after initialization"""
        self._validate_paths()
        self._validate_docker_config()
    
    def _validate_paths(self):
        """Validate that all required paths exist"""
        required_paths = {
            "Repository root": self.repo_root,
            "References directory": self.refs_dir,
            "VEP cache": self.cache_dir,
            "VEP plugins": self.plugins_dir
        }
        
        missing_paths = []
        for name, path in required_paths.items():
            if not path.exists():
                missing_paths.append(f"{name}: {path}")
        
        if missing_paths:
            raise FileNotFoundError(
                f"Missing required VEP paths:\n" + "\n".join(missing_paths)
            )
        
        logger.debug(f"VEP paths validated: {len(required_paths)} paths OK")
    
    def _validate_docker_config(self):
        """Validate Docker configuration"""
        if not self.docker_image:
            raise ValueError("Docker image must be specified")
        
        if self.docker_timeout <= 0:
            raise ValueError("Docker timeout must be positive")
        
        if self.assembly not in ["GRCh37", "GRCh38"]:
            logger.warning(f"Unusual genome assembly: {self.assembly}")
    
    @classmethod
    def from_repo_root(cls, repo_root: Optional[Path] = None) -> "VEPDockerConfig":
        """
        Create VEP Docker configuration from repository root
        
        Args:
            repo_root: Repository root path (auto-detected if None)
            
        Returns:
            Configured VEPDockerConfig instance
        """
        if repo_root is None:
            # Auto-detect repo root by looking for key files
            current = Path.cwd()
            while current != current.parent:
                if (current / "pyproject.toml").exists() and (current / ".refs").exists():
                    repo_root = current
                    break
                current = current.parent
            else:
                raise FileNotFoundError("Could not auto-detect repository root")
        
        repo_root = Path(repo_root).resolve()
        refs_dir = repo_root / ".refs"
        cache_dir = refs_dir / "functional_predictions" / "vep_cache"
        plugins_dir = refs_dir / "functional_predictions" / "vep_plugins"
        
        return cls(
            repo_root=repo_root,
            refs_dir=refs_dir,
            cache_dir=cache_dir,
            plugins_dir=plugins_dir
        )


class VEPDockerManager:
    """Centralized VEP Docker operations manager"""
    
    def __init__(self, config: Optional[VEPDockerConfig] = None):
        """
        Initialize VEP Docker Manager
        
        Args:
            config: VEP Docker configuration (auto-created if None)
        """
        self.config = config or VEPDockerConfig.from_repo_root()
        logger.info(f"VEP Docker Manager initialized with {self.config.docker_image}")
    
    def get_mount_arguments(self, 
                          input_dir: Path, 
                          output_dir: Path,
                          mode: VEPDockerMode = VEPDockerMode.ANNOTATION) -> List[str]:
        """
        Generate standardized Docker mount arguments
        
        Args:
            input_dir: Directory containing input files
            output_dir: Directory for output files  
            mode: VEP execution mode
            
        Returns:
            List of Docker mount arguments
        """
        input_dir = Path(input_dir).resolve()
        output_dir = Path(output_dir).resolve()
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Standard read-only mounts
        ro_suffix = ":ro" if self.config.use_read_only_mounts else ""
        
        mounts = [
            "-v", f"{self.config.cache_dir}:/opt/vep/.vep{ro_suffix}",
            "-v", f"{self.config.plugins_dir}:/opt/vep/plugins{ro_suffix}",
            "-v", f"{self.config.refs_dir}:/.refs{ro_suffix}",
            "-v", f"{input_dir}:/input{ro_suffix}",
            "-v", f"{output_dir}:/output"
        ]
        
        # Mode-specific additional mounts
        if mode == VEPDockerMode.DIAGNOSTIC:
            # Add extra mounts for diagnostic access
            mounts.extend([
                "-v", f"{self.config.repo_root}:/repo{ro_suffix}"
            ])
        
        return mounts
    
    def build_docker_command(self,
                           input_file: Path,
                           output_file: Path, 
                           vep_args: Optional[List[str]] = None,
                           mode: VEPDockerMode = VEPDockerMode.ANNOTATION) -> List[str]:
        """
        Build complete Docker command for VEP execution
        
        Args:
            input_file: Input VCF file path
            output_file: Output file path
            vep_args: Additional VEP arguments
            mode: VEP execution mode
            
        Returns:
            Complete Docker command as list of strings
        """
        input_file = Path(input_file).resolve()
        output_file = Path(output_file).resolve()
        
        # Validate input file exists
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Get mount arguments
        input_dir = input_file.parent
        output_dir = output_file.parent
        mounts = self.get_mount_arguments(input_dir, output_dir, mode)
        
        # Build base Docker command
        cmd = [
            "docker", "run", "--rm",
            *mounts,
            "-w", self.config.working_directory,
            self.config.docker_image,
            "vep"
        ]
        
        # Add standard VEP arguments
        container_input = f"/input/{input_file.name}"
        container_output = f"/output/{output_file.name}"
        
        standard_args = [
            "--input_file", container_input,
            "--output_file", container_output,
            "--format", "vcf",
            "--json",
            "--cache",
            "--offline", 
            "--dir_cache", "/opt/vep/.vep",
            "--dir_plugins", "/opt/vep/plugins",
            "--assembly", self.config.assembly,
            "--force_overwrite",
            "--no_stats"
        ]
        
        cmd.extend(standard_args)
        
        # Add custom VEP arguments
        if vep_args:
            cmd.extend(vep_args)
        
        return cmd
    
    def execute_vep(self,
                   input_file: Path,
                   output_file: Path,
                   vep_args: Optional[List[str]] = None,
                   mode: VEPDockerMode = VEPDockerMode.ANNOTATION,
                   capture_output: bool = True) -> subprocess.CompletedProcess:
        """
        Execute VEP via Docker with standardized configuration
        
        Args:
            input_file: Input VCF file path
            output_file: Output file path  
            vep_args: Additional VEP arguments
            mode: VEP execution mode
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CompletedProcess result
            
        Raises:
            subprocess.CalledProcessError: If VEP execution fails
            FileNotFoundError: If input file or required paths missing
        """
        cmd = self.build_docker_command(input_file, output_file, vep_args, mode)
        
        logger.info(f"Executing VEP: {input_file.name} -> {output_file.name}")
        logger.debug(f"VEP command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=self.config.docker_timeout,
                check=False  # We'll handle errors manually
            )
            
            if result.returncode != 0:
                error_msg = f"VEP failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nSTDERR: {result.stderr}"
                logger.error(error_msg)
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )
            
            logger.info(f"VEP completed successfully: {output_file}")
            return result
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"VEP timed out after {self.config.docker_timeout}s")
            raise
        except Exception as e:
            logger.error(f"VEP execution failed: {e}")
            raise
    
    def test_vep_setup(self) -> Dict[str, Any]:
        """
        Test VEP Docker setup and return diagnostic information
        
        Returns:
            Dictionary with test results and diagnostic information
        """
        results = {
            "config_valid": False,
            "docker_available": False,
            "image_available": False,
            "mounts_accessible": False,
            "vep_executable": False,
            "cache_valid": False,
            "plugins_loaded": False,
            "errors": []
        }
        
        try:
            # Test 1: Config validation (already done in __init__)
            results["config_valid"] = True
            
            # Test 2: Docker availability
            docker_test = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                timeout=10
            )
            results["docker_available"] = docker_test.returncode == 0
            
            # Test 3: Docker image availability
            if results["docker_available"]:
                image_test = subprocess.run(
                    ["docker", "images", self.config.docker_image, "-q"],
                    capture_output=True,
                    timeout=30
                )
                results["image_available"] = bool(image_test.stdout.strip())
            
            # Test 4: Mount accessibility (quick test)
            if results["image_available"]:
                test_input = self.config.repo_root / "example_input"
                test_output = self.config.repo_root / "out"
                
                if test_input.exists():
                    mounts = self.get_mount_arguments(test_input, test_output, VEPDockerMode.DIAGNOSTIC)
                    mount_test = subprocess.run(
                        ["docker", "run", "--rm", *mounts, self.config.docker_image, "ls", "/opt/vep/.vep"],
                        capture_output=True,
                        timeout=60
                    )
                    results["mounts_accessible"] = mount_test.returncode == 0
            
            # Test 5: VEP executable
            if results["mounts_accessible"]:
                vep_test = subprocess.run(
                    ["docker", "run", "--rm", self.config.docker_image, "vep", "--help"],
                    capture_output=True,
                    timeout=30
                )
                results["vep_executable"] = vep_test.returncode == 0
            
            # Additional tests would go here (cache validation, plugin loading)
            
        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"VEP setup test failed: {e}")
        
        return results
    
    def get_config_summary(self) -> Dict[str, str]:
        """Get human-readable configuration summary"""
        return {
            "Docker Image": self.config.docker_image,
            "Repository Root": str(self.config.repo_root),
            "VEP Cache": str(self.config.cache_dir),
            "VEP Plugins": str(self.config.plugins_dir), 
            "Assembly": self.config.assembly,
            "Working Directory": self.config.working_directory,
            "Timeout": f"{self.config.docker_timeout}s"
        }


# Factory function for easy instantiation
def create_vep_docker_manager(repo_root: Optional[Path] = None) -> VEPDockerManager:
    """
    Factory function to create VEP Docker Manager with default configuration
    
    Args:
        repo_root: Repository root path (auto-detected if None)
        
    Returns:
        Configured VEPDockerManager instance
    """
    config = VEPDockerConfig.from_repo_root(repo_root)
    return VEPDockerManager(config)