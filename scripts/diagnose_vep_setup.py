#!/usr/bin/env python3
"""
Comprehensive VEP setup diagnostic script

This script checks:
1. Docker availability and VEP image
2. File paths and permissions
3. Plugin availability
4. Basic VEP execution
5. Plugin loading
"""

import subprocess
import sys
from pathlib import Path
import json
import os

class VEPDiagnostics:
    def __init__(self):
        self.refs_dir = Path(".refs")
        self.issues = []
        self.successes = []
        
    def run_all_checks(self):
        """Run all diagnostic checks"""
        print("VEP Setup Diagnostics")
        print("=" * 80)
        
        self.check_docker()
        self.check_vep_image()
        self.check_directory_structure()
        self.check_required_files()
        self.check_plugin_files()
        self.test_basic_vep()
        self.test_vep_with_plugins()
        
        self.print_summary()
        
    def check_docker(self):
        """Check if Docker is available"""
        print("\n[1/7] Checking Docker availability...")
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.successes.append(f"Docker available: {result.stdout.strip()}")
            print(f"  ✓ {result.stdout.strip()}")
        except Exception as e:
            self.issues.append("Docker not available or not in PATH")
            print(f"  ✗ Docker not found: {e}")
            
    def check_vep_image(self):
        """Check if VEP Docker image is available"""
        print("\n[2/7] Checking VEP Docker image...")
        try:
            result = subprocess.run(
                ["docker", "images", "ensemblorg/ensembl-vep", "--format", "{{.Tag}}"],
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                self.successes.append(f"VEP image available: {result.stdout.strip()}")
                print(f"  ✓ VEP image tags: {result.stdout.strip()}")
            else:
                print("  ⚠ No VEP image found, will download on first run")
        except Exception as e:
            self.issues.append(f"Error checking VEP image: {e}")
            print(f"  ✗ Error: {e}")
            
    def check_directory_structure(self):
        """Check if required directories exist"""
        print("\n[3/7] Checking directory structure...")
        
        required_dirs = [
            self.refs_dir / "functional_predictions" / "vep_cache",
            self.refs_dir / "functional_predictions" / "vep_plugins",
            self.refs_dir / "functional_predictions" / "plugin_data",
            self.refs_dir / "variant" / "vcf" / "dbnsfp",
            self.refs_dir / "misc" / "fasta" / "assembly",
        ]
        
        for dir_path in required_dirs:
            if dir_path.exists() and dir_path.is_dir():
                print(f"  ✓ {dir_path}")
                self.successes.append(f"Directory exists: {dir_path}")
            else:
                print(f"  ✗ Missing: {dir_path}")
                self.issues.append(f"Missing directory: {dir_path}")
                
    def check_required_files(self):
        """Check for essential files"""
        print("\n[4/7] Checking required files...")
        
        required_files = {
            "Reference FASTA": self.refs_dir / "misc" / "fasta" / "assembly" / "Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz",
            "Reference Index": self.refs_dir / "misc" / "fasta" / "assembly" / "Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz.fai",
            "VEP Cache": self.refs_dir / "functional_predictions" / "vep_cache" / "homo_sapiens" / "114_GRCh38",
            "dbNSFP VCF": self.refs_dir / "variant" / "vcf" / "dbnsfp" / "dbnsfp.vcf.gz",
            "dbNSFP Index": self.refs_dir / "variant" / "vcf" / "dbnsfp" / "dbnsfp.vcf.gz.tbi",
        }
        
        for name, file_path in required_files.items():
            if file_path.exists():
                if file_path.is_file():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    print(f"  ✓ {name}: {size_mb:.1f} MB")
                    self.successes.append(f"{name} exists: {size_mb:.1f} MB")
                else:
                    print(f"  ✓ {name}: Directory exists")
                    self.successes.append(f"{name} directory exists")
            else:
                print(f"  ✗ {name}: NOT FOUND at {file_path}")
                self.issues.append(f"{name} missing: {file_path}")
                
    def check_plugin_files(self):
        """Check VEP plugin files"""
        print("\n[5/7] Checking VEP plugins...")
        
        plugins_dir = self.refs_dir / "functional_predictions" / "vep_plugins"
        if plugins_dir.exists():
            pm_files = list(plugins_dir.glob("*.pm"))
            print(f"  ✓ Found {len(pm_files)} plugin files")
            
            # Check specific important plugins
            important_plugins = ["dbNSFP.pm", "AlphaMissense.pm", "Conservation.pm", "LoFtool.pm"]
            for plugin in important_plugins:
                plugin_path = plugins_dir / plugin
                if plugin_path.exists():
                    print(f"    ✓ {plugin}")
                else:
                    print(f"    ✗ {plugin} - NOT FOUND")
                    self.issues.append(f"Missing plugin: {plugin}")
        else:
            self.issues.append("VEP plugins directory not found")
            
    def test_basic_vep(self):
        """Test basic VEP execution without plugins"""
        print("\n[6/7] Testing basic VEP execution...")
        
        # Use existing test VCF if available, otherwise create minimal one
        test_vcf = Path("example_input/proper_test.vcf")
        if not test_vcf.exists():
            test_vcf = Path("out/test_minimal.vcf")
            test_vcf.parent.mkdir(exist_ok=True)
            
            with open(test_vcf, "w") as f:
                f.write("##fileformat=VCFv4.2\n")
                f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                f.write("7\t140753336\t.\tA\tT\t.\tPASS\t.\n")  # BRAF V600E
            
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{Path.cwd()}:/data",
            "-v", f"{Path.cwd()}/.refs:/opt/vep/.vep",
            "ensemblorg/ensembl-vep:release_114.0",
            "vep",
            "--format", "vcf",
            "--json",
            "--cache",
            "--dir_cache", "/opt/vep/.vep/functional_predictions/vep_cache",
            "--assembly", "GRCh38",
            "--offline",
            "--input_file", f"/data/{test_vcf}",
            "--output_file", "STDOUT",
            "--no_stats",
            "--force_overwrite"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.successes.append("Basic VEP execution successful")
                print("  ✓ Basic VEP execution works")
                
                # Check if output is valid JSON
                try:
                    output_lines = [line for line in result.stdout.split('\n') if line and not line.startswith('#')]
                    if output_lines:
                        json.loads(output_lines[0])
                        print("  ✓ VEP produces valid JSON output")
                except:
                    print("  ⚠ VEP output is not valid JSON")
            else:
                self.issues.append(f"VEP execution failed with code {result.returncode}")
                print(f"  ✗ VEP failed with exit code {result.returncode}")
                print(f"    STDERR: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            self.issues.append("VEP execution timed out")
            print("  ✗ VEP execution timed out")
        except Exception as e:
            self.issues.append(f"VEP execution error: {e}")
            print(f"  ✗ Error: {e}")
            
    def test_vep_with_plugins(self):
        """Test VEP with plugins"""
        print("\n[7/7] Testing VEP with plugins...")
        
        # Use same test VCF as basic test
        test_vcf = Path("example_input/proper_test.vcf")
        if not test_vcf.exists():
            test_vcf = Path("out/test_minimal.vcf")
        
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{Path.cwd()}:/data",
            "-v", f"{Path.cwd()}/.refs:/opt/vep/.vep",
            "ensemblorg/ensembl-vep:release_114.0",
            "vep",
            "--format", "vcf",
            "--json",
            "--cache",
            "--dir_cache", "/opt/vep/.vep/functional_predictions/vep_cache",
            "--dir_plugins", "/opt/vep/.vep/functional_predictions/vep_plugins",
            "--plugin", "dbNSFP,/opt/vep/.vep/variant/vcf/dbnsfp/dbnsfp.vcf.gz,SIFT_score,Polyphen2_HDIV_score",
            "--assembly", "GRCh38",
            "--offline",
            "--input_file", f"/data/{test_vcf}",
            "--output_file", "STDOUT",
            "--no_stats",
            "--force_overwrite"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                self.successes.append("VEP with plugins successful")
                print("  ✓ VEP with dbNSFP plugin works")
            else:
                self.issues.append(f"VEP with plugins failed with code {result.returncode}")
                print(f"  ✗ VEP with plugins failed with exit code {result.returncode}")
                print(f"    STDERR: {result.stderr[:500]}")
                
                # Check for common issues
                if "Can't locate" in result.stderr:
                    print("    → Plugin file not found or not accessible")
                if "Permission denied" in result.stderr:
                    print("    → Permission issue with mounted volumes")
                if "Cannot use file" in result.stderr:
                    print("    → Data file format or index issue")
                    
        except subprocess.TimeoutExpired:
            self.issues.append("VEP with plugins timed out")
            print("  ✗ VEP with plugins timed out")
        except Exception as e:
            self.issues.append(f"VEP plugin test error: {e}")
            print(f"  ✗ Error: {e}")
            
    def print_summary(self):
        """Print diagnostic summary"""
        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        print(f"\n✓ Successes: {len(self.successes)}")
        for success in self.successes:
            print(f"  - {success}")
            
        print(f"\n✗ Issues Found: {len(self.issues)}")
        for issue in self.issues:
            print(f"  - {issue}")
            
        if self.issues:
            print("\nRECOMMENDED ACTIONS:")
            
            if any("Docker" in issue for issue in self.issues):
                print("  1. Ensure Docker is installed and running")
                
            if any("directory" in issue.lower() for issue in self.issues):
                print("  2. Run setup scripts to create missing directories")
                
            if any("plugin" in issue.lower() for issue in self.issues):
                print("  3. Download missing VEP plugins")
                print("     - Check if .pm files exist in .refs/functional_predictions/vep_plugins/")
                print("     - Ensure plugin data files are in correct locations")
                
            if any("VEP execution failed" in issue for issue in self.issues):
                print("  4. Check Docker volume mounts and file permissions")
                print("     - Ensure .refs directory is accessible")
                print("     - Check if paths inside container match mounted volumes")
                
            if any("FASTA" in issue or "Cache" in issue for issue in self.issues):
                print("  5. Complete VEP setup:")
                print("     - Download reference FASTA")
                print("     - Install VEP cache for GRCh38")
                
        else:
            print("\n✅ All checks passed! VEP is properly configured.")

def main():
    """Run VEP diagnostics"""
    diagnostics = VEPDiagnostics()
    diagnostics.run_all_checks()
    
    # Return exit code based on issues found
    sys.exit(1 if diagnostics.issues else 0)

if __name__ == "__main__":
    main()