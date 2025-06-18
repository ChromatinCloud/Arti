#!/usr/bin/env python3
"""
Process all ClinVar significance files through OncoKB API
Using 1000-variant batches for efficiency
"""

import sys
from pathlib import Path
import time
from datetime import datetime
import logging

# Set up logging
log_file = Path(f"/tmp/clinvar_oncokb_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent))
from clinvar_to_oncokb import process_clinvar_file

def estimate_processing_time(file_path: Path) -> float:
    """Estimate processing time based on file size"""
    size_mb = file_path.stat().st_size / (1024 * 1024)
    # Rough estimate: ~1000 variants per MB, 1000 variants per batch, 2 seconds per batch
    estimated_batches = size_mb  # Approximately
    estimated_seconds = estimated_batches * 2 + 60  # Add overhead
    return estimated_seconds

def main():
    clinvar_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/")
    oncokb_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/oncokb/oncokb_by_significance/")
    
    # Create output directory
    oncokb_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all ClinVar files
    clinvar_files = sorted(clinvar_dir.glob("*.tsv"))
    
    logger.info(f"Starting OncoKB annotation for {len(clinvar_files)} ClinVar files")
    logger.info(f"Using 1000-variant batches for efficiency")
    logger.info(f"Log file: {log_file}")
    
    # Process files in order of importance
    priority_order = ['PLP.tsv', 'P.tsv', 'VUS.tsv', 'C.tsv', 'BLB.tsv', 'B.tsv', 'Other.tsv']
    
    # Sort files by priority
    sorted_files = []
    for priority_name in priority_order:
        for f in clinvar_files:
            if f.name == priority_name:
                sorted_files.append(f)
                break
    
    # Add any files not in priority list
    for f in clinvar_files:
        if f not in sorted_files:
            sorted_files.append(f)
    
    total_start = time.time()
    
    for idx, clinvar_file in enumerate(sorted_files, 1):
        output_file = oncokb_dir / clinvar_file.name
        
        # Skip if already processed
        if output_file.exists():
            logger.info(f"[{idx}/{len(sorted_files)}] Skipping {clinvar_file.name} - already processed")
            continue
        
        # Estimate time
        estimated_time = estimate_processing_time(clinvar_file)
        logger.info(f"\n[{idx}/{len(sorted_files)}] Processing {clinvar_file.name}")
        logger.info(f"  File size: {clinvar_file.stat().st_size / (1024*1024):.1f} MB")
        logger.info(f"  Estimated time: {estimated_time/60:.1f} minutes")
        
        file_start = time.time()
        
        try:
            process_clinvar_file(clinvar_file, output_file)
            
            file_duration = time.time() - file_start
            logger.info(f"  Completed in {file_duration/60:.1f} minutes")
            
            # Quick stats
            import pandas as pd
            df = pd.read_csv(output_file, sep='\t', nrows=1000)
            logger.info(f"  Sample size: {len(df)} variants checked")
            
        except Exception as e:
            logger.error(f"  ERROR processing {clinvar_file.name}: {str(e)}")
            continue
        
        # Brief pause between files
        time.sleep(2)
    
    total_duration = time.time() - total_start
    logger.info(f"\n{'='*80}")
    logger.info(f"PROCESSING COMPLETE")
    logger.info(f"Total time: {total_duration/3600:.1f} hours")
    logger.info(f"Output directory: {oncokb_dir}")
    logger.info(f"Log file: {log_file}")
    
    # Run analysis on all results
    logger.info("\nRunning final analysis...")
    from analyze_oncokb_results import main as analyze_results
    analyze_results()

if __name__ == "__main__":
    # Show estimated total time
    clinvar_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/")
    total_size_gb = sum(f.stat().st_size for f in clinvar_dir.glob("*.tsv")) / (1024**3)
    
    # Updated estimate: 10M variants, 5K API calls with 2000 per batch
    estimated_hours = (5000 * 2 / 3600) + 0.5  # ~3 hours
    
    print(f"ClinVar to OncoKB Annotation Pipeline")
    print(f"{'='*50}")
    print(f"Total data size: {total_size_gb:.1f} GB")
    print(f"Estimated variants: ~10 million")
    print(f"API calls needed: ~5,000 (2000 variants per call)")
    print(f"Estimated total time: {estimated_hours:.1f} hours")
    print(f"\nStarting processing with 2000-variant batches...")
    print(f"The process is resumable - you can stop and restart anytime.")
    print(f"{'='*50}\n")
    
    main()