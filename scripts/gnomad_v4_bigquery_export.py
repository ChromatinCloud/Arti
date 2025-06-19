#!/usr/bin/env python3
"""
Export ALL gnomAD AFs using BigQuery (if/when v4 becomes available)

Currently only v2.1.1 is in BigQuery, but this script is ready for v4.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_gnomad_v2_all_afs(output_bucket, output_prefix):
    """Export all gnomAD v2.1.1 AFs to GCS bucket"""
    
    logger.info("Exporting ALL gnomAD v2.1.1 AFs via BigQuery...")
    
    # Build query for all chromosomes
    chromosomes = ['1','2','3','4','5','6','7','8','9','10','11','12',
                   '13','14','15','16','17','18','19','20','21','22','X','Y']
    
    query_parts = []
    
    for chrom in chromosomes:
        query_parts.append(f"""
        SELECT
          '{chrom}' as CHROM,
          start_position as POS,
          reference_bases as REF,
          alternate_bases[SAFE_OFFSET(0)].alt as ALT,
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
        WHERE vep[SAFE_OFFSET(0)].allele_freq.gnomad IS NOT NULL
        """)
    
    full_query = " UNION ALL ".join(query_parts)
    full_query = f"""
    CREATE OR REPLACE TABLE `{output_prefix}_gnomad_v2_all_afs` AS
    {full_query}
    ORDER BY CHROM, POS
    """
    
    # Export to table first
    logger.info("Creating BigQuery table with all AFs...")
    
    cmd = [
        "bq", "query",
        "--use_legacy_sql=false",
        "--max_rows=0",
        full_query
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info("✓ BigQuery table created")
        
        # Now export to GCS
        logger.info("Exporting to Google Cloud Storage...")
        
        export_cmd = [
            "bq", "extract",
            "--destination_format=CSV",
            "--compression=GZIP",
            f"{output_prefix}_gnomad_v2_all_afs",
            f"{output_bucket}/gnomad_v2_all_afs_*.csv.gz"
        ]
        
        subprocess.run(export_cmd, check=True)
        logger.info(f"✓ Exported to {output_bucket}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Export failed: {e}")
        return False

def create_common_variants_query(min_af=0.001):
    """Query for common variants only"""
    
    chromosomes = ['1','2','3','4','5','6','7','8','9','10','11','12',
                   '13','14','15','16','17','18','19','20','21','22','X','Y']
    
    query_parts = []
    
    for chrom in chromosomes:
        query_parts.append(f"""
        SELECT
          '{chrom}' as CHROM,
          start_position as POS,
          reference_bases as REF,
          alternate_bases[SAFE_OFFSET(0)].alt as ALT,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad AS FLOAT64) as AF,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_afr AS FLOAT64) as AF_afr,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_amr AS FLOAT64) as AF_amr,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_asj AS FLOAT64) as AF_asj,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_eas AS FLOAT64) as AF_eas,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_fin AS FLOAT64) as AF_fin,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_nfe AS FLOAT64) as AF_nfe,
          CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad_sas AS FLOAT64) as AF_sas
        FROM `bigquery-public-data.gnomAD.v2_1_1_genomes__chr{chrom}`
        WHERE CAST(vep[SAFE_OFFSET(0)].allele_freq.gnomad AS FLOAT64) >= {min_af}
        """)
    
    return " UNION ALL ".join(query_parts) + " ORDER BY CHROM, POS"

def download_from_gcs(bucket_path, local_dir):
    """Download exported files from GCS"""
    
    logger.info(f"Downloading from {bucket_path} to {local_dir}")
    
    cmd = ["gsutil", "-m", "cp", "-r", bucket_path, str(local_dir)]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info("✓ Download complete")
        
        # Combine files
        local_files = sorted(Path(local_dir).glob("*.csv.gz"))
        
        if local_files:
            combined_file = Path(local_dir) / "gnomad_all_afs_combined.tsv.gz"
            
            logger.info(f"Combining {len(local_files)} files...")
            
            # Use zcat and gzip to combine
            cmd = f"zcat {' '.join(str(f) for f in local_files)} | gzip > {combined_file}"
            subprocess.run(cmd, shell=True, check=True)
            
            logger.info(f"✓ Combined file: {combined_file}")
            
            return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Download failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Export ALL gnomAD AFs using BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Currently supports gnomAD v2.1.1 (v4 not yet in BigQuery).

This is the FASTEST method for getting all AFs:
1. Runs a single BigQuery job across all chromosomes
2. Exports compressed CSV to Google Cloud Storage
3. Downloads to local machine

Prerequisites:
- gcloud auth login
- gsutil configured
- BigQuery project set up

Examples:
  # Export all gnomAD v2.1.1 AFs to GCS
  python gnomad_v4_bigquery_export.py --export --bucket gs://my-bucket --project my-project
  
  # Export only common variants (AF >= 0.1%)
  python gnomad_v4_bigquery_export.py --export --bucket gs://my-bucket --project my-project --min-af 0.001
  
  # Download previously exported files
  python gnomad_v4_bigquery_export.py --download --bucket gs://my-bucket/gnomad_export --output ./gnomad_data
        """
    )
    
    parser.add_argument("--export", action="store_true", help="Export data from BigQuery")
    parser.add_argument("--download", action="store_true", help="Download from GCS")
    parser.add_argument("--bucket", help="GCS bucket (e.g., gs://my-bucket)")
    parser.add_argument("--project", help="BigQuery project ID")
    parser.add_argument("--output", help="Local output directory")
    parser.add_argument("--min-af", type=float, help="Minimum AF threshold for filtering")
    
    args = parser.parse_args()
    
    if args.export:
        if not args.bucket or not args.project:
            parser.error("--bucket and --project required for export")
        
        # Set project
        subprocess.run(["gcloud", "config", "set", "project", args.project], check=True)
        
        # Create dataset if needed
        dataset_name = f"{args.project}.gnomad_export"
        subprocess.run(["bq", "mk", "-d", dataset_name], capture_output=True)
        
        # Export
        output_prefix = f"{args.project}.gnomad_export"
        
        if args.min_af:
            logger.info(f"Exporting common variants (AF >= {args.min_af})")
            
            query = create_common_variants_query(args.min_af)
            output_file = Path(args.output) if args.output else Path("gnomad_common_variants.csv")
            
            cmd = [
                "bq", "query",
                "--use_legacy_sql=false",
                "--format=csv",
                "--max_rows=0",
                query
            ]
            
            with open(output_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            logger.info(f"✓ Exported to {output_file}")
        
        else:
            success = export_gnomad_v2_all_afs(args.bucket, output_prefix)
            
            if success:
                logger.info("\n✅ Export complete!")
                logger.info(f"Files are in: {args.bucket}")
                logger.info("To download: python gnomad_v4_bigquery_export.py --download --bucket <path> --output <dir>")
    
    elif args.download:
        if not args.bucket or not args.output:
            parser.error("--bucket and --output required for download")
        
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        download_from_gcs(args.bucket, output_dir)
    
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())