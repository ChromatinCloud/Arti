#!/usr/bin/env python3
"""
Stream ALL gnomAD v4 AFs without downloading full files

This streams directly from Google Cloud Storage and extracts only the AF data.
Much more efficient than downloading everything!
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# gnomAD v4.1 URLs
GNOMAD_V4_URLS = {
    "genomes": "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{}.vcf.bgz",
    "exomes": "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/exomes/gnomad.exomes.v4.1.sites.chr{}.vcf.bgz"
}

CHROMOSOMES = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 
               '11', '12', '13', '14', '15', '16', '17', '18', '19', 
               '20', '21', '22', 'X', 'Y']

def stream_chromosome_afs(dataset, chrom, output_file, fields="minimal"):
    """Stream AFs for a single chromosome directly from URL"""
    
    url = GNOMAD_V4_URLS[dataset].format(chrom)
    
    logger.info(f"Streaming {dataset} chr{chrom} AFs...")
    
    # Define field extraction based on mode
    if fields == "minimal":
        # Just AF and max pop AF
        format_str = "%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/AF\\t%INFO/AF_grpmax\\n"
        header = "CHROM\tPOS\tREF\tALT\tAF\tAF_grpmax\n"
    elif fields == "populations":
        # All population AFs
        format_str = "%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/AF\\t%INFO/AF_afr\\t%INFO/AF_ami\\t%INFO/AF_amr\\t%INFO/AF_asj\\t%INFO/AF_eas\\t%INFO/AF_fin\\t%INFO/AF_mid\\t%INFO/AF_nfe\\t%INFO/AF_sas\\t%INFO/AF_remaining\\n"
        header = "CHROM\tPOS\tREF\tALT\tAF\tAF_afr\tAF_ami\tAF_amr\tAF_asj\tAF_eas\tAF_fin\tAF_mid\tAF_nfe\tAF_sas\tAF_remaining\n"
    else:  # comprehensive
        format_str = "%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/AF\\t%INFO/AF_afr\\t%INFO/AF_ami\\t%INFO/AF_amr\\t%INFO/AF_asj\\t%INFO/AF_eas\\t%INFO/AF_fin\\t%INFO/AF_mid\\t%INFO/AF_nfe\\t%INFO/AF_sas\\t%INFO/AF_remaining\\t%INFO/AF_grpmax\\t%INFO/AN\\t%INFO/AC\\t%INFO/popmax\\n"
        header = "CHROM\tPOS\tREF\tALT\tAF\tAF_afr\tAF_ami\tAF_amr\tAF_asj\tAF_eas\tAF_fin\tAF_mid\tAF_nfe\tAF_sas\tAF_remaining\tAF_grpmax\tAN\tAC\tpopmax\n"
    
    # Stream with bcftools
    cmd = [
        "bcftools", "query",
        "-f", format_str,
        url
    ]
    
    try:
        start_time = time.time()
        variant_count = 0
        
        # Write header if this is a new file
        write_header = not output_file.exists() or output_file.stat().st_size == 0
        
        with open(output_file, 'a') as f:
            if write_header:
                f.write(header)
            
            # Stream data
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Process lines as they come
            for line in process.stdout:
                f.write(line)
                variant_count += 1
                
                # Progress update every 100k variants
                if variant_count % 100000 == 0:
                    logger.info(f"  Chr{chrom}: {variant_count:,} variants processed...")
            
            process.wait()
            
            if process.returncode != 0:
                stderr = process.stderr.read()
                logger.error(f"Error streaming chr{chrom}: {stderr}")
                return False, 0
        
        duration = time.time() - start_time
        logger.info(f"✓ Chr{chrom}: {variant_count:,} variants in {duration:.1f}s ({variant_count/duration:.0f} var/s)")
        
        return True, variant_count
        
    except Exception as e:
        logger.error(f"✗ Failed to stream chr{chrom}: {e}")
        return False, 0

def estimate_variants():
    """Estimate total number of variants"""
    
    estimates = {
        "genomes": {
            "chr1": 25_000_000,
            "total": 600_000_000  # ~600M variants in genomes
        },
        "exomes": {
            "chr1": 10_000_000,
            "total": 250_000_000  # ~250M variants in exomes
        }
    }
    
    logger.info("Estimated variant counts:")
    logger.info(f"  Genomes: ~{estimates['genomes']['total']:,} variants")
    logger.info(f"  Exomes: ~{estimates['exomes']['total']:,} variants")
    
    return estimates

def create_filtered_stream(dataset, chrom, output_file, min_af=0.001):
    """Stream only common variants (AF >= threshold)"""
    
    url = GNOMAD_V4_URLS[dataset].format(chrom)
    
    logger.info(f"Streaming {dataset} chr{chrom} with AF >= {min_af}...")
    
    # Use awk to filter on the fly
    cmd = f"""
    bcftools query -f '%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/AF\\t%INFO/AF_afr\\t%INFO/AF_amr\\t%INFO/AF_asj\\t%INFO/AF_eas\\t%INFO/AF_fin\\t%INFO/AF_nfe\\t%INFO/AF_sas\\n' {url} | \
    awk -F'\\t' 'BEGIN {{OFS="\\t"}} $5 >= {min_af} {{print}}'
    """
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        
        variant_count = len(result.stdout.strip().split('\n'))
        
        with open(output_file, 'a') as f:
            if output_file.stat().st_size == 0:
                f.write("CHROM\tPOS\tREF\tALT\tAF\tAF_afr\tAF_amr\tAF_asj\tAF_eas\tAF_fin\tAF_nfe\tAF_sas\n")
            f.write(result.stdout)
        
        duration = time.time() - start_time
        logger.info(f"✓ Chr{chrom}: {variant_count:,} common variants (AF>={min_af}) in {duration:.1f}s")
        
        return True, variant_count
        
    except Exception as e:
        logger.error(f"✗ Failed to stream chr{chrom}: {e}")
        return False, 0

def main():
    parser = argparse.ArgumentParser(
        description="Stream ALL gnomAD v4 AFs without downloading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This streams gnomAD v4.1 data directly from Google Cloud Storage.
No need to download 150GB of data!

Output formats:
- minimal: CHROM, POS, REF, ALT, AF, AF_grpmax (smallest)
- populations: Above + all population AFs (recommended)
- comprehensive: Everything including AN, AC, popmax

Examples:
  # Stream all genome AFs (all populations)
  python stream_gnomad_v4_afs.py --dataset genomes --output gnomad_v4_genome_afs.tsv
  
  # Stream only specific chromosomes
  python stream_gnomad_v4_afs.py --dataset genomes --output gnomad_chr1-3.tsv --chromosomes 1,2,3
  
  # Get only common variants (AF >= 0.1%)
  python stream_gnomad_v4_afs.py --dataset genomes --output common_variants.tsv --min-af 0.001
  
  # Minimal output (faster, smaller file)
  python stream_gnomad_v4_afs.py --dataset genomes --output gnomad_minimal.tsv --fields minimal
  
  # Run in parallel (faster for multiple chromosomes)
  python stream_gnomad_v4_afs.py --dataset genomes --output gnomad_afs.tsv --threads 4
        """
    )
    
    parser.add_argument("--dataset", choices=["genomes", "exomes"], required=True,
                       help="Which dataset to stream")
    parser.add_argument("--output", "-o", required=True, help="Output TSV file")
    parser.add_argument("--chromosomes", help="Specific chromosomes (default: all)")
    parser.add_argument("--fields", choices=["minimal", "populations", "comprehensive"], 
                       default="populations", help="Which fields to extract")
    parser.add_argument("--min-af", type=float, help="Only keep variants with AF >= threshold")
    parser.add_argument("--threads", type=int, default=1, help="Number of parallel streams")
    parser.add_argument("--append", action="store_true", help="Append to existing file")
    
    args = parser.parse_args()
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Clear file if not appending
    if not args.append and output_path.exists():
        output_path.unlink()
    
    # Determine chromosomes
    if args.chromosomes:
        chromosomes = args.chromosomes.split(',')
    else:
        chromosomes = CHROMOSOMES
    
    logger.info(f"Streaming gnomAD v4.1 {args.dataset} data")
    logger.info(f"Chromosomes: {', '.join(chromosomes)}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Fields: {args.fields}")
    
    if args.min_af:
        logger.info(f"Filtering: AF >= {args.min_af}")
    
    # Estimate size
    estimates = estimate_variants()
    
    start_time = time.time()
    total_variants = 0
    
    if args.threads > 1:
        # Parallel processing
        logger.info(f"Using {args.threads} parallel streams")
        
        # Create temporary files for each chromosome
        temp_files = {}
        for chrom in chromosomes:
            temp_files[chrom] = output_path.parent / f".tmp_chr{chrom}.tsv"
        
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            tasks = {}
            
            for chrom in chromosomes:
                if args.min_af:
                    task = executor.submit(create_filtered_stream, args.dataset, 
                                         chrom, temp_files[chrom], args.min_af)
                else:
                    task = executor.submit(stream_chromosome_afs, args.dataset, 
                                         chrom, temp_files[chrom], args.fields)
                tasks[task] = chrom
            
            # Wait for completion
            for task in as_completed(tasks):
                chrom = tasks[task]
                success, variant_count = task.result()
                if success:
                    total_variants += variant_count
        
        # Combine temporary files
        logger.info("Combining chromosome files...")
        
        with open(output_path, 'w') as out:
            header_written = False
            
            for chrom in chromosomes:
                temp_file = temp_files[chrom]
                if temp_file.exists():
                    with open(temp_file) as f:
                        lines = f.readlines()
                        
                        if lines:
                            if not header_written:
                                out.write(lines[0])  # Header
                                header_written = True
                            
                            out.writelines(lines[1:] if len(lines) > 1 else [])
                    
                    # Clean up
                    temp_file.unlink()
    
    else:
        # Sequential processing
        for chrom in chromosomes:
            if args.min_af:
                success, variant_count = create_filtered_stream(
                    args.dataset, chrom, output_path, args.min_af)
            else:
                success, variant_count = stream_chromosome_afs(
                    args.dataset, chrom, output_path, args.fields)
            
            if success:
                total_variants += variant_count
    
    duration = time.time() - start_time
    
    # Final statistics
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024**2)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Streaming complete!")
        logger.info(f"📁 Output: {output_path}")
        logger.info(f"📊 Total variants: {total_variants:,}")
        logger.info(f"💾 File size: {size_mb:.1f}MB")
        logger.info(f"⏱️  Time: {duration:.1f}s ({total_variants/duration:.0f} variants/s)")
        logger.info(f"{'='*60}")
        
        # Show preview
        logger.info("\n📋 Preview:")
        with open(output_path) as f:
            for i, line in enumerate(f):
                if i < 5:
                    print(f"  {line.strip()}")
                else:
                    break
        
        return 0
    else:
        logger.error("No output generated")
        return 1

if __name__ == "__main__":
    sys.exit(main())