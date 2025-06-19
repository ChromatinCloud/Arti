#!/usr/bin/env python3
"""
Population AF Quick Extractor

Automatically chooses the fastest method for your use case:
- BigQuery (fastest, seconds) for ad-hoc queries  
- Local VEP (fast, minutes) for existing VCF panels
- Pre-extraction (setup once, query in milliseconds) for repeated use

Usage: python get_population_afs.py input.vcf.gz --output results.tsv
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent

def check_bigquery_available():
    """Check if BigQuery is available"""
    try:
        result = subprocess.run(["bq", "version"], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_vep_available():
    """Check if VEP is available"""
    vep_script = SCRIPT_DIR / "vep"
    return vep_script.exists()

def count_variants_in_vcf(vcf_path):
    """Count variants in VCF to determine best approach"""
    try:
        result = subprocess.run(
            ["bcftools", "view", "-H", str(vcf_path), "|", "wc", "-l"],
            shell=True, capture_output=True, text=True
        )
        return int(result.stdout.strip())
    except:
        # Fallback count
        try:
            with open(vcf_path) as f:
                count = sum(1 for line in f if not line.startswith('#'))
            return count
        except:
            return 0

def recommend_approach(vcf_path, variant_count):
    """Recommend the best approach based on context"""
    has_bq = check_bigquery_available()
    has_vep = check_vep_available()
    
    logger.info(f"Analyzing {variant_count:,} variants...")
    logger.info(f"BigQuery available: {has_bq}")
    logger.info(f"Local VEP available: {has_vep}")
    
    if variant_count <= 1000 and has_bq:
        return "bigquery", "Small panel + BigQuery available = fastest (seconds)"
    elif variant_count <= 50000 and has_vep:
        return "vep", "Medium panel + local VEP = fast and reliable (minutes)"
    elif has_bq:
        return "bigquery", "Large panel but BigQuery handles it well (seconds)"
    elif has_vep:
        return "vep", "No BigQuery, using local VEP (minutes)"
    else:
        return None, "No suitable extraction method available"

def run_bigquery_extraction(vcf_path, output_path):
    """Run BigQuery extraction"""
    logger.info("🚀 Using BigQuery extraction (fastest)...")
    
    cmd = [
        "python", str(SCRIPT_DIR / "bigquery_af_extractor.py"),
        "--dataset", "gnomad_v4",
        "--vcf-panel", str(vcf_path),
        "--output", str(output_path),
        "--compress"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("✅ BigQuery extraction completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ BigQuery extraction failed: {e}")
        return False

def run_vep_extraction(vcf_path, output_path):
    """Run VEP extraction"""
    logger.info("🔧 Using local VEP extraction...")
    
    cmd = [
        "python", str(SCRIPT_DIR / "create_af_tables.py"),
        str(vcf_path),
        "--output", str(output_path),
        "--method", "enhanced"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        logger.info("✅ VEP extraction completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ VEP extraction failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Get population AF data using the fastest available method",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script automatically chooses the best approach:

🚀 BigQuery (seconds): For any size panel when available
🔧 Local VEP (minutes): Reliable fallback for offline use  
📊 Pre-extracted (milliseconds): For repeated queries (separate setup)

Examples:
  # Automatic method selection
  python get_population_afs.py my_panel.vcf.gz --output panel_afs.tsv
  
  # Force specific method
  python get_population_afs.py my_panel.vcf.gz --output panel_afs.tsv --method bigquery
  
  # Check what methods are available
  python get_population_afs.py --check-methods
        """
    )
    
    parser.add_argument("vcf_file", nargs="?", help="Input VCF file")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--method", choices=["auto", "bigquery", "vep"], default="auto",
                       help="Force specific extraction method")
    parser.add_argument("--check-methods", action="store_true", 
                       help="Check available extraction methods")
    
    args = parser.parse_args()
    
    if args.check_methods:
        logger.info("🔍 Checking available extraction methods...")
        
        has_bq = check_bigquery_available()
        has_vep = check_vep_available()
        
        print("\\n📋 Available Methods:")
        print(f"  🚀 BigQuery: {'✅ Available' if has_bq else '❌ Not available (install gcloud + bq)'}")
        print(f"  🔧 Local VEP: {'✅ Available' if has_vep else '❌ Not available (run setup_vep.sh)'}")
        
        if has_bq:
            print("\\n💡 BigQuery is fastest for most use cases (seconds)")
        elif has_vep:
            print("\\n💡 Local VEP is reliable for offline use (minutes)")
        else:
            print("\\n⚠️  No extraction methods available - install BigQuery or VEP")
        
        return 0
    
    if not args.vcf_file or not args.output:
        logger.error("VCF file and output path required")
        return 1
    
    vcf_path = Path(args.vcf_file)
    output_path = Path(args.output)
    
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    # Count variants and recommend approach
    variant_count = count_variants_in_vcf(vcf_path)
    
    if args.method == "auto":
        method, reason = recommend_approach(vcf_path, variant_count)
        if not method:
            logger.error(f"❌ {reason}")
            return 1
        logger.info(f"📋 Recommended: {method} ({reason})")
    else:
        method = args.method
        logger.info(f"📋 Using forced method: {method}")
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run extraction
    success = False
    
    if method == "bigquery":
        success = run_bigquery_extraction(vcf_path, output_path)
    elif method == "vep":
        success = run_vep_extraction(vcf_path, output_path)
    
    if success:
        logger.info(f"\\n🎉 Population AF extraction complete!")
        logger.info(f"📁 Output: {output_path}")
        
        # Show file info
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024**2)
            logger.info(f"📊 File size: {size_mb:.1f} MB")
            
            # Preview results
            logger.info("\\n📋 Preview:")
            try:
                with open(output_path) as f:
                    for i, line in enumerate(f):
                        if i < 3:
                            print(f"  {line.strip()}")
                        else:
                            break
            except:
                pass
        
        return 0
    else:
        logger.error("❌ Extraction failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())