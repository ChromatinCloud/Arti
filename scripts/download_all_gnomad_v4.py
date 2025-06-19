#!/usr/bin/env python3
"""
Download ALL gnomAD v4 variant data

This downloads the complete gnomAD v4.1 dataset with all population AFs.
Warning: This is ~50-100GB of compressed data!
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# gnomAD v4.1 download URLs
GNOMAD_V4_BASE = {
    "genomes": "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{}.vcf.bgz",
    "exomes": "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/exomes/gnomad.exomes.v4.1.sites.chr{}.vcf.bgz"
}

# Chromosomes to download
CHROMOSOMES = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 
               '11', '12', '13', '14', '15', '16', '17', '18', '19', 
               '20', '21', '22', 'X', 'Y']

def estimate_size():
    """Estimate total download size"""
    logger.info("Estimating download size...")
    
    # These are rough estimates based on gnomAD v4 file sizes
    sizes = {
        "genomes": {
            "per_chr_avg_gb": 2.5,  # Average ~2.5GB per chromosome
            "total_gb": 60
        },
        "exomes": {
            "per_chr_avg_gb": 4.0,  # Exomes are larger due to more samples
            "total_gb": 96
        }
    }
    
    logger.info(f"Estimated sizes:")
    logger.info(f"  Genomes: ~{sizes['genomes']['total_gb']}GB compressed")
    logger.info(f"  Exomes: ~{sizes['exomes']['total_gb']}GB compressed")
    logger.info(f"  Total: ~{sizes['genomes']['total_gb'] + sizes['exomes']['total_gb']}GB compressed")
    logger.info(f"  Uncompressed: ~{(sizes['genomes']['total_gb'] + sizes['exomes']['total_gb']) * 5}GB")
    
    return sizes

def download_chromosome(dataset, chrom, output_dir, skip_existing=True):
    """Download a single chromosome file"""
    
    url = GNOMAD_V4_BASE[dataset].format(chrom)
    filename = f"gnomad.{dataset}.v4.1.sites.chr{chrom}.vcf.bgz"
    output_path = output_dir / filename
    
    # Check if already exists
    if skip_existing and output_path.exists():
        size_gb = output_path.stat().st_size / (1024**3)
        if size_gb > 0.1:  # At least 100MB
            logger.info(f"✓ Already exists: {filename} ({size_gb:.1f}GB)")
            return True, filename, size_gb
    
    logger.info(f"Downloading {dataset} chr{chrom}...")
    
    # Download with wget (more reliable for large files)
    cmd = [
        "wget", 
        "-c",  # Continue partial downloads
        "-O", str(output_path),
        url
    ]
    
    try:
        start_time = time.time()
        subprocess.run(cmd, check=True)
        
        # Also download the index
        index_url = url + ".tbi"
        index_cmd = ["wget", "-c", "-O", str(output_path) + ".tbi", index_url]
        subprocess.run(index_cmd, check=True)
        
        duration = time.time() - start_time
        size_gb = output_path.stat().st_size / (1024**3)
        
        logger.info(f"✓ Downloaded {filename} ({size_gb:.1f}GB in {duration:.0f}s)")
        return True, filename, size_gb
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to download {filename}: {e}")
        return False, filename, 0

def extract_all_afs(vcf_file, output_file):
    """Extract all AFs from a downloaded VCF file"""
    
    logger.info(f"Extracting AFs from {vcf_file.name}...")
    
    # Extract specific fields including all population AFs
    cmd = [
        "bcftools", "query",
        "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/AF\\t%INFO/AF_afr\\t%INFO/AF_ami\\t%INFO/AF_amr\\t%INFO/AF_asj\\t%INFO/AF_eas\\t%INFO/AF_fin\\t%INFO/AF_mid\\t%INFO/AF_nfe\\t%INFO/AF_sas\\t%INFO/AF_remaining\\t%INFO/AF_grpmax\\t%INFO/AN\\t%INFO/AC\\n",
        str(vcf_file)
    ]
    
    try:
        with open(output_file, 'w') as f:
            # Write header
            f.write("CHROM\tPOS\tREF\tALT\tAF\tAF_afr\tAF_ami\tAF_amr\tAF_asj\tAF_eas\tAF_fin\tAF_mid\tAF_nfe\tAF_sas\tAF_remaining\tAF_grpmax\tAN\tAC\n")
            
            # Run extraction
            subprocess.run(cmd, stdout=f, check=True)
        
        # Count variants
        with open(output_file) as f:
            variant_count = sum(1 for line in f) - 1
        
        size_mb = output_file.stat().st_size / (1024**2)
        logger.info(f"✓ Extracted {variant_count:,} variants ({size_mb:.1f}MB)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to extract AFs: {e}")
        return False

def create_combined_af_file(af_dir, output_file):
    """Combine all chromosome AF files into one"""
    
    logger.info("Combining all AF files...")
    
    af_files = sorted(af_dir.glob("*.af.tsv"))
    
    with open(output_file, 'w') as out:
        # Write header once
        header_written = False
        
        for af_file in af_files:
            logger.info(f"  Adding {af_file.name}")
            
            with open(af_file) as f:
                lines = f.readlines()
                
                if not header_written:
                    out.write(lines[0])  # Header
                    header_written = True
                
                # Write data lines
                out.writelines(lines[1:])
    
    size_gb = output_file.stat().st_size / (1024**3)
    
    with open(output_file) as f:
        total_variants = sum(1 for line in f) - 1
    
    logger.info(f"✓ Combined file created: {total_variants:,} variants ({size_gb:.1f}GB)")

def main():
    parser = argparse.ArgumentParser(
        description="Download ALL gnomAD v4 variant data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This downloads the COMPLETE gnomAD v4.1 dataset.

WARNING: This requires ~150GB of disk space for compressed files
         and ~750GB if you uncompress them!

Steps:
1. Downloads all chromosome VCF files
2. Extracts AF data to TSV format
3. Optionally combines into single file

Examples:
  # Download only genomes
  python download_all_gnomad_v4.py --output-dir gnomad_v4_data --dataset genomes
  
  # Download only specific chromosomes
  python download_all_gnomad_v4.py --output-dir gnomad_v4_data --chromosomes 1,2,3
  
  # Extract AFs after download
  python download_all_gnomad_v4.py --output-dir gnomad_v4_data --extract-only
  
  # Full pipeline: download + extract + combine
  python download_all_gnomad_v4.py --output-dir gnomad_v4_data --dataset genomes --extract --combine
        """
    )
    
    parser.add_argument("--output-dir", required=True, help="Output directory for downloads")
    parser.add_argument("--dataset", choices=["genomes", "exomes", "both"], default="genomes",
                       help="Which dataset to download")
    parser.add_argument("--chromosomes", help="Specific chromosomes (comma-separated, e.g., '1,2,X')")
    parser.add_argument("--extract", action="store_true", help="Extract AFs to TSV after download")
    parser.add_argument("--extract-only", action="store_true", help="Only extract AFs from existing files")
    parser.add_argument("--combine", action="store_true", help="Combine all chromosome files")
    parser.add_argument("--threads", type=int, default=4, help="Number of parallel downloads")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine which chromosomes to process
    if args.chromosomes:
        chromosomes = args.chromosomes.split(',')
    else:
        chromosomes = CHROMOSOMES
    
    # Determine which datasets
    if args.dataset == "both":
        datasets = ["genomes", "exomes"]
    else:
        datasets = [args.dataset]
    
    # Estimate size
    if not args.extract_only:
        sizes = estimate_size()
        
        response = input("\nProceed with download? (y/n): ")
        if response.lower() != 'y':
            logger.info("Download cancelled")
            return 0
    
    # Extract only mode
    if args.extract_only:
        logger.info("Extract-only mode")
        
        for dataset in datasets:
            dataset_dir = output_dir / dataset
            af_dir = output_dir / f"{dataset}_afs"
            af_dir.mkdir(exist_ok=True)
            
            for chrom in chromosomes:
                vcf_file = dataset_dir / f"gnomad.{dataset}.v4.1.sites.chr{chrom}.vcf.bgz"
                if vcf_file.exists():
                    af_file = af_dir / f"chr{chrom}.af.tsv"
                    extract_all_afs(vcf_file, af_file)
            
            if args.combine:
                combined_file = output_dir / f"gnomad.{dataset}.v4.1.all_afs.tsv"
                create_combined_af_file(af_dir, combined_file)
        
        return 0
    
    # Download mode
    total_downloaded = 0
    
    for dataset in datasets:
        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading gnomAD v4.1 {dataset}")
        logger.info(f"{'='*60}")
        
        dataset_dir = output_dir / dataset
        dataset_dir.mkdir(exist_ok=True)
        
        # Download with thread pool
        download_tasks = []
        
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            for chrom in chromosomes:
                task = executor.submit(download_chromosome, dataset, chrom, dataset_dir)
                download_tasks.append((chrom, task))
            
            # Track progress
            completed = 0
            total_size = 0
            
            for chrom, task in download_tasks:
                success, filename, size_gb = task.result()
                completed += 1
                total_size += size_gb
                
                logger.info(f"Progress: {completed}/{len(chromosomes)} chromosomes, {total_size:.1f}GB total")
        
        total_downloaded += total_size
        
        # Extract AFs if requested
        if args.extract:
            logger.info(f"\nExtracting AFs from {dataset}...")
            af_dir = output_dir / f"{dataset}_afs"
            af_dir.mkdir(exist_ok=True)
            
            for chrom in chromosomes:
                vcf_file = dataset_dir / f"gnomad.{dataset}.v4.1.sites.chr{chrom}.vcf.bgz"
                if vcf_file.exists():
                    af_file = af_dir / f"chr{chrom}.af.tsv"
                    extract_all_afs(vcf_file, af_file)
            
            # Combine if requested
            if args.combine:
                combined_file = output_dir / f"gnomad.{dataset}.v4.1.all_afs.tsv"
                create_combined_af_file(af_dir, combined_file)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ Download complete!")
    logger.info(f"📁 Total downloaded: {total_downloaded:.1f}GB")
    logger.info(f"📂 Output directory: {output_dir}")
    logger.info(f"{'='*60}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())