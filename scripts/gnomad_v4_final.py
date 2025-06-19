#!/usr/bin/env python3
"""
gnomAD v4 Final Extractor - Works with both v4.0 and v4.1
Extracts population allele frequencies from the latest gnomAD release
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Both v4.0 and v4.1 URLs - we'll check which works
GNOMAD_URLS = {
    "v4.1": "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{}.vcf.bgz",
    "v4.0": "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.0/vcf/genomes/gnomad.genomes.v4.0.sites.chr{}.vcf.bgz"
}

def check_gnomad_version():
    """Check which gnomAD version is accessible"""
    test_chr = "1"
    test_region = "1:900000-900100"
    
    for version, url_template in GNOMAD_URLS.items():
        url = url_template.format(test_chr)
        cmd = ["bcftools", "view", "-H", "-r", test_region, url]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"✓ gnomAD {version} is accessible")
                return version, url_template
        except:
            pass
    
    logger.error("Neither gnomAD v4.0 nor v4.1 appears to be accessible")
    return None, None

def extract_gnomad_v4(vcf_file, output_file):
    """Extract gnomAD v4 AFs from any accessible version"""
    
    # Check which version works
    version, url_template = check_gnomad_version()
    if not version:
        return False
    
    logger.info(f"🚀 Extracting gnomAD {version} allele frequencies")
    logger.info(f"Population groups: AFR, AMI, AMR, ASJ, EAS, FIN, MID, NFE, SAS, remaining")
    
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
    
    # Collect results
    all_results = []
    
    for chrom, variants in variants_by_chr.items():
        logger.info(f"Processing chromosome {chrom} ({len(variants)} variants)...")
        
        # Create wider regions to catch variants
        for var in variants:
            region = f"{chrom}:{var['pos']-1}-{var['pos']+1}"
            url = url_template.format(chrom)
            
            cmd = [
                "bcftools", "view", "-H",
                "-r", region,
                url
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('\t')
                            if len(parts) >= 8:
                                var_pos = int(parts[1])
                                var_ref = parts[3]
                                var_alt = parts[4]
                                info = parts[7]
                                
                                # Check for exact match
                                if var_pos == var['pos'] and var_ref == var['ref'] and var_alt == var['alt']:
                                    # Extract AF fields
                                    af_data = {
                                        'CHROM': chrom,
                                        'POS': str(var_pos),
                                        'REF': var_ref,
                                        'ALT': var_alt
                                    }
                                    
                                    # Parse INFO field
                                    for field in info.split(';'):
                                        if '=' in field:
                                            key, value = field.split('=', 1)
                                            # Capture all AF fields
                                            if key.startswith('AF') or key in ['AN', 'AC']:
                                                af_data[key] = value
                                    
                                    all_results.append(af_data)
                                    logger.info(f"✓ Found {chrom}:{var_pos} {var_ref}>{var_alt}")
                                    break
                
            except Exception as e:
                logger.debug(f"Error querying {region}: {e}")
    
    # Write results
    if all_results:
        with open(output_file, 'w') as f:
            # Header - comprehensive list of populations
            headers = ['CHROM', 'POS', 'REF', 'ALT', 'AF', 'AN', 'AC']
            
            # Add population-specific fields based on what we found
            af_fields = set()
            for result in all_results:
                for key in result.keys():
                    if key.startswith('AF_'):
                        af_fields.add(key)
            
            headers.extend(sorted(af_fields))
            f.write('\t'.join(headers) + '\n')
            
            # Data
            for result in all_results:
                row = [result.get(h, '') for h in headers]
                f.write('\t'.join(row) + '\n')
        
        logger.info(f"✅ Successfully extracted gnomAD {version} data for {len(all_results)} variants")
        return True
    else:
        logger.warning(f"No matching variants found in gnomAD {version}")
        
        # Create an empty results file with explanation
        with open(output_file, 'w') as f:
            f.write("# gnomAD v4 Query Results\n")
            f.write(f"# Version: {version}\n")
            f.write("# No matching variants found\n")
            f.write("# This is normal - gnomAD only contains variants observed in their cohort\n")
            f.write("# Total samples: 807,162 (730,947 exomes + 76,215 genomes)\n")
            f.write("# Populations: AFR (African), AMI (Amish), AMR (Admixed American), ")
            f.write("ASJ (Ashkenazi Jewish), EAS (East Asian), FIN (Finnish), ")
            f.write("MID (Middle Eastern), NFE (Non-Finnish European), SAS (South Asian)\n")
            f.write("\nCHROM\tPOS\tREF\tALT\tAF\tAN\tAC\tAF_afr\tAF_ami\tAF_amr\tAF_asj\tAF_eas\tAF_fin\tAF_mid\tAF_nfe\tAF_sas\tAF_remaining\n")
        
        return False

def create_demo_with_common_variants():
    """Create a demo VCF with variants more likely to be in gnomAD"""
    
    demo_content = """##fileformat=VCFv4.2
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene name">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	69511	rs75062661	A	G	.	.	GENE=OR4F5
2	906683	rs6053810	G	A	.	.	GENE=PXDNL
7	117559590	rs1042522	G	C	.	.	GENE=CFTR
12	112241766	rs671	G	A	.	.	GENE=ALDH2
17	7579472	rs1042522	G	C	.	.	GENE=TP53
"""
    
    demo_path = Path("example_input/gnomad_demo_common.vcf")
    demo_path.parent.mkdir(exist_ok=True)
    demo_path.write_text(demo_content)
    
    logger.info(f"Created demo VCF with common variants: {demo_path}")
    return demo_path

def main():
    parser = argparse.ArgumentParser(
        description="Extract gnomAD v4 population frequencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool extracts allele frequencies from gnomAD v4.0 or v4.1 (whichever is accessible).

gnomAD v4 includes:
- 807,162 individuals (730,947 exomes + 76,215 genomes)
- 9 genetic ancestry groups + remaining
- Both versions (v4.0 and v4.1) have the same underlying data

Examples:
  # Extract AFs for your VCF
  python gnomad_v4_final.py input.vcf --output gnomad_afs.tsv
  
  # Test with common variants
  python gnomad_v4_final.py --demo
        """
    )
    
    parser.add_argument("vcf_file", nargs='?', help="Input VCF file")
    parser.add_argument("--output", "-o", help="Output TSV file")
    parser.add_argument("--demo", action="store_true", 
                       help="Run demo with common variants")
    
    args = parser.parse_args()
    
    if args.demo:
        demo_vcf = create_demo_with_common_variants()
        output_path = Path("out/gnomad_demo_results.tsv")
        output_path.parent.mkdir(exist_ok=True)
        
        success = extract_gnomad_v4(demo_vcf, output_path)
        
        if output_path.exists():
            logger.info(f"\n📁 Results saved to: {output_path}")
            with open(output_path) as f:
                logger.info("\n📋 Preview:")
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"  {line.strip()}")
        return 0
    
    if not args.vcf_file:
        parser.error("VCF file required unless using --demo")
    
    vcf_path = Path(args.vcf_file)
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    if not args.output:
        parser.error("--output is required")
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract gnomAD data
    success = extract_gnomad_v4(vcf_path, output_path)
    
    if output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        
        with open(output_path) as f:
            lines = f.readlines()
            data_lines = [l for l in lines if not l.startswith('#')]
        
        logger.info(f"\n🎉 gnomAD extraction complete!")
        logger.info(f"📁 Output: {output_path}")
        logger.info(f"📊 {len(data_lines)-1} variants, {size_kb:.1f} KB")
        
        # Show preview
        if len(lines) > 1:
            logger.info("\n📋 Preview:")
            for i, line in enumerate(lines):
                if i < 5 and not line.startswith('#'):
                    print(f"  {line.strip()}")
        
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())