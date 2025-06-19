#!/usr/bin/env python3
"""
Process ClinVar Pathogenic/Likely Pathogenic (PLP) variants through OncoKB API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.process_all_clinvar_oncokb import process_single_file
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
log_file = f"/tmp/clinvar_oncokb_PLP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Process PLP.tsv file"""
    logger.info("Starting OncoKB processor for Pathogenic/Likely Pathogenic (PLP) variants")
    logger.info(f"Log file: {log_file}")
    
    # Path to PLP.tsv
    plp_file = Path(".refs/clinical_evidence/clinvar/clinvar_by_significance/PLP.tsv")
    
    if not plp_file.exists():
        logger.error(f"File not found: {plp_file}")
        return 1
    
    # Use smaller batch size for pathogenic variants (better OncoKB response)
    batch_size = 500
    
    logger.info(f"Processing {plp_file.name} with batch size {batch_size}")
    logger.info(f"File size: {plp_file.stat().st_size / (1024**2):.1f} MB")
    
    # Process the file
    process_single_file(str(plp_file), batch_size=batch_size)
    
    logger.info(f"Completed processing {plp_file.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())