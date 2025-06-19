#!/usr/bin/env python3
"""
Population and Subpopulation Allele Frequency Table Generator

Creates flat TSV files with gnomAD and All of Us allele frequencies using VEP.
Supports both plugin-based and built-in AF extraction methods.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import tempfile
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
REFS_DIR = REPO_ROOT / ".refs"

def check_vep_setup():
    """Verify VEP is properly configured"""
    vep_script = SCRIPT_DIR / "vep"
    if not vep_script.exists():
        raise FileNotFoundError(f"VEP script not found at {vep_script}")
    
    vep_cache = REFS_DIR / "functional_predictions" / "vep_cache"
    if not vep_cache.exists():
        raise FileNotFoundError(f"VEP cache not found at {vep_cache}")
    
    gnomad_plugin = REFS_DIR / "functional_predictions" / "vep_plugins" / "gnomADc.pm"
    if not gnomad_plugin.exists():
        logger.warning(f"gnomADc plugin not found at {gnomad_plugin} - will use built-in AF flags")
        return False
    
    return True

def find_gnomad_files():
    """Find available gnomAD data files"""
    gnomad_dir = REFS_DIR / "population_frequencies" / "gnomad"
    
    # Look for common gnomAD file patterns
    patterns = [
        "gnomad.v4.1.sites.bcf",
        "gnomad.v4.0.sites.bcf", 
        "gnomad_v3.1.2_sites.bcf",
        "gnomad.genomes.r3.0.sites.vcf.gz",
        "gnomad.exomes.r2.1.1.sites.vcf.gz"
    ]
    
    found_files = []
    for pattern in patterns:
        files = list(gnomad_dir.glob(f"**/{pattern}"))
        found_files.extend(files)
    
    # Also check for any BCF/VCF files
    bcf_files = list(gnomad_dir.glob("**/*.bcf"))
    vcf_files = list(gnomad_dir.glob("**/*.vcf.gz"))
    
    all_files = found_files + bcf_files + vcf_files
    
    logger.info(f"Found {len(all_files)} potential gnomAD files:")
    for f in all_files:
        logger.info(f"  {f}")
    
    return all_files

def create_af_table_with_plugin(vcf_path, output_path, gnomad_file=None, aou_file=None):
    """Create AF table using gnomAD plugin and custom files"""
    
    vep_script = SCRIPT_DIR / "vep"
    
    # Build VEP command
    cmd = [
        str(vep_script),
        "--cache", "--offline",
        "--assembly", "GRCh38",
        "--input_file", str(vcf_path),
        "--tab",
        "--output_file", str(output_path)
    ]
    
    # Add gnomAD plugin if file available
    if gnomad_file and Path(gnomad_file).exists():
        cmd.extend(["--plugin", f"gnomADc,{gnomad_file}"])
        fields = ["Uploaded_variation", "Location", "Allele", "gnomAD_AF"]
    else:
        logger.warning("No gnomAD file specified or file not found - using built-in AF flags")
        cmd.extend(["--af", "--af_gnomadg", "--af_gnomade"])
        fields = ["Uploaded_variation", "Location", "Allele", "AF", "AF_gnomadg", "AF_gnomade"]
    
    # Add All of Us custom file if provided
    if aou_file and Path(aou_file).exists():
        cmd.extend(["--custom", f"{aou_file},AllOfUs,vcf,exact,0,AF"])
        fields.append("AllOfUs_AF")
    
    # Set output fields
    cmd.extend(["--fields", ",".join(fields)])
    
    logger.info(f"Running VEP command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("VEP completed successfully")
        if result.stdout:
            logger.info(f"VEP stdout: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"VEP failed with return code {e.returncode}")
        logger.error(f"VEP stdout: {e.stdout}")
        logger.error(f"VEP stderr: {e.stderr}")
        return False

def create_af_table_builtin(vcf_path, output_path):
    """Create AF table using VEP's built-in AF flags"""
    
    vep_script = SCRIPT_DIR / "vep"
    
    cmd = [
        str(vep_script),
        "--cache", "--offline",
        "--assembly", "GRCh38", 
        "--input_file", str(vcf_path),
        "--af",          # Standard ExAC/1KG/ESP/gnomAD exomes
        "--af_gnomadg",  # gnomAD genomes
        "--af_gnomade",  # gnomAD exomes
        "--tab",
        "--fields", "Uploaded_variation,Location,Allele,AF,AF_gnomadg,AF_gnomade,Existing_variation",
        "--output_file", str(output_path)
    ]
    
    logger.info(f"Running VEP command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("VEP completed successfully")
        if result.stdout:
            logger.info(f"VEP stdout: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"VEP failed with return code {e.returncode}")
        logger.error(f"VEP stdout: {e.stdout}")
        logger.error(f"VEP stderr: {e.stderr}")
        return False

def create_enhanced_af_table(vcf_path, output_path):
    """Create comprehensive AF table with all available population data"""
    
    vep_script = SCRIPT_DIR / "vep"
    
    cmd = [
        str(vep_script),
        "--cache", "--offline",
        "--assembly", "GRCh38",
        "--input_file", str(vcf_path),
        "--af",          # Standard populations
        "--af_1kg",      # 1000 Genomes
        "--af_gnomadg",  # gnomAD genomes  
        "--af_gnomade",  # gnomAD exomes
        "--af_esp",      # ESP populations
        "--tab",
        "--fields", "Uploaded_variation,Location,Allele,Gene,Consequence,AF,AF_1kg,AF_gnomadg,AF_gnomade,AF_esp,Existing_variation,CLIN_SIG",
        "--output_file", str(output_path)
    ]
    
    logger.info(f"Running VEP enhanced command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("VEP enhanced processing completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"VEP enhanced processing failed: {e}")
        logger.error(f"VEP stderr: {e.stderr}")
        return False

def validate_vcf(vcf_path):
    """Basic VCF validation"""
    if not Path(vcf_path).exists():
        raise FileNotFoundError(f"VCF file not found: {vcf_path}")
    
    # Check if it's compressed and indexed
    vcf_file = Path(vcf_path)
    if vcf_file.suffix == ".gz":
        index_file = vcf_file.with_suffix(vcf_file.suffix + ".tbi")
        if not index_file.exists():
            logger.warning(f"No index found for {vcf_path} - VEP may be slower")
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Generate population allele frequency tables using VEP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic built-in AF extraction
  python create_af_tables.py input.vcf.gz --output af_basic.tsv --method builtin
  
  # Enhanced extraction with all populations
  python create_af_tables.py input.vcf.gz --output af_enhanced.tsv --method enhanced
  
  # Plugin-based extraction with custom gnomAD file
  python create_af_tables.py input.vcf.gz --output af_plugin.tsv --method plugin \\
    --gnomad-file /path/to/gnomad.v4.1.sites.bcf
  
  # Plugin with both gnomAD and All of Us files
  python create_af_tables.py input.vcf.gz --output af_comprehensive.tsv --method plugin \\
    --gnomad-file /path/to/gnomad.v4.1.sites.bcf \\
    --aou-file /path/to/aou.af.vcf.gz
        """
    )
    
    parser.add_argument("vcf_file", help="Input VCF file (can be bgzipped)")
    parser.add_argument("--output", "-o", required=True, help="Output TSV file")
    parser.add_argument("--method", choices=["builtin", "plugin", "enhanced"], default="builtin",
                       help="Method for AF extraction (default: builtin)")
    parser.add_argument("--gnomad-file", help="Path to gnomAD BCF/VCF file for plugin method")
    parser.add_argument("--aou-file", help="Path to All of Us VCF file for plugin method")
    parser.add_argument("--check-setup", action="store_true", help="Check VEP setup and available files")
    
    args = parser.parse_args()
    
    if args.check_setup:
        logger.info("Checking VEP setup...")
        try:
            has_plugin = check_vep_setup()
            logger.info(f"VEP setup: {'OK' if has_plugin else 'OK (built-in only)'}")
            
            gnomad_files = find_gnomad_files()
            if gnomad_files:
                logger.info("Available gnomAD files:")
                for f in gnomad_files[:5]:  # Show first 5
                    logger.info(f"  {f}")
                if len(gnomad_files) > 5:
                    logger.info(f"  ... and {len(gnomad_files) - 5} more")
            else:
                logger.warning("No gnomAD files found")
                
        except Exception as e:
            logger.error(f"Setup check failed: {e}")
            return 1
        return 0
    
    # Validate inputs
    try:
        validate_vcf(args.vcf_file)
        check_vep_setup()
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run the appropriate method
    success = False
    
    if args.method == "builtin":
        logger.info("Using built-in AF flags method")
        success = create_af_table_builtin(args.vcf_file, args.output)
        
    elif args.method == "enhanced":
        logger.info("Using enhanced built-in method with all populations")
        success = create_enhanced_af_table(args.vcf_file, args.output)
        
    elif args.method == "plugin":
        logger.info("Using plugin-based method")
        success = create_af_table_with_plugin(
            args.vcf_file, args.output, 
            args.gnomad_file, args.aou_file
        )
    
    if success:
        logger.info(f"AF table created successfully: {args.output}")
        
        # Show preview of results
        if Path(args.output).exists():
            logger.info("Preview of results:")
            with open(args.output) as f:
                for i, line in enumerate(f):
                    if i < 5:  # Show first 5 lines
                        logger.info(f"  {line.strip()}")
                    else:
                        break
        return 0
    else:
        logger.error("AF table creation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())