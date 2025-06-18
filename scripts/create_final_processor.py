#!/usr/bin/env python3
"""
Final processor for B, LB, and BLB files
"""

import sys
from pathlib import Path
import time
from datetime import datetime
import logging

# Set up logging with different file name
log_file = Path(f"/tmp/clinvar_oncokb_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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

def main():
    clinvar_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/")
    oncokb_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/oncokb/oncokb_by_significance/")
    
    # Create output directory
    oncokb_dir.mkdir(parents=True, exist_ok=True)
    
    # Process B, LB, and BLB files after others complete
    priority_order = ['B.tsv', 'LB.tsv', 'BLB.tsv']
    
    logger.info(f"Starting FINAL OncoKB processor")
    logger.info(f"Will process: {', '.join(priority_order)}")
    logger.info(f"Log file: {log_file}")
    
    total_start = time.time()
    
    for idx, filename in enumerate(priority_order, 1):
        clinvar_file = clinvar_dir / filename
        output_file = oncokb_dir / filename
        
        if not clinvar_file.exists():
            logger.warning(f"File not found: {clinvar_file}")
            continue
            
        # Skip if already processed
        if output_file.exists():
            logger.info(f"[{idx}/{len(priority_order)}] Skipping {filename} - already processed")
            continue
        
        logger.info(f"\n[{idx}/{len(priority_order)}] Processing {filename}")
        logger.info(f"  File size: {clinvar_file.stat().st_size / (1024*1024):.1f} MB")
        
        file_start = time.time()
        
        try:
            process_clinvar_file(clinvar_file, output_file)
            
            file_duration = time.time() - file_start
            logger.info(f"  Completed in {file_duration/60:.1f} minutes")
            
        except Exception as e:
            logger.error(f"  ERROR processing {filename}: {str(e)}")
            continue
        
        # Brief pause between files
        time.sleep(2)
    
    total_duration = time.time() - total_start
    logger.info(f"\n{'='*80}")
    logger.info(f"FINAL PROCESSOR COMPLETE")
    logger.info(f"Total time: {total_duration/3600:.1f} hours")
    logger.info(f"Output directory: {oncokb_dir}")

if __name__ == "__main__":
    print(f"Starting FINAL OncoKB processor")
    print(f"This will process: B, LB, BLB")
    print(f"{'='*50}\n")
    
    main()