#!/usr/bin/env python3
"""
gnomAD v4.1 Extractor using bcftools view
More robust approach for cloud-hosted VCF files
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GNOMAD_V4_BASE = "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{}.vcf.bgz"

def extract_gnomad_v4_robust(vcf_file, output_file):
    """Extract gnomAD v4.1 AFs using bcftools view with wider regions"""
    
    logger.info("🚀 Extracting gnomAD v4.1 allele frequencies (robust method)")
    
    # Parse input VCF
    variants_by_chr = {}
    
    try:
        with open(vcf_file) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    chrom = parts[0].replace('chr', '')
                    pos = int(parts[1])
                    ref = parts[3]
                    alt = parts[4]
                    
                    if chrom not in variants_by_chr:
                        variants_by_chr[chrom] = []
                    
                    variants_by_chr[chrom].append({
                        'pos': pos,
                        'ref': ref,
                        'alt': alt
                    })
        
        total_variants = sum(len(v) for v in variants_by_chr.values())
        logger.info(f"Found {total_variants} variants across {len(variants_by_chr)} chromosomes")
        
    except Exception as e:
        logger.error(f"Failed to parse VCF: {e}")
        return False
    
    # Collect all results
    all_results = []
    
    for chrom, variants in variants_by_chr.items():
        logger.info(f"Processing chromosome {chrom} ({len(variants)} variants)...")
        
        # Create regions that are slightly wider to ensure we catch the variants
        regions = []
        for var in variants:
            # Add 10bp padding on each side
            regions.append(f"{chrom}:{var['pos']-10}-{var['pos']+10}")
        
        # gnomAD URL for this chromosome
        gnomad_url = GNOMAD_V4_BASE.format(chrom)
        
        # Try different approaches
        for region in regions:
            cmd = [
                "bcftools", "view", "-H",
                "-r", region,
                gnomad_url
            ]
            
            try:
                logger.debug(f"Querying region {region}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout:
                    # Parse each line
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('\t')
                            if len(parts) >= 8:
                                var_chrom = parts[0]
                                var_pos = int(parts[1])
                                var_ref = parts[3]
                                var_alt = parts[4]
                                info = parts[7]
                                
                                # Check if this matches any of our variants
                                for target_var in variants:
                                    if (var_pos == target_var['pos'] and 
                                        var_ref == target_var['ref'] and 
                                        var_alt == target_var['alt']):
                                        
                                        # Extract AF fields from INFO
                                        af_data = {
                                            'CHROM': var_chrom,
                                            'POS': str(var_pos),
                                            'REF': var_ref,
                                            'ALT': var_alt
                                        }
                                        
                                        # Parse INFO field for AF values
                                        for field in info.split(';'):
                                            if '=' in field:
                                                key, value = field.split('=', 1)
                                                if key in ['AF', 'AF_grpmax', 'AF_afr', 'AF_amr', 
                                                          'AF_asj', 'AF_eas', 'AF_fin', 'AF_nfe', 
                                                          'AF_sas', 'AF_mid', 'AF_ami', 'AF_remaining']:
                                                    af_data[key] = value
                                        
                                        all_results.append(af_data)
                                        logger.info(f"✓ Found variant {var_chrom}:{var_pos} {var_ref}>{var_alt}")
                                        break
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout querying region {region}")
            except Exception as e:
                logger.warning(f"Error querying region {region}: {e}")
    
    # Write results
    if all_results:
        with open(output_file, 'w') as f:
            # Header
            headers = ['CHROM', 'POS', 'REF', 'ALT', 'AF', 'AF_grpmax', 
                      'AF_afr', 'AF_amr', 'AF_asj', 'AF_eas', 'AF_fin', 
                      'AF_nfe', 'AF_sas', 'AF_mid', 'AF_ami', 'AF_remaining']
            f.write('\t'.join(headers) + '\n')
            
            # Data
            for result in all_results:
                row = [result.get(h, '') for h in headers]
                f.write('\t'.join(row) + '\n')
        
        logger.info(f"✅ Successfully extracted gnomAD v4.1 data for {len(all_results)} variants")
        return True
    else:
        logger.warning("No matching variants found in gnomAD v4.1")
        
        # Let's check if we can access the data at all
        logger.info("\nTesting gnomAD v4.1 accessibility...")
        test_regions = [
            ("1", "1:10000-11000"),
            ("7", "7:140000000-140001000"),
            ("17", "17:7670000-7680000")
        ]
        
        for test_chrom, test_region in test_regions:
            url = GNOMAD_V4_BASE.format(test_chrom)
            cmd = ["bcftools", "view", "-H", "-r", test_region, url]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    line_count = len(result.stdout.strip().split('\n')) if result.stdout else 0
                    if line_count > 0:
                        logger.info(f"✓ Can access gnomAD v4.1 chr{test_chrom} - found {line_count} variants in test region")
                    else:
                        logger.info(f"✓ Can access gnomAD v4.1 chr{test_chrom} - but no variants in test region")
                else:
                    logger.warning(f"✗ Cannot access gnomAD v4.1 chr{test_chrom}")
            except:
                logger.warning(f"✗ Error accessing gnomAD v4.1 chr{test_chrom}")
        
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Extract gnomAD v4.1 population frequencies (robust method)"
    )
    
    parser.add_argument("vcf_file", help="Input VCF file")
    parser.add_argument("--output", "-o", required=True, help="Output TSV file")
    
    args = parser.parse_args()
    
    vcf_path = Path(args.vcf_file)
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract gnomAD v4.1 data
    success = extract_gnomad_v4_robust(vcf_path, output_path)
    
    if success and output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        
        with open(output_path) as f:
            line_count = sum(1 for line in f) - 1
        
        logger.info(f"\n🎉 gnomAD v4.1 extraction complete!")
        logger.info(f"📁 Output: {output_path}")
        logger.info(f"📊 {line_count} variants, {size_kb:.1f} KB")
        
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
        logger.info("\nYour variants were not found in gnomAD v4.1.")
        logger.info("This is normal - gnomAD only contains variants observed in their population cohort.")
        logger.info("Consider using variants from known common SNPs or cancer hotspots for testing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())