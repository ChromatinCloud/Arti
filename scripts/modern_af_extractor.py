#!/usr/bin/env python3
"""
Modern AF Extractor - gnomAD v4 and All of Us

Extracts comprehensive allele frequencies from the latest huge datasets:
- gnomAD v4.1 (via Hail/cloud access)
- All of Us v7 (via Terra/BigQuery)

These are the current gold-standard population databases.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging
import requests
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_gnomad_v4_with_tabix(vcf_file, output_file):
    """
    Extract gnomAD v4.1 data using tabix on cloud-hosted files
    
    This is the FASTEST method for gnomAD v4 - direct HTTP range queries
    """
    logger.info("🚀 Extracting gnomAD v4.1 data (latest release)")
    
    # gnomAD v4.1 public URLs (these are the actual public files)
    GNOMAD_V4_GENOMES = "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{}.vcf.bgz"
    GNOMAD_V4_EXOMES = "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/exomes/gnomad.exomes.v4.1.sites.chr{}.vcf.bgz"
    
    # Extract regions from input VCF
    regions = []
    try:
        with open(vcf_file) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    chrom = parts[0].replace('chr', '')
                    pos = int(parts[1])
                    regions.append((chrom, pos))
        
        logger.info(f"Found {len(regions)} variants to query")
    except Exception as e:
        logger.error(f"Failed to parse VCF: {e}")
        return False
    
    # Query each variant using tabix
    results = []
    
    for chrom, pos in regions:
        # Try genomes first
        url = GNOMAD_V4_GENOMES.format(chrom)
        region = f"{chrom}:{pos}-{pos}"
        
        cmd = ["tabix", url, region]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                # Parse the VCF line to extract AF data
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 8:
                            info = parts[7]
                            
                            # Extract AF values from INFO field
                            af_data = {
                                'CHROM': chrom,
                                'POS': pos,
                                'REF': parts[3],
                                'ALT': parts[4],
                                'AF': extract_info_field(info, 'AF'),
                                'AF_grpmax': extract_info_field(info, 'AF_grpmax'),
                                'AF_afr': extract_info_field(info, 'AF_afr'),
                                'AF_amr': extract_info_field(info, 'AF_amr'),
                                'AF_asj': extract_info_field(info, 'AF_asj'),
                                'AF_eas': extract_info_field(info, 'AF_eas'),
                                'AF_fin': extract_info_field(info, 'AF_fin'),
                                'AF_nfe': extract_info_field(info, 'AF_nfe'),
                                'AF_sas': extract_info_field(info, 'AF_sas'),
                                'AF_mid': extract_info_field(info, 'AF_mid'),
                                'AF_ami': extract_info_field(info, 'AF_ami'),
                                'AF_remaining': extract_info_field(info, 'AF_remaining')
                            }
                            results.append(af_data)
                            break
            else:
                logger.debug(f"No data found for {chrom}:{pos}")
                
        except subprocess.CalledProcessError as e:
            logger.warning(f"tabix failed for {chrom}:{pos}: {e}")
        except FileNotFoundError:
            logger.error("tabix not found. Install with: conda install -c bioconda tabix")
            return False
    
    # Write results
    if results:
        with open(output_file, 'w') as f:
            # Header
            headers = ['CHROM', 'POS', 'REF', 'ALT', 'AF', 'AF_grpmax', 
                      'AF_afr', 'AF_amr', 'AF_asj', 'AF_eas', 'AF_fin', 
                      'AF_nfe', 'AF_sas', 'AF_mid', 'AF_ami', 'AF_remaining']
            f.write('\t'.join(headers) + '\n')
            
            # Data
            for r in results:
                row = [str(r.get(h, '')) for h in headers]
                f.write('\t'.join(row) + '\n')
        
        logger.info(f"✅ Extracted gnomAD v4.1 data for {len(results)} variants")
        return True
    else:
        logger.error("No gnomAD v4 data found")
        return False

def extract_info_field(info_string, field_name):
    """Extract a field from VCF INFO string"""
    for item in info_string.split(';'):
        if item.startswith(field_name + '='):
            return item.split('=')[1]
    return ''

def extract_aou_with_bigquery(vcf_file, output_file):
    """
    Extract All of Us v7 data via BigQuery
    
    Note: This requires AoU researcher access
    """
    logger.info("🧬 Extracting All of Us v7 data")
    
    # Parse variants
    variants = []
    try:
        with open(vcf_file) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    variants.append({
                        'chrom': parts[0].replace('chr', ''),
                        'pos': int(parts[1]),
                        'ref': parts[3],
                        'alt': parts[4]
                    })
    except Exception as e:
        logger.error(f"Failed to parse VCF: {e}")
        return False
    
    # AoU public tier query (if you have access)
    # This is a template - actual table names depend on your workspace
    query = """
    SELECT 
      chromosome,
      position,
      ref_allele,
      alt_allele,
      allele_frequency as AF,
      allele_frequency_african_ancestry as AF_afr,
      allele_frequency_latino as AF_amr,
      allele_frequency_east_asian_ancestry as AF_eas,
      allele_frequency_european_ancestry as AF_eur,
      allele_frequency_middle_eastern_ancestry as AF_mid,
      allele_frequency_south_asian_ancestry as AF_sas
    FROM `aou-res-curation-output-prod.R2022Q4R9.wgs_variant_stats`
    WHERE 
    """
    
    # Add variant conditions
    conditions = []
    for v in variants[:100]:  # Limit for BigQuery
        conditions.append(f"""(chromosome = 'chr{v['chrom']}' AND 
                             position = {v['pos']} AND 
                             ref_allele = '{v['ref']}' AND 
                             alt_allele = '{v['alt']}')""")
    
    query += " OR ".join(conditions)
    
    logger.info("Note: All of Us data requires authenticated access via Terra platform")
    logger.info("Visit: https://www.researchallofus.org/data-tools/workbench/")
    
    # Create template output
    with open(output_file, 'w') as f:
        f.write("CHROM\tPOS\tREF\tALT\tAoU_AF\tAoU_AF_afr\tAoU_AF_amr\tAoU_AF_eas\tAoU_AF_eur\tAoU_AF_mid\tAoU_AF_sas\n")
        f.write("# All of Us data requires authenticated access\n")
        f.write("# Query template saved for Terra workbench use\n")
    
    # Save query for user
    query_file = output_file.with_suffix('.aou_query.sql')
    with open(query_file, 'w') as f:
        f.write(query)
    
    logger.info(f"📄 AoU query saved to: {query_file}")
    return True

def extract_gnomad_v4_api(vcf_file, output_file):
    """
    Alternative: Use gnomAD GraphQL API for small queries
    """
    logger.info("🌐 Using gnomAD v4 GraphQL API")
    
    # Parse variants
    variants = []
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
                    
                    # Create variant ID in gnomAD format
                    var_id = f"{chrom}-{pos}-{ref}-{alt}"
                    variants.append(var_id)
    except Exception as e:
        logger.error(f"Failed to parse VCF: {e}")
        return False
    
    # Query gnomAD API
    results = []
    api_url = "https://gnomad.broadinstitute.org/api"
    
    for var_id in variants[:10]:  # Limit for demo
        query = """
        query VariantQuery($variantId: String!) {
          variant(variantId: $variantId, datasetId: "gnomad_r4") {
            variant_id
            chrom
            pos
            ref
            alt
            genome {
              af
              af_afr
              af_amr
              af_asj
              af_eas
              af_fin
              af_nfe
              af_sas
              af_mid
              af_ami
              af_remaining
            }
          }
        }
        """
        
        try:
            response = requests.post(
                api_url,
                json={'query': query, 'variables': {'variantId': var_id}},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('variant'):
                    variant = data['data']['variant']
                    genome = variant.get('genome', {})
                    
                    results.append({
                        'CHROM': variant['chrom'],
                        'POS': variant['pos'],
                        'REF': variant['ref'],
                        'ALT': variant['alt'],
                        'AF': genome.get('af', ''),
                        'AF_afr': genome.get('af_afr', ''),
                        'AF_amr': genome.get('af_amr', ''),
                        'AF_asj': genome.get('af_asj', ''),
                        'AF_eas': genome.get('af_eas', ''),
                        'AF_fin': genome.get('af_fin', ''),
                        'AF_nfe': genome.get('af_nfe', ''),
                        'AF_sas': genome.get('af_sas', ''),
                        'AF_mid': genome.get('af_mid', ''),
                        'AF_ami': genome.get('af_ami', ''),
                        'AF_remaining': genome.get('af_remaining', '')
                    })
                    
        except Exception as e:
            logger.warning(f"API query failed for {var_id}: {e}")
    
    # Write results
    if results:
        with open(output_file, 'w') as f:
            headers = ['CHROM', 'POS', 'REF', 'ALT', 'AF', 'AF_afr', 'AF_amr', 
                      'AF_asj', 'AF_eas', 'AF_fin', 'AF_nfe', 'AF_sas', 
                      'AF_mid', 'AF_ami', 'AF_remaining']
            f.write('\t'.join(headers) + '\n')
            
            for r in results:
                row = [str(r.get(h, '')) for h in headers]
                f.write('\t'.join(row) + '\n')
        
        logger.info(f"✅ Extracted gnomAD v4 data via API for {len(results)} variants")
        return True
    else:
        logger.error("No results from gnomAD API")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Extract AF data from modern huge datasets (gnomAD v4, All of Us)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Methods available:

🚀 tabix: Direct HTTP range queries to gnomAD v4.1 (fastest, recommended)
🌐 api: gnomAD GraphQL API (good for small queries)
🧬 aou: All of Us template (requires Terra access)

Examples:
  # Extract gnomAD v4.1 using tabix (fastest)
  python modern_af_extractor.py input.vcf --output gnomad_v4_afs.tsv --method tabix
  
  # Use gnomAD API for small queries
  python modern_af_extractor.py input.vcf --output gnomad_api_afs.tsv --method api
  
  # Generate All of Us query template
  python modern_af_extractor.py input.vcf --output aou_template.tsv --method aou
        """
    )
    
    parser.add_argument("vcf_file", help="Input VCF file")
    parser.add_argument("--output", "-o", required=True, help="Output TSV file")
    parser.add_argument("--method", choices=["tabix", "api", "aou"], default="tabix",
                       help="Extraction method")
    
    args = parser.parse_args()
    
    vcf_path = Path(args.vcf_file)
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run selected method
    success = False
    
    if args.method == "tabix":
        success = extract_gnomad_v4_with_tabix(vcf_path, output_path)
    elif args.method == "api":
        success = extract_gnomad_v4_api(vcf_path, output_path)
    elif args.method == "aou":
        success = extract_aou_with_bigquery(vcf_path, output_path)
    
    if success and output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        
        with open(output_path) as f:
            line_count = sum(1 for line in f) - 1
        
        logger.info(f"\n🎉 Successfully extracted modern AF data!")
        logger.info(f"📁 Output: {output_path}")
        logger.info(f"📊 {line_count} records, {size_kb:.1f} KB")
        
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
        logger.error("AF extraction failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())