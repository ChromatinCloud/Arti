#!/usr/bin/env python3
"""
gnomAD BigQuery Extractor - WORKING VERSION

Extracts comprehensive allele frequencies from gnomAD using BigQuery.
Handles per-chromosome tables and provides all population frequencies.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_variants_from_vcf(vcf_file):
    """Extract chromosome, position, ref, alt from VCF"""
    variants_by_chr = {}
    
    try:
        cmd = ["bcftools", "query", "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\n", str(vcf_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        for line in result.stdout.strip().split('\n'):
            if line:
                chrom, pos, ref, alt = line.split('\t')
                # Normalize chromosome name
                chrom = chrom.replace('chr', '')
                
                if chrom not in variants_by_chr:
                    variants_by_chr[chrom] = []
                
                variants_by_chr[chrom].append({
                    'pos': int(pos),
                    'ref': ref,
                    'alt': alt
                })
        
        total_variants = sum(len(v) for v in variants_by_chr.values())
        logger.info(f"Found {total_variants} variants across {len(variants_by_chr)} chromosomes")
        
        return variants_by_chr
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to parse VCF: {e}")
        return {}

def create_gnomad_query(chromosome, variants, dataset="v2_1_1_genomes"):
    """Create BigQuery SQL for specific variants on a chromosome"""
    
    # Build WHERE clause for specific positions
    position_conditions = []
    for var in variants:
        position_conditions.append(f"(start_position = {var['pos']} AND reference_bases = '{var['ref']}' AND alternate_bases[OFFSET(0)].alt = '{var['alt']}')")
    
    where_clause = " OR ".join(position_conditions)
    
    # gnomAD v2.1.1 schema
    query = f"""
    SELECT
      '{chromosome}' as CHROM,
      start_position as POS,
      reference_bases as REF,
      alternate_bases[OFFSET(0)].alt as ALT,
      -- Global AF
      vep[OFFSET(0)].allele_freq.gnomad as AF,
      -- Population-specific AFs
      vep[OFFSET(0)].allele_freq.gnomad_afr as AF_afr,
      vep[OFFSET(0)].allele_freq.gnomad_amr as AF_amr,
      vep[OFFSET(0)].allele_freq.gnomad_asj as AF_asj,
      vep[OFFSET(0)].allele_freq.gnomad_eas as AF_eas,
      vep[OFFSET(0)].allele_freq.gnomad_fin as AF_fin,
      vep[OFFSET(0)].allele_freq.gnomad_nfe as AF_nfe,
      vep[OFFSET(0)].allele_freq.gnomad_sas as AF_sas,
      vep[OFFSET(0)].allele_freq.gnomad_oth as AF_oth
    FROM `bigquery-public-data.gnomAD.{dataset}__chr{chromosome}`
    WHERE ({where_clause})
    """
    
    return query

def create_gnomad_v3_query(chromosome, variants):
    """Create BigQuery SQL for gnomAD v3 (genomes only)"""
    
    position_conditions = []
    for var in variants:
        position_conditions.append(f"(start_position = {var['pos']} AND reference_bases = '{var['ref']}' AND alternate_bases[OFFSET(0)].alt = '{var['alt']}')")
    
    where_clause = " OR ".join(position_conditions)
    
    query = f"""
    SELECT
      '{chromosome}' as CHROM,
      start_position as POS,
      reference_bases as REF,
      alternate_bases[OFFSET(0)].alt as ALT,
      -- Global AF
      vep[OFFSET(0)].allele_freq.gnomad_v3 as AF,
      -- Population-specific AFs (v3 schema)
      vep[OFFSET(0)].allele_freq.gnomad_v3_afr as AF_afr,
      vep[OFFSET(0)].allele_freq.gnomad_v3_amr as AF_amr,
      vep[OFFSET(0)].allele_freq.gnomad_v3_asj as AF_asj,
      vep[OFFSET(0)].allele_freq.gnomad_v3_eas as AF_eas,
      vep[OFFSET(0)].allele_freq.gnomad_v3_fin as AF_fin,
      vep[OFFSET(0)].allele_freq.gnomad_v3_nfe as AF_nfe,
      vep[OFFSET(0)].allele_freq.gnomad_v3_sas as AF_sas,
      vep[OFFSET(0)].allele_freq.gnomad_v3_mid as AF_mid
    FROM `bigquery-public-data.gnomAD.v3_genomes__chr{chromosome}`
    WHERE ({where_clause})
    """
    
    return query

def run_bigquery_for_chromosome(chromosome, variants, output_file, dataset="v2_1_1_genomes", append=False):
    """Run BigQuery for a single chromosome"""
    
    if dataset == "v3_genomes":
        query = create_gnomad_v3_query(chromosome, variants)
    else:
        query = create_gnomad_query(chromosome, variants, dataset)
    
    logger.info(f"Querying {len(variants)} variants on chromosome {chromosome}")
    
    cmd = [
        "bq", "query",
        "--use_legacy_sql=false",
        "--format=csv",
        "--max_rows=100000",
        query
    ]
    
    try:
        mode = 'a' if append else 'w'
        with open(output_file, mode) as f:
            # Write header only for first chromosome
            if not append:
                if dataset == "v3_genomes":
                    header = "CHROM,POS,REF,ALT,AF,AF_afr,AF_amr,AF_asj,AF_eas,AF_fin,AF_nfe,AF_sas,AF_mid\n"
                else:
                    header = "CHROM,POS,REF,ALT,AF,AF_afr,AF_amr,AF_asj,AF_eas,AF_fin,AF_nfe,AF_sas,AF_oth\n"
                f.write(header)
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            
            # Process output to remove header and empty lines
            lines = result.stdout.strip().split('\n')
            if lines and lines[0].startswith('CHROM'):
                lines = lines[1:]  # Skip header from BigQuery
            
            for line in lines:
                if line.strip():
                    f.write(line + '\n')
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"BigQuery failed for chromosome {chromosome}: {e.stderr}")
        return False

def convert_csv_to_tsv(csv_file, tsv_file):
    """Convert CSV output to TSV format"""
    import csv
    
    with open(csv_file, 'r') as infile, open(tsv_file, 'w') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile, delimiter='\t')
        
        for row in reader:
            writer.writerow(row)
    
    logger.info(f"Converted to TSV format: {tsv_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Extract gnomAD AF data using BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract gnomAD v2.1.1 genomes data
  python gnomad_bigquery_extractor.py input.vcf --output gnomad_afs.tsv
  
  # Extract gnomAD v2.1.1 exomes data
  python gnomad_bigquery_extractor.py input.vcf --output gnomad_exomes.tsv --dataset v2_1_1_exomes
  
  # Extract gnomAD v3 genomes data  
  python gnomad_bigquery_extractor.py input.vcf --output gnomad_v3.tsv --dataset v3_genomes
  
  # Convert to TSV format
  python gnomad_bigquery_extractor.py input.vcf --output gnomad_afs.tsv --tsv
        """
    )
    
    parser.add_argument("vcf_file", help="Input VCF file")
    parser.add_argument("--output", "-o", required=True, help="Output file")
    parser.add_argument("--dataset", choices=["v2_1_1_genomes", "v2_1_1_exomes", "v3_genomes"], 
                       default="v2_1_1_genomes", help="gnomAD dataset to query")
    parser.add_argument("--tsv", action="store_true", help="Convert output to TSV format")
    
    args = parser.parse_args()
    
    vcf_path = Path(args.vcf_file)
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    # Extract variants by chromosome
    variants_by_chr = extract_variants_from_vcf(vcf_path)
    if not variants_by_chr:
        logger.error("No variants found in VCF")
        return 1
    
    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use CSV for initial output
    csv_output = output_path.with_suffix('.csv')
    
    # Query each chromosome
    success_count = 0
    for i, (chrom, variants) in enumerate(variants_by_chr.items()):
        append = i > 0  # Append after first chromosome
        
        if run_bigquery_for_chromosome(chrom, variants, csv_output, args.dataset, append):
            success_count += 1
        else:
            logger.warning(f"Failed to query chromosome {chrom}")
    
    if success_count == 0:
        logger.error("All queries failed")
        return 1
    
    # Convert to TSV if requested
    if args.tsv:
        convert_csv_to_tsv(csv_output, output_path)
        csv_output.unlink()  # Remove CSV file
    else:
        # Rename CSV to final output
        csv_output.rename(output_path)
    
    # Show summary
    if output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        
        with open(output_path) as f:
            line_count = sum(1 for line in f) - 1  # Subtract header
        
        logger.info(f"\n🎉 Successfully extracted gnomAD AF data!")
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

if __name__ == "__main__":
    sys.exit(main())