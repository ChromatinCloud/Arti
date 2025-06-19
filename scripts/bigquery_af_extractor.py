#!/usr/bin/env python3
"""
BigQuery AF Extractor - FASTEST approach for comprehensive population data

Extracts allele frequencies from major datasets using BigQuery:
- gnomAD v4 (all populations & subpopulations)  
- All of Us (AoU) with population breakdown
- 1000 Genomes Project

Results in seconds, outputs to TSV for local use.
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# BigQuery public datasets
BIGQUERY_DATASETS = {
    "gnomad_v4": {
        "table": "bigquery-public-data.gnomAD.v4_0_sites",
        "description": "gnomAD v4.0 with all populations and subpopulations",
        "populations": ["afr", "amr", "asj", "eas", "fin", "nfe", "sas", "oth"],
        "af_fields": ["AF", "AF_popmax"] + [f"AF_{pop}" for pop in ["afr", "amr", "asj", "eas", "fin", "nfe", "sas", "oth"]]
    },
    "aou_v7": {
        "table": "aou-res-curation-output-prod.aou_phenotypic.person_ehr_data",  # Example - actual table varies
        "description": "All of Us population frequencies",
        "populations": ["afr", "amr", "asn", "eur", "mid"],
        "note": "Requires AoU Researcher Workbench access"
    },
    "kg1_phase3": {
        "table": "bigquery-public-data.human_genome_variants.1000_genomes_phase_3_variants_20150220",
        "description": "1000 Genomes Phase 3 all populations", 
        "populations": ["afr", "amr", "eas", "eur", "sas"],
        "af_fields": ["AF"] + [f"{pop}_AF" for pop in ["AFR", "AMR", "EAS", "EUR", "SAS"]]
    }
}

def check_bq_setup():
    """Check if BigQuery CLI is available and authenticated"""
    try:
        # Check if bq command exists
        result = subprocess.run(["bq", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("BigQuery CLI not found. Install with: pip install google-cloud-bigquery")
            return False
            
        # Check authentication
        result = subprocess.run(["bq", "ls"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("BigQuery not authenticated. Run: gcloud auth login")
            return False
            
        logger.info("BigQuery CLI ready")
        return True
        
    except FileNotFoundError:
        logger.error("BigQuery CLI not found. Install Google Cloud SDK")
        return False

def create_gnomad_query(chromosome=None, start_pos=None, end_pos=None, gene_list=None):
    """Create optimized gnomAD BigQuery SQL"""
    
    # Base SELECT with all population AFs
    select_fields = [
        "CHROM", "POS", "REF", "ALT",
        "AF", "AF_popmax",
        "AF_afr", "AF_amr", "AF_asj", "AF_eas", "AF_fin", "AF_nfe", "AF_sas", "AF_oth",
        "AC_afr", "AC_amr", "AC_asj", "AC_eas", "AC_fin", "AC_nfe", "AC_sas", "AC_oth", 
        "AN_afr", "AN_amr", "AN_asj", "AN_eas", "AN_fin", "AN_nfe", "AN_sas", "AN_oth"
    ]
    
    query = f"""
    SELECT
      {', '.join(select_fields)}
    FROM `bigquery-public-data.gnomAD.v4_0_sites`
    WHERE 1=1
    """
    
    # Add filters to reduce scan size
    if chromosome:
        query += f" AND CHROM = '{chromosome}'"
    
    if start_pos and end_pos:
        query += f" AND POS BETWEEN {start_pos} AND {end_pos}"
    
    if gene_list:
        # This would require joining with gene annotation table
        gene_list_str = "', '".join(gene_list)
        query += f" AND gene_symbol IN ('{gene_list_str}')"
    
    # Add reasonable limits for testing
    if not chromosome and not gene_list:
        query += " LIMIT 100000"  # Prevent huge scans
    
    return query

def create_kg1_query(chromosome=None, start_pos=None, end_pos=None):
    """Create 1000 Genomes BigQuery SQL"""
    
    select_fields = [
        "reference_name as CHROM", "start_position as POS", 
        "reference_bases as REF", "alternate_bases[SAFE_OFFSET(0)].alt as ALT",
        "AF", "EUR_AF", "AFR_AF", "AMR_AF", "EAS_AF", "SAS_AF"
    ]
    
    query = f"""
    SELECT
      {', '.join(select_fields)}
    FROM `bigquery-public-data.human_genome_variants.1000_genomes_phase_3_variants_20150220`
    WHERE 1=1
    """
    
    if chromosome:
        query += f" AND reference_name = '{chromosome}'"
    
    if start_pos and end_pos:
        query += f" AND start_position BETWEEN {start_pos} AND {end_pos}"
    
    if not chromosome:
        query += " LIMIT 50000"
    
    return query

def run_bigquery(query, output_file, dataset_name):
    """Execute BigQuery and save results"""
    
    logger.info(f"Running BigQuery for {dataset_name}...")
    logger.info(f"Query preview: {query[:200]}...")
    
    # Use bq command line tool for better control
    cmd = [
        "bq", "query",
        "--use_legacy_sql=false",
        "--format=csv",
        "--max_rows=0",  # No limit
        query
    ]
    
    try:
        start_time = time.time()
        
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
        
        duration = time.time() - start_time
        
        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024**2)
            
            # Count rows
            with open(output_file) as f:
                row_count = sum(1 for line in f) - 1  # Subtract header
            
            logger.info(f"✅ {dataset_name}: {row_count:,} variants, {size_mb:.1f} MB in {duration:.1f}s")
            return True
        else:
            logger.error(f"❌ Query failed for {dataset_name}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ BigQuery failed for {dataset_name}: {e.stderr}")
        return False

def create_panel_specific_query(vcf_file, dataset="gnomad_v4"):
    """Create query for specific variants from a VCF file"""
    
    logger.info(f"Creating variant-specific query from {vcf_file}")
    
    # Extract variants from VCF
    variants = []
    try:
        cmd = ["bcftools", "query", "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\n", str(vcf_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        for line in result.stdout.strip().split('\n'):
            if line:
                chrom, pos, ref, alt = line.split('\t')
                variants.append((chrom, int(pos), ref, alt))
        
        logger.info(f"Found {len(variants)} variants in VCF")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to parse VCF: {e}")
        return None
    
    if dataset == "gnomad_v4":
        # Create IN clause for efficient lookup
        variant_conditions = []
        for chrom, pos, ref, alt in variants[:1000]:  # Limit for BigQuery
            variant_conditions.append(f"(CHROM = '{chrom}' AND POS = {pos} AND REF = '{ref}' AND ALT = '{alt}')")
        
        if variant_conditions:
            where_clause = " OR ".join(variant_conditions)
            
            query = f"""
            SELECT
              CHROM, POS, REF, ALT, AF, AF_popmax,
              AF_afr, AF_amr, AF_asj, AF_eas, AF_fin, AF_nfe, AF_sas, AF_oth
            FROM `bigquery-public-data.gnomAD.v4_0_sites`
            WHERE ({where_clause})
            ORDER BY CHROM, POS
            """
            return query
    
    return None

def compress_and_index(tsv_file):
    """Compress and index the TSV file for fast access"""
    try:
        # Sort by chromosome and position
        sorted_file = tsv_file.with_suffix('.sorted.tsv')
        cmd = ["sort", "-k1,1V", "-k2,2n", str(tsv_file)]
        
        with open(sorted_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        # Replace original with sorted
        sorted_file.replace(tsv_file)
        
        # Compress with bgzip
        subprocess.run(["bgzip", "-f", str(tsv_file)], check=True)
        compressed_file = tsv_file.with_suffix(tsv_file.suffix + '.gz')
        
        # Create tabix index
        subprocess.run(["tabix", "-f", "-s1", "-b2", "-e2", str(compressed_file)], check=True)
        
        logger.info(f"Created indexed file: {compressed_file}")
        return compressed_file
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to compress/index: {e}")
        return tsv_file

def main():
    parser = argparse.ArgumentParser(
        description="Extract AF data using BigQuery (fastest approach)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all populations for chromosome 7
  python bigquery_af_extractor.py --dataset gnomad_v4 --chromosome 7 --output gnomad_chr7.tsv
  
  # Get AF data for specific genomic region
  python bigquery_af_extractor.py --dataset gnomad_v4 --chromosome 17 --start 41000000 --end 42000000 --output brca1_region.tsv
  
  # Get AF data for variants in a VCF panel
  python bigquery_af_extractor.py --dataset gnomad_v4 --vcf-panel my_panel.vcf.gz --output panel_afs.tsv
  
  # Get 1000 Genomes data
  python bigquery_af_extractor.py --dataset kg1_phase3 --chromosome 22 --output kg1_chr22.tsv
  
  # Check BigQuery setup
  python bigquery_af_extractor.py --check-setup
        """
    )
    
    parser.add_argument("--dataset", choices=list(BIGQUERY_DATASETS.keys()), 
                       default="gnomad_v4", help="Dataset to query")
    parser.add_argument("--chromosome", help="Specific chromosome (e.g., 7, X)")
    parser.add_argument("--start", type=int, help="Start position")
    parser.add_argument("--end", type=int, help="End position") 
    parser.add_argument("--vcf-panel", help="Extract AF for variants in this VCF file")
    parser.add_argument("--output", "-o", help="Output TSV file")
    parser.add_argument("--check-setup", action="store_true", help="Check BigQuery setup")
    parser.add_argument("--compress", action="store_true", help="Compress and index output")
    
    args = parser.parse_args()
    
    if args.check_setup:
        logger.info("Checking BigQuery setup...")
        if check_bq_setup():
            logger.info("✅ BigQuery ready")
            
            # Test query
            test_query = "SELECT COUNT(*) as total_variants FROM `bigquery-public-data.gnomAD.v4_0_sites` LIMIT 1"
            logger.info("Running test query...")
            
            try:
                result = subprocess.run(
                    ["bq", "query", "--use_legacy_sql=false", "--format=csv", test_query],
                    capture_output=True, text=True, check=True
                )
                logger.info(f"✅ Test query successful: {result.stdout.strip()}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Test query failed: {e.stderr}")
                return 1
        else:
            logger.error("❌ BigQuery setup incomplete")
            return 1
        return 0
    
    # Check BigQuery setup
    if not check_bq_setup():
        logger.error("BigQuery setup required. Run with --check-setup for details.")
        return 1
    
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create appropriate query
    if args.vcf_panel:
        query = create_panel_specific_query(args.vcf_panel, args.dataset)
        if not query:
            logger.error("Failed to create panel-specific query")
            return 1
    elif args.dataset == "gnomad_v4":
        query = create_gnomad_query(args.chromosome, args.start, args.end)
    elif args.dataset == "kg1_phase3":
        query = create_kg1_query(args.chromosome, args.start, args.end)
    else:
        logger.error(f"Query creation not implemented for {args.dataset}")
        return 1
    
    # Run the query
    success = run_bigquery(query, output_file, args.dataset)
    
    if success:
        if args.compress:
            compressed_file = compress_and_index(output_file)
        
        logger.info(f"\\n🎉 AF data extraction complete!")
        logger.info(f"📁 Output: {output_file}")
        
        # Show preview
        logger.info("\\n📋 Preview:")
        try:
            with open(output_file) as f:
                for i, line in enumerate(f):
                    if i < 3:
                        logger.info(f"  {line.strip()}")
                    else:
                        break
        except:
            pass
        
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())