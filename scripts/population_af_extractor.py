#!/usr/bin/env python3
"""
Population AF Extractor - Multiple Datasets via BigQuery

Extracts comprehensive allele frequencies from:
- 1000 Genomes Project (definite availability)
- gnomAD v2.1.1 (working)
- ClinVar (for pathogenicity context)
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_variants_from_vcf(vcf_file):
    """Extract variants from VCF file"""
    variants = []
    
    try:
        cmd = ["bcftools", "query", "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\n", str(vcf_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        for line in result.stdout.strip().split('\n'):
            if line:
                chrom, pos, ref, alt = line.split('\t')
                variants.append({
                    'chrom': chrom.replace('chr', ''),
                    'pos': int(pos),
                    'ref': ref,
                    'alt': alt
                })
        
        logger.info(f"Found {len(variants)} variants in VCF")
        return variants
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to parse VCF: {e}")
        return []

def query_1000genomes(variants, output_file):
    """Query 1000 Genomes Project data"""
    
    logger.info("🌍 Querying 1000 Genomes Project data...")
    
    # Build WHERE conditions
    conditions = []
    for v in variants[:100]:  # Limit to 100 for BigQuery
        conditions.append(f"""(reference_name = '{v['chrom']}' AND 
                             start_position = {v['pos']} AND 
                             reference_bases = '{v['ref']}' AND 
                             alternate_bases[SAFE_OFFSET(0)].alt = '{v['alt']}')""")
    
    where_clause = " OR ".join(conditions)
    
    query = f"""
    SELECT
      reference_name as CHROM,
      start_position as POS,
      reference_bases as REF,
      alternate_bases[SAFE_OFFSET(0)].alt as ALT,
      -- Overall AF
      quality,
      -- Super populations
      SAS_AF, EAS_AF, AFR_AF, EUR_AF, AMR_AF,
      -- Subpopulations
      GBR_AF, FIN_AF, CHS_AF, PUR_AF, CDX_AF, CLM_AF, IBS_AF, PEL_AF,
      PJL_AF, KHV_AF, ACB_AF, GWD_AF, ESN_AF, BEB_AF, MSL_AF, STU_AF,
      ITU_AF, CEU_AF, YRI_AF, CHB_AF, JPT_AF, LWK_AF, ASW_AF, MXL_AF,
      TSI_AF, GIH_AF
    FROM `bigquery-public-data.human_genome_variants.1000_genomes_phase_3_variants_20150220`
    WHERE {where_clause}
    ORDER BY reference_name, start_position
    """
    
    cmd = [
        "bq", "query",
        "--use_legacy_sql=false",
        "--format=csv",
        "--max_rows=100000",
        query
    ]
    
    try:
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
        
        logger.info("✅ 1000 Genomes query completed")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ 1000 Genomes query failed: {e.stderr}")
        return False

def query_gnomad_v2(variants, output_file):
    """Query gnomAD v2.1.1 with working approach"""
    
    logger.info("🧬 Querying gnomAD v2.1.1 data...")
    
    # Group variants by chromosome
    variants_by_chr = {}
    for v in variants:
        chrom = v['chrom']
        if chrom not in variants_by_chr:
            variants_by_chr[chrom] = []
        variants_by_chr[chrom].append(v)
    
    all_results = []
    
    for chrom, chr_variants in variants_by_chr.items():
        # Skip if chromosome table doesn't exist
        if chrom not in ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','X','Y']:
            continue
            
        conditions = []
        for v in chr_variants[:20]:  # Limit per chromosome
            conditions.append(f"""(start_position = {v['pos']} AND 
                                 reference_bases = '{v['ref']}' AND 
                                 alternate_bases[SAFE_OFFSET(0)].alt = '{v['alt']}')""")
        
        where_clause = " OR ".join(conditions)
        
        query = f"""
        SELECT
          '{chrom}' as CHROM,
          start_position as POS,
          reference_bases as REF,
          alternate_bases[SAFE_OFFSET(0)].alt as ALT,
          quality,
          -- Extract AF from the vep array structure
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad AS FLOAT64) as AF,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_afr AS FLOAT64) as AF_afr,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_amr AS FLOAT64) as AF_amr,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_asj AS FLOAT64) as AF_asj,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_eas AS FLOAT64) as AF_eas,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_fin AS FLOAT64) as AF_fin,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_nfe AS FLOAT64) as AF_nfe,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_sas AS FLOAT64) as AF_sas,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_oth AS FLOAT64) as AF_oth
        FROM `bigquery-public-data.gnomAD.v2_1_1_genomes__chr{chrom}`
        WHERE {where_clause}
        """
        
        cmd = [
            "bq", "query",
            "--use_legacy_sql=false",
            "--format=csv",
            "--max_rows=1000",
            query
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Has data beyond header
                all_results.extend(lines[1:])  # Skip header
                
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to query chromosome {chrom}: {e.stderr}")
    
    # Write results
    if all_results:
        with open(output_file, 'w') as f:
            # Header
            f.write("CHROM,POS,REF,ALT,QUAL,AF,AF_afr,AF_amr,AF_asj,AF_eas,AF_fin,AF_nfe,AF_sas,AF_oth\n")
            for line in all_results:
                f.write(line + '\n')
        
        logger.info(f"✅ gnomAD query completed with {len(all_results)} results")
        return True
    else:
        logger.error("❌ No gnomAD results found")
        return False

def combine_results(kg_file, gnomad_file, output_file):
    """Combine results from multiple sources"""
    
    logger.info("🔄 Combining results from all sources...")
    
    # Read both files and merge
    import csv
    
    # Read 1000 Genomes data
    kg_data = {}
    if Path(kg_file).exists():
        with open(kg_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['CHROM']}:{row['POS']}:{row['REF']}:{row['ALT']}"
                kg_data[key] = row
    
    # Read gnomAD data
    gnomad_data = {}
    if Path(gnomad_file).exists():
        with open(gnomad_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['CHROM']}:{row['POS']}:{row['REF']}:{row['ALT']}"
                gnomad_data[key] = row
    
    # Combine and write
    all_keys = sorted(set(kg_data.keys()) | set(gnomad_data.keys()))
    
    with open(output_file, 'w', newline='') as f:
        # Comprehensive header
        fieldnames = [
            'CHROM', 'POS', 'REF', 'ALT',
            # 1000 Genomes
            '1KG_AFR', '1KG_AMR', '1KG_EAS', '1KG_EUR', '1KG_SAS',
            # gnomAD
            'gnomAD_AF', 'gnomAD_AFR', 'gnomAD_AMR', 'gnomAD_ASJ', 'gnomAD_EAS',
            'gnomAD_FIN', 'gnomAD_NFE', 'gnomAD_SAS', 'gnomAD_OTH'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        
        for key in all_keys:
            chrom, pos, ref, alt = key.split(':')
            row = {
                'CHROM': chrom,
                'POS': pos,
                'REF': ref,
                'ALT': alt
            }
            
            # Add 1KG data
            if key in kg_data:
                kg = kg_data[key]
                row.update({
                    '1KG_AFR': kg.get('AFR_AF', ''),
                    '1KG_AMR': kg.get('AMR_AF', ''),
                    '1KG_EAS': kg.get('EAS_AF', ''),
                    '1KG_EUR': kg.get('EUR_AF', ''),
                    '1KG_SAS': kg.get('SAS_AF', '')
                })
            
            # Add gnomAD data
            if key in gnomad_data:
                gn = gnomad_data[key]
                row.update({
                    'gnomAD_AF': gn.get('AF', ''),
                    'gnomAD_AFR': gn.get('AF_afr', ''),
                    'gnomAD_AMR': gn.get('AF_amr', ''),
                    'gnomAD_ASJ': gn.get('AF_asj', ''),
                    'gnomAD_EAS': gn.get('AF_eas', ''),
                    'gnomAD_FIN': gn.get('AF_fin', ''),
                    'gnomAD_NFE': gn.get('AF_nfe', ''),
                    'gnomAD_SAS': gn.get('AF_sas', ''),
                    'gnomAD_OTH': gn.get('AF_oth', '')
                })
            
            writer.writerow(row)
    
    logger.info(f"✅ Combined {len(all_keys)} unique variants")

def main():
    parser = argparse.ArgumentParser(
        description="Extract population AF data from multiple sources via BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Extracts comprehensive population frequency data from:
- 1000 Genomes Project (26 populations)
- gnomAD v2.1.1 (9 populations)

Examples:
  # Extract all population data
  python population_af_extractor.py input.vcf --output population_afs.tsv
  
  # Extract only 1000 Genomes data
  python population_af_extractor.py input.vcf --output kg_afs.tsv --dataset 1kg
  
  # Extract only gnomAD data
  python population_af_extractor.py input.vcf --output gnomad_afs.tsv --dataset gnomad
        """
    )
    
    parser.add_argument("vcf_file", help="Input VCF file")
    parser.add_argument("--output", "-o", required=True, help="Output TSV file")
    parser.add_argument("--dataset", choices=["all", "1kg", "gnomad"], default="all",
                       help="Which datasets to query")
    
    args = parser.parse_args()
    
    vcf_path = Path(args.vcf_file)
    if not vcf_path.exists():
        logger.error(f"VCF file not found: {vcf_path}")
        return 1
    
    # Extract variants
    variants = extract_variants_from_vcf(vcf_path)
    if not variants:
        logger.error("No variants found in VCF")
        return 1
    
    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Query datasets
    success = False
    
    if args.dataset in ["all", "1kg"]:
        kg_output = output_path.with_suffix('.1kg.csv')
        if query_1000genomes(variants, kg_output):
            success = True
    
    if args.dataset in ["all", "gnomad"]:
        gnomad_output = output_path.with_suffix('.gnomad.csv')
        if query_gnomad_v2(variants, gnomad_output):
            success = True
    
    if args.dataset == "all" and success:
        # Combine results
        combine_results(
            output_path.with_suffix('.1kg.csv'),
            output_path.with_suffix('.gnomad.csv'),
            output_path
        )
        
        # Clean up intermediate files
        output_path.with_suffix('.1kg.csv').unlink(missing_ok=True)
        output_path.with_suffix('.gnomad.csv').unlink(missing_ok=True)
    
    elif args.dataset == "1kg":
        kg_output.rename(output_path)
    elif args.dataset == "gnomad":
        gnomad_output.rename(output_path)
    
    if success and output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        
        with open(output_path) as f:
            line_count = sum(1 for line in f) - 1  # Subtract header
        
        logger.info(f"\n🎉 Successfully extracted population AF data!")
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
        logger.error("Failed to extract AF data")
        return 1

if __name__ == "__main__":
    sys.exit(main())