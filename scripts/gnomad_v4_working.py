#!/usr/bin/env python3
"""
gnomAD v4.1 Working Extractor

Uses bcftools to extract AF data from gnomAD v4.1 public cloud files.
This is the actual working solution for the latest gnomAD data.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# gnomAD v4.1 public URLs
GNOMAD_V4_BASE = "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{}.vcf.bgz"

def extract_gnomad_v4_afs(vcf_file, output_file):
    """Extract gnomAD v4.1 AFs using bcftools"""
    
    logger.info("🚀 Extracting gnomAD v4.1 allele frequencies")
    
    # Step 1: Create regions file from input VCF
    regions_by_chr = {}
    
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
                    
                    if chrom not in regions_by_chr:
                        regions_by_chr[chrom] = []
                    
                    regions_by_chr[chrom].append({
                        'pos': pos,
                        'ref': ref,
                        'alt': alt,
                        'region': f"{chrom}:{pos}-{pos}"
                    })
        
        total_variants = sum(len(v) for v in regions_by_chr.values())
        logger.info(f"Found {total_variants} variants across {len(regions_by_chr)} chromosomes")
        
    except Exception as e:
        logger.error(f"Failed to parse VCF: {e}")
        return False
    
    # Step 2: Query each chromosome
    all_results = []
    
    for chrom, variants in regions_by_chr.items():
        logger.info(f"Querying chromosome {chrom} ({len(variants)} variants)...")
        
        # Create regions file for this chromosome
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bed', delete=False) as tmp:
            for var in variants:
                # BED format: chr start end
                tmp.write(f"{chrom}\t{var['pos']-1}\t{var['pos']}\n")
            regions_file = tmp.name
        
        # gnomAD v4.1 URL for this chromosome
        gnomad_url = GNOMAD_V4_BASE.format(chrom)
        
        # Extract with bcftools
        cmd = [
            "bcftools", "query",
            "-R", regions_file,
            "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\t%INFO/AF\\t%INFO/AF_grpmax\\t%INFO/AF_afr\\t%INFO/AF_amr\\t%INFO/AF_asj\\t%INFO/AF_eas\\t%INFO/AF_fin\\t%INFO/AF_nfe\\t%INFO/AF_sas\\t%INFO/AF_mid\\t%INFO/AF_ami\\t%INFO/AF_remaining\\n",
            gnomad_url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                # Parse results and match with our variants
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 5:
                        # Find matching variant
                        line_pos = int(parts[1])
                        line_ref = parts[2]
                        line_alt = parts[3]
                        
                        for var in variants:
                            if var['pos'] == line_pos and var['ref'] == line_ref and var['alt'] == line_alt:
                                all_results.append(line)
                                break
            
            # Clean up
            Path(regions_file).unlink()
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to query chromosome {chrom}: {e}")
            Path(regions_file).unlink(missing_ok=True)
    
    # Step 3: Write results
    if all_results:
        with open(output_file, 'w') as f:
            # Header
            headers = ['CHROM', 'POS', 'REF', 'ALT', 'AF', 'AF_grpmax', 
                      'AF_afr', 'AF_amr', 'AF_asj', 'AF_eas', 'AF_fin', 
                      'AF_nfe', 'AF_sas', 'AF_mid', 'AF_ami', 'AF_remaining']
            f.write('\t'.join(headers) + '\n')
            
            # Data
            for line in all_results:
                f.write(line + '\n')
        
        logger.info(f"✅ Successfully extracted gnomAD v4.1 data for {len(all_results)} variants")
        return True
    else:
        logger.error("No data extracted")
        return False

def create_comprehensive_af_report(gnomad_file, output_file):
    """Create a comprehensive AF report with population analysis"""
    
    logger.info("📊 Creating comprehensive population frequency report")
    
    import csv
    
    # Read gnomAD data
    data = []
    with open(gnomad_file, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            data.append(row)
    
    # Create enhanced report
    with open(output_file, 'w') as f:
        f.write("# gnomAD v4.1 Population Frequency Report\n")
        f.write(f"# Total variants: {len(data)}\n")
        f.write("# Populations: AFR (African), AMR (American), ASJ (Ashkenazi Jewish), ")
        f.write("EAS (East Asian), FIN (Finnish), NFE (Non-Finnish European), ")
        f.write("SAS (South Asian), MID (Middle Eastern), AMI (Amish), Remaining\n\n")
        
        # Detailed table
        headers = ['Variant', 'Global_AF', 'Max_Pop_AF', 'AFR', 'AMR', 'ASJ', 
                  'EAS', 'FIN', 'NFE', 'SAS', 'MID', 'AMI', 'Remaining']
        f.write('\t'.join(headers) + '\n')
        
        for row in data:
            variant = f"{row['CHROM']}:{row['POS']}:{row['REF']}>{row['ALT']}"
            values = [
                variant,
                row.get('AF', '0'),
                row.get('AF_grpmax', '0'),
                row.get('AF_afr', '0'),
                row.get('AF_amr', '0'),
                row.get('AF_asj', '0'),
                row.get('AF_eas', '0'),
                row.get('AF_fin', '0'),
                row.get('AF_nfe', '0'),
                row.get('AF_sas', '0'),
                row.get('AF_mid', '0'),
                row.get('AF_ami', '0'),
                row.get('AF_remaining', '0')
            ]
            f.write('\t'.join(values) + '\n')

def main():
    parser = argparse.ArgumentParser(
        description="Extract gnomAD v4.1 population frequencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This extracts comprehensive population frequency data from gnomAD v4.1:
- 807,162 individuals from 11 populations
- Direct access to public cloud data
- All population and subpopulation frequencies

Examples:
  # Extract gnomAD v4.1 AFs
  python gnomad_v4_working.py input.vcf --output gnomad_v4_afs.tsv
  
  # Create comprehensive report
  python gnomad_v4_working.py input.vcf --output gnomad_v4_afs.tsv --report
        """
    )
    
    parser.add_argument("vcf_file", help="Input VCF file")
    parser.add_argument("--output", "-o", required=True, help="Output TSV file")
    parser.add_argument("--report", action="store_true", 
                       help="Create comprehensive population report")
    
    args = parser.parse_args()
    
    vcf_path = Path(args.vcf_file)
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract gnomAD v4.1 data
    success = extract_gnomad_v4_afs(vcf_path, output_path)
    
    if success and args.report:
        report_path = output_path.with_suffix('.report.tsv')
        create_comprehensive_af_report(output_path, report_path)
        logger.info(f"📄 Comprehensive report: {report_path}")
    
    if success and output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        
        with open(output_path) as f:
            line_count = sum(1 for line in f) - 1
        
        logger.info(f"\n🎉 gnomAD v4.1 extraction complete!")
        logger.info(f"📁 Output: {output_path}")
        logger.info(f"📊 {line_count} variants, {size_kb:.1f} KB")
        
        # Show preview
        logger.info("\n📋 Preview of gnomAD v4.1 data:")
        with open(output_path) as f:
            for i, line in enumerate(f):
                if i < 5:
                    print(f"  {line.strip()}")
                else:
                    break
        
        return 0
    else:
        logger.error("Failed to extract gnomAD v4.1 data")
        return 1

if __name__ == "__main__":
    sys.exit(main())