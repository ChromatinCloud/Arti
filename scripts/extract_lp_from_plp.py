#!/usr/bin/env python3
"""
Extract Likely Pathogenic (LP) variants from the PLP OncoKB results
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
log_file = f"/tmp/extract_LP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Extract LP variants from PLP file"""
    logger.info("Extracting Likely Pathogenic (LP) variants from PLP OncoKB results")
    logger.info(f"Log file: {log_file}")
    
    # Input and output paths
    plp_file = Path(".refs/clinical_evidence/oncokb/oncokb_by_significance/PLP.tsv")
    lp_file = Path(".refs/clinical_evidence/oncokb/oncokb_by_significance/LP.tsv")
    
    if not plp_file.exists():
        logger.error(f"PLP file not found: {plp_file}")
        return 1
    
    logger.info(f"Reading PLP file: {plp_file}")
    logger.info(f"File size: {plp_file.stat().st_size / (1024**3):.2f} GB")
    
    # Read the PLP file
    try:
        # Read in chunks for memory efficiency
        chunk_size = 100000
        lp_chunks = []
        total_plp = 0
        total_lp = 0
        
        for chunk in pd.read_csv(plp_file, sep='\t', chunksize=chunk_size):
            total_plp += len(chunk)
            
            # Filter for Likely Pathogenic
            # ClinVar uses "Likely pathogenic" in ClinicalSignificance column
            if 'ClinicalSignificance' in chunk.columns:
                lp_chunk = chunk[chunk['ClinicalSignificance'].str.contains('Likely pathogenic', na=False, case=False)]
            else:
                logger.error("ClinicalSignificance column not found!")
                return 1
            
            if len(lp_chunk) > 0:
                lp_chunks.append(lp_chunk)
                total_lp += len(lp_chunk)
            
            logger.info(f"Processed {total_plp:,} variants, found {total_lp:,} LP variants")
        
        # Combine all LP chunks
        if lp_chunks:
            logger.info("Combining LP chunks...")
            lp_df = pd.concat(lp_chunks, ignore_index=True)
            
            logger.info(f"Total PLP variants: {total_plp:,}")
            logger.info(f"Total LP variants: {len(lp_df):,}")
            logger.info(f"LP percentage: {len(lp_df)/total_plp*100:.1f}%")
            
            # Save LP file
            logger.info(f"Saving LP variants to: {lp_file}")
            lp_df.to_csv(lp_file, sep='\t', index=False)
            logger.info(f"LP file size: {lp_file.stat().st_size / (1024**2):.1f} MB")
            
            # Sample statistics
            if 'oncokb_data' in lp_df.columns:
                has_oncokb = lp_df['oncokb_data'].notna().sum()
                logger.info(f"LP variants with OncoKB annotations: {has_oncokb:,} ({has_oncokb/len(lp_df)*100:.1f}%)")
        else:
            logger.warning("No LP variants found in PLP file!")
            
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return 1
    
    logger.info("Extraction completed successfully!")
    return 0

if __name__ == "__main__":
    main()