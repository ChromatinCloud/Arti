#!/usr/bin/env python3
"""
Process ClinVar Conflicting (C) variants through OncoKB API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.process_all_clinvar_oncokb import process_single_file
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
log_file = f"/tmp/clinvar_oncokb_C_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Process C.tsv file"""
    logger.info("Starting OncoKB processor for Conflicting (C) variants")
    logger.info(f"Log file: {log_file}")
    
    # Path to C.tsv
    c_file = Path(".refs/clinical_evidence/clinvar/clinvar_by_significance/C.tsv")
    
    if not c_file.exists():
        logger.error(f"File not found: {c_file}")
        return 1
    
    # Use batch size of 2000 for non-pathogenic variants
    batch_size = 2000
    
    logger.info(f"Processing {c_file.name} with batch size {batch_size}")
    logger.info(f"File size: {c_file.stat().st_size / (1024**2):.1f} MB")
    
    # Process the file
    process_single_file(str(c_file), batch_size=batch_size)
    
    logger.info(f"Completed processing {c_file.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())