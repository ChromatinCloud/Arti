#!/usr/bin/env python3
"""
Comprehensive AF Dataset Extractor

Pre-extracts allele frequency data from major population datasets:
- gnomAD v4.1 (genomes & exomes) with all subpopulations
- All of Us (AoU) 
- 1000 Genomes Project
- ESP6500
- ExAC

Creates compact, indexed AF-only files for sub-second queries.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import tempfile
import logging
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
REFS_DIR = REPO_ROOT / ".refs"

# Major population datasets and their download locations
DATASETS = {
    "gnomad_v4_genomes": {
        "url": "https://gnomad-public-us-east-1.s3.amazonaws.com/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.vcf.bgz",
        "description": "gnomAD v4.1 genomes with all subpopulations",
        "size_gb": 85,
        "populations": ["AFR", "AMR", "ASJ", "EAS", "FIN", "NFE", "SAS", "OTH"]
    },
    "gnomad_v4_exomes": {
        "url": "https://gnomad-public-us-east-1.s3.amazonaws.com/release/4.1/vcf/exomes/gnomad.exomes.v4.1.sites.vcf.bgz", 
        "description": "gnomAD v4.1 exomes with all subpopulations",
        "size_gb": 45,
        "populations": ["AFR", "AMR", "ASJ", "EAS", "FIN", "NFE", "SAS", "OTH"]
    },
    "aou_v7": {
        "url": "gs://fc-aou-datasets-controlled/v7/wgs/short_read/snv_indel/aux/research/aou_wgs_research_v7.vcf.gz",
        "description": "All of Us v7 WGS variants", 
        "size_gb": 120,
        "populations": ["AFR", "AMR", "ASN", "EUR", "MID"],
        "note": "Requires GCP access to controlled-tier data"
    },
    "kg1_phase3": {
        "url": "http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5c.20130502.sites.vcf.gz",
        "description": "1000 Genomes Phase 3 all populations",
        "size_gb": 12,
        "populations": ["AFR", "AMR", "EAS", "EUR", "SAS"]
    },
    "esp6500": {
        "url": "https://esp.gs.washington.edu/drupal/sites/esp.gs.washington.edu/files/ESP6500SI-V2-SSA137.GRCh38-liftover.snps_indels.vcf.tar.gz",
        "description": "ESP6500 European American and African American",
        "size_gb": 3,
        "populations": ["EA", "AA", "ALL"]
    }
}

def check_available_space():
    """Check available disk space"""
    statvfs = os.statvfs(REFS_DIR)
    free_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
    logger.info(f"Available disk space: {free_gb:.1f} GB")
    
    total_size = sum(d["size_gb"] for d in DATASETS.values())
    logger.info(f"Total dataset size: {total_size} GB")
    
    if free_gb < total_size + 50:  # 50 GB buffer
        logger.warning(f"Low disk space! Need ~{total_size + 50} GB total")
        return False
    return True

def download_dataset(dataset_name, dataset_info, target_dir):
    """Download a single dataset"""
    url = dataset_info["url"]
    size_gb = dataset_info["size_gb"]
    
    logger.info(f"Downloading {dataset_name} ({size_gb} GB)...")
    
    # Create dataset-specific directory
    ds_dir = target_dir / dataset_name
    ds_dir.mkdir(parents=True, exist_ok=True)
    
    filename = Path(url).name
    output_path = ds_dir / filename
    
    # Skip if already exists
    if output_path.exists():
        logger.info(f"  {dataset_name}: Already exists, skipping download")
        return output_path
    
    # Handle different protocols
    if url.startswith("gs://"):
        return download_gcs_file(url, output_path)
    elif url.startswith("http"):
        return download_http_file(url, output_path)
    else:
        logger.error(f"Unsupported URL scheme: {url}")
        return None

def download_http_file(url, output_path):
    """Download file via HTTP with progress"""
    try:
        # Use wget for better progress and resume capability
        cmd = ["wget", "-c", "-O", str(output_path), url]
        
        logger.info(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024**2)
            logger.info(f"  Downloaded: {size_mb:.1f} MB")
            return output_path
        else:
            logger.error(f"  Download failed: {output_path} not created")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"  Download failed: {e}")
        return None
    except FileNotFoundError:
        logger.error("  wget not found, falling back to curl...")
        return download_with_curl(url, output_path)

def download_with_curl(url, output_path):
    """Fallback download with curl"""
    try:
        cmd = ["curl", "-L", "-o", str(output_path), url]
        subprocess.run(cmd, check=True)
        return output_path if output_path.exists() else None
    except subprocess.CalledProcessError as e:
        logger.error(f"  curl download failed: {e}")
        return None

def download_gcs_file(gs_url, output_path):
    """Download from Google Cloud Storage"""
    try:
        cmd = ["gsutil", "cp", gs_url, str(output_path)]
        
        logger.info(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        
        if output_path.exists():
            return output_path
        else:
            logger.error(f"  GCS download failed: {output_path} not created")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"  GCS download failed: {e}")
        logger.info("  Note: AoU data requires GCP access to controlled-tier datasets")
        return None
    except FileNotFoundError:
        logger.error("  gsutil not found - install Google Cloud SDK for AoU data")
        return None

def extract_af_data(vcf_path, output_path, dataset_info):
    """Extract AF data from VCF to compact format"""
    dataset_name = vcf_path.parent.name
    populations = dataset_info.get("populations", [])
    
    logger.info(f"Extracting AF data from {dataset_name}...")
    
    # Build bcftools command for AF extraction
    if "gnomad" in dataset_name:
        # gnomAD has complex AF fields: AF, AF_popmax, AF_<pop>, AC_<pop>, AN_<pop>
        af_fields = ["AF", "AF_popmax"]
        for pop in populations:
            af_fields.extend([f"AF_{pop}", f"AC_{pop}", f"AN_{pop}"])
        
        bcftools_cmd = [
            "bcftools", "query",
            "-f", f"%CHROM\\t%POS\\t%REF\\t%ALT\\t{','.join(['%' + f for f in af_fields])}\\n",
            str(vcf_path)
        ]
        
    elif "aou" in dataset_name:
        # All of Us format
        af_fields = ["AF"]
        for pop in populations:
            af_fields.append(f"AF_{pop}")
        
        bcftools_cmd = [
            "bcftools", "query", 
            "-f", f"%CHROM\\t%POS\\t%REF\\t%ALT\\t{','.join(['%' + f for f in af_fields])}\\n",
            str(vcf_path)
        ]
        
    elif "kg1" in dataset_name:
        # 1000 Genomes format
        bcftools_cmd = [
            "bcftools", "query",
            "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\t%AF\\t%EUR_AF\\t%AFR_AF\\t%AMR_AF\\t%EAS_AF\\t%SAS_AF\\n",
            str(vcf_path)
        ]
        
    else:
        # Generic format
        bcftools_cmd = [
            "bcftools", "query",
            "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\t%AF\\n", 
            str(vcf_path)
        ]
    
    # Create header
    if "gnomad" in dataset_name:
        header = ["CHROM", "POS", "REF", "ALT", "AF", "AF_popmax"] + [f"AF_{p}" for p in populations] + [f"AC_{p}" for p in populations] + [f"AN_{p}" for p in populations]
    elif "aou" in dataset_name:
        header = ["CHROM", "POS", "REF", "ALT", "AF"] + [f"AF_{p}" for p in populations]
    elif "kg1" in dataset_name:
        header = ["CHROM", "POS", "REF", "ALT", "AF", "EUR_AF", "AFR_AF", "AMR_AF", "EAS_AF", "SAS_AF"]
    else:
        header = ["CHROM", "POS", "REF", "ALT", "AF"]
    
    try:
        # Extract and compress
        with open(output_path, 'w') as out_f:
            # Write header
            out_f.write("\\t".join(header) + "\\n")
            
            # Run bcftools and write data
            result = subprocess.run(bcftools_cmd, stdout=out_f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"bcftools failed: {result.stderr}")
                return False
        
        # Compress and index
        compressed_path = output_path.with_suffix(output_path.suffix + ".gz")
        
        # bgzip the file
        subprocess.run(["bgzip", "-f", str(output_path)], check=True)
        
        # Create tabix index
        subprocess.run(["tabix", "-f", "-s1", "-b2", "-e2", str(compressed_path)], check=True)
        
        # Check output size
        if compressed_path.exists():
            size_mb = compressed_path.stat().st_size / (1024**2)
            logger.info(f"  Created {compressed_path.name}: {size_mb:.1f} MB")
            return compressed_path
        else:
            logger.error(f"  Failed to create {compressed_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"AF extraction failed: {e}")
        return False
    except FileNotFoundError as e:
        logger.error(f"Required tool not found: {e}")
        logger.error("Install bcftools, bgzip, and tabix")
        return False

def create_af_lookup_index(af_files, output_dir):
    """Create unified AF lookup index"""
    index_file = output_dir / "af_lookup_index.json"
    
    index_data = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "datasets": {},
        "total_variants": 0
    }
    
    for af_file in af_files:
        if not af_file or not af_file.exists():
            continue
            
        dataset_name = af_file.parent.name
        
        # Count variants
        try:
            result = subprocess.run(
                ["zcat", str(af_file), "|", "wc", "-l"], 
                shell=True, capture_output=True, text=True
            )
            variant_count = int(result.stdout.strip()) - 1  # Subtract header
        except:
            variant_count = 0
        
        index_data["datasets"][dataset_name] = {
            "file": str(af_file.relative_to(output_dir)),
            "variant_count": variant_count,
            "size_mb": af_file.stat().st_size / (1024**2)
        }
        
        index_data["total_variants"] += variant_count
    
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=2)
    
    logger.info(f"Created lookup index: {index_file}")
    logger.info(f"Total variants across all datasets: {index_data['total_variants']:,}")
    
    return index_file

def main():
    parser = argparse.ArgumentParser(
        description="Extract comprehensive AF datasets for fast lookups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available datasets:
{chr(10).join([f"  {name}: {info['description']} ({info['size_gb']} GB)" for name, info in DATASETS.items()])}

Examples:
  # Download and extract all datasets
  python extract_af_datasets.py --all
  
  # Just gnomAD datasets  
  python extract_af_datasets.py --datasets gnomad_v4_genomes gnomad_v4_exomes
  
  # Check what's available without downloading
  python extract_af_datasets.py --list
  
  # Extract from already downloaded files
  python extract_af_datasets.py --extract-only
        """
    )
    
    parser.add_argument("--datasets", nargs="+", choices=list(DATASETS.keys()),
                       help="Specific datasets to download/extract")
    parser.add_argument("--all", action="store_true", help="Download/extract all datasets")
    parser.add_argument("--extract-only", action="store_true", 
                       help="Only extract AF data from existing downloads")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--output-dir", default=str(REFS_DIR / "af_datasets"),
                       help="Output directory for AF datasets")
    parser.add_argument("--parallel", type=int, default=2, 
                       help="Number of parallel downloads (default: 2)")
    
    args = parser.parse_args()
    
    if args.list:
        print("\\nAvailable datasets:")
        for name, info in DATASETS.items():
            print(f"  {name}:")
            print(f"    Description: {info['description']}")
            print(f"    Size: {info['size_gb']} GB")
            print(f"    Populations: {', '.join(info['populations'])}")
            if 'note' in info:
                print(f"    Note: {info['note']}")
            print()
        return 0
    
    # Determine which datasets to process
    if args.all:
        datasets_to_process = list(DATASETS.keys())
    elif args.datasets:
        datasets_to_process = args.datasets
    else:
        logger.error("Specify --all, --datasets, or --list")
        return 1
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check disk space
    if not args.extract_only and not check_available_space():
        logger.error("Insufficient disk space")
        return 1
    
    logger.info(f"Processing {len(datasets_to_process)} datasets...")
    
    # Download datasets (if not extract-only)
    downloaded_files = []
    if not args.extract_only:
        logger.info("=== DOWNLOAD PHASE ===")
        
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            download_futures = {
                executor.submit(download_dataset, name, DATASETS[name], output_dir): name
                for name in datasets_to_process
            }
            
            for future in as_completed(download_futures):
                dataset_name = download_futures[future]
                try:
                    result = future.result()
                    if result:
                        downloaded_files.append(result)
                        logger.info(f"✅ Downloaded {dataset_name}")
                    else:
                        logger.error(f"❌ Failed to download {dataset_name}")
                except Exception as e:
                    logger.error(f"❌ Exception downloading {dataset_name}: {e}")
    else:
        # Find existing files
        for name in datasets_to_process:
            ds_dir = output_dir / name
            if ds_dir.exists():
                vcf_files = list(ds_dir.glob("*.vcf.gz")) + list(ds_dir.glob("*.vcf.bgz"))
                downloaded_files.extend(vcf_files)
    
    # Extract AF data
    logger.info("=== EXTRACTION PHASE ===")
    af_files = []
    
    for vcf_file in downloaded_files:
        dataset_name = vcf_file.parent.name
        af_output = vcf_file.parent / f"{dataset_name}_af_data.tsv"
        
        dataset_info = None
        for name, info in DATASETS.items():
            if name == dataset_name:
                dataset_info = info
                break
        
        if not dataset_info:
            logger.warning(f"No dataset info for {dataset_name}, using generic extraction")
            dataset_info = {"populations": []}
        
        result = extract_af_data(vcf_file, af_output, dataset_info)
        if result:
            af_files.append(result)
    
    # Create lookup index
    if af_files:
        logger.info("=== INDEXING PHASE ===")
        create_af_lookup_index(af_files, output_dir)
        
        logger.info(f"\\n🎉 Successfully created {len(af_files)} AF datasets!")
        logger.info(f"📁 Output directory: {output_dir}")
        logger.info("\\n🚀 These files provide sub-second AF lookups for:")
        for af_file in af_files:
            logger.info(f"   • {af_file.name}")
    else:
        logger.error("No AF files were created")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())